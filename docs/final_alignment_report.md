# HINO EcoPilot｜第二輪資料定義校正與提案一致化報告

查核日期：2026-10-02。直接修改既有專案；保留複合行程鍵、RAW／DERIVED／MOCK 分離、跨車 Benchmark、Gap 非節油承諾、離線回退、GroupKFold／baseline、來源 SHA-256 與不含 `.venv` 的交付方式。

## Source Audit

| 來源 | 查核結果 |
| --- | --- |
| Competition XLSX：`output` + `欄位對照表` | 493,744 資料列、55 欄。`can.canStatus` 實際有 0／9；`event[n].info.duration` 對照單位為秒。原始 SHA-256：`a58e9f0a372d8f0372b3b2e8d634ab411e0f28c527251679a0770b1271d6794b`。 |
| HINO competition FAQ PDF | 第 2–3 頁：Event 8 預設超速容許值 0 km/h，可由客戶調整，歷史各車設定不可追溯。第 4–6 頁：Event 7 門檻可調。第 10 頁：idling 為車輛靜止、引擎未熄火，競賽資料無駕駛身分。 |
| `Event Type_0929補充.xlsx` / `event代碼` | Event 2、6、7、8、11 的描述及可調參數；Event 8 與 FAQ 不同，登錄 `SOURCE_CONFLICT`，不重建門檻。 |
| 同 XLSX 的三張已遷移 Rawdata sheet | 314 個去重 field／sheet 記錄。可查 `driverUid`、燃油率、踏板、檔位、PTO 等，但本次 extract 沒有，正式供應待確認。14V3 的 `duration` 標分鐘，與 Competition 對照表的秒不一致，登錄 `REFERENCE_CONFLICT` 並以 Competition 為準。 |
| `14.1-胎壓資料格式(已作廢)` | Deprecated reference，不進分析。 |

參考 XLSX 與 FAQ 保存在 `data/reference`，source registry 列 SHA-256；pipeline 不將參考列合併到 telemetry／trips。事件及欄位 reference 產物與四層能力矩陣由實際 XLSX 產生。

## 第二輪方法與 Schema 修正

- CAN：0=NORMAL、任一非零=ABNORMAL、缺值=UNKNOWN；只有 status=0 才用有效 CAN speed，否則回退有效 GPS。9 不推斷為特定 Bus 組合。新增 `can_status_unknown_flag`。
- 怠速：`idle_minutes` 仍由 `carStatus=idling` 與有效 timestamp interval 算出；Event 2 不是完整 idle duration，且 PTO／任務未知時不能推定怠速浪費。
- 來源事件：Event 6／7／8／11 只作 Supporting Evidence。Event 6 不作 Primary Lever；Event 6／7 不作車況配對或主要 ML 特徵。Event 8 不自行重建。Event 11 不等於 EcoPilot 的負載 >90% 比例。
- Breaking changes：`high_rpm_ratio`→`rpm_above_2500_ratio`、`high_engine_load_ratio`→`engine_load_above_90_ratio`；五個來源事件計數欄加 `_event_count`；`idle_priority_pct`→`idle_context_priority_pct`。刪除 `acceleration_per_100km`、`acceleration_excess_score`、`acceleration_priority_pct` 及其 peer 欄。新 trips schema 99 欄，沒有舊欄重複輸出。
- 三項槓桿：Idle／Stop Context、RPM Pattern、Engine Load Pattern。Owner：怠速交調度並支援駕駛；轉速交駕駛並支援管理者；負載交管理者並支援調度／維修；車況／DTC 交維修；低或不足證據交管理者補證據。`owner_confidence` 是路由證據完整度，非模型機率。
- UI：資料旅程展示四層來源；車隊頁標「觀測怠速」；行程頁分開三槓桿與設定依賴來源事件；案例 B 改「操作型態待核對」；管理頁顯示 Primary Owner／Supporting Roles／Handoff Reason；資料頁提供 Current Data、Event Reference、Production Data Capability、Methodology、Model Validation、Pilot Validation 六個分頁。
- Pilot：`action_outcomes_template.csv` 只有 header；沒有虛構採行或節油成效。

