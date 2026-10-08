from src.schema import build_dictionary


def test_source_type_valid():
    d = build_dictionary(['enabledCode', 'trip_id', 'trip_fuel_l', 'driver_id', 'expected_fuel_l', 'vehicle_health_flag'])
    assert set(d.source_type) == {'RAW', 'DERIVED', 'MOCK'}
    assert set(d.column) == {'enabledCode', 'trip_id', 'trip_fuel_l', 'driver_id', 'expected_fuel_l', 'vehicle_health_flag'}
    for field in ['description','used_for','calculation','limitations']:
        assert d[field].str.len().gt(0).all()
    assert d.set_index('column').loc['trip_fuel_l','source_type'] == 'DERIVED'
