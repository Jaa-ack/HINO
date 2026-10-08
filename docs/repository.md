# Git 與本機檔案管理

Git repository 根目錄為 `hino-ecopilot/`。上傳內容包含程式、測試、依賴版本、公開文件、Logo、Streamlit 主題設定、空白 `.env.example` 與 Pilot outcome 模板。

## 本機保留位置

| 路徑（相對於 repository） | 內容 | Git |
| --- | --- | --- |
| `../.local-only/video/project-output/` | 原專案 `output/`：影片成品、錄製腳本、素材、旁白、字幕、QA | repository 外；工作區忽略 |
| `../.local-only/video/workspace-output/` | 原工作區 `output/`，保留另一組製作檔以免覆蓋 | repository 外；工作區忽略 |
| `../.local-only/deliveries/` | 原有交付 ZIP，內含競賽資料 | repository 外；工作區忽略 |
| `../.local-only/reports/` | 含實際車輛、行程與位置的檢查報告 | repository 外；工作區忽略 |
| `data/raw/` | 競賽原始 XLSX | 僅追蹤 `.gitkeep` |
| `data/reference/` | FAQ PDF、0929 補充 XLSX、來源登錄與參考產物 | 僅追蹤 `.gitkeep` |
| `data/interim/`、`data/processed/`、`data/mock/` | 原始快取、衍生分析與帶有行程鍵的 Mock | 僅追蹤 `.gitkeep` |
| `data/pilot/` | 本機追蹤資料庫 | 僅追蹤空白 CSV 模板 |
| `docs/data_profile.*`、`docs/workbook_field_mapping.json` | 含來源欄位範例的自動產物 | 忽略 |
| `docs/screenshots/` | 顯示真實資料的介面截圖 | 忽略 |
| `.env`、`.streamlit/secrets.toml` | 個人金鑰與私密設定 | 忽略 |
| `.venv/`、`.runtime/`、瀏覽器及 Python 快取 | 本機環境與暫存 | 忽略 |

整理保留既有資料與製作檔；分析資料留在程式原本使用的路徑。原始 XLSX 從工作區上層移入 `data/raw/`，本機 source manifest 改用相對路徑，SHA-256 維持不變。影片腳本中的舊路徑可能需依新位置調整，重製影片時請先核對。

## Clone 後執行

Git 不包含競賽原始資料或既有分析結果。取得授權資料後，放置：

- `data/raw/output data_Hotai_20260511.xlsx`
- `data/reference/HINO competition FAQ.pdf`
- `data/reference/Event Type_0929補充.xlsx`

```bash
./ecopilot setup
./ecopilot check
./ecopilot build --ml
./ecopilot test -q
./ecopilot start
```

完整測試包含實際資料與介面整合檢查，需先建置以上本機資料。選配 AI 可複製 `.env.example` 成 `.env` 後填入個人設定。

## 檢查上傳清單

```bash
git status --short
git ls-files
git status --short --ignored
```

`.gitignore` 保護一般 `git add`，不保護 `git add -f` 或已追蹤的檔案。加入新資料檔或設定前請核對清單；私密資料不使用強制加入。

`scripts/package_delivery.py` 是完整資料交付工具，會封裝原始資料、分析結果及截圖；ZIP 與 Git 上傳清單分開管理。需要建立交付檔時，指定本機保留區：

```bash
./ecopilot python scripts/package_delivery.py --output ../.local-only/deliveries/hino-ecopilot-delivery.zip
```
