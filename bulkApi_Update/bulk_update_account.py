"""
bulk_update_account.py

Atualiza o objeto Account em massa via Salesforce Bulk API 2.0,
processando N arquivos CSV em SEQUENCIA (um so comeca depois que
o anterior chega em JobComplete), sem intervencao humana.

Autenticacao delegada ao modulo auth.py (Client Credentials Flow).

── PRE-REQUISITOS ──────────────────────────────────────────────
1. Connected App no Salesforce com:
   - "Enable Client Credentials Flow" marcado
   - Run As: um usuario de integracao com o Profile/Permission Set
     correto para editar Account
2. pip install -r requirements.txt (requests)
3. Python >= 3.9
4. auth.py na mesma pasta

── VARIAVEIS DE AMBIENTE ───────────────────────────────────────
SF_CLIENT_ID       Consumer Key do Connected App     (usado por auth.py)
SF_CLIENT_SECRET   Consumer Secret do Connected App  (usado por auth.py)
SF_LOGIN_URL       https://SEU_DOMINIO.my.salesforce.com (usado por auth.py)
SF_API_VERSION     ex: v61.0
CSV_DIR            Diretorio com os 23 CSVs (nomeie 01_...csv, 02_...csv, ...)

── FORMATO DO CSV ──────────────────────────────────────────────
Precisa ter a coluna "Id" (Account Id de 18 digitos) + a coluna do campo a atualizar.
Ex: Id,Custom_Field__c

── USO ─────────────────────────────────────────────────────────
python bulk_update_account.py
"""

import os
import sys
import time
import glob
import logging
from pathlib import Path

import requests

from auth import authenticate, AuthError

# ---------- CONFIG ----------
CONFIG = {
    "api_version": os.environ.get("SF_API_VERSION", "v61.0"),
    "csv_dir": os.environ.get("CSV_DIR", "./csv"),
    "object": "Account",
    "operation": "update",
    "poll_interval_sec": 15,
    "poll_timeout_sec": 2 * 60 * 60,  # 2h por job; ajuste se 1M linhas demorar mais
    "stop_on_error": True,
}

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


class BulkApiError(Exception):
    pass


def _headers(auth, content_type="application/json"):
    return {"Authorization": f"Bearer {auth['access_token']}", "Content-Type": content_type}


# ---------- 1. CRIAR JOB ----------
def create_job(auth):
    url = f"{auth['instance_url']}/services/data/{CONFIG['api_version']}/jobs/ingest"
    resp = requests.post(
        url,
        headers=_headers(auth),
        json={
            "object": CONFIG["object"],
            "operation": CONFIG["operation"],
            "lineEnding": "LF",
        },
        timeout=30,
    )
    if not resp.ok:
        raise BulkApiError(f"Erro ao criar job: {resp.status_code} {resp.text}")
    return resp.json()


# ---------- 2. UPLOAD DO CSV ----------
def upload_csv(auth, job_id, file_path):
    url = f"{auth['instance_url']}/services/data/{CONFIG['api_version']}/jobs/ingest/{job_id}/batches"
    with open(file_path, "rb") as f:
        resp = requests.put(url, headers=_headers(auth, "text/csv"), data=f, timeout=600)
    if not resp.ok:
        raise BulkApiError(f"Erro ao subir CSV: {resp.status_code} {resp.text}")


# ---------- 3. FECHAR JOB ----------
def close_job(auth, job_id):
    url = f"{auth['instance_url']}/services/data/{CONFIG['api_version']}/jobs/ingest/{job_id}"
    resp = requests.patch(url, headers=_headers(auth), json={"state": "UploadComplete"}, timeout=30)
    if not resp.ok:
        raise BulkApiError(f"Erro ao fechar job: {resp.status_code} {resp.text}")


# ---------- 4. POLLING DE STATUS ----------
def wait_for_completion(auth, job_id):
    start = time.time()
    url = f"{auth['instance_url']}/services/data/{CONFIG['api_version']}/jobs/ingest/{job_id}"

    while True:
        resp = requests.get(url, headers=_headers(auth), timeout=30)
        if not resp.ok:
            raise BulkApiError(f"Erro ao consultar status: {resp.status_code} {resp.text}")
        data = resp.json()

        log.info(
            "Job %s -> state=%s processed=%s failed=%s",
            job_id,
            data.get("state"),
            data.get("numberRecordsProcessed", 0),
            data.get("numberRecordsFailed", 0),
        )

        if data["state"] == "JobComplete":
            return data
        if data["state"] in ("Failed", "Aborted"):
            raise BulkApiError(f"Job {job_id} terminou como {data['state']}")
        if time.time() - start > CONFIG["poll_timeout_sec"]:
            raise BulkApiError(f"Timeout esperando job {job_id} completar")

        time.sleep(CONFIG["poll_interval_sec"])


# ---------- 5. BAIXAR RESULTADOS (sucesso/erro) ----------
def download_results(auth, job_id, file_label):
    for kind in ("successfulResults", "failedResults"):
        url = f"{auth['instance_url']}/services/data/{CONFIG['api_version']}/jobs/ingest/{job_id}/{kind}"
        resp = requests.get(url, headers=_headers(auth), timeout=60)
        if not resp.ok:
            continue
        out_path = LOG_DIR / f"{file_label}_{kind}.csv"
        out_path.write_text(resp.text)
        log.info("Resultado salvo: %s", out_path)


# ---------- PIPELINE PRINCIPAL ----------
def process_file(auth, file_path):
    file_label = Path(file_path).stem
    log.info("=== Iniciando %s ===", file_label)

    job = create_job(auth)
    log.info("Job criado: %s", job["id"])

    upload_csv(auth, job["id"], file_path)
    log.info("CSV enviado para job %s", job["id"])

    close_job(auth, job["id"])
    log.info("Job %s fechado, aguardando processamento...", job["id"])

    final_status = wait_for_completion(auth, job["id"])
    download_results(auth, job["id"], file_label)

    failed = final_status.get("numberRecordsFailed", 0)
    if failed > 0:
        log.warning("ATENCAO: %s registros falharam em %s", failed, file_label)
        if CONFIG["stop_on_error"]:
            raise BulkApiError(f"Parando sequencia: falhas em {file_label}")

    log.info(
        "=== Concluido %s: %s processados ===\n",
        file_label,
        final_status.get("numberRecordsProcessed", 0),
    )


def main():
    files = sorted(
                    glob.glob(os.path.join(CONFIG["csv_dir"], "*.csv")),
                    key=lambda f: int(Path(f).stem.split("_")[-1])
                )

    if not files:
        log.error("Nenhum CSV encontrado em %s", CONFIG["csv_dir"])
        sys.exit(1)

    log.info("Encontrados %d arquivos.", len(files))

    for file_path in files:
        # Reautentica a cada arquivo (via auth.py) para evitar expiracao
        # do access_token em execucoes muito longas.
        try:
            auth = authenticate()
        except AuthError as exc:
            log.error("Falha na autenticacao: %s", exc)
            sys.exit(1)

        process_file(auth, file_path)

    log.info("TODOS OS ARQUIVOS PROCESSADOS COM SUCESSO.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log.error("ERRO FATAL: %s", exc)
        sys.exit(1)