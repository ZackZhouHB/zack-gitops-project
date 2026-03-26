-- PostgreSQL schema for the Teacher Accreditation Agent
-- Auto-runs on first container start via Docker entrypoint

-- Conversations: track each chat session
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY,
    trace_id UUID UNIQUE NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    total_tokens INT DEFAULT 0,
    total_tool_calls INT DEFAULT 0,
    workflow_type TEXT,
    final_status TEXT DEFAULT 'in_progress'
);

-- Tool call log: every tool invocation with timing and results
CREATE TABLE IF NOT EXISTS tool_call_log (
    id SERIAL PRIMARY KEY,
    trace_id UUID REFERENCES conversations(trace_id),
    step_number INT,
    tool_name TEXT NOT NULL,
    input_params JSONB,
    output_result JSONB,
    latency_ms INT,
    tokens_used INT DEFAULT 0,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Workflow state: persist multi-step workflow progress
CREATE TABLE IF NOT EXISTS workflow_state (
    id SERIAL PRIMARY KEY,
    trace_id UUID REFERENCES conversations(trace_id),
    workflow_type TEXT NOT NULL,
    current_step INT DEFAULT 0,
    state_data JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Escalation queue: human handoff tracking
CREATE TABLE IF NOT EXISTS escalation_queue (
    id SERIAL PRIMARY KEY,
    trace_id UUID REFERENCES conversations(trace_id),
    reason TEXT NOT NULL,
    context_summary TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    acknowledged_at TIMESTAMP
);

-- Checklists: tracked requirements checklists
CREATE TABLE IF NOT EXISTS checklists (
    id UUID PRIMARY KEY,
    trace_id UUID REFERENCES conversations(trace_id),
    title TEXT NOT NULL,
    checklist_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Checklist items: individual items within a checklist
CREATE TABLE IF NOT EXISTS checklist_items (
    id SERIAL PRIMARY KEY,
    checklist_id UUID REFERENCES checklists(id),
    description TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    notes TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);
