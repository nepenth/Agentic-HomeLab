-- Email Synchronization and Intelligence System Schema
-- This creates the foundation for local email storage, embeddings, and task generation

-- Email accounts (user's configured email providers)
CREATE TABLE email_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_type VARCHAR(50) NOT NULL, -- 'gmail', 'outlook', 'imap', 'exchange'
    email_address VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),

    -- Authentication (encrypted)
    auth_type VARCHAR(50) NOT NULL, -- 'oauth2', 'password', 'app_password'
    auth_credentials JSONB NOT NULL, -- encrypted credentials

    -- Sync configuration
    sync_settings JSONB DEFAULT '{}', -- folders, date ranges, filters
    sync_interval_minutes INTEGER DEFAULT 15,
    auto_sync_enabled BOOLEAN DEFAULT true,

    -- Sync status
    last_sync_at TIMESTAMP WITH TIME ZONE,
    next_sync_at TIMESTAMP WITH TIME ZONE,
    sync_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'syncing', 'success', 'error'
    last_error TEXT,
    total_emails_synced INTEGER DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, email_address)
);

-- Email storage (actual email content)
CREATE TABLE emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES email_accounts(id) ON DELETE CASCADE,

    -- Email identifiers
    message_id VARCHAR(255) NOT NULL, -- From email headers
    thread_id VARCHAR(255),
    in_reply_to VARCHAR(255),

    -- Content
    subject TEXT,
    body_text TEXT,
    body_html TEXT,
    snippet TEXT, -- First 200 chars for preview

    -- Participants
    sender_email VARCHAR(255),
    sender_name VARCHAR(255),
    reply_to_email VARCHAR(255),
    to_recipients JSONB DEFAULT '[]', -- Array of {email, name}
    cc_recipients JSONB DEFAULT '[]',
    bcc_recipients JSONB DEFAULT '[]',

    -- Timestamps
    sent_at TIMESTAMP WITH TIME ZONE,
    received_at TIMESTAMP WITH TIME ZONE,

    -- Classification
    importance_score FLOAT DEFAULT 0.5, -- 0.0 to 1.0
    urgency_score FLOAT DEFAULT 0.5,
    category VARCHAR(100), -- 'work', 'personal', 'finance', 'travel', etc.
    labels JSONB DEFAULT '[]', -- Array of label strings

    -- Email metadata
    folder_path VARCHAR(500), -- INBOX, Sent, etc.
    size_bytes INTEGER,
    has_attachments BOOLEAN DEFAULT false,
    attachment_count INTEGER DEFAULT 0,

    -- Status flags
    is_read BOOLEAN DEFAULT false,
    is_flagged BOOLEAN DEFAULT false,
    is_important BOOLEAN DEFAULT false,
    is_spam BOOLEAN DEFAULT false,
    is_deleted BOOLEAN DEFAULT false,

    -- Processing status
    embeddings_generated BOOLEAN DEFAULT false,
    tasks_generated BOOLEAN DEFAULT false,
    last_processed_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(account_id, message_id)
);

-- Email embeddings (for semantic search)
CREATE TABLE email_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,

    -- Embedding metadata
    embedding_type VARCHAR(50) NOT NULL, -- 'subject', 'body', 'combined', 'summary'
    content_hash VARCHAR(64), -- SHA256 of source content

    -- Vector embedding
    embedding_vector vector(1536), -- OpenAI embedding size, adjust as needed

    -- Model info
    model_name VARCHAR(100),
    model_version VARCHAR(50),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(email_id, embedding_type)
);

-- Email attachments
CREATE TABLE email_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,

    -- File info
    filename VARCHAR(500) NOT NULL,
    content_type VARCHAR(200),
    content_id VARCHAR(255), -- For inline attachments
    size_bytes INTEGER,

    -- Storage
    storage_type VARCHAR(50) DEFAULT 'local', -- 'local', 's3', 'gcs'
    file_path TEXT, -- Local or cloud storage path
    content_hash VARCHAR(64), -- SHA256 for deduplication

    -- Processing
    is_inline BOOLEAN DEFAULT false,
    extracted_text TEXT, -- OCR/extracted text for search
    embedding_vector vector(1536), -- For document similarity search
    embeddings_generated BOOLEAN DEFAULT false,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(email_id, filename)
);

