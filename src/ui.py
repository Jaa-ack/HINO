"""Six cached, provenance-aware Streamlit views; never read Excel at runtime."""
from __future__ import annotations

import html
import json
import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pyarrow.parquet as pq
import pydeck as pdk
import streamlit as st

from src.llm import narrate
from src.mock_context import MOCK_RULES
from src.recommendations import FACTOR_NAMES, PERSONAS, recommend, HEALTH_ACTION
from src.utils import ROOT, DISCLAIMER
from src.config import TYPE_DEFINITION, HINO_SERIES, HEALTH_RESIDUAL_THRESHOLD, ANALYSIS_VERSION

GREEN, LIME, AMBER, BLUE = "#247153", "#C9E99A", "#CD9A45", "#548DA7"
PAGES = {"journey": ("01", "資料旅程", "從一筆訊號，走到一個可執行的決策。"),
         "fleet": ("02", "車隊總覽", "看見節能機會，讓整個車隊一起行動。"),
         "trip": ("03", "行程探索", "每個建議，都能回到這一趟的證據。"),
         "coach": ("04", "駕駛節能教練", "把複雜的數據，變成下一個簡單的行動。"),
         "manager": ("05", "管理行動中心", "省油需要協作。為每個問題，找到合適的負責人。"),
         "assumptions": ("06", "資料與假設", "看清楚資料的來源，也看清楚分析的邊界。")}
SOURCE_LABELS = {"RAW": "原始資料 RAW", "DERIVED": "衍生資料 DERIVED", "MOCK": "模擬資料 MOCK"}
PERSONA_LABELS = {"DRIVER": "駕駛", "DISPATCHER": "調度人員", "FLEET_MANAGER": "車隊管理者", "MAINTENANCE": "維修人員"}
CASE_LABELS = {"A": "怠速／停留情境待核對", "B": "操作型態待核對案例", "C": "車況檢查訊號"}
BENCHMARK_LABELS = {"L1": "同系列、路線、里程區間、時段（L1）", "L2": "同系列、里程區間、時段（L2）", "L3": "同系列、里程區間（L3）"}
MOCK_VALUE_LABELS = {"urban_delivery": "市區配送", "intercity": "跨城運輸", "depot_transfer": "車庫間調度",
                     "low": "低", "medium": "中", "high": "高", "clear": "晴朗", "rain": "下雨",
                     "delivery": "配送", "pickup": "取貨", "warehouse_wait": "倉儲等待", "rest": "休息", "unknown": "未知"}
FIELD_LABELS = {"enabledCode": "車輛識別碼", "journeyCode": "行程編號", "vehicle_type": "HINO 系列（Type）",
                "trip_distance_km": "行程里程（公里）", "trip_fuel_l": "行程燃油（公升）", "idle_minutes": "怠速時間（分鐘）",
                "route_id": "路線格網", "driver_id": "模擬駕駛代碼", "payload_ratio": "模擬載重比例",
                "traffic_level": "模擬交通狀況", "stop_purpose": "模擬停靠目的", "data_quality_score": "資料品質分數"}
FLAG_LABELS = {"fuel_reset_flag": "燃油計數器重設", "mileage_reset_flag": "里程計數器重設",
               "fuel_missing_flag": "燃油資料缺漏", "mileage_missing_flag": "里程資料缺漏",
               "large_timestamp_gap_flag": "時間間隔過大", "missing_gps_flag": "GPS 資料缺漏",
               "low_sample_count_flag": "樣本筆數偏少", "duplicate_timestamp_flag": "時間戳記重複",
               "gps_speed_conflict_flag": "GPS 與 CAN 速度不一致", "implausible_mileage_flag": "里程跳點",
               "can_error_flag": "CAN 狀態異常", "can_status_unknown_flag": "CAN 狀態未知", "type_conflict_flag": "車型類別不一致",
               "vehicle_health_flag": "車況檢查訊號"}


def display_source(kind):
    return SOURCE_LABELS.get(kind, kind)


def display_value(value):
    return MOCK_VALUE_LABELS.get(str(value), str(value))


def localized_dictionary(dictionary):
    view = dictionary.copy()
    view["source_type"] = view.source_type.map(display_source)
    return view.rename(columns={"column": "原始欄位代碼", "description": "欄位定義", "source_type": "資料來源",
                                "used_for": "用途", "calculation": "計算方式", "limitations": "限制"})

CSS = """
<style>
.block-container{max-width:1440px;padding-top:3rem;padding-bottom:3rem}
h1{font-size:2.2rem!important;letter-spacing:-.065rem;font-weight:700!important}
h2,h3{letter-spacing:-.025rem}
[data-testid="stSidebar"]{border-right:1px solid #E2E9DF;background:#fff}
[data-testid="stSidebarNav"]{padding-top:.6rem}
[data-testid="stMetric"]{background:#fff;border:1px solid #E2E9DF;border-radius:14px;padding:15px 12px;min-height:115px}
[data-testid="stMetricLabel"]{color:#62776B;font-size:.8rem}
[data-testid="stMetricValue"]{font-size:1.45rem;font-weight:650}
[data-testid="stMetricLabel"] p{white-space:normal!important;font-size:.73rem}
[data-testid="stVerticalBlockBorderWrapper"]>div{border-color:#E2E9DF!important;border-radius:15px!important}
.eyebrow{font-size:.68rem;letter-spacing:.14em;font-weight:700;color:#6C8376;margin-bottom:.5rem}
.badge{display:inline-block;padding:3px 9px;border-radius:5px;font-size:.65rem;font-weight:750;letter-spacing:.065em;vertical-align:middle;margin-right:6px}
.raw{background:#E1EDF6;color:#3F728A}.derived{background:#E2EEDB;color:#43703C}.mock{background:#F7ECD7;color:#986929}
.hero{background:linear-gradient(110deg,#153E31,#28563E);color:#fff;border-radius:18px;padding:28px 32px;margin:12px 0 24px;position:relative;overflow:hidden}
.hero::after{content:'';position:absolute;right:-70px;top:-100px;width:340px;height:340px;border:1px solid #9EC28D45;border-radius:50%;box-shadow:0 0 0 40px #8FAB7910,0 0 0 85px #8FAB7908;pointer-events:none}
.hero h2{font-size:1.45rem;color:#fff;margin:4px 0 10px;font-weight:600}
.hero p{font-size:.88rem;color:#D8E5D5;margin:0;max-width:80%}
.hero .eyebrow{color:#C9E99A}.hero .large{font-size:2.9rem;font-weight:650;letter-spacing:-.08rem;line-height:1.3}
.source-note{color:#718174;font-size:.76rem;line-height:1.65;margin:10px 0 18px}
.flow{display:flex;gap:8px;flex-wrap:wrap;margin:22px 0}.flow-step{flex:1;min-width:100px;padding:15px 12px;border:1px solid #DDE6D8;border-radius:10px;background:white;font-size:.8rem;color:#3C5547}.flow-step b{display:block;color:#204D38;margin:7px 0}.flow-step span{color:#88A17F;font-size:.65rem}
.one-action{background:#EFF5E8;border-left:4px solid #68953D;border-radius:8px;padding:22px 25px;margin:12px 0 20px;color:#20442C;font-size:1.14rem;line-height:1.7}
.footnote{border-top:1px solid #DDE5D8;padding-top:18px;margin-top:28px;color:#778274;font-size:.7rem}
</style>
"""


