-- Migration: Secure authentication and membership authorization
-- Version: 003
-- Depends on: 002_strengthen_core_schema.sql

CREATE EXTENSION IF NOT EXISTS citext;

-- A login email identifies one account. Refuse to merge ambiguous legacy users
-- automatically because choosing which password/profile survives is unsafe.
DO $$
BEGIN
    IF EXISTS (
        SELECT LOWER(email)
        FROM users
        GROUP BY LOWER(email)
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION
            'Migration 003: duplicate user emails must be resolved before enabling global identities';
    END IF;
END $$;

ALTER TABLE users
    ALTER COLUMN email TYPE CITEXT USING email::CITEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_global
    ON users(email);

-- Memberships now support one user in multiple companies. The direct user to
-- company columns remain only as a compatibility bridge for older code.
ALTER TABLE memberships
    DROP CONSTRAINT IF EXISTS fk_memberships_user_company;

-- Invitation roles now use the membership vocabulary.
UPDATE invitations
SET role = CASE role
    WHEN 'company_admin' THEN 'owner'
    WHEN 'hr_manager' THEN 'admin'
    WHEN 'employee' THEN 'member'
    ELSE role
END;

ALTER TABLE invitations
    DROP CONSTRAINT IF EXISTS ck_invitations_role;
ALTER TABLE invitations
    ADD CONSTRAINT ck_invitations_role
    CHECK (role IN ('owner', 'admin', 'member'));

-- Persist only a digest of invitation secrets. The legacy token column remains
-- nullable for a compatibility window but new application code never writes it.
ALTER TABLE invitations
    ADD COLUMN IF NOT EXISTS token_hash CHAR(64);
UPDATE invitations
SET token_hash = ENCODE(DIGEST(token, 'sha256'), 'hex')
WHERE token_hash IS NULL
  AND token IS NOT NULL;
ALTER TABLE invitations
    ALTER COLUMN token DROP NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_invitations_token_hash
    ON invitations(token_hash)
    WHERE token_hash IS NOT NULL;

ALTER TABLE invitations
    ALTER COLUMN expires_at TYPE TIMESTAMPTZ
        USING expires_at AT TIME ZONE 'UTC',
    ALTER COLUMN accepted_at TYPE TIMESTAMPTZ
        USING accepted_at AT TIME ZONE 'UTC',
    ALTER COLUMN created_at TYPE TIMESTAMPTZ
        USING created_at AT TIME ZONE 'UTC';

-- Refresh tokens are opaque random secrets. Only their SHA-256 hashes are
-- stored, allowing rotation and server-side revocation.
CREATE TABLE IF NOT EXISTS refresh_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    membership_id UUID NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    replaced_by UUID REFERENCES refresh_sessions(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    CONSTRAINT ck_refresh_sessions_expiry
        CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS idx_refresh_sessions_user_active
    ON refresh_sessions(user_id, expires_at DESC)
    WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_refresh_sessions_membership_active
    ON refresh_sessions(membership_id, expires_at DESC)
    WHERE revoked_at IS NULL;
