import csv

from split_csv import split_csv


def _write_input_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def test_split_csv_single_file_when_under_max_rows(tmp_path):
    input_file = tmp_path / "input.csv"
    _write_input_csv(input_file, ["Id", "Name"], [["001", "Acme"], ["002", "Globex"]])

    output_dir = tmp_path / "out"
    split_csv(str(input_file), str(output_dir), "parte", max_rows=10)

    files = sorted(output_dir.glob("*.csv"))
    assert len(files) == 1
    assert files[0].name == "parte_1.csv"

    with open(files[0], newline="") as f:
        rows = list(csv.reader(f))
    assert rows == [["Id", "Name"], ["001", "Acme"], ["002", "Globex"]]


def test_split_csv_splits_into_multiple_files(tmp_path):
    input_file = tmp_path / "input.csv"
    rows = [[str(i), f"Nome {i}"] for i in range(10)]
    _write_input_csv(input_file, ["Id", "Name"], rows)

    output_dir = tmp_path / "out"
    split_csv(str(input_file), str(output_dir), "parte", max_rows=3)

    files = sorted(output_dir.glob("*.csv"), key=lambda p: int(p.stem.split("_")[-1]))
    assert [f.name for f in files] == ["parte_1.csv", "parte_2.csv", "parte_3.csv", "parte_4.csv"]

    # 3 arquivos com 3 linhas de dados + 1 com a linha restante (10 = 3+3+3+1)
    row_counts = []
    for f in files:
        with open(f, newline="") as fh:
            rows_in_file = list(csv.reader(fh))
        row_counts.append(len(rows_in_file) - 1)  # descontando o header
    assert row_counts == [3, 3, 3, 1]


def test_split_csv_repeats_header_in_every_file(tmp_path):
    input_file = tmp_path / "input.csv"
    rows = [[str(i), f"Nome {i}"] for i in range(5)]
    _write_input_csv(input_file, ["Id", "Name"], rows)

    output_dir = tmp_path / "out"
    split_csv(str(input_file), str(output_dir), "parte", max_rows=2)

    for f in output_dir.glob("*.csv"):
        with open(f, newline="") as fh:
            first_row = next(csv.reader(fh))
        assert first_row == ["Id", "Name"]


def test_split_csv_preserves_total_row_count(tmp_path):
    input_file = tmp_path / "input.csv"
    rows = [[str(i), f"Nome {i}"] for i in range(97)]
    _write_input_csv(input_file, ["Id", "Name"], rows)

    output_dir = tmp_path / "out"
    split_csv(str(input_file), str(output_dir), "parte", max_rows=10)

    total_data_rows = 0
    for f in output_dir.glob("*.csv"):
        with open(f, newline="") as fh:
            total_data_rows += len(list(csv.reader(fh))) - 1
    assert total_data_rows == 97


def test_split_csv_creates_output_dir_if_missing(tmp_path):
    input_file = tmp_path / "input.csv"
    _write_input_csv(input_file, ["Id"], [["001"]])

    output_dir = tmp_path / "nested" / "out"  # não existe ainda
    split_csv(str(input_file), str(output_dir), "parte", max_rows=10)

    assert output_dir.exists()
    assert (output_dir / "parte_1.csv").exists()


def test_split_csv_uses_given_prefix(tmp_path):
    input_file = tmp_path / "input.csv"
    _write_input_csv(input_file, ["Id"], [["001"]])

    output_dir = tmp_path / "out"
    split_csv(str(input_file), str(output_dir), "contas_2024", max_rows=10)

    assert (output_dir / "contas_2024_1.csv").exists()


# ---------- detecção automática de encoding ----------

from split_csv import detect_encoding


def test_detect_encoding_utf8_without_bom(tmp_path):
    input_file = tmp_path / "input.csv"
    input_file.write_bytes("Id,Nome\n001,João\n".encode("utf-8"))

    assert detect_encoding(str(input_file)) in ("utf_8", "utf-8")


def test_detect_encoding_utf8_with_bom_returns_utf8_sig(tmp_path):
    input_file = tmp_path / "input.csv"
    input_file.write_bytes("Id,Nome\n001,João\n".encode("utf-8-sig"))

    assert detect_encoding(str(input_file)) == "utf-8-sig"


def test_detect_encoding_cp1252(tmp_path):
    input_file = tmp_path / "input.csv"
    input_file.write_bytes("Id,Nome\n001,João da Silva\n002,Conceição Araújo\n003,José Ánderson\n".encode("cp1252"))

    assert detect_encoding(str(input_file)) == "cp1252"


def test_detect_encoding_empty_file_falls_back(tmp_path):
    input_file = tmp_path / "input.csv"
    input_file.write_bytes(b"")

    assert detect_encoding(str(input_file)) == "utf-8-sig"


def test_split_csv_handles_cp1252_input_without_corrupting_accents(tmp_path):
    input_file = tmp_path / "input.csv"
    input_file.write_bytes(
        "Id,Nome\n001,João da Silva\n002,Conceição Araújo\n".encode("cp1252")
    )

    output_dir = tmp_path / "out"
    split_csv(str(input_file), str(output_dir), "parte", max_rows=10)

    content = (output_dir / "parte_1.csv").read_text(encoding="utf-8")
    assert "João da Silva" in content
    assert "Conceição Araújo" in content


def test_split_csv_strips_bom_from_first_column_name(tmp_path):
    input_file = tmp_path / "input.csv"
    input_file.write_bytes("Id,Nome\n001,Acme\n".encode("utf-8-sig"))

    output_dir = tmp_path / "out"
    split_csv(str(input_file), str(output_dir), "parte", max_rows=10)

    first_line = (output_dir / "parte_1.csv").read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "Id,Nome"
    assert "\ufeff" not in first_line