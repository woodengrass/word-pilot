# 03｜學習、評分與記憶排程基線

## 1. 基本做法

反覆提取、間隔安排、立即正確回饋、語境與搭配練習。研究依據與限制見 `docs/08` 決策紀錄。

- 預設短教學後再作答，不把每個新字逼成先猜題（預測試留作後續實驗）。已學項目、或過往已有強證據的目標可以直接測。
- FSRS 只負責記憶狀態與複習時間；題目品質、猜測、技能轉移、時間規劃由本產品其他部分處理。
- V1 不疊加 BKT、IRT、HLR 或深度模型；先有透明基線與資料。

本文件中的數值都在 `contracts/policy-v1.json`，以 key 名稱引用。

## 2. 學習目標、能力證據與複習義務要分開

需要區分不同義項、用法、辨認與產出能力，例如 intelligence 的「智力」、「情報」、gather intelligence 用法與實際字形產出。**這是證據隔離的要求，不是「每個 target × 每種 response mode 都必須生成一份獨立的每日複習卡」的要求。**

- 一次 presentation 的成本只計一次，主要被測的 target 取得直接證據；確實涉及的其他能力可留下有限的輔助訊號，但不能把同題當多次獨立成功或多次 FSRS Good。
- 沒有測到的第二義、拼寫、自由產出，不因語境選擇題正確而自動通過。
- 反過來，非書寫考試也不要求每個詞都通過中翻英、英翻中及精確拼字才可降低練習強度。
- 記憶狀態可依能力分別保存，但新增義項／題型不應機械地增加等量的長期複習義務；由當前目標與已取得的有效證據決定下一步。實作形式由 agent 評估，避免為此提早建大型知識追蹤框架。

Word 與 Phrase 使用同一 FSRS adapter，但不同 target 集合、題型與耗時先驗。沒有證據顯示「片語必須用另一套遺忘方程」，所以不憑空寫第二個 FSRS；先確保片語不被當成單字拆解、也不從構成詞繼承掌握。

例如 account for：
phrase_comprehension 測「解釋/占比」的適用義；phrase_slot 測 for 或其他關鍵結構；完整產出為 cued_recall。知道 account 一個字不算知道 account for。

## 3. 第一次學習

一次只呈現一個主要義項與一個相關用法：
- 英文、詞性、清楚的繁中義。
- 一個高價值搭配或固定用法。
- 一個易讀例句，可點發音。
- 可展開其餘資料，但不要求當下背全部。

閱讀時間由使用者控制，不固定「看 3 秒就下一題」。
接著穿插其他 target，再用不同表述的簡短題目練習。至少隔 `memory.intervening_distinct_targets` 個不同 target；若清單不足，換活動或稍後再測，不連續強灌相同題。

多義引入：以內容優先分級與學生實際目標決定先學哪個義項，**不預設辭典第一義就是唯一基礎義**。核心能力已有初次教學與有效應答後，可在時間允許時加入其他重要義；不必等第一義長期穩定，也不一次開全部義項。使用者指定的考試範圍不能被低詞頻自動排除。

教學閱讀與看到答案都屬 exposure，不是「已會」的證據。

## 4. 題型與最低要求

| 題型 | 主要 target | 注意事項 |
|---|---|---|
| **1–2 句語境克漏字：句子空格選英文詞** | sense / usage | V1 非書寫考試的主力；依 item 明確指定主要測量目標，選項合理、唯一可答。 |
| 英文語境 → 意義選擇 | sense_comprehension | 可教學或輔助診斷；只靠上下文猜出已印在題目的 target 意義，不能替代「能從選項選對詞」的直接證據。 |
| 概念/中文提示 → 英文選擇 | sense 或 word_form / recognition | 是辨認，不等於無提示回想；不能成為所有考試字的必做門檻。 |
| 搭配/片語槽位選擇 | usage / phrase_slot | 干擾項符合相同詞性，語境排除歧義。 |
| 多義情境辨識 | sense | 不考「第幾個意思」，考實際用法。 |
| 短文小題組 | 每小題一個 target | 共享閱讀耗時，不把整段時間乘以題數。 |
| 短輸入回想 | word_form / cued_recall | 少量；答案不確定、有效近義詞無法判斷時不硬扣。 |
| 精確拼寫/片語產出 | exact_form | 只在書寫目標啟用；大小寫仍不扣。 |

普通學習中，最近 `interaction.typing_window` 個計分 presentation 最多 `interaction.ordinary_typing_max` 個必需鍵盤輸入；這是操作負擔上限，不必填滿。
短文小題組的長度與小題數見 `interaction.short_passage_words`、`interaction.short_passage_items`；預估剩餘時間太少時不開始。使用者仍能中斷，閱讀與答案草稿保留。

