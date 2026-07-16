import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from gen_jwt import build_assertion, exchange_token


@pytest.fixture
def rsa_private_key_pem():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def test_build_assertion_contains_expected_claims(rsa_private_key_pem):
    assertion = build_assertion(
        private_key=rsa_private_key_pem,
        consumer_key="consumer123",
        username="user@org.com",
        login_url="https://login.salesforce.com",
    )

    decoded = pyjwt.decode(assertion, options={"verify_signature": False})
    assert decoded["iss"] == "consumer123"
    assert decoded["sub"] == "user@org.com"
    assert decoded["aud"] == "https://login.salesforce.com"
    assert "exp" in decoded


def test_build_assertion_expires_in_about_180_seconds(rsa_private_key_pem):
    import time

    before = int(time.time())
    assertion = build_assertion(rsa_private_key_pem, "ck", "user@org.com", "https://login.salesforce.com")
    decoded = pyjwt.decode(assertion, options={"verify_signature": False})

    assert 170 <= (decoded["exp"] - before) <= 190


def test_exchange_token_success(requests_mock):
    requests_mock.post(
        "https://login.salesforce.com/services/oauth2/token",
        json={"access_token": "abc123", "instance_url": "https://myorg.my.salesforce.com"},
        status_code=200,
    )

    result = exchange_token("https://login.salesforce.com", "fake-assertion")

    assert result["access_token"] == "abc123"
    assert result["instance_url"] == "https://myorg.my.salesforce.com"


def test_exchange_token_sends_jwt_bearer_grant(requests_mock):
    requests_mock.post(
        "https://login.salesforce.com/services/oauth2/token",
        json={"access_token": "abc123", "instance_url": "https://myorg.my.salesforce.com"},
        status_code=200,
    )

    exchange_token("https://login.salesforce.com", "my-jwt-assertion")

    sent_body = requests_mock.last_request.text
    assert "grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer" in sent_body
    assert "assertion=my-jwt-assertion" in sent_body


def test_exchange_token_failure_raises_runtime_error(requests_mock):
    requests_mock.post(
        "https://login.salesforce.com/services/oauth2/token",
        json={"error": "invalid_grant", "error_description": "expired assertion"},
        status_code=400,
    )

    with pytest.raises(RuntimeError, match="400"):
        exchange_token("https://login.salesforce.com", "fake-assertion")
