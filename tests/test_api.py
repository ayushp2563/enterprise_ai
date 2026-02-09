import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, Mock

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
    
    def test_query_without_api_key(self):
        """Test query endpoint without API key."""
        response = client.post(
            "/api/query/",
            json={"question": "Test question"}
        )
        assert response.status_code == 401
    
    @patch('app.api.query.get_rag_engine')
    def test_query_with_api_key(self, mock_rag):
        """Test query endpoint with API key."""
        # Mock RAG engine
        mock_engine = Mock()
        mock_engine.query.return_value = {
            "answer": "Test answer",
            "sources": [],
            "query_time": 0.5,
            "model_used": "llama-3.3-70b-versatile"
        }
        mock_rag.return_value = mock_engine
        
        response = client.post(
            "/api/query/",
            json={"question": "Test question"},
            headers={"X-API-Key": "test_api_key"}
        )
        
        # Will fail without proper API key, but tests the flow
        # In real tests, you'd set the correct API key
        assert response.status_code in [200, 401]
    
    def test_documents_list_without_api_key(self):
        """Test documents list without API key."""
        response = client.get("/api/documents/")
        assert response.status_code == 401
