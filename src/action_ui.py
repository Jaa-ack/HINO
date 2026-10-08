"""A compact, evidence-first action editor for the management page."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st

from src.action_tracking import ACTION_STATUSES, VERIFICATION_PENDING, ActionStore, action_key


def role_names(roles, labels):
    # Parquet list columns arrive as ndarray; normalize at this display boundary.
    return "、".join(labels.get(role, role) for role in roles) if isinstance(roles, (list, tuple, np.ndarray)) else ""


def action_workbench(view, labels):
    if view.empty:
        st.info("目前篩選沒有待辦，請調整負責角色或分析範圍。")
        return
    choices = {action_key(row): row for _, row in view.iterrows()}
    def choice_label(key):
        row = choices[key]
        return f"{row['problem']} · {row['vehicle']} · 行程 {row['trip_id'].split('::')[-1]}"

    selected = st.selectbox("選擇待辦案件", list(choices), format_func=choice_label, key="action_case")
    action = choices[selected]
    with st.container(border=True):
        st.markdown(f"### {action['problem']}")
        owner, helpers = st.columns(2)
        owner.markdown(f"**主要負責：{labels.get(action['primary_owner'], action['primary_owner'])}**")
        helpers.markdown(f"**協作角色：{role_names(action['supporting_roles'], labels) or '依核對結果指派'}**")
        st.write("**證據｜** " + action["evidence"])
        st.write("**待核對｜** " + action["handoff_reason"])
        st.write("**建議下一步｜** " + action["action"])
        if action["primary_owner"] == "DISPATCHER":
            st.caption("調度提示：可先到「車隊總覽」查看跨車怠速熱點，再核對到站時窗與停留用途。")
        st.caption(f"車輛 {action['vehicle']} · {action['trip_id']} · {action['source']}")

    demonstration = st.checkbox("操作示範紀錄（與實際試行分開保存）", value=True, key="action_demo_scope")
    store = ActionStore()
    record = store.load(action, demonstration=demonstration)
    scope = "demo" if demonstration else "pilot"
    key = f"{scope}_{selected}"
    default_date = datetime.now(ZoneInfo("Asia/Taipei")).date() + timedelta(days=7)
    with st.form(f"action_form_{key}"):
        measures = st.text_area("執行措施", value=record["measures"] if record else "",
                                placeholder="例如：與客戶核對卸貨時窗，調整到站時間；下一週追蹤同條件行程。",
                                height=90, key=f"measures_{key}")
        status_col, date_col = st.columns(2)
        status = status_col.selectbox("追蹤狀態", ACTION_STATUSES,
                                      index=ACTION_STATUSES.index(record["status"]) if record else 0,
                                      key=f"status_{key}")
        follow_up = date_col.date_input("下次追蹤日期", value=date.fromisoformat(record["follow_up_date"]) if record else default_date,
                                        key=f"follow_up_{key}")
        submitted = st.form_submit_button("保存行動紀錄", type="primary", key="save_action")
    if submitted:
        try:
            record = store.save(action, measures=measures, status=status, follow_up_date=follow_up, demonstration=demonstration)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.success(("操作示範紀錄" if demonstration else "實際試行紀錄") + "已保存；重新開啟仍可讀取。")
    if record:
        st.info(f"已保存：{record['status']} · 下次追蹤 {record['follow_up_date']} · {VERIFICATION_PENDING}。")
    else:
        st.caption("保存措施後持續追蹤；採納或執行不代表已證實節油，成效仍待後續可比較行程驗證。")
    records = store.records(demonstration=demonstration)
    if records:
        with st.expander(f"已保存的{'操作示範' if demonstration else '實際試行'}紀錄（{len(records)}）"):
            history = pd.DataFrame(records)[["trip_id", "problem", "measures", "status", "follow_up_date", "verification"]]
            history.columns = ["行程", "問題", "執行措施", "狀態", "下次追蹤", "成效驗證"]
            st.dataframe(history, hide_index=True, width="stretch")
