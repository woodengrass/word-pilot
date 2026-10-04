# 08｜研究決策與未知事項

研究查核日期：2026-10-04。這份計畫區分三種依據：
- 已有研究/官方文件支持的方向；
- 本產品的可測試工程基線；
- 資料足夠後才應啟用的假設。

## 決策紀錄

| 決策 | 依據 | 不可延伸成的結論 |
|---|---|---|
| 持續提取、延遲檢查 | 詞彙提取研究 [S03] | 不是只要四選一做得快就長期會。 |
| 初教正確搭配後再提取 | L2 搭配研究 [S04] | 不是所有搭配測量都證明某個固定間隔最佳。 |
| 義項分開、逐步啟用 | 多義詞研究 [S05] | 不是固定學滿 N 次就永遠會第二義。 |
| 新字不强制先猜 | 預測試研究的族群/材料有界限 [S06] | 不是預測試無效，而是暫不把它當普遍最優預設。 |
| FSRS-6 adapter | 原始算法與 Swift 實作 [S09][S10] | FSRS 未自動解決選擇題猜測、異質題目或答案曝光。 |
| 先不用完整 IRT/BKT/深度模型 | 知識追蹤比較 [S08] | 簡單模型不是必然最好；需在自己的 held-out 資料比較。 |
| 保存 elapsed、格式、個人差異 | HLR [S07] | 不承諾拿一篇 Duolingo 論文參數就能轉移本產品。 |
| 有期限與成本限制的排程 | 最佳化間隔研究可作方向 [S26] | 本產品的 heuristic 不等同論文已證明全域最佳解。 |
| 不硬判個人疲勞上限 | 疲勞/考試時段研究適用情境有限 [S25] | 手機答慢不代表生理疲勞，也沒有普遍每日最多 50 詞。 |
| AI 全量審查 + 盲解 + 風險抽樣 | LLM judge 偏差研究 [S19] | 不同模型同意不等於詞庫無錯。 |

## 工程初值統一放 policy-v1.json

以下皆非學術最佳常數：
0.90 target retention、3 個穿插 target、24h delayed、stable 證據數與 7d lag、
普通題每 20 題最多 2 次鍵盤輸入、3 個日期查詢提示、每日最多 3 次同 target 補救、
04:00 學習日界線、成本先驗、shrinkage prior strength=30、32 組 forecast simulation。

改這些值要：
1. 版本化與說明假設。
2. 跑 deterministic 回歸與受影響事件 replay。
3. 用延遲新題/有效時間/負擔觀察，不只看當下分數。
4. 涉及評分標準或舊資料語義時保留舊版本，不靜默覆蓋。

## 認真保留的未知問題

- 二元 Again/Good 在這種混合 recognition 題庫的 FSRS calibration。
- 題目難度對記憶估計的偏差，以及片語/單字成本先驗差异。
- 自願查字對後續回答的提示效應；目前 reanchor 是保守設計，需防過度複習。
- 長文/選擇題訓練對實際試題的轉移，不以題型外觀相近保證。
- 目標深度縮減在考前的 coverage/retention 取捨。
- 手機零碎使用的計時誤差与個人有效時間估計。
- 個人化邊際效益需跨日延遲表現，且控制題目難度、先備知識和被系統選中的偏差。

這些不是開發前必須向使用者詢問的選项；先把可測基線與資料收集（本地）做對，再用測試者自願資料改進。

## 來源索引

完整機器可讀來源在 `contracts/sources.json`。以下保留用途、網址与限制；軟體依賴版本以實作時 lockfile 為準，資料來源則固定到內容包 manifest。

### [S01] 高中英文參考詞彙表（111 學年度起適用）
大考中心。查核日期：2026-10-04。
用途與限制：約六千詞條、六級；封面有非營利使用與營利用途書面授權條件。不是完整雙語詞典。

`https://www.ceec.edu.tw/files/file_pool/1/0K213635079130230766/高中英文參考詞彙表(111學年度起適用).pdf`

