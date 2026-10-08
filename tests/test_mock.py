import pandas as pd

from src.clean import clean_telemetry
from src.events import normalize_events
from src.trips import aggregate_trips
from src.mock_context import generate_mock_context


def test_mock_reproducible(raw_sample):
    trips = aggregate_trips(clean_telemetry(raw_sample), normalize_events(raw_sample))
    before = trips.copy(deep=True)
    a = generate_mock_context(trips)
    b = generate_mock_context(trips.iloc[::-1])
    pd.testing.assert_frame_equal(a.sort_values('trip_id').reset_index(drop=True), b.sort_values('trip_id').reset_index(drop=True))
    pd.testing.assert_frame_equal(trips, before)
    assert a.payload_ratio.between(0, 1).all()
    assert a.is_mock.all()
    assert not {'trip_fuel_l','trip_distance_km'} & set(a.columns)
    assert 'seed=42' in a.mock_generation_rule.iloc[0]
