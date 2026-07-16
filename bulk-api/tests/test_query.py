import pytest

import query


def set_config(monkeypatch, **env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    query.CONFIG = query.build_config()
    return query.CONFIG


# ---------- build_config / _build_query ----------

def test_build_query_minimal(monkeypatch):
    set_config(monkeypatch, SF_OBJECT="Account", SF_FIELDS="Id,Name")
    assert query._build_query() == "SELECT Id, Name FROM Account"


def test_build_query_with_where(monkeypatch):
    set_config(monkeypatch, SF_OBJECT="Account", SF_FIELDS="Id", SF_WHERE="Name = 'Acme'")
    assert query._build_query() == "SELECT Id FROM Account WHERE Name = 'Acme'"


def test_build_query_with_order_by_and_limit(monkeypatch):
    set_config(
        monkeypatch,
        SF_OBJECT="Account",
        SF_FIELDS="Id,Name",
        SF_ORDER_BY="CreatedDate DESC",
        SF_LIMIT="100",
    )
    assert query._build_query() == "SELECT Id, Name FROM Account ORDER BY CreatedDate DESC LIMIT 100"


def test_build_query_full_clause_order(monkeypatch):
    """WHERE, ORDER BY e LIMIT precisam sair nessa ordem exata (sintaxe SOQL)."""
    set_config(
        monkeypatch,
        SF_OBJECT="Contact",
        SF_FIELDS="Id, Email",
        SF_WHERE="Email != null",
        SF_ORDER_BY="Email",
        SF_LIMIT="50",
    )
    assert query._build_query() == (
        "SELECT Id, Email FROM Contact WHERE Email != null ORDER BY Email LIMIT 50"
    )


def test_build_query_missing_object_raises(monkeypatch):
    set_config(monkeypatch, SF_FIELDS="Id")
    with pytest.raises(query.QueryApiError, match="SF_OBJECT"):
        query._build_query()


def test_build_query_missing_fields_raises(monkeypatch):
    set_config(monkeypatch, SF_OBJECT="Account")
    with pytest.raises(query.QueryApiError, match="SF_FIELDS"):
        query._build_query()


def test_build_config_defaults(monkeypatch):
    cfg = set_config(monkeypatch, SF_OBJECT="Account", SF_FIELDS="Id")
    assert cfg["api_version"] == "v61.0"
    assert cfg["output_path"] == "./output/resultado.csv"
    assert cfg["where"] is None
    assert cfg["order_by"] is None
    assert cfg["limit"] is None


# ---------- create_job ----------

def test_create_job_success(monkeypatch, requests_mock, fake_auth):
    set_config(monkeypatch, SF_API_VERSION="v61.0")
    requests_mock.post(
        f"{fake_auth['instance_url']}/services/data/v61.0/jobs/query",
        json={"id": "750xx000000001", "state": "UploadComplete"},
        status_code=200,
    )

    result = query.create_job(fake_auth, "SELECT Id FROM Account")

    assert result["id"] == "750xx000000001"


def test_create_job_failure_raises(monkeypatch, requests_mock, fake_auth):
    set_config(monkeypatch, SF_API_VERSION="v61.0")
    requests_mock.post(
        f"{fake_auth['instance_url']}/services/data/v61.0/jobs/query",
        json={"message": "INVALID_FIELD"},
        status_code=400,
    )

    with pytest.raises(query.QueryApiError, match="400"):
        query.create_job(fake_auth, "SELECT Nope FROM Account")


# ---------- wait_for_completion ----------

def test_wait_for_completion_returns_on_job_complete(monkeypatch, requests_mock, fake_auth):
    set_config(monkeypatch, SF_API_VERSION="v61.0")
    requests_mock.get(
        f"{fake_auth['instance_url']}/services/data/v61.0/jobs/query/750xx",
        json={"state": "JobComplete", "numberRecordsProcessed": 42},
        status_code=200,
    )

    result = query.wait_for_completion(fake_auth, "750xx")

    assert result["state"] == "JobComplete"
    assert result["numberRecordsProcessed"] == 42


def test_wait_for_completion_raises_on_failed(monkeypatch, requests_mock, fake_auth):
    set_config(monkeypatch, SF_API_VERSION="v61.0")
    requests_mock.get(
        f"{fake_auth['instance_url']}/services/data/v61.0/jobs/query/750xx",
        json={"state": "Failed"},
        status_code=200,
    )

    with pytest.raises(query.QueryApiError, match="Failed"):
        query.wait_for_completion(fake_auth, "750xx")


def test_wait_for_completion_times_out(monkeypatch, requests_mock, fake_auth):
    cfg = set_config(monkeypatch, SF_API_VERSION="v61.0")
    cfg["poll_timeout_sec"] = 0  # força timeout na primeira checagem
    cfg["poll_interval_sec"] = 0
    requests_mock.get(
        f"{fake_auth['instance_url']}/services/data/v61.0/jobs/query/750xx",
        json={"state": "InProgress"},
        status_code=200,
    )

    with pytest.raises(query.QueryApiError, match="Timeout"):
        query.wait_for_completion(fake_auth, "750xx")


# ---------- download_results ----------

def test_download_results_single_page(monkeypatch, requests_mock, fake_auth, tmp_path):
    set_config(monkeypatch, SF_API_VERSION="v61.0")
    output_path = tmp_path / "out" / "resultado.csv"

    requests_mock.get(
        f"{fake_auth['instance_url']}/services/data/v61.0/jobs/query/750xx/results",
        content=b"Id,Name\n001,Acme\n",
        headers={"Sforce-Locator": "null"},
        status_code=200,
    )

    query.download_results(fake_auth, "750xx", str(output_path))

    assert output_path.read_text() == "Id,Name\n001,Acme\n"


def test_download_results_paginated_skips_header_after_first_page(monkeypatch, requests_mock, fake_auth, tmp_path):
    set_config(monkeypatch, SF_API_VERSION="v61.0")
    output_path = tmp_path / "resultado.csv"

    responses = [
        {"content": b"Id,Name\n001,Acme\n", "headers": {"Sforce-Locator": "page2"}, "status_code": 200},
        {"content": b"Id,Name\n002,Globex\n", "headers": {"Sforce-Locator": "null"}, "status_code": 200},
    ]
    requests_mock.get(
        f"{fake_auth['instance_url']}/services/data/v61.0/jobs/query/750xx/results",
        responses,
    )

    query.download_results(fake_auth, "750xx", str(output_path))

    content = output_path.read_text()
    assert content == "Id,Name\n001,Acme\n002,Globex\n"
    assert content.count("Id,Name") == 1  # header não duplicado
