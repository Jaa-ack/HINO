import json
import pandas as pd
import pytest

from src.clean import clean_telemetry
from src.events import normalize_events
from src.trips import aggregate_trips


def build(raw):
    return aggregate_trips(clean_telemetry(raw), normalize_events(raw))


def test_trip_key_unique(raw_sample):
    trips = build(raw_sample)
    assert len(trips) == 2
    assert trips.trip_id.is_unique
    assert trips.journeyCode.nunique() == 1


def test_trip_fuel_nonnegative(raw_sample):
    trips = build(raw_sample).set_index("enabledCode")
    assert trips.loc["A", "trip_fuel_l"] == pytest.approx(1.0)
    assert (trips.trip_fuel_l >= 0).all()
    assert trips.loc["A", "fuel_reset_flag"]


def test_trip_distance_nonnegative(raw_sample):
    trips = build(raw_sample).set_index("enabledCode")
    assert trips.loc["A", "trip_distance_km"] == pytest.approx(2.0)
    assert (trips.trip_distance_km >= 0).all()
    assert trips.loc["A", "mileage_reset_flag"]


def test_timestamp_gap_is_unobserved_not_idling(raw_sample):
    t = build(raw_sample).set_index("enabledCode").loc["A"]
    assert t.duration_minutes == 12
    assert t.idle_minutes == 1
    assert t.driving_minutes == 1
    assert t.unobserved_minutes == 10
    assert t.large_timestamp_gap_flag
    assert t.idle_ratio == .5


def test_event_payload_lossless_and_duplicate_reports_retained(raw_sample):
    raw = pd.concat([raw_sample, raw_sample.iloc[:1]], ignore_index=True)
    events = normalize_events(raw)
    assert len(events) == 2
    assert json.loads(events.raw_payload_json.iloc[0])["event[0].info.custom"] == "preserve me"
    assert events["info.dtcCodes[0]"].iloc[0] == "P0104"
    trips = build(raw).set_index("enabledCode")
    assert trips.loc["A", "rapid_accel_event_count"] == 1


def test_optional_missing_columns_are_unknown_not_zero(raw_sample):
    raw = raw_sample[["enabledCode", "journeyCode", "time", "source_row"]]
    t = build(raw)
    assert t.trip_fuel_l.isna().all()
    assert t.trip_distance_km.isna().all()
    assert t.missing_gps_flag.all()
    assert t.idle_ratio.isna().all()


def test_duplicate_timestamp_does_not_double_count_and_invalid_key_quarantined(raw_sample):
    raw = pd.concat([raw_sample, raw_sample.iloc[:1].assign(enabledCode=None)], ignore_index=True)
    cleaned = clean_telemetry(raw)
    assert len(cleaned) == len(raw)
    assert cleaned.invalid_key_flag.sum() == 1
    assert len(aggregate_trips(cleaned, normalize_events(raw))) == 2