def badge(kind):
    return f'<span class="badge {kind.lower()}">{display_source(kind)}</span>'


def number(v, decimals=1):
    return "—" if v is None or pd.isna(v) else f"{v:,.{decimals}f}"


@st.cache_data(show_spinner=False)
def _table(name, modified):
    return pd.read_parquet(ROOT / name)


def table(name):
    p = ROOT / name
    return _table(name, p.stat().st_mtime_ns)


@st.cache_data(show_spinner=False)
def _json(name, modified):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def document(name):
    return _json(name, (ROOT / name).stat().st_mtime_ns)


@st.cache_data(show_spinner=False)
def trip_telemetry(trip_id, modified):
    columns = ["trip_id", "timestamp", "latitude", "longitude", "speed", "rpm", "engine_load", "status", "interval_seconds", "is_canonical"]
    t = pd.read_parquet(ROOT / "data/interim/telemetry.parquet", filters=[("trip_id", "=", trip_id)], columns=columns)
    return t.loc[t.is_canonical].sort_values("timestamp").reset_index(drop=True)


def telemetry_for(trip_id):
    return trip_telemetry(trip_id, (ROOT / "data/interim/telemetry.parquet").stat().st_mtime_ns)


def chart(fig, height=310):
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Arial, sans-serif", color="#365345", size=12), margin=dict(l=8, r=15, t=15, b=12),
                      height=height, legend=dict(orientation="h", y=1.14, x=0), hoverlabel=dict(bgcolor="white"))
    fig.update_xaxes(gridcolor="#E9EFE4")
    fig.update_yaxes(gridcolor="#E9EFE4")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def source_note(text):
    st.markdown(f'<div class="source-note">{text}</div>', unsafe_allow_html=True)


def metrics(items):
    cols = st.columns(len(items))
    for col, (label, value, origin) in zip(cols, items):
        with col:
            st.metric(label, value)
            st.markdown(badge(origin), unsafe_allow_html=True)


def hero(eyebrow, title, detail):
    st.markdown(f'<div class="hero"><div class="eyebrow">{html.escape(eyebrow)}</div><h2>{html.escape(title)}</h2><p>{html.escape(detail)}</p></div>', unsafe_allow_html=True)


def filter_fleet(trips, key):
    with st.sidebar:
        st.divider()
        st.caption("分析範圍")
        types = sorted(trips.vehicle_type.unique())
        selected = st.multiselect("HINO 系列（Type）", types, default=types, format_func=lambda value: HINO_SERIES.get(value, value), key=f"types_{key}")
        dates = st.date_input("行程日期範圍", value=(trips.start_time.min().date(), trips.start_time.max().date()), key=f"dates_{key}")
    out = trips.loc[trips.vehicle_type.isin(selected)]
    if isinstance(dates, (tuple, list)) and len(dates) == 2:
        out = out.loc[out.start_time.dt.date.between(dates[0], dates[1])]
    if out.empty:
        st.info("此篩選沒有行程。請調整HINO 系列（Type）或日期範圍。")
        st.stop()
    return out


def trip_selector(trips, page):
    cases = document("data/processed/demo_cases.json")
    labels = {f"示範案例 {key} · {CASE_LABELS[key]}": c for key, c in cases.items()}
    choice = st.selectbox("快速案例 / 自選行程", list(labels) + ["自選行程"], key=f"case_{page}")
    if choice != "自選行程":
        case = labels[choice]
        if not case["trip_id"]:
            st.info(case["reason"])
            st.stop()
        return trips.loc[trips.trip_id.eq(case["trip_id"])].iloc[0]
    cols = st.columns([1, 1, 2])
    vehicle = cols[0].selectbox("車輛識別碼 · 原始資料", sorted(trips.enabledCode.unique()), key=f"vehicle_{page}")
    v = trips.loc[trips.enabledCode.eq(vehicle)]
    date = cols[1].selectbox("行程日期 · 衍生資料", sorted(v.start_time.dt.date.unique()), key=f"date_{page}")
    v = v.loc[v.start_time.dt.date.eq(date)]
    trip_id = cols[2].selectbox("行程編號 · 原始資料", v.trip_id.tolist(), format_func=lambda s: s.split("::")[-1], key=f"journey_{page}")
    return v.loc[v.trip_id.eq(trip_id)].iloc[0]


def fuel_comparison(t):
    metrics([("實際燃油 Actual Fuel", number(t.trip_fuel_l) + " L", "DERIVED"),
             ("比較預期 Comparable Expected Fuel", number(t.expected_fuel_l) + " L", "DERIVED"),
             ("相較同儕燃油差距 Benchmark Gap", number(t.benchmark_gap_l, 2) + " L", "DERIVED"),
             ("比較證據強度 Benchmark Quality", t.benchmark_quality if pd.notna(t.benchmark_quality) else "證據不足", "DERIVED")])
    if pd.isna(t.expected_fuel_l):
        st.info("目前資料不足以判斷。本趟未符合品質／最小樣本要求；仍可查看真實行程資料。")
    else:
        source_note(f"{badge('DERIVED')} 相似行程比較基準：{BENCHMARK_LABELS.get(t.benchmark_level, t.benchmark_level)} · {int(t.peer_trip_count)} 趟／{int(t.peer_vehicle_count)} 台其他車，已排除本車。燃油差距占實際燃油 {number(t.benchmark_gap_pct)}%。")
        st.caption(f"同儕中位數 {number(t.peer_fuel_median_l_per_km, 3)} L/km · IQR {number(t.peer_fuel_iqr_l_per_km, 3)} L/km · 離散程度 {number(t.benchmark_dispersion, 3)}。比較證據強度不是資料品質分數或機率。")
    st.caption("Primary Evidence Mode：僅 RAW／DERIVED；比較基準參照完整歷史資料期間。" + DISCLAIMER)


