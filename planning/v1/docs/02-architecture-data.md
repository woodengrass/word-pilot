# 02｜技術架構、資料模型與資料安全

## 1. 技術決策

| 範圍 | 決策 |
|---|---|
| App | Swift 6 語言模式、SwiftUI、Swift Concurrency；最低 iOS 17（產品選擇）。 |
| 資料庫 | SQLite + GRDB。content.sqlite 唯讀；user.sqlite 可寫。 |
| 依賴管理 | Swift Package Manager；提交 Package.resolved；不用 latest 浮動依賴。 |
| 記憶模型 | FSRS-6，先評估/驗證 swift-fsrs，經自有 adapter 隔離。 |
| 測試 | Swift Testing 測純邏輯與資料層；XCTest/XCUIAutomation 測 iOS UI 與中斷。 |
| 內容工具 | Python 3.12+、標準 sqlite3、JSON Schema；可用 uv 管理依賴。LLM 供應商呼叫只在開發工具。 |
| 音訊 | AVSpeechSynthesizer + 本機可用英語 voice；音標與多音詞資料来自內容包。 |
| 開發環境 | OpenCode + OMO 操作 repo；Xcode MCP 負責平台建置/測試；SourceKit-LSP 輔助語義導航。 |
| V1 不加入 | 後端、帳號、CloudKit entitlement、支付 SDK、ORM 雙軌、Rust/KMP 共用核心。 |

GRDB 的 migration、觀察與併發功能適合這裡。[S11] 本次查到的參考版本為 7.11.1；M0 在使用者 Mac 上驗證並固定實際依賴。FSRS 的 Swift README 同時提到 v5/v6，必須明確選擇 21 參數的 v6 路徑並做跨實作測試，不能以預設值猜版本。[S09][S10]

不要為了接 agent 升到 beta Xcode。使用能在使用者 Mac 上執行、並滿足所用 API 的正式工具鏈，將 Xcode、Swift、SDK、最低 iOS、套件 revision 記入 toolchain-lock.md。

## 2. 模組边界

起始只有一個本地 Swift package 和 App target；不要一開始拆十幾個 package。

```
App/
  Features/Study/
  Features/Dictionary/
  Features/Plans/
  Features/Settings/
  Platform/Speech/
  Platform/Backup/
  Platform/Widgets/
Packages/StudyCore/
  Domain/
  Learning/
  Planning/
  Persistence/
  Content/
  Tests/
tools/content/
tools/evaluation/
docs/
contracts/
fixtures/
```

邏輯依賴方向：
SwiftUI → Application services → Learning/Planning 純函式 → Domain。
GRDB 位於持久層邊界，不進演算法值型別。演算法不得 import SwiftUI、CloudKit、UIKit，也不得在內部直接呼叫 Date.now 或全域亂數。

提供 Clock、CalendarPolicy、RandomSource 或值參數；同樣輸入、內容/策略版本與 seed 必須得到同樣輸出。這是未來 Android 移植與事件重放的契約。

不要把學習演算法寫入 View，也不需要為每個查詢建立 Repository/UseCase/Factory 多層類別。先有明確函式和少量可測試服務，再按真實需要拆分。

## 3. 內容模型

### Entry

一個可搜尋、可加入的主項目，有穩定的 content ID：
- kind：word 或 phrase。
- lemma：展示主形式，例如 intelligence 或 take advantage of。
- normalized_key：查詢用；不是語義身份。
- 多詞性放在 Sense；同一 headword 可呈現多詞性。
- Word 與 Phrase 可共用查詢介面，但 UI、目標種類與學習統計分開。

ID 由本專案分配並維護，不用來源詞典的義項排序、文字 hash 或「第 2 義」當永久 ID。來源 ID 放映射表。更換供應商不等於重置使用者。

### Sense

包含詞性、繁中解釋、必要英文釋義、語域/限制、重要度層級及歸屬 Entry。義項切法面向學生，不照抄 WordNet 全部細分。不要把完全同義的中文說法誤拆成三個要背的義項。

importance_tier：
- core：該詞核心、常見且適用目標族群的意思。
- important：常見第二義/第三義或有可驗證考試相關度的意思。
- extended：較少用但在產品範圍内。
重要度標記是編輯判斷；只有确实統計過資料才能標「考題頻率」。

### UsagePattern / Example / PhraseDetail

