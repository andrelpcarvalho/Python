"""
bulk_update.py

Atualiza QUALQUER objeto do Salesforce em massa via Bulk API 2.0,
processando N arquivos CSV em SEQUENCIA (um so comeca depois que
o anterior chega em JobComplete), sem intervencao humana.

Se as colunas do CSV nao baterem com os nomes de campo da API,
rode field_mapping.py antes — ele gera header_mapping.json, que
este script aplica automaticamente (reescrevendo so a linha de
header de cada CSV antes do upload; o corpo e copiado bruto, sem
reprocessar as linhas, entao funciona bem mesmo em arquivos de
milhoes de linhas).

Autenticacao delegada ao modulo auth.py (Client Credentials Flow).

── PRE-REQUISITOS ──────────────────────────────────────────────
1. Connected App no Salesforce com "Enable Client Credentials Flow"
   e "Run As" apontando pro usuario de integracao com permissao no
   objeto e operacao escolhidos.
2. pip install -r requirements.txt
3. auth.py na mesma pasta
4. (Opcional) header_mapping.json gerado por field_mapping.py, se
   as colunas do CSV nao baterem com a API.

── VARIAVEIS DE AMBIENTE ───────────────────────────────────────
SF_CLIENT_ID          Consumer Key do Connected App     (usado por auth.py)
SF_CLIENT_SECRET      Consumer Secret do Connected App  (usado por auth.py)
SF_LOGIN_URL          https://SEU_DOMINIO.my.salesforce.com (usado por auth.py)
SF_API_VERSION        ex: v61.0
SF_OBJECT             objeto alvo, ex: Account, Contact, Custom_Object__c
SF_OPERATION          insert | update | upsert | delete  (padrão: update)
SF_EXTERNAL_ID_FIELD  obrigatório só se SF_OPERATION=upsert
CSV_DIR               diretório com os CSVs (nomeados 01_...csv, 02_...csv, ...)
HEADER_MAPPING_PATH   caminho do mapping gerado por field_mapping.py (padrão: header_mapping.json)

── USO ─────────────────────────────────────────────────────────
python bulk_update.py
"""

import csv
import glob
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from auth import authenticate, AuthError

load_dotenv()

VALID_OPERATIONS = {"insert", "update", "upsert", "delete"}


def build_config():
    return {
        "api_version": os.environ.get("SF_API_VERSION", "v61.0"),
        "object": os.environ.get("SF_OBJECT"),
        "operation": os.environ.get("SF_OPERATION", "update").lower(),
        "external_id_field": os.environ.get("SF_EXTERNAL_ID_FIELD"),
        "csv_dir": os.environ.get("CSV_DIR", "./csv"),
        "mapping_path": os.environ.get("HEADER_MAPPING_PATH", "header_mapping.json"),
        "poll_interval_sec": 15,
        "poll_timeout_sec": 2 * 60 * 60,  # 2h por job; ajuste se 1M linhas demorar mais
        "stop_on_error": True,
    }


# ---------- CONFIG ----------
CONFIG = build_config()

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

import logging

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


def reload_config():
    """Relê o .env do disco e reconstrói o CONFIG. Usado pelo run.py
    depois que o config.py acabou de atualizar o .env."""
    global CONFIG
    load_dotenv(override=True)
    CONFIG = build_config()
    return CONFIG


def _headers(auth, content_type="application/json"):
    return {"Authorization": f"Bearer {auth['access_token']}", "Content-Type": content_type}


def validate_config():
    if not CONFIG["object"]:
        raise BulkApiError("SF_OBJECT não definido no .env")
    if CONFIG["operation"] not in VALID_OPERATIONS:
        raise BulkApiError(f"SF_OPERATION inválido: '{CONFIG['operation']}'. Use um de {VALID_OPERATIONS}")
    if CONFIG["operation"] == "upsert" and not CONFIG["external_id_field"]:
        raise BulkApiError("SF_EXTERNAL_ID_FIELD é obrigatório quando SF_OPERATION=upsert")


# ---------- MAPEAMENTO DE HEADER ----------
def load_mapping():
    path = CONFIG["mapping_path"]
    if not path or not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_mapping(file_path, mapping):
    """Reescreve só a linha de header do CSV, usando o mapping.
    O corpo do arquivo é copiado bruto (sem reparsear), pra suportar
    arquivos de milhões de linhas sem custo extra relevante.
    Retorna o path a usar no upload (temporário se houve reescrita,
    ou o original se não havia nada pra trocar).
    """
    if not mapping:
        return file_path, None

    with open(file_path, "r", newline="", encoding="utf-8-sig") as infile:
        original_header = next(csv.reader(infile))

    new_header = [mapping.get(col, col) for col in original_header]
    if new_header == original_header:
        return file_path, None

    tmp = tempfile.NamedTemporaryFile(
        mode="w", newline="", suffix=".csv", delete=False, encoding="utf-8", dir=LOG_DIR
    )
    with open(file_path, "r", newline="", encoding="utf-8-sig") as infile:
        infile.readline()  # pula o header antigo
        writer = csv.writer(tmp)
        writer.writerow(new_header)
        tmp.flush()
        shutil.copyfileobj(infile, tmp)
    tmp.close()

    return tmp.name, tmp.name  # segundo valor = marca pra deletar depois


