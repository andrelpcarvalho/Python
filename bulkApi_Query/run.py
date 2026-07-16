"""
run.py

Orquestra o fluxo completo: pergunta a configuracao da query
(config.py) e, em seguida, ja executa o bulk_query.py com o .env
recem-atualizado. Um comando só, do "o que eu quero consultar"
ate o CSV pronto.

── USO ─────────────────────────────────────────────────────────
python run.py
"""

import sys

import config
import bulk_query


def main():
    print("== Passo 1/2: configurar a query ==\n")
    config.main()

    print("\n== Passo 2/2: executando a query na Bulk API 2.0 ==\n")
    bulk_query.reload_config()  # relê o .env que o config.py acabou de escrever
    bulk_query.main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado pelo usuário.")
        sys.exit(1)