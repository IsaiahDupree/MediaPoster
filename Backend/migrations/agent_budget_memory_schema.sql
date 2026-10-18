-- Agent Budget and Memory Tables
-- ================================
-- Tracks API usage/costs per agent and stores agent learnings

-- Budget tracking table
CREATE TABLE IF NOT EXISTS agent_budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    api_calls_today INTEGER DEFAULT 0,
    api_calls_limit INTEGER DEFAULT 100,
    tokens_used INTEGER DEFAULT 0,
    tokens_limit INTEGER DEFAULT 500000,
    cost_today DECIMAL(10,4) DEFAULT 0.0,
    cost_limit DECIMAL(10,2) DEFAULT 5.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_type, date)
);

-- Index for daily lookups
CREATE INDEX IF NOT EXISTS idx_agent_budgets_date ON agent_budgets(date);
CREATE INDEX IF NOT EXISTS idx_agent_budgets_agent_date ON agent_budgets(agent_type, date);

-- Agent memory/learnings table
CREATE TABLE IF NOT EXISTS agent_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,
    learning TEXT NOT NULL,
    context TEXT DEFAULT '',
    relevance_score DECIMAL(5,4) DEFAULT 0.5,
    embedding vector(1536),  -- For semantic search if pgvector is available
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for memory queries
CREATE INDEX IF NOT EXISTS idx_agent_memories_agent ON agent_memories(agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_memories_relevance ON agent_memories(relevance_score DESC);
CREATE INDEX IF NOT EXISTS idx_agent_memories_created ON agent_memories(created_at DESC);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to budgets
DROP TRIGGER IF EXISTS update_agent_budgets_updated_at ON agent_budgets;
CREATE TRIGGER update_agent_budgets_updated_at
    BEFORE UPDATE ON agent_budgets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to memories
DROP TRIGGER IF EXISTS update_agent_memories_updated_at ON agent_memories;
CREATE TRIGGER update_agent_memories_updated_at
    BEFORE UPDATE ON agent_memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default budget limits for each agent type
INSERT INTO agent_budgets (agent_type, date, api_calls_limit, tokens_limit, cost_limit)
VALUES 
    ('narrative', CURRENT_DATE, 100, 500000, 5.0),
    ('experiments', CURRENT_DATE, 50, 250000, 2.5),
    ('content_mix', CURRENT_DATE, 100, 500000, 5.0)
ON CONFLICT (agent_type, date) DO NOTHING;
