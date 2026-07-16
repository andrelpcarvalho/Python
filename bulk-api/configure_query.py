"""
configure_query.py

Roda ANTES do query.py. Pergunta no terminal quais sao o
objeto, os campos, o WHERE e o output path da query, e grava essas
respostas no .env — sem apagar as outras variaveis que ja
estiverem la (SF_CLIENT_ID, SF_CLIENT_SECRET, SF_LOGIN_URL etc).

Util pra rodar queries diferentes sem editar o .env na mao toda vez.

── USO ─────────────────────────────────────────────────────────
python configure_query.py
python query.py
"""

import os

ENV_PATH = ".env"


def read_env(path: str) -> dict:
    """Le o .env existente (se houver) pra um dict, preservando ordem."""
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


def ask_yes_no(label: str, default: bool = False) -> bool:
    suffix = " [S/n]" if default else " [s/N]"
    answer = input(f"{label}{suffix}: ").strip().lower()
    if not answer:
        return default
    return answer in ("s", "sim", "y", "yes")


def ask_int(label: str, current: str = "") -> str:
    suffix = f" [{current}]" if current else ""
    while True:
        answer = input(f"{label}{suffix}: ").strip()
        if not answer:
            return current
        if answer.isdigit():
            return answer
        print("  -> precisa ser um número inteiro. Tente de novo.")


def main():
    values = read_env(ENV_PATH)

    print("== Configuração da query (Bulk API 2.0) ==")
    print("Enter em branco mantém o valor atual (entre colchetes).\n")

    obj = ask("Objeto (ex: Account)", values.get("SF_OBJECT", "Account"))
    fields = ask("Campos, separados por vírgula (ex: Id,Name)", values.get("SF_FIELDS", "Id,Name"))

    where_atual = values.get("SF_WHERE", "")
    usar_where = ask_yes_no("Usar cláusula WHERE?", default=bool(where_atual))
    where = ask("Cláusula WHERE, sem o 'WHERE' (ex: Name = 'John Doe')", where_atual) if usar_where else ""

    order_by_atual = values.get("SF_ORDER_BY", "")
    usar_order_by = ask_yes_no("Usar ORDER BY?", default=bool(order_by_atual))
    order_by = ask("Campo(s) do ORDER BY (ex: CreatedDate DESC)", order_by_atual) if usar_order_by else ""

    limit_atual = values.get("SF_LIMIT", "")
    usar_limit = ask_yes_no("Usar LIMIT?", default=bool(limit_atual))
    limit = ask_int("Valor do LIMIT (ex: 1000)", limit_atual) if usar_limit else ""

    output_path = ask("Output path (ex: ./output/resultado.csv)", values.get("SF_OUTPUT_PATH", "./output/resultado.csv"))

    values["SF_OBJECT"] = obj
    values["SF_FIELDS"] = fields
    values["SF_WHERE"] = where
    values["SF_ORDER_BY"] = order_by
    values["SF_LIMIT"] = limit
    values["SF_OUTPUT_PATH"] = output_path

    write_env(ENV_PATH, values)

    print(f"\n.env atualizado em: {os.path.abspath(ENV_PATH)}")
    print(f"  SF_OBJECT={obj}")
    print(f"  SF_FIELDS={fields}")
    print(f"  SF_WHERE={where}")
    print(f"  SF_ORDER_BY={order_by}")
    print(f"  SF_LIMIT={limit}")
    print(f"  SF_OUTPUT_PATH={output_path}")


if __name__ == "__main__":
    main()
