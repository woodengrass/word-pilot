# Word Pilot｜V1 開發主計畫

版本：1.0  
日期：2026-10-04

本文件是 V1 的主索引。完整規格拆在 `docs/`，機器可讀契約在 `contracts/`，OpenCode + OMO 的執行規則在 `agent/`。

## 產品目標

Word Pilot 是一個 iPhone-first、離線優先的英文詞彙學習 App，主要面向台灣高中生與大學前非母語學習者。

使用者只需要：

- 查詢或輸入想學的英文單字／片語。
- 明確按下加入。
- 設定每天可投入的時間。
- 視需要設定考試日期，以及該考試是否需要英文書寫。

系統自己決定：

- 今天學哪些新內容。
- 哪些舊內容該複習。
- 該用哪一種題型。
- 哪些義項與搭配優先。
- 考前時間不足時應該先保留哪些核心內容。
- 何時需要額外診斷或加強。
- 使用者目前的學習負荷是否合理。

不使用 Anki 式 Again / Hard / Good / Easy，也不要求使用者自行判斷熟悉度。

## V1 范圍

- Swift + SwiftUI。
- 本地資料庫優先考慮 SQLite（GRDB 為優先候選），實作時驗證後鎖定。
- 核心完全離線。
- 約 10k–12k 個高品質英文 headword，外加獨立片語集合。
- 繁中解釋、多詞性、多義項、例句、搭配／用法、詞形與發音資訊。
- 單字與片語分開建模，但都可以加入考試、長期複習。
- 支援單字搜尋、一鍵加入與逐行批次貼上。
- 未收錄內容不可加入；提供明確 Cambridge Dictionary 外連。
- V1 不做 OCR、照片解析、runtime LLM、帳號、同步、Android、訂閱。核心學習不依賴伺服器；beta／後續可有獨立的 opt-in 隱私聚合研究服務，但不接收 user-level 學習資料。

完整產品規則見 `docs/01-product.md`。

## 技術方向

架構只規定要達成的性質，具體 module、package、schema 由實作時決定並記錄理由：

- 學習排程、評分與 planner 可以脫離 UI 測試與重現；時間、日曆與亂數由外部注入。
- 詞庫內容與使用者學習資料的生命週期分開：詞庫升版不重置學習紀錄，備份不需複製整個詞庫。是否用兩個 SQLite 檔由實作評估。
- word / phrase / sense / learning target 有自有的穩定 ID。
- 原始作答事件是長期 source of truth；mastery、forecast 與 cost profile 是可重新計算的衍生狀態。

`contracts/content.sql`、`contracts/user.sql` 是一種可行資料表示的參考草稿，不是必須遵守的 schema。

完整說明見 `docs/02-architecture-data.md`。

## 學習模型

核心原則：

1. 短教學。
2. 間隔後無提示作答。
3. 立即提供正確回饋。
4. 換不同語境與搭配再次驗證。
5. 跨日延遲檢查。

主要題型：

- 英文語境 → 意義。
- 中文／概念 → 英文辨認。
- context cloze。
- collocation / phrase slot。
- 多義辨識。
- 短文小題組。
- 少量短輸入。
- Writing 需求時才增加 exact spelling / production。

MemoryUnit 以 `target × response_mode` 分開保存，避免「選擇題會了」直接等同於「能拼寫與產出」。

FSRS-6 只負責記憶狀態與複習時間。V1 客觀映射：

- 有效、無提示、首次作答正確 → Good。
- 有效、無提示、首次作答錯誤 → Again。
- 提示後答對、看過答案、退出、技術故障 → 不作為 Good。
- lookup 不直接改 FSRS。

詳見 `docs/03-learning-engine.md` 與 `contracts/policy-v1.json`。

## 時間與考試規劃

使用者不設定每日新字數，只設定每日可用時間。

Planner 會：

- 優先處理到期與高風險內容。
- 控制新內容產生的後續複習債務。
- 多場考試共用同一份每日時間。
- 同一項目出現在多場考試只保留一份 mastery。
- 考前時間不足時先暫緩 Extended，再縮 Standard；Foundation 的評分標準不降低。
- 考後只移除 deadline urgency，保留長期複習。

個人化先做實際耗時、錯誤補救成本、delayed performance 與 workload；疲勞／邊際效益模型等有真實延遲資料後再啟用。

詳見 `docs/04-planner-personalization.md`。

## 隱私與跨使用者演算法改進

個人化學習資料與個人記憶模型預設只存在裝置上。跨使用者改善演算法時採用 privacy-preserving aggregate research：

- 使用者明確 opt-in；拒絕不影響任何核心功能。
- raw events、個人詞彙歷史與 individual memory parameters 不上傳。
- 裝置只產生預先定義的有限統計／模型 contribution。
- 收集鏈路要分離來源身分與 contribution，並使用安全聚合，使研究端只得到達最低群體門檻的 aggregate。
- 不建立 user-level telemetry / research profile。
- 這套研究資料管線與未來 CloudKit／其他同步完全分離。

完整 privacy target、threat model 與驗收見 `docs/privacy-data-collection.md`。

## 詞庫與 AI pipeline

內容不是 runtime 生成，而是開發階段建立、審查、版本化後打包進 App。

參考流程（具體階段與格式由 content tooling 依實際規模設計）：

```
來源與授權 gate
→ headword / phrase 清單
→ 自有穩定 ID
→ 義項與用法整理
→ LLM 生成候選
→ LLM 全量審查
→ 題目盲解與歧義審查
→ 程式驗證
→ 人工高風險抽查
→ 版本化內容包 + provenance
```

每個欄位保留 provenance，包括來源、版本、授權、生成模型、prompt 版本、審查結果與修改歷史。

完整規則見 `docs/05-content-pipeline.md`。

## 測試原則

分開驗證：

- 軟體是否正確。
- 內容是否正確。
- 學習效果是否真的改善 delayed transfer。

QA 覆蓋資料遺失、重複提交、跨日、詞庫升版、考試不足、查字訊號、大小寫、拼字容錯、片語、備份還原、無障礙與實機性能。

詳見 `docs/06-validation-release.md`。

## 實作里程碑

- M0：可靠的開發基礎（build、測試、本地持久化、可重現依賴）。
- M1：200 詞 + 30 片語 content pilot。
- M2：離線字典、本機 persistence、備份。
- M3：客觀評分、FSRS、學習循環、續接。
- M4：時間預算、考試、forecast、個人化成本。
- M5：完整內容、內容升版與可靠性。
- M6：同學 beta 與算法校正。

第一輪只做 M0（`agent/START-M0.md` 的完成條件），完成後停止。

完整任務 DAG 見 `docs/07-roadmap-tasks.md` 與 `contracts/tasks.json`。

## 研究邊界

已有研究支持 retrieval practice、spacing、搭配詞與多義詞分開處理等方向；但沒有研究直接證明本產品所有工程常數為最佳值。

FSRS 的客觀題型映射、考前 coverage/depth 取捨、查字曝光、個人疲勞與手機零碎使用都保留為需 beta 驗證的問題。

來源與限制見 `docs/08-research-decisions.md`。

## 第一個執行入口

OpenCode + OMO：

1. 讀 `planning/v1/README.md`。
2. 讀 `planning/v1/agent/AGENTS.md`。
3. 使用 `planning/v1/agent/START-M0.md`。
4. 只做 M0；細節與技術選擇依 START-M0 自行決定並記錄。
5. 完成後提供 build/test/限制報告，再決定是否進 M1。
