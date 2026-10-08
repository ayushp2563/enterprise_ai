import pytest
from datetime import datetime
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.security.auth import get_current_user

client = TestClient(app)


class TestAPIEndpoints:
    """Tests for API endpoints."""
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Enterprise AI Assistant" in response.json()["message"]
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_query_without_authentication(self):
        """Protected query endpoint rejects an anonymous caller."""
        response = client.post(
            "/api/query/",
            json={"question": "Test question"}
        )
        assert response.status_code == 401
    
    def test_authenticated_user_can_read_profile(self):
        """Authentication context is serialized through the public schema."""
        now = datetime.now()
        principal = {
            "id": 1,
            "public_id": uuid4(),
            "company_id": 1,
            "membership_id": uuid4(),
            "email": "user@example.com",
            "full_name": "Test User",
            "role": "member",
            "is_active": True,
            "last_login": None,
            "created_at": now,
            "updated_at": now,
        }
        app.dependency_overrides[get_current_user] = lambda: principal
        try:
            response = client.get("/api/auth/me")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["role"] == "member"
    
    def test_documents_list_without_authentication(self):
        """Document listing rejects an anonymous caller."""
        response = client.get("/api/documents/")
        assert response.status_code == 401
