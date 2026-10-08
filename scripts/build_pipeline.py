"""Run phases in order. Reuse raw Parquet only when source checksum matches."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd

from src.clean import clean_telemetry
from src.events import normalize_events
from src.ingest import find_workbook, inspect_workbook
from src.trips import aggregate_trips
from src.utils import ROOT, sha256, write_json, write_processed_parquet
from src.config import ANALYSIS_VERSION, SOURCE_CONTRACT_VERSION, EVENT_REFERENCE_VERSION


def build(input_path=None, output_dir=ROOT, phase=5, force=False, use_ml=False):
    if phase not in range(1, 6):
        raise ValueError("Pipeline phase must be 1–5")
    root = Path(output_dir).resolve()
    source = Path(input_path or find_workbook(root)).resolve()
    before = sha256(source)
    for directory in ["data/interim", "data/processed", "data/mock", "docs"]:
        (root / directory).mkdir(parents=True, exist_ok=True)
    interim, processed = root / "data/interim", root / "data/processed"
    manifest_path = interim / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    if force or manifest.get("sha256") != before or not (interim / "raw_snapshot.parquet").exists():
        inspect_workbook(source, root)
    else:
        print("Phase 1: source checksum verified; using raw Parquet cache", flush=True)
    from src.ingest import write_profile_markdown
    write_profile_markdown(json.loads((root / "docs/data_profile.json").read_text()), root / "docs/data_profile.md")
    if phase == 1:
        assert sha256(source) == before, "Source workbook was modified"
        write_json(processed / "pipeline_summary.json", {"phase": 1, "evidence_mode": "PRIMARY_EVIDENCE_MODE",
                                                     "analysis_version": ANALYSIS_VERSION,
                                                     "source_contract_version": SOURCE_CONTRACT_VERSION,
                                                     "event_reference_version": EVENT_REFERENCE_VERSION,
                                                     "source_sha256": before})
        return
    raw = pd.read_parquet(interim / "raw_snapshot.parquet")
    profile = json.loads((root / "docs/data_profile.json").read_text())
    from src.reference import build_reference, EVENT_FILE
    if (root / 'data/reference' / EVENT_FILE).exists():
        build_reference(root, profile['columns'], before)
    confirmed_units = {k: v["unit"] for k, v in profile["columns"].items()}
    telemetry = clean_telemetry(raw, confirmed_units=confirmed_units)
    events = normalize_events(raw)
    telemetry.to_parquet(interim / "telemetry.parquet", index=False, compression="zstd")
    events.to_parquet(interim / "events.parquet", index=False, compression="zstd")
    trips = aggregate_trips(telemetry, events)
    write_processed_parquet(trips, processed / "trips.parquet")
    assert trips.trip_id.is_unique
    assert len(telemetry) == len(raw)
    if phase >= 3:
        from src.mock_context import generate_mock_context
        context = generate_mock_context(trips, seed=42)
        context.to_parquet(root / "data/mock/trip_context_mock.parquet", index=False)
        assert not (set(context) - {"trip_id"}) & set(trips), "Mock columns must never overwrite real features"
        if phase == 3:
            trips = trips.merge(context, on="trip_id", how="left", validate="one_to_one")
            write_processed_parquet(trips, processed / "trips_enriched.parquet")
    if phase >= 4:
        from src.benchmarks import build_benchmarks
        from src.attribution import estimate_opportunities, build_hotspots
        from src.fuel_model import analyze_vehicle_health, evaluate_optional_ml
        trips = estimate_opportunities(build_benchmarks(trips))
        trips = analyze_vehicle_health(trips)
        # Attach demo context only AFTER primary benchmark, levers and health.
        evidence_trips = trips
        trips = trips.merge(context, on="trip_id", how="left", validate="one_to_one")
        write_processed_parquet(trips, processed / "trips_enriched.parquet")
        hotspots = build_hotspots(telemetry, trips)
        write_processed_parquet(hotspots, processed / "idle_hotspots.parquet")
        if use_ml:
            try:
                predictions, model_report = evaluate_optional_ml(evidence_trips)
                write_processed_parquet(predictions, processed / "ml_predictions.parquet")
            except Exception as exc:
                (processed / "ml_predictions.parquet").unlink(missing_ok=True)
                model_report = {"status": "failed_optional", "reason": str(exc)}
        else:
            (processed / "ml_predictions.parquet").unlink(missing_ok=True)
            model_report = {"status": "not_requested", "enable": "python scripts/build_pipeline.py --ml"}
        model_report.update(analysis_version=ANALYSIS_VERSION, source_contract_version=SOURCE_CONTRACT_VERSION,
                            event_reference_version=EVENT_REFERENCE_VERSION)
        write_json(processed / "model_report.json", model_report)
        print(f"Phase 4: {trips.expected_fuel_l.notna().sum()} supported benchmarks; {len(hotspots)} idle grids", flush=True)
    if phase >= 5:
        from src.recommendations import decision_packet, recommend, PERSONAS, action_center
        from src.demo_cases import select_demo_cases
        from src.trips import grid_cell
        idle = telemetry.loc[telemetry.is_canonical & telemetry.status.eq("idling") & telemetry.interval_seconds.gt(0) & telemetry.latitude.notna()].copy()
        idle["cell"] = [grid_cell(lat, lon, 3) for lat, lon in zip(idle.latitude, idle.longitude)]
        ranked = idle.groupby(["trip_id", "cell"]).interval_seconds.sum().reset_index().sort_values("interval_seconds", ascending=False)
        hotspots_by_trip = ranked.drop_duplicates("trip_id").set_index("trip_id").cell.to_dict()
        packets = [decision_packet(t, "GRID-" + hotspots_by_trip[t.trip_id] if t.trip_id in hotspots_by_trip else None) for _, t in trips.iterrows()]
        write_json(processed / "decision_packets.json", {p["trip_id"]: p for p in packets})
        write_json(processed / "recommendations.json", {p["trip_id"]: {role: recommend(p, role) for role in PERSONAS} for p in packets})
        write_json(processed / "demo_cases.json", select_demo_cases(trips))
        write_processed_parquet(action_center(trips), processed / "actions.parquet")
        print(f"Phase 5: {len(packets)} decision packets; four personas each", flush=True)
    assert sha256(source) == before, "Source workbook was modified"
    if phase >= 3:
        from src.schema import write_dictionary
        write_dictionary(trips, root, json.loads((root / "docs/data_profile.json").read_text()))
    summary = {"phase": phase, "evidence_mode": "PRIMARY_EVIDENCE_MODE", "analysis_version": ANALYSIS_VERSION,
               "source_contract_version": SOURCE_CONTRACT_VERSION, "event_reference_version": EVENT_REFERENCE_VERSION,
               "raw_rows": len(raw), "trips": len(trips), "vehicles": trips.enabledCode.nunique(),
               "events": len(events), "eligible_trips": int(trips.benchmark_eligible.sum()), "source_sha256": before,
               "quarantined_rows": int((telemetry.invalid_key_flag | telemetry.invalid_timestamp_flag).sum())}
    write_json(processed / "pipeline_summary.json", summary)
    print(summary, flush=True)
    return trips


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    parser.add_argument("--phase", type=int, choices=range(1, 6), default=5)
    parser.add_argument("--force", action="store_true", help="Re-read Excel instead of the verified Parquet cache")
    parser.add_argument("--ml", action="store_true", help="Also evaluate optional ML model")
    args = parser.parse_args()
    build(args.input, args.output_dir, args.phase, args.force, args.ml)
