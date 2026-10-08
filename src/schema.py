"""Column-level provenance and definitions; fail on undocumented derived fields."""
import pandas as pd

from src.mock_context import MOCK_RULES
from src.config import HINO_SERIES, TYPE_DEFINITION, LEVER_FEATURES
from src.utils import markdown_table
from src.utils import write_processed_parquet

DEFINITIONS = {
    "trip_id": "車輛識別碼與行程編號經網址安全編碼後，以 :: 組成唯一行程鍵",
    "vehicle_type": TYPE_DEFINITION,
    "start_time": "行程第一筆有效時間", "end_time": "行程最後一筆有效時間",
    "duration_minutes": "行程起訖時間差換算為分鐘，包含未觀測區段",
    "observed_minutes": "相鄰時間大於零且不超過 300 秒的有效間隔總分鐘數",
    "unobserved_minutes": "行程總時長扣除已觀測分鐘數",
    "unknown_status_minutes": "有效時間間隔內，車輛狀態未知的分鐘數",
    "sample_count": "去除同一行程重複時間後的有效資料列數", "raw_sample_count": "同一行程的原始資料列數",
    "start_lat": "第一筆有效 GPS 緯度", "start_lon": "第一筆有效 GPS 經度",
    "end_lat": "最後一筆有效 GPS 緯度", "end_lon": "最後一筆有效 GPS 經度",
    "driving_minutes": "原始狀態為行駛時的有效前向間隔總分鐘數",
    "idle_minutes": "carStatus=idling 的有效前向時間間隔總分鐘數；不是 Event 2 duration，亦不判定為浪費",
    "parking_minutes": "原始狀態為停車時的有效前向間隔總分鐘數",
    "idle_ratio": "怠速時間除以怠速與行駛時間總和；分母為零時留空",
    "trip_distance_km": "相鄰有效累積里程的非負差分總和；沒有可用差分時留空",
    "trip_fuel_l": "相鄰有效累積燃油的非負差分總和；沒有可用差分時留空",
    "km_per_l": "行程里程除以行程燃油；分母為零時留空",
    "fuel_l_per_100km": "行程燃油除以行程里程，再乘以 100；分母為零時留空",
    "avg_speed": "行駛狀態下按有效秒數加權的平均車速；CAN status=0 才優先採 CAN，否則回退有效 GPS",
    "max_speed": "CAN status=0 才採 CAN、否則回退 GPS 的有效速度最大值（公里／小時）",
    "avg_rpm": "引擎運轉時按有效秒數加權的平均轉速", "p95_rpm": "引擎運轉時按有效秒數加權的第 95 百分位轉速",
    "rpm_above_2500_ratio": "EcoPilot 原型衍生特徵：轉速超過 2,500 RPM 的有效引擎運轉時間比例；不是 HINO 官方事件門檻",
    "avg_engine_load": "引擎運轉時按有效秒數加權的平均負載百分比",
    "p95_engine_load": "引擎運轉時按有效秒數加權的第 95 百分位負載百分比",
    "engine_load_above_90_ratio": "EcoPilot 原型衍生特徵：負載超過 90% 的有效引擎運轉時間比例；不等於來源 Event 11",
    "can_status_state": "行程 CAN 狀態：任一非零為 ABNORMAL；否則任一缺失為 UNKNOWN；全為零才 NORMAL",
    "event_count": "去除同一事件重複通報後的總事件數", "stop_count": "進入怠速或停車狀態的連續區段數；長缺口會中斷區段",
    "coverage_ratio": "已觀測時間除以行程總時長；零時長時設為零",
    "data_quality_score": "從 100 分扣除各項品質問題的分數；詳見分析方法第 4 節",
    "benchmark_eligible": "品質分數、里程、燃油與覆蓋率達門檻，且沒有累積讀值或 Type 衝突的行程",
    "origin_cell": "第一筆有效 GPS 經緯度四捨五入至小數點後兩位", "destination_cell": "最後一筆有效 GPS 經緯度四捨五入至小數點後兩位",
    "route_id": "HINO 系列（Type）結合方向性的起終點格網；缺少必要座標時為未知",
    "distance_bin": "里程區間：0–5、5–20、20–50、50–100、100–200、200 公里以上",
    "time_of_day": "依行程開始時間分為早間、日間、傍晚或夜間",
    "benchmark_level": "第一個符合至少五趟、兩台其他車的比較層級 L1／L2／L3；否則為證據不足",
    "peer_trip_count": "入選的其他車輛相似行程數",
    "peer_vehicle_count": "入選相似行程涉及的其他車輛數",
    "peer_fuel_median_l_per_km": "相似行程每公里燃油強度的中位數（L/km）",
    "peer_fuel_iqr_l_per_km": "同儕燃油強度第 75 減第 25 百分位（L/km）",
    "benchmark_dispersion": "同儕燃油強度 IQR / median；無單位",
    "benchmark_quality": "比較證據強度 HIGH／MEDIUM／LOW；依層級、趟數、車數與離散程度；非品質分數或機率；不足時留空",
    "evidence_mode": "PRIMARY_EVIDENCE_MODE：主要分析僅 RAW／DERIVED",
    "benchmark_gap_l": "max(實際燃油 − 相似行程預期燃油, 0)；是相較同儕燃油差距，並非可實現節省",
    "benchmark_gap_pct": "燃油差距 / 本趟實際燃油 × 100；分母為零或不足時留空",
    "lever_status": "HEURISTIC_PRIORITY 表示行為與同儕證據齊全；不足時 INSUFFICIENT_DATA",
    "expected_fuel_l": "相似行程每公里燃油強度乘以本趟里程",
    "expected_km_per_l": "相似行程燃油強度的倒數（公里／公升）",
    "opportunity_status": "OBSERVED_COMPARISON 或 INSUFFICIENT_DATA；未知不當零",
    "health_expected_fuel_l": "跨車配對行程的加權燃油強度中位數乘以本趟里程",
    "health_peer_count": "支援車況配對的其他行程數，最多 20 趟",
    "health_peer_vehicle_count": "支援車況配對的其他車輛數，至少兩台",
    "health_match_distance": "入選車況配對行程的平均特徵距離；數值越小越相似",
    "vehicle_residual_ratio": "實測燃油相對於配對預期燃油的比例差異",
    "consecutive_anomaly_trips": "依時間排序、殘差連續超過 15% 的行程數；未知或不合格行程會中斷",
    "vehicle_health_flag": "連續至少三趟符合異常條件的檢查訊號；不是故障診斷",
}
FLAGS = {
    "fuel_reset_flag": "任一相鄰累積燃油讀值出現負差分", "mileage_reset_flag": "任一相鄰累積里程讀值出現負差分",
    "fuel_missing_flag": "任一有效行程列的累積燃油讀值缺失", "mileage_missing_flag": "任一有效行程列的累積里程讀值缺失",
    "large_timestamp_gap_flag": "任一相鄰時間間隔超過 300 秒", "missing_gps_flag": "任一 GPS 座標缺失、超界或為 (0,0)",
    "low_sample_count_flag": "有效資料列少於五筆", "duplicate_timestamp_flag": "同一行程出現重複時間戳記",
    "gps_speed_conflict_flag": "GPS 顯示零速但 CAN 速度超過 5 公里／小時", "implausible_mileage_flag": "里程增量超過依時間間隔計算的原型上限",
    "can_error_flag": "任一原始 CAN 狀態有值且非零；來源特定錯誤碼不推定 Bus 組合",
    "can_status_unknown_flag": "任一原始 CAN 狀態缺失，不能視為正常",
    "type_conflict_flag": "同一行程出現多種HINO 系列（Type）",
}
EVENT_COUNTS = {"rapid_accel_event_count": 6, "rapid_decel_event_count": 7,
                "speeding_event_count": 8, "engine_overload_event_count": 11, "dtc_event_count": 9}
