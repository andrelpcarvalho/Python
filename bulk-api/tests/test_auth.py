import pytest

from auth import authenticate, AuthError


def test_authenticate_missing_credentials_raises(monkeypatch):
    monkeypatch.delenv("SF_CLIENT_ID", raising=False)
    monkeypatch.delenv("SF_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("SF_LOGIN_URL", raising=False)

    with pytest.raises(AuthError, match="obrigatorios"):
        authenticate()


def test_authenticate_success(monkeypatch, requests_mock):
    monkeypatch.setenv("SF_CLIENT_ID", "client-id")
    monkeypatch.setenv("SF_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("SF_LOGIN_URL", "https://suaorg.my.salesforce.com")

    requests_mock.post(
        "https://suaorg.my.salesforce.com/services/oauth2/token",
        json={"access_token": "abc123", "instance_url": "https://suaorg.my.salesforce.com"},
        status_code=200,
    )

    result = authenticate()

    assert result == {"access_token": "abc123", "instance_url": "https://suaorg.my.salesforce.com"}


def test_authenticate_sends_client_credentials_grant(monkeypatch, requests_mock):
    monkeypatch.setenv("SF_CLIENT_ID", "client-id")
    monkeypatch.setenv("SF_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("SF_LOGIN_URL", "https://suaorg.my.salesforce.com")

    requests_mock.post(
        "https://suaorg.my.salesforce.com/services/oauth2/token",
        json={"access_token": "abc123", "instance_url": "https://suaorg.my.salesforce.com"},
        status_code=200,
    )

    authenticate()

    sent_body = requests_mock.last_request.text
    assert "grant_type=client_credentials" in sent_body
    assert "client_id=client-id" in sent_body
    assert "client_secret=client-secret" in sent_body


def test_authenticate_http_error_raises_autherror(monkeypatch, requests_mock):
    monkeypatch.setenv("SF_CLIENT_ID", "client-id")
    monkeypatch.setenv("SF_CLIENT_SECRET", "wrong-secret")
    monkeypatch.setenv("SF_LOGIN_URL", "https://suaorg.my.salesforce.com")

    requests_mock.post(
        "https://suaorg.my.salesforce.com/services/oauth2/token",
        json={"error": "invalid_client"},
        status_code=400,
    )

    with pytest.raises(AuthError, match="400"):
        authenticate()
