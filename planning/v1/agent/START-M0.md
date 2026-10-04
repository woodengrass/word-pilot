先閱讀 planning/v1/README.md、docs/01-product.md、docs/02-architecture-data.md、
docs/07-roadmap-tasks.md、contracts/ 與 agent/AGENTS.md。

本次只完成 M0：T001–T004，不做完整 App、不生成全量詞庫。
若 repo 已存在先檢查，不覆蓋既有設定、程式、AGENTS.md 或 OpenCode/OMO 配置。

請建立可建置的 iOS SwiftUI 專案與一個純 Swift StudyCore package，
部署目標以規格的 iOS 17 作起点，核對實際可用 Xcode/Swift/SDK。
加入並鎖定 GRDB 與合適的 FSRS-6 Swift 實作；明確確認所用參數和同日學習行为。
把 contracts SQL 對應成 migration 基線，建立 versioned policy decoding、
可注入 clock/calendar/seed 和最小測試，不提前做未使用的架構層。
確認 Xcode MCP 是否可用，保留 CLI fallback；不要替我重配 OMO 模型。

驗收：
1. Simulator 可啟動空白 App。
2. StudyCore 測試可執行。
3. 兩份 DB 可以建立，foreign key / integrity check 通過。
4. policy 與 sample contracts 可讀。
5. 記錄 dependency 版本及實際 build/test 結果。
6. 列出尚需使用者操作的簽名/權限；沒有這類阻礙就自行完成，不問學術參數問題。

完成後交付變更、測試、限制，停在 M0 gate，勿直接進下一里程碑。