def data_journey(trips):
    profile = document("docs/data_profile.json")
    summary = document("data/processed/pipeline_summary.json")
    hero("資料 → 洞察 → 決策 → 行動", "讓資料的每一步，都看得見。", "原始訊號保留可追溯性，衍生指標揭露計算方式，模擬情境清楚標記來源。")
    metrics([("原始訊號筆數", f"{profile['row_count']:,}", "RAW"), ("行程總數", f"{len(trips):,}", "DERIVED"),
             ("車輛數", str(profile['vehicle_count']), "RAW"), ("事件紀錄數", f"{summary['events']:,}", "DERIVED"),
             ("模擬欄位數", str(len(MOCK_RULES)), "MOCK")])
    st.subheader("四層資料來源架構")
    st.dataframe(pd.DataFrame([
        {"層級": "A Competition Core", "狀態": "此次競賽實際提供", "內容": "車輛、行程、GPS、里程、燃油、RPM、負載、carStatus、來源事件"},
        {"層級": "B Extended iTRAQ", "狀態": "參考 schema；正式可用性待確認", "內容": "driverUid、燃油率、踏板、檔位、PTO 等"},
        {"層級": "C Enterprise Context", "狀態": "需企業系統介接", "內容": "任務、實際載重、交付窗口、停靠用途、維修"},
        {"層級": "D External Context", "狀態": "選配外部來源", "內容": "交通、天氣、坡度"},
    ]), hide_index=True, width="stretch")
    steps = [("01", "原始車聯網資料", "Excel 與欄位對照"), ("02", "清理", "品質檢查與時間整理"), ("03", "行程彙整", "車輛＋行程編號"),
             ("04", "觀測比較基準", "跨車 L1–L3"), ("05", "燃油差距與槓桿", "差距＋優先度"), ("06", "車況檢查訊號", "持續配對殘差"), ("07", "決策資料包", "角色建議 → 解釋 → Pilot")]
    st.markdown('<div class="flow">' + ''.join(f'<div class="flow-step"><span>{n} →</span><b>{title}</b>{sub}</div>' for n, title, sub in steps) + '</div>', unsafe_allow_html=True)
    st.info("Evidence Mode：Primary analysis 只用 Competition Core 的 RAW／DERIVED。Mock 是 Production Context 的 placeholder，不決定比較基準、主要 KPI、車況訊號或 Maintenance 觸發。")
    st.caption(TYPE_DEFINITION)
    st.caption("RAW iTRAQ → Data Quality → Trip Aggregation → Observed Comparable Benchmark → Fuel Efficiency Gap → Improvement Lever Ranking → Vehicle Efficiency Signal → Decision Packet → Persona Recommendation → GenAI Grounded Explanation → Action / Pilot Validation")
    with st.expander("Prototype 與 Production Roadmap"):
        st.write("目前：離線歷史資料、行程分析、歷史回放、比較基準、改善篩選、角色決策與選配 GenAI 解釋。")
        st.write("Stage 2 確認 Extended iTRAQ 的 driverUid／tachographDriver、燃油率、踏板、檔位與 PTO；Stage 3 介接任務、載重、交付窗口、停靠用途與維修；Stage 4 接入外部路況、天氣、坡度；Stage 5 Live Stream 與閉環 Pilot。")
    left, right = st.columns([1.2, 1])
    with left, st.container(border=True):
        st.subheader("HINO 原本提供什麼？")
        st.markdown(badge("RAW") + " 原始車聯網資料預覽", unsafe_allow_html=True)
        raw = next(pq.ParquetFile(ROOT / "data/interim/raw_snapshot.parquet").iter_batches(batch_size=8)).to_pandas()
        preferred = [c for c in ["Type", "enabledCode", "journeyCode", "time", "carStatus", "can.totalMileage", "can.engine.totalFuelUsed"] if c in raw]
        raw_labels = {"Type": "HINO 系列（Type）", "enabledCode": "車輛識別碼 enabledCode", "journeyCode": "行程編號 journeyCode",
                      "time": "時間 time", "carStatus": "車輛狀態 carStatus", "can.totalMileage": "累積里程 can.totalMileage",
                      "can.engine.totalFuelUsed": "累積燃油 can.engine.totalFuelUsed"}
        st.dataframe(raw[preferred].rename(columns=raw_labels), hide_index=True, width="stretch")
        st.caption("從原始資料快照取樣顯示；完整欄位、缺值與型態已記錄於資料檢查報告。")
    with right, st.container(border=True):
        st.subheader("三種資料，三種責任")
        for origin, title, text in [("RAW", "車聯網量測", "車輛識別碼、累積里程、累積燃油、GPS、引擎與事件。"),
                                    ("DERIVED", "可追溯的計算", "時間差、行程燃油、格網路線、相似行程基準與改善估計。"),
                                    ("MOCK", "明示的情境假設", "虛擬駕駛、載重、交通、任務與停靠用途；固定亂數種子為 42。")]:
            st.markdown(badge(origin) + f" **{title}**", unsafe_allow_html=True)
            st.caption(text)
    st.subheader("清理與品質處理")
    st.dataframe(pd.DataFrame([
        {"資料問題": "journeyCode 跨車重複", "觀察筆數": profile['quality'].get('journey_codes_shared_across_vehicles', 0), "處理方式": "使用 enabledCode＋journeyCode 作為行程識別碼"},
        {"資料問題": "時間戳記重複", "觀察筆數": profile['quality'].get('duplicate_trip_timestamps', 0), "處理方式": "保留原始列；計算時採同時間最後一筆"},
        {"資料問題": "時間間隔超過 300 秒", "觀察筆數": profile['quality'].get('gaps_over_300s', 0), "處理方式": "整段標為未觀測，不歸入前一狀態"},
        {"資料問題": "GPS 零速但 CAN 顯示移動", "觀察筆數": profile['quality'].get('gps_zero_when_can_moving_rows', 0), "處理方式": "僅 CAN status=0 才優先採 CAN；其他情況回退有效 GPS 並保留衝突標記"},
    ]), hide_index=True, width="stretch")
    with st.expander("查看完整資料檢查報告"):
        st.markdown((ROOT / "docs/data_profile.md").read_text())