### [S02] 學測英文考科考試說明（115 學年度起適用）
大考中心。查核日期：2026-10-04。
用途與限制：測驗包括詞義、構詞、搭配、篇章運用與寫作。不能把一個詞彙 App 說成完整學測準備。

`https://www.ceec.edu.tw/files/file_pool/1/0P091472305863258925/01_115學年度起適用學測英文考科考試說明.pdf`

### [S03] The Critical Importance of Retrieval for Learning
Karpicke & Roediger, 2008, Science。查核日期：2026-10-04。
用途與限制：外語詞對的實驗支持成功回想後繼續提取練習；不是本產品最佳題型比例或間隔的直接證明。

`https://learninglab.psych.purdue.edu/downloads/2008/2008_Karpicke_Roediger_Science.pdf`

### [S04] Effects of retrieval schedules on the acquisition of explicit, automatized-explicit, and implicit knowledge of L2 collocations
Fang, Elgort & Chen, 2024, SSLA。查核日期：2026-10-04。
用途與限制：先學正確搭配再提取。間隔效果依測量能力而異，不代表所有指標都勝過集中練習。

`https://www.cambridge.org/core/journals/studies-in-second-language-acquisition/article/abs/effects-of-retrieval-schedules-on-the-acquisition-of-explicit-automatizedexplicit-and-implicit-knowledge-of-l2-collocations/201FABD72088A7F590598A5973E5B499`

### [S05] How well are primary and secondary meanings of L2 words acquired?
González-Fernández & Webb, 2024, SSLA。查核日期：2026-10-04。
用途與限制：該 EFL 實驗中熟詞新義不比生詞首義容易；支持分開記錄義項，不支持硬編最佳引入間隔。

`https://www.cambridge.org/core/journals/studies-in-second-language-acquisition/article/abs/how-well-are-primary-and-secondary-meanings-of-l2-words-acquired/D8D404658168A1BCC7BB9906765DE5DF`

### [S06] Duolingo-inspired pretesting with words and pictures improves vocabulary learning
Chua & Pan, 2026, Cognitive Research。查核日期：2026-10-04。
用途與限制：成人英語使用者學具體西班牙語名詞，搭配圖像。預測試值得測試，但不能直接外推高中抽象詞與搭配詞。

`https://link.springer.com/article/10.1186/s41235-026-00708-y`

### [S07] A Trainable Spaced Repetition Model for Language Learning
Settles & Meeder, 2016, ACL。查核日期：2026-10-04。
用途與限制：HLR 是可訓練的記憶模型，列為後續比較基線，不與 FSRS 疊成未驗證的總分。

`https://aclanthology.org/P16-1174/`

### [S08] When is Deep Learning the Best Approach to Knowledge Tracing?
Gervet et al., 2020, Journal of Educational Data Mining。查核日期：2026-10-04。
用途與限制：比較多種追蹤模型；模型好壞與資料條件有關，校準須檢查。不是 BKT 或深度模型對本 App 的背書。

`https://theophilegervet.github.io/assets/pdf/gervet2020deep.pdf`

### [S09] FSRS algorithm specification
Open Spaced Repetition。查核日期：2026-10-04。
用途與限制：FSRS-6 的 D/S/R、21 個參數與同日更新公式。適配客觀選擇題仍須產品層驗證。

`https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm`

### [S10] swift-fsrs
Open Spaced Repetition。查核日期：2026-10-04。
用途與限制：Swift 實作提供 FSRS-6 與 FSRS-5；明確指定演算法/參數，不能依 README 的預設敘述猜版本。

`https://github.com/open-spaced-repetition/swift-fsrs`

### [S11] GRDB.swift README
GRDB 作者與維護者。查核日期：2026-10-04。
用途與限制：SQLite、migration、observation、concurrency；本次看到的基準版本為 7.11.1。

`https://raw.githubusercontent.com/groue/GRDB.swift/master/README.md`

### [S12] CKSyncEngine
Apple。查核日期：2026-10-04。
用途與限制：協助同步本地與 CloudKit 紀錄；仍須處理狀態持久化、帳號與特定衝突，非零成本自動同步。

`https://developer.apple.com/documentation/cloudkit/cksyncengine-5sie5`

