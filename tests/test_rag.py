import pytest
from app.services.rag_engine import RAGEngine
from app.services.document_ingestion import DocumentIngestionService
from app.services.vector_store import VectorStoreService
from app.services.llm_service import LLMService
from unittest.mock import Mock, patch


class TestRAGEngine:
    """Tests for RAG Engine."""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services."""
        with patch('app.services.rag_engine.get_ingestion_service') as mock_ingestion, \
             patch('app.services.rag_engine.get_vector_store') as mock_vector, \
             patch('app.services.rag_engine.get_llm_service') as mock_llm:
            
            # Mock ingestion service
            mock_ingestion_instance = Mock()
            mock_ingestion_instance.generate_embeddings.return_value = [[0.1] * 384]
            mock_ingestion.return_value = mock_ingestion_instance
            
            # Mock vector store
            mock_vector_instance = Mock()
            mock_vector_instance.similarity_search.return_value = [
                {
                    'chunk_id': 1,
                    'document_id': 1,
                    'chunk_text': 'Test chunk content',
                    'chunk_index': 0,
                    'document_title': 'Test Document',
                    'metadata': {},
                    'similarity': 0.95
                }
            ]
            mock_vector.return_value = mock_vector_instance
            
            # Mock LLM service
            mock_llm_instance = Mock()
            mock_llm_instance.generate_response.return_value = "This is a test answer."
            mock_llm.return_value = mock_llm_instance
            
            yield {
                'ingestion': mock_ingestion_instance,
                'vector': mock_vector_instance,
                'llm': mock_llm_instance
            }
    
    def test_query_with_results(self, mock_services):
        """Test RAG query with results."""
        engine = RAGEngine()
        
        result = engine.query("What is the test?")
        
        assert 'answer' in result
        assert 'sources' in result
        assert 'query_time' in result
        assert 'model_used' in result
        assert result['answer'] == "This is a test answer."
        assert len(result['sources']) > 0
    
    def test_query_no_results(self, mock_services):
        """Test RAG query with no results."""
        mock_services['vector'].similarity_search.return_value = []
        
        engine = RAGEngine()
        result = engine.query("What is the test?")
        
        assert 'answer' in result
        assert "don't have enough information" in result['answer'].lower()
        assert len(result['sources']) == 0
    
    def test_build_context(self, mock_services):
        """Test context building."""
        engine = RAGEngine()
        
        chunks = [
            {
                'document_title': 'Doc 1',
                'chunk_text': 'Content 1',
                'similarity': 0.95
            },
            {
                'document_title': 'Doc 2',
                'chunk_text': 'Content 2',
                'similarity': 0.90
            }
        ]
        
        context = engine._build_context(chunks)
        
        assert 'Doc 1' in context
        assert 'Doc 2' in context
        assert 'Content 1' in context
        assert 'Content 2' in context


class TestDocumentIngestion:
    """Tests for Document Ingestion."""
    
    def test_chunk_text(self):
        """Test text chunking."""
        service = DocumentIngestionService()
        
        text = "This is a test. " * 200  # Create long text
        chunks = service.chunk_text(text)
        
        assert len(chunks) > 0
        assert all(len(chunk) <= service.text_splitter._chunk_size + 100 for chunk in chunks)
    
    def test_generate_embeddings(self):
        """Test embedding generation."""
        service = DocumentIngestionService()
        
        texts = ["Test text 1", "Test text 2"]
        embeddings = service.generate_embeddings(texts)
        
        assert len(embeddings) == 2
        assert len(embeddings[0]) == 384  # all-MiniLM-L6-v2 dimension


class TestLLMService:
    """Tests for LLM Service."""
    
    @patch('app.services.llm_service.Groq')
    def test_generate_response(self, mock_groq):
        """Test LLM response generation."""
        # Mock Groq client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq.return_value = mock_client
        
        service = LLMService()
        response = service.generate_response("Test prompt")
        
        assert response == "Test response"
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('app.services.llm_service.Groq')
    def test_extract_intent(self, mock_groq):
        """Test intent extraction."""
        # Mock Groq client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="question"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq.return_value = mock_client
        
        service = LLMService()
        intent = service.extract_intent("What is the weather?")
        
        assert intent == "question"
