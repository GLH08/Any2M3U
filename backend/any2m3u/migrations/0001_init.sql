CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    last_login_at   TEXT
);

CREATE TABLE IF NOT EXISTS sources (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    type              TEXT NOT NULL CHECK(type IN ('webdav','local')),
    config_json       TEXT NOT NULL,
    group_by_dir      INTEGER NOT NULL DEFAULT 0,
    refresh_cron      TEXT,
    enabled           INTEGER NOT NULL DEFAULT 1,
    last_scan_at      TEXT,
    last_scan_status  TEXT,
    last_error        TEXT,
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scan_cache (
    source_id           INTEGER PRIMARY KEY REFERENCES sources(id) ON DELETE CASCADE,
    scanned_at          TEXT NOT NULL,
    entry_count         INTEGER NOT NULL,
    total_bytes         INTEGER NOT NULL,
    entries_jsonl_path  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rules (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id         INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    name              TEXT NOT NULL,
    include_exts      TEXT,
    exclude_keywords  TEXT,
    include_paths     TEXT,
    group_title       TEXT NOT NULL DEFAULT '',
    tpl               TEXT NOT NULL,
    logo_dir          TEXT NOT NULL DEFAULT '',
    enabled           INTEGER NOT NULL DEFAULT 1,
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pull_tokens (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    token         TEXT UNIQUE NOT NULL,
    created_at    TEXT NOT NULL,
    last_used_at  TEXT,
    expires_at    TEXT,
    revoked       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    id            TEXT PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at    TEXT NOT NULL,
    expires_at    TEXT NOT NULL,
    ip            TEXT
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    name TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);
