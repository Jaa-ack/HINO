from datetime import date, datetime, timedelta

import pytest
from streamlit.testing.v1 import AppTest

from src.utils import ROOT


def sample_action(problem="怠速／停留情境優先核對"):
    return {
        "trip_id": "vehicle::trip-1", "problem": problem,
        "primary_owner": "DISPATCHER", "supporting_roles": ["DRIVER", "FLEET_MANAGER"],
        "evidence": "怠速 12 分鐘；停留用途待核對",
    }


def test_action_record_persists_and_reopens_without_claiming_outcome(tmp_path):
    from src.action_tracking import ActionStore

    path = tmp_path / "actions.sqlite3"
    saved = ActionStore(path).save(sample_action(), measures="核對卸貨預約並調整到站時間", status="執行中",
                                   follow_up_date=date(2026, 10, 13), demonstration=True)
    reopened = ActionStore(path).load(sample_action(), demonstration=True)
    assert reopened == saved
    assert reopened["measures"] == "核對卸貨預約並調整到站時間"
    assert reopened["status"] == "執行中"
    assert reopened["follow_up_date"] == "2026-10-13"
    assert reopened["verification"] == "待後續可比較行程驗證"


def test_record_timestamp_uses_taipei_timezone(tmp_path):
    from src.action_tracking import ActionStore

    saved = ActionStore(tmp_path / "actions.sqlite3").save(
        sample_action(), measures="核對卸貨時窗", status="已採納",
        follow_up_date=date(2026, 10, 13), demonstration=True)
    assert datetime.fromisoformat(saved["updated_at"]).utcoffset() == timedelta(hours=8)
    assert saved["verification"] == "待後續可比較行程驗證"


def test_action_key_is_stable_and_separates_problems_on_same_trip(tmp_path):
    from src.action_tracking import ActionStore, action_key

    first = sample_action()
    second = sample_action("車況檢查訊號")
    assert action_key(first) == action_key(dict(first, evidence="新增核對證據"))
    assert action_key(first) != action_key(second)
    store = ActionStore(tmp_path / "actions.sqlite3")
    store.save(first, measures="核對卸貨預約", status="已採納", follow_up_date=date(2026, 10, 13), demonstration=False)
    store.save(second, measures="安排車況檢查", status="待驗證", follow_up_date=date(2026, 10, 14), demonstration=False)
    store.save(first, measures="調整卸貨預約", status="執行中", follow_up_date=date(2026, 10, 15), demonstration=False)
    assert len(store.records(demonstration=False)) == 2
    assert store.load(first, demonstration=False)["measures"] == "調整卸貨預約"
    assert store.load(second, demonstration=False)["measures"] == "安排車況檢查"


def test_demonstration_records_are_isolated_from_real_pilot(tmp_path):
    from src.action_tracking import ActionStore

    store = ActionStore(tmp_path / "actions.sqlite3")
    store.save(sample_action(), measures="操作示範：核對卸貨", status="已採納",
               follow_up_date=date(2026, 10, 13), demonstration=True)
    assert store.load(sample_action(), demonstration=False) is None
    assert store.records(demonstration=False) == []
    store.save(sample_action(), measures="實際試行核對", status="待核對",
               follow_up_date=date(2026, 10, 13), demonstration=False)
    assert store.load(sample_action(), demonstration=True)["measures"] == "操作示範：核對卸貨"
    assert store.load(sample_action(), demonstration=False)["measures"] == "實際試行核對"


@pytest.mark.parametrize("measures", ["", "  \n  "])
def test_empty_measures_are_rejected_without_saving(tmp_path, measures):
    from src.action_tracking import ActionStore

    store = ActionStore(tmp_path / "actions.sqlite3")
    with pytest.raises(ValueError, match="執行措施"):
        store.save(sample_action(), measures=measures, status="待核對",
                   follow_up_date=date(2026, 10, 13), demonstration=True)
    assert store.records(demonstration=True) == []


def test_manager_shows_parquet_supporting_roles_and_saves_reloadable_demo(tmp_path, monkeypatch):
    if not (ROOT / "data/processed/actions.parquet").exists():
        pytest.skip("Run pipeline first")
    monkeypatch.setenv("ECOPILOT_ACTION_DB", str(tmp_path / "actions.sqlite3"))
    app = AppTest.from_string("from src.ui import render\nrender('manager')", default_timeout=60).run()
    app.selectbox[0].select("DISPATCHER").run()
    assert not app.exception
    # A Parquet list column is ndarray; the existing list/tuple-only renderer loses it.
    table = next(frame.value for frame in app.dataframe if "Supporting Roles" in frame.value.columns)
    assert table["Supporting Roles"].str.contains("駕駛").any()
    assert {"行動工作台", "全部待辦", "車況證據"} <= {tab.label for tab in app.tabs}
    assert app.checkbox(key="action_demo_scope").value is True
    app.button(key="save_action").click().run()
    assert any("執行措施" in message.value for message in app.error)
    app.text_area[0].set_value("先向客戶核對卸貨時窗，再調整到站時間")
    next(box for box in app.selectbox if box.label == "追蹤狀態").select("執行中")
    app.button(key="save_action").click().run()
    assert not app.exception
    assert any("操作示範紀錄已保存" in message.value for message in app.success)
    reopened = AppTest.from_string("from src.ui import render\nrender('manager')", default_timeout=60).run()
    reopened.selectbox[0].select("DISPATCHER").run()
    assert reopened.text_area[0].value == "先向客戶核對卸貨時窗，再調整到站時間"
    assert next(box for box in reopened.selectbox if box.label == "追蹤狀態").value == "執行中"
    assert any("待後續可比較行程驗證" in message.value for message in reopened.info)
