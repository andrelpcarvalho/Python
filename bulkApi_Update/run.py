"""
run.py

Orquestra o fluxo completo do bulkApi:
  1. config.py       -> pergunta objeto, operação, external ID field, CSV_DIR
  2. field_mapping.py -> opcional, só se as colunas do CSV não baterem com a API
  3. bulk_update.py   -> executa o update/insert/upsert/delete em massa

Um comando só, do "o que eu quero fazer" até os 23 arquivos processados.

── USO ─────────────────────────────────────────────────────────
python run.py
"""

import sys

import config
import field_mapping
import bulk_update


def ask_yes_no(label: str, default: bool = False) -> bool:
    suffix = " [S/n]" if default else " [s/N]"
    answer = input(f"{label}{suffix}: ").strip().lower()
    if not answer:
        return default
    return answer in ("s", "sim", "y", "yes")


def main():
    print("== Passo 1/3: configurar objeto e operação ==\n")
    config.main()

    print("\n== Passo 2/3: mapeamento de colunas ==")
    precisa_mapear = ask_yes_no(
        "As colunas do CSV batem exatamente com os nomes de campo da API?", default=True
    )
    if not precisa_mapear:
        print()
        field_mapping.main()
    else:
        print("Pulando mapeamento — CSV será enviado com as colunas originais.")

    print("\n== Passo 3/3: executando o bulk update ==\n")
    bulk_update.reload_config()  # relê o .env que o config.py acabou de escrever
    bulk_update.main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado pelo usuário.")
        sys.exit(1)