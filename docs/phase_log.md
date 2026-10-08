# HINO EcoPilot｜執行與驗證紀錄

2026-10-02 第二輪資料定義校正。來源：Competition XLSX、HINO competition FAQ PDF、`Event Type_0929補充.xlsx`；來源 SHA-256 與衝突見 [來源契約](source_contract.md) 和 `data/reference/source_registry.json`。

| 資料階段 | 全量重建結果 |
| --- | --- |
| 1 Inspect | Competition XLSX SHA-256 未變，重用唯讀 raw snapshot；0929 與 FAQ 保存於 reference，未合併成 telemetry |
| 2 Clean + Trip | 493,744 原始列、111,172 事件紀錄、3,541 行程、20 車；1,401 合格行程；CAN status 三態與 GPS fallback |
| 3 Mock Context | 每趟 8 個 MOCK 欄位，固定種子 42；只作正式營運情境 placeholder |
| 4 Benchmark + Opportunity + Health | 1,383 趟支持行程；L2 1,146／L3 237；MEDIUM 1,065／LOW 318；三項槓桿；34 趟歷史車況訊號、7 車 |
| 5 Decision Outputs | 3,541 決策資料包、四角色建議、2,969 筆行動待辦；99 個行程欄位字典 |

正向比較差距 1,631.785106740589 L，不是可實現節省量。選配 ML 重新訓練與驗證：5-fold GroupKFold MAE 2.298430 L、R² 0.834672；Baseline A 3.483318 L、B 2.345707 L。時間留出訓練 1,115／測試 281，排除 5 趟跨界行程；模型 MAE 1.452298 L、R² 0.825068。

UI 與測試獨立於五個資料 phase。最終 `compileall` 通過、`./ecopilot test -q` 85 passed、環境檢查通過。六頁實際瀏覽器載入 0 個 Streamlit exception，Event Reference、Production Data Capability、Pilot Validation 分頁內容已核對；新版截圖保存在本機 `docs/screenshots/`，不納入 Git。完整限制與交付檢查見 [第二輪一致化報告](final_alignment_report.md)。
