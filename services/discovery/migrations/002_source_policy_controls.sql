BEGIN;

ALTER TABLE source_policy
    ADD COLUMN IF NOT EXISTS policy_scope text NOT NULL DEFAULT 'production'
        CHECK (policy_scope IN ('research','poc','production')),
    ADD COLUMN IF NOT EXISTS allowed_path_prefixes text[] NOT NULL DEFAULT ARRAY[]::text[],
    ADD COLUMN IF NOT EXISTS max_requests_per_hour integer NOT NULL DEFAULT 1
        CHECK (max_requests_per_hour > 0 AND max_requests_per_hour <= 3600),
    ADD COLUMN IF NOT EXISTS attribution_required boolean NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS content_storage_allowed boolean NOT NULL DEFAULT false;

COMMIT;
