import logging
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.workflows import WorkflowRequest, WorkflowResponse, WorkflowStatus
from app.services.workflow_automation import get_workflow_service
from app.security.auth import verify_api_key
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workflows", tags=["Workflows"])


@router.post("/execute", response_model=WorkflowResponse)
async def execute_workflow(
    request: WorkflowRequest,
    api_key: str = Depends(verify_api_key)
) -> WorkflowResponse:
    """
    Execute a workflow.
    
    Args:
        request: Workflow execution request
        api_key: Validated API key
        
    Returns:
        Workflow execution result
    """
    try:
        logger.info(f"Executing workflow: {request.workflow_type}")
        
        workflow_service = get_workflow_service()
        result = workflow_service.execute_workflow(
            workflow_type=request.workflow_type,
            parameters=request.parameters
        )
        
        return WorkflowResponse(
            workflow_id=hash(str(datetime.now())),  # Simple ID generation
            status=WorkflowStatus.COMPLETED,
            result=result,
            created_at=datetime.now(),
            completed_at=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}")
        
        return WorkflowResponse(
            workflow_id=hash(str(datetime.now())),
            status=WorkflowStatus.FAILED,
            error=str(e),
            created_at=datetime.now()
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "workflows"}
