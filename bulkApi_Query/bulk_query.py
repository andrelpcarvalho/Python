"""
bulk_query.py

Executa uma SOQL query em massa via Salesforce Bulk API 2.0 (Query),
baixando o resultado como CSV local. Mesmo fluxo assincrono do
bulk_update_account.py (criar job -> poll ate JobComplete -> baixar
resultado), so que aqui o job e de leitura (jobs/query), nao de ingest.

Autenticacao delegada ao modulo auth.py (Client Credentials Flow).

── PRE-REQUISITOS ──────────────────────────────────────────────
1. auth.py na mesma pasta
2. pip install -r requirements.txt (requests, python-dotenv)
3. Python >= 3.9

── VARIAVEIS DE AMBIENTE ───────────────────────────────────────
SF_CLIENT_ID       Consumer Key do Connected App     (usado por auth.py)
SF_CLIENT_SECRET   Consumer Secret do Connected App  (usado por auth.py)
SF_LOGIN_URL       https://SEU_DOMINIO.my.salesforce.com (usado por auth.py)
SF_API_VERSION     ex: v61.0
SF_OBJECT          objeto da query, ex: Account
SF_FIELDS          campos separados por virgula, ex: Id,Name,BillingCity
SF_WHERE           clausula WHERE opcional, ex: CreatedDate = TODAY
SF_OUTPUT_PATH     caminho do CSV de saida, ex: ./output/resultado.csv

── USO ─────────────────────────────────────────────────────────
python bulk_query.py
"""

import os
import sys
import time
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv

from auth import authenticate, AuthError

load_dotenv()

# ---------- CONFIG ----------
def build_config():
    return {
        "api_version": os.environ.get("SF_API_VERSION", "v61.0"),
        "object": os.environ.get("SF_OBJECT"),
        "fields": os.environ.get("SF_FIELDS"),
        "where": os.environ.get("SF_WHERE"),  # opcional
        "order_by": os.environ.get("SF_ORDER_BY"),  # opcional
        "limit": os.environ.get("SF_LIMIT"),  # opcional
        "output_path": os.environ.get("SF_OUTPUT_PATH", "./output/resultado.csv"),
        "poll_interval_sec": 5,
        "poll_timeout_sec": 60 * 60,  # 1h; ajuste se a query for muito pesada
        "page_size": 50000,  # registros por pagina no download do resultado
    }


CONFIG = build_config()

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "run.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def reload_config():
    """Relê o .env do disco e reconstrói o CONFIG. Usado pelo run.py
    depois que o config.py acabou de atualizar o .env."""
    global CONFIG
    load_dotenv(override=True)
    CONFIG = build_config()
    return CONFIG


def _headers(auth, content_type="application/json"):
    return {"Authorization": f"Bearer {auth['access_token']}", "Content-Type": content_type}


def _build_query():
    if not CONFIG["object"] or not CONFIG["fields"]:
        raise QueryApiError("SF_OBJECT e SF_FIELDS sao obrigatorios no .env")

    fields = ", ".join(f.strip() for f in CONFIG["fields"].split(","))
    query = f"SELECT {fields} FROM {CONFIG['object']}"
    if CONFIG["where"]:
        query += f" WHERE {CONFIG['where']}"
    if CONFIG["order_by"]:
        query += f" ORDER BY {CONFIG['order_by']}"
    if CONFIG["limit"]:
        query += f" LIMIT {CONFIG['limit']}"
    return query


# ---------- 1. CRIAR JOB ----------
def create_job(auth, query):
    url = f"{auth['instance_url']}/services/data/{CONFIG['api_version']}/jobs/query"
    resp = requests.post(
        url,
        headers=_headers(auth),
        json={"operation": "query", "query": query},
        timeout=30,
    )
    if not resp.ok:
        raise QueryApiError(f"Erro ao criar job: {resp.status_code} {resp.text}")
    return resp.json()


# ---------- 2. POLLING DE STATUS ----------
def wait_for_completion(auth, job_id):
    start = time.time()
    url = f"{auth['instance_url']}/services/data/{CONFIG['api_version']}/jobs/query/{job_id}"

    while True:
        resp = requests.get(url, headers=_headers(auth), timeout=30)
        if not resp.ok:
            raise QueryApiError(f"Erro ao consultar status: {resp.status_code} {resp.text}")
        data = resp.json()

        log.info(
            "Job %s -> state=%s recordCount=%s",
            job_id,
            data.get("state"),
            data.get("numberRecordsProcessed", 0),
        )

        if data["state"] == "JobComplete":
            return data
        if data["state"] in ("Failed", "Aborted"):
            raise QueryApiError(f"Job {job_id} terminou como {data['state']}")
        if time.time() - start > CONFIG["poll_timeout_sec"]:
            raise QueryApiError(f"Timeout esperando job {job_id} completar")

        time.sleep(CONFIG["poll_interval_sec"])


# ---------- 3. BAIXAR RESULTADO (paginado) ----------
def download_results(auth, job_id, output_path):
    url = f"{auth['instance_url']}/services/data/{CONFIG['api_version']}/jobs/query/{job_id}/results"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    locator = None
    first_page = True

    with open(output_path, "wb") as f:
        while True:
            params = {"maxRecords": CONFIG["page_size"]}
            if locator:
                params["locator"] = locator

            resp = requests.get(url, headers=_headers(auth), params=params, timeout=60)
            if not resp.ok:
                raise QueryApiError(f"Erro ao baixar resultado: {resp.status_code} {resp.text}")

            if first_page:
                f.write(resp.content)
                first_page = False
            else:
                # pula a linha de header nas paginas seguintes
                _, _, rest = resp.content.partition(b"\n")
                f.write(rest)

            locator = resp.headers.get("Sforce-Locator")
            if not locator or locator == "null":
                break

    log.info("Resultado salvo em %s", output_path)


# ---------- PIPELINE PRINCIPAL ----------
def run_query():
    query = _build_query()
    log.info("Query montada: %s", query)

    auth = authenticate()

    job = create_job(auth, query)
    log.info("Job criado: %s", job["id"])

    wait_for_completion(auth, job["id"])
    download_results(auth, job["id"], CONFIG["output_path"])

    log.info("=== Concluido: resultado em %s ===", CONFIG["output_path"])


def main():
    try:
        run_query()
    except AuthError as exc:
        log.error("Erro de autenticacao: %s", exc)
        sys.exit(1)
    except QueryApiError as exc:
        log.error("Erro no job de query: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()