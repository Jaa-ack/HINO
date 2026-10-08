import json
import pandas as pd
import pytest

from src.recommendations import decision_packet, recommend
from src.llm import narrate
from src.demo_cases import select_demo_cases


def sample_trip():
    return dict(trip_id='A::1',enabledCode='A',journeyCode='1', trip_fuel_l=20.,expected_fuel_l=16., benchmark_gap_l=4.,benchmark_gap_pct=20.,
        idle_context_priority_pct=60.,rpm_priority_pct=25.,engine_load_priority_pct=15.,benchmark_quality="MEDIUM",
        vehicle_health_flag=False,vehicle_residual_ratio=None,dtc_event_count=0,idle_minutes=18.,rpm_above_2500_ratio=.2,
        peer_trip_count=7,peer_vehicle_count=2,benchmark_level='L2',data_quality_score=100,route_id='route',
        opportunity_status='OBSERVED_COMPARISON',stop_purpose='warehouse_wait',driver_id='MOCK-A',payload_ratio=.5,
        traffic_level='high',task_type='urban_delivery',consecutive_anomaly_trips=0,health_peer_count=0,
        start_time=pd.Timestamp('2025-01-01'),end_time=pd.Timestamp('2025-01-01 02:00'))


def test_decision_packet_numbers():
    trip = sample_trip()
    p = decision_packet(trip)
    assert p['actual_fuel_l'] == trip['trip_fuel_l']
    assert p['benchmark_gap_l'] == trip['benchmark_gap_l']
    assert sum(c['priority_pct'] for c in p['improvement_levers']) == pytest.approx(100.)
    assert '非因果證明' in p['disclaimer']
    assert all(set(e) == {'evidence_id','source_type','field','value','unit'} for e in p['evidence'])
    assert p['mock_context']['source_type'] == 'MOCK'
    json.dumps(p,allow_nan=False)
    for persona in ['DRIVER','DISPATCHER','FLEET_MANAGER','MAINTENANCE']:
        rec = recommend(p,persona)
        assert rec['next_action']
        assert rec['handoff_role'] in ['DRIVER','DISPATCHER','FLEET_MANAGER','MAINTENANCE']
        assert rec['mode'] == 'deterministic_template'
        assert '引擎故障' not in str(rec)


def test_missing_evidence_is_explicit_and_llm_offline_works():
    p = decision_packet({'trip_id':'unknown','trip_fuel_l':float('nan')})
    assert p['actual_fuel_l'] is None
    result = narrate(p,'DRIVER',use_llm=False)
    assert '目前資料不足以判斷' in result['evidence_summary']
    assert result['mode'] == 'deterministic_template'
    assert result['packet']['trip_id'] == 'unknown'


def test_demo_cases_do_not_invent_absent_anomaly():
    trip = sample_trip()
    cases = select_demo_cases(pd.DataFrame([trip]))
    assert cases['A']['trip_id'] == 'A::1'
    assert cases['C']['trip_id'] is None
    assert '不足' in cases['C']['reason']


def test_demo_cases_match_actionable_role_instead_of_largest_weak_gap():
    base = sample_trip()
    trips = pd.DataFrame([
        {**base, 'trip_id': 'weak', 'benchmark_quality': 'LOW', 'benchmark_gap_l': 100},
        {**base, 'trip_id': 'idle', 'benchmark_gap_l': 2, 'idle_context_priority_pct': 100,
         'rpm_priority_pct': 0, 'engine_load_priority_pct': 0},
        {**base, 'trip_id': 'rpm', 'benchmark_gap_l': 1, 'idle_context_priority_pct': 0,
         'rpm_priority_pct': 100, 'engine_load_priority_pct': 0},
        {**base, 'trip_id': 'load', 'benchmark_gap_l': 10, 'idle_context_priority_pct': 0,
         'rpm_priority_pct': 0, 'engine_load_priority_pct': 100},
    ])
    cases = select_demo_cases(trips)
    assert cases['A']['trip_id'] == 'idle'
    assert cases['B']['trip_id'] == 'rpm'


def test_weak_comparison_does_not_become_driver_or_dispatch_demo():
    cases = select_demo_cases(pd.DataFrame([{**sample_trip(), 'benchmark_quality': 'LOW'}]))
    assert cases['A']['trip_id'] is None
    assert cases['B']['trip_id'] is None
    assert '不足' in cases['A']['reason']


@pytest.mark.parametrize('payload', [[], {'output':[{'content':[{'type':'output_text','text':'{"summary":"節省 999 L","actions":["更換引擎"]}'}]}]}])
def test_optional_llm_invalid_shape_or_invented_claim_falls_back(monkeypatch,payload):
    import src.llm as llm
    monkeypatch.setenv('OPENAI_API_KEY','test-placeholder')
    monkeypatch.setenv('OPENAI_MODEL','test-model')
    monkeypatch.setenv('ECOPILOT_ENABLE_LLM','true')
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return payload
    monkeypatch.setattr(llm.requests,'post',lambda *args,**kwargs:Response())
    result = narrate(decision_packet(sample_trip()),'DRIVER',use_llm=True)
    assert result['mode'] == 'deterministic_template'
    assert '999' not in result['evidence_summary']
