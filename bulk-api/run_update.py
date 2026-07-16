"""
run_update.py

Orquestra o fluxo de update/insert/upsert/delete:
  1. configure_update.py -> pergunta objeto, operação, external ID field, CSV_DIR
  2. field_mapping.py    -> opcional, só se as colunas do CSV não baterem com a API
  3. update.py            -> executa o job em massa

── USO ─────────────────────────────────────────────────────────
python run_update.py
"""

import sys

import configure_update as config
import field_mapping
import update as bulk_update


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
    ja_bate = ask_yes_no("As colunas do CSV batem exatamente com os nomes de campo da API?", default=True)
    if not ja_bate:
        print()
        field_mapping.main()
    else:
        print("Pulando mapeamento — CSV será enviado com as colunas originais.")

    print("\n== Passo 3/3: executando o job em massa ==\n")
    bulk_update.reload_config()  # relê o .env que o configure_update.py acabou de escrever
    bulk_update.main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado pelo usuário.")
        sys.exit(1)
