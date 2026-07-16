"""
config.py

Roda ANTES do bulk_update.py. Pergunta no terminal qual objeto,
operação, external ID field (se upsert) e diretório de CSVs usar,
e grava essas respostas no .env — sem apagar as outras variáveis
que já estiverem lá (SF_CLIENT_ID, SF_CLIENT_SECRET, SF_LOGIN_URL etc).

── USO ─────────────────────────────────────────────────────────
python config.py
"""

import os

ENV_PATH = ".env"
VALID_OPERATIONS = ("insert", "update", "upsert", "delete")


def read_env(path: str) -> dict:
    values = {}
    if os.path.exists(path):
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                values[key.strip()] = _unquote(value.strip())
    return values


def write_env(path: str, values: dict) -> None:
    with open(path, "w") as f:
        for key, value in values.items():
            f.write(f'{key}="{_escape(value)}"\n')


def _escape(value: str) -> str:
    return value.replace('"', '\\"')


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1].replace('\\"', '"')
    return value


def ask(label: str, current: str = "") -> str:
    suffix = f" [{current}]" if current else ""
    answer = input(f"{label}{suffix}: ").strip()
    return answer if answer else current


def ask_choice(label: str, options: tuple, current: str = "") -> str:
    default = current if current in options else options[0]
    while True:
        answer = ask(f"{label} ({'/'.join(options)})", default)
        if answer in options:
            return answer
        print(f"  -> escolha um de: {', '.join(options)}")


def main():
    values = read_env(ENV_PATH)

    print("== Configuração do bulk update (Bulk API 2.0) ==")
    print("Enter em branco mantém o valor atual (entre colchetes).\n")

    obj = ask("Objeto alvo (ex: Account, Contact, Custom_Object__c)", values.get("SF_OBJECT", ""))
    operation = ask_choice("Operação", VALID_OPERATIONS, values.get("SF_OPERATION", "update"))

    external_id_field = values.get("SF_EXTERNAL_ID_FIELD", "")
    if operation == "upsert":
        external_id_field = ask("Campo de External ID (ex: External_Id__c)", external_id_field)
    else:
        external_id_field = ""

    csv_dir = ask("Diretório com os CSVs", values.get("CSV_DIR", "./csv"))

    values["SF_OBJECT"] = obj
    values["SF_OPERATION"] = operation
    values["SF_EXTERNAL_ID_FIELD"] = external_id_field
    values["CSV_DIR"] = csv_dir
    values.setdefault("HEADER_MAPPING_PATH", "header_mapping.json")

    write_env(ENV_PATH, values)

    print(f"\n.env atualizado em: {os.path.abspath(ENV_PATH)}")
    print(f"  SF_OBJECT={obj}")
    print(f"  SF_OPERATION={operation}")
    print(f"  SF_EXTERNAL_ID_FIELD={external_id_field}")
    print(f"  CSV_DIR={csv_dir}")


if __name__ == "__main__":
    main()