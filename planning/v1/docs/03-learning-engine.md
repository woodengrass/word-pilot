# 03｜學習、評分與記憶排程基線

## 1. 證據支持什麼，沒有支持什麼

本產品採用反覆提取、間隔安排、立即提供正確回饋、語境與搭配練習。外語詞對實驗支持持續提取對延遲保留的作用；搭配詞研究支持把正確用法的初次學習與後续提取結合，但不同能力測量的效果不同。[S03][S04]

第二義不能因為主字形熟悉就自動算已會。[S05] 這支持分開記錄義項，不提供「第一義學三次後一定要教第二義」的最佳常數。

預測試可能有益，但所讀研究使用成人、具體名詞與圖像，並不是台灣高中抽象詞/搭配詞的完整證據。[S06] V1 默認短教學後作答；已學項目、使用者過往強證據支持的目標可以直接測。預測試作為後續實驗，不把每個新字逼成猜題。

FSRS 只負責記憶狀態與複習時間，沒有替本產品完成題目品質、猜測、技能轉移、時間規劃與疲勞建模。[S09]
V1 不先疊加 BKT + IRT + HLR + 深度模型。先有透明基線與資料；HLR、logistic knowledge tracing 是後續比較候選。[S07][S08]

## 2. 學習單位與能力隔離

每個啟用中的 MemoryUnit = target_id × response_mode × user_id。

例：
- intelligence / 智力義 / recognition
- intelligence / 情報義 / recognition
- intelligence / gather intelligence 用法 / recognition
- intelligence / 字形回想 / cued_recall
- intelligence / 字形拼寫 / exact_form

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
接著穿插其他 target，再用不同表述的簡短題目練習。V1 初值為至少隔 3 個不同 target；若清單不足，換活動或稍後再測，不連續強灌相同題。

多義引入：第一義已經完成首次教學且有一次有效應答後，第二個重要義可成為候選；是否當天加入由時間負荷決定。不能要求第一義達到長期穩定才開第二義，也不一次開全部義項。

教學閱讀與看到答案都屬 exposure，不是「已會」的證據。

## 4. 題型與最低要求

| 題型 | 主要 target | 注意事項 |
|---|---|---|
| 英文語境 → 意義選擇 | sense_comprehension | 不用多個同樣合理中文選項硬湊唯一答案。 |
| 概念/中文提示 → 英文選擇 | sense 或 word_form / recognition | 是辨認，不等於無提示回想。 |
| 1–2 句語境克漏字 | sense / usage | 依 item 明確指定主要測量目標。 |
| 搭配/片語槽位選擇 | usage / phrase_slot | 干擾項符合相同詞性，語境排除歧義。 |
| 多義情境辨識 | sense | 不考「第幾個意思」，考實際用法。 |
| 短文小題組 | 每小題一個 target | 共享閱讀耗時，不把整段時間乘以題數。 |
| 短輸入回想 | word_form / cued_recall | 少量；答案不確定、有效近義詞無法判斷時不硬扣。 |
| 精確拼寫/片語產出 | exact_form | 只在書寫目標啟用；大小寫仍不扣。 |

普通學習初始上限：最近 20 個計分 presentation 最多 2 個必需鍵盤輸入。這是操作負擔的工程初值，不是最佳教育比例；不保證一定填滿名額。
短文小題組初期 50–100 個英文詞、2–3 小題；預估剩餘時間太少時不開始。使用者仍能中斷，閱讀與答案草稿保留。

不能把所有相關詞以字母順序排成一組連續教；也不刻意在首次教學大量混入極相似詞。易混辨識在各自意義已建立後才作候選。

## 5. 題目有效性優先於學生分數

每次評分先判斷：
1. 題目 revision 是否有效、是否被本機回報暫停。
2. 是否已展示答案/提示。
3. 是否有中斷、未提交或技術故障。
4. 此題是否真的測到主要 target，而非只靠語法排除或句外常識。
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

