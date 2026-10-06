"""PostgreSQL-backed tenant isolation tests.

Run with RUN_DB_TESTS=1 after applying migrations to DATABASE_URL.
"""

import os

import psycopg2
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security.auth import get_current_user
from app.services.vector_store import VectorStoreService


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="requires migrated PostgreSQL/pgvector test database",
)


@pytest.fixture()
def tenant_records():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    embedding_a = [0.1] * 384
    embedding_b = [0.2] * 384

    with conn:
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE companies CASCADE")
            cursor.execute("""
                INSERT INTO companies (name, slug)
                VALUES ('Tenant A', 'tenant-a'), ('Tenant B', 'tenant-b')
                RETURNING id
            """)
            company_a, company_b = [row[0] for row in cursor.fetchall()]

            cursor.execute("""
                INSERT INTO users (
                    company_id, email, password_hash, full_name, role
                )
                VALUES
                    (%s, 'a@example.test', 'hash', 'User A', 'company_admin'),
                    (%s, 'b@example.test', 'hash', 'User B', 'company_admin')
                RETURNING id
            """, (company_a, company_b))
            user_a, user_b = [row[0] for row in cursor.fetchall()]

            cursor.execute("""
                INSERT INTO memberships (company_id, user_id, role)
                VALUES (%s, %s, 'owner'), (%s, %s, 'owner')
                RETURNING id
            """, (company_a, user_a, company_b, user_b))
            membership_a, membership_b = [row[0] for row in cursor.fetchall()]

            cursor.execute("""
                INSERT INTO documents (
                    company_id, uploaded_by, title, is_active,
                    ingestion_status
                )
                VALUES
                    (%s, %s, 'Tenant A Policy', true, 'completed'),
                    (%s, %s, 'Tenant B Policy', true, 'completed')
                RETURNING id
            """, (company_a, user_a, company_b, user_b))
            document_a, document_b = [row[0] for row in cursor.fetchall()]

            cursor.execute("""
                INSERT INTO document_chunks (
                    document_id, company_id, chunk_text, chunk_index,
                    embedding, embedding_model
                )
                VALUES
                    (%s, %s, 'A confidential policy', 0, %s::vector, 'test'),
                    (%s, %s, 'B confidential policy', 0, %s::vector, 'test')
            """, (
                document_a, company_a, embedding_a,
                document_b, company_b, embedding_b,
            ))

    yield {
        "company_a": company_a,
        "company_b": company_b,
        "user_a": user_a,
        "membership_a": membership_a,
        "document_a": document_a,
        "document_b": document_b,
        "embedding_a": embedding_a,
    }

    conn.close()


def test_vector_search_and_chunk_access_are_tenant_scoped(tenant_records):
    store = VectorStoreService()

    results = store.similarity_search(
        tenant_records["embedding_a"],
        company_id=tenant_records["company_a"],
        top_k=10,
        threshold=-1,
    )

    assert {item["document_id"] for item in results} == {
        tenant_records["document_a"]
    }
    assert store.get_document_chunks(
        tenant_records["document_b"],
        tenant_records["company_a"],
    ) == []

    store.delete_document_chunks(
        tenant_records["document_b"],
        tenant_records["company_a"],
    )
    assert store.get_document_chunks(
        tenant_records["document_b"],
        tenant_records["company_b"],
    )
    store.close()


def test_user_cannot_fetch_another_tenants_document(tenant_records):
    principal = {
        "id": tenant_records["user_a"],
        "membership_id": tenant_records["membership_a"],
        "company_id": tenant_records["company_a"],
        "role": "owner",
        "is_active": True,
        "email": "a@example.test",
    }

    app.dependency_overrides[get_current_user] = lambda: principal
    try:
        response = TestClient(app).get(
            f"/api/documents/{tenant_records['document_b']}"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
