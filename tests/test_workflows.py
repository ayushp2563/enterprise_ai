import pytest
from app.services.workflow_automation import WorkflowAutomationService
from app.models.workflows import WorkflowType
from unittest.mock import patch, Mock


class TestWorkflowAutomation:
    """Tests for Workflow Automation."""
    
    @patch('app.services.workflow_automation.get_llm_service')
    def test_create_ticket(self, mock_llm):
        """Test ticket creation workflow."""
        # Mock LLM service
        mock_llm_instance = Mock()
        mock_llm_instance.generate_response.return_value = "Enhanced description"
        mock_llm.return_value = mock_llm_instance
        
        service = WorkflowAutomationService()
        
        result = service.execute_workflow(
            workflow_type=WorkflowType.TICKET_CREATION,
            parameters={
                "title": "Test Ticket",
                "description": "Test description",
                "priority": "high",
                "category": "bug"
            }
        )
        
        assert "ticket_id" in result
        assert result["title"] == "Test Ticket"
        assert result["priority"] == "high"
        assert result["status"] == "created"
    
    @patch('app.services.workflow_automation.get_llm_service')
    def test_summarize_report(self, mock_llm):
        """Test report summarization workflow."""
        # Mock LLM service
        mock_llm_instance = Mock()
        mock_llm_instance.generate_summary.return_value = "Test summary"
        mock_llm_instance.generate_response.return_value = "- Key point 1\n- Key point 2"
        mock_llm.return_value = mock_llm_instance
        
        service = WorkflowAutomationService()
        
        result = service.execute_workflow(
            workflow_type=WorkflowType.REPORT_SUMMARY,
            parameters={
                "report_text": "This is a long report text that needs summarization.",
                "max_length": 500
            }
        )
        
        assert "summary" in result
        assert "key_points" in result
        assert result["summary"] == "Test summary"
