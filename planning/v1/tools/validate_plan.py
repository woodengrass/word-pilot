#!/usr/bin/env python3
"""Spec checks for planning/v1.

Checks that referenced files exist, JSON schemas and examples agree, both SQL
contracts load and accept the examples, the user DB guards (atomic rollback,
one answer per presentation, required answer fields) hold, policy invariants
are intact, the task DAG is well formed, and every [Sxx] citation resolves.

It does not build Swift, check FSRS numerics, or test on a device.

Usage: python3 tools/validate_plan.py [--output validation-report.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
results: list[dict] = []


def check(name: str):
    def wrap(fn):
        try:
            detail = fn()
            results.append({"check": name, "ok": True, "detail": detail or ""})
        except Exception as exc:  # noqa: BLE001 - report every failure
            results.append({"check": name, "ok": False, "detail": f"{type(exc).__name__}: {exc}"})
        return fn
    return wrap


def load_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def content_examples() -> list[tuple[str, dict]]:
    return [(p.name, json.loads(p.read_text(encoding="utf-8")))
            for p in sorted((ROOT / "examples/content").glob("*.json"))]


def event_examples() -> list[dict]:
    lines = (ROOT / "examples/events/sample-events.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def open_db(rel: str) -> sqlite3.Connection:
    db = sqlite3.connect(":memory:", isolation_level=None)
    db.executescript((ROOT / rel).read_text(encoding="utf-8"))
    db.execute("PRAGMA foreign_keys = ON")
    return db


def assert_db_clean(db: sqlite3.Connection):
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "integrity_check failed"
    fk = db.execute("PRAGMA foreign_key_check").fetchall()
    assert not fk, f"foreign_key_check: {fk}"


@check("referenced files exist")
def _():
    text = "\n".join((ROOT / f).read_text(encoding="utf-8")
                     for f in ["README.md", "PLAN.md", "agent/AGENTS.md", "agent/START-M0.md"])
    refs = set(re.findall(r"`((?:contracts|docs|agent|tools|examples)/[^`\s]*|[\w-]+\.(?:txt|json|md))`", text))
    refs.discard("validation-report.json")  # produced by this script
    missing = sorted(r for r in refs if not (ROOT / r.rstrip("/")).exists())
    assert not missing, f"missing: {missing}"
    return f"{len(refs)} references"


@check("JSON schemas are valid draft 2020-12")
def _():
    for rel in ["contracts/content-entry.schema.json", "contracts/review-event.schema.json"]:
        Draft202012Validator.check_schema(load_json(rel))


@check("content examples match schema and are internally consistent")
def _():
    v = Draft202012Validator(load_json("contracts/content-entry.schema.json"))
    for name, doc in content_examples():
        errors = [f"{name}:{'/'.join(map(str, e.path))}: {e.message}" for e in v.iter_errors(doc)]
        assert not errors, errors
        sense_ids = {s["id"] for s in doc["senses"]}
        usage_ids = {u["id"] for u in doc.get("usages", [])}
        target_ids = {t["id"] for t in doc["targets"]}
        for t in doc["targets"]:
            assert t.get("sense_id") is None or t["sense_id"] in sense_ids, f"{name}: target sense"
            assert t.get("usage_id") is None or t["usage_id"] in usage_ids, f"{name}: target usage"
        for q in doc["questions"]:
            assert q["primary_target_id"] in target_ids, f"{name}: question target"
            choices = q["body"].get("choices", [])
            for i in q["answers"].get("correct_choice_indexes", []):
                assert i < len(choices), f"{name}: answer index out of range"
            if q["response_mode"] == "recognition":
                assert choices and "correct_choice_indexes" in q["answers"], f"{name}: recognition needs choices"
        dictionary_families = {ex["family_id"] for s in doc["senses"] for ex in s["examples"]
                               if ex["exposure_role"] == "dictionary"}
        for q in doc["questions"]:
            if q["exposure_role"] == "check":
                assert q["family_id"] not in dictionary_families, f"{name}: check family shown in dictionary"
    return f"{len(content_examples())} entries"


@check("event examples match schema")
def _():
    v = Draft202012Validator(load_json("contracts/review-event.schema.json"))
    for i, ev in enumerate(event_examples(), 1):
        errors = [f"line {i}:{'/'.join(map(str, e.path))}: {e.message}" for e in v.iter_errors(ev)]
        assert not errors, errors
    # Negative case: assisted answer must not carry a Good rating.
    bad = next(e for e in event_examples() if e["kind"] == "answer" and e["payload"]["assistance"] != "none")
    bad = json.loads(json.dumps(bad))
    bad["payload"]["fsrs_rating"] = 3
    assert not v.is_valid(bad), "assisted answer with fsrs_rating=3 was accepted"


@check("content.sql loads examples, FK/integrity/FTS ok")
def _():
    db = open_db("contracts/content.sql")
    db.execute("INSERT INTO source VALUES ('project-editorial','Project editorial','v1','planning/v1','proprietary',NULL,'pending','{}')")
    db.execute("BEGIN")
    for _, d in content_examples():
        e = d["entry"]
        db.execute("INSERT INTO entry VALUES (?,?,?,?,?,?,?)",
                   (e["id"], e["kind"], e["headword"], e["normalized_key"],
                    json.dumps(e.get("pronunciation", [])), e["content_revision"], e["status"]))
        for a in e.get("aliases", []):
            db.execute("INSERT INTO entry_alias VALUES (?,?,?)", (e["id"], a["normalized_alias"], a["alias_kind"]))
        for s in d["senses"]:
            db.execute("INSERT INTO sense VALUES (?,?,?,?,?,?,?,?,?)",
                       (s["id"], e["id"], s["part_of_speech"], s["definition_zh"], s.get("definition_en"),
                        s["editorial_tier"], s["display_order"], s["content_revision"], s["status"]))
            for ex in s["examples"]:
                db.execute("INSERT INTO example VALUES (?,?,?,?,?,?,?)",
                           (ex["id"], s["id"], ex["sentence_en"], ex.get("translation_zh"),
                            ex["family_id"], ex["exposure_role"], ex["content_revision"]))
        for u in d.get("usages", []):
            db.execute("INSERT INTO usage_pattern VALUES (?,?,?,?,?,?,?,?)",
                       (u["id"], e["id"], u.get("sense_id"), u["pattern_text"], u["explanation_zh"],
                        json.dumps(u.get("structure", {})), u["editorial_tier"], u["content_revision"]))
        for t in d["targets"]:
            db.execute("INSERT INTO learning_target VALUES (?,?,?,?,?,?,?,?,?)",
                       (t["id"], e["id"], t.get("sense_id"), t.get("usage_id"), t["kind"], t["editorial_tier"],
                        json.dumps(t["response_modes"]), int(t["learning_ready"]), t["content_revision"]))
        for q in d["questions"]:
            db.execute("INSERT INTO question VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (q["id"], q["revision"], q["primary_target_id"], q["family_id"], q["format"],
                        q["response_mode"], q["exposure_role"], q.get("group_id"), q["status"],
                        json.dumps(q["body"], ensure_ascii=False), json.dumps(q["answers"]),
                        q["explanation_zh"], q["editorial_difficulty"]))
        for p in d["provenance"]:
            db.execute("INSERT INTO provenance_artifact VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                       (p["id"], p["entity_type"], p["entity_id"], p["entity_revision"], p["field_path"],
                        p["value_sha256"], p["source_id"], p.get("source_record_id"), p["derivation"],
                        json.dumps(p.get("process", {})), p["review_status"], "2026-10-04T00:00:00.000Z"))
        aliases = " ".join(a["normalized_alias"] for a in e.get("aliases", []))
        defs = " ".join(s["definition_zh"] for s in d["senses"])
        db.execute("INSERT INTO entry_search VALUES (?,?,?,?)", (e["id"], e["headword"], aliases, defs))
    db.execute("COMMIT")
    assert_db_clean(db)
    hit = db.execute("SELECT entry_id FROM entry_search WHERE entry_search MATCH 'accounted'").fetchall()
    assert len(hit) == 1, f"FTS alias lookup returned {hit}"
    prefix = db.execute("SELECT count(*) FROM entry_search WHERE entry_search MATCH 'intel*'").fetchone()[0]
    assert prefix == 1, "FTS prefix lookup failed"


def seeded_user_db():
    db = open_db("contracts/user.sql")
    evs = event_examples()
    prof, dev = evs[0]["profile_id"], evs[0]["device_id"]
    db.execute("INSERT INTO local_profile VALUES (?,?,?,?,?,?)",
               (prof, "2026-10-05T11:00:00.000Z", 900, 4, "Asia/Taipei", "{}"))
    db.execute("INSERT INTO device (id, profile_id) VALUES (?,?)", (dev, prof))
    return db, evs, prof, dev


def insert_presentation(db, pid, prof, ev):
    db.execute("""INSERT INTO presentation (id, profile_id, target_id, response_mode, question_id,
                  question_revision, content_pack_version, status, presented_at_utc, snapshot_json)
                  VALUES (?,?,?,?,?,?,?,?,?,?)""",
               (pid, prof, ev["target_id"], ev["response_mode"], ev["question_id"], ev["question_revision"],
                ev["content_pack_version"], "open", ev["occurred_at_utc"], "{}"))


def insert_event(db, ev):
    db.execute("""INSERT INTO learning_event (id, profile_id, device_id, device_sequence, kind, presentation_id,
                  entry_id, target_id, response_mode, question_id, question_revision, occurred_at_utc,
                  timezone_id, study_day, schema_version, policy_version, content_pack_version, payload_json)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (ev["id"], ev["profile_id"], ev["device_id"], ev["device_sequence"], ev["kind"],
                ev.get("presentation_id"), ev.get("entry_id"), ev.get("target_id"), ev.get("response_mode"),
                ev.get("question_id"), ev.get("question_revision"), ev["occurred_at_utc"], ev["timezone_id"],
                ev["study_day"], ev["schema_version"], ev["policy_version"], ev["content_pack_version"],
                json.dumps(ev["payload"])))


@check("user.sql loads event examples, FK/integrity ok")
def _():
    db, evs, prof, _ = seeded_user_db()
    for ev in evs:
        if ev.get("presentation_id"):
            insert_presentation(db, ev["presentation_id"], prof, ev)
        insert_event(db, ev)
    assert_db_clean(db)
    return f"{len(evs)} events"


@check("user.sql guards: one answer per presentation, required answer fields, timestamp format")
def _():
    db, evs, prof, _ = seeded_user_db()
    ans = next(e for e in evs if e["kind"] == "answer")
    insert_presentation(db, ans["presentation_id"], prof, ans)
    insert_event(db, ans)
    dup = {**ans, "id": "00000000-0000-4000-8000-000000000001", "device_sequence": 99}
    try:
        insert_event(db, dup)
        raise AssertionError("second answer for same presentation accepted")
    except sqlite3.IntegrityError:
        pass
    seq_clash = {**ans, "id": "00000000-0000-4000-8000-000000000002", "kind": "exposure", "presentation_id": None}
    try:
        insert_event(db, seq_clash)
        raise AssertionError("duplicate (device_id, device_sequence) accepted")
    except sqlite3.IntegrityError:
        pass
    missing = {**ans, "id": "00000000-0000-4000-8000-000000000003", "device_sequence": 100,
               "presentation_id": None, "entry_id": None}
    try:
        insert_event(db, missing)
        raise AssertionError("answer without entry_id/presentation_id accepted")
    except sqlite3.IntegrityError:
        pass
    bad_ts = {**ans, "id": "00000000-0000-4000-8000-000000000004", "device_sequence": 101, "kind": "exposure",
              "presentation_id": None, "occurred_at_utc": "2026-10-06 10:30:00"}
    try:
        insert_event(db, bad_ts)
        raise AssertionError("non-canonical occurred_at_utc accepted")
    except sqlite3.IntegrityError:
        pass


