-- Migration: Strengthen core schema
-- Description: Adds durable ingestion, memberships, conversations, audit events,
--              tenant-safe chunk ownership, constraints, and query-driven indexes.
-- Version: 002
-- Depends on: 001_add_multi_tenancy.sql

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Refuse to hide legacy data corruption. These checks provide actionable
-- failures before tenant constraints and unique indexes are installed.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM users
        WHERE role NOT IN ('company_admin', 'hr_manager', 'employee')
    ) THEN
        RAISE EXCEPTION 'Migration 002: users contains unsupported role values';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM query_logs
        WHERE confidence_score IS NOT NULL
          AND (confidence_score < 0 OR confidence_score > 1)
    ) THEN
        RAISE EXCEPTION 'Migration 002: query_logs contains confidence scores outside 0..1';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM query_logs
        WHERE feedback_rating IS NOT NULL
          AND feedback_rating NOT BETWEEN 1 AND 5
    ) THEN
        RAISE EXCEPTION 'Migration 002: query_logs contains feedback ratings outside 1..5';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM hr_escalations
        WHERE status IS NOT NULL
          AND status NOT IN ('pending', 'contacted', 'resolved')
    ) THEN
        RAISE EXCEPTION 'Migration 002: hr_escalations contains unsupported status values';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM document_chunks
        GROUP BY document_id, chunk_index
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Migration 002: duplicate document chunk positions must be resolved';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM invitations AS i
        JOIN users AS u ON u.id = i.invited_by
        WHERE i.company_id <> u.company_id
    ) THEN
        RAISE EXCEPTION 'Migration 002: cross-company invitation inviter detected';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM documents AS d
        JOIN users AS u ON u.id = d.uploaded_by
        WHERE d.company_id <> u.company_id
    ) THEN
        RAISE EXCEPTION 'Migration 002: cross-company document uploader detected';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM query_logs AS q
        JOIN users AS u ON u.id = q.user_id
        WHERE q.company_id <> u.company_id
    ) THEN
        RAISE EXCEPTION 'Migration 002: cross-company query log user detected';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM hr_escalations AS h
        JOIN query_logs AS q ON q.id = h.query_log_id
        WHERE h.company_id <> q.company_id
    ) THEN
        RAISE EXCEPTION 'Migration 002: cross-company escalation query detected';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM hr_escalations AS h
        JOIN users AS u ON u.id = h.user_id
        WHERE h.company_id <> u.company_id
    ) THEN
        RAISE EXCEPTION 'Migration 002: cross-company escalation user detected';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM hr_escalations AS h
        JOIN users AS u ON u.id = h.resolved_by
        WHERE h.company_id <> u.company_id
    ) THEN
        RAISE EXCEPTION 'Migration 002: cross-company escalation resolver detected';
    END IF;
END $$;

-- ============================================================================
-- 1. ADD STABLE PUBLIC IDENTIFIERS WITHOUT BREAKING CURRENT INTEGER FOREIGN KEYS
-- ============================================================================
ALTER TABLE companies
    ADD COLUMN IF NOT EXISTS public_id UUID DEFAULT gen_random_uuid();
UPDATE companies SET public_id = gen_random_uuid() WHERE public_id IS NULL;
ALTER TABLE companies ALTER COLUMN public_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_public_id
    ON companies(public_id);

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS public_id UUID DEFAULT gen_random_uuid();
UPDATE users SET public_id = gen_random_uuid() WHERE public_id IS NULL;
ALTER TABLE users ALTER COLUMN public_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_public_id
    ON users(public_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_id_company
    ON users(id, company_id);

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS public_id UUID DEFAULT gen_random_uuid();
UPDATE documents SET public_id = gen_random_uuid() WHERE public_id IS NULL;
ALTER TABLE documents ALTER COLUMN public_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_public_id
    ON documents(public_id);

-- ============================================================================
-- 2. MEMBERSHIPS
-- Keep users.company_id/users.role during the authentication transition.
-- Phase 3 will make memberships the authorization source of truth.
-- ============================================================================
CREATE TABLE IF NOT EXISTS memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_memberships_company_user UNIQUE (company_id, user_id),
    CONSTRAINT ck_memberships_role
        CHECK (role IN ('owner', 'admin', 'member'))
);