明確使用 FSRS-6，固定参数版本。起始 desired_retention=0.90 是排程參數，不是對使用者宣稱 90% 會考對；V1 不自動擬合每個人的 21 個參數。[S09][S10]

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
- practice：尚未有 3 個其他 target 且剛看過同答案，僅練習。
- short_term：有穿插但未達 24 小時，記為同日/短間隔 observation。
- delayed：距最新相關答案曝光至少 24 小時。
後兩者可更新記憶排程，但只有 delayed 可提供長期穩定證據。24 小時與 3 個穿插項是保守工程初值。

必須用參考實作測試 FSRS 的同日更新、跨日定義、失敗重學、時區和 fractional elapsed time；若 Swift wrapper 有自己的 learning steps，要停用或明確與本 App 合併，不能兩套短間隔排程同時工作。

### 外部查字/額外曝光造成的污染

對很久没測的 target，剛查過答案後答對，不能按「隔了 60 天仍記得」提高穩定度。
V1 採保守干預：
- 已知有額外答案曝光後的診斷若正確，不增加 S/D；以可追溯的 reanchor 事件重設觀察起點，保留原能力歷史，安排下一個獨立檢查。
- 診斷若無提示仍答錯，可記 Again。
- reanchor 是本產品的明確例外，不偽裝成原版 FSRS grade；不能用它訓練 FSRS 的 recall labels。
- V1 的下一個獨立檢查預設不晚於原先計畫與 7 天中的較早者；原日期已過則至少留 1 天，不立即重刷。
- 這個規則是否過度複習需在 beta 評估；純 lookup 本身不觸發重設，只有後續診斷處理曝光污染。

這避免把被提示的成功變成「長期記得」，也避免每次翻字典直接把熟字打回新字。

## 8. 掌握狀態：不輸出假精確百分比

V1 採可解釋的證據狀態，不把手填權重叫 Bayesian mastery probability。

- not_started：尚未教/測。
- learning：已教或練習，證據不足。
- foundation_verified：至少 2 次無提示有效成功，至少 2 個情境 family，其中至少 1 次 delayed；相關重要 target 也需满足。
- stable：至少 3 次 delayed 成功，跨至少 3 個學習日期，含一次間隔至少 7 天、以及一次先前未曝光的合格 check family。
- reinforcement_needed：出現正式失敗或新內容使舊證據不足；歷史不清空。
- suspended：使用者暫停，排程不可自行恢復。

「目前穩定」不代表永久學會。到期狀態另外呈現，可逐漸拉長間隔；系統不可能達到完全確定永不忘記。

上述次数/日數是 Policy v1 的驗收規則，需按 beta 的延遲新題表現調整；不應對外稱學術最佳門檻。deadline 只改變目前優先取得哪些證據，不改每次答對/答錯與 foundation_verified 的定義。

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

題型不能全數跨成單一「intelligence 0.92」。不夠資料時，採較保守的到期安排與狀態顯示；不要製造「難度已校準」的說法。

後續候選：以 FSRS 的 logit(R)、題型、詞/片語種類、實際 lag、提示、近期錯誤等特徵，訓練正則化 logistic 校準器；需要 held-out 評估，改善才啟用。[S08]
V1 不訓練大型 DKT，不把 IRT 的資訊量最大化當成學習收益最大化。

## 11. 最小接口

```
score(question, response, normalizationRules) -> ScoringResult
classifyEvidence(presentation, events, exposures) -> Evidence
updateMemory(state, evidence, now, policy) -> MemoryTransition
deriveStatus(historySummary, requiredTargets, policy) -> EvidenceStatus
eligibleQuestions(target, mode, seenFamilies, contentVersion) -> [Question]
```

MemoryTransition 包含 new_state、next_due、applied_rule、version、理由。所有判斷可由 debug 頁面查出，不能只存 opaque mastery。
