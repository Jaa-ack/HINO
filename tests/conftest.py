import pandas as pd
import pytest


@pytest.fixture
def raw_sample():
    return pd.DataFrame({
        "enabledCode": ["A"] * 4 + ["B"] * 2,
        "journeyCode": ["001"] * 6,
        "Type": ["300"] * 6,
        "time": ["2025-01-01 00:00:00", "2025-01-01 00:01:00", "2025-01-01 00:02:00",
                 "2025-01-01 00:12:00", "2025-01-01 01:00:00", "2025-01-01 01:01:00"],
        "carStatus": ["2", "1", "2", "0", "1", "0"],
        "can.totalMileage": ["100", "101", "5", "6", "1", "2"],
        "can.engine.totalFuelUsed": ["10", "10.5", "1", "1.5", "10", "10.5"],
        "gps.longitude": ["121"] * 6, "gps.latitude": ["25"] * 6,
        "can.canSpeed": ["0", "60", "0", "0", "60", "0"],
        "can.engine.rpm": ["800", "2700", "800", "0", "1600", "0"],
        "can.engine.engineLoad": ["10", "95", "10", "0", "50", "0"],
        "event[0].type": ["6", None, None, None, None, None],
        "event[0].info.custom": ["preserve me", None, None, None, None, None],
        "event[0].info.dtcCodes[0]": ["P0104", None, None, None, None, None],
        "source_row": list(range(2, 8)),
    })


@pytest.fixture
def peer_trips():
    records = []
    for i in range(18):
        records.append(dict(trip_id=f"t{i}", enabledCode=f"V{i//3}", journeyCode=str(i), vehicle_type="300",
          start_time=pd.Timestamp("2025-01-01") + pd.Timedelta(days=i % 3), end_time=pd.Timestamp("2025-01-01") + pd.Timedelta(days=i % 3, minutes=60),
          trip_distance_km=40., trip_fuel_l=20. if i < 3 else 10., duration_minutes=60., benchmark_eligible=True,
          route_id="same", distance_bin="20–50", time_of_day="day", payload_ratio=.5, traffic_level="medium",
          task_type="urban_delivery", weather="clear", idle_ratio=.3 if i < 3 else .1, rpm_above_2500_ratio=.3 if i < 3 else .1,
          engine_load_above_90_ratio=.3 if i < 3 else .1, rapid_accel_event_count=4 if i < 3 else 1, rapid_decel_event_count=1, avg_speed=40.,
          idle_minutes=18. if i < 3 else 6., data_quality_score=100, stop_purpose="warehouse_wait", is_mock=True,
          dtc_event_count=0, origin_cell="25,121", fuel_l_per_100km=50. if i<3 else 25.))
    return pd.DataFrame(records)
