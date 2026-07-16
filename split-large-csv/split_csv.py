"""
split_csv.py

Divide um CSV grande em N arquivos menores, com no máximo MAX_ROWS
linhas cada (fora o header, que é repetido em todos os arquivos).

── VARIAVEIS DE AMBIENTE (via .env) ────────────────────────────
INPUT_FILE       Caminho do CSV de origem
OUTPUT_DIR       Pasta onde os arquivos divididos serão salvos (ex: ./csv)
OUTPUT_PREFIX    Prefixo dos arquivos gerados (ex: parte -> parte_1.csv, parte_2.csv, ...)
MAX_ROWS         Linhas por arquivo (padrão: 1000000)

── USO ─────────────────────────────────────────────────────────
python split_csv.py
"""

import csv
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

INPUT_FILE = os.environ.get("INPUT_FILE", "seu_arquivo.csv")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./csv")
OUTPUT_PREFIX = os.environ.get("OUTPUT_PREFIX", "parte")
MAX_ROWS = int(os.environ.get("MAX_ROWS", "1000000"))

csv.field_size_limit(sys.maxsize)  # evita erro com campos grandes (long text, rich text)


def split_csv(input_file, output_dir, output_prefix, max_rows):
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    with open(input_file, "r", newline="", encoding="utf-8-sig") as infile:
        reader = csv.reader(infile)
        header = next(reader)
        file_index = 1
        row_count = 0

        def new_outfile(index):
            path = Path(output_dir) / f"{output_prefix}_{index}.csv"
            f = open(path, "w", newline="", encoding="utf-8")
            w = csv.writer(f)
            w.writerow(header)
            return f, w, path

        outfile, writer, current_path = new_outfile(file_index)
        print(f"Escrevendo {current_path}")

        for row in reader:
            if row_count >= max_rows:
                outfile.close()
                file_index += 1
                row_count = 0
                outfile, writer, current_path = new_outfile(file_index)
                print(f"Escrevendo {current_path}")

            writer.writerow(row)
            row_count += 1

        outfile.close()
        print(f"Concluído: {file_index} arquivos gerados em {output_dir}/")


if __name__ == "__main__":
    if not os.path.exists(INPUT_FILE):
        print(f"ERRO: INPUT_FILE não encontrado: {INPUT_FILE}")
        sys.exit(1)
    split_csv(INPUT_FILE, OUTPUT_DIR, OUTPUT_PREFIX, MAX_ROWS)