INSERT INTO memberships (company_id, user_id, role, is_active)
SELECT
    company_id,
    id,
    CASE role
        WHEN 'company_admin' THEN 'owner'
        WHEN 'hr_manager' THEN 'admin'
        ELSE 'member'
    END,
    is_active
FROM users
ON CONFLICT (company_id, user_id) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_memberships_user_active
    ON memberships(user_id, is_active)
    WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_memberships_company_role_active
    ON memberships(company_id, role)
    WHERE is_active = true;

ALTER TABLE memberships
    DROP CONSTRAINT IF EXISTS fk_memberships_user_company;
ALTER TABLE memberships
    ADD CONSTRAINT fk_memberships_user_company
    FOREIGN KEY (user_id, company_id)
    REFERENCES users(id, company_id)
    ON DELETE CASCADE;

DROP TRIGGER IF EXISTS update_memberships_updated_at ON memberships;
CREATE TRIGGER update_memberships_updated_at
    BEFORE UPDATE ON memberships
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 3. DOCUMENT LIFECYCLE AND DEDUPLICATION METADATA
-- ============================================================================
ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS original_filename VARCHAR(500),
    ADD COLUMN IF NOT EXISTS media_type VARCHAR(255),
    ADD COLUMN IF NOT EXISTS storage_key TEXT,
    ADD COLUMN IF NOT EXISTS checksum_sha256 CHAR(64),
    ADD COLUMN IF NOT EXISTS ingestion_status VARCHAR(20) DEFAULT 'completed',
    ADD COLUMN IF NOT EXISTS ingestion_error TEXT,
    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

UPDATE documents
SET
    original_filename = COALESCE(
        original_filename,
        metadata->>'filename',
        title
    ),
    ingestion_status = COALESCE(ingestion_status, 'completed'),
    completed_at = COALESCE(completed_at, created_at)
WHERE original_filename IS NULL
   OR ingestion_status IS NULL
   OR completed_at IS NULL;

ALTER TABLE documents
    ALTER COLUMN ingestion_status SET NOT NULL;

ALTER TABLE documents
    DROP CONSTRAINT IF EXISTS ck_documents_ingestion_status;
ALTER TABLE documents
    ADD CONSTRAINT ck_documents_ingestion_status
    CHECK (ingestion_status IN ('pending', 'processing', 'completed', 'failed'));

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_company_checksum_active
    ON documents(company_id, checksum_sha256)
    WHERE is_active = true AND checksum_sha256 IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_documents_company_active_created
    ON documents(company_id, created_at DESC)
    WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_documents_company_status_created
    ON documents(company_id, ingestion_status, created_at DESC)
    WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_documents_company_category_active
    ON documents(company_id, category)
    WHERE is_active = true;

ALTER TABLE documents
    DROP CONSTRAINT IF EXISTS fk_documents_uploader_company;
ALTER TABLE documents
    ADD CONSTRAINT fk_documents_uploader_company
    FOREIGN KEY (uploaded_by, company_id)
    REFERENCES users(id, company_id);

-- ============================================================================
-- 4. TENANT-SAFE DOCUMENT CHUNKS AND CITATION METADATA
-- ============================================================================
ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS company_id INTEGER,
    ADD COLUMN IF NOT EXISTS page_number INTEGER,
    ADD COLUMN IF NOT EXISTS token_count INTEGER,
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(255)
        DEFAULT 'all-MiniLM-L6-v2';

UPDATE document_chunks AS dc
SET company_id = d.company_id
FROM documents AS d
WHERE dc.document_id = d.id
  AND dc.company_id IS NULL;

