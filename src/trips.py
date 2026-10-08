"""Trip metrics from actual timestamps and adjacent cumulative meter deltas."""
import numpy as np
import pandas as pd


def weighted_mean(values, seconds):
    mask = values.notna() & seconds.gt(0)
    return float(np.average(values[mask], weights=seconds[mask])) if mask.any() else np.nan


def weighted_quantile(values, seconds, q=.95):
    mask = values.notna() & seconds.gt(0)
    if not mask.any():
        return np.nan
    order = np.argsort(values[mask].to_numpy())
    v, w = values[mask].to_numpy()[order], seconds[mask].to_numpy()[order]
    return float(v[np.searchsorted(np.cumsum(w), q * w.sum())])


def ratio_above(values, seconds, threshold):
    total = seconds[values.notna()].sum()
    return float(seconds[values.gt(threshold)].sum() / total) if total > 0 else np.nan


def grid_cell(lat, lon, decimals=2):
    return f"{lat:.{decimals}f},{lon:.{decimals}f}" if pd.notna(lat) and pd.notna(lon) else None


def aggregate_trips(telemetry, events):
    canonical = telemetry.loc[telemetry.is_canonical]
    event_counts = events.drop_duplicates("event_identity").groupby(["trip_id", "event_name"]).size() if len(events) else pd.Series(dtype=int)
    records = []
    raw_counts = telemetry.groupby("trip_id").size()
    for trip_id, g in canonical.groupby("trip_id", sort=True):
        first, last = g.iloc[0], g.iloc[-1]
        dt = g.interval_seconds
        elapsed = (last.timestamp - first.timestamp).total_seconds() / 60
        observed = dt.sum() / 60
        known = dt[g.status.isin(["driving", "idling", "parking"])].sum() / 60
        gps = g.dropna(subset=["latitude", "longitude"])
        r = {"trip_id": trip_id, "enabledCode": first.enabledCode, "journeyCode": first.journeyCode,
             "vehicle_type": first.vehicle_type, "start_time": first.timestamp, "end_time": last.timestamp,
             "duration_minutes": elapsed, "observed_minutes": observed, "unobserved_minutes": elapsed - observed,
             "sample_count": len(g), "raw_sample_count": int(raw_counts[trip_id]),
             "start_lat": gps.latitude.iloc[0] if len(gps) else np.nan, "start_lon": gps.longitude.iloc[0] if len(gps) else np.nan,
             "end_lat": gps.latitude.iloc[-1] if len(gps) else np.nan, "end_lon": gps.longitude.iloc[-1] if len(gps) else np.nan}
        for metric in ["driving", "idle", "parking"]:
            status = "idling" if metric == "idle" else metric
            r[metric + "_minutes"] = float(dt[g.status.eq(status)].sum() / 60) if known else np.nan
        engine_minutes = r["driving_minutes"] + r["idle_minutes"]
        r["idle_ratio"] = r["idle_minutes"] / engine_minutes if engine_minutes > 0 else np.nan
        r["unknown_status_minutes"] = observed - known
        for meter, result in [("fuel", "trip_fuel_l"), ("mileage", "trip_distance_km")]:
            delta = g[meter + "_delta"]
            r[result] = float(delta.clip(lower=0).sum()) if delta.notna().any() else np.nan
            r[meter + "_reset_flag"] = bool(delta.lt(0).any())
            r[meter + "_missing_flag"] = bool(g[meter].isna().any())
        fuel, distance = r["trip_fuel_l"], r["trip_distance_km"]
        r["km_per_l"] = distance / fuel if fuel > 0 else np.nan
        r["fuel_l_per_100km"] = fuel / distance * 100 if distance > 0 else np.nan
        moving = dt.where(g.status.eq("driving"), 0)
        operating = dt.where(g.status.isin(["driving", "idling"]), 0)
        r.update({"avg_speed": weighted_mean(g.speed, moving), "max_speed": g.speed.max(),
                  "avg_rpm": weighted_mean(g.rpm, operating), "p95_rpm": weighted_quantile(g.rpm, operating),
                  "rpm_above_2500_ratio": ratio_above(g.rpm, operating, 2500),
                  "avg_engine_load": weighted_mean(g.engine_load, operating), "p95_engine_load": weighted_quantile(g.engine_load, operating),
                  "engine_load_above_90_ratio": ratio_above(g.engine_load, operating, 90),
                  "large_timestamp_gap_flag": bool(g.large_timestamp_gap_flag.any()),
                  "missing_gps_flag": bool(g.invalid_gps_flag.any()), "low_sample_count_flag": len(g) < 5,
                  "duplicate_timestamp_flag": bool(g.duplicate_timestamp_flag.any()),
                  "gps_speed_conflict_flag": bool(g.gps_speed_conflict_flag.any()),
                  "implausible_mileage_flag": bool(g.implausible_mileage_flag.any()),
                  "can_status_state": "ABNORMAL" if (g.can_status.notna() & g.can_status.ne(0)).any() else "UNKNOWN" if g.can_status.isna().any() else "NORMAL",
                  "can_error_flag": bool((g.can_status.notna() & g.can_status.ne(0)).any()),
                  "can_status_unknown_flag": bool(g.can_status.isna().any()),
                  "type_conflict_flag": g.vehicle_type.nunique() > 1,
                  "coverage_ratio": observed / elapsed if elapsed > 0 else 0.0})
        for metric, name in [("rapid_accel_event_count", "accelerate"), ("rapid_decel_event_count", "decelerate"),
                             ("speeding_event_count", "speeding"), ("engine_overload_event_count", "engineOverloading"), ("dtc_event_count", "dtc")]:
            r[metric] = int(event_counts.get((trip_id, name), 0))
        r["event_count"] = int(event_counts.loc[trip_id].sum()) if trip_id in event_counts.index.get_level_values(0) else 0
        stopped = g.status.isin(["idling", "parking"])
        r["stop_count"] = int((stopped & (~stopped.shift(fill_value=False) | g.timestamp.diff().dt.total_seconds().gt(300))).sum())
        penalties = {"fuel_reset_flag": 25, "mileage_reset_flag": 25, "large_timestamp_gap_flag": 15,
                     "missing_gps_flag": 10, "low_sample_count_flag": 20, "fuel_missing_flag": 20,
                     "mileage_missing_flag": 20, "implausible_mileage_flag": 35, "can_error_flag": 10,
                     "duplicate_timestamp_flag": 5, "type_conflict_flag": 20}
        r["data_quality_score"] = max(0, 100 - sum(weight for flag, weight in penalties.items() if r[flag]))
        r["benchmark_eligible"] = bool(r["data_quality_score"] >= 70 and distance >= 5 and fuel >= 1 and
                                       r["coverage_ratio"] >= .8 and not any(r[f] for f in
                                       ["fuel_reset_flag", "mileage_reset_flag", "implausible_mileage_flag", "fuel_missing_flag", "mileage_missing_flag", "type_conflict_flag"]))
        r["origin_cell"], r["destination_cell"] = grid_cell(r["start_lat"], r["start_lon"]), grid_cell(r["end_lat"], r["end_lon"])
        r["route_id"] = (f"{r['vehicle_type']}|{r['origin_cell']}→{r['destination_cell']}"
                         if r["origin_cell"] and r["destination_cell"] else "UNKNOWN")
        r["distance_bin"] = str(pd.cut([distance], [0, 5, 20, 50, 100, 200, np.inf], right=False,
                                        labels=["0–5", "5–20", "20–50", "50–100", "100–200", "200+"])[0])
        hour = first.timestamp.hour
        r["time_of_day"] = "morning" if 6 <= hour < 10 else "day" if 10 <= hour < 16 else "evening" if 16 <= hour < 20 else "night"
        records.append(r)
    if not records:
        raise ValueError("沒有可聚合的複合 trip key 與 timestamp；原始列保留於 telemetry.parquet，請檢查資料品質。")
    return pd.DataFrame(records)
