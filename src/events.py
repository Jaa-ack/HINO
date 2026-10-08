"""Lossless event long table, including unrecognized event subfields."""
import json
import re

import numpy as np
import pandas as pd

from src.clean import make_trip_id
from src.utils import json_safe

EVENT_NAMES = {1: "driving", 2: "idle", 3: "parked", 4: "engineOn", 5: "fence", 6: "accelerate",
               7: "decelerate", 8: "speeding", 9: "dtc", 10: "engineOverheat", 11: "engineOverloading",
               12: "fatigue", 13: "seatbelt", 14: "phone", 15: "smoking", 16: "distract", 17: "lensWardOff",
               18: "driverLost", 19: "pcs", 20: "ldws"}


def normalize_events(raw):
    indices = sorted({int(m.group(1)) for col in raw for m in [re.match(r"event\[(\d+)\]", col)] if m})
    pieces = []
    for i in indices:
        prefix = f"event[{i}]."
        columns = [c for c in raw if c.startswith(prefix) or c == f"event[{i}]"]
        subset = raw.loc[raw[columns].replace(r"^\s*$", pd.NA, regex=True).notna().any(axis=1)]
        if subset.empty:
            continue
        long = pd.DataFrame(index=subset.index)
        for c in ["enabledCode", "journeyCode", "source_row"]:
            long[c] = subset[c] if c in subset else pd.NA
        long["timestamp"] = pd.to_datetime(subset.get("time"), format="mixed", errors="coerce")
        for target, source in [("longitude", "gps.longitude"), ("latitude", "gps.latitude"), ("speed", "gps.speed")]:
            long[target] = pd.to_numeric(subset[source], errors="coerce") if source in subset else np.nan
        long["event_index"] = i
        for c in columns:
            long[c.removeprefix(prefix)] = subset[c].astype("string")
        long["event_type"] = pd.to_numeric(long.get("type"), errors="coerce")
        long["event_name"] = long.event_type.map(EVENT_NAMES).fillna("unknown")
        long["raw_payload_json"] = [json.dumps(json_safe(r), ensure_ascii=False, sort_keys=True) for r in subset[columns].to_dict("records")]
        long["event_value"] = long.raw_payload_json
        pieces.append(long)
    base_columns = ["trip_id", "enabledCode", "journeyCode", "timestamp", "event_index", "event_type", "event_name",
                    "event_value", "raw_payload_json", "source_row", "longitude", "latitude", "speed", "event_identity"]
    if not pieces:
        return pd.DataFrame(columns=base_columns)
    result = pd.concat(pieces, ignore_index=True)
    result["trip_id"] = [make_trip_id(v, j) if pd.notna(v) and pd.notna(j) else None for v, j in zip(result.enabledCode, result.journeyCode)]
    start = pd.to_datetime(result.get("startTime", pd.Series(index=result.index, dtype="str")), format="mixed", errors="coerce").fillna(result.timestamp)
    # Repeated start/end reports of one event count once; all original records remain above.
    result["event_identity"] = result.trip_id.astype(str) + "|" + result.event_type.astype(str) + "|" + start.astype(str)
    return result
