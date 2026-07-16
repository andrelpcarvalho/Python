import configure_update as cu


# ---------- read_env / write_env (mesma lógica de configure_query.py) ----------

def test_write_then_read_env_roundtrip(tmp_path):
    path = str(tmp_path / ".env")
    cu.write_env(path, {"SF_OBJECT": "Account", "SF_OPERATION": "update"})

    assert cu.read_env(path) == {"SF_OBJECT": "Account", "SF_OPERATION": "update"}


# ---------- ask_choice ----------

def test_ask_choice_returns_default_on_blank(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "")
    assert cu.ask_choice("Operação", cu.VALID_OPERATIONS, current="upsert") == "upsert"


def test_ask_choice_falls_back_to_first_option_if_current_invalid(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "")
    assert cu.ask_choice("Operação", cu.VALID_OPERATIONS, current="patch") == cu.VALID_OPERATIONS[0]


def test_ask_choice_rejects_invalid_then_accepts_valid(monkeypatch):
    answers = iter(["patch", "delete"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    assert cu.ask_choice("Operação", cu.VALID_OPERATIONS) == "delete"


# ---------- main (fluxo completo) ----------

def test_main_writes_update_fields_to_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    answers = iter([
        "Contact",   # objeto
        "update",    # operação
        "./meus_csvs",  # csv_dir
    ])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    cu.main()

    values = cu.read_env(".env")
    assert values["SF_OBJECT"] == "Contact"
    assert values["SF_OPERATION"] == "update"
    assert values["SF_EXTERNAL_ID_FIELD"] == ""
    assert values["CSV_DIR"] == "./meus_csvs"
    assert values["HEADER_MAPPING_PATH"] == "header_mapping.json"


def test_main_upsert_asks_for_external_id_field(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    answers = iter([
        "Account",
        "upsert",
        "External_Id__c",
        "./csv",
    ])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    cu.main()

    values = cu.read_env(".env")
    assert values["SF_OPERATION"] == "upsert"
    assert values["SF_EXTERNAL_ID_FIELD"] == "External_Id__c"


def test_main_switching_away_from_upsert_clears_external_id_field(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cu.write_env(".env", {"SF_OBJECT": "Account", "SF_OPERATION": "upsert", "SF_EXTERNAL_ID_FIELD": "External_Id__c"})

    answers = iter([
        "",       # objeto -> mantém Account
        "update",  # troca de upsert pra update
        "",        # csv_dir -> mantém default
    ])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    cu.main()

    values = cu.read_env(".env")
    assert values["SF_OPERATION"] == "update"
    assert values["SF_EXTERNAL_ID_FIELD"] == ""


def test_main_preserves_credentials_already_in_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cu.write_env(".env", {"SF_CLIENT_ID": "existing-id"})

    answers = iter(["Account", "update", "./csv"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    cu.main()

    values = cu.read_env(".env")
    assert values["SF_CLIENT_ID"] == "existing-id"
    assert values["SF_OBJECT"] == "Account"