UsagePattern 儲存搭配、句型、片語可變槽位與限制；Example 指向實際呈現的 Sense/UsagePattern。
PhraseDetail 額外描述固定/可變部分、可分離性、受詞位置、介系詞與合法變形。
Word 的搭配和獨立 Phrase 如語義確實相同，可由人工定義 target equivalence；不得僅因文字重疊自動共享掌握。

### LearningTarget 與 MemoryUnit

LearningTarget 是「要驗證的內容」：
- sense_comprehension：某義項的理解與語境辨識。
- usage_pattern：某搭配或用法。
- phrase_comprehension：完整片語意義。
- phrase_slot：片語關鍵成分/語序/介系詞。
- word_form：詞形回想或拼字（通常 Entry 層，不因每個義項複製拼字）。

MemoryUnit = 某使用者 + LearningTarget + response_mode。
response_mode 分 recognition、cued_recall、exact_form。選擇題成功不更新 exact_form，也不把 recognition 自動灌到 cued_recall。

不是每個詞一開始生成所有使用者狀態；只在該目標實際啟用時建立 MemoryUnit，避免一口氣排出數萬個待背項目。

### Question

有穩定 ID、revision、primary target、題型、response_mode、情境 family ID、題幹、固定核驗選項、接受答案集合、解釋、內容品質狀態與 train/check 分區。
一題只有一個主要計分 target。次要標籤幫助分析，不因整句答對就自動推定每個字都學會。

## 4. 使用者資料

| 實體 | 原始資料還是衍生資料 | 用途 |
|---|---|---|
| Enrollment | 原始決策 | 使用者明確加入/暫停的 Word 或 Phrase。 |
| Exam / ExamEntry | 原始決策 | 考試時間、書寫目標、內容歸屬。 |
| ImportBatch | 原始來源 | 一次匯入的名稱與項目；不是每天必選的單字本。 |
| Presentation | 暫存但須持久化 | 原題版本、選項順序、草稿、是否已提交。 |
| LearningEvent | 原始事件 | 作答、曝光、初始化、撤銷/修正等；唯一 event ID。 |
| LookupEvent | 有期限的原始事件 | 詞條查看與查詢提示；不當成作答。 |
| StudySlice | 原始時間片 | 活動/中斷/不確定時間；避免只存累計秒數。 |
| MemoryProjection | 可重算 | FSRS state、到期時間、證據狀態。 |
| LearnerCostProfile | 可重算 | 個人分題型耗時與後續負荷參數。 |
| DayPlan / Forecast | 可重算 | 計畫快照、版本、採用目標深度與原因。 |

原始事件至少有 event_id、schema_version、device_id、device_sequence、occurred_at_utc_ms、local_day、time_zone、entry_id、target_id、response_mode、presentation_id、question_revision、content_pack_version、policy_version。
作答 payload 保存原答案/正規化答案（若有）、選項順序、首次答案、提示、曝光/中斷標記與耗時；敏感匯出時預設移除原始自由輸入。

相同 presentation 的提交要冪等；重送不得多算一次。更正採新 correction/invalidation 事件，不直接改寫原始答案以掩蓋當時狀況。

## 5. 一次提交的交易

1. 取得當前 presentation，確認仍未提交且版本可計分。
2. 評分/正規化，產生 immutable event 和 evidence。
3. 在 user.sqlite 同一個 transaction 中：
   - 寫 LearningEvent（唯一 ID 與 presentation 約束）。
   - 寫此次已確認的 StudySlice。
   - 更新受影響 MemoryProjection。
   - 將 Presentation 設為 submitted。
   - 寫當日計画的輕量變更/失效標記。
4. commit 成功後，UI 才顯示已保存並切下一題。
5. commit 失敗：停在原題，顯示可重試訊息；不能裝成保存成功。

大型未來預測不放在交易內，也不放主執行緒。每次作答只更新少量 target；完整 forecast 在背景、日切換/匯入/修改考試或定期失效後重算。

## 6. 兩個 SQLite 的邊界

content.sqlite 隨 App 交付並以 read-only 開啟；V1 更新詞庫跟著 App build，不做網路動態下載。

user.sqlite 只存內容 ID/必要歷史快照，不複製完整詞典。SQLite 不能用普通 foreign key 跨這兩個 DB；跨庫關聯由 ContentCatalog、內容驗證工具和 migration 檢查，不能寫看似存在但無法生效的跨庫 FK。

