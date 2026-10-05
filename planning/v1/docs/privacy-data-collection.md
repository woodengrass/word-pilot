# Privacy-preserving research data collection

狀態：採用中的產品／架構原則  
目的：在不建立任何可讀的單一使用者研究資料庫下，取得足以改善 Word Pilot 演算法的群體統計。

## 核心決策

Word Pilot 採用「方案 A」：

- 完整作答歷史、學過哪些字、個人記憶曲線、個人化參數、精確時間線與 planner 狀態只留在使用者自己的裝置。
- 個人化學習本身完全在本機運作，不需要把個人模型上傳。
- 跨使用者的演算法改進只使用使用者明確同意後產生的研究 contribution。
- contribution 先在裝置上轉成有限、預先定義的統計或模型更新；不傳 raw events。
- 收集鏈路必須讓研究端無法讀取任何單一使用者的 contribution，也不應取得能把 contribution 與來源裝置／IP 長期連結的識別資訊。
- 只有達到最低群體門檻後的 aggregate 才能被研究端讀取。
- App 不因使用者拒絕研究資料分享而限制任何核心功能；撤回同意後停止未來 contribution。
- 不建立 user-level telemetry、research profile、個人雲端 FSRS 參數或「匿名 user ID + 完整歷史」資料庫。

這個原則獨立於未來的同步功能。即使日後加入 CloudKit 或其他跨裝置同步，同步資料也不能被默認拿來做群體研究。

## 為什麼這樣做

目前演算法真正需要的跨使用者資料主要是群體層級資訊，例如：

- population memory model / initial prior。
- 各題型 predicted vs actual 的 calibration。
- 題型耗時分布。
- planner 預估時間與實際時間的群體誤差。
- item / target difficulty 的 aggregate。
- 不同演算法版本的 aggregate outcome。

這些問題不需要研究端知道「哪一個學生做了什麼」。

個人的持續個人化則相反：它需要完整歷史，因此最適合留在裝置上處理。

## 資料邊界

### 永遠留在裝置上的資料

研究資料收集不應把下列內容傳到 Word Pilot 的研究基礎設施：

- raw answer / review events。
- 個人學過或查過的完整 word / phrase 清單。
- 個人 FSRS / memory parameters 或完整 memory curve。
- 自訂考試名稱、批次名稱、自由輸入內容。
- 可重建個人使用時間線的精確 timestamp sequence。
- device ID、Apple ID、CloudKit ID、帳號 ID 或穩定 research ID，除非未來某個研究問題真的不可避免且經過新的 privacy review。

### 可以考慮聚合的資料

資料應先在本機轉成研究真正需要的 bounded contribution，例如：

- calibration bins：某預測區間的 correct count / total count。
- 題型層級的 response-time histogram / quantiles contribution。
- planner forecast error 的統計量。
- 某 target 的 aggregate attempts / correct / prediction residual；必須受最低 cohort 門檻保護。
- population optimizer 所需的 aggregate update / sufficient statistics。

具體統計 schema 由要回答的研究問題決定，不為了「以後也許有用」收集額外欄位。

## Privacy-preserving aggregation 的結果要求

實作技術由 agent 在需要時研究與選擇，但最後必須滿足以下性質：

1. **沒有單一使用者可讀資料落在研究 backend。**  
   Application server、資料庫、dashboard 或一般 log 被完整取得時，不應出現某個人的 raw history、個人參數或可讀 contribution。

2. **來源身分與 contribution 分離。**  
   可考慮 Oblivious HTTP 類的 relay / gateway 分離，使看到來源 IP 的元件看不到可讀 contribution，而能處理 contribution 的元件看不到原始來源 IP。

3. **單一聚合方不足以解出個人 contribution。**  
   可考慮 multi-party secure aggregation、DAP/VDAF、Prio 類設計。至少一個獨立聚合方未被攻破／未串通時，單一 contribution 不應可被還原。

4. **只輸出群體 aggregate。**  
   未達最低 cohort 的統計不釋出。最低門檻屬 privacy parameter，需依 beta 規模與統計粒度驗證後決定，不在 planning 階段寫死。

5. **不能任意切 cohort。**  
   研究端不應能反覆查詢高度重疊的小群體並以相減方式還原個體。aggregate 應以預先定義的 metric schema / epoch 產生，而不是提供任意 SQL 式分群查詢。

6. **一般 infrastructure log 不得破壞匿名性。**  
   request body、IP、精確接收時間與其他 network metadata 的保留策略必須和 privacy claim 一起驗證；不能 payload 匿名、server log 卻能重新連回來源。

## Differential Privacy

V1／beta 不把 differential-privacy noise 當預設必要條件。

