import json

import pytest

import field_mapping


# ---------- get_first_csv_header ----------

def test_get_first_csv_header_reads_first_file(tmp_path):
    (tmp_path / "01_dados.csv").write_text("Id,Name\n001,Acme\n")
    (tmp_path / "02_dados.csv").write_text("Id,Name\n002,Globex\n")

    header, sample_file = field_mapping.get_first_csv_header(str(tmp_path))

    assert header == ["Id", "Name"]
    assert sample_file.endswith("01_dados.csv")


def test_get_first_csv_header_no_files_raises(tmp_path):
    with pytest.raises(SystemExit):
        field_mapping.get_first_csv_header(str(tmp_path))


# ---------- describe_object ----------

def test_describe_object_success(requests_mock, fake_auth):
    requests_mock.get(
        f"{fake_auth['instance_url']}/services/data/v61.0/sobjects/Account/describe",
        json={"fields": [{"name": "Id", "label": "Account ID"}, {"name": "Name", "label": "Account Name"}]},
        status_code=200,
    )

    fields = field_mapping.describe_object(fake_auth, "Account", "v61.0")

    assert {f["name"] for f in fields} == {"Id", "Name"}


def test_describe_object_failure_raises(requests_mock, fake_auth):
    requests_mock.get(
        f"{fake_auth['instance_url']}/services/data/v61.0/sobjects/Invalid__c/describe",
        json={"message": "not found"},
        status_code=404,
    )

    with pytest.raises(SystemExit):
        field_mapping.describe_object(fake_auth, "Invalid__c", "v61.0")


# ---------- suggest_field ----------

FIELDS = [
    {"name": "Id", "label": "Account ID"},
    {"name": "Name", "label": "Account Name"},
    {"name": "BillingCity", "label": "Billing City"},
]


def test_suggest_field_exact_name_match():
    assert field_mapping.suggest_field("Name", FIELDS) == "Name"


def test_suggest_field_case_insensitive_match():
    assert field_mapping.suggest_field("name", FIELDS) == "Name"


def test_suggest_field_label_match_ignoring_spaces():
    assert field_mapping.suggest_field("Billing City", FIELDS) == "BillingCity"


def test_suggest_field_underscore_normalized_match():
    assert field_mapping.suggest_field("billing_city", FIELDS) == "BillingCity"


def test_suggest_field_fuzzy_match():
    # "Nmae" é um typo perto o suficiente de "Name" pra bater no fuzzy match
    assert field_mapping.suggest_field("Nmae", FIELDS) == "Name"


def test_suggest_field_no_match_returns_none():
    assert field_mapping.suggest_field("Totally_Unrelated_Column_Xyz", FIELDS) is None


# ---------- main (fluxo interativo completo, com input/rede mockados) ----------

def test_main_end_to_end_with_scripted_answers(tmp_path, monkeypatch, requests_mock, fake_auth):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "csv").mkdir()
    (tmp_path / "csv" / "01_dados.csv").write_text("id_conta,nome_completo\n001,Acme\n")

    monkeypatch.setenv("CSV_DIR", "csv")
    monkeypatch.setenv("SF_OBJECT", "Account")
    monkeypatch.setenv("SF_API_VERSION", "v61.0")
    monkeypatch.setenv("SF_CLIENT_ID", "cid")
    monkeypatch.setenv("SF_CLIENT_SECRET", "cs")
    monkeypatch.setenv("SF_LOGIN_URL", fake_auth["instance_url"])

    requests_mock.post(
        f"{fake_auth['instance_url']}/services/oauth2/token",
        json=fake_auth,
        status_code=200,
    )
    requests_mock.get(
        f"{fake_auth['instance_url']}/services/data/v61.0/sobjects/Account/describe",
        json={"fields": [{"name": "Id", "label": "Account ID"}, {"name": "Name", "label": "Account Name"}]},
        status_code=200,
    )

    # Nenhuma das duas colunas bate automaticamente (nem por nome, label ou
    # fuzzy match) -> respondemos as duas diretamente com o campo certo.
    answers = iter(["Id", "Name"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    field_mapping.main()

    saved = json.loads((tmp_path / "header_mapping.json").read_text())
    assert saved == {"id_conta": "Id", "nome_completo": "Name"}