搜尋資料與用戶歷史分開，避免升級詞庫意外重建 user.sqlite。

## 7. 內容與演算法升級

Content pack manifest 至少含：pack_id、version、schema_version、min_app_version、checksum、entry/phrase/target/question counts、licensing_profile、build_run_id。

義項改字不改 ID；語義實質改變要新 revision 或新 ID：
- 一對一同義替換：保留/明確映射。
- 一義拆兩義：保留歷史，但不能把原 mastery 複製成兩個都會；新義標為待確認。
- 多義合併：保留事件，對新 target 重新投影；不得平均兩個百分比就算完成。
- 移除內容：使用者項目標為暫不可用，可匯出、不丟紀錄。
- 撤銷歧義題：保留原始作答但排除無效測量，重算受影響 target。

新模型重放以「截至當時可見的事件」運算，不得使用未來回答。保留舊引擎版本與參數摘要以便比較。更換 source sense ID 不靠文字相等猜映射。

## 8. 備份、還原與刪除

V1 提供兩種明確用途：
- 完整本機備份：一致性 SQLite snapshot + manifest + 內容/演算法版本資訊。
- 可攜匯出：JSONL events、學習清單、考試、設定與必要 target 映射；供未來移植或使用者保存。

使用 SQLite/GRDB 的一致性備份；不可在 WAL 正在使用時只複製 user.sqlite。[S20]
備份不包含 LLM 金鑰或開發用來源原文。若尚未實作加密匯出，UI 必須明示檔案含學習資料，不得宣稱端對端加密。

V1 還原採「驗證 → 自動備份現況 → 原子替換」，不做未驗證的合併同步。資料庫毀損、未知較新 schema、校驗失敗都應拒絕還原且保留原資料。

本機資料使用 iOS Data Protection。清除全部學習資料與清除查詢歷史分開；後者不能刪掉正式作答歷史。長期原始作答保留到使用者刪除；查詢歷史預設只保留 90 天，因為它不用來重建 FSRS 正式記憶狀態。

OS 裝置備份是否啟用由使用者控制。App 應說「不自行上傳」，不能承諾作業系統永不備份。

## 9. 未來同步：預備契約，不在 V1 寫同步框架

V1 先做到穩定 ID、device sequence、更新版本、刪除 tombstone、可重放事件與可攜匯出。

有實際 Apple 多裝置需求後，可加 CKSyncEngine。它幫助傳輸與追蹤變更，但衝突、帳號切換、永久錯誤與本機 engine state 的保存仍是 App 的責任。[S12]

未來跨 Android/Web 時，優先讓所有平台共用同一中立同步服務；不要長期用兩套彼此無關的雲儲存同一個人的主進度。CloudKit → 中立服務要設計身份綁定與一次遷移，不只是換一個 protocol 實作。

同步規格的前置要求：
- sync 原始事件與使用者決策；mastery 不做 last-write-wins。
- event ID 去重，處理離線重送、晚到事件、時鐘偏差與跨裝置並行回答。
- 同一 target 同時在兩台機器答對，不能當兩次獨立長期提取來增加穩定度。
- 事件重放的順序与並行事件合併政策必須固定；只照手機牆上時間排序不夠。
- 帳號變更不可把前一個人的本地進度上傳給下一個人。
- tombstone 防止已刪除項目被舊裝置復活。
- 先完成同步測試矩陣，再移植 Android；UI 原生重寫與引擎移植是實際工作，不宣稱零成本。

## 10. Agent 工作流

Xcode 的外部 MCP 使用 xcrun mcpbridge，需在 Xcode 開啟權限與專案。[S13]
OpenCode 使用官方 local MCP 格式；只合併 xcode 設定，不覆蓋原本 OMO 與其他工作專案的設定。[S14]

SourceKit-LSP 可輔助套件的導航/引用，但索引及編譯上下文影響能力。[S15] 不把「LSP 沒錯」當成 iOS build 通過；也不假定只裝 SourceKit-LSP 就知道所有 .xcodeproj 設定。

驗證節奏：完成一組一致變更 → 聚焦 unit/integration tests → 受影響 iOS target build → 有 UI 改动則 simulator/preview + 必要真機檢查。不要每改一行跑全專案，亦不得把測試改弱來配合錯誤實作。
