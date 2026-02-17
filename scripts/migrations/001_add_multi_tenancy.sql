-- Migration: Add Multi-Tenancy Support
-- Description: Adds companies, users, invitations, and HR escalation tables
-- Version: 001
-- Date: 2026-02-17

-- ============================================================================
-- 1. CREATE COMPANIES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    domain VARCHAR(255),
    settings JSONB DEFAULT '{}',
    subscription_tier VARCHAR(50) DEFAULT 'free',
    max_employees INTEGER DEFAULT 50,
    max_documents INTEGER DEFAULT 100,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_companies_slug ON companies(slug);
CREATE INDEX idx_companies_domain ON companies(domain);

-- ============================================================================
-- 2. CREATE USERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'employee',
    -- Roles: 'company_admin', 'hr_manager', 'employee'
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(company_id, email)
);

CREATE INDEX idx_users_company_id ON users(company_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- ============================================================================
-- 3. CREATE INVITATIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS invitations (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'employee',
    token VARCHAR(255) UNIQUE NOT NULL,
    invited_by INTEGER REFERENCES users(id),
    expires_at TIMESTAMP NOT NULL,
    accepted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(company_id, email)
);

CREATE INDEX idx_invitations_company_id ON invitations(company_id);
CREATE INDEX idx_invitations_token ON invitations(token);
CREATE INDEX idx_invitations_email ON invitations(email);

-- ============================================================================
-- 4. MODIFY DOCUMENTS TABLE (Add Multi-Tenancy)
-- ============================================================================
-- Add columns if they don't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='documents' AND column_name='company_id') THEN
        ALTER TABLE documents ADD COLUMN company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='documents' AND column_name='uploaded_by') THEN
        ALTER TABLE documents ADD COLUMN uploaded_by INTEGER REFERENCES users(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='documents' AND column_name='category') THEN
        ALTER TABLE documents ADD COLUMN category VARCHAR(100);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='documents' AND column_name='is_active') THEN
        ALTER TABLE documents ADD COLUMN is_active BOOLEAN DEFAULT true;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_documents_company_id ON documents(company_id);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);

-- ============================================================================
-- 5. MODIFY QUERY_LOGS TABLE (Add Multi-Tenancy and HR Escalation)
-- ============================================================================
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='query_logs' AND column_name='company_id') THEN
        ALTER TABLE query_logs ADD COLUMN company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='query_logs' AND column_name='user_id') THEN
        ALTER TABLE query_logs ADD COLUMN user_id INTEGER REFERENCES users(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='query_logs' AND column_name='confidence_score') THEN
        ALTER TABLE query_logs ADD COLUMN confidence_score FLOAT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='query_logs' AND column_name='escalated_to_hr') THEN
        ALTER TABLE query_logs ADD COLUMN escalated_to_hr BOOLEAN DEFAULT false;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='query_logs' AND column_name='feedback_rating') THEN
        ALTER TABLE query_logs ADD COLUMN feedback_rating INTEGER;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_query_logs_company_id ON query_logs(company_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_user_id ON query_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_escalated ON query_logs(escalated_to_hr);

-- ============================================================================
-- 6. CREATE HR_ESCALATIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS hr_escalations (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    query_log_id INTEGER REFERENCES query_logs(id),
    user_id INTEGER REFERENCES users(id),
    question TEXT NOT NULL,
    reason VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    -- Status: 'pending', 'contacted', 'resolved'
    hr_response TEXT,
    resolved_by INTEGER REFERENCES users(id),
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_hr_escalations_company_id ON hr_escalations(company_id);
CREATE INDEX idx_hr_escalations_user_id ON hr_escalations(user_id);
CREATE INDEX idx_hr_escalations_status ON hr_escalations(status);
CREATE INDEX idx_hr_escalations_created_at ON hr_escalations(created_at);

-- ============================================================================
-- 7. CREATE DEFAULT COMPANY FOR EXISTING DATA
-- ============================================================================
INSERT INTO companies (name, slug, domain, subscription_tier, is_active)
VALUES ('Default Company', 'default-company', 'example.com', 'free', true)
ON CONFLICT (slug) DO NOTHING;

-- ============================================================================
-- 8. MIGRATE EXISTING DOCUMENTS TO DEFAULT COMPANY
-- ============================================================================
DO $$ 
DECLARE
    default_company_id INTEGER;
BEGIN
    SELECT id INTO default_company_id FROM companies WHERE slug = 'default-company';
    
    IF default_company_id IS NOT NULL THEN
        UPDATE documents 
        SET company_id = default_company_id 
        WHERE company_id IS NULL;
        
        UPDATE query_logs 
        SET company_id = default_company_id 
        WHERE company_id IS NULL;
    END IF;
END $$;

-- ============================================================================
-- 9. MAKE COMPANY_ID NOT NULL (After Migration)
-- ============================================================================
DO $$ 
BEGIN
    -- Only make NOT NULL if all rows have been migrated
    IF NOT EXISTS (SELECT 1 FROM documents WHERE company_id IS NULL) THEN
        ALTER TABLE documents ALTER COLUMN company_id SET NOT NULL;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM query_logs WHERE company_id IS NULL) THEN
        ALTER TABLE query_logs ALTER COLUMN company_id SET NOT NULL;
    END IF;
END $$;

-- ============================================================================
-- 10. CREATE UPDATED_AT TRIGGER FUNCTION
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to companies
DROP TRIGGER IF EXISTS update_companies_updated_at ON companies;
CREATE TRIGGER update_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to users
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to documents
DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
