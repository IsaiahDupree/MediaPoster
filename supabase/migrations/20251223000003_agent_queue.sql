-- Agent Queue Table for Job Processing
-- Simple DB-backed queue (can swap to pgmq later)

CREATE TABLE IF NOT EXISTS agent_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID,

  topic TEXT NOT NULL,
  run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,

  status TEXT NOT NULL DEFAULT 'queued', -- queued|processing|done|failed
  attempts INT NOT NULL DEFAULT 0,

  available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  locked_at TIMESTAMPTZ,
  locked_by TEXT,
  last_error TEXT,

  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient queue processing
CREATE INDEX IF NOT EXISTS idx_agent_queue_available
  ON agent_queue (status, available_at);

CREATE INDEX IF NOT EXISTS idx_agent_queue_topic
  ON agent_queue (topic, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_queue_run
  ON agent_queue (run_id);

-- Function to claim next available job
CREATE OR REPLACE FUNCTION claim_queue_job(worker_id TEXT, batch_size INT DEFAULT 1)
RETURNS SETOF agent_queue
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  WITH claimed AS (
    SELECT id FROM agent_queue
    WHERE status = 'queued'
      AND available_at <= NOW()
    ORDER BY created_at ASC
    LIMIT batch_size
    FOR UPDATE SKIP LOCKED
  )
  UPDATE agent_queue q
  SET status = 'processing',
      locked_at = NOW(),
      locked_by = worker_id,
      attempts = attempts + 1
  FROM claimed c
  WHERE q.id = c.id
  RETURNING q.*;
END $$;

-- Function to complete a job
CREATE OR REPLACE FUNCTION complete_queue_job(job_id UUID, success BOOLEAN, error_msg TEXT DEFAULT NULL)
RETURNS VOID
LANGUAGE plpgsql AS $$
BEGIN
  UPDATE agent_queue
  SET status = CASE WHEN success THEN 'done' ELSE 'failed' END,
      last_error = error_msg
  WHERE id = job_id;
END $$;

-- Function to retry failed jobs
CREATE OR REPLACE FUNCTION retry_failed_jobs(max_attempts INT DEFAULT 3)
RETURNS INT
LANGUAGE plpgsql AS $$
DECLARE
  retried INT;
BEGIN
  WITH updated AS (
    UPDATE agent_queue
    SET status = 'queued',
        available_at = NOW() + (attempts * INTERVAL '1 minute'),
        locked_at = NULL,
        locked_by = NULL
    WHERE status = 'failed'
      AND attempts < max_attempts
    RETURNING 1
  )
  SELECT COUNT(*) INTO retried FROM updated;
  RETURN retried;
END $$;

COMMENT ON TABLE agent_queue IS 'Job queue for agent task processing';
COMMENT ON COLUMN agent_queue.status IS 'Job status: queued, processing, done, failed';
COMMENT ON COLUMN agent_queue.attempts IS 'Number of processing attempts';
