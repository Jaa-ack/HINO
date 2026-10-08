from streamlit.testing.v1 import AppTest


def test_fleet_distinguishes_cross_vehicle_hotspots_and_operational_checks():
    app = AppTest.from_string("from src.ui import render\nrender('fleet')", default_timeout=60).run()
    assert not app.exception
    assert any(item.value == "跨車怠速／停留熱點" for item in app.subheader)
    assert any(item.label == "選擇跨車熱點" for item in app.selectbox)
    labels = {item.label for item in app.metric}
    assert {"不同車輛", "涉及行程", "觀測怠速"} <= labels
    assert any("PTO" in item.value and "到站窗口" in item.value for item in app.info)
    assert any("駕駛識別" in item.value for item in app.caption)