def validate_mapped_header(header):
    """Confere se o header final tem o que a operação exige, antes de
    gastar tempo subindo milhões de linhas que vão falhar de qualquer jeito.
    """
    if CONFIG["operation"] in ("update", "delete") and "Id" not in header:
        raise BulkApiError(
            f"Operação '{CONFIG['operation']}' exige uma coluna 'Id' no CSV (após o mapeamento). "
            f"Colunas atuais: {header}"
        )
    if CONFIG["operation"] == "upsert" and CONFIG["external_id_field"] not in header:
        raise BulkApiError(
            f"Operação 'upsert' exige a coluna '{CONFIG['external_id_field']}' no CSV (após o mapeamento). "
            f"Colunas atuais: {header}"
        )


# ---------- 1. CRIAR JOB ----------
def create_job(auth):
    url = f"{auth['instance_url']}/services/data/{CONFIG['api_version']}/jobs/ingest"
    body = {
        "object": CONFIG["object"],
        "operation": CONFIG["operation"],
        "lineEnding": "LF",
    }
    if CONFIG["operation"] == "upsert":
        body["externalIdFieldName"] = CONFIG["external_id_field"]

    resp = requests.post(url, headers=_headers(auth), json=body, timeout=30)
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
def process_file(auth, file_path, mapping):
    file_label = Path(file_path).stem
    log.info("=== Iniciando %s (objeto=%s, operação=%s) ===", file_label, CONFIG["object"], CONFIG["operation"])

    upload_path, tmp_to_delete = apply_mapping(file_path, mapping)

    job = create_job(auth)
    log.info("Job criado: %s", job["id"])

    try:
        upload_csv(auth, job["id"], upload_path)
        log.info("CSV enviado para job %s", job["id"])

        close_job(auth, job["id"])
        log.info("Job %s fechado, aguardando processamento...", job["id"])

        final_status = wait_for_completion(auth, job["id"])
        download_results(auth, job["id"], file_label)
    finally:
        if tmp_to_delete:
            os.remove(tmp_to_delete)

    failed = final_status.get("numberRecordsFailed", 0)
    if failed > 0:
        log.warning("ATENÇÃO: %s registros falharam em %s", failed, file_label)
        if CONFIG["stop_on_error"]:
            raise BulkApiError(f"Parando sequência: falhas em {file_label}")

    log.info("=== Concluído %s: %s processados ===\n", file_label, final_status.get("numberRecordsProcessed", 0))


def main():
    try:
        validate_config()
    except BulkApiError as exc:
        log.error("Configuração inválida: %s", exc)
        sys.exit(1)

    files = sorted(
        glob.glob(os.path.join(CONFIG["csv_dir"], "*.csv")),
        key=lambda f: int(Path(f).stem.split("_")[-1]) if Path(f).stem.split("_")[-1].isdigit() else 0,
    )
    if not files:
        log.error("Nenhum CSV encontrado em %s", CONFIG["csv_dir"])
        sys.exit(1)

    mapping = load_mapping()
    if mapping:
        log.info("Usando mapeamento de colunas: %s", CONFIG["mapping_path"])

    # Valida o header do primeiro arquivo antes de processar os 23 —
    # falha rápido se faltar Id / external id field.
    with open(files[0], "r", newline="", encoding="utf-8-sig") as f:
        original_header = next(csv.reader(f))
    mapped_header = [mapping.get(c, c) for c in original_header] if mapping else original_header
    try:
        validate_mapped_header(mapped_header)
    except BulkApiError as exc:
        log.error(str(exc))
        sys.exit(1)

    log.info("Encontrados %d arquivos. Objeto=%s Operação=%s", len(files), CONFIG["object"], CONFIG["operation"])

    for file_path in files:
        try:
            auth = authenticate()
        except AuthError as exc:
            log.error("Falha na autenticação: %s", exc)
            sys.exit(1)

        process_file(auth, file_path, mapping)

    log.info("TODOS OS ARQUIVOS PROCESSADOS COM SUCESSO.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log.error("ERRO FATAL: %s", exc)
        sys.exit(1)