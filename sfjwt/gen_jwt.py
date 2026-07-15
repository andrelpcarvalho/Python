import jwt
import time
import os
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

token = jwt.encode(
    payload,
    private_key,
    algorithm='RS256'
)

print(token)