def fleet_overview(trips):
    df = filter_fleet(trips, "fleet")
    supported = df.loc[df.benchmark_gap_l.notna()]
    fuel_mask = (df.trip_fuel_l.notna() & df.trip_distance_km.notna() & ~df.fuel_reset_flag & ~df.mileage_reset_flag
                 & ~df.implausible_mileage_flag & ~df.fuel_missing_flag & ~df.mileage_missing_flag)
    measured = df.loc[fuel_mask]
    distance, fuel = measured.trip_distance_km.sum(min_count=1), measured.trip_fuel_l.sum(min_count=1)
    gap = supported.benchmark_gap_l.sum(min_count=1)
    engine_minutes = df.driving_minutes.sum(min_count=1) + df.idle_minutes.sum(min_count=1)
    hero("Primary Evidence Mode · 觀測比較", f"{number(gap)} L 相較同儕燃油差距，從核對證據開始。",
         f"{len(supported):,} / {len(df):,} 趟具有比較支持。燃油差距不是可實現節省；先核對停留、任務與車況條件。")
    metrics([("總行駛里程", number(distance, 0) + " km", "DERIVED"), ("累計觀測燃油", number(fuel, 0) + " L", "DERIVED"),
             ("車隊平均油耗效率", number(distance / fuel if fuel > 0 else None, 2) + " km/L", "DERIVED")])
    metrics([("觀測怠速時間占比", number(df.idle_minutes.sum(min_count=1) / engine_minutes * 100 if engine_minutes > 0 else None) + "%", "DERIVED"),
             ("相較同儕燃油差距", number(gap) + " L", "DERIVED"), ("具比較支持行程數", f"{len(supported):,} / {len(df):,}", "DERIVED")])
    source_note(f"里程／燃油總量排除 {int((~fuel_mask).sum()):,} 趟讀值缺漏、重設或里程跳點。差距為支持行程的正差加總，不與負差互抵。{DISCLAIMER}。")
    a, b = st.columns([1.15, 1])
    with a, st.container(border=True):
        st.subheader("車隊燃油趨勢")
        st.caption("同一組支持行程按月彙整 · Actual Fuel / Comparable Expected Fuel")
        if len(supported):
            monthly = supported.assign(month=supported.start_time.dt.to_period("M").dt.to_timestamp()).groupby("month")[["trip_fuel_l", "expected_fuel_l"]].sum().reset_index()
            fig = go.Figure()
            for c, label, color in [("trip_fuel_l", "實際燃油", GREEN), ("expected_fuel_l", "比較預期燃油", AMBER)]:
                fig.add_trace(go.Scatter(x=monthly.month, y=monthly[c], name=label, mode="lines+markers", line=dict(color=color, width=2.5)))
            fig.update_xaxes(tickformat="%Y/%m")
            fig.update_yaxes(title="燃油用量（L）")
            chart(fig)
        else:
            st.info("目前資料不足以判斷。")
    with b, st.container(border=True):
        st.subheader("前五大行程燃油差距")
        st.caption("篩選線索；請一起核對 Benchmark Quality")
        top = supported.nlargest(5, "benchmark_gap_l").sort_values("benchmark_gap_l")
        if len(top):
            fig = go.Figure(go.Bar(x=top.benchmark_gap_l, y=top.trip_id, orientation="h", marker_color=GREEN,
                text=[f"{v:.2f} L · {q}" for v, q in zip(top.benchmark_gap_l, top.benchmark_quality)], textposition="auto"))
            fig.update_yaxes(ticktext=[str(v)[:10] + " · " + str(d)[5:10] for v, d in zip(top.enabledCode, top.start_time)], tickvals=top.trip_id)
            fig.update_xaxes(title="Benchmark Fuel Gap（L）")
            chart(fig)
        else:
            st.info("此範圍沒有可比較行程。")
    a, b = st.columns([1.15, 1])
    with a, st.container(border=True):
        st.subheader("跨車怠速／停留熱點")
        st.caption("完整歷史期間，獨立於側欄篩選 · 至少兩台車共同出現 · 僅觀測分鐘")
        hotspots = table("data/processed/idle_hotspots.parquet")
        if "vehicle_count" not in hotspots:
            st.info("請重新建置熱點資料，以核對是否跨車重複發生。")
        else:
            repeated = hotspots.loc[hotspots.vehicle_count.ge(2)].sort_values("total_idle_minutes", ascending=False)
            if repeated.empty:
                st.info("目前沒有至少兩台車共同出現的熱點；不將單車重複停靠解讀為跨車流程問題。")
            else:
                selected = st.selectbox("選擇跨車熱點", repeated.stop_hotspot_id.tolist(), key="fleet_cross_vehicle_hotspot")
                hotspot = repeated.loc[repeated.stop_hotspot_id.eq(selected)].iloc[0]
                metrics([("不同車輛", f"{int(hotspot.vehicle_count)} 台", "DERIVED"),
                         ("涉及行程", f"{int(hotspot.trip_count)} 趟", "DERIVED"),
                         ("觀測怠速", f"{number(hotspot.total_idle_minutes, 0)} 分", "DERIVED")])
                if pd.notna(hotspot.get("peak_idle_hour")):
                    hour = int(hotspot.peak_idle_hour)
                    st.write(f"**怠速累積最多時段：{hour:02d}:00–{(hour + 1) % 24:02d}:00** · {number(hotspot.peak_idle_minutes)} 分鐘")
                st.info("調度下一步：核對到站窗口、排隊與裝卸安排，確認 PTO／設備是否需要引擎運轉，再決定如何調整。")
            with st.expander("查看所有重複停靠熱點（含單車）"):
                st.dataframe(hotspots.loc[hotspots.visit_count.ge(2), ["stop_hotspot_id", "vehicle_count", "trip_count", "total_idle_minutes"]].round(2).rename(columns={
                    "stop_hotspot_id": "熱點格網", "vehicle_count": "不同車輛數", "trip_count": "涉及行程數", "total_idle_minutes": "觀測怠速分鐘"}), hide_index=True, width="stretch")
        st.caption("格網相近不代表同一客戶；停靠用途待核對。缺少真實駕駛識別，尚不能判定跨駕駛重複性，也不能將全部怠速視為浪費。")
    with b, st.container(border=True):
        st.subheader("車況檢查訊號")
        st.caption("篩選期間曾出現的連續偏高殘差；提示核對，不表示目前車況")
        anomalies = df.loc[df.vehicle_health_flag]
        if len(anomalies):
            view = anomalies.groupby("enabledCode").agg(flagged_trips=("trip_id", "size"), max_streak=("consecutive_anomaly_trips", "max"), last_signal=("start_time", "max")).sort_values("flagged_trips", ascending=False).head(5)
            st.dataframe(view.rename(columns={"flagged_trips": "訊號行程數", "max_streak": "最長連續趟數", "last_signal": "最近訊號時間"}).rename_axis("車輛識別碼"), width="stretch")
        else:
            st.info("此範圍未出現有足夠證據的連續訊號。")
    st.caption("車隊主要 KPI、比較基準與車況檢查訊號只使用 RAW／DERIVED。MOCK 不參與任何主要定量結論。")


