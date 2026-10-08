"""Estimated Improvement Levers: evidence-based screening, without liter attribution."""
import numpy as np
import pandas as pd
import pandas as pd

from src.config import LEVER_FEATURES
from src.trips import grid_cell


def estimate_opportunities(trips):
    out = trips.copy()
    known = out.expected_fuel_l.notna() & out.trip_fuel_l.notna() & out.benchmark_eligible
    out['benchmark_gap_l'] = (out.trip_fuel_l - out.expected_fuel_l).clip(lower=0).where(known)
    out['benchmark_gap_pct'] = out.benchmark_gap_l / out.trip_fuel_l.replace(0, np.nan) * 100
    scores = []
    for factor, (feature, floor) in LEVER_FEATURES.items():
        excess = (out[feature] - out['peer_' + feature]).clip(lower=0)
        base = out['peer_' + feature].abs().clip(lower=floor)
        column = factor + '_excess_score'
        out[column] = (excess / (excess + base)).where(known)
        scores.append(column)
    complete = out[scores].notna().all(axis=1)
    total = out[scores].sum(axis=1).replace(0, np.nan)
    for factor in LEVER_FEATURES:
        out[factor + '_priority_pct'] = (100 * out[factor + '_excess_score'] / total).fillna(0).where(complete)
    out['opportunity_status'] = np.where(known, 'OBSERVED_COMPARISON', 'INSUFFICIENT_DATA')
    out['lever_status'] = np.where(complete, 'HEURISTIC_PRIORITY', 'INSUFFICIENT_DATA')
    return out


def build_hotspots(telemetry, trips):
    columns = ["stop_hotspot_id", "latitude", "longitude", "visit_count", "trip_count", "vehicle_count",
               "avg_idle_minutes", "total_idle_minutes", "peak_idle_hour", "peak_idle_minutes",
               "stop_purpose_mock", "is_mock_purpose"]
    t = telemetry.loc[telemetry.is_canonical].sort_values(["trip_id", "timestamp"]).copy()
    is_idle = t.status.eq("idling") & t.interval_seconds.gt(0) & t.latitude.notna() & t.longitude.notna()
    t["cell"] = [grid_cell(lat, lon, 3) for lat, lon in zip(t.latitude, t.longitude)]
    new_episode = (t.trip_id.ne(t.trip_id.shift()) | ~is_idle.shift(fill_value=False) | t.cell.ne(t.cell.shift()) |
                   t.timestamp.diff().dt.total_seconds().gt(300))
    t["visit_id"] = new_episode.fillna(True).astype("int64").cumsum()
    idle = t.loc[is_idle].copy()
    if idle.empty:
        return pd.DataFrame(columns=columns)
    idle["minutes"] = idle.interval_seconds / 60
    # Attribute only valid observed intervals, splitting across clock-hour boundaries.
    # The hour denotes accumulated idling evidence, not confirmed queueing or a cause.
    remaining = idle[["cell", "timestamp", "interval_seconds"]].copy()
    hourly_parts = []
    while not remaining.empty:
        next_hour = remaining.timestamp.dt.floor('h') + pd.Timedelta(hours=1)
        seconds = np.minimum(remaining.interval_seconds, (next_hour - remaining.timestamp).dt.total_seconds())
        hourly_parts.append(pd.DataFrame({'cell': remaining.cell, 'hour': remaining.timestamp.dt.hour,
                                         'minutes': seconds / 60}))
        remaining['interval_seconds'] -= seconds
        remaining['timestamp'] = next_hour
        remaining = remaining.loc[remaining.interval_seconds.gt(0)].copy()
    hourly = pd.concat(hourly_parts).groupby(['cell', 'hour'], as_index=False).minutes.sum()
    peaks = hourly.sort_values(['minutes', 'hour'], ascending=[False, True]).drop_duplicates('cell').set_index('cell')
    visits = idle.groupby(["trip_id", "cell", "visit_id"], as_index=False).agg(minutes=("minutes", "sum"))
    allocation = visits.merge(trips[["trip_id", "enabledCode", "stop_purpose"]], on="trip_id", how="left", validate="many_to_one")
    rows = []
    for cell, g in allocation.groupby("cell"):
        lat, lon = map(float, cell.split(","))
        rows.append({"stop_hotspot_id": "GRID-" + cell, "latitude": lat, "longitude": lon,
                     "visit_count": len(g), "trip_count": g.trip_id.nunique(), "vehicle_count": g.enabledCode.nunique(),
                     "avg_idle_minutes": g.minutes.mean(), "peak_idle_hour": int(peaks.loc[cell, 'hour']),
                     "peak_idle_minutes": float(peaks.loc[cell, 'minutes']),
                     "total_idle_minutes": g.minutes.sum(),
                     "stop_purpose_mock": ", ".join(sorted(g.stop_purpose.dropna().unique())), "is_mock_purpose": True})
    return pd.DataFrame(rows, columns=columns).sort_values("total_idle_minutes", ascending=False).reset_index(drop=True)
