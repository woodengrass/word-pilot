# 此專案的 Agent 實作規則

本檔是專案專用規則範本。與既有 AGENTS.md 合併，不覆蓋使用者其他通用開發規則。
先讀 planning/v1/README.md、docs/07-roadmap-tasks.md 與當前 milestone 涉及的規格。

## 範圍
- iOS-first、完全離線核心。不要自行新增登入、伺服器、OCR、照片解析、runtime LLM、廣告或付費。
- 日常由系統排程，不能用「選 deck / 選模式 / 自評熟悉度」繞過需求。
- 未加入詞的查詢不會自動 enrollment，大小寫永不扣分。
- 只實作被指定的 milestone；完成後報驗收，不順手展開全部後續系統。

## 架構
- 學習排程、評分與 planner 的核心邏輯不 import SwiftUI、UIKit、CloudKit 或資料庫套件；具體 module 形式由實作決定。
- 資料存取與核心邏輯分離（形式由實作決定）；一般函式注入 clock/calendar/seed，不隱藏讀取 Date.now。
- 保存原始事件與版本，衍生狀態可 replay；答案交易要原子且 idempotent。
- 不用供應商 sense IDs 當專案主鍵；不可在內容升版時重建所有 ID。
- schema/migrations、lockfile、Xcode project 由當前整合者單一負責，子 agent 不併發修改同一份。
- 建立必要接口即可，不製造尚無需求的 ServiceLocator、插件框架或雙向同步層。

## 研究與參數
- 規格中標為工程初值的門檻不是文獻最佳常數。
- FSRS wrapper/defaults 先核對版本與 conformance，不憑記憶猜 API。
- 不把答得快、查字、單次選擇答對直接等同掌握。
- 無法可靠評分的題目標 unscorable/quarantined，不扣學生分數。
- 不默默改教學效果定義來讓 forecast 看起來可行。

## 工具與驗證
- iOS build/test 以 Xcode 結果為準；可用 Xcode MCP，CLI 作 fallback。
- LSP 幫助導覽與局部診斷，不把它當完整 Xcode target build。
- 跑 coherent change 的 focused tests；跨共用邏輯/資料 migration 再跑相關整合測試。
- 超時是未知，不是通過；缺 Xcode/授權/真機不能寫成已驗證。
- 收到 API 或 symbol 不確定時查官方文件/依賴源碼，再修改。
- 保留既有 OpenCode + OMO 配置，新增 MCP 只 merge 對應欄位。
- 不上傳私人資料、不接受付費合約、不修改正式簽名團隊，除非取得明確授權。

## 內容
- 素材有 source/license/derivation/review lineage；pending 權利不視為已批准。
- AI 審核通過不是法律授權，也不是答案絕對正確。
- contracts/content.sql、user.sql 是參考草稿，不是必須遵守的 schema；實作時依 docs/02 的資料需求自行設計 migration，並補真實回歸測試。

## 每次交付
報告完成的任務 ID、修改檔案、實際執行與未執行的驗證、政策/資料版本、限制和下一個可實作任務。