def route_map(tel):
    gps = tel.dropna(subset=["latitude", "longitude"])
    if gps.empty:
        st.info("本趟沒有有效 GPS。")
        return
    # Limit rendering only; analytics always use the full telemetry.
    stride = max(1, len(gps) // 1500)
    gps = pd.concat([gps.iloc[::stride], gps.tail(1)]).drop_duplicates("timestamp")
    mode = st.radio("路線呈現方式", ["地圖", "離線 GPS 座標圖"], horizontal=True)
    if mode == "地圖":
        path = gps[["longitude", "latitude"]].values.tolist()
        layer = pdk.Layer("PathLayer", [{"path": path}], get_path="path", get_color=[36, 113, 83], width_min_pixels=3)
        stops = pdk.Layer("ScatterplotLayer", gps.loc[gps.status.eq("idling"), ["latitude", "longitude"]],
                          get_position="[longitude, latitude]", get_fill_color=[205, 154, 69, 160], get_radius=70, radius_min_pixels=3)
        view = pdk.data_utils.compute_view(gps[["longitude", "latitude"]])
        st.pydeck_chart(pdk.Deck(layers=[layer, stops], initial_view_state=view,
                                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"), height=330)
    else:
        fig = px.line(gps, x="longitude", y="latitude", markers=False, color_discrete_sequence=[GREEN])
        fig.add_trace(go.Scatter(x=[gps.longitude.iloc[0], gps.longitude.iloc[-1]], y=[gps.latitude.iloc[0], gps.latitude.iloc[-1]], mode="markers+text", text=["起點", "終點"], textposition="top center", marker=dict(size=10, color=[GREEN, AMBER]), showlegend=False))
        fig.update_xaxes(title="經度")
        fig.update_yaxes(title="緯度", scaleanchor="x", scaleratio=1)
        chart(fig, 330)
    st.caption("GPS 衍生路線 · 金色點為怠速樣本。底圖需網路；離線座標圖不需外部服務。定位跳點可能影響路線形狀。")


def trip_explorer(trips):
    t = trip_selector(trips, "trip")
    packet = document("data/processed/decision_packets.json")[t.trip_id]
    st.caption(f"車輛 {t.enabledCode} · 行程 {t.journeyCode} · {t.start_time:%Y-%m-%d %H:%M} → {t.end_time:%H:%M} · HINO 系列（Type） {t.vehicle_type}")
    fuel_comparison(t)
    a, b = st.columns([1.15, 1])
    tel = telemetry_for(t.trip_id)
    with a, st.container(border=True):
        st.subheader("路線與停留")
        route_map(tel)
    with b, st.container(border=True):
        st.subheader("改善槓桿優先度")
        st.caption("Estimated Improvement Levers · 怠速／停留情境、轉速型態、引擎負載型態的核對優先度")
        if t.lever_status == "HEURISTIC_PRIORITY":
            priorities = [t[factor + "_priority_pct"] for factor in FACTOR_NAMES]
            fig = go.Figure(go.Bar(x=priorities, y=list(FACTOR_NAMES.values()), orientation="h", marker_color=GREEN,
                                  text=[f"{v:.1f}%" for v in priorities], textposition="auto"))
            fig.update_xaxes(title="改善優先度 %", range=[0, 100])
            chart(fig, 330)
            if not any(priorities):
                st.info("沒有高於同儕中位數的行為指標；不強行分配改善槓桿。")
        else:
            st.info("行為或同儕證據不足，暫不排序改善槓桿；燃油差距仍獨立呈現。")
        st.caption("優先度不是節油比例，各槓桿可能相關。高負載須先核對真實任務與載重，不能歸責駕駛。")
    st.subheader("行程時間軸")
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=.045)
    for i, (column, label, color) in enumerate([("speed", "車速（km/h）", GREEN), ("rpm", "引擎轉速（RPM）", BLUE), ("engine_load", "引擎負載（%）", AMBER)], start=1):
        fig.add_trace(go.Scatter(x=tel.timestamp, y=tel[column], name=label, mode="lines", line=dict(color=color, width=1.3)), row=i, col=1)
        fig.update_yaxes(title_text=label, row=i, col=1)
    states = tel.status.map({"parking": 0, "driving": 1, "idling": 2})
    fig.add_trace(go.Scatter(x=tel.timestamp, y=states, name="車輛狀態（carStatus）", mode="lines", line=dict(color="#847A9D", shape="hv")), row=4, col=1)
    fig.update_yaxes(tickvals=[0, 1, 2], ticktext=["停車", "行駛", "怠速"], row=4, col=1)
    fig.update_layout(showlegend=False)
    chart(fig, 420)
    source_note(f"{badge('DERIVED')} CAN status=0 時優先採有效 CAN；其餘回退有效 GPS；曲線不作插值。行程時長 {number(t.duration_minutes)} 分鐘，已觀測 {number(t.observed_minutes)} 分鐘，未觀測 {number(t.unobserved_minutes)} 分鐘。")
    st.subheader("Supporting Events｜來源事件")
    st.dataframe(pd.DataFrame([{"事件": name, "去重通報次數": int(t[field]), "角色": "設定依賴，僅供核對"} for field, name in [
        ("rapid_accel_event_count", "急加速 Event 6"), ("rapid_decel_event_count", "急減速 Event 7"),
        ("speeding_event_count", "超速 Event 8 · SOURCE_CONFLICT"), ("engine_overload_event_count", "引擎過載 Event 11")]]), hide_index=True)
    st.caption("來源事件設定可能因車輛／客戶與時間不同；不作無條件跨車績效比較。Event 8 不由 EcoPilot 重建；Event 11 不等於負載 >90% 比例。")
    a, b = st.columns([1, 1])
    with a, st.container(border=True):
        st.subheader("資料來源對照")
        view = [{"欄位": f"{FIELD_LABELS.get(c, c)}（{c}）", "數值": display_value(t[c]), "來源": display_source("MOCK" if c in MOCK_RULES else "RAW" if c in ["enabledCode", "journeyCode"] else "DERIVED")}
                for c in ["enabledCode", "journeyCode", "trip_distance_km", "trip_fuel_l", "idle_minutes", "route_id", "driver_id", "payload_ratio", "traffic_level", "stop_purpose", "data_quality_score"]]
        st.dataframe(pd.DataFrame(view), hide_index=True, width="stretch")
        with st.expander("完整欄位定義與品質標記"):
            flags = [{"品質標記": f"{FLAG_LABELS.get(c, c)}（{c}）", "是否出現": "是" if bool(t[c]) else "否"} for c in trips if c.endswith("_flag")]
            st.dataframe(pd.DataFrame(flags), hide_index=True)
            st.caption("比較證據強度與資料品質分數分開解讀；未觀測營運條件需未來補齊。")
            st.dataframe(localized_dictionary(table("data/processed/data_dictionary.parquet")), hide_index=True)
    with b, st.container(border=True):
        st.subheader("相同證據，各司其職")
        persona = st.selectbox("查看角色建議", PERSONAS, format_func=lambda value: PERSONA_LABELS[value])
        result = recommend(packet, persona)
        if st.button("以生成式 AI 調整建議措辭", help="需設定 API 金鑰、模型與啟用開關；只傳送匿名 trip key、角色與允許的結構化證據，移除原始識別碼及座標。"):
            with st.spinner("產生有根據的角色建議…"):
                result = narrate(packet, persona, use_llm=True)
        st.caption("建議產生方式：" + {"deterministic_template": "離線範本", "openai_structured_generation": "有證據引用的結構化 GenAI 解釋"}.get(result["mode"], result["mode"]))
        st.markdown("**" + result["headline"] + "**")
        st.write(result["evidence_summary"])
        st.write(result["next_action"])
        st.caption("待核對：" + "；".join(result["what_to_verify"]))
        st.caption("交接角色：" + PERSONA_LABELS[result["handoff_role"]])
        st.caption("引用證據：" + "、".join(result["evidence_ids"]))
        if result.get("fallback_reason"):
            st.info(result["fallback_reason"])
        if not os.getenv("OPENAI_API_KEY"):
            st.caption("目前未設定 API 金鑰，已使用完整離線範本。")
        with st.expander("查看／下載決策資料包（原始欄位代碼）"):
            st.json(packet)
            st.download_button("下載決策資料包 JSON", json.dumps(packet, ensure_ascii=False, indent=2), file_name="decision_packet.json", mime="application/json")


def driver_coach(trips):
    t = trip_selector(trips, "coach")
    packet = document("data/processed/decision_packets.json")[t.trip_id]
    st.caption(f"車輛 {t.enabledCode} · {t.start_time:%Y-%m-%d} · 模擬駕駛代碼 {t.driver_id}")
    st.info("Prototype historical simulation：行程前、歷史回放、行程後均使用歷史資料；Real-time driver alerts 屬 Production Roadmap。")
    phase = st.radio("教練介入時機", ["行程前", "歷史回放", "行程後"], horizontal=True)
    if phase == "行程前":
        hero("行程前 · 歷史情境", "出發前，先對齊停留安排。", "以已完成行程的資料模擬下一趟準備，並非事前預測或即時派工。")
        action = "出發前先與調度確認停靠用途、作業需求與到站窗口。"
        st.write(f"模擬任務：{display_value(t.task_type)} · 配送窗口：{t.delivery_window} · 路況：{display_value(t.traffic_level)}")
        st.markdown(badge("MOCK") + " 上述任務、時間窗口與路況均為模擬情境。", unsafe_allow_html=True)
    elif phase == "歷史回放":
        tel = telemetry_for(t.trip_id)
        idle_indices = tel.index[tel.status.eq("idling")].tolist()
        default = idle_indices[len(idle_indices) // 2] if idle_indices else max(0, len(tel) // 2)
        idx = st.slider("歷史回放位置（非即時訊號）", 0, max(1, len(tel) - 1), value=min(default, max(1, len(tel)-1)))
        idx = min(idx, len(tel) - 1)
        current = tel.iloc[idx]
        cursor = idx
        while cursor > 0 and tel.iloc[cursor-1].status == "idling" and current.status == "idling" and (tel.iloc[cursor].timestamp-tel.iloc[cursor-1].timestamp).total_seconds() <= 300:
            cursor -= 1
        minutes = (current.timestamp - tel.iloc[cursor].timestamp).total_seconds() / 60 if current.status == "idling" else 0
        hero("Historical Replay · 歷史回放", f"{current.timestamp:%H:%M:%S} · 目前連續怠速 {minutes:.1f} 分鐘", "此為歷史時間戳記差分的回放，不是連線中的即時駕駛提醒。")
        st.caption(f"回放狀態：{MOCK_VALUE_LABELS.get(current.status, {'parking': '停車', 'driving': '行駛', 'idling': '怠速'}.get(current.status, current.status))} · 由原始 carStatus 衍生")
        action = "安全停妥且作業允許時，先確認是否仍需保持引擎運轉。" if current.status == "idling" else "保持注意路況，以平順操作接續車流。"
    else:
        hero("行程後 · 回顧與行動", "下一趟，只先做好一件事。", "先理解停留、任務與車況，再一起找到能調整的部分。")
        fuel_comparison(t)
        rec = recommend(packet, "DRIVER")
        st.write(rec["evidence_summary"])
        action = rec["next_action"]
        if packet["improvement_levers"]:
            st.write("本趟優先核對的改善槓桿：" + FACTOR_NAMES[packet["improvement_levers"][0]["factor"]])
    st.markdown('<div class="eyebrow">下一步只做一件事</div>', unsafe_allow_html=True)
    st.markdown('<div class="one-action">' + html.escape(action) + '</div>', unsafe_allow_html=True)
    st.caption("這是共同改善的起點，不是駕駛績效排名。" + DISCLAIMER + "。")


def manager_center(trips):
    from src.action_ui import action_workbench, role_names

    df = filter_fleet(trips, "manager")
    actions = table("data/processed/actions.parquet")
    actions = actions.loc[actions.trip_id.isin(df.trip_id)].copy()
    hero("跨角色協作", "讓每個機會，都有下一步。", "調度核對停留情境，駕駛核對操作型態，維修核對車況；管理者串接缺少的營運條件。")
    cols = st.columns(4)
    for col, role, title in zip(cols, ["FLEET_MANAGER", "DISPATCHER", "DRIVER", "MAINTENANCE"],
                                ["車隊管理者 · 補證據", "調度人員 · 停留情境", "駕駛教練 · 操作協作", "維修人員 · 車況檢查"]):
        with col:
            subset = actions.loc[actions.owner.eq(role)]
            st.caption(title)
            st.markdown(f"**{len(subset):,} 項待核對**")
    role = st.selectbox("負責角色", ["ALL", "DISPATCHER", "DRIVER", "FLEET_MANAGER", "MAINTENANCE"], format_func=lambda value: PERSONA_LABELS.get(value, "全部角色"))
    view = actions if role == "ALL" else actions.loc[actions.owner.eq(role)]
    sort = st.radio("排序", ["相較同儕燃油差距", "優先檢查車況"], horizontal=True)
    if sort == "優先檢查車況":
        view = view.assign(_priority=view.owner.eq("MAINTENANCE")).sort_values(["_priority", "benchmark_gap_l"], ascending=[False, False]).drop(columns="_priority")
    else:
        view = view.sort_values("benchmark_gap_l", ascending=False, na_position="last")
    workbench_tab, all_tab, health_tab = st.tabs(["行動工作台", "全部待辦", "車況證據"])
    with workbench_tab:
        action_workbench(view, PERSONA_LABELS)

    localized_actions = view.drop(columns="owner").rename(columns={"trip_id": "行程識別碼", "vehicle": "車輛識別碼", "problem": "問題",
                                             "primary_owner": "Primary Owner", "supporting_roles": "Supporting Roles", "handoff_reason": "Handoff Reason",
                                             "owner_confidence": "接手證據完整度", "evidence": "依據", "benchmark_gap_l": "相較同儕燃油差距（L）",
                                             "action": "建議行動", "source": "資料來源", "benchmark_quality": "比較證據強度"}).copy()
    localized_actions["Primary Owner"] = localized_actions["Primary Owner"].map(PERSONA_LABELS)
    localized_actions["Supporting Roles"] = localized_actions["Supporting Roles"].map(lambda roles: role_names(roles, PERSONA_LABELS))
    with all_tab:
        st.caption(f"共 {len(view):,} 項 · 問題 → 主要負責 → 協作角色 → 依據 → 行動")
        st.dataframe(localized_actions, hide_index=True, width="stretch", column_config={"相較同儕燃油差距（L）": st.column_config.NumberColumn("相較同儕燃油差距（L）", format="%.2f")})
        st.download_button("下載行動待辦清單 CSV", localized_actions.to_csv(index=False).encode("utf-8-sig"), "ecopilot_actions.csv", "text/csv")
    with health_tab:
        st.subheader("車輛效率殘差證據")
        vehicles = df.loc[df.vehicle_health_flag, "enabledCode"].unique().tolist()
        if not vehicles:
            st.info("目前沒有符合連續異常條件的車輛；不產生示範案例 C。")
        else:
            vehicle = st.selectbox("有歷史檢查訊號的車輛", sorted(vehicles))
            v = df.loc[df.enabledCode.eq(vehicle)].sort_values("start_time")
            fig = go.Figure(go.Scatter(x=v.start_time, y=v.vehicle_residual_ratio * 100, mode="markers", name="配對殘差", marker=dict(color=np.where(v.vehicle_health_flag, AMBER, GREEN), size=7)))
            fig.add_hline(y=HEALTH_RESIDUAL_THRESHOLD * 100, line_dash="dot", line_color=AMBER, annotation_text="原型門檻 +15%")
            fig.update_xaxes(tickformat="%Y/%m")
            fig.update_yaxes(title="燃油殘差（%）")
            chart(fig)
            st.write(HEALTH_ACTION)
            st.caption("車況配對只使用觀測行程與行為。真實載重、交通與維修紀錄仍缺，MOCK 不參與配對；此為歷史訊號。")
            with st.expander("核對連續行程、支持樣本與未觀測區段"):
                st.dataframe(v[["trip_id", "start_time", "trip_fuel_l", "health_expected_fuel_l", "health_peer_count", "health_match_distance", "vehicle_residual_ratio", "consecutive_anomaly_trips", "vehicle_health_flag"]].rename(columns={"trip_id": "行程識別碼", "start_time": "開始時間", "trip_fuel_l": "實測燃油（L）", "health_expected_fuel_l": "配對預期燃油（L）", "health_peer_count": "支持行程數", "health_match_distance": "配對距離", "vehicle_residual_ratio": "殘差比例", "consecutive_anomaly_trips": "連續異常趟數", "vehicle_health_flag": "檢查訊號"}), hide_index=True)


def assumptions_page(trips):
    st.info("模擬資料僅供原型展示。" + DISCLAIMER + "。")
    dictionary = table("data/processed/data_dictionary.parquet")
    metrics([(display_source(kind) + " · 欄位數", str(int(dictionary.source_type.eq(kind).sum())), kind) for kind in ["RAW", "DERIVED", "MOCK"]])
    pipeline = document("data/processed/pipeline_summary.json")
    st.caption(f"analysis_version={pipeline['analysis_version']} · source_contract_version={pipeline['source_contract_version']} · event_reference_version={pipeline['event_reference_version']}")
    tabs = st.tabs(["Current Data", "Event Reference", "Production Data Capability", "Methodology", "Model Validation", "Pilot Validation"])
    with tabs[0]:
        st.subheader("此次 Competition Data｜欄位字典")
        st.caption("欄位代碼與計算公式維持原始名稱，方便對照資料產物；來源、用途與限制另以中文說明。")
        selected = st.multiselect("來源", ["RAW", "DERIVED", "MOCK"], default=["RAW", "DERIVED", "MOCK"], format_func=display_source)
        query = st.text_input("搜尋欄位")
        view = dictionary.loc[dictionary.source_type.isin(selected) & dictionary.column.str.contains(query, case=False, regex=False)]
        st.dataframe(localized_dictionary(view), hide_index=True, width="stretch")
        st.download_button("下載欄位字典 CSV", localized_dictionary(dictionary).to_csv(index=False).encode("utf-8-sig"), "data_dictionary.csv", "text/csv")
    with tabs[1]:
        st.markdown((ROOT / "docs/event_reference.md").read_text())
        st.dataframe(table("data/reference/event_reference.parquet"), hide_index=True, width="stretch")
    with tabs[2]:
        st.markdown((ROOT / "docs/data_capability_matrix.md").read_text().split('| field')[0])
        capability = pd.read_csv(ROOT / "data/reference/data_capability_matrix.csv")
        st.dataframe(capability, hide_index=True, width="stretch")
        st.caption("正式產品可擴充資料：Extended iTRAQ 的 driverUid、engineFuelRate、pedalPosition、ptoSwitch 等欄位在參考 schema 中，但本次競賽沒有；正式可用性待確認。Mock 是 Production Context placeholder。")
    with tabs[3]:
        st.markdown((ROOT / "docs/methodology.md").read_text())
    with tabs[4]:
        report = document("data/processed/model_report.json")
        st.caption("Validation / Scenario Support：選配模型不決定主要 KPI、比較基準或車況訊號。")
        if report.get("status") == "evaluated":
            st.markdown("**選配模型已完成驗證：隨機森林回歸。**")
            st.caption(f"依車輛分組進行五折回溯驗證，共 {report['n_trips']:,} 趟合格行程；測試時保留整台車。")
            st.dataframe(pd.DataFrame([{"模型": "Random Forest", "MAE（L）": report.get("mae_l"), "R²": report.get("r2")},
                                       {"模型": "Baseline A", "MAE（L）": report.get("baseline_a_mae_l")},
                                       {"模型": "Baseline B", "MAE（L）": report.get("baseline_b_mae_l")}]), hide_index=True)
            st.caption(f"相對 Baseline A／B 的 MAE 變化：{number(report.get('relative_improvement_vs_a') * 100)}%／{number(report.get('relative_improvement_vs_b') * 100)}%；這是預測誤差，不是節油成效。")
            st.json(report.get("time_holdout", {}))
        else:
            st.info("選配模型驗證尚未完成；主要比較仍可使用。")
        with st.expander("查看原始模型報告（技術欄位代碼）"):
            st.json(report)
    with tabs[5]:
        st.markdown((ROOT / "docs/pilot_validation.md").read_text())
        st.caption("目前 Pilot template 只有 header，沒有虛構 Outcome。")
    with tabs[0]:
        st.subheader("Mock Context｜Production Context Placeholder")
        st.markdown((ROOT / "docs/assumptions.md").read_text())
    with tabs[0]:
        st.subheader("Data Quality｜資料品質")
        flags = pd.DataFrame({"品質標記": [f"{FLAG_LABELS.get(c, c)}（{c}）" for c in trips if c.endswith("_flag")],
                              "受影響行程數": [int(trips[c].sum()) for c in trips if c.endswith("_flag")]})
        st.dataframe(flags, hide_index=True, width="stretch")
        quality_fig = px.histogram(trips, x="data_quality_score", nbins=20, color_discrete_sequence=[GREEN], labels={"data_quality_score": "資料品質分數"})
        quality_fig.update_yaxes(title="行程數")
        chart(quality_fig)
        st.caption("資料品質分數是工程品質檢查指標，不是模型信心值；品質不足的行程仍保留。")
        pipeline = document("data/processed/pipeline_summary.json")
        st.caption(f"本次建置保留 {pipeline['raw_rows']:,} 筆原始訊號，彙整 {pipeline['trips']:,} 趟行程；其中 {pipeline['eligible_trips']:,} 趟符合比較前的品質條件。")
        with st.expander("查看原始處理摘要（技術欄位代碼）"):
            st.json(pipeline)
    with tabs[3]:
        st.subheader("Benchmark Evidence Quality｜比較證據強度")
        st.write("HIGH：L1、至少十趟／三台其他車、IQR/median ≤ 0.25。MEDIUM：L1/L2、至少八趟／兩台、IQR/median ≤ 0.5。其餘已支持比較為 LOW；未支持留空。")
        st.caption("這是 comparison evidence strength，不是資料品質分數或機率。L3 一律 LOW；高強度也不代表已控制真實載重與任務。")
        st.dataframe(trips.groupby(["benchmark_level", "benchmark_quality"], dropna=False).size().rename("行程數").reset_index().rename(columns={"benchmark_level": "比較層級", "benchmark_quality": "比較證據強度"}), hide_index=True)
        st.caption(TYPE_DEFINITION)


def render(page):
    st.markdown(CSS, unsafe_allow_html=True)
    _, title, subtitle = PAGES[page]
    st.markdown('<div class="eyebrow">HINO EcoPilot｜車隊協同節能決策原型</div>', unsafe_allow_html=True)
    st.title(title)
    st.caption(subtitle)
    required = ["data/processed/trips_enriched.parquet", "data/processed/decision_packets.json", "data/processed/demo_cases.json", "data/processed/data_dictionary.parquet", "data/processed/pipeline_summary.json", "data/processed/actions.parquet", "data/processed/idle_hotspots.parquet", "data/processed/model_report.json", "docs/data_profile.json", "data/interim/raw_snapshot.parquet", "data/interim/telemetry.parquet"]
    if any(not (ROOT / p).exists() for p in required):
        st.info("尚未建置完整資料。請先在專案目錄執行：./ecopilot build")
        st.stop()
    summary = document("data/processed/pipeline_summary.json")
    if summary.get("phase", 0) < 5 or summary.get("analysis_version") != ANALYSIS_VERSION:
        st.info("目前資料不完整或為舊版分析。請執行 ./ecopilot build 後重新整理。")
        st.stop()
    trips = table("data/processed/trips_enriched.parquet")
    if "benchmark_gap_l" not in trips:
        st.info("目前只有部分資料處理輸出。請執行完整 build_pipeline.py 後重整。")
        st.stop()
    with st.sidebar:
        st.markdown(badge("RAW") + badge("DERIVED") + badge("MOCK"), unsafe_allow_html=True)
        st.caption("以證據串起每一步。\n\n一起，把節能變成下一步。")
    {"journey": data_journey, "fleet": fleet_overview, "trip": trip_explorer, "coach": driver_coach,
     "manager": manager_center, "assumptions": assumptions_page}[page](trips)
    st.markdown('<div class="footnote">HINO EcoPilot · 原型系統 &nbsp; / &nbsp; ' + DISCLAIMER + ' &nbsp; / &nbsp; 模擬資料僅供原型展示。</div>', unsafe_allow_html=True)
