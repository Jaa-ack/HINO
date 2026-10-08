from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('page,title', [
    ('journey','資料旅程'),('fleet','車隊總覽'),('trip','行程探索'),
    ('coach','駕駛節能教練'),('manager','管理行動中心'),('assumptions','資料與假設')])
def test_six_pages_render_real_processed_data(page,title):
    if not (ROOT/'data/processed/demo_cases.json').exists():
        pytest.skip('Run build_pipeline.py before full UI integration checks')
    app = AppTest.from_string(f"from src.ui import render\nrender('{page}')", default_timeout=60).run()
    assert not app.exception
    assert any(title in t.value for t in app.title), f'Missing page title: {title}'


def test_demo_case_switch_and_coach_replay_controls():
    if not (ROOT/'data/processed/demo_cases.json').exists():
        pytest.skip('Run pipeline first')
    app = AppTest.from_string("from src.ui import render\nrender('trip')", default_timeout=60).run()
    assert app.selectbox[0].options[0].startswith('示範案例 A')
    app.selectbox[0].select(app.selectbox[0].options[1]).run()
    assert not app.exception
    import json
    cases = json.loads((ROOT/'data/processed/demo_cases.json').read_text())
    packets = json.loads((ROOT/'data/processed/decision_packets.json').read_text())
    if cases['B']['trip_id']:
        assert app.metric[0].value == f"{packets[cases['B']['trip_id']]['actual_fuel_l']:,.1f} L"
    app.radio[0].set_value('離線 GPS 座標圖').run()
    assert not app.exception
    coach = AppTest.from_string("from src.ui import render\nrender('coach')", default_timeout=60).run()
    coach.radio[0].set_value('歷史回放').run()
    assert not coach.exception
    assert len(coach.slider) == 1
    coach.slider[0].set_value(0).run()
    assert not coach.exception
    coach.radio[0].set_value('行程後').run()
    assert not coach.exception
    assert len(coach.metric) == 4


def test_reviewer_facing_controls_have_chinese_labels():
    if not (ROOT/'data/processed/demo_cases.json').exists():
        pytest.skip('Run pipeline first')
    fleet = AppTest.from_string("from src.ui import render\nrender('fleet')", default_timeout=60).run()
    assert not fleet.exception
    assert fleet.metric[0].label == '總行駛里程'
    assert all(any('\u4e00' <= character <= '\u9fff' for character in metric.label) for metric in fleet.metric)
    manager = AppTest.from_string("from src.ui import render\nrender('manager')", default_timeout=60).run()
    assert not manager.exception
    assert any(box.label == '負責角色' for box in manager.selectbox)
    assumptions = AppTest.from_string("from src.ui import render\nrender('assumptions')", default_timeout=60).run()
    assert not assumptions.exception
    assert {'Current Data', 'Event Reference', 'Production Data Capability', 'Methodology',
            'Model Validation', 'Pilot Validation'} <= {tab.label for tab in assumptions.tabs}


def test_model_validation_explains_result_in_chinese():
    if not (ROOT/'data/processed/model_report.json').exists():
        pytest.skip('Run pipeline first')
    app = AppTest.from_string("from src.ui import render\nrender('assumptions')", default_timeout=60).run()
    assert not app.exception
    import json
    report = json.loads((ROOT/'data/processed/model_report.json').read_text())
    if report['status'] == 'evaluated':
        assert any('選配模型已完成驗證：隨機森林回歸' in item.value for item in app.markdown)
    else:
        assert any('選配模型' in item.value for item in app.info)
    assert any('原始模型報告' in item.label for item in app.expander)
