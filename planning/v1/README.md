# 離線英文詞彙學習 App｜開發計畫 v1

版本：1.0  
整理與研究查核：2026-10-04  
狀態：可開始 M0；這是規格、資料契約與任務包，不是已完成的 App 或完整詞庫。

## 先看這裡

給人閱讀：`PLAN.md` 是完整合併版。  
給 OpenCode / OMO：分段讀 `docs/`，依 `contracts/tasks.json` 執行。  
第一次派工：`agent/START-M0.md`。  
專案規則：將 `agent/AGENTS.md` 合併進既有規則，不直接覆蓋。

建議把本資料夾放到 repo 的 `planning/v1/`。App 暫用中性的 `VocabApp` 作工程名稱，產品品牌不阻擋開發。

## 已定的產品邊界

iPhone-first、SwiftUI、SQLite + GRDB、離線詞庫與客觀作答。
只輸入英文，單字與片語分開管理；查詢不等於加入。
使用者提供每日可用時間與可選的考試日期，不管理新字數、複習間隔或熟悉度。
大部分使用點擊題，重視語境、搭配、多義；少量短輸入，寫作目標才嚴格拼字，大小寫永不扣。
原始學習事件與內容來源可追溯；不做 runtime AI、照片辨識、帳號或 V1 同步。
未收錄字可自行點開 Cambridge 查詢，不能加入；這是離線核心之外的明確外連。
完整內容目標約 10k–12k 個 headword + 初始常用片語，先用 200 詞 + 30 片語跑通小型完整流程。

## 文件

| 文件 | 用途 |
|---|---|
| docs/01-product.md | 產品規則、流程、邊界與可驗收需求 |
| docs/02-architecture-data.md | 技術棧、資料模型、事件、備份、未來同步 |
| docs/03-learning-engine.md | 初次學習、客觀評分、FSRS 接法、掌握證據 |
| docs/04-planner-personalization.md | 時間預算、期限、負荷估計、下一題 |
| docs/05-content-pipeline.md | 來源授權、AI 全量審查、provenance、內容建置 |
| docs/06-validation-release.md | 28 個重要情境、性能、學習評估、beta |
| docs/07-roadmap-tasks.md | M0–M6、31 個有依賴與驗收的任務 |
| docs/08-research-decisions.md | 文獻決策、工程假設、26 個來源索引 |
| docs/09-review-load-simulation.md | 複習負荷模擬：每字 unit 數 × 每日時間能撐多少字 |

## 可用的起始契約

`contracts/content.sql`、`contracts/user.sql`：可以在 SQLite 執行的起始 schema；落成 App 時要轉成受版本管理的 migration。
`contracts/policy-v1.json`：集中管理未經產品實驗校準的工程初值。
`contracts/content-entry.schema.json`、`contracts/review-event.schema.json`：可攜格式與事件規則。
`contracts/tasks.json`：任務 DAG。
`contracts/sources.json`：研究、官方文件與授權來源。
`contracts/opencode-xcode.fragment.json`：Xcode MCP 設定片段，僅合併 xcode 欄位，保留現有 OMO。
`tools/simulate_review_load.py`：複習負荷模擬，結果與假設見 docs/09。

`examples/` 是格式與行為示例。它們不是全量詞庫，也未經正式雙語內容審訂，不可直接當成已通過品質 gate 的正式內容。

## 執行規格檢查

在本資料夾內：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-plan.txt
python3 tools/validate_plan.py --output validation-report.json
```

會檢查 JSON schema/示例、SQL/外鍵/FTS、原子回滾與重複作答保護、政策不變條件、任務依賴及引用 ID。
這不會建置 Swift、不驗證 FSRS 的實際數值、不測 iPhone；這些是 M0/M3/實機階段的驗收。
已提供一次實際執行的 `validation-report.json`，重跑後可替換。

## 一開始的實作順序

M0 工具鏈與資料契約 -> M1 小型內容 -> M2 字典與保存 -> M3 學習循環 ->
M4 時間與考試 -> M5 全量內容與可靠性 -> M6 同學 beta。

不要先把全量內容生成完，也不要先接 CloudKit。
第一次交給 OMO 的範圍是 T001–T004；開起來、測得動、資料格式一致後再往下。

## 未決但不阻擋 M0 的事情

CEEC 或其他受條件限制資料的發布許可尚需按實際用途確認；不得把「免費測試」當作通用豁免。
正式上架/外部 TestFlight 的 Apple 帳號、合約與費用在發佈階段由持有人處理。
高階疲勞、邊際效率與個人 FSRS 擬合需要真實延遲資料；本計畫已給可測基線，不假裝這些已獲證明。
