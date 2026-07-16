"""
run_query.py

Orquestra o fluxo de query:
  1. configure_query.py -> pergunta objeto, campos, WHERE, ORDER BY, LIMIT, output
  2. query.py             -> executa a query na Bulk API 2.0

── USO ─────────────────────────────────────────────────────────
python run_query.py
"""

import sys

import configure_query as config
import query as bulk_query


def main():
    print("== Passo 1/2: configurar a query ==\n")
    config.main()

    print("\n== Passo 2/2: executando a query na Bulk API 2.0 ==\n")
    bulk_query.reload_config()  # relê o .env que o configure_query.py acabou de escrever
    bulk_query.main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado pelo usuário.")
        sys.exit(1)