FEATURE_NAMES = {"idle_ratio": "觀測怠速時間比例", "rpm_above_2500_ratio": "轉速超過 2,500 RPM 時間比例",
                 "engine_load_above_90_ratio": "負載超過 90% 時間比例"}


def build_dictionary(columns, profile=None):
    profile = profile or {}
    rows = []
    for column in columns:
        source = "DERIVED"
        limitations = "衍生統計受資料品質與原型假設限制，參見「分析方法」分頁；不是新增量測。"
        used = "行程分析／品質檢查／介面呈現／決策依據"
        if column in MOCK_RULES:
            source, calculation = "MOCK", MOCK_RULES[column]
            limitations = "模擬資料僅供原型展示；不是 HINO 真實營運資料。隨機種子為 42。"
            used = "Demo Persona Context／Future Enrichment；禁止用於主要分析"
        elif column in ["enabledCode", "journeyCode"]:
            source, calculation = "RAW", "直接保留原始活頁簿欄位作為字串識別碼"
            limitations = "journeyCode 非全資料唯一；必須與 enabledCode 配對。"
        elif column == "Type":
            source, calculation = "RAW", TYPE_DEFINITION
        elif column in DEFINITIONS:
            calculation = DEFINITIONS[column]
        elif column in FLAGS:
            calculation = FLAGS[column]
        elif column in EVENT_COUNTS:
            calculation = f"iTRAQ 來源類型代碼 {EVENT_COUNTS[column]} 去重事件次數；不是 EcoPilot 自行重建或跨車標準化績效"
            limitations = "來源事件門檻可能依車輛、客戶與時間設定；僅供核對。DTC 次數不是故障碼數量或確診數。"
        elif column.startswith("peer_"):
            feature = column.removeprefix("peer_")
            calculation = f"排除目標車輛後，入選相似行程的{FEATURE_NAMES.get(feature, feature)}中位數"
        elif column.endswith("_excess_score"):
            calculation = "正向行為差 /（正向差 + max(abs(peer median), 尺度下限)）；0–1 heuristic，用於相對優先度，非機率"
        elif column.endswith("_priority_pct"):
            calculation = "各槓桿 excess score / 三項 score 總和 × 100；全零則為零；任一缺失則全留空；不是節油比例"
        elif column in profile.get("columns", {}):
            source, calculation = "RAW", "原始活頁簿直接保留；單位見欄位對照表"
            limitations = "缺值不補造；原始來源可追溯到來源列號 source_row。"
        else:
            raise ValueError(f"Undocumented column: {column}")
        if "expected" in column or "saving" in column or "prediction" in column or column.startswith("peer_"):
            limitations += " 觀測比較估計，非因果證明；只用 RAW／DERIVED，仍缺真實載重與任務條件。"
        rows.append({"column": column, "description": calculation, "source_type": source, "used_for": used,
                     "calculation": calculation, "limitations": limitations})
    return pd.DataFrame(rows)


def write_dictionary(trips, root, profile):
    dictionary = build_dictionary(trips.columns, profile)
    write_processed_parquet(dictionary, root / "data/processed/data_dictionary.parquet")
    raw = build_dictionary(profile["columns"], profile)
    labels = {"column": "原始欄位代碼", "description": "欄位定義", "source_type": "資料來源", "used_for": "用途", "calculation": "計算方式", "limitations": "限制"}
    def readable(frame):
        return frame.assign(source_type=frame.source_type.map({"RAW": "原始資料 RAW", "DERIVED": "衍生資料 DERIVED", "MOCK": "模擬資料 MOCK"})).rename(columns=labels)
    content = "# 資料欄位字典\n\n每個衍生行程欄位的來源與定義。RAW／DERIVED／MOCK 互斥；is_mock 僅標記模擬營運情境，不表示整趟車聯網原始資料為虛構。\n\n## 衍生行程欄位\n\n"
    content += markdown_table(readable(dictionary).to_dict("records"), list(labels.values()))
    content += "\n\n## 原始活頁簿欄位\n\n" + markdown_table(readable(raw).to_dict("records"), list(labels.values()))
    (root / "docs/data_dictionary.md").write_text(content + "\n", encoding="utf-8")
    return dictionary
