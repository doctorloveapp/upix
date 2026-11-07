-- Proposta per il backend PostgreSQL personalizzato. Non eseguita/deployata.
-- Solo il backend possiede credenziali e decide lo stato verified.
CREATE TABLE upix_runs (
    id uuid PRIMARY KEY,
    campaign_id text NOT NULL,
    manifest_hash char(64) NOT NULL,
    seed bigint NOT NULL,
    capability_hash text NOT NULL,
    status text NOT NULL CHECK (status IN ('started', 'pending', 'verified', 'rejected')),
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    input_log jsonb
);

CREATE TABLE upix_scores (
    run_id uuid PRIMARY KEY REFERENCES upix_runs(id),
    player_name varchar(32) NOT NULL,
    score bigint NOT NULL CHECK (score BETWEEN 0 AND 1000000000000),
    levels_completed integer NOT NULL CHECK (levels_completed >= 0),
    elapsed_ticks bigint NOT NULL CHECK (elapsed_ticks >= 0),
    completed boolean NOT NULL,
    verified_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX upix_runs_campaign_status ON upix_runs(campaign_id, status);
CREATE INDEX upix_scores_ranking ON upix_scores(score DESC, levels_completed DESC, elapsed_ticks ASC);
-- Query della classifica: join upix_runs, filtro status='verified' e campaign_id.
-- UNIQUE run_id e transazione di finalizzazione rendono idempotente il commit.