## 全量重建後統計

`./ecopilot build --ml` 完成；保留未變的原始 XLSX 與 raw snapshot，舊 processed 結果先清除再重新產生。

| 指標 | 新結果 |
| --- | ---: |
| 原始列／事件紀錄 | 493,744／111,172 |
| 車輛／行程 | 20／3,541 |
| 比較前合格／有 Benchmark 支持 | 1,401／1,383 |
| L2／L3；MEDIUM／LOW | 1,146／237；1,065／318 |
| 正向 Benchmark Gap | 1,631.785 L；不是節省量 |
| 車況檢查訊號 | 34 趟／7 台車 |
| 行動待辦 | 2,969 筆；FLEET_MANAGER 2,551、DISPATCHER 155、DRIVER 137、MAINTENANCE 126 |
| 觀測 CAN 狀態 | NORMAL 3,479 趟、ABNORMAL 62 趟、UNKNOWN 0 趟 |
| 事件 reference／擴充欄位記錄／能力矩陣 | 20／314／31 |
| 決策資料包／欄位字典 | 3,541／99 欄 |

### 重新執行的 ML 驗證

| 驗證 | RF MAE | R² | Baseline A MAE | Baseline B MAE | RF 對 A／B 的 MAE 變化 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5-fold GroupKFold by vehicle，1,401 趟 | 2.298430 L | 0.834672 | 3.483318 L | 2.345707 L | 34.02%／2.02% |
| 時間 holdout：訓練 1,115、測試 281 | 1.452298 L | 0.825068 | 3.448399 L | 1.790061 L | 57.88%／18.87% |

時間切分排除五趟跨界行程。模型只作回顧 Validation／Scenario Support，不參與核心 KPI 或車況訊號；誤差變化不是節油成效。

## 驗證與限制

`./ecopilot python -m compileall -q src scripts tests pages app.py` 通過；`./ecopilot test -q` **85 passed**；`./ecopilot check` 確認 Python 3.14.3、48 個鎖定套件一致、無依賴破損。六頁真實資料 AppTest 通過，瀏覽器逐頁載入 0 個 Streamlit exception，並保存六張 v3 截圖。直接開啟深層路由時，Streamlit 前端對相對 `_stcore/health` 與 `_stcore/host-config` 發出十個非阻斷 404；六頁內容仍正常顯示。瀏覽器檢查以 127.0.0.1:18502 進行，因 18501 已被其他程序占用。

仍缺正式產品可驗證的 driverUid／tachographDriver、PTO、實際載重、任務、停留用途、路況、天氣、坡度與維修；不能判定可避免怠速、跨車 Event 標準化績效、故障原因或已實現節油。來源 Event 8 與 duration 單位的參考衝突已登錄，歷史各車事件門檻不可追溯。要證明價值需真實資料介接及有對照的 Pilot Closed-loop。

## 交付封裝驗收（2026-10-03）

最終 ZIP 由 `scripts/package_delivery.py` 重新建立於專案上層。封裝含競賽原始 XLSX、HINO competition FAQ、0929 事件／Rawdata 參考 XLSX、來源登錄、重建後 processed 產物、Pilot 空白模板、六張 v3 頁面截圖與本報告。`ZipFile.testzip()` CRC 檢查通過；三份來源檔在 ZIP 內的 SHA-256 均與原檔一致；pipeline summary、model report、source registry 版本均為 `ecopilot_v3`／`competition+faq+event0929_v1`／`0929`。ZIP 排除 `.venv`、`.runtime`、快取、`.playwright-cli` 與 `.env`。實際檔案數與壓縮包 SHA-256 可用封裝後命令再次查核，避免在報告中留下自指的過期雜湊。
