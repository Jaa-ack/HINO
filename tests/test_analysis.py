import numpy as np
import pandas as pd
import pytest

from src.benchmarks import build_benchmarks
from src.attribution import estimate_opportunities, build_hotspots
from src.fuel_model import analyze_vehicle_health



def test_benchmark_excludes_subject_vehicle_and_records_relaxation(peer_trips):
    result = build_benchmarks(peer_trips)
    assert result.loc[0, 'expected_fuel_l'] == 10
    assert result.loc[0, 'peer_trip_count'] == 15
    assert result.loc[0, 'benchmark_level'] == 'L1'
    changed = peer_trips.copy()
    changed.loc[:2, 'trip_fuel_l'] = 999
    assert build_benchmarks(changed).loc[0, 'expected_fuel_l'] == 10
    changed.loc[0, 'route_id'] = 'unique'
    assert build_benchmarks(changed).loc[0, 'benchmark_level'] == 'L2'


def test_insufficient_peers_do_not_fabricate_expected_fuel(peer_trips):
    t = estimate_opportunities(build_benchmarks(peer_trips.head(3)))
    assert t.expected_fuel_l.isna().all()
    assert t.benchmark_gap_l.isna().all()


def test_improvement_priorities_not_negative_and_normalized(peer_trips):
    t = estimate_opportunities(build_benchmarks(peer_trips))
    cols = ['idle_context_priority_pct','rpm_priority_pct','engine_load_priority_pct']
    assert (t[cols] >= 0).all().all()
    assert np.allclose(t[cols].sum(axis=1).iloc[:3], 100)
    assert np.allclose(t[cols].sum(axis=1).iloc[3:], 0)
    assert (t.benchmark_gap_l <= t.trip_fuel_l).all()
    assert t.loc[0,'benchmark_gap_l'] > 0
    assert t.loc[3,'benchmark_gap_l'] == 0


def test_vehicle_health_requires_consecutive_supported_residuals(peer_trips):
    t = analyze_vehicle_health(peer_trips)
    v = t[t.enabledCode == 'V0'].sort_values('start_time')
    assert not bool(v.iloc[0].vehicle_health_flag)
    assert not bool(v.iloc[1].vehicle_health_flag)
    assert bool(v.iloc[2].vehicle_health_flag)
    assert not t[t.enabledCode != 'V0'].vehicle_health_flag.any()
    insufficient = analyze_vehicle_health(peer_trips.head(3))
    assert not insufficient.vehicle_health_flag.any()
    assert insufficient.vehicle_residual_ratio.isna().all()


@pytest.mark.parametrize('arrow_strings', [False, True])
def test_hotspots_count_visits_not_samples_and_observed_minutes(peer_trips, arrow_strings):
    telemetry = pd.DataFrame(dict(trip_id=['t0']*4, is_canonical=[True]*4, status=['idling','idling','driving','idling'],
        latitude=[25.]*4, longitude=[121.]*4, interval_seconds=[60.,60.,60.,60.], next_gap_seconds=[60.,60.,60.,0.],
        timestamp=pd.date_range('2025-01-01', periods=4, freq='min')))
    if arrow_strings:
        telemetry['trip_id'] = telemetry.trip_id.astype('string')
    trips = estimate_opportunities(build_benchmarks(peer_trips))
    hotspots = build_hotspots(telemetry, trips)
    assert hotspots.visit_count.sum() == 2
    assert hotspots.total_idle_minutes.sum() == 3
    # Only observed idle minutes are shown; no allocated fuel-saving claim.
    assert hotspots.total_idle_minutes.sum() <= trips.iloc[0].idle_minutes
    assert not any('saving' in c or 'fuel_opportunity' in c for c in hotspots)


def test_hotspots_show_observed_vehicle_support_and_hourly_idle(peer_trips):
    telemetry = pd.DataFrame(dict(
        trip_id=['t0', 't1', 't3'], is_canonical=[True] * 3, status=['idling'] * 3,
        latitude=[25.] * 3, longitude=[121.] * 3, interval_seconds=[120., 60., 120.],
        timestamp=pd.to_datetime(['2025-01-01 07:59', '2025-01-02 08:10', '2025-01-03 08:59']),
    ))
    hotspot = build_hotspots(telemetry, peer_trips).iloc[0]
    assert hotspot.vehicle_count == 2  # t0 and t1 are the same observed vehicle.
    assert hotspot.trip_count == 3
    assert hotspot.total_idle_minutes == pytest.approx(5.)
    assert hotspot.peak_idle_hour == 8
    assert hotspot.peak_idle_minutes == pytest.approx(3.)  # Split intervals at clock-hour boundaries.
    assert 'driver_count' not in hotspot.index


def test_repeated_same_vehicle_hotspot_is_not_cross_vehicle(peer_trips):
    telemetry = pd.DataFrame(dict(
        trip_id=['t0', 't1'], is_canonical=[True] * 2, status=['idling'] * 2,
        latitude=[25.] * 2, longitude=[121.] * 2, interval_seconds=[60., 60.],
        timestamp=pd.to_datetime(['2025-01-01 23:59:30', '2025-01-02 00:01:00']),
    ))
    hotspot = build_hotspots(telemetry, peer_trips).iloc[0]
    assert hotspot.vehicle_count == 1
    assert hotspot.peak_idle_hour == 0
    assert hotspot.peak_idle_minutes == pytest.approx(1.5)
