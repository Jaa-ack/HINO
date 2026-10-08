import hashlib

import openpyxl
import pandas as pd

from src.ingest import inspect_workbook


def test_inspection_profiles_all_rows_and_retains_unknown_fields(tmp_path):
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "output"
    sheet.append(["enabledCode", "journeyCode", "time", "mystery", "event[0].type"])
    sheet.append(["A", "0001", "2025-01-01 00:00:00", 9, 6])
    sheet.append(["B", "0001", "2025-01-01 00:01:00", None, None])
    path = tmp_path / "source.xlsx"
    book.save(path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    result = inspect_workbook(path, tmp_path / "out", chunk_size=1)
    assert result["row_count"] == 2
    assert result["trip_count"] == 2
    assert result["columns"]["mystery"]["missing_pct"] == 50
    assert result["columns"]["mystery"]["unit"] == "UNKNOWN"
    raw = pd.read_parquet(tmp_path / "out/data/interim/raw_snapshot.parquet")
    assert raw["journeyCode"].tolist() == ["0001", "0001"]
    assert raw["mystery"].iloc[0] == "9"
    assert (tmp_path / "out/docs/data_profile.md").exists()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