ALTER TABLE document_chunks
    ALTER COLUMN company_id SET NOT NULL;

ALTER TABLE document_chunks
    DROP CONSTRAINT IF EXISTS fk_document_chunks_company;
ALTER TABLE document_chunks
    ADD CONSTRAINT fk_document_chunks_company
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_id_company
    ON documents(id, company_id);

ALTER TABLE document_chunks
    DROP CONSTRAINT IF EXISTS fk_document_chunks_document_company;
ALTER TABLE document_chunks
    ADD CONSTRAINT fk_document_chunks_document_company
    FOREIGN KEY (document_id, company_id)
    REFERENCES documents(id, company_id)
    ON DELETE CASCADE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_document_chunks_document_position
    ON document_chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_document_chunks_company_document
    ON document_chunks(company_id, document_id);

-- ============================================================================
-- 5. DURABLE INGESTION JOBS
-- ============================================================================
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    locked_at TIMESTAMPTZ,
    locked_by VARCHAR(255),
    error_code VARCHAR(100),
    error_detail TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ingestion_jobs_document UNIQUE (document_id),
    CONSTRAINT ck_ingestion_jobs_status
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    CONSTRAINT ck_ingestion_jobs_attempts
        CHECK (
            attempt_count >= 0
            AND max_attempts > 0
            AND attempt_count <= max_attempts
        )
);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_claim
    ON ingestion_jobs(available_at, created_at)
    WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_company_status
    ON ingestion_jobs(company_id, status, created_at DESC);

ALTER TABLE ingestion_jobs
    DROP CONSTRAINT IF EXISTS fk_ingestion_jobs_document_company;
ALTER TABLE ingestion_jobs
    ADD CONSTRAINT fk_ingestion_jobs_document_company
    FOREIGN KEY (document_id, company_id)
    REFERENCES documents(id, company_id)
    ON DELETE CASCADE;

DROP TRIGGER IF EXISTS update_ingestion_jobs_updated_at ON ingestion_jobs;
CREATE TRIGGER update_ingestion_jobs_updated_at
    BEFORE UPDATE ON ingestion_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 6. CONVERSATIONS AND MESSAGES
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_conversations_company_user_updated
    ON conversations(company_id, user_id, updated_at DESC)
    WHERE archived_at IS NULL;

ALTER TABLE conversations
    DROP CONSTRAINT IF EXISTS fk_conversations_user_company;
ALTER TABLE conversations
    ADD CONSTRAINT fk_conversations_user_company
    FOREIGN KEY (user_id, company_id)
    REFERENCES users(id, company_id)
    ON DELETE CASCADE;

DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    citations JSONB NOT NULL DEFAULT '[]',
    retrieval_metadata JSONB NOT NULL DEFAULT '{}',
    model VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_messages_role
        CHECK (role IN ('user', 'assistant', 'system'))
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
    ON messages(conversation_id, created_at, id);
CREATE INDEX IF NOT EXISTS idx_messages_company_created
    ON messages(company_id, created_at DESC);

ALTER TABLE messages
    DROP CONSTRAINT IF EXISTS fk_messages_user_company;
ALTER TABLE messages
    ADD CONSTRAINT fk_messages_user_company
    FOREIGN KEY (user_id, company_id)
    REFERENCES users(id, company_id)
    ON DELETE SET NULL (user_id);

-- Enforce that a message and its conversation belong to the same company.
CREATE UNIQUE INDEX IF NOT EXISTS uq_conversations_id_company
    ON conversations(id, company_id);

ALTER TABLE messages
    DROP CONSTRAINT IF EXISTS fk_messages_conversation_company;
ALTER TABLE messages
    ADD CONSTRAINT fk_messages_conversation_company
    FOREIGN KEY (conversation_id, company_id)
    REFERENCES conversations(id, company_id)
    ON DELETE CASCADE;

