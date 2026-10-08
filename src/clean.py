"""Keep original columns; add typed features and explicit quality flags."""
from urllib.parse import quote

import numpy as np
import pandas as pd

ALIASES = {
    "longitude": ["gps.longitude"], "latitude": ["gps.latitude"],
    "gps_speed": ["gps.speed"], "can_speed": ["can.canSpeed", "canSpeed"],
    "mileage": ["can.totalMileage"], "fuel": ["can.engine.totalFuelUsed"],
    "rpm": ["can.engine.rpm", "rpm"], "engine_load": ["can.engine.engineLoad", "engineLoad"],
    "can_status": ["can.canStatus", "canStatus"],
}
GAP_SECONDS = 300


def make_trip_id(vehicle, journey):
    return quote(str(vehicle), safe="") + "::" + quote(str(journey), safe="")


def clean_telemetry(raw, confirmed_units=None):
    df = raw.copy()
    if "source_row" not in df:
        df["source_row"] = np.arange(2, len(df) + 2)
    for key in ["enabledCode", "journeyCode"]:
        if key not in df:
            df[key] = pd.NA
        df[key] = df[key].astype("string").str.strip().replace("", pd.NA)
    df["invalid_key_flag"] = df[["enabledCode", "journeyCode"]].isna().any(axis=1)
    df["trip_id"] = [make_trip_id(v, j) if pd.notna(v) and pd.notna(j) else None
                     for v, j in zip(df.enabledCode, df.journeyCode)]
    df["timestamp"] = pd.to_datetime(df.get("time", pd.Series(index=df.index, dtype="str")), format="mixed", errors="coerce")
    df["invalid_timestamp_flag"] = df.timestamp.isna()
    df["vehicle_type"] = df.get("Type", pd.Series("UNKNOWN", index=df.index)).fillna("UNKNOWN").astype(str)
    for canonical, aliases in ALIASES.items():
        original = next((c for c in aliases if c in raw), None)
        df[canonical] = pd.to_numeric(raw[original], errors="coerce").astype(float) if original else np.nan
    if confirmed_units is not None:
        # A plausible field name is not evidence of its unit. Preserve raw values,
        # but suppress unit-bearing derived meter metrics when unconfirmed.
        for original, canonical, allowed in [("can.totalMileage", "mileage", {"km", "公里"}),
                                              ("can.engine.totalFuelUsed", "fuel", {"l", "公升"})]:
            if str(confirmed_units.get(original, "UNKNOWN")).strip().lower() not in allowed:
                df[canonical] = np.nan
    gps_valid = df.latitude.between(-90, 90) & df.longitude.between(-180, 180) & ~((df.latitude == 0) & (df.longitude == 0))
    df["invalid_gps_flag"] = ~gps_valid
    df.loc[~gps_valid, ["latitude", "longitude"]] = np.nan
    df["invalid_speed_flag"] = ((df.can_speed.notna() & ~df.can_speed.between(0, 160)) |
                                (df.gps_speed.notna() & ~df.gps_speed.between(0, 160)))
    df["can_status_state"] = np.select([df.can_status.eq(0), df.can_status.notna()],
                                        ["NORMAL", "ABNORMAL"], default="UNKNOWN")
    can = df.can_speed.where(df.can_speed.between(0, 160) & df.can_status.eq(0))
    gps = df.gps_speed.where(df.gps_speed.between(0, 160))
    df["speed"] = can.fillna(gps)
    df["speed_source"] = np.where(can.notna(), "CAN_CONFIRMED", np.where(gps.notna(), "GPS_FALLBACK", "UNKNOWN"))
    df["gps_speed_conflict_flag"] = (df.gps_speed.eq(0) & df.can_speed.gt(5))
    for c, maximum in [("rpm", 8031.875), ("engine_load", 250)]:
        df[c] = df[c].where(df[c].between(0, maximum))
    status = df.get("carStatus", pd.Series("unknown", index=df.index)).astype("string").str.lower()
    df["status"] = status.replace({"0": "parking", "0.0": "parking", "1": "driving", "1.0": "driving", "2": "idling", "2.0": "idling"})
    df["status"] = df.status.where(df.status.isin(["parking", "driving", "idling"]), "unknown")
    df = df.sort_values(["trip_id", "timestamp", "source_row"], kind="stable").reset_index(drop=True)
    df["duplicate_timestamp_flag"] = df.duplicated(["trip_id", "timestamp"], keep=False) & df.trip_id.notna()
    # Keep all rows; mark the deterministic last source row at a timestamp as canonical.
    df["is_canonical"] = (~df.duplicated(["trip_id", "timestamp"], keep="last") &
                          ~df.invalid_key_flag & ~df.invalid_timestamp_flag)
    df["interval_seconds"] = 0.0
    df["next_gap_seconds"] = 0.0
    df["large_timestamp_gap_flag"] = False
    df["fuel_delta"] = np.nan
    df["mileage_delta"] = np.nan
    canonical = df.loc[df.is_canonical]
    groups = canonical.groupby("trip_id", sort=False)
    gap = (groups.timestamp.shift(-1) - canonical.timestamp).dt.total_seconds()
    df.loc[canonical.index, "next_gap_seconds"] = gap.fillna(0)
    df.loc[canonical.index, "interval_seconds"] = gap.where(gap.between(0, GAP_SECONDS), 0).fillna(0)
    df.loc[canonical.index, "large_timestamp_gap_flag"] = gap.gt(GAP_SECONDS)
    for field in ["fuel", "mileage"]:
        valid_meter = canonical[field].where(canonical[field].ge(0))
        # Do not bridge missing readings: adjacent valid readings only.
        delta = valid_meter.groupby(canonical.trip_id, sort=False).diff()
        df.loc[canonical.index, field + "_delta"] = delta
    previous_seconds = groups.timestamp.diff().dt.total_seconds()
    # 2 km slack handles quantized odometers; retain the delta but exclude flagged trips from modelling.
    df["implausible_mileage_flag"] = False
    df.loc[canonical.index, "implausible_mileage_flag"] = df.loc[canonical.index, "mileage_delta"].gt(previous_seconds / 3600 * 160 + 2)
    return df
