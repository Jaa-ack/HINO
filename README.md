# HINO EcoPilot｜車隊協同節能決策原型

HINO EcoPilot 將 iTRAQ 車聯網資料整理成可比較的行程證據，先判斷是否存在燃油效率差距，再找出值得優先核對的操作、怠速／停留及車輛效率訊號，最後把問題交給真正有權處理的角色。系統不把高油耗直接歸責於駕駛，也不把來源事件次數直接視為標準化績效。

這是離線歷史資料 Prototype：Competition Core RAW／DERIVED 驅動主要分析，Mock 是 Production Context 的展示 placeholder。Historical Replay 不代表即時 Coaching；Benchmark Gap 不等於保證節省；車況訊號不診斷故障。真正節油成果須由 Pilot 閉環驗證。

## 五分鐘展示

1. **資料旅程**：指出此次 Competition Core、Extended iTRAQ Production Reference、企業營運情境與外部資料四層。0929 XLSX 是參考 metadata，不是第二份 telemetry。
2. **車隊總覽**：看總里程、觀測燃油、km/L、觀測怠速比例與有比較支持的燃油差距；不把怠速或差距稱為已節省。
3. **行程探索**：`enabledCode + journeyCode` 還原一車一趟；Idle Duration 取自 `carStatus + timestamp`，不是 Event 2。Comparable Benchmark 排除本車。三項槓桿只排序核對優先度；Event 6／7／8／11 只作設定依賴的 Supporting Evidence。
4. **駕駛節能教練**：案例 B 是「操作型態待核對」，不是判定駕駛錯誤；歷史回放不是 Live Alert。
5. **管理行動中心**：在「行動工作台」按角色選擇案件，查看主要負責人、協作角色、證據與待核對項目，填寫執行措施、追蹤狀態與下次追蹤日期並保存。負載需先核對載重、坡度、任務與車況；低證據先補資料。「全部待辦」可下載 CSV，「車況證據」可核對連續殘差。
6. **資料與假設**：查看來源事件衝突、四層能力矩陣、模型基線驗證與 Pilot 空白成效模板。GenAI 只把已計算證據轉成角色化下一步。

## 此次 Competition Data 與 Production Reference

| 層級 | 內容 | 目前地位 |
| --- | --- | --- |
| A Competition Core | 20 台車、`enabledCode`、`journeyCode`、Type、GPS、里程、燃油、RPM、負載、carStatus、來源 Events 等 | 此次 XLSX 實際觀測，進主要分析 |
| B Extended iTRAQ | `driverUid`、`tachographDriver`、`engineFuelRate`、`instantaneousFuel`、`pedalPosition`、`gearBoxPosition`、`ptoSwitch` 等 | 0929 已遷移 Rawdata 的參考 schema；競賽 extract 沒有，正式可用性待確認 |
| C Enterprise Context | Task、Actual Payload、Delivery Window、Stop Purpose、Maintenance | 需企業營運系統介接 |
| D External Context | Traffic、Weather、Gradient | 選配外部來源 |

`driver_id`、任務／載重／停靠用途與路況在 Prototype 為 MOCK。正式產品應先確認 iTRAQ 的 `driverUid`／`tachographDriver` 等欄位，並依車型、設備及資料管線查證；不預設需增設感測器，也不把參考 schema 當成此次競賽實測值。`ptoSwitch` 不在競賽資料，故目前無法判定怠速是否可避免。詳見 [來源契約](docs/source_contract.md)、[資料能力矩陣](docs/data_capability_matrix.md) 與 [事件參考](docs/event_reference.md)。

FAQ 與 0929 參考表對 Event 8 超速預設門檻不同，標記 `SOURCE_CONFLICT`。EcoPilot 不重建 Event 8；僅保留 iTRAQ 系統通報的去重次數。Event 6／7／8／11 設定可能依客戶與時期變動，不直接作跨車績效或主要 ML 特徵。`rpm_above_2500_ratio` 與 `engine_load_above_90_ratio` 是 EcoPilot 原型衍生門檻，不等於 HINO 官方 Event 11。

## 快速啟動與重建

需要 Python 3.14；本機驗證為 macOS ARM64／Python 3.14.3。Git 版本只包含程式與公開文件，原始資料、分析產物、私密設定及影片製作檔保留在本機；位置與上傳規則見 [Git 與本機檔案管理](docs/repository.md)。交付 ZIP 不含 `.venv`。已有本機分析資料時，在專案目錄執行：

```bash
./ecopilot setup
./ecopilot check
./ecopilot start
```

開啟 <http://127.0.0.1:18501>；啟動終端以 Ctrl+C 停止。若只取得程式碼，將競賽原始 XLSX 放入 `data/raw/`，將 FAQ PDF 與 `Event Type_0929補充.xlsx` 放入 `data/reference/`，然後執行：

