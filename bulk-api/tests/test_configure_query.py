import configure_query as cq


# ---------- read_env / write_env / escape / unquote ----------

def test_write_then_read_env_roundtrip(tmp_path):
    path = str(tmp_path / ".env")
    cq.write_env(path, {"SF_OBJECT": "Account", "SF_WHERE": "Name = 'Acme'"})

    values = cq.read_env(path)

    assert values == {"SF_OBJECT": "Account", "SF_WHERE": "Name = 'Acme'"}


def test_read_env_missing_file_returns_empty_dict(tmp_path):
    assert cq.read_env(str(tmp_path / "nao_existe.env")) == {}


def test_read_env_ignores_comments_and_blank_lines(tmp_path):
    path = tmp_path / ".env"
    path.write_text('# comentário\n\nSF_OBJECT="Account"\n')

    assert cq.read_env(str(path)) == {"SF_OBJECT": "Account"}


def test_write_env_preserves_existing_keys_not_touched(tmp_path):
    path = str(tmp_path / ".env")
    cq.write_env(path, {"SF_CLIENT_ID": "abc", "SF_OBJECT": "Account"})

    values = cq.read_env(path)
    values["SF_OBJECT"] = "Contact"  # simula o config.py atualizando só um campo
    cq.write_env(path, values)

    final = cq.read_env(path)
    assert final == {"SF_CLIENT_ID": "abc", "SF_OBJECT": "Contact"}


def test_write_env_escapes_double_quotes(tmp_path):
    path = str(tmp_path / ".env")
    cq.write_env(path, {"SF_WHERE": 'Name = "Acme"'})

    raw = open(path).read()
    assert raw == 'SF_WHERE="Name = \\"Acme\\""\n'

    assert cq.read_env(path) == {"SF_WHERE": 'Name = "Acme"'}


# ---------- ask / ask_choice / ask_int ----------

def test_ask_returns_answer_when_given(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "Account")
    assert cq.ask("Objeto") == "Account"


def test_ask_returns_current_when_blank(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "")
    assert cq.ask("Objeto", current="Contact") == "Contact"


def test_ask_yes_no_blank_returns_default_true(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "")
    assert cq.ask_yes_no("Usar WHERE?", default=True) is True


def test_ask_yes_no_blank_returns_default_false(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "")
    assert cq.ask_yes_no("Usar WHERE?", default=False) is False


def test_ask_yes_no_accepts_s(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "s")
    assert cq.ask_yes_no("Usar WHERE?", default=False) is True


def test_ask_yes_no_accepts_n(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "n")
    assert cq.ask_yes_no("Usar WHERE?", default=True) is False


def test_ask_int_accepts_digits(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "1000")
    assert cq.ask_int("Limit") == "1000"


def test_ask_int_rejects_non_digit_then_accepts(monkeypatch):
    answers = iter(["abc", "500"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    assert cq.ask_int("Limit") == "500"


def test_ask_int_blank_keeps_current(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "")
    assert cq.ask_int("Limit", current="200") == "200"


# ---------- main (fluxo completo) ----------

def test_main_writes_all_query_fields_to_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    answers = iter([
        "Account",              # objeto
        "Id,Name",              # campos
        "s",                    # usar WHERE?
        "Name != null",         # WHERE
        "s",                    # usar ORDER BY?
        "CreatedDate DESC",     # ORDER BY
        "s",                    # usar LIMIT?
        "500",                  # LIMIT
        "./output/contas.csv",  # output path
    ])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    cq.main()

    values = cq.read_env(".env")
    assert values["SF_OBJECT"] == "Account"
    assert values["SF_FIELDS"] == "Id,Name"
    assert values["SF_WHERE"] == "Name != null"
    assert values["SF_ORDER_BY"] == "CreatedDate DESC"
    assert values["SF_LIMIT"] == "500"
    assert values["SF_OUTPUT_PATH"] == "./output/contas.csv"


def test_main_skips_optional_clauses_when_answered_no(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    answers = iter([
        "Contact",   # objeto
        "Id",        # campos
        "n",         # WHERE? não
        "n",         # ORDER BY? não
        "n",         # LIMIT? não
        "",          # output path (mantém default)
    ])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    cq.main()

    values = cq.read_env(".env")
    assert values["SF_WHERE"] == ""
    assert values["SF_ORDER_BY"] == ""
    assert values["SF_LIMIT"] == ""


def test_main_preserves_credentials_already_in_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cq.write_env(".env", {"SF_CLIENT_ID": "existing-id", "SF_CLIENT_SECRET": "existing-secret"})

    answers = iter(["Account", "Id", "n", "n", "n", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    cq.main()

    values = cq.read_env(".env")
    assert values["SF_CLIENT_ID"] == "existing-id"
    assert values["SF_CLIENT_SECRET"] == "existing-secret"
    assert values["SF_OBJECT"] == "Account"
