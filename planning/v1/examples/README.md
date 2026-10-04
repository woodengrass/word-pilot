# examples/

格式與行為示例，給 `tools/validate_plan.py` 驗證 schema 與 SQL 匯入用。

- `content/*.json`：符合 `contracts/content-entry.schema.json` 的兩個條目（單字 intelligence、片語 account for）。
- `events/sample-events.jsonl`：符合 `contracts/review-event.schema.json` 的事件，含一筆提示後答對（fsrs_rating 為 null）。

這些不是全量詞庫，也未經正式雙語內容審訂：全部標為 `draft`、`learning_ready=false`、`review_status=pending`，不可直接當成已通過品質 gate 的正式內容。
UUID 由固定 namespace 的 uuid5 產生，只是為了讓示例可重現。
