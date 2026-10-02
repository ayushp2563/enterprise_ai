import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.models.auth import (
    UserResponse, UserUpdate,
    InvitationCreate, InvitationResponse, InvitationCreatedResponse
)
from app.services.user_service import get_user_service, UserService
from app.services.auth_service import get_auth_service, AuthService
from app.security.auth import require_admin, require_owner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    """
    List all users in the company.
    
    Requires: HR Manager or Admin role
    """
    try:
        users = user_service.get_users_by_company(
            company_id=current_user["company_id"],
            skip=skip,
            limit=limit
        )
        return [UserResponse(**user) for user in users]
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )


@router.get("/{user_id:int}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: dict = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get user details by ID.
    
    Requires: HR Manager or Admin role
    """
    try:
        user = user_service.get_user_by_id(
            user_id=user_id,
            company_id=current_user["company_id"]
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(**user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user"
        )


@router.put("/{user_id:int}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: dict = Depends(require_owner),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update user details.
    
    Requires: Admin role
    """
    try:
        if user_update.full_name is not None and user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Users manage their own profile name",
            )

        user = user_service.update_user(
            user_id=user_id,
            company_id=current_user["company_id"],
            full_name=user_update.full_name,
            role=user_update.role,
            is_active=user_update.is_active
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        logger.info(f"User {user_id} updated by {current_user['email']}")
        return UserResponse(**user)
        
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.delete("/{user_id:int}")
async def deactivate_user(
    user_id: int,
    current_user: dict = Depends(require_owner),
    user_service: UserService = Depends(get_user_service)
):
    """
    Deactivate a user (soft delete).
    
    Requires: Admin role
    """
    try:
        # Prevent self-deactivation
        if user_id == current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account"
            )
        
        success = user_service.deactivate_user(
            user_id=user_id,
            company_id=current_user["company_id"]
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        logger.info(f"User {user_id} deactivated by {current_user['email']}")
        return {"message": "User deactivated successfully"}
        
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except Exception as e:
        logger.error(f"Error deactivating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user"
        )


@router.post(
    "/invite",
    response_model=InvitationCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_user(
    invitation: InvitationCreate,
    current_user: dict = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Invite a new user to the company.
    
    Requires: HR Manager or Admin role
    """
    try:
        if current_user["role"] == "admin" and invitation.role != "member":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins may only invite members",
            )

        invitation_data = auth_service.create_invitation(
            company_id=current_user["company_id"],
            email=invitation.email,
            role=invitation.role,
            invited_by=current_user["id"]
        )
        
        logger.info(
            "Invitation created",
            extra={"company_id": current_user["company_id"]},
        )
        
        # In production, send email here with invitation link
        # Example: send_invitation_email(invitation.email, invitation_data["token"])
        
        return InvitationCreatedResponse(**invitation_data)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating invitation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invitation"
        )


@router.get("/invitations/pending", response_model=List[InvitationResponse])
async def list_pending_invitations(
    current_user: dict = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    """
    List all pending invitations for the company.
    
    Requires: HR Manager or Admin role
    """
    try:
        invitations = user_service.get_invitations_by_company(
            company_id=current_user["company_id"]
        )
        return [InvitationResponse(**inv) for inv in invitations]
        
    except Exception as e:
        logger.error(f"Error listing invitations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list invitations"
        )