-- ============================================================================
-- 7. AUDIT EVENTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id TEXT,
    request_id UUID,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_company_created
    ON audit_events(company_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_resource
    ON audit_events(company_id, resource_type, resource_id, created_at DESC);

ALTER TABLE audit_events
    DROP CONSTRAINT IF EXISTS fk_audit_events_actor_company;
ALTER TABLE audit_events
    ADD CONSTRAINT fk_audit_events_actor_company
    FOREIGN KEY (actor_user_id, company_id)
    REFERENCES users(id, company_id)
    ON DELETE SET NULL (actor_user_id);

-- ============================================================================
-- 8. TENANT CONSISTENCY FOR EXISTING RELATIONSHIPS
-- ============================================================================
CREATE UNIQUE INDEX IF NOT EXISTS uq_query_logs_id_company
    ON query_logs(id, company_id);

ALTER TABLE invitations
    DROP CONSTRAINT IF EXISTS fk_invitations_inviter_company;
ALTER TABLE invitations
    ADD CONSTRAINT fk_invitations_inviter_company
    FOREIGN KEY (invited_by, company_id)
    REFERENCES users(id, company_id);

ALTER TABLE query_logs
    DROP CONSTRAINT IF EXISTS fk_query_logs_user_company;
ALTER TABLE query_logs
    ADD CONSTRAINT fk_query_logs_user_company
    FOREIGN KEY (user_id, company_id)
    REFERENCES users(id, company_id);

ALTER TABLE hr_escalations
    DROP CONSTRAINT IF EXISTS fk_hr_escalations_query_company;
ALTER TABLE hr_escalations
    ADD CONSTRAINT fk_hr_escalations_query_company
    FOREIGN KEY (query_log_id, company_id)
    REFERENCES query_logs(id, company_id);

ALTER TABLE hr_escalations
    DROP CONSTRAINT IF EXISTS fk_hr_escalations_user_company;
ALTER TABLE hr_escalations
    ADD CONSTRAINT fk_hr_escalations_user_company
    FOREIGN KEY (user_id, company_id)
    REFERENCES users(id, company_id);

ALTER TABLE hr_escalations
    DROP CONSTRAINT IF EXISTS fk_hr_escalations_resolver_company;
ALTER TABLE hr_escalations
    ADD CONSTRAINT fk_hr_escalations_resolver_company
    FOREIGN KEY (resolved_by, company_id)
    REFERENCES users(id, company_id);

-- ============================================================================
-- 9. CONSTRAINTS AND INDEXES FOR EXISTING TABLES
-- ============================================================================
ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_role;
ALTER TABLE users
    ADD CONSTRAINT ck_users_role
    CHECK (role IN ('company_admin', 'hr_manager', 'employee'));

ALTER TABLE query_logs DROP CONSTRAINT IF EXISTS ck_query_logs_confidence;
ALTER TABLE query_logs
    ADD CONSTRAINT ck_query_logs_confidence
    CHECK (
        confidence_score IS NULL
        OR (confidence_score >= 0 AND confidence_score <= 1)
    );

ALTER TABLE query_logs DROP CONSTRAINT IF EXISTS ck_query_logs_feedback;
ALTER TABLE query_logs
    ADD CONSTRAINT ck_query_logs_feedback
    CHECK (
        feedback_rating IS NULL
        OR feedback_rating BETWEEN 1 AND 5
    );

ALTER TABLE hr_escalations DROP CONSTRAINT IF EXISTS ck_hr_escalations_status;
ALTER TABLE hr_escalations
    ADD CONSTRAINT ck_hr_escalations_status
    CHECK (status IN ('pending', 'contacted', 'resolved'));

CREATE INDEX IF NOT EXISTS idx_query_logs_company_user_created
    ON query_logs(company_id, user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_hr_escalations_company_status_created
    ON hr_escalations(company_id, status, created_at DESC);
