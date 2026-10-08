# iTRAQ 事件參考

來源：`Event Type_0929補充.xlsx` 的 `event代碼` sheet；僅為 reference metadata，不是新增 telemetry。

| event_type | event_name_zh | trigger_definition | parameter_configurable | comparison_role | source_conflict_flag | source_note |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 怠速開始 | 引擎轉速不為「0」、時速為 「0」，持續「5」分鐘(未觸發怠速前，速度超過10km/h counter歸零)；怠速解除：車速「10」以上持續「30」秒 | True | SUPPORTING_ONLY |  | Event Type_0929補充.xlsx / event代碼；原表開關=ON/OFF |
| 6 | 急加速 | 當每秒速度差變化量大於「10」km/h，同時有連續2筆資料(V4-V2>5, V3-V1>5)成立 | True | SUPPORTING_ONLY |  | Event Type_0929補充.xlsx / event代碼；原表開關=ON/OFF |
| 7 | 急減速 | 每隔秒速度變化小於「-15」km/h，且有連續2筆資料(V4-V2<=-15, V3-V1<=-15)，即為急減速行為 | True | SUPPORTING_ONLY |  | Event Type_0929補充.xlsx / event代碼；原表開關=ON/OFF |
| 8 | 超速 | 1. 車速>=路段限速+10 KM/H並持續 5 秒後觸發。 / 2. 車速>=「107」 KM/H並持續 「5」 秒後觸發。；超速解除：1. 車速<=路段限速km/H以下，持續 5 秒 / 2. 車速「95」km/H以下，持續「5」秒 | True | SUPPORTING_ONLY | SOURCE_CONFLICT | Event Type_0929補充.xlsx / event代碼；原表開關=ON/OFF |
| 11 | 引擎過載 | 引擎負載大於 「83」%且持續「5」秒；引擎過載解除：引擎負載小於 「83」%且持續「5」秒 | True | SUPPORTING_ONLY |  | Event Type_0929補充.xlsx / event代碼；原表開關=ON/OFF |

Event 2 的觸發／解除門檻不等於完整怠速時長。`idle_minutes` 只依 `carStatus=idling` 與有效 timestamp interval 計算。

Event 6／7／8／11 為設定依賴的來源事件，僅作支持證據；事件計數不是跨車標準化績效。Event 8 競賽 FAQ 第 2–3 頁與 0929 的預設門檻不同，標記 `SOURCE_CONFLICT`；保留來源系統通報，不自行重建。`engine_load_above_90_ratio` 是 EcoPilot 原型特徵，不等於來源 Event 11（參考描述 >83% 持續 5 秒，參數可調）。
