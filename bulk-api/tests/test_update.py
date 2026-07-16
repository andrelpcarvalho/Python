import json

import pytest

import update


def set_config(monkeypatch, **env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    update.CONFIG = update.build_config()
    return update.CONFIG


# ---------- validate_config ----------

def test_validate_config_missing_object_raises(monkeypatch):
    set_config(monkeypatch)
    with pytest.raises(update.BulkApiError, match="SF_OBJECT"):
        update.validate_config()


def test_validate_config_invalid_operation_raises(monkeypatch):
    set_config(monkeypatch, SF_OBJECT="Account", SF_OPERATION="delete_all")
    with pytest.raises(update.BulkApiError, match="SF_OPERATION"):
        update.validate_config()


def test_validate_config_upsert_without_external_id_raises(monkeypatch):
    set_config(monkeypatch, SF_OBJECT="Account", SF_OPERATION="upsert")
    with pytest.raises(update.BulkApiError, match="SF_EXTERNAL_ID_FIELD"):
        update.validate_config()


def test_validate_config_upsert_with_external_id_ok(monkeypatch):
    set_config(monkeypatch, SF_OBJECT="Account", SF_OPERATION="upsert", SF_EXTERNAL_ID_FIELD="External_Id__c")
    update.validate_config()  # não deve levantar


def test_validate_config_default_operation_is_update(monkeypatch):
    cfg = set_config(monkeypatch, SF_OBJECT="Account")
    assert cfg["operation"] == "update"


# ---------- validate_mapped_header ----------

def test_validate_mapped_header_update_requires_id(monkeypatch):
    set_config(monkeypatch, SF_OBJECT="Account", SF_OPERATION="update")
    with pytest.raises(update.BulkApiError, match="Id"):
        update.validate_mapped_header(["Name", "BillingCity"])


def test_validate_mapped_header_update_with_id_ok(monkeypatch):
    set_config(monkeypatch, SF_OBJECT="Account", SF_OPERATION="update")
    update.validate_mapped_header(["Id", "Name"])  # não deve levantar


def test_validate_mapped_header_insert_does_not_require_id(monkeypatch):
    set_config(monkeypatch, SF_OBJECT="Account", SF_OPERATION="insert")
    update.validate_mapped_header(["Name", "BillingCity"])  # não deve levantar


def test_validate_mapped_header_upsert_requires_external_id_field(monkeypatch):
    set_config(monkeypatch, SF_OBJECT="Account", SF_OPERATION="upsert", SF_EXTERNAL_ID_FIELD="External_Id__c")
    with pytest.raises(update.BulkApiError, match="External_Id__c"):
        update.validate_mapped_header(["Name"])


def test_validate_mapped_header_delete_requires_id(monkeypatch):
    set_config(monkeypatch, SF_OBJECT="Account", SF_OPERATION="delete")
    with pytest.raises(update.BulkApiError, match="Id"):
        update.validate_mapped_header(["Name"])


# ---------- apply_mapping ----------

def test_apply_mapping_no_mapping_returns_original_path(tmp_path):
    csv_file = tmp_path / "dados.csv"
    csv_file.write_text("Id,Name\n001,Acme\n")

    upload_path, tmp_to_delete = update.apply_mapping(str(csv_file), None)

    assert upload_path == str(csv_file)
    assert tmp_to_delete is None


def test_apply_mapping_identity_mapping_returns_original_path(tmp_path):
    csv_file = tmp_path / "dados.csv"
    csv_file.write_text("Id,Name\n001,Acme\n")

    upload_path, tmp_to_delete = update.apply_mapping(str(csv_file), {"Id": "Id", "Name": "Name"})

    assert upload_path == str(csv_file)
    assert tmp_to_delete is None


def test_apply_mapping_rewrites_header_only(tmp_path, monkeypatch):
    # LOG_DIR é onde o arquivo temporário é criado; aponta pro tmp_path do teste
    monkeypatch.setattr(update, "LOG_DIR", tmp_path)

    csv_file = tmp_path / "dados.csv"
    csv_file.write_text("id_conta,nome_completo\n001,Acme Corp\n002,Globex Corp\n")

    mapping = {"id_conta": "Id", "nome_completo": "Name"}
    upload_path, tmp_to_delete = update.apply_mapping(str(csv_file), mapping)

    assert upload_path != str(csv_file)  # é um arquivo temporário novo
    assert tmp_to_delete == upload_path

    content = open(upload_path, newline="", encoding="utf-8").read()
    assert content == "Id,Name\r\n001,Acme Corp\n002,Globex Corp\n"

    update.os.remove(upload_path)  # limpeza


def test_apply_mapping_preserves_row_count_for_large_body(tmp_path, monkeypatch):
    monkeypatch.setattr(update, "LOG_DIR", tmp_path)

    csv_file = tmp_path / "dados.csv"
    rows = [f"{i},Nome {i}\n" for i in range(1000)]
    csv_file.write_text("id_conta,nome\n" + "".join(rows))

    upload_path, tmp_to_delete = update.apply_mapping(str(csv_file), {"id_conta": "Id", "nome": "Name"})

    with open(upload_path, encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1001  # header + 1000 linhas
    assert lines[0].strip() == "Id,Name"

    update.os.remove(upload_path)


# ---------- load_mapping ----------

def test_load_mapping_missing_file_returns_none(monkeypatch, tmp_path):
    set_config(monkeypatch, SF_OBJECT="Account", HEADER_MAPPING_PATH=str(tmp_path / "nao_existe.json"))
    assert update.load_mapping() is None


def test_load_mapping_reads_json(monkeypatch, tmp_path):
    mapping_file = tmp_path / "header_mapping.json"
    mapping_file.write_text(json.dumps({"id_conta": "Id"}))
    set_config(monkeypatch, SF_OBJECT="Account", HEADER_MAPPING_PATH=str(mapping_file))

    assert update.load_mapping() == {"id_conta": "Id"}


# ---------- create_job ----------

def test_create_job_update_body(monkeypatch, requests_mock, fake_auth):
    set_config(monkeypatch, SF_OBJECT="Account", SF_OPERATION="update", SF_API_VERSION="v61.0")
    requests_mock.post(
        f"{fake_auth['instance_url']}/services/data/v61.0/jobs/ingest",
        json={"id": "750xx"},
        status_code=200,
    )

    update.create_job(fake_auth)

    body = requests_mock.last_request.json()
    assert body == {"object": "Account", "operation": "update", "lineEnding": "LF"}


def test_create_job_upsert_includes_external_id_field(monkeypatch, requests_mock, fake_auth):
    set_config(
        monkeypatch,
        SF_OBJECT="Account",
        SF_OPERATION="upsert",
        SF_EXTERNAL_ID_FIELD="External_Id__c",
        SF_API_VERSION="v61.0",
    )
    requests_mock.post(
        f"{fake_auth['instance_url']}/services/data/v61.0/jobs/ingest",
        json={"id": "750xx"},
        status_code=200,
    )

    update.create_job(fake_auth)

    body = requests_mock.last_request.json()
    assert body["externalIdFieldName"] == "External_Id__c"


def test_create_job_failure_raises(monkeypatch, requests_mock, fake_auth):
    set_config(monkeypatch, SF_OBJECT="Account", SF_OPERATION="update", SF_API_VERSION="v61.0")
    requests_mock.post(
        f"{fake_auth['instance_url']}/services/data/v61.0/jobs/ingest",
        json={"message": "INVALID_OPERATION"},
        status_code=400,
    )

    with pytest.raises(update.BulkApiError, match="400"):
        update.create_job(fake_auth)


# ---------- wait_for_completion ----------

def test_wait_for_completion_success(monkeypatch, requests_mock, fake_auth):
    set_config(monkeypatch, SF_OBJECT="Account", SF_API_VERSION="v61.0")
    requests_mock.get(
        f"{fake_auth['instance_url']}/services/data/v61.0/jobs/ingest/750xx",
        json={"state": "JobComplete", "numberRecordsProcessed": 10, "numberRecordsFailed": 0},
        status_code=200,
    )

    result = update.wait_for_completion(fake_auth, "750xx")
    assert result["state"] == "JobComplete"


def test_wait_for_completion_aborted_raises(monkeypatch, requests_mock, fake_auth):
    set_config(monkeypatch, SF_OBJECT="Account", SF_API_VERSION="v61.0")
    requests_mock.get(
        f"{fake_auth['instance_url']}/services/data/v61.0/jobs/ingest/750xx",
        json={"state": "Aborted"},
        status_code=200,
    )

    with pytest.raises(update.BulkApiError, match="Aborted"):
        update.wait_for_completion(fake_auth, "750xx")