原因是本產品的第一目標不是公開一個可任意查詢的統計平台，而是取得少量預先定義的群體模型與 calibration 統計。若 secure aggregation、來源分離、最低 cohort 與固定查詢面已足以符合 threat model，引入 noise 可能只會降低演算法校準精度。

但 DP 不是永久排除。如果未來：

- 對外發布高度細分 aggregate；
- 允許大量 cohort slicing；
- 需要抵抗「攻擊者已知其他大部分參與者資料」的 membership / differencing inference；
- 或 privacy threat model 提高；

則重新評估 differential privacy。

## 同意與使用者控制

研究資料分享採 **explicit opt-in**：

- 不同意也可完整使用 Word Pilot。
- 同意畫面要清楚說明：完整學習歷史與個人模型留在裝置上；對外只貢獻無法由研究端讀取的群體統計／模型更新。
- 使用者可以撤回；撤回後不再產生新的研究 contribution。
- 已經完成且無法拆回個人的群體 aggregate，不應宣稱可以再抽出某個人的貢獻；隱私政策要清楚說明這一點。
- App 不需要 ATT，除非未來實際行為符合 Apple 對跨公司 tracking 的定義；本研究架構本身不應做 tracking。

Apple App Review Guideline 5.1.1(ii) 要求收集 user / usage data 時取得使用者同意，即使資料在收集當下或之後立即匿名化；因此匿名化不是省略 consent 的理由。

## 台灣個資法定位

本文件不是法律意見。

個資會目前的正式函釋明確區分「仍可能間接識別的去識別化資料」與「完全匿名且無還原可能性，因此不在個資法保護範圍內的資料」。方案 A 的目標是讓研究端最終只持有後者等級的群體 aggregate，而不是持有假名化的 user-level dataset。

在真正完成實作與 threat-model review 前，仍以較保守方式處理：
- 清楚告知與取得同意。
- 資料最小化。
- 不把研究資料另作其他用途。
- beta 涉及未成年人的同意流程，在公開／大規模使用前依實際發佈方式再次做法律確認。

## Threat model

這個方案要能合理承諾：

- Word Pilot application backend / database / dashboard 被攻破，不會得到可讀的單一使用者學習資料。
- 任一單一 aggregation party 被攻破，不足以還原 individual contribution。
- 研究端拿不到「來源 IP ↔ 可讀 contribution」的對應表。
- 最終只有滿足最低群體門檻的預定 aggregate。

這個方案**不**宣稱：
- 使用者自己的 iPhone 已被攻破時仍能保護該裝置內的資料。
- 所有獨立 aggregation parties、relay、gateway 同時串通／被完全攻破時仍有普通 secure aggregation 的同等保證。
- 在沒有 differential privacy 的情況下，能抵抗所有可能結合任意外部資訊的統計推論。

這些限制要反映在真正的 privacy claim 中。

## 驗收重點

進入會收研究 contribution 的 beta / release 前，至少驗證：

- 關閉 research sharing 時沒有任何研究 contribution 離開裝置，核心學習功能完全正常。
- raw learning events、個人詞彙歷史與 individual memory parameters 沒有研究 upload path。
- 研究 backend 沒有 user-level research table 或穩定 user/research identifier。
- 單一 backend compromise 或單一 aggregation share 無法讀出個人 contribution。
- aggregate 未達 privacy threshold 時無法釋出。
- 不能利用合法介面產生兩個高度重疊 aggregate 再相減得到個人 contribution。
- 一般 access/error logs 不保存足以把 contribution 重新連回來源的 metadata。
- consent、withdrawal 與 privacy-policy 文案和實際技術行為一致。

## 可研究的技術

這些是候選，不是預先指定的 implementation：

- IETF Oblivious HTTP (RFC 9458) 用於來源與內容分離。
- DAP / VDAF / Prio 類 multi-party privacy-preserving measurement / secure aggregation。
- 若未來 threat model 需要，再加入 differential privacy。

選型時以實際可審計性、iOS 支援、運維複雜度與 privacy guarantee 為準，而不是為了追求「密碼學很複雜」而過度設計。

## 官方參考

- Apple App Review Guidelines 5.1.1 / 5.1.2: https://developer.apple.com/app-store/review/guidelines/tw/
- Apple User Privacy and Data Use: https://developer.apple.com/app-store/user-privacy-and-data-use/
- 台灣個人資料保護法: https://law.pdpc.gov.tw/LawContent.aspx?id=FL010627
- 個資會函釋（完全匿名且無還原可能性的區分）: https://www.pdpc.gov.tw/News_Content/102/1058/
- IETF Oblivious HTTP, RFC 9458: https://datatracker.ietf.org/doc/rfc9458/
