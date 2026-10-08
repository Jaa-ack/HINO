# 專案環境管理

HINO EcoPilot 的套件、執行入口與暫存設定均由專案管理。使用 `./ecopilot` 即可操作，不必 `source .venv/bin/activate`，也不會改寫 `.zshrc`、全域 pip 設定、其他專案套件或系統服務。

## 包裝內容與支援範圍

| 檔案 | 用途 |
| --- | --- |
| `ecopilot` | macOS／Linux 的命令入口；固定使用專案 Python，找不到環境便停止。 |
| `scripts/environment.py` | 建立、檢查、啟動及維護環境；僅使用 Python 標準函式庫。 |
| `.python-version` | 記錄已驗證的 Python 3.14.3；入口接受 Python 3.14 系列。 |
| `requirements-lock.txt` | 實際執行環境的完整套件版本；安裝以此檔為準。 |
| `requirements.txt` | 直接相依套件的相容版本範圍，供開發維護參考。 |
| `.streamlit/config.toml` | 本機位址、18501 埠、主題、停用檔案監看與統計傳送。 |
| `.env.example` | 選配 AI 的環境設定範本；核心功能不需要金鑰。 |

目前已驗證 macOS ARM64、Python 3.14.3。Linux 有相容命令入口，但尚未完成實機驗證；Windows 未提供原生命令入口。套件鎖定檔不包含 Python 執行檔或套件下載檔，首次安裝需有 Python 3.14 及套件來源的網路連線。安裝只接受預先編譯套件，不會自動安裝系統編譯工具。

## 啟動與停止

```bash
cd hino-ecopilot
./ecopilot check
./ecopilot start
```

在瀏覽器開啟 <http://127.0.0.1:18501>。服務只綁定本機回送位址；同網段其他電腦無法直接連入。

在**啟動服務的終端機按 `Ctrl+C`**停止。入口會由 Streamlit 程序取代，不會額外留下啟動器或常駐管理程序。關閉網頁分頁並不等於停止服務。沒有安裝登入時自動啟動項目。

可用以下唯讀命令確認指定埠是否仍有程序監聽；沒有輸出表示該埠沒有監聽者：

```bash
lsof -nP -iTCP:18501 -sTCP:LISTEN
```

若終端機已遺失，先透過 `lsof` 找到程序，再以 `lsof -a -p <PID> -d cwd` 確認其工作目錄確實是本專案，確認後才執行 `kill -TERM <PID>`。不要以 `killall Python`、`pkill streamlit` 等廣泛指令停止服務，避免影響其他程式。

連接埠衝突時可選另一埠：

```bash
./ecopilot start --port 18502
```

指令只檢查能否使用指定連接埠，不會終止原先占用該埠的程式。更換埠後，瀏覽器網址及 `lsof` 指令也要使用相同數字。修改程式碼或設定後需按 `Ctrl+C` 再啟動，因為預設已停用檔案監看與自動重新執行。

## 隔離範圍

- **套件：**固定使用 `.venv/bin/python`，以 Python 隔離模式忽略外部 `PYTHONPATH`、`PYTHONHOME` 與使用者套件。不接受共用系統套件的虛擬環境，也拒絕將整個 `.venv` 連結至其他環境。
- **安裝：**只透過虛擬環境內的 pip 安裝鎖定版本；清除繼承的 pip 選項並略過 pip 設定檔，避免 `--user` 或外部安裝目錄污染環境。一般啟動不會安裝套件。
- **設定：**入口僅調整當次程序的環境變數；不改變呼叫端終端機。保留專案 `.env` 與選配 AI 的設定，不會在檢查時列印金鑰。
- **暫存：**指令使用 `.runtime/tmp/`，遵循 XDG 的快取使用 `.runtime/cache/`；pip 安裝停用快取。Python 編譯快取與 pytest 快取仍可能存放於專案內。
- **運算：**限制常見數值函式庫的原生執行緒為 1，停用檔案監看以降低閒置負擔。選配模型本身仍可能使用多個工作執行緒。

