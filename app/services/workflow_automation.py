import logging
from datetime import datetime
from typing import Dict, Any
from app.models.workflows import WorkflowType, WorkflowStatus, TicketCreationParams, ReportSummaryParams
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class WorkflowAutomationService:
    """Service for automating workflows."""
    
    def __init__(self):
        """Initialize the workflow automation service."""
        self.llm_service = get_llm_service()
        logger.info("Initialized WorkflowAutomationService")
    
    def execute_workflow(
        self,
        workflow_type: WorkflowType,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a workflow based on type.
        
        Args:
            workflow_type: Type of workflow to execute
            parameters: Workflow parameters
            
        Returns:
            Workflow execution result
        """
        logger.info(f"Executing workflow: {workflow_type}")
        
        try:
            if workflow_type == WorkflowType.TICKET_CREATION:
                return self._create_ticket(parameters)
            elif workflow_type == WorkflowType.REPORT_SUMMARY:
                return self._summarize_report(parameters)
            else:
                raise ValueError(f"Unsupported workflow type: {workflow_type}")
                
        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}")
            raise
    
    def _create_ticket(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a ticket (simulated).
        
        Args:
            parameters: Ticket creation parameters
            
        Returns:
            Ticket creation result
        """
        # Validate parameters
        params = TicketCreationParams(**parameters)
        
        # In a real implementation, this would integrate with a ticketing system
        # For now, we'll simulate ticket creation
        ticket_id = f"TICKET-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Use LLM to enhance the ticket description if needed
        enhanced_description = self.llm_service.generate_response(
            prompt=f"Enhance this ticket description to be more clear and actionable:\n\n{params.description}",
            system_message="You are a helpful assistant that improves ticket descriptions.",
            temperature=0.5,
            max_tokens=500
        )
        
        result = {
            "ticket_id": ticket_id,
            "title": params.title,
            "description": params.description,
            "enhanced_description": enhanced_description,
            "priority": params.priority,
            "category": params.category,
            "status": "created",
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"Created ticket: {ticket_id}")
        return result
    
    def _summarize_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Summarize a report.
        
        Args:
            parameters: Report summary parameters
            
        Returns:
            Report summary result
        """
        # Validate parameters
        params = ReportSummaryParams(**parameters)
        
        # Generate summary using LLM
        summary = self.llm_service.generate_summary(
            text=params.report_text,
            max_length=params.max_length
        )
        
        # Extract key points
        key_points_prompt = f"""Based on this report, extract 3-5 key points in bullet format:

{params.report_text}

Key points:"""
        
        key_points = self.llm_service.generate_response(
            prompt=key_points_prompt,
            system_message="You are a helpful assistant that extracts key points from reports.",
            temperature=0.3,
            max_tokens=300
        )
        
        result = {
            "summary": summary,
            "key_points": key_points,
            "original_length": len(params.report_text),
            "summary_length": len(summary),
            "created_at": datetime.now().isoformat()
        }
        
        logger.info("Generated report summary")
        return result
    
    def detect_workflow_intent(self, query: str) -> WorkflowType:
        """
        Detect if a query should trigger a workflow.
        
        Args:
            query: User query
            
        Returns:
            Detected workflow type or None
        """
        intent = self.llm_service.extract_intent(query)
        
        intent_mapping = {
            "ticket_creation": WorkflowType.TICKET_CREATION,
            "report_summary": WorkflowType.REPORT_SUMMARY
        }
        
        return intent_mapping.get(intent)


# Singleton instance
_workflow_service = None


def get_workflow_service() -> WorkflowAutomationService:
    """Get singleton instance of WorkflowAutomationService."""
    global _workflow_service
    if _workflow_service is None:
        _workflow_service = WorkflowAutomationService()
    return _workflow_service
