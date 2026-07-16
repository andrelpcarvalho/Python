"""
bulk_query.py

Executa uma SOQL query em massa via Salesforce Bulk API 2.0
(Query), baixando o resultado como CSV local. Segue o mesmo fluxo
assincrono do bulk_update_account.py: cria job, faz poll ate
JobComplete, so que aqui o job e de leitura (jobs/query), nao de
ingest.

Objeto, campos e output path vem do .env (rode config.py antes
pra preencher/atualizar essas variaveis via terminal).
Autenticacao delegada ao modulo auth.py (Client Credentials Flow).

── PRE-REQUISITOS ──────────────────────────────────────────────
1. auth.py no mesmo diretorio
2. .env preenchido (rode: python config.py)
   - SF_CLIENT_ID, SF_CLIENT_SECRET, SF_LOGIN_URL (auth)
   - SF_OBJECT, SF_FIELDS, SF_OUTPUT_PATH (query)
3. pip install requests python-dotenv

── USO ──────────────────────────────────────────────────────────
python config.py              # preenche/atualiza o .env
python bulk_query_account.py  # roda a query
"""

import os
import time
import logging

import requests
from dotenv import load_dotenv

from auth import authenticate, AuthError

load_dotenv()

log = logging.getLogger(__name__)

API_VERSION = "v61.0"
POLL_INTERVAL = 5  # segundos entre cada checagem de status
MAX_RECORDS_PER_PAGE = 50000


class QueryJobError(Exception):
    pass


def _criar_job(instance_url: str, headers: dict, query: str) -> str:
    resp = requests.post(
        f"{instance_url}/services/data/{API_VERSION}/jobs/query",
        headers=headers,
        json={"operation": "query", "query": query},
        timeout=30,
    )
    resp.raise_for_status()
    job_id = resp.json()["id"]
    log.info("Job criado: %s", job_id)
    return job_id


def _aguardar_job(status_url: str, headers: dict) -> None:
    while True:
        resp = requests.get(status_url, headers=headers, timeout=30)
        resp.raise_for_status()
        state = resp.json()["state"]
        log.info("Status: %s", state)

        if state == "JobComplete":
            return
        if state in ("Failed", "Aborted"):
            raise QueryJobError(f"Job terminou com estado {state}")

        time.sleep(POLL_INTERVAL)


def _baixar_resultado(results_url: str, headers: dict, output_path: str) -> None:
    locator = None
    first_chunk = True

    with open(output_path, "wb") as f:
        while True:
            params = {"maxRecords": MAX_RECORDS_PER_PAGE}
            if locator:
                params["locator"] = locator

            resp = requests.get(results_url, headers=headers, params=params, timeout=60)
            resp.raise_for_status()

            if first_chunk:
                f.write(resp.content)
                first_chunk = False
            else:
                # pula a linha de header nas paginas seguintes
                _, _, resto = resp.content.partition(b"\n")
                f.write(resto)

            locator = resp.headers.get("Sforce-Locator")
            if not locator or locator == "null":
                break

    log.info("Resultado salvo em %s", output_path)


def run_query(query: str, output_path: str = "resultado.csv") -> str:
    """Executa a query e salva o resultado em output_path. Retorna o path."""
    auth = authenticate()
    instance_url = auth["instance_url"]
    headers = {
        "Authorization": f"Bearer {auth['access_token']}",
        "Content-Type": "application/json",
    }

    job_id = _criar_job(instance_url, headers, query)
    status_url = f"{instance_url}/services/data/{API_VERSION}/jobs/query/{job_id}"

    _aguardar_job(status_url, headers)
    _baixar_resultado(f"{status_url}/results", headers, output_path)

    return output_path


def _montar_query_do_env() -> tuple[str, str]:
    """Le SF_OBJECT / SF_FIELDS / SF_OUTPUT_PATH do .env e monta a SOQL.

    Retorna (query, output_path).
    """
    objeto = os.environ.get("SF_OBJECT")
    campos = os.environ.get("SF_FIELDS")
    output_path = os.environ.get("SF_OUTPUT_PATH", "resultado.csv")

    if not objeto or not campos:
        raise QueryJobError(
            "SF_OBJECT e SF_FIELDS nao encontrados no .env. Rode 'python config.py' primeiro."
        )

    campos_formatados = ", ".join(c.strip() for c in campos.split(","))
    query = f"SELECT {campos_formatados} FROM {objeto}"
    return query, output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")

    try:
        query, output_path = _montar_query_do_env()
        log.info("Query montada: %s", query)
        run_query(query, output_path)
    except AuthError as exc:
        log.error("Erro de autenticacao: %s", exc)
    except QueryJobError as exc:
        log.error("Erro no job de query: %s", exc)