不能把所有相關詞以字母順序排成一組連續教；也不刻意在首次教學大量混入極相似詞。易混辨識在各自意義已建立後才作候選。

## 5. 題目有效性優先於學生分數

每次評分先判斷：
1. 題目 revision 是否有效、是否被本機回報暫停。
2. 是否已展示答案/提示。
3. 是否有中斷、未提交或技術故障。
4. 此題是否真的測到主要 target：例如不能只在題目印出 `issue`，再要求學生靠雜誌上下文猜它的意思，就宣稱已具備選詞能力；在句子留空、`issue` 列為選項的題目，也須有合理干擾項、只有一個合格答案，不能單靠詞性或荒謬選項秒殺。利用題目本來提供的語境合理推論是有效的考試能力，**額外提示／先看答案**才是受輔助練習。
5. 回答是否属于已審核的接受答案/別名。

「回報題目有問題」立即暫停該 revision，這次測量暫不影響 mastery。使用者不必先證明自己對；後續內容修正可在開發階段處理。

無資料或答案語義不確定：回傳 unscorable，而不是 false。例句克漏字若很多近義詞成立，改成有核驗選項或重寫題目，不讓離線評分器硬猜自由文字含義。

## 6. 拼字與輸入判分

共同正規化：Unicode 正規化、前後空白、合理的多重空白、大小寫不敏感；保留原輸入供本機回溯。
合法英美拼法、彎直引號與可接受屈折形式由內容包明確列出。
不要全局刪除連字號/介系詞/否定詞；re-sign 和 resign 不可因正規化變成同字。

一般 cued_recall：
- 命中接受答案：correct。
- 只差一個字元、長度足够且唯一對應目标、又不是另一個真實英文詞：可記 lexical_recall=correct、orthography=incorrect。
- form/from、trial/trail 等本身都是詞：不可只憑 edit distance 自動判對。
- 不確定為同義可接受答案：unscorable，顯示參考說法並標記內容需擴充。

exact_form：
- 先做上述不涉及語義的正規化；再嚴格比對合法答案。
- intelligence / Intelligence / INTELLIGENCE 全部相同。
- 大小寫不會在任何單字或片語拼字練習中扣分。
- 詞形與時態錯誤若不是當題明確測量目標，不能擴大解讀為整個單字不會。

一個輸入可產生「回想成功、拼字失敗」兩個明確不同的 observation；計算學習量與耗時時仍只是一個 presentation，不能灌成兩次獨立測量。

## 7. FSRS adapter：ObjectiveRatingV1

明確使用 FSRS-6。**目標記憶率（desired retention）不是固定值，也不是產品目標**：它是演算法依內容價值、考試期限、時間壓力、個人記憶曲線與已有證據，為每個 target 動態決定的手段（見 `docs/04-planner-personalization.md` §5a）。起始值 `memory.initial_desired_retention` 只在資料不足時使用，也不代表考試答對率。V1 在本機資料足夠時可以漸進擬合少量可信參數；只有通過未參與擬合資料的預測驗證、且不造成不合理排程突變才採用。資料不足或驗證無改善時用 FSRS-6 預設參數（[S09]）；有群體研究結果後才可改用族群起點。絕不把擬合列為核心使用門檻。[S09][S10]

| 作答事件 | 內部處理 |
|---|---|
| 有效、無提示、首次提交答對 | Good（3）。 |
| 有效、無提示、首次提交答錯 | Again（1）。 |
| 看提示/看答案後答對 | assisted_practice，不能作 Good。 |
| 沒提交、離開、程式故障 | unscorable，沒有 FSRS grade。 |
| 教學閱讀、查字 | exposure，沒有 FSRS grade。 |
| 有疑義/已撤銷題目 | invalidated，沒有 FSRS grade，必要時重放。 |

不從反應快慢映射 Hard/Easy；V1 不使用 2/4 級。這個二元映射是本產品的可測試基線，不是 FSRS 對選擇題的官方效果保證。

### 初始學習與同日練習

新 target 的 exposure 建立 acquisition 狀態，不直接建立 Good 紀錄。
首次無提示、與剛看答案有合理間隔的應答可以初始化 FSRS；短間隔練習另標 short_term。
同一次 presentation 最多更新一次；直接照剛才顯示的答案再按一次不是新的提取。

由 adapter 明確區分：
- practice：穿插的其他 target 未達 `memory.intervening_distinct_targets`，且剛看過同答案，僅練習。
- short_term：有穿插但距最新相關答案曝光未達 `memory.delayed_min_seconds`，記為同日/短間隔 observation。
- delayed：距最新相關答案曝光至少 `memory.delayed_min_seconds`。
後兩者可更新記憶排程，但只有 delayed 可提供長期穩定證據。

必須用參考實作測試 FSRS 的同日更新、跨日定義、失敗重學、時區和 fractional elapsed time；若 Swift wrapper 有自己的 learning steps，要停用或明確與本 App 合併，不能兩套短間隔排程同時工作。

### 外部查字/額外曝光造成的污染

對很久没測的 target，剛查過答案後答對，不能按「隔了 60 天仍記得」提高穩定度。
V1 採保守干預：
- 已知有額外答案曝光後的診斷若正確，不增加 S/D；以可追溯的 reanchor 事件重設觀察起點，保留原能力歷史，安排下一個獨立檢查。
- 診斷若無提示仍答錯，可記 Again。
- reanchor 是本產品的明確例外，不偽裝成原版 FSRS grade；不能用它訓練 FSRS 的 recall labels。
- 下一個獨立檢查不晚於原先計畫與 `memory.reanchor_validation_max_days` 天中的較早者；原日期已過則至少留 1 天，不立即重刷。
- 這個規則是否過度複習需在 beta 評估；純 lookup 本身不觸發重設，只有後續診斷處理曝光污染。

這避免把被提示的成功變成「長期記得」，也避免每次翻字典直接把熟字打回新字。

## 8. 掌握狀態：不輸出假精確百分比

V1 採可解釋的證據狀態，不把手填權重叫 Bayesian mastery probability。

- not_started：尚未教/測。
- learning：已教或練習，證據不足。
- foundation_verified：達到 `evidence.foundation` 的無提示有效成功數、情境 family 數與 delayed 成功數；相關重要 target 也需滿足。
- stable：達到 `evidence.stable` 的 delayed 成功數、學習日期數、一次長間隔，以及一次先前未曝光的合格 check family。
- reinforcement_needed：出現正式失敗或新內容使舊證據不足；歷史不清空。
- suspended：使用者暫停，排程不可自行恢復。

「目前穩定」不代表永久學會。到期狀態另外呈現，可逐漸拉長間隔；系統不可能達到完全確定永不忘記。

這些次數／日數只用於描述**特定證據的可靠程度**，不是每個考試義項永久需要繳交的最低複習次數，也不是科學最佳常數。deadline、考試型態與必要能力影響「對目前考試是否已有足夠證據，可以減少密集複習」；不能改寫原始答對／答錯、虛構多份獨立證據，或把學會語境選詞顯示成已能拼字。已足夠的能力仍保留間隔檢查可能性，有錯誤／長時間未驗證時可再加強。

一個詞的狀態來自當前目標範圍內的 target，不取各義項平均，避免「第一義很熟」掩蓋「第二義完全沒學」。

## 9. 反猜測與題目記憶

四選一隨機猜對機率 1/4 是數學模型，不表示每題學生的實際猜測率都是 25%。不能以連對三題就直接計算 1/64 並宣稱確定會，因為題目可能相關。

措施：
- 選項位置洗牌並保存順序。
- 不同情境 family，避免只換人名。
- 隔日/隔週檢查。
- 純中英選項題不單獨满足完整 target 的驗收，需有語境題。
- 少量 cued_recall 作能力檢查，recognition 與 recall 不互相灌分。
- 題庫有 train/check 分離；check 的句子不可預先當字典例句展示。
- check 一旦出過，就不再算未見題；以新 family 或內容版本補充評量。
- 同 family 重複答對可幫練習，但不增加「情境多樣性」證據。

## 10. FSRS 與題型之間的限制

初期混合了不同難度的 recognition 題，FSRS 的預測仍可能失準。因此记录题型、family、編輯難度、干擾項、答案曝光，按格式分层評估 calibration，不能只看全域平均正確率。

題型不能全數跨成單一「intelligence 0.92」。尤其要區分「已知英文形式能否判斷意思」、「句子留空能否選出正確字」與「能否自行產出字形」；不夠資料時，採較保守的到期安排與狀態顯示，不製造「難度已校準」的說法。

**驗收重點：**在合理難度的未見考試型語境題上能作答，是非書寫考試的主要結果；模型中的 FSRS R、foundation_verified、review due 都只是安排與解釋證據的工具。減少重複練習後，須以相同時間下的未見題表現確認沒有以遺忘換取表面效率。

後續的校準模型見 `docs/08`「後續研究候選」。

## 11. 最小接口（示意，實作可調整命名與形式）

```
score(question, response, normalizationRules) -> ScoringResult
classifyEvidence(presentation, events, exposures) -> Evidence
updateMemory(state, evidence, now, policy) -> MemoryTransition
deriveStatus(historySummary, requiredTargets, policy) -> EvidenceStatus
eligibleQuestions(target, mode, seenFamilies, contentVersion) -> [Question]
```

MemoryTransition 包含 new_state、next_due、applied_rule、version、理由。所有判斷可由 debug 頁面查出，不能只存 opaque mastery。
