# HINO EcoPilot｜資料與假設

Primary Evidence Mode 只用此次 Competition Core 的 RAW／DERIVED。Mock Context 是正式產品 C／D 層情境的 placeholder，用於角色展示和未來欄位需求，不能決定 Expected Fuel、Benchmark Quality、Vehicle Health、Maintenance 或主要 KPI。四層來源見 [資料能力矩陣](data_capability_matrix.md)；來源優先級見 [來源契約](source_contract.md)。

## Type 與原始資料

Type 為 HINO 車型系列代碼；300／500／700 分別代表 HINO 300／500／700 系列。現有資料不足以確認細部車型、噸位與引擎規格，因此僅用於系列分組比較。

原始來源為使用者提供的 HINO iTRAQ XLSX。時間無時區資訊，依 Asia/Taipei 解讀是明示假設。單位只依欄位對照表，缺確認時不計算帶 L／km 單位的指標。原始檔唯讀且以 SHA-256 校驗。

## 最小 Mock Set

每趟以 seed=42 與 SHA-256 建立獨立 RNG，輸入列順序不影響結果；規則版本 v2。存於 data/mock/trip_context_mock.parquet，依 trip_id 一對一連接。主分析先完成，再附加 Mock；ML 使用附加前的 evidence-only 表。

| Mock field | 具體產品用途 | 產生規則 |
| --- | --- | --- |
| driver_id | Driver Eco Coach 的模擬身分 | 每車固定兩至三個虛擬代碼，依日期／日夜輪替 |
| task_type | 行程前 Demo Task Context | ≥80 km 跨城；其餘 75% 配送、25% 調度 |
| payload_ratio | Trip Explorer Future Enrichment | 跨城 Beta(5,2)、配送 Beta(3,3)、調度 Beta(2,4)；第一參數加入系列雜湊偏移 0–0.4 |
| traffic_level | 行程前路況情境 | 尖峰 07–09／16–19 高中低機率 65/25/10%；其餘 15/40/45% |
| delivery_window | 行程前、調度窗口核對 | 起始整點至兩小時後 |
| stop_purpose | Trip Explorer 與熱點的待核對用途 | 怠速 >20 分鐘時等待／配送／休息／未知機率 55/25/10/10%；其餘依任務 |
| mock_generation_rule | Data & Assumptions 重現性 | v2、種子、每趟穩定雜湊 |
| is_mock | MOCK badge／來源分類 | 僅標記營運情境，不表示真實車聯網是虛構 |

刪除沒有產品用途的 driver_experience_years、task_id、planned_distance_km、shift_type、task_priority、weather。天氣仍是未來需串接的真實欄位，不再合成。

## 比較與啟發式的界線

Benchmark Quality 依 peer count、vehicle count、IQR/median、L1–L3 決定，是 comparison evidence strength，不是資料品質、概率或因果信心。改善槓桿用相對行為差正規化成優先度，未使用 HINO 係數或 ML 因果學習。本版本不保留 scenario saving、公升分攤或每月節油外推。

車況配對近似比較已觀測條件；15% 殘差及連續三趟是原型 heuristic。DTC 是待核對事件，不是確診結果。完整公式見 [分析方法](methodology.md)。

## 已知限制與 Future Enrichment

- 20 台車、歷史資料，並非完整出勤日曆；缺一天資料不能推論沒有出勤。
- 累積燃油常以 0.5 L 更新，短程比例不穩定；排除條件仍可能改變可比較樣本的代表性。
- GPS 端點格網不是道路、坡度或作業等價；高強度比較仍有未觀測因素。
- 此次競賽缺真實 Driver ID、Task ID、載重、交通、天氣、停靠目的、交付窗口與維修紀錄。iTRAQ 參考 schema 有 driverUid／tachographDriver、燃油率、踏板、檔位、PTO 等欄位，但不是此次實測值，正式可用性待依設備及管線確認；已作廢胎壓表不納入分析。
- 歷史 benchmark 參考完整資料期間，包含目標趟之後資料；不能稱為事前預測。
- ML GroupKFold 與時間 holdout 是回顧驗證；同車可能跨時間切分，行為在行程後才已知。
- API 故障或回覆不合格時核心離線功能仍可用；本機規則不能全面保證語言語意，正式導入需額外 eval。
- 比較差距不能證明可省燃油；角色待辦不能證明問題已解決；需要 Pilot 對照及 closed-loop measurement。

## Pilot 建議紀錄

以真實任務、載重、交通條件確認可比較性；記錄 Problem、Owner、Evidence、Action、接手時間與處理狀態。導入後以同條件觀測燃油、里程、怠速與支持趟數追蹤，並保留未採行組或其他適當對照。這是驗證計畫，Prototype 尚未取得成效證據。

## 事件與怠速補充

`idle_minutes` 是 `carStatus=idling` 加有效 timestamp interval 的 Vehicle State Duration，不是 Event 2 duration。來源 Event 6／7／8／11 的設定可能不同，只作 Supporting Evidence；Event 8 門檻有 `SOURCE_CONFLICT`，不重建。`engine_load_above_90_ratio` 不等於 Event 11。缺 `ptoSwitch`、任務與停留用途，不能把觀測怠速直接判定為可避免浪費。
