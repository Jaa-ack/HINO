import pandas as pd

from src.clean import clean_telemetry
from src.events import normalize_events
from src.trips import aggregate_trips
from src.config import LEVER_FEATURES, ML_NUMERIC_FEATURES
from src.recommendations import decision_packet
from src.benchmarks import build_benchmarks
from src.attribution import estimate_opportunities
from src.fuel_model import analyze_vehicle_health
from src.utils import ROOT
import json
import pyarrow.parquet as pq


def test_can_status_zero_is_normal(raw_sample):
    data = raw_sample.assign(**{"can.canStatus": [0] * len(raw_sample)})
    result = clean_telemetry(data)
    assert result.can_status_state.eq("NORMAL").all()
    assert result.speed_source.iloc[1] == "CAN_CONFIRMED"


def test_can_status_nonzero_is_abnormal(raw_sample):
    data = raw_sample.assign(**{"can.canStatus": [1, 9, 0, 0, 0, 0]})
    telemetry = clean_telemetry(data)
    trips = aggregate_trips(telemetry, normalize_events(data))
    assert telemetry.can_status_state.iloc[0] == "ABNORMAL"
    assert trips.loc[trips.enabledCode.eq("A"), "can_error_flag"].iloc[0]


def test_can_status_missing_is_unknown(raw_sample):
    telemetry = clean_telemetry(raw_sample)
    trips = aggregate_trips(telemetry, normalize_events(raw_sample))
    assert telemetry.can_status_state.eq("UNKNOWN").all()
    assert trips.can_status_unknown_flag.all()


def test_missing_can_status_does_not_treat_can_speed_as_confirmed_normal(raw_sample):
    data = raw_sample.assign(**{"gps.speed": [5, 40, 5, 5, 40, 5]})
    telemetry = clean_telemetry(data)
    assert telemetry.speed_source.eq("GPS_FALLBACK").all()
    assert telemetry.loc[telemetry.can_speed.eq(60), "speed"].eq(40).all()


def test_idle_minutes_uses_car_status_not_event_2(raw_sample):
    a = raw_sample.copy()
    b = raw_sample.copy()
    b["event[0].type"] = "2"
    left = aggregate_trips(clean_telemetry(a), normalize_events(a))
    right = aggregate_trips(clean_telemetry(b), normalize_events(b))
    pd.testing.assert_series_equal(left.idle_minutes, right.idle_minutes)


def test_event_6_7_not_primary_features():
    assert "acceleration" not in LEVER_FEATURES
    assert not any("event_count" in name for name in ML_NUMERIC_FEATURES)


def test_event_6_not_primary_lever(peer_trips):
    base = estimate_opportunities(build_benchmarks(peer_trips))
    changed = peer_trips.copy()
    changed['rapid_accel_event_count'] = 9999
    newer = estimate_opportunities(build_benchmarks(changed))
    cols = [f'{f}_priority_pct' for f in LEVER_FEATURES]
    pd.testing.assert_frame_equal(base[cols], newer[cols])


def test_event_7_not_health_match_feature(peer_trips):
    base = analyze_vehicle_health(peer_trips)
    changed = peer_trips.copy()
    changed['rapid_decel_event_count'] = range(len(changed))
    newer = analyze_vehicle_health(changed)
    pd.testing.assert_series_equal(base.health_expected_fuel_l, newer.health_expected_fuel_l)


def test_event_6_7_not_primary_ml_features():
    assert 'rapid_accel_event_count' not in ML_NUMERIC_FEATURES
    assert 'rapid_decel_event_count' not in ML_NUMERIC_FEATURES


def test_event_8_not_reconstructed(raw_sample):
    data = raw_sample.copy()
    data['can.canStatus'] = 0
    data['can.canSpeed'] = 150
    data['event[0].type'] = None
    trips = aggregate_trips(clean_telemetry(data), normalize_events(data))
    assert trips.speeding_event_count.eq(0).all()


def test_event_8_source_conflict_documented():
    ref = pd.read_parquet(ROOT / 'data/reference/event_reference.parquet')
    row = ref.loc[ref.event_type.eq(8)].iloc[0]
    assert row.source_conflict_flag
    assert row.comparison_role == 'SUPPORTING_ONLY'
    assert 'SOURCE_CONFLICT' in (ROOT / 'docs/source_contract.md').read_text()


def test_event_11_separate_from_engine_load_above_90_ratio(raw_sample):
    data = raw_sample.copy()
    data['can.engine.engineLoad'] = 95
    data['event[0].type'] = None
    trips = aggregate_trips(clean_telemetry(data), normalize_events(data))
    assert trips.engine_load_above_90_ratio.max() == 1
    assert trips.engine_overload_event_count.eq(0).all()


