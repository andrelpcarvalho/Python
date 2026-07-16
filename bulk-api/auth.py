"""
auth.py

Responsável só pela autenticação Salesforce via OAuth 2.0
Client Credentials Flow. Usado como módulo (import) pelo
bulk_update_account.py, mas também roda standalone pra
testar as credenciais isoladamente.

── VARIAVEIS DE AMBIENTE ───────────────────────────────────────
SF_CLIENT_ID       Consumer Key do Connected App
SF_CLIENT_SECRET   Consumer Secret do Connected App
SF_LOGIN_URL       https://SEU_DOMINIO.my.salesforce.com

── USO STANDALONE (só pra testar login) ────────────────────────
python auth.py
"""

import os
import sys
import logging

import requests

log = logging.getLogger(__name__)


class AuthError(Exception):
    pass


def authenticate():
    """Autentica via Client Credentials Flow.

    Retorna dict: {"access_token": ..., "instance_url": ...}
    """
    client_id = os.environ.get("SF_CLIENT_ID")
    client_secret = os.environ.get("SF_CLIENT_SECRET")
    login_url = os.environ.get("SF_LOGIN_URL")

    if not all([client_id, client_secret, login_url]):
        raise AuthError("SF_CLIENT_ID, SF_CLIENT_SECRET e SF_LOGIN_URL sao obrigatorios")

    resp = requests.post(
        f"{login_url}/services/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    if not resp.ok:
        raise AuthError(f"Falha na autenticacao: {resp.status_code} {resp.text}")

    data = resp.json()
    return {"access_token": data["access_token"], "instance_url": data["instance_url"]}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    try:
        auth = authenticate()
        log.info("Autenticado com sucesso.")
        log.info("instance_url: %s", auth["instance_url"])
        log.info("access_token: %s...%s (ocultado)", auth["access_token"][:8], auth["access_token"][-4:])
    except AuthError as exc:
        log.error("ERRO: %s", exc)
        sys.exit(1)
