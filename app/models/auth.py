from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class CompanyBase(BaseModel):
    """Base company model."""
    name: str = Field(..., min_length=1, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)


class CompanyCreate(CompanyBase):
    """Company creation with admin user."""
    slug: str = Field(..., min_length=3, max_length=100, pattern=r'^[a-z0-9-]+$')
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8, max_length=72)
    admin_full_name: str = Field(..., min_length=1, max_length=255)


class CompanyUpdate(BaseModel):
    """Company update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    settings: Optional[dict] = None
    max_employees: Optional[int] = None
    max_documents: Optional[int] = None


class CompanyResponse(CompanyBase):
    """Company response model."""
    id: int
    slug: str
    settings: dict
    subscription_tier: str
    max_employees: int
    max_documents: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    """User creation model."""
    password: str = Field(..., min_length=8)
    role: str = Field(default='employee', pattern=r'^(company_admin|hr_manager|employee)$')


class UserLogin(BaseModel):
    """User login model."""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """User update model."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, pattern=r'^(company_admin|hr_manager|employee)$')
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """User response model."""
    id: int
    company_id: int
    role: str
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenRefresh(BaseModel):
    """Token refresh model."""
    refresh_token: str


class InvitationCreate(BaseModel):
    """Invitation creation model."""
    email: EmailStr
    role: str = Field(default='employee', pattern=r'^(company_admin|hr_manager|employee)$')


class InvitationResponse(BaseModel):
    """Invitation response model."""
    id: int
    company_id: int
    email: str
    role: str
    token: str
    invited_by: Optional[int]
    expires_at: datetime
    accepted_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class InvitationAccept(BaseModel):
    """Invitation acceptance model."""
    token: str
    password: str = Field(..., min_length=8, max_length=72)
    full_name: str = Field(..., min_length=1, max_length=255)
