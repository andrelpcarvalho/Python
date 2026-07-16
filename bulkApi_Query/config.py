"""
config.py

Roda ANTES do bulk_query_account.py. Pergunta no terminal quais
sao o objeto, os campos e o output path da query, e grava essas
respostas no .env — sem apagar as outras variaveis que ja
estiverem la (SF_CLIENT_ID, SF_CLIENT_SECRET, SF_LOGIN_URL etc).

── USO ──────────────────────────────────────────────────────────
python config.py
"""

import os
import logging

log = logging.getLogger(__name__)

ENV_PATH = ".env"


def _ler_env(path: str) -> dict:
    """Le o .env existente (se houver) pra um dict, preservando ordem."""
    valores = {}
    if os.path.exists(path):
        with open(path, "r") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                chave, _, valor = linha.partition("=")
                valores[chave.strip()] = valor.strip()
    return valores


def _escrever_env(path: str, valores: dict) -> None:
    with open(path, "w") as f:
        for chave, valor in valores.items():
            f.write(f"{chave}={valor}\n")


def _perguntar(label: str, atual: str = "") -> str:
    sufixo = f" [{atual}]" if atual else ""
    resposta = input(f"{label}{sufixo}: ").strip()
    return resposta if resposta else atual


def main():
    valores = _ler_env(ENV_PATH)

    print("== Configuracao da query (Bulk API 2.0) ==")
    print("Enter em branco mantem o valor atual (entre colchetes).\n")

    objeto = _perguntar("Objeto (ex: Account)", valores.get("SF_OBJECT", "Account"))

    campos_atual = valores.get("SF_FIELDS", "Id,Name")
    campos = _perguntar("Campos, separados por virgula (ex: Id,Name)", campos_atual)

    output_atual = valores.get("SF_OUTPUT_PATH", "resultado.csv")
    output_path = _perguntar("Output path (ex: resultado.csv)", output_atual)

    valores["SF_OBJECT"] = objeto
    valores["SF_FIELDS"] = campos
    valores["SF_OUTPUT_PATH"] = output_path

    _escrever_env(ENV_PATH, valores)
    print(f"\n.env atualizado em: {os.path.abspath(ENV_PATH)}")
    print(f"  SF_OBJECT={objeto}")
    print(f"  SF_FIELDS={campos}")
    print(f"  SF_OUTPUT_PATH={output_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    main()