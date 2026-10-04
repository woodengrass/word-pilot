-- Reference draft (not a binding schema; see docs/02). Not an applied production migration.
-- Cross-references from user.sqlite are checked by the application/content validator.
PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;

CREATE TABLE pack_metadata (
    key TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL
);
CREATE TABLE source (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    source_version TEXT NOT NULL,
    locator TEXT NOT NULL,
    license_id TEXT NOT NULL,
    license_text_sha256 TEXT,
    rights_status TEXT NOT NULL CHECK(rights_status IN ('approved','approved_with_conditions','pending','excluded')),
    conditions_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(conditions_json))
);
CREATE TABLE entry (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id) = 36),
    kind TEXT NOT NULL CHECK(kind IN ('word','phrase')),
    headword TEXT NOT NULL CHECK(length(trim(headword)) > 0),
    normalized_key TEXT NOT NULL,
    pronunciation_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(pronunciation_json)),
    content_revision INTEGER NOT NULL CHECK(content_revision > 0),
    status TEXT NOT NULL CHECK(status IN ('draft','reviewed','published','retired')),
    UNIQUE(kind, normalized_key)
);
CREATE TABLE entry_alias (
    entry_id TEXT NOT NULL REFERENCES entry(id),
    normalized_alias TEXT NOT NULL,
    alias_kind TEXT NOT NULL CHECK(alias_kind IN ('inflection','variant','search')),
    PRIMARY KEY(entry_id, normalized_alias, alias_kind)
);
CREATE INDEX entry_alias_lookup ON entry_alias(normalized_alias);

CREATE TABLE sense (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id) = 36),
    entry_id TEXT NOT NULL REFERENCES entry(id),
    part_of_speech TEXT NOT NULL,
    definition_zh TEXT NOT NULL,
    definition_en TEXT,
    editorial_tier TEXT NOT NULL CHECK(editorial_tier IN ('core','important','extended')),
    display_order INTEGER NOT NULL CHECK(display_order >= 0),
    content_revision INTEGER NOT NULL CHECK(content_revision > 0),
    status TEXT NOT NULL CHECK(status IN ('draft','reviewed','published','retired'))
);
CREATE INDEX sense_entry ON sense(entry_id,display_order);

CREATE TABLE example (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id) = 36),
    sense_id TEXT NOT NULL REFERENCES sense(id),
    sentence_en TEXT NOT NULL,
    translation_zh TEXT,
    family_id TEXT NOT NULL,
    exposure_role TEXT NOT NULL CHECK(exposure_role IN ('dictionary','teaching','check_only')),
    content_revision INTEGER NOT NULL CHECK(content_revision > 0)
);
CREATE TABLE usage_pattern (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id) = 36),
    entry_id TEXT NOT NULL REFERENCES entry(id),
    sense_id TEXT REFERENCES sense(id),
    pattern_text TEXT NOT NULL,
    explanation_zh TEXT NOT NULL,
    structure_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(structure_json)),
    editorial_tier TEXT NOT NULL CHECK(editorial_tier IN ('core','important','extended')),
    content_revision INTEGER NOT NULL CHECK(content_revision > 0)
);
CREATE TABLE learning_target (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id) = 36),
    entry_id TEXT NOT NULL REFERENCES entry(id),
    sense_id TEXT REFERENCES sense(id),
    usage_id TEXT REFERENCES usage_pattern(id),
    kind TEXT NOT NULL CHECK(kind IN ('sense_comprehension','usage_pattern','phrase_comprehension','phrase_slot','word_form')),
    editorial_tier TEXT NOT NULL CHECK(editorial_tier IN ('core','important','extended')),
    response_modes_json TEXT NOT NULL CHECK(json_valid(response_modes_json)),
    learning_ready INTEGER NOT NULL DEFAULT 0 CHECK(learning_ready IN (0,1)),
    content_revision INTEGER NOT NULL CHECK(content_revision > 0)
);
CREATE INDEX target_entry ON learning_target(entry_id);
CREATE TABLE question (
    id TEXT NOT NULL CHECK(length(id) = 36),
    revision INTEGER NOT NULL CHECK(revision > 0),
    primary_target_id TEXT NOT NULL REFERENCES learning_target(id),
    family_id TEXT NOT NULL,
    format TEXT NOT NULL CHECK(format IN ('meaning_choice','reverse_choice','context_cloze','collocation_choice','sense_choice','phrase_slot','typed_recall','exact_form','passage_item')),
    response_mode TEXT NOT NULL CHECK(response_mode IN ('recognition','cued_recall','exact_form')),
    exposure_role TEXT NOT NULL CHECK(exposure_role IN ('train','check')),
    group_id TEXT,
    status TEXT NOT NULL CHECK(status IN ('draft','reviewed','published','quarantined','retired')),
    body_json TEXT NOT NULL CHECK(json_valid(body_json)),
    answers_json TEXT NOT NULL CHECK(json_valid(answers_json)),
    explanation_zh TEXT NOT NULL,
    editorial_difficulty TEXT NOT NULL CHECK(editorial_difficulty IN ('introductory','standard','challenging')),
    PRIMARY KEY(id,revision)
);
CREATE INDEX question_candidates ON question(primary_target_id,response_mode,status,exposure_role);
CREATE INDEX question_family ON question(family_id);

CREATE TABLE provenance_artifact (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id) = 36),
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_revision INTEGER NOT NULL CHECK(entity_revision > 0),
    field_path TEXT NOT NULL,
    value_sha256 TEXT NOT NULL CHECK(length(value_sha256) = 64),
    source_id TEXT NOT NULL REFERENCES source(id),
    source_record_id TEXT,
    derivation TEXT NOT NULL CHECK(derivation IN ('direct','adapted','generated','editorial')),
    process_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(process_json)),
    review_status TEXT NOT NULL CHECK(review_status IN ('pending','approved','disputed','rejected')),
    created_at_utc TEXT NOT NULL
);
CREATE INDEX provenance_entity ON provenance_artifact(entity_type,entity_id,field_path);
CREATE TABLE provenance_dependency (
    artifact_id TEXT NOT NULL REFERENCES provenance_artifact(id),
    input_artifact_id TEXT NOT NULL REFERENCES provenance_artifact(id),
    PRIMARY KEY(artifact_id,input_artifact_id),
    CHECK(artifact_id != input_artifact_id)
);
CREATE TABLE content_mapping (
    old_entity_id TEXT NOT NULL,
    new_entity_id TEXT NOT NULL,
    mapping_kind TEXT NOT NULL CHECK(mapping_kind IN ('equivalent','split','merge','retired','provider_alias')),
    evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json)),
    PRIMARY KEY(old_entity_id,new_entity_id,mapping_kind)
);
CREATE VIRTUAL TABLE entry_search USING fts5(
    entry_id UNINDEXED, headword, aliases, definitions,
    tokenize = 'unicode61'
);
