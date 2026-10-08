"""Phase 1: inspect without building the prototype."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ingest import find_workbook, inspect_workbook
from src.utils import ROOT

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    result = inspect_workbook(args.input or find_workbook(), ROOT)
    print({k: result[k] for k in ["row_count", "column_count", "vehicle_count", "journey_count", "trip_count", "time_range"]})
