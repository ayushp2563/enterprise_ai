-- Migration: Scope tenant actors through memberships
-- Version: 004
-- Depends on: 003_secure_authentication.sql
--
-- Phase 2 linked tenant actor columns to users(id, company_id). That prevents a
-- valid global user from writing in a secondary organization. Memberships are
-- the authoritative proof that a user belongs to a company.

CREATE UNIQUE INDEX IF NOT EXISTS uq_memberships_user_company
    ON memberships(user_id, company_id);

ALTER TABLE invitations
    DROP CONSTRAINT IF EXISTS fk_invitations_inviter_company;
ALTER TABLE invitations
    ADD CONSTRAINT fk_invitations_inviter_company
    FOREIGN KEY (invited_by, company_id)
    REFERENCES memberships(user_id, company_id);

ALTER TABLE documents
    DROP CONSTRAINT IF EXISTS fk_documents_uploader_company;
ALTER TABLE documents
    ADD CONSTRAINT fk_documents_uploader_company
    FOREIGN KEY (uploaded_by, company_id)
    REFERENCES memberships(user_id, company_id);

ALTER TABLE query_logs
    DROP CONSTRAINT IF EXISTS fk_query_logs_user_company;
ALTER TABLE query_logs
    ADD CONSTRAINT fk_query_logs_user_company
    FOREIGN KEY (user_id, company_id)
    REFERENCES memberships(user_id, company_id);

ALTER TABLE conversations
    DROP CONSTRAINT IF EXISTS fk_conversations_user_company;
ALTER TABLE conversations
    ADD CONSTRAINT fk_conversations_user_company
    FOREIGN KEY (user_id, company_id)
    REFERENCES memberships(user_id, company_id)
    ON DELETE CASCADE;

ALTER TABLE messages
    DROP CONSTRAINT IF EXISTS fk_messages_user_company;
ALTER TABLE messages
    ADD CONSTRAINT fk_messages_user_company
    FOREIGN KEY (user_id, company_id)
    REFERENCES memberships(user_id, company_id)
    ON DELETE SET NULL (user_id);

ALTER TABLE audit_events
    DROP CONSTRAINT IF EXISTS fk_audit_events_actor_company;
ALTER TABLE audit_events
    ADD CONSTRAINT fk_audit_events_actor_company
    FOREIGN KEY (actor_user_id, company_id)
    REFERENCES memberships(user_id, company_id)
    ON DELETE SET NULL (actor_user_id);

ALTER TABLE hr_escalations
    DROP CONSTRAINT IF EXISTS fk_hr_escalations_user_company;
ALTER TABLE hr_escalations
    ADD CONSTRAINT fk_hr_escalations_user_company
    FOREIGN KEY (user_id, company_id)
    REFERENCES memberships(user_id, company_id);

ALTER TABLE hr_escalations
    DROP CONSTRAINT IF EXISTS fk_hr_escalations_resolver_company;
ALTER TABLE hr_escalations
    ADD CONSTRAINT fk_hr_escalations_resolver_company
    FOREIGN KEY (resolved_by, company_id)
    REFERENCES memberships(user_id, company_id);
