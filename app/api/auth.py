import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.auth import (
    CompanyCreate, CompanyResponse,
    UserLogin, UserResponse,
    TokenResponse, TokenRefresh,
    InvitationAccept, LogoutRequest
)
from app.services.auth_service import get_auth_service, AuthService
from app.security.auth import get_current_user
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def build_token_response(
    auth_service: AuthService,
    user: dict,
    refresh_token: str | None = None,
) -> TokenResponse:
    """Issue an access token and, when needed, a refresh session."""
    access_token = auth_service.create_access_token(
        data={
            "sub": str(user["id"]),
            "mid": str(user["membership_id"]),
        },
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    if refresh_token is None:
        refresh_token = auth_service.create_refresh_session(
            user_id=user["id"],
            membership_id=user["membership_id"],
        )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse(**user),
    )


@router.post("/register-company", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_company(
    company_data: CompanyCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new company with an admin user.
    
    This creates:
    - A new company workspace
    - An admin user account
    - Returns JWT tokens for immediate login
    """
    try:
        # Create company and admin user
        company, user = auth_service.create_company(
            name=company_data.name,
            slug=company_data.slug,
            domain=company_data.domain,
            admin_email=company_data.admin_email,
            admin_password=company_data.admin_password,
            admin_full_name=company_data.admin_full_name
        )
        
        logger.info(f"Company '{company['name']}' registered successfully")
        return build_token_response(auth_service, user)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error registering company: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register company"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate a user and return JWT tokens.
    """
    try:
        # Authenticate user
        user = auth_service.authenticate_user(
            email=credentials.email,
            password=credentials.password,
            organization_slug=credentials.organization_slug,
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info("User logged in successfully")
        return build_token_response(auth_service, user)
        
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token using a refresh token.
    """
    try:
        user, new_refresh_token = auth_service.rotate_refresh_session(
            token_data.refresh_token
        )
        return build_token_response(auth_service, user, new_refresh_token)
        
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/accept-invitation", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def accept_invitation(
    invitation_data: InvitationAccept,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Accept an invitation and create a user account.
    """
    try:
        # Accept invitation and create user
        user, company = auth_service.accept_invitation(
            token=invitation_data.token,
            password=invitation_data.password,
            full_name=invitation_data.full_name
        )
        
        logger.info("User accepted invitation and created membership")
        return build_token_response(auth_service, user)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error accepting invitation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept invitation"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    """
    return UserResponse(**current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    logout_data: LogoutRequest,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Revoke the supplied refresh session."""
    auth_service.revoke_refresh_session(
        logout_data.refresh_token,
        user_id=current_user["id"],
        membership_id=current_user["membership_id"],
    )
    logger.info("User logged out")
    return None
