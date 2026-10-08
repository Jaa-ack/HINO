"""Evidence boundary regressions: mutate context, not just inspect feature lists."""
import json

import numpy as np
import pandas as pd
import pytest

from src.benchmarks import build_benchmarks
from src.attribution import estimate_opportunities
from src.fuel_model import analyze_vehicle_health, evaluate_optional_ml
from src.recommendations import decision_packet
from src.llm import narrate
from src.mock_context import MOCK_RULES

MOCK_FIELDS = ['payload_ratio', 'traffic_level', 'task_type', 'weather']


def altered_mock(trips):
    changed = trips.copy()
    changed['payload_ratio'] = np.linspace(0, 100, len(trips))
    for c in MOCK_FIELDS[1:]:
        changed[c] = [f'UNIQUE-{i}' for i in range(len(trips))]
    return changed


def test_type_mapping_300_500_700():
    from src import schema
    assert getattr(schema, 'HINO_SERIES', None) == {'300': 'HINO 300 系列', '500': 'HINO 500 系列', '700': 'HINO 700 系列'}
    assert '車型系列代碼' in schema.build_dictionary(['vehicle_type']).description.iloc[0]


def test_primary_benchmark_does_not_use_mock_fields(peer_trips):
    without = peer_trips.drop(columns=MOCK_FIELDS)
    actual = build_benchmarks(without)
    assert actual.expected_fuel_l.iloc[0] == 10


def test_vehicle_health_does_not_use_mock_fields(peer_trips):
    actual = analyze_vehicle_health(peer_trips.drop(columns=MOCK_FIELDS))
    assert actual.vehicle_health_flag.iloc[2]


def test_mock_change_does_not_change_primary_benchmark(peer_trips):
    a, b = build_benchmarks(peer_trips), build_benchmarks(altered_mock(peer_trips))
    cols = [c for c in a if c.startswith(('benchmark_', 'peer_', 'expected_'))]
    pd.testing.assert_frame_equal(a[cols], b[cols])


def test_mock_change_does_not_change_vehicle_health_flag(peer_trips):
    a, b = analyze_vehicle_health(peer_trips), analyze_vehicle_health(altered_mock(peer_trips))
    cols = [c for c in a if c.startswith(('health_', 'vehicle_', 'consecutive_'))]
    pd.testing.assert_frame_equal(a[cols], b[cols])


def test_benchmark_quality_exists(peer_trips):
    result = build_benchmarks(peer_trips)
    assert {'peer_fuel_median_l_per_km', 'peer_fuel_iqr_l_per_km', 'benchmark_dispersion', 'benchmark_quality'} <= set(result)
    assert set(result.benchmark_quality) <= {'HIGH', 'MEDIUM', 'LOW'}
    assert result.peer_fuel_median_l_per_km.iloc[0] == .25
    assert result.peer_fuel_iqr_l_per_km.iloc[0] == 0
    assert result.benchmark_quality.iloc[0] == 'HIGH'
    insufficient = build_benchmarks(peer_trips.head(3))
    assert insufficient.benchmark_quality.isna().all()


def test_benchmark_gap_nonnegative(peer_trips):
    result = estimate_opportunities(build_benchmarks(peer_trips))
    assert 'benchmark_gap_l' in result
    assert result.benchmark_gap_l.ge(0).all()
    assert result.benchmark_gap_l.iloc[0] == 10
    assert result.benchmark_gap_pct.iloc[0] == 50
    assert result.benchmark_gap_l.iloc[3] == 0
    insufficient = estimate_opportunities(build_benchmarks(peer_trips.head(3)))
    assert insufficient.benchmark_gap_l.isna().all()


def test_priorities_are_percentages_and_not_liters(peer_trips):
    result = estimate_opportunities(build_benchmarks(peer_trips.drop(columns=MOCK_FIELDS)))
    cols = [f'{factor}_priority_pct' for factor in ['idle_context', 'rpm', 'engine_load']]
    assert set(cols) <= set(result)
    assert np.isclose(result[cols].iloc[0].sum(), 100)
    assert result[cols].iloc[3].sum() == 0
    assert not any(c.endswith('_saving_l') for c in result)
    unknown = peer_trips.copy()
    unknown.loc[0, 'idle_ratio'] = np.nan
    out = estimate_opportunities(build_benchmarks(unknown))
    assert pd.notna(out.benchmark_gap_l.iloc[0])
    assert out[cols].iloc[0].isna().all()


def packet(peer_trips):
    return decision_packet(analyze_vehicle_health(estimate_opportunities(build_benchmarks(peer_trips))).iloc[0])


def generated(evidence_ids):
    return dict(headline='核對等待安排', evidence_summary='怠速觀測值得與到站安排一起核對。',
                next_action='請與調度確認等待安排。', what_to_verify=['核對實際停靠用途。'],
                handoff_role='DISPATCHER', evidence_ids=evidence_ids)


