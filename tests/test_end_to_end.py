import hashlib
import json

import openpyxl
import pandas as pd

from scripts.build_pipeline import build


def test_no_raw_overwrite(tmp_path):
    path = tmp_path / 'source.xlsx'
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = 'output'
    sheet.append(['enabledCode','journeyCode','time','Type','carStatus','can.totalMileage','can.engine.totalFuelUsed'])
    for i in range(6):
        sheet.append(['V','001',f'2025-01-01 00:0{i}:00','300','1',100+i,10+i*.5])
    book.save(path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    out = tmp_path / 'build'
    build(path, out, phase=5)
    a = pd.read_parquet(out/'data/processed/trips_enriched.parquet')
    # This workbook has no field mapping: do not invent L / km units.
    assert a.trip_fuel_l.isna().all()
    assert a.trip_distance_km.isna().all()
    packets = json.loads((out/'data/processed/decision_packets.json').read_text())
    build(path, out, phase=5)
    b = pd.read_parquet(out/'data/processed/trips_enriched.parquet')
    pd.testing.assert_frame_equal(a,b)
    assert len(packets) == 1
    assert packets['V::001']['expected_fuel_l'] is None
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_real_artifacts_are_complete_and_consistent():
    from src.utils import ROOT, sha256
    import pytest
    manifest_path = ROOT/'data/interim/source_manifest.json'
    if not (ROOT/'data/processed/decision_packets.json').exists():
        pytest.skip('Run pipeline first for real-data integration')
    manifest = json.loads(manifest_path.read_text())
    source = ROOT / manifest['source_path']
    if not source.exists():
        from src.ingest import find_workbook
        source = find_workbook()
    assert sha256(source) == manifest['sha256']
    trips = pd.read_parquet(ROOT/'data/processed/trips_enriched.parquet')
    dictionary = pd.read_parquet(ROOT/'data/processed/data_dictionary.parquet')
    assert set(dictionary.column) == set(trips.columns)
    assert trips.trip_id.is_unique
    assert trips.trip_fuel_l.dropna().ge(0).all()
    assert trips.trip_distance_km.dropna().ge(0).all()
    packets = json.loads((ROOT/'data/processed/decision_packets.json').read_text())
    for t in trips.itertuples(index=False):
        packet = packets[t.trip_id]
        if pd.notna(t.trip_fuel_l):
            assert packet['actual_fuel_l'] == t.trip_fuel_l
        if pd.notna(t.benchmark_gap_l):
            assert packet['benchmark_gap_l'] == t.benchmark_gap_l
        priorities = packet['improvement_levers']
        if priorities:
            assert abs(sum(c['priority_pct'] for c in priorities)-100) < 1e-8
    hotspots = pd.read_parquet(ROOT/'data/processed/idle_hotspots.parquet')
    assert hotspots.total_idle_minutes.sum() <= trips.idle_minutes.sum() + 1e-8
    assert all(c['trip_id'] is None or c['trip_id'] in packets for c in json.loads((ROOT/'data/processed/demo_cases.json').read_text()).values())


def test_no_generated_artifact_claims_causality():
    from src.utils import ROOT
    trips = pd.read_parquet(ROOT/'data/processed/trips_enriched.parquet')
    assert not any('saving_l' in c or 'anomaly_score' in c for c in trips.columns)
    for file in ['decision_packets.json', 'recommendations.json', 'demo_cases.json']:
        text = (ROOT/'data/processed'/file).read_text()
        for forbidden in ['estimated_saving_l', 'top_causes', '因果歸因', '故障診斷', '已改善', '實際節省', '即時 AI 教練']:
            assert forbidden not in text, f'{file}: {forbidden}'
    actions = pd.read_parquet(ROOT/'data/processed/actions.parquet')
    assert actions.loc[actions.owner.eq('MAINTENANCE'), 'benchmark_gap_l'].isna().all()