```bash
./ecopilot build --ml
./ecopilot test -q
./ecopilot start
```

來源 SHA-256 相同時重用 raw Parquet 快取；`--force` 可重新讀 XLSX。原始來源不寫回，補充 XLSX 不併入 telemetry。六頁分析讀取本機處理產物；管理行動中心另外將人工填寫的措施保存到 `data/pilot/action_tracking.sqlite3`，不改寫來源或分析結果。可選配 GenAI：設定 `.env` 的 API key、模型及 `ECOPILOT_ENABLE_LLM=true`，在行程頁主動按鈕；外送只含匿名 trip key、角色與白名單結構化證據，不送原始 ID、GPS 或 Mock，API 不可用時回退離線範本。

行動工作台預設勾選「操作示範紀錄」，與實際試行分開讀寫；同一趟行程的不同問題各自保存，重新開啟可繼續編輯。紀錄時間與預設追蹤日期使用 Asia/Taipei。狀態為「待核對／已採納／執行中／待驗證」，只記錄人工填寫的進度，不判定執行成功或節油；所有狀態均標示「待後續可比較行程驗證」。這是本機原型，尚未提供多人帳號、通知、企業工單介接或自動前後成效驗證。測試或獨立展示可透過 `ECOPILOT_ACTION_DB` 指定另一個 SQLite 檔案。

## 方法與重建後結果

流程：iTRAQ Competition Data → Data Quality → Trip Reconstruction → Comparable Trip Benchmark → Benchmark Fuel Gap → 三項 Improvement Lever Screening → Vehicle Efficiency Signal → Owner Assignment → Decision Packet → GenAI Persona Recommendation → Action → Pilot Outcome Validation。`RAW / DERIVED / MOCK` 僅描述 Prototype runtime 來源；四層能力矩陣描述正式產品可接資料來源，兩者用途不同。

2026-10-02 執行 `./ecopilot build --ml`：493,744 原始列、55 欄、111,172 事件紀錄，彙整 3,541 趟、20 台車；1,401 趟符合比較前品質條件。1,383 趟得到同儕支持（L2 1,146、L3 237；L1 0），MEDIUM 1,065、LOW 318、HIGH 0。正向 Benchmark Gap 合計 **1,631.785 L**，不是可實現節省。車況檢查訊號 **34 趟／7 台車**；行動待辦 **2,969 筆**（包含比較證據不足的補證據待辦）。Event 6／7 移除後，車況訊號數值已由新模型重算。

Random Forest 只作 Validation／Scenario Support，6 個數值特徵加 `vehicle_type`、`route_id`、`time_of_day`；不含來源 Event 6／7 或 Mock。預處理與兩個 baseline 在各訓練折內擬合。

| 驗證 | RF MAE | RF R² | Baseline A MAE | Baseline B MAE | RF 相對 A／B 的 MAE 變化 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5-fold GroupKFold by vehicle，1,401 趟 | 2.298 L | 0.835 | 3.483 L | 2.346 L | 34.02%／2.02% |
| 時間 holdout，訓練 1,115、測試 281 趟 | 1.452 L | 0.825 | 3.448 L | 1.790 L | 57.88%／18.87% |

MAE 變化是回顧預測誤差變化，不是節油成效。時間 holdout 可能包含相同車輛，行程後特徵不能當成出發前預測。完整公式與限制見 [分析方法](docs/methodology.md)、[假設](docs/assumptions.md)。

## Production Roadmap 與交付

Stage 1：Competition Core 與本機 Recommendation → Action 追蹤已可用。Stage 2：確認 Extended iTRAQ 的駕駛、燃油率、踏板、檔位與 PTO 欄位。Stage 3：介接企業 Task、Payload、Delivery Window、Stop Purpose、Maintenance。Stage 4：接入外部 Traffic、Weather、Gradient。Stage 5：Live Stream 與完整 Recommendation → Action → Outcome → Learning 閉環；在真實試行中以採納率、執行率、可比較前後與可行時對照組驗證，操作示範紀錄不計入實際成果。空白 [Pilot outcome 模板](data/pilot/action_outcomes_template.csv) 不含虛構成果。

```bash
./ecopilot python -m compileall -q src scripts tests pages app.py
./ecopilot test -q
./ecopilot python scripts/package_delivery.py --output ../.local-only/deliveries/hino-ecopilot-delivery.zip
```

交付 ZIP 保存在專案旁的 `.local-only/deliveries/`，包含原始競賽 XLSX、FAQ、0929 參考檔、來源登錄、處理資料、六頁程式與文件；排除 `.venv`、快取與 `.env`。這是含私密資料的完整交付包，不納入 Git 上傳。完整檢查結果見 [第二輪一致化報告](docs/final_alignment_report.md)。
