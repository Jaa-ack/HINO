# HINO EcoPilot Source Contract v3

此契約將「此次競賽實際觀測」與「正式產品參考能力」分開。來源登錄與 SHA-256 見 `data/reference/source_registry.json`。

| 優先級 | 來源 | 用途與界線 |
| --- | --- | --- |
| A | `output data_Hotai_20260511.xlsx` 的 `output`、`欄位對照表` | 決定此次 extract 實際欄位、格式與單位；RAW 保持唯讀。 |
| B | `HINO competition FAQ.pdf` | 解讀競賽資料、事件設定與限制。 |
| C | `Event Type_0929補充.xlsx` 的 `event代碼` | 事件觸發與可調參數的 reference metadata；不新增 telemetry rows。 |
| D | 同檔 `14-Rawdata(已遷移)`、`14V2-Rawdata(已遷移)`、`14V3-Rawdata(已遷移)` | Extended iTRAQ Production Schema Reference；不代表此次 extract 有欄位，也不保證正式介接可提供。 |
| E | 同檔 `14.1-胎壓資料格式(已作廢)` | Deprecated reference，不納入分析。 |

此次 extract 的 `event[n].info.duration` 欄位對照單位為**秒**。已遷移 `14V3-Rawdata` 的多個 `duration` 列卻標為**分鐘**，因此登錄 `REFERENCE_CONFLICT`；A 優先於 D，不覆寫競賽單位。`idle_minutes` 只用 `carStatus=idling` 與有效 timestamp interval；不依 Event 2 次數或 duration。`can.canStatus` 在 extract 觀測到 0、9；0 為 NORMAL，任何非零為來源回報 ABNORMAL，缺值為 UNKNOWN。9 不推定為特定 CAN Bus 組合。只有 0 時 CAN speed 才視為狀態已確認正常；其餘可回退有效 GPS speed。

## SOURCE_CONFLICT：Event 8

FAQ 第 2–3 頁描述圖資路段限速加可調容許值，預設 0 km/h、持續 5 秒；0929 `event代碼` 描述路段限速 +10 km/h 持續 5 秒或 107 km/h 持續 5 秒。兩份來源不一致，且 FAQ 明言無法追溯每台車各時期設定。EcoPilot 不選定其中一條重建公式；`speeding_event_count` 僅計數 iTRAQ 已通報的 Event 8，作支持證據。

FAQ 第 4–6 頁也說 Event 7 門檻可由客戶調整，不能由事件次數直接比較不同車的操作績效。0929 的 Event 6、7、11 含可調門檻；Event 11 的 >83% 持續 5 秒描述，不等於 EcoPilot 的 `engine_load_above_90_ratio`。Event count 均為來源事件的去重通報數，DTC 事件數不是故障碼數或確診數。

`rpm_above_2500_ratio`、`engine_load_above_90_ratio` 是 EcoPilot Prototype 觀測衍生特徵，不是 HINO 官方事件門檻。三項 Primary Improvement Levers 是怠速／停留情境、轉速型態與引擎負載型態；排序是核對優先度，並非因果、節油比例或可省公升。缺少 PTO、真實任務與停留用途時，怠速不能判為可避免浪費。