def test_rpm_threshold_name_is_explicit(raw_sample):
    trips = aggregate_trips(clean_telemetry(raw_sample), normalize_events(raw_sample))
    assert 'rpm_above_2500_ratio' in trips
    assert 'high_rpm_ratio' not in trips


def test_engine_load_threshold_name_is_explicit(raw_sample):
    trips = aggregate_trips(clean_telemetry(raw_sample), normalize_events(raw_sample))
    assert 'engine_load_above_90_ratio' in trips
    assert 'high_engine_load_ratio' not in trips


def test_acceleration_priority_removed(peer_trips):
    out = estimate_opportunities(build_benchmarks(peer_trips))
    assert 'acceleration_priority_pct' not in out
    assert 'idle_context_priority_pct' in out


def test_mock_driver_marked_as_competition_placeholder():
    capability = pd.read_csv(ROOT / 'data/reference/data_capability_matrix.csv')
    driver = capability.loc[capability.field.eq('driverUid')].iloc[0]
    assert not driver.competition_available
    assert driver.reference_schema_documented
    assert 'placeholder' in (ROOT / 'docs/data_capability_matrix.md').read_text()


def test_extended_itraq_fields_not_inserted_as_observed_raw():
    telemetry_schema = pd.read_parquet(ROOT / 'data/interim/telemetry.parquet').columns
    assert not {'driverUid', 'engineFuelRate', 'ptoSwitch'} & set(telemetry_schema)


def test_pto_listed_as_extended_itraq_to_confirm():
    _assert_extended_to_confirm('ptoSwitch')


def test_driveruid_listed_as_extended_itraq_to_confirm():
    _assert_extended_to_confirm('driverUid')


def test_engine_fuel_rate_listed_as_extended_itraq_to_confirm():
    _assert_extended_to_confirm('engineFuelRate')


def _assert_extended_to_confirm(field):
    capability = pd.read_csv(ROOT / 'data/reference/data_capability_matrix.csv')
    row = capability.loc[capability.field.eq(field)].iloc[0]
    assert row.data_layer == 'B_EXTENDED_ITRAQ'
    assert row.reference_schema_documented
    assert not row.competition_available
    assert row.production_availability == 'PRODUCTION_AVAILABILITY_TO_CONFIRM'


def test_pilot_outcome_template_has_no_fake_rows():
    template = pd.read_csv(ROOT / 'data/pilot/action_outcomes_template.csv')
    assert template.empty
    assert {'action_id', 'primary_owner', 'action_taken', 'before_metric', 'after_metric'} <= set(template)


def test_processed_metadata_has_contract_versions():
    summary = json.loads((ROOT / 'data/processed/pipeline_summary.json').read_text())
    model = json.loads((ROOT / 'data/processed/model_report.json').read_text())
    packet = next(iter(json.loads((ROOT / 'data/processed/decision_packets.json').read_text()).values()))
    for record in [summary, model, packet]:
        assert record['analysis_version'] == 'ecopilot_v3'
        assert record['source_contract_version'] == 'competition+faq+event0929_v1'
        assert record['event_reference_version'] == '0929'
    metadata = pq.read_metadata(ROOT / 'data/processed/trips_enriched.parquet').metadata
    assert metadata[b'analysis_version'] == b'ecopilot_v3'


def test_idle_owner_has_driver_supporting_role():
    packet = decision_packet({"trip_id": "A::1", "benchmark_gap_l": 1, "benchmark_quality": "HIGH",
                              "idle_context_priority_pct": 80, "rpm_priority_pct": 10,
                              "engine_load_priority_pct": 10})
    assert packet["primary_owner"] == "DISPATCHER"
    assert "DRIVER" in packet["supporting_roles"]


def test_engine_load_owner_not_automatically_driver():
    packet = decision_packet({"trip_id": "A::1", "benchmark_gap_l": 1, "benchmark_quality": "HIGH",
                              "idle_context_priority_pct": 10, "rpm_priority_pct": 10,
                              "engine_load_priority_pct": 80})
    assert packet["primary_owner"] == "FLEET_MANAGER"
    assert set(packet["supporting_roles"]) == {"DISPATCHER", "MAINTENANCE"}


def test_low_evidence_routes_to_manager_for_evidence_gathering():
    packet = decision_packet({"trip_id": "A::1", "benchmark_gap_l": 1, "benchmark_quality": "LOW",
                              "idle_context_priority_pct": 90, "rpm_priority_pct": 5,
                              "engine_load_priority_pct": 5})
    assert packet['primary_owner'] == 'FLEET_MANAGER'
    assert packet['owner_confidence'] == 'ROUTING_EVIDENCE_LIMITED'
    assert '補齊' in packet['handoff_reason']
