import jwt
import time
import os
import requests
from dotenv import load_dotenv

load_dotenv()

private_key_path = os.getenv("SF_PRIVATE_KEY_PATH")
consumer_key = os.getenv("SF_CONSUMER_KEY")
username = os.getenv("SF_USERNAME")
login_url = os.getenv("SF_LOGIN_URL")

with open(private_key_path, "r") as f:
    private_key = f.read()

payload = {
    'iss': consumer_key,
    'sub': username,
    'aud': login_url,
    'exp': int(time.time()) + 180,  # 3 minutos, conforme recomendado pela Salesforce
}

assertion = jwt.encode(
    payload,
    private_key,
    algorithm='RS256'
)

response = requests.post(
    f"{login_url}/services/oauth2/token",
    data={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
    },
    timeout=30,
)

if not response.ok:
    print(f"Erro ao trocar o JWT pelo access token: {response.status_code} {response.text}")
    raise SystemExit(1)

token_data = response.json()

print("Autenticado com sucesso.")
print(f"access_token: {token_data['access_token']}")
print(f"instance_url: {token_data['instance_url']}")