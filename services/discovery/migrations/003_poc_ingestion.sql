BEGIN;

CREATE TABLE IF NOT EXISTS ingestion_run (
    id uuid PRIMARY KEY,
    policy_scope text NOT NULL CHECK (policy_scope IN ('research','poc','production')),
    started_at timestamptz NOT NULL,
    completed_at timestamptz,
    status text NOT NULL CHECK (status IN ('running','completed','partial','failed')),
    source_count integer NOT NULL DEFAULT 0 CHECK (source_count >= 0),
    blocked_count integer NOT NULL DEFAULT 0 CHECK (blocked_count >= 0),
    failed_count integer NOT NULL DEFAULT 0 CHECK (failed_count >= 0),
    observation_count integer NOT NULL DEFAULT 0 CHECK (observation_count >= 0),
    candidate_count integer NOT NULL DEFAULT 0 CHECK (candidate_count >= 0),
    inserted_count integer NOT NULL DEFAULT 0 CHECK (inserted_count >= 0),
    updated_count integer NOT NULL DEFAULT 0 CHECK (updated_count >= 0),
    duplicate_count integer NOT NULL DEFAULT 0 CHECK (duplicate_count >= 0),
    expired_count integer NOT NULL DEFAULT 0 CHECK (expired_count >= 0),
    ranked_count integer NOT NULL DEFAULT 0 CHECK (ranked_count >= 0),
    metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_run_started_at
    ON ingestion_run(started_at DESC);

CREATE TABLE IF NOT EXISTS ingestion_source_result (
    id bigserial PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES ingestion_run(id) ON DELETE CASCADE,
    source_key text NOT NULL,
    source_url text,
    fetch_mode text,
    status text NOT NULL CHECK (status IN ('ok','blocked','skipped','error')),
    observed_at timestamptz,
    http_status integer,
    candidate_count integer NOT NULL DEFAULT 0 CHECK (candidate_count >= 0),
    inserted_count integer NOT NULL DEFAULT 0 CHECK (inserted_count >= 0),
    updated_count integer NOT NULL DEFAULT 0 CHECK (updated_count >= 0),
    duplicate_count integer NOT NULL DEFAULT 0 CHECK (duplicate_count >= 0),
    expired_count integer NOT NULL DEFAULT 0 CHECK (expired_count >= 0),
    error_code text,
    detail text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_source_result_run
    ON ingestion_source_result(run_id, source_key);

ALTER TABLE discovery
    ADD COLUMN IF NOT EXISTS dedupe_key text,
    ADD COLUMN IF NOT EXISTS first_seen_at timestamptz,
    ADD COLUMN IF NOT EXISTS last_seen_at timestamptz,
    ADD COLUMN IF NOT EXISTS seen_count integer NOT NULL DEFAULT 1 CHECK (seen_count > 0),
    ADD COLUMN IF NOT EXISTS last_ingestion_run_id uuid REFERENCES ingestion_run(id);

UPDATE discovery
SET first_seen_at = COALESCE(first_seen_at, observed_at),
    last_seen_at = COALESCE(last_seen_at, observed_at)
WHERE first_seen_at IS NULL OR last_seen_at IS NULL;

ALTER TABLE discovery
    ALTER COLUMN first_seen_at SET DEFAULT now(),
    ALTER COLUMN first_seen_at SET NOT NULL,
    ALTER COLUMN last_seen_at SET DEFAULT now(),
    ALTER COLUMN last_seen_at SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_discovery_dedupe_key
    ON discovery(dedupe_key)
    WHERE dedupe_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_discovery_active_rank
    ON discovery(freshness_state, last_seen_at DESC)
    WHERE freshness_state <> 'expired';

COMMIT;
