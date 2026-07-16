"""
gen_jwt.py

Monta um JWT assinado com a chave privada (gen_cert.py) e troca pelo
access token no endpoint OAuth do Salesforce (JWT Bearer Flow).

── VARIAVEIS DE AMBIENTE ───────────────────────────────────────
SF_PRIVATE_KEY_PATH  caminho da chave privada (gerada por gen_cert.py)
SF_CONSUMER_KEY      Consumer Key da Connected App
SF_USERNAME           usuário pre-authorized na Connected App
SF_LOGIN_URL          https://login.salesforce.com ou https://test.salesforce.com

── USO ─────────────────────────────────────────────────────────
python gen_jwt.py
"""

import os
import time

import jwt
import requests
from dotenv import load_dotenv

load_dotenv()


def build_assertion(private_key: str, consumer_key: str, username: str, login_url: str) -> str:
    """Monta e assina o JWT (assertion) usado no JWT Bearer Flow."""
    payload = {
        "iss": consumer_key,
        "sub": username,
        "aud": login_url,
        "exp": int(time.time()) + 180,  # 3 minutos, conforme recomendado pela Salesforce
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def exchange_token(login_url: str, assertion: str) -> dict:
    """Troca o JWT assinado pelo access token. Levanta RuntimeError se falhar."""
    response = requests.post(
        f"{login_url}/services/oauth2/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        },
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Erro ao trocar o JWT pelo access token: {response.status_code} {response.text}")
    return response.json()


def main():
    private_key_path = os.getenv("SF_PRIVATE_KEY_PATH")
    consumer_key = os.getenv("SF_CONSUMER_KEY")
    username = os.getenv("SF_USERNAME")
    login_url = os.getenv("SF_LOGIN_URL")

    with open(private_key_path, "r") as f:
        private_key = f.read()

    assertion = build_assertion(private_key, consumer_key, username, login_url)

    try:
        token_data = exchange_token(login_url, assertion)
    except RuntimeError as exc:
        print(str(exc))
        raise SystemExit(1)

    print("Autenticado com sucesso.")
    print(f"access_token: {token_data['access_token']}")
    print(f"instance_url: {token_data['instance_url']}")


if __name__ == "__main__":
    main()
