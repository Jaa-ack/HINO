"""Select real evidence; absence is a valid result, not permission to fabricate."""
import pandas as pd

from src.recommendations import decision_packet


def select_demo_cases(trips):
    cases = {}
    selected = set()
    labels = {"A": "怠速／停留情境待核對", "B": "操作型態待核對案例", "C": "車況檢查訊號"}
    owners = pd.Series({idx: decision_packet(t)['primary_owner'] for idx, t in trips.iterrows()}, dtype='object')
    for key in ["A", "B", "C"]:
        pool = trips.loc[~trips.trip_id.isin(selected)].copy()
        if key in {"A", "B"}:
            role = 'DISPATCHER' if key == 'A' else 'DRIVER'
            pool = pool.loc[pool.benchmark_quality.isin(['MEDIUM', 'HIGH']) & owners.loc[pool.index].eq(role)]
        if key == "A":
            score = (pool.benchmark_gap_l * pool.idle_context_priority_pct / 100)
        elif key == "B":
            score = pool.benchmark_gap_l * pool.rpm_priority_pct / 100
        else:
            score = pool.get("vehicle_residual_ratio", pd.Series(float("nan"), index=pool.index)).where(pool.vehicle_health_flag)
        pool = pool.loc[score.notna() & score.gt(0)]
        if pool.empty:
            cases[key] = {"label": labels[key], "trip_id": None, "reason": "目前資料不足以判斷；沒有符合證據強度、負責角色與案例條件的不同真實行程。"}
        else:
            winner = pool.assign(_score=score.loc[pool.index]).sort_values(["_score", "trip_id"], ascending=[False, True]).iloc[0]
            selected.add(winner.trip_id)
            cases[key] = {"label": labels[key], "trip_id": winner.trip_id, "source_type": "DERIVED", "reason": "依真實車聯網資料的衍生指標選取；A／B 需中等以上比較證據且主責分別為調度／駕駛，C 需持續車況檢查訊號。MOCK 未參與案例排序。"}
    return cases