### [S13] Giving external agents access to Xcode
Apple。查核日期：2026-10-04。
用途與限制：Xcode 外部 agent 可用 xcrun mcpbridge；要啟用權限並開啟專案。

`https://developer.apple.com/documentation/xcode/giving-external-agents-access-to-xcode`

### [S14] MCP servers
OpenCode。查核日期：2026-10-04。
用途與限制：官方目前文件有 local stdio MCP 設定。須以使用者實際安裝版本驗證，不整份覆蓋既有設定。

`https://opencode.ai/docs/mcp-servers/`

### [S15] SourceKit-LSP README
Swift project。查核日期：2026-10-04。
用途與限制：SwiftPM / 編譯資料與索引狀態會影響語義工具；不能把 LSP 沒報錯當成 iOS 成功 build。

`https://raw.githubusercontent.com/swiftlang/sourcekit-lsp/main/README.md`

### [S16] Open English WordNet license
Open English WordNet。查核日期：2026-10-04。
用途與限制：CC BY 4.0 並保留底層 Princeton WordNet 的歸屬與條款；保留具體版本的授權檔。

`https://github.com/globalwordnet/english-wordnet/blob/main/LICENSE.md`

### [S17] License and Commercial Use of WordNet
Princeton University。查核日期：2026-10-04。
用途與限制：允許使用、修改與散布並有保留聲明要求。不是所有網路英文詞庫的共同授權。

`https://wordnet.princeton.edu/license-and-commercial-use`

### [S18] wordfreq licensing
wordfreq maintainer。查核日期：2026-10-04。
用途與限制：程式碼 Apache 2.0；資料與再散布另有 CC BY-SA 4.0 條件。列為隔離、可選來源。

`https://raw.githubusercontent.com/rspeer/wordfreq/master/LICENSE.txt`

### [S19] Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena
Zheng et al., 2023, NeurIPS / arXiv。查核日期：2026-10-04。
用途與限制：LLM judge 有位置、自我偏好等偏差。該研究不是詞典正確率驗證；本計畫據此保留盲審與人工抽驗。

`https://arxiv.org/html/2306.05685`

### [S20] Online Backup API
SQLite。查核日期：2026-10-04。
用途與限制：使用一致性備份，不在 WAL 活動時只複製單一 sqlite 檔。

`https://sqlite.org/backup.html`

### [S21] TestFlight overview
Apple。查核日期：2026-10-04。
用途與限制：對同學測試採 TestFlight；外部測試首個 build 需審查，build 有有效期限。

`https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview`

### [S22] Developer account overview
Apple。查核日期：2026-10-04。
用途與限制：Personal Team 可個人真機測試但有短期佈建限制；正式 beta 發布要另外處理開發者會員。

`https://developer.apple.com/tw/help/account/basics/about-your-developer-account`

### [S23] Linking to specific app scenes from your widget or Live Activity
Apple。查核日期：2026-10-04。
用途與限制：Widget 深連結直達字典/學習；入口意圖應優先於一般啟動導向。

`https://developer.apple.com/documentation/widgetkit/linking-to-specific-app-scenes-from-your-widget-or-live-activity`

### [S24] AVSpeechSynthesizer
Apple。查核日期：2026-10-04。
用途與限制：系統 TTS；實際離線聲音可用性與多音詞讀法仍要在目標裝置測試。

`https://developer.apple.com/documentation/avfaudio/avspeechsynthesizer`

### [S25] Cognitive fatigue influences students' performance on standardized tests
Sievertsen, Gino & Piovesan, 2016, PNAS。查核日期：2026-10-04。
用途與限制：學校考試中的時間與休息效應不能直接換算為手機背單字的每日吸收上限。

`https://www.pnas.org/doi/10.1073/pnas.1516947113`

### [S26] Enhancing human learning via spaced repetition optimization
Tabibian et al., 2019, PNAS。查核日期：2026-10-04。
用途與限制：提供在記憶模型與成本假設下最佳化的研究方向；不把理論最適性套到本產品未校準的規則上。

`https://europepmc.org/article/PMC/PMC6410796`
