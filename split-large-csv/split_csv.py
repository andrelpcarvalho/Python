"""
split_csv.py

Divide um CSV grande em N arquivos menores, com no máximo MAX_ROWS
linhas cada (fora o header, que é repetido em todos os arquivos).

O encoding do arquivo de origem é detectado automaticamente (via
charset-normalizer), então funciona tanto com CSVs em UTF-8 quanto
com os exportados em Latin-1/Windows-1252 (comum em planilhas Excel
salvas no Brasil). O arquivo de SAÍDA é sempre gravado em UTF-8,
que é o encoding exigido pela Bulk API 2.0 do Salesforce.

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

from charset_normalizer import from_bytes
from dotenv import load_dotenv

load_dotenv()

INPUT_FILE = os.environ.get("INPUT_FILE", "seu_arquivo.csv")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./csv")
OUTPUT_PREFIX = os.environ.get("OUTPUT_PREFIX", "parte")
MAX_ROWS = int(os.environ.get("MAX_ROWS", "1000000"))

csv.field_size_limit(sys.maxsize)  # evita erro com campos grandes (long text, rich text)

DEFAULT_ENCODING_FALLBACK = "utf-8-sig"
DETECTION_SAMPLE_BYTES = 1_000_000  # 1MB é suficiente pra detectar; evita ler o arquivo inteiro


def detect_encoding(path, sample_size=DETECTION_SAMPLE_BYTES):
    """Detecta o encoding real do arquivo lendo uma amostra dos primeiros
    bytes (não o arquivo inteiro — importante pra CSVs de vários GB).

    Restringe os candidatos a UTF-8, Windows-1252 e Latin-1 (ISO-8859-1) —
    são praticamente os únicos encodings realistas pra CSV exportado de
    planilha/sistema no Brasil. Sem essa restrição, o charset-normalizer
    pode confundir CP1252 com codepages parecidas porém erradas (ex:
    CP1250, usado na Europa Central), trocando acentuação silenciosamente
    e sem erro nenhum — pior que simplesmente falhar.

    Cai para utf-8-sig se a detecção não conseguir decidir.
    """
    with open(path, "rb") as f:
        raw_sample = f.read(sample_size)

    if not raw_sample:
        return DEFAULT_ENCODING_FALLBACK

    result = from_bytes(raw_sample, cp_isolation=["utf_8", "cp1252", "iso-8859-1"]).best()
    if result is None:
        return DEFAULT_ENCODING_FALLBACK

    encoding = str(result.encoding)

    # utf_8 "puro" não remove BOM automaticamente — se o arquivo tem BOM,
    # precisamos do utf-8-sig pra não vazar \ufeff no nome da 1ª coluna
    # (isso quebraria silenciosamente o casamento de campo "Id" no Salesforce).
    if encoding in ("utf_8", "utf-8") and raw_sample.startswith(b"\xef\xbb\xbf"):
        encoding = "utf-8-sig"

    return encoding


def split_csv(input_file, output_dir, output_prefix, max_rows):
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    encoding = detect_encoding(input_file)
    print(f"Encoding detectado em {input_file}: {encoding}")

    with open(input_file, "r", newline="", encoding=encoding, errors="strict") as infile:
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
        print(f"Concluído: {file_index} arquivos gerados em {output_dir}/ (saída em UTF-8)")


if __name__ == "__main__":
    if not os.path.exists(INPUT_FILE):
        print(f"ERRO: INPUT_FILE não encontrado: {INPUT_FILE}")
        sys.exit(1)
    try:
        split_csv(INPUT_FILE, OUTPUT_DIR, OUTPUT_PREFIX, MAX_ROWS)
    except UnicodeDecodeError as exc:
        print(
            "ERRO: mesmo com detecção automática, não foi possível decodificar o arquivo.\n"
            f"Detalhe: {exc}\n"
            "O arquivo pode ter encoding misto (partes em codificações diferentes) — "
            "nesse caso, considere reabrir e resalvar o CSV como UTF-8 numa ferramenta "
            "como o Excel/LibreOffice antes de rodar o split."
        )
        sys.exit(1)