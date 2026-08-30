BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS source_policy (
    source_key text PRIMARY KEY,
    access_mode text NOT NULL CHECK (access_mode IN ('allow','partner_only','user_share_only','deny')),
    reason text NOT NULL,
    policy_url text,
    robots_required boolean NOT NULL DEFAULT true,
    reviewed_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS source_observation (
    id uuid PRIMARY KEY,
    source_key text NOT NULL REFERENCES source_policy(source_key),
    source_url text NOT NULL,
    observed_at timestamptz NOT NULL,
    content_hash text NOT NULL,
    adapter text,
    http_status integer,
    extracted jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_source_observation_source_time
    ON source_observation (source_key, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_source_observation_hash
    ON source_observation (source_key, content_hash);

-- Current state is updated only when the incoming observation is newer.
CREATE TABLE IF NOT EXISTS source_state (
    source_key text PRIMARY KEY REFERENCES source_policy(source_key),
    observation_id uuid NOT NULL REFERENCES source_observation(id),
    last_observed_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION promote_source_state(
    p_source_key text,
    p_observation_id uuid,
    p_observed_at timestamptz
) RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    affected integer;
BEGIN
    INSERT INTO source_state(source_key, observation_id, last_observed_at)
    VALUES (p_source_key, p_observation_id, p_observed_at)
    ON CONFLICT (source_key) DO UPDATE
      SET observation_id = EXCLUDED.observation_id,
          last_observed_at = EXCLUDED.last_observed_at,
          updated_at = now()
      WHERE EXCLUDED.last_observed_at > source_state.last_observed_at;

    GET DIAGNOSTICS affected = ROW_COUNT;
    RETURN affected = 1;
END;
$$;

CREATE TABLE IF NOT EXISTS canonical_entity (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    normalized_name text NOT NULL,
    category text,
    address text,
    location geography(Point, 4326),
    external_ids jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_canonical_entity_name ON canonical_entity (normalized_name);
CREATE INDEX IF NOT EXISTS idx_canonical_entity_location ON canonical_entity USING gist (location);
CREATE INDEX IF NOT EXISTS idx_canonical_entity_external_ids ON canonical_entity USING gin (external_ids);

CREATE TABLE IF NOT EXISTS discovery (
    id uuid PRIMARY KEY,
    discovery_type text NOT NULL CHECK (discovery_type IN ('deal','opening','event','price_drop','new_product','new_menu','happy_hour','trending')),
    entity_id uuid REFERENCES canonical_entity(id),
    source_key text NOT NULL REFERENCES source_policy(source_key),
    source_url text NOT NULL,
    title text NOT NULL,
    observed_at timestamptz NOT NULL,
    starts_at timestamptz,
    expires_at timestamptz,
    original_price numeric,
    current_price numeric,
    currency text,
    freshness_state text NOT NULL CHECK (freshness_state IN ('verified_live','likely_live','unverified','expired')),
    embedding vector,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (expires_at IS NULL OR freshness_state = 'expired' OR expires_at > observed_at)
);

CREATE INDEX IF NOT EXISTS idx_discovery_entity ON discovery (entity_id);
CREATE INDEX IF NOT EXISTS idx_discovery_source_time ON discovery (source_key, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_discovery_expiry ON discovery (expires_at) WHERE expires_at IS NOT NULL;

CREATE TABLE IF NOT EXISTS discovery_evidence (
    id bigserial PRIMARY KEY,
    discovery_id uuid NOT NULL REFERENCES discovery(id) ON DELETE CASCADE,
    source_observation_id uuid NOT NULL REFERENCES source_observation(id),
    field_name text NOT NULL,
    raw_value text NOT NULL,
    confidence double precision NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    observed_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_discovery_evidence_discovery ON discovery_evidence(discovery_id);
CREATE INDEX IF NOT EXISTS idx_discovery_evidence_observation ON discovery_evidence(source_observation_id);

COMMIT;
