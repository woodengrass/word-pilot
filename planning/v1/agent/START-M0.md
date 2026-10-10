# M0｜建立可靠的開發基礎

先閱讀：

- `planning/v1/agent/AGENTS.md`
- `planning/v1/PLAN.md`
- `planning/v1/docs/02-architecture-data.md`
- `planning/v1/contracts/tasks.json` 中 milestone 為 M0 的任務（T001–T004）

## 目標

建立一個之後能安心開發 lexvane 的 iOS 基礎。

這一階段不需要實作完整字典、學習演算法、全量詞庫或漂亮 UI。重點是確認選定的技術與專案結構能支援後續需求，而不是先把未來架構全部做出來。

## 已知技術方向

- 原生 iOS：Swift / SwiftUI / Xcode。
- 本地資料需要適合大量離線詞庫、事件紀錄、搜尋與 migration；SQLite + GRDB 是目前優先候選。
- 記憶模型在 M3 才接入；M0 不需要為了「預留」而提前把算法接進來。
- OpenCode + OMO 是主要 agent 工作流；Xcode tooling 應能真正驗證 iOS build。

如果檢查 repo 或官方資料後認為具體做法應調整，可以自行決定並記錄理由。

## M0 完成條件

- iOS App 可以用實際 Xcode toolchain build 並在 Simulator 執行。
- 專案有可持續使用的 automated test 基礎。
- 本地持久化方向已被實際驗證，能保存並重新讀取簡單測試資料。
- 主要 dependency 與 toolchain 版本可重現。
- OpenCode/OMO 與 Xcode 的實際工作方式已驗證；不要破壞現有 OMO 設定。
- 架構足以繼續 M1/M2，但沒有為尚未發生的同步、Android、複雜算法做大量預先工程。
- 對任何仍不確定的重要技術選擇，留下簡短 decision note，而不是用猜測鎖死未來。

只有遇到需要產品 owner 決定的事項才詢問；一般 Swift、Xcode、database、dependency 與測試問題自行調查解決。

完成 M0 後停下來，回報驗證結果與下一個合理 milestone。