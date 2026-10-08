# 07｜實作順序與可派工任務

## 1. 分段交付，不一次做完所有模組

| 階段 | 完成後能做什麼 | 不在這一階段做 |
|---|---|---|
| M0 開發基礎 | Xcode 可建置、測試可跑、本地持久化已驗證、依賴可重現、技術決策有紀錄。 | 學習算法、漂亮首頁、全量生成、帳號同步。 |
| M1 內容 pilot | 200 詞 + 30 片語有來源、義項優先分級與合理語境選詞題，內容包可重建。 | 一口氣生成全部十萬題、完整考古題統計平台。 |
| M2 離線字典與資料安全 | 查字、一鍵加入、批次匯入、local persistence、可備份還原。 | 學習效率模型的高階訓練。 |
| M3 核心學習循環 | 以語境選詞為主的有效作答 -> 可追溯證據 -> 記憶排程與下一題；避免重複複習義務、可續接。 | 複雜 deadline 最佳化、fatigue personalization。 |
| M4 自動規劃 | 每日時間與原始考試範圍／期限約束、forecast、合理調整新舊內容、資料夠多時的本機記憶校正。 | 精確因果得分率模型、CloudKit、Android、付費。 |
| M5 完整內容與可靠性 | 內容擴展、版本遷移、壞題撤銷、實機負載、可供同學測試。 | 對外宣稱經證明提升學測成績。 |
| M6 beta 與校正 | 跨日使用、修內容/體驗，以相同時間的未見語境題與原始範圍覆蓋檢驗效果。 | 無資料就上大型自適應模型；未通過 privacy gate 不啟用研究上傳。 |

里程碑用驗收 gate，不承諾幾天完成。資料授權、全量內容審查和真實延遲測試可能比寫 UI 更慢。

## 2. 主線依賴

```
M0 -> M1 -> M2 -> M3 -> M4 -> M5 -> M6
                   \------ 備份/還原 ------/
       內容 pipeline 在 pilot 穩定後可與 App 開發並行
```

內容全量化應等 M3 題型與 scorer 的格式穩定，再大規模執行；不要先生成後全部重做。
一個 milestone 裡可以完成多個小提交，每個 coherent change 執行對應測試，不每改一行就全專案 build。

## 3. 任務清單

33 個任務（T001–T033）的依賴與驗收條件只寫在 `contracts/tasks.json`，這裡不重複。依 `depends_on` 決定順序；同一 milestone 內沒有依賴關係的任務可以並行。

## 4. OpenCode + OMO 的工作分配

一次指定一個 milestone，主 agent 負責整合：
- app/domain agent：App 與學習核心邏輯，不能改內容 schema 而不通知整合者。
- content agent：pipeline/fixtures/provenance，不改個人學習狀態定義。
- tests/review agent：獨立驗收，先看資料完整性和錯誤評分，不只看格式。

schema/migration、Package.resolved、Xcode project 設定一次只有一個寫入者。
子 agent 可先提出差異或在不同分支工作，不讓多個進程同時修改同一個 Simulator/local DB 或打架寫 pbxproj。
不用為了這個專案增加一堆新 harness/插件；保留使用者既有 OMO。

每個任務交付必須包含：
變更檔案、通過/未跑的測試、資料/政策版本、已知限制、下一個可執行任務。
不把「看起來可編譯」寫成「build 成功」。

## 5. 後續階段，先不實作

P1 Apple 裝置同步：真的有多 Apple 裝置需求後再做 CKSyncEngine adapter、account lifecycle、衝突與離線合併演練。[S12]
P2 Android/桌面：依實際測試群決定 client 技術與中立 backend；共用內容 ID、事件 contract、政策 test vectors。不可讓两个獨立雲都掌管同一份狀態而沒有合併規則。
P3 進階個人化：V1 的本機 FSRS 校正見 T032；後續候選模型見 `docs/08` 的「後續研究候選」。
P4 收費/開源：分離 code/content 授權；不把營運決策塞入 V1 核心架構。
