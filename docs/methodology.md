# HINO EcoPilot｜分析方法 v3

Primary Evidence Mode：比較基準、燃油差距、槓桿、車況訊號及主要 ML 僅用 Competition Core 的 RAW／DERIVED。資料來源優先級、SHA 與 Event 8 衝突見 [來源契約](source_contract.md)。燃油差距不是可實現節省。

## 資料與行程

`output data_Hotai_20260511.xlsx` 以唯讀方式檢查，`raw_snapshot` 保留原欄與 `source_row`，來源 SHA-256 在建置前後核對。`Event Type_0929補充.xlsx` 是 reference metadata，只產生 `data/reference` 的事件、擴充欄位及能力矩陣；不 append／merge 到 raw snapshot、telemetry 或 trips。FAQ 為定義與限制來源。已作廢胎壓表不進分析。

行程鍵為 `enabledCode + journeyCode`；同時間的原始列保留，計算採最後來源列。相鄰前向間隔僅接受 0–300 秒；長缺口標為未觀測。`idle_minutes` 由 `carStatus=idling` 的有效 interval 加總，**不是 Event 2 次數或 event duration**。競賽欄位對照表的 `event[n].info.duration` 單位是秒。靜止但引擎運轉可為 PTO／設備作業，現有資料缺 `ptoSwitch` 與真實停靠用途，不能判為浪費。

累積里程、燃油只加總相鄰有效讀值的非負差分；重設、缺值、時間缺口與里程跳點留品質旗標。單位以競賽欄位對照表為準；不明單位不產生 L／km 指標。車型 Type 300／500／700 是 HINO 系列，不代表細車型、噸位或引擎。

## CAN 與衍生特徵

`can_status_state`：0→NORMAL；任何非零→ABNORMAL；缺值→UNKNOWN。`can_error_flag` 於有值且非零成立；`can_status_unknown_flag` 記缺值。此次 extract 有 0、9；不將 9 解釋為特定 CAN Bus 組合。只有 CAN status=0 且速度 0–160 km/h，才採 `CAN_CONFIRMED`；其餘退回有效 GPS speed，標為 `GPS_FALLBACK`，都無效則 `UNKNOWN`。RAW 不改寫。

`rpm_above_2500_ratio` 為 RPM >2500 的有效引擎運轉時間比例；`engine_load_above_90_ratio` 為負載 >90% 的比例。兩者都是 EcoPilot Prototype threshold，**不是 HINO 官方事件門檻**，後者不等於來源 Event 11。事件長表保存所有 `event[n]` 原內容，依行程、類型、開始時間去重後得到 `rapid_accel_event_count`、`rapid_decel_event_count`、`speeding_event_count`、`engine_overload_event_count`、`dtc_event_count`。DTC 事件次數不是故障碼數或確診數。Event 6／7／8／11 的門檻可調，僅作 Supporting Evidence；Event 8 不自行重建，詳見 [事件參考](event_reference.md)。

## Comparable Trip Benchmark

合格行程需品質分數 ≥70、里程 ≥5 km、燃油 ≥1 L、時間覆蓋率 ≥80%，且無關鍵讀值重設、缺漏、里程跳點或 Type 衝突。基準排除目標車；每層至少五趟、兩台其他車。L1：同系列＋路線端點格網＋里程區間＋時段；L2：同系列＋里程區間＋時段；L3：同系列＋里程區間。都不足則留空。同儕 median L/km × 本趟里程為 `expected_fuel_l`；另記 IQR、dispersion 與 HIGH／MEDIUM／LOW 比較證據強度。燃油差距 `max(actual−expected,0)`，百分比以 actual 為分母；未知不補零。歷史全期基準可能含目標趟之後的行程，不能視為前瞻預測。

## 三項 Improvement Levers

`idle_context`、`rpm`、`engine_load` 對應 `idle_ratio`、`rpm_above_2500_ratio`、`engine_load_above_90_ratio`。同一批入選同儕中位數必須各有至少五個非缺值。`excess=max(observed−peer,0)`；`score=excess/(excess+max(abs(peer),0.05))`；三項 score 正規化成 `idle_context_priority_pct`、`rpm_priority_pct`、`engine_load_priority_pct`。任一必要值缺失時三項優先度留空且 `lever_status=INSUFFICIENT_DATA`；全可比較但沒有正向超額時均為 0。這是核對優先度，不是因果比例、節油率或可省公升；Event 6／7 次數不進槓桿。

## Vehicle Efficiency Check Signal

同系列、同里程區間、合格且排除本車。觀測配對特徵：`trip_distance_km`、`duration_minutes`、`route_id`、`idle_ratio`、`rpm_above_2500_ratio`、`engine_load_above_90_ratio`、`avg_speed`；系列是先篩條件。距離對數、比例及速度差按原型尺度標準化，路線不同加 1；距離 ≤8 最近最多 20 趟，至少五趟與兩台其他車。Event 6／7 不參與配對。依 `1/(1+match_distance)` 加權中位數形成期望燃油；殘差 >15% 連續三趟給檢查訊號。未知或不合格行程中斷序列。DTC 只增加核對證據；不診斷故障、不分配維修節油量。

## 選配 ML 驗證

RandomForestRegressor，100 trees、max_depth=9、min_samples_leaf=5、seed=42。數值特徵只有 `trip_distance_km`、`duration_minutes`、`idle_ratio`、`rpm_above_2500_ratio`、`engine_load_above_90_ratio`、`avg_speed`；類別特徵 `vehicle_type`、`route_id`、`time_of_day`。Event 6／7 及所有 Mock 不進主要 ML。GroupKFold 依 `enabledCode` 整車留出，預處理與模型僅在訓練折擬合。Baseline A 是訓練折 median L/km × 測試里程；Baseline B 為系列＋里程區間 median L/km，未知分組退回 A。另設不重疊時間 holdout；兩側可能仍有同車。報告 MAE、R² 及相對 baseline 的**預測誤差變化**，不是節油成效。模型不驅動核心基準、車況訊號或 KPI。

## Owner、GenAI 與 Pilot

Decision Packet 包含 evidence_id/source_type/field/value/unit、三項槓桿、`primary_owner`、`supporting_roles`、`handoff_reason` 與 `owner_confidence`。後者只表示路由所需證據完整度，不是模型機率。怠速／停留→DISPATCHER＋DRIVER；轉速→DRIVER＋FLEET_MANAGER；負載→FLEET_MANAGER＋DISPATCHER／MAINTENANCE；車況／DTC→MAINTENANCE＋FLEET_MANAGER；低或不足比較證據→FLEET_MANAGER 先補證據。不可從高負載或來源事件次數直接歸責駕駛。

Python 計算全部數值；選配 GenAI 只把白名單結構化證據轉為定性語句，外送匿名 key、不送原始 ID／GPS／Mock，且失敗時回退離線範本。採行與成效需按 [Pilot 驗證](pilot_validation.md) 記錄，目前模板沒有虛構 outcome。
