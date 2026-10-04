-- Local user contract v1. Events are durable; projections/caches are rebuildable.
PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;

CREATE TABLE local_profile (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id) = 36),
    created_at_utc TEXT NOT NULL,
    daily_budget_seconds INTEGER NOT NULL CHECK(daily_budget_seconds > 0),
    study_day_start_hour INTEGER NOT NULL DEFAULT 4 CHECK(study_day_start_hour BETWEEN 0 AND 23),
    timezone_id TEXT NOT NULL,
    settings_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(settings_json))
);
CREATE TABLE device (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id) = 36),
    profile_id TEXT NOT NULL REFERENCES local_profile(id),
    next_event_sequence INTEGER NOT NULL DEFAULT 1 CHECK(next_event_sequence > 0)
);
CREATE TABLE enrollment (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id) = 36),
    profile_id TEXT NOT NULL REFERENCES local_profile(id),
    entry_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active','paused','removed')),
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    deleted_at_utc TEXT,
    UNIQUE(profile_id,entry_id)
);
CREATE TABLE exam (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id) = 36),
    profile_id TEXT NOT NULL REFERENCES local_profile(id),
    title TEXT NOT NULL,
    exam_local_date TEXT NOT NULL,
    timezone_id TEXT NOT NULL,
    prepare_by_utc TEXT NOT NULL,
    writing_required INTEGER NOT NULL DEFAULT 0 CHECK(writing_required IN (0,1)),
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    deleted_at_utc TEXT
);
CREATE TABLE exam_entry (
    exam_id TEXT NOT NULL REFERENCES exam(id),
    enrollment_id TEXT NOT NULL REFERENCES enrollment(id),
    created_at_utc TEXT NOT NULL,
    deleted_at_utc TEXT,
    PRIMARY KEY(exam_id,enrollment_id)
);
CREATE TABLE import_batch (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id) = 36),
    profile_id TEXT NOT NULL REFERENCES local_profile(id),
    label TEXT NOT NULL,
    created_at_utc TEXT NOT NULL
);
CREATE TABLE import_batch_entry (
    batch_id TEXT NOT NULL REFERENCES import_batch(id),
    enrollment_id TEXT NOT NULL REFERENCES enrollment(id),
    PRIMARY KEY(batch_id,enrollment_id)
);
CREATE TABLE presentation (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id) = 36),
    profile_id TEXT NOT NULL REFERENCES local_profile(id),
    target_id TEXT NOT NULL,
    response_mode TEXT NOT NULL CHECK(response_mode IN ('recognition','cued_recall','exact_form')),
    question_id TEXT,
    question_revision INTEGER,
    family_id TEXT,
    content_pack_version TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('open','submitted','abandoned')),
    presented_at_utc TEXT NOT NULL,
    submitted_at_utc TEXT,
    choice_order_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(choice_order_json)),
    draft_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(draft_json)),
    snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json))
);
CREATE INDEX presentation_resume ON presentation(profile_id,status,presented_at_utc);

CREATE TABLE learning_event (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id) = 36),
    profile_id TEXT NOT NULL REFERENCES local_profile(id),
    device_id TEXT NOT NULL REFERENCES device(id),
    device_sequence INTEGER NOT NULL CHECK(device_sequence > 0),
    kind TEXT NOT NULL CHECK(kind IN ('answer','exposure','reanchor','invalidate','enrollment_change','exam_change','settings_change')),
    presentation_id TEXT REFERENCES presentation(id),
    target_id TEXT,
    response_mode TEXT CHECK(response_mode IN ('recognition','cued_recall','exact_form')),
    occurred_at_utc TEXT NOT NULL,
    timezone_id TEXT NOT NULL,
    study_day TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    policy_version TEXT NOT NULL,
    content_pack_version TEXT NOT NULL,
    payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
    UNIQUE(device_id,device_sequence)
);
CREATE UNIQUE INDEX one_answer_per_presentation
    ON learning_event(presentation_id) WHERE kind = 'answer';
CREATE INDEX event_replay ON learning_event(profile_id,occurred_at_utc,device_id,device_sequence);
CREATE INDEX event_target ON learning_event(profile_id,target_id,occurred_at_utc);

CREATE TABLE memory_projection (
    profile_id TEXT NOT NULL REFERENCES local_profile(id),
    target_id TEXT NOT NULL,
    response_mode TEXT NOT NULL CHECK(response_mode IN ('recognition','cued_recall','exact_form')),
    fsrs_state_json TEXT NOT NULL CHECK(json_valid(fsrs_state_json)),
    evidence_status TEXT NOT NULL CHECK(evidence_status IN ('not_started','learning','foundation_verified','stable','reinforcement_needed','suspended')),
    evidence_summary_json TEXT NOT NULL CHECK(json_valid(evidence_summary_json)),
    due_at_utc TEXT,
    last_event_id TEXT REFERENCES learning_event(id),
    algorithm_version TEXT NOT NULL,
    content_pack_version TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    PRIMARY KEY(profile_id,target_id,response_mode)
);
CREATE INDEX memory_due ON memory_projection(profile_id,due_at_utc);

CREATE TABLE study_slice (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id) = 36),
    profile_id TEXT NOT NULL REFERENCES local_profile(id),
    presentation_id TEXT REFERENCES presentation(id),
    group_id TEXT,
    phase TEXT NOT NULL CHECK(phase IN ('teaching','reading','answering','feedback')),
    started_at_utc TEXT NOT NULL,
    study_day TEXT NOT NULL,
    active_ms INTEGER NOT NULL CHECK(active_ms >= 0),
    timing_quality TEXT NOT NULL CHECK(timing_quality IN ('reliable','uncertain','excluded')),
    clock_info_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(clock_info_json))
);
CREATE INDEX study_day_time ON study_slice(profile_id,study_day);

CREATE TABLE lookup_event (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id) = 36),
    profile_id TEXT NOT NULL REFERENCES local_profile(id),
    entry_id TEXT NOT NULL,
    viewed_sense_id TEXT,
    occurred_at_utc TEXT NOT NULL,
    local_date TEXT NOT NULL,
    context_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(context_json))
);
CREATE INDEX lookup_count ON lookup_event(profile_id,entry_id,local_date);
CREATE TABLE lookup_prompt_state (
    profile_id TEXT NOT NULL REFERENCES local_profile(id),
    entry_id TEXT NOT NULL,
    dismissed_until_utc TEXT,
    last_prompted_at_utc TEXT,
    PRIMARY KEY(profile_id,entry_id)
);
CREATE TABLE item_report (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id) = 36),
    profile_id TEXT NOT NULL REFERENCES local_profile(id),
    question_id TEXT NOT NULL,
    question_revision INTEGER NOT NULL,
    presentation_id TEXT REFERENCES presentation(id),
    reason_code TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    resolved_at_utc TEXT
);
CREATE TABLE learner_cost_profile (
    profile_id TEXT NOT NULL REFERENCES local_profile(id),
    bucket_key TEXT NOT NULL,
    sample_count INTEGER NOT NULL CHECK(sample_count >= 0),
    model_version TEXT NOT NULL,
    summary_json TEXT NOT NULL CHECK(json_valid(summary_json)),
    updated_at_utc TEXT NOT NULL,
    PRIMARY KEY(profile_id,bucket_key)
);
CREATE TABLE planner_cache (
    profile_id TEXT NOT NULL REFERENCES local_profile(id),
    study_day TEXT NOT NULL,
    input_fingerprint TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    plan_json TEXT NOT NULL CHECK(json_valid(plan_json)),
    generated_at_utc TEXT NOT NULL,
    PRIMARY KEY(profile_id,study_day)
);
