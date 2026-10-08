# 四層資料能力矩陣

A 為此次 Competition Core；B 為已遷移 iTRAQ Rawdata 的參考 schema，正式可用性需核對；C 需企業營運系統；D 為選配外部資料。Mock 是 C／D 的 Prototype placeholder。

| field | display_name | data_layer | competition_available | reference_schema_documented | production_availability | current_prototype_use | future_product_use | limitations | source_file | source_sheet |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| enabledCode | enabledCode | A_COMPETITION_CORE | True | False | AVAILABLE_IN_COMPETITION | RAW / DERIVED | 可比較行程證據 | 本次 extract 實際欄位與單位以競賽活頁簿為準 | output data_Hotai_20260511.xlsx | output / 欄位對照表 |
| journeyCode | journeyCode | A_COMPETITION_CORE | True | False | AVAILABLE_IN_COMPETITION | RAW / DERIVED | 可比較行程證據 | 本次 extract 實際欄位與單位以競賽活頁簿為準 | output data_Hotai_20260511.xlsx | output / 欄位對照表 |
| Type | Type | A_COMPETITION_CORE | True | False | AVAILABLE_IN_COMPETITION | RAW / DERIVED | 可比較行程證據 | 本次 extract 實際欄位與單位以競賽活頁簿為準 | output data_Hotai_20260511.xlsx | output / 欄位對照表 |
| gps.longitude | gps.longitude | A_COMPETITION_CORE | True | False | AVAILABLE_IN_COMPETITION | RAW / DERIVED | 可比較行程證據 | 本次 extract 實際欄位與單位以競賽活頁簿為準 | output data_Hotai_20260511.xlsx | output / 欄位對照表 |
| gps.latitude | gps.latitude | A_COMPETITION_CORE | True | False | AVAILABLE_IN_COMPETITION | RAW / DERIVED | 可比較行程證據 | 本次 extract 實際欄位與單位以競賽活頁簿為準 | output data_Hotai_20260511.xlsx | output / 欄位對照表 |
| can.totalMileage | can.totalMileage | A_COMPETITION_CORE | True | False | AVAILABLE_IN_COMPETITION | RAW / DERIVED | 可比較行程證據 | 本次 extract 實際欄位與單位以競賽活頁簿為準 | output data_Hotai_20260511.xlsx | output / 欄位對照表 |
| can.engine.totalFuelUsed | can.engine.totalFuelUsed | A_COMPETITION_CORE | True | False | AVAILABLE_IN_COMPETITION | RAW / DERIVED | 可比較行程證據 | 本次 extract 實際欄位與單位以競賽活頁簿為準 | output data_Hotai_20260511.xlsx | output / 欄位對照表 |
| can.engine.rpm | can.engine.rpm | A_COMPETITION_CORE | True | False | AVAILABLE_IN_COMPETITION | RAW / DERIVED | 可比較行程證據 | 本次 extract 實際欄位與單位以競賽活頁簿為準 | output data_Hotai_20260511.xlsx | output / 欄位對照表 |
| can.engine.engineLoad | can.engine.engineLoad | A_COMPETITION_CORE | True | False | AVAILABLE_IN_COMPETITION | RAW / DERIVED | 可比較行程證據 | 本次 extract 實際欄位與單位以競賽活頁簿為準 | output data_Hotai_20260511.xlsx | output / 欄位對照表 |
| carStatus | carStatus | A_COMPETITION_CORE | True | False | AVAILABLE_IN_COMPETITION | RAW / DERIVED | 可比較行程證據 | 本次 extract 實際欄位與單位以競賽活頁簿為準 | output data_Hotai_20260511.xlsx | output / 欄位對照表 |
| event[0].type | event[0].type | A_COMPETITION_CORE | True | False | AVAILABLE_IN_COMPETITION | RAW / DERIVED | 可比較行程證據 | 本次 extract 實際欄位與單位以競賽活頁簿為準 | output data_Hotai_20260511.xlsx | output / 欄位對照表 |
| driverUid | 駕駛 ID | B_EXTENDED_ITRAQ | False | True | PRODUCTION_AVAILABILITY_TO_CONFIRM | NONE | 取代 Prototype 模擬駕駛代碼；正式提供情況待確認 | 參考 schema 已遷移；依車型、設備及管線確認。不得視為本次競賽實測資料。 | Event Type_0929補充.xlsx | 14-Rawdata(已遷移) / 14V2-Rawdata(已遷移) / 14V3-Rawdata(已遷移) |
| tachographDriver | 大餅駕駛 ID | B_EXTENDED_ITRAQ | False | True | PRODUCTION_AVAILABILITY_TO_CONFIRM | NONE | 核對駕駛輪替；正式提供情況待確認 | 參考 schema 已遷移；依車型、設備及管線確認。不得視為本次競賽實測資料。 | Event Type_0929補充.xlsx | 14-Rawdata(已遷移) / 14V2-Rawdata(已遷移) / 14V3-Rawdata(已遷移) |
| engineFuelRate | 引擎燃油率 | B_EXTENDED_ITRAQ | False | True | PRODUCTION_AVAILABILITY_TO_CONFIRM | NONE | 更直接估算怠速與區段燃油；單位及可用性待確認 | 參考 schema 已遷移；依車型、設備及管線確認。不得視為本次競賽實測資料。 | Event Type_0929補充.xlsx | 14-Rawdata(已遷移) / 14V2-Rawdata(已遷移) / 14V3-Rawdata(已遷移) |
| instantaneousFuel | 瞬時燃油 | B_EXTENDED_ITRAQ | False | True | PRODUCTION_AVAILABILITY_TO_CONFIRM | NONE | 輔助區段燃油分析；單位及可用性待確認 | 參考 schema 已遷移；依車型、設備及管線確認。不得視為本次競賽實測資料。 | Event Type_0929補充.xlsx | 14-Rawdata(已遷移) / 14V2-Rawdata(已遷移) / 14V3-Rawdata(已遷移) |
| pedalPosition | 油門踏板位置 | B_EXTENDED_ITRAQ | False | True | PRODUCTION_AVAILABILITY_TO_CONFIRM | NONE | 理解操作需求；可用性待確認 | 參考 schema 已遷移；依車型、設備及管線確認。不得視為本次競賽實測資料。 | Event Type_0929補充.xlsx | 14-Rawdata(已遷移) / 14V2-Rawdata(已遷移) / 14V3-Rawdata(已遷移) |
| gearBoxPosition | 變速箱檔位 | B_EXTENDED_ITRAQ | False | True | PRODUCTION_AVAILABILITY_TO_CONFIRM | NONE | 理解轉速與檔位型態；可用性待確認 | 參考 schema 已遷移；依車型、設備及管線確認。不得視為本次競賽實測資料。 | Event Type_0929補充.xlsx | 14-Rawdata(已遷移) / 14V2-Rawdata(已遷移) / 14V3-Rawdata(已遷移) |
| ptoSwitch | PTO 開關 | B_EXTENDED_ITRAQ | False | True | PRODUCTION_AVAILABILITY_TO_CONFIRM | NONE | 判斷停留時是否可能有必要作業；可用性待確認 | 參考 schema 已遷移；依車型、設備及管線確認。不得視為本次競賽實測資料。 | Event Type_0929補充.xlsx | 14-Rawdata(已遷移) / 14V2-Rawdata(已遷移) / 14V3-Rawdata(已遷移) |
| streetName | 道路名稱 | B_EXTENDED_ITRAQ | False | True | PRODUCTION_AVAILABILITY_TO_CONFIRM | NONE | 增加路段情境；可用性待確認 | 參考 schema 已遷移；依車型、設備及管線確認。不得視為本次競賽實測資料。 | Event Type_0929補充.xlsx | 14-Rawdata(已遷移) / 14V2-Rawdata(已遷移) / 14V3-Rawdata(已遷移) |
| streetLevel | 道路層級 | B_EXTENDED_ITRAQ | False | True | PRODUCTION_AVAILABILITY_TO_CONFIRM | NONE | 改善路段分組；可用性待確認 | 參考 schema 已遷移；依車型、設備及管線確認。不得視為本次競賽實測資料。 | Event Type_0929補充.xlsx | 14-Rawdata(已遷移) / 14V2-Rawdata(已遷移) / 14V3-Rawdata(已遷移) |
| brakeSwitch | 煞車開關 | B_EXTENDED_ITRAQ | False | True | PRODUCTION_AVAILABILITY_TO_CONFIRM | NONE | 理解操作情境；可用性待確認 | 參考 schema 已遷移；依車型、設備及管線確認。不得視為本次競賽實測資料。 | Event Type_0929補充.xlsx | 14-Rawdata(已遷移) / 14V2-Rawdata(已遷移) / 14V3-Rawdata(已遷移) |
| clutchSwitch | 離合器開關 | B_EXTENDED_ITRAQ | False | True | PRODUCTION_AVAILABILITY_TO_CONFIRM | NONE | 理解操作情境；可用性待確認 | 參考 schema 已遷移；依車型、設備及管線確認。不得視為本次競賽實測資料。 | Event Type_0929補充.xlsx | 14-Rawdata(已遷移) / 14V2-Rawdata(已遷移) / 14V3-Rawdata(已遷移) |
| task_id | task_id | C_ENTERPRISE_CONTEXT | False | False | ENTERPRISE_INTEGRATION_REQUIRED | NONE | 確認任務 | 需企業營運系統串接 |  |  |
| actual_payload | actual_payload | C_ENTERPRISE_CONTEXT | False | False | ENTERPRISE_INTEGRATION_REQUIRED | NONE | 控制實際載重 | 需企業營運系統串接 |  |  |
| delivery_window | delivery_window | C_ENTERPRISE_CONTEXT | False | False | ENTERPRISE_INTEGRATION_REQUIRED | MOCK placeholder | 核對到站窗口 | 需企業營運系統串接 |  |  |
| stop_purpose | stop_purpose | C_ENTERPRISE_CONTEXT | False | False | ENTERPRISE_INTEGRATION_REQUIRED | MOCK placeholder | 區分停留用途 | 需企業營運系統串接 |  |  |
| loading_status | loading_status | C_ENTERPRISE_CONTEXT | False | False | ENTERPRISE_INTEGRATION_REQUIRED | NONE | 核對裝卸作業 | 需企業營運系統串接 |  |  |
| maintenance_history | maintenance_history | C_ENTERPRISE_CONTEXT | False | False | ENTERPRISE_INTEGRATION_REQUIRED | NONE | 核對保養 | 需企業營運系統串接 |  |  |
| traffic | traffic | D_EXTERNAL_CONTEXT | False | False | EXTERNAL_OPTIONAL | MOCK placeholder | 擴充環境比較條件 | 須取得外部可靠來源 |  |  |
| weather | weather | D_EXTERNAL_CONTEXT | False | False | EXTERNAL_OPTIONAL | NONE | 擴充環境比較條件 | 須取得外部可靠來源 |  |  |
| road_gradient | road_gradient | D_EXTERNAL_CONTEXT | False | False | EXTERNAL_OPTIONAL | NONE | 擴充環境比較條件 | 須取得外部可靠來源 |  |  |

B 層不代表競賽 extract 已觀測到這些值，也不代表所有車型或設備都提供；欄位不進入 telemetry 或主要模型。已作廢胎壓表僅作 deprecated reference。
