"""Observed Comparable Trip Benchmark; every subject vehicle is excluded."""
import numpy as np
import pandas as pd

from src.config import EVIDENCE_MODE, LEVER_FEATURES, MIN_PEER_TRIPS, MIN_PEER_VEHICLES

BEHAVIORS = [feature for feature, _ in LEVER_FEATURES.values()]


def comparison_quality(level, trips, vehicles, dispersion):
    """Heuristic comparison evidence strength; neither probability nor data quality."""
    if level == 'L1' and trips >= 10 and vehicles >= 3 and dispersion <= .25:
        return 'HIGH'
    if level in {'L1', 'L2'} and trips >= 8 and vehicles >= 2 and dispersion <= .5:
        return 'MEDIUM'
    return 'LOW'


def build_benchmarks(trips, min_peers=MIN_PEER_TRIPS):
    out = trips.copy()
    out['evidence_mode'] = EVIDENCE_MODE
    out['benchmark_level'] = 'INSUFFICIENT'
    out['benchmark_quality'] = pd.Series(None, index=out.index, dtype='object')
    out['peer_trip_count'] = 0
    out['peer_vehicle_count'] = 0
    for c in ['expected_fuel_l', 'expected_km_per_l', 'peer_fuel_median_l_per_km',
              'peer_fuel_iqr_l_per_km', 'benchmark_dispersion'] + ['peer_' + b for b in BEHAVIORS]:
        out[c] = np.nan
    eligible = out.loc[out.benchmark_eligible & out.trip_distance_km.gt(0) & out.trip_fuel_l.gt(0)]
    grouped = {k: g for k, g in eligible.groupby(['vehicle_type', 'distance_bin'])}
    for idx, t in eligible.iterrows():
        pool = grouped[(t.vehicle_type, t.distance_bin)]
        pool = pool.loc[pool.enabledCode.ne(t.enabledCode)]
        strict = pool.route_id.eq(t.route_id) & (t.route_id != 'UNKNOWN') & pool.time_of_day.eq(t.time_of_day)
        medium = pool.time_of_day.eq(t.time_of_day)
        for level, candidates in [('L1', pool.loc[strict]), ('L2', pool.loc[medium]), ('L3', pool)]:
            count, vehicles = len(candidates), candidates.enabledCode.nunique()
            if count < max(MIN_PEER_TRIPS, min_peers) or vehicles < MIN_PEER_VEHICLES:
                continue
            intensity = candidates.trip_fuel_l / candidates.trip_distance_km
            median = float(intensity.median())
            iqr = float(intensity.quantile(.75) - intensity.quantile(.25))
            dispersion = iqr / median
            out.loc[idx, ['benchmark_level', 'peer_trip_count', 'peer_vehicle_count']] = [level, count, vehicles]
            out.loc[idx, 'peer_fuel_median_l_per_km'] = median
            out.loc[idx, 'peer_fuel_iqr_l_per_km'] = iqr
            out.loc[idx, 'benchmark_dispersion'] = dispersion
            out.loc[idx, 'benchmark_quality'] = comparison_quality(level, count, vehicles, dispersion)
            out.loc[idx, 'expected_fuel_l'] = median * t.trip_distance_km
            out.loc[idx, 'expected_km_per_l'] = 1 / median
            for behavior in BEHAVIORS:
                observed = candidates[behavior].dropna()
                out.loc[idx, 'peer_' + behavior] = observed.median() if len(observed) >= MIN_PEER_TRIPS else np.nan
            break
    return out