@check("user.sql answer transaction is atomic")
def _():
    db, evs, prof, _ = seeded_user_db()
    ans = next(e for e in evs if e["kind"] == "answer")
    insert_presentation(db, ans["presentation_id"], prof, ans)
    db.execute("BEGIN")
    try:
        insert_event(db, ans)
        db.execute("UPDATE presentation SET status='submitted' WHERE id=?", (ans["presentation_id"],))
        # Projection write fails (invalid evidence_status) -> whole submit must roll back.
        db.execute("""INSERT INTO memory_projection VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                   (prof, ans["target_id"], "recognition", "{}", "mastered", "{}", None, ans["id"],
                    "fsrs-6", "pilot-0", ans["occurred_at_utc"]))
        db.execute("COMMIT")
        raise AssertionError("invalid projection accepted")
    except sqlite3.IntegrityError:
        db.execute("ROLLBACK")
    assert db.execute("SELECT count(*) FROM learning_event").fetchone()[0] == 0, "event survived rollback"
    assert db.execute("SELECT status FROM presentation").fetchone()[0] == "open", "presentation survived rollback"


@check("policy invariants")
def _():
    p = load_json("contracts/policy-v1.json")
    m, ev, it, pl = p["memory"], p["evidence"], p["interaction"], p["planner"]
    assert m["algorithm"] == "FSRS-6"
    assert m["ratings"] == {"correct_unaided": 3, "incorrect_unaided": 1}, "only Again/Good allowed"
    assert 0 < m["desired_retention"] < 1
    assert m["use_latency_for_rating"] is False and m["fit_individual_weights_in_v1"] is False
    assert m["delayed_min_seconds"] >= 86400
    assert ev["lookup_alone_changes_grade"] is False and ev["self_rating_enabled"] is False
    assert ev["stable"]["delayed_successes"] >= ev["foundation"]["delayed_successes"]
    assert ev["foundation"]["unaided_successes"] >= ev["foundation"]["delayed_successes"]
    assert it["case_sensitive_grading"] is False and it["automatic_enrollment"] is False
    assert 0 <= it["ordinary_typing_max"] <= it["typing_window"]
    assert 0 < p["cost"]["planning_quantile"] < 1
    assert 0 < pl["high_risk_retrievability_threshold"] < 1
    assert pl["min_horizon_days"] <= pl["max_detailed_horizon_days"]
    assert pl["parallel_exam_budgets"] is False and pl["scope_reduction_changes_scoring"] is False
    assert pl["automatic_budget_increase"] is False


@check("task DAG is well formed and matches roadmap doc")
def _():
    tasks = load_json("contracts/tasks.json")
    ids = [t["id"] for t in tasks]
    assert len(ids) == len(set(ids)), "duplicate task IDs"
    by_id = {t["id"]: t for t in tasks}
    for t in tasks:
        for d in t["depends_on"]:
            assert d in by_id, f"{t['id']} depends on unknown {d}"
            assert by_id[d]["milestone"] <= t["milestone"], f"{t['id']} depends on later milestone {d}"
    state: dict[str, int] = {}

    def visit(n: str):
        if state.get(n) == 1:
            raise AssertionError(f"cycle at {n}")
        if state.get(n) == 2:
            return
        state[n] = 1
        for d in by_id[n]["depends_on"]:
            visit(d)
        state[n] = 2
    for n in ids:
        visit(n)
    doc_ids = re.findall(r"^### (T\d{3}) ", (ROOT / "docs/07-roadmap-tasks.md").read_text(encoding="utf-8"), re.M)
    assert doc_ids == ids, "docs/07 task list differs from contracts/tasks.json"
    return f"{len(ids)} tasks"


@check("every [Sxx] citation resolves in sources.json")
def _():
    known = {s["id"] for s in load_json("contracts/sources.json")}
    cited: set[str] = set()
    for f in [ROOT / "PLAN.md", ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]:
        cited |= set(re.findall(r"\[(S\d{2})\]", f.read_text(encoding="utf-8")))
    unknown = sorted(cited - known)
    assert not unknown, f"unknown citations: {unknown}"
    return f"{len(cited)} cited / {len(known)} registered"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    report = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "sqlite": sqlite3.sqlite_version,
        "passed": all(r["ok"] for r in results),
        "checks": results,
        "not_covered": ["Swift build", "FSRS numeric conformance", "device performance"],
    }
    for r in results:
        print(("PASS " if r["ok"] else "FAIL ") + r["check"] + (f" — {r['detail']}" if r["detail"] else ""))
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
