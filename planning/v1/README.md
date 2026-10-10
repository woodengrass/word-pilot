# lexvane｜開發計畫 v1

狀態：可開始 M0。這是規格、資料契約與任務包，不是已完成的 App 或詞庫。

這些文件主要給 agent 讀。閱讀順序：

1. `agent/AGENTS.md`：工作規則，以及每個 milestone 要讀哪些文件。
2. `PLAN.md`：產品目標、核心規則、文件索引。
3. 當前 milestone 的 `agent/START-*.md`（目前是 `START-M0.md`）與 `contracts/tasks.json` 中該 milestone 的任務。

`agent/AGENTS.md` 要合併進專案既有的規則，不直接覆蓋。產品與 App 顯示名稱統一為 `lexvane`；新建 Xcode 專案與 Target 使用 `Lexvane`，Swift 型別依命名慣例使用 `LexvaneApp`。
