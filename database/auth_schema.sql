PRAGMA foreign_keys = ON;

BEGIN;

CREATE TABLE IF NOT EXISTS accounts (
    account_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('operator', 'coordinator', 'maintainer'))
) STRICT;

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    account_id INTEGER NOT NULL
        REFERENCES accounts (account_id) ON DELETE CASCADE,
    expires_at INTEGER NOT NULL
) STRICT;

COMMIT;
