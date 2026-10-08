from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DISCLAIMER = "歷史觀測比較與啟發式篩選；非因果證明，燃油差距不等於可實現節省，成效需 Pilot 驗證"


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [json_safe(v) for v in value]
    if isinstance(value, (pd.Timestamp,)):
        return None if pd.isna(value) else value.isoformat()
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(value), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def write_processed_parquet(frame, path):
    """Stamp processed Parquet schemas with the build's interpretation contract."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    from src.config import ANALYSIS_VERSION, SOURCE_CONTRACT_VERSION, EVENT_REFERENCE_VERSION
    table = pa.Table.from_pandas(frame, preserve_index=False)
    metadata = dict(table.schema.metadata or {})
    metadata.update({b'analysis_version': ANALYSIS_VERSION.encode(),
                     b'source_contract_version': SOURCE_CONTRACT_VERSION.encode(),
                     b'event_reference_version': EVENT_REFERENCE_VERSION.encode()})
    pq.write_table(table.replace_schema_metadata(metadata), path)


def markdown_table(rows, columns):
    def cell(v):
        return str(v).replace("|", "\\|").replace("\n", " / ")
    return "\n".join(["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"] +
                     ["| " + " | ".join(cell(r.get(c, "")) for c in columns) + " |" for r in rows])


def stable_int(value):
    return int(hashlib.sha256(str(value).encode()).hexdigest()[:16], 16)