這些設定隔離 Python 相依與執行設定，**不是容器或作業系統沙箱**。主機的 CPU、記憶體、磁碟與基礎 Python 仍共用；完整 Excel 建置或模型訓練會使用運算資源，沒有硬性資源配額。使用者自行透過 `python` 指令執行的程式也保有原本的檔案權限。若其他本機工作對效能敏感，可先停下網頁服務，待適當時段再執行完整建置。

## 搬移與重建

搬移時保留程式、`ecopilot`、`scripts/`、`pages/`、`src/`、`tests/`、`assets/`、`docs/`、`.streamlit/`、依賴清單、`pytest.ini` 與 `.env.example`。不要直接複製 `.venv/`，因為它含有原電腦的絕對路徑；`.runtime/`、測試快取與瀏覽器暫存也不必搬移。

若需要立即展示相同資料，可另行複製完整 `data/`；若要重新建置，則另行提供原始 Excel。`.env` 中的個人金鑰應在新電腦自行設定。程式環境與分析資料是分開管理的，`setup` 不會重建或刪除既有分析結果。

在新電腦進入專案目錄後：

```bash
./ecopilot setup
./ecopilot check
# 已有完整 data/ 與 docs/ 產物時可略過下一行
./ecopilot build --input '/原始資料路徑/output data_Hotai_20260511.xlsx'
./ecopilot test -q
./ecopilot start
```

若要重建損壞的環境，先停止服務，將 `.venv` **移到備份位置**，再執行 `./ecopilot setup`；檢查與測試通過後才自行刪除備份。原始資料及分析產物不在 `.venv` 裡，不需刪除。Homebrew 升級或移除基礎 Python 導致舊環境失效時，也用同樣方式重建。

## 常見問題

| 訊息或情況 | 處理方式 |
| --- | --- |
| 尚未建立專案虛擬環境 | 準備 Python 3.14 後執行 `./ecopilot setup`。 |
| 套件與鎖定檔不一致 | 執行 `./ecopilot setup`，再 `./ecopilot check`；不要使用系統 pip 修復。 |
| `.venv` 不完整或未隔離系統套件 | 停止服務、備份 `.venv`，再重新 setup；入口不會自動刪除環境。 |
| 安裝找不到相容套件 | 檢查 Python 3.14、CPU 架構及網路；不要用管理員權限安裝來繞過錯誤。 |
| 無法使用連接埠 | 使用 `--port` 換埠；現有程式會繼續運行。 |
| 已開網頁但沒有資料 | 執行 `./ecopilot build`；setup 只處理套件。 |
| 需要回收暫存空間 | 停止服務及所有建置／測試指令後，可刪除 `.runtime/`，下次操作會重建。 |

`./ecopilot check` 只檢查 Python 與套件，不代表資料完整或網頁服務已啟動；資料與六頁互動由 `./ecopilot test -q` 驗證。完整頁面測試需要既有分析產物，缺少時會顯示跳過，因此新環境需先建置資料。

## 最終交付 ZIP

`./ecopilot python scripts/package_delivery.py --output ../.local-only/deliveries/hino-ecopilot-delivery.zip` 將交付 ZIP 存入本機保留區。未指定 `--output` 時，工具仍預設輸出到專案上層；`.gitignore` 排除 ZIP。封裝程式排除 `.venv/`、`.runtime/`、`__pycache__/`、`.pytest_cache/`、`.playwright-cli/`、`.git/`、`.env`、舊 output 與符號連結；保留 `docs/screenshots/` 的截圖。原始 XLSX 以原位元組封裝進 `data/raw/`，來源 manifest 在 ZIP 內使用相對路徑。ZIP 包含實際資料與本機紀錄，須以授權交付方式另行提供，不納入 Git。Git 版本的範圍與重建方式見 [Git 與本機檔案管理](repository.md)。

開發目錄保留本機環境以執行服務與測試；該環境不是交付內容。接收端先安裝 Python 3.14，再執行 `./ecopilot setup`。本次沒有在另一台電腦重新下載所有套件，跨平台安裝仍需接收端驗證。