def intercept(monkeypatch, output, captured):
    import src.llm as llm
    monkeypatch.setenv('OPENAI_API_KEY', 'test-placeholder')
    monkeypatch.setenv('OPENAI_MODEL', 'test-model')
    monkeypatch.setenv('ECOPILOT_ENABLE_LLM', 'true')
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': json.dumps(output)}]}]}
    def post(*args, **kwargs):
        captured.update(kwargs['json'])
        return Response()
    monkeypatch.setattr(llm.requests, 'post', post)


def test_genai_unknown_evidence_id_falls_back(peer_trips, monkeypatch):
    p = packet(peer_trips)
    assert p.get('evidence'), 'Decision Packet needs traceable evidence IDs'
    intercept(monkeypatch, generated(['invented']), {})
    result = narrate(p, 'DRIVER', use_llm=True)
    assert result['mode'] == 'deterministic_template'
    assert 'fallback_reason' in result


def test_external_llm_payload_excludes_raw_vehicle_identifier(peer_trips, monkeypatch):
    p = packet(peer_trips)
    p.update(enabledCode='VEHICLE-SECRET', journeyCode='JOURNEY-SECRET', trip_id='VEHICLE-SECRET::JOURNEY-SECRET',
             route_id='25.123,121.456', route_hotspot='GRID-25.123,121.456')
    captured = {}
    intercept(monkeypatch, {}, captured)
    narrate(p, 'DRIVER', use_llm=True)
    outgoing = captured['input']
    for forbidden in ['enabledCode', 'journeyCode', 'VEHICLE-SECRET', 'JOURNEY-SECRET', '25.123', '121.456', 'mock_context']:
        assert forbidden not in outgoing
    payload = json.loads(outgoing)
    assert set(payload) == {'anonymous_trip_key', 'persona', 'evidence', 'ownership'}
    assert payload['ownership'] == {'primary_owner': 'DISPATCHER', 'supporting_roles': ['DRIVER'],
                                    'handoff_role': 'DISPATCHER'}


def test_genai_generates_new_qualitative_language(peer_trips, monkeypatch):
    p = packet(peer_trips)
    assert p.get('evidence'), 'Decision Packet needs traceable evidence IDs'
    output = generated(['E_idle_minutes'])
    intercept(monkeypatch, output, {})
    result = narrate(p, 'DRIVER', use_llm=True)
    assert result['mode'] == 'openai_structured_generation'
    for key, value in output.items(): assert result[key] == value


def test_genai_cannot_reassign_calculated_owner(peer_trips, monkeypatch):
    p = packet(peer_trips)
    assert p['primary_owner'] == 'DISPATCHER'
    output = generated(['E_idle_minutes'])
    output['handoff_role'] = 'DRIVER'
    captured = {}
    intercept(monkeypatch, output, captured)
    result = narrate(p, 'DRIVER', use_llm=True)
    assert result['mode'] == 'deterministic_template'
    assert result['handoff_role'] == 'DISPATCHER'
    assert 'fallback_reason' in result


@pytest.mark.parametrize('claim', ['可節省 99 L', '可節省九十九公升', 'The truck saves ninety liters', '引擎故障已確診', '駕駛操作太差'])
def test_genai_rejects_numbers_diagnoses_and_blame(peer_trips, monkeypatch, claim):
    p = packet(peer_trips)
    output = generated(['E_idle_minutes'])
    output['evidence_summary'] = claim
    intercept(monkeypatch, output, {})
    result = narrate(p, 'DRIVER', use_llm=True)
    assert result['mode'] == 'deterministic_template'


def test_ml_uses_evidence_and_training_fold_baselines(peer_trips):
    frames = []
    for month in range(4):
        f = peer_trips.copy()
        f.trip_id = f.trip_id + f'-{month}'
        f.start_time = f.start_time + pd.Timedelta(days=month*35)
        f.end_time = f.end_time + pd.Timedelta(days=month*35)
        frames.append(f)
    trips = pd.concat(frames, ignore_index=True).drop(columns=MOCK_FIELDS)
    predictions, report = evaluate_optional_ml(trips)
    assert report['status'] == 'evaluated'
    assert {'baseline_a_prediction_l', 'baseline_b_prediction_l', 'fold'} <= set(predictions)
    assert {'baseline_a_mae_l', 'baseline_b_mae_l', 'relative_improvement_vs_a', 'relative_improvement_vs_b'} <= set(report)
    assert set(report['numeric_features'] + report['categorical_features']).isdisjoint(MOCK_FIELDS)
    assert report['time_holdout']['status'] == 'evaluated'
    assert report['time_holdout']['train_end'] < report['time_holdout']['test_start']
    assert predictions.groupby(trips.enabledCode).fold.nunique().eq(1).all()


def test_mock_set_is_minimal():
    assert set(MOCK_RULES) == {'driver_id','task_type','payload_ratio','traffic_level','delivery_window','stop_purpose','mock_generation_rule','is_mock'}


def test_pipeline_rejects_nonexistent_phases(tmp_path):
    from scripts.build_pipeline import build
    with pytest.raises(ValueError, match='1.*5'):
        build('missing.xlsx', tmp_path, phase=7)
