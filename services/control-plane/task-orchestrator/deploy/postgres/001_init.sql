CREATE TABLE IF NOT EXISTS embedding_tasks (
    task_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(128) NOT NULL,
    task_type VARCHAR(64) NOT NULL DEFAULT 'embedding_batch',
    modality VARCHAR(32) NOT NULL DEFAULT 'text',
    model VARCHAR(128) NOT NULL,
    source_payload JSONB NOT NULL,
    callback_url TEXT NULL,
    status VARCHAR(32) NOT NULL,
    progress DOUBLE PRECISION NOT NULL DEFAULT 0,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    error_code VARCHAR(64) NULL,
    error_message TEXT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_embedding_tasks_tenant_status
    ON embedding_tasks (tenant_id, status);

CREATE INDEX IF NOT EXISTS idx_embedding_tasks_updated_at
    ON embedding_tasks (updated_at DESC);

CREATE TABLE IF NOT EXISTS embedding_task_state_history (
    id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,
    from_status VARCHAR(32) NULL,
    to_status VARCHAR(32) NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    progress DOUBLE PRECISION NOT NULL DEFAULT 0,
    error_code VARCHAR(64) NULL,
    error_message TEXT NULL,
    operator VARCHAR(64) NOT NULL DEFAULT 'system',
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_embedding_task_state_history_task
        FOREIGN KEY (task_id) REFERENCES embedding_tasks (task_id)
);

CREATE INDEX IF NOT EXISTS idx_embedding_task_state_history_task_changed
    ON embedding_task_state_history (task_id, changed_at DESC);