-- Tasks generated from emails
CREATE TABLE email_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Task content
    title VARCHAR(500) NOT NULL,
    description TEXT,
    task_type VARCHAR(100), -- 'reply', 'followup', 'calendar', 'action_item', 'reminder'

    -- Scheduling
    due_date TIMESTAMP WITH TIME ZONE,
    priority INTEGER DEFAULT 3, -- 1=urgent, 5=low
    estimated_duration_minutes INTEGER,

    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'cancelled'
    completion_percentage INTEGER DEFAULT 0,

    -- Generation metadata
    auto_generated BOOLEAN DEFAULT true,
    generation_prompt TEXT,
    generation_model VARCHAR(100),
    confidence_score FLOAT, -- 0.0 to 1.0

    -- Context
    related_emails JSONB DEFAULT '[]', -- Array of related email IDs
    action_required BOOLEAN DEFAULT false,
    external_references JSONB DEFAULT '{}', -- Calendar events, contacts, etc.

    -- Completion tracking
    completed_at TIMESTAMP WITH TIME ZONE,
    completed_by UUID REFERENCES users(id),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Email sync history (for tracking and debugging)
CREATE TABLE email_sync_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES email_accounts(id) ON DELETE CASCADE,

    -- Sync details
    sync_type VARCHAR(50) NOT NULL, -- 'full', 'incremental', 'manual'
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL, -- 'running', 'success', 'error', 'cancelled'

    -- Results
    emails_processed INTEGER DEFAULT 0,
    emails_added INTEGER DEFAULT 0,
    emails_updated INTEGER DEFAULT 0,
    emails_deleted INTEGER DEFAULT 0,
    attachments_processed INTEGER DEFAULT 0,

    -- Error tracking
    error_message TEXT,
    error_details JSONB,

    -- Performance metrics
    duration_seconds INTEGER,
    memory_usage_mb INTEGER,
    api_calls_made INTEGER
);

-- Indexes for performance
CREATE INDEX idx_emails_user_id ON emails(user_id);
CREATE INDEX idx_emails_account_id ON emails(account_id);
CREATE INDEX idx_emails_sent_at ON emails(sent_at DESC);
CREATE INDEX idx_emails_received_at ON emails(received_at DESC);
CREATE INDEX idx_emails_sender_email ON emails(sender_email);
CREATE INDEX idx_emails_subject_gin ON emails USING gin(to_tsvector('english', subject));
CREATE INDEX idx_emails_body_gin ON emails USING gin(to_tsvector('english', body_text));
CREATE INDEX idx_emails_category ON emails(category);
CREATE INDEX idx_emails_importance ON emails(importance_score DESC);
CREATE INDEX idx_emails_flags ON emails(is_read, is_flagged, is_important);

-- Vector similarity search index
CREATE INDEX idx_email_embeddings_vector ON email_embeddings USING ivfflat (embedding_vector vector_cosine_ops);

-- Task indexes
CREATE INDEX idx_email_tasks_user_id ON email_tasks(user_id);
CREATE INDEX idx_email_tasks_email_id ON email_tasks(email_id);
CREATE INDEX idx_email_tasks_due_date ON email_tasks(due_date);
CREATE INDEX idx_email_tasks_status ON email_tasks(status);
CREATE INDEX idx_email_tasks_priority ON email_tasks(priority);

-- Account sync indexes
CREATE INDEX idx_email_accounts_user_id ON email_accounts(user_id);
CREATE INDEX idx_email_accounts_sync_status ON email_accounts(sync_status);
CREATE INDEX idx_email_accounts_next_sync ON email_accounts(next_sync_at);

-- Comments for documentation
COMMENT ON TABLE email_accounts IS 'User email account configurations for synchronization';
COMMENT ON TABLE emails IS 'Local storage of synchronized email content with metadata';
COMMENT ON TABLE email_embeddings IS 'Vector embeddings for semantic email search';
COMMENT ON TABLE email_attachments IS 'Email attachments with extracted content and embeddings';
COMMENT ON TABLE email_tasks IS 'Tasks automatically generated from email analysis';
COMMENT ON TABLE email_sync_history IS 'Audit log of email synchronization operations';