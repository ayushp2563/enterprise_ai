from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.security.auth import get_current_user, require_admin, require_owner
from app.services.auth_service import AuthService


class FakeAuthService:
    def __init__(self, payload=None, principal=None):
        self.payload = payload
        self.principal = principal
        self.requested_principal = None

    def decode_token(self, token):
        return self.payload

    def get_principal(self, user_id, membership_id):
        self.requested_principal = (user_id, membership_id)
        return self.principal


@pytest.mark.asyncio
async def test_authentication_requires_bearer_credentials():
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=None, auth_service=FakeAuthService())

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_access_token_requires_membership_claim():
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="signed-token",
    )
    service = FakeAuthService(payload={"sub": "42", "type": "access"})

    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=credentials, auth_service=service)

    assert exc.value.status_code == 401
    assert service.requested_principal is None


@pytest.mark.asyncio
async def test_authorization_uses_database_membership_role():
    membership_id = str(uuid4())
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="signed-token",
    )
    principal = {
        "id": 42,
        "membership_id": membership_id,
        "company_id": 7,
        "role": "member",
        "is_active": True,
    }
    service = FakeAuthService(
        payload={
            "sub": "42",
            "mid": membership_id,
            "role": "owner",  # Must not be authoritative.
            "type": "access",
        },
        principal=principal,
    )

    current_user = await get_current_user(
        credentials=credentials,
        auth_service=service,
    )

    assert current_user["role"] == "member"
    assert service.requested_principal == (42, membership_id)

    with pytest.raises(HTTPException) as exc:
        await require_admin(current_user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_owner_and_admin_permission_boundaries():
    owner = {"role": "owner", "is_active": True}
    admin = {"role": "admin", "is_active": True}
    member = {"role": "member", "is_active": True}

    assert await require_owner(owner) is owner
    assert await require_admin(owner) is owner
    assert await require_admin(admin) is admin

    with pytest.raises(HTTPException):
        await require_owner(admin)
    with pytest.raises(HTTPException):
        await require_admin(member)


def test_argon2_hashes_complete_password_beyond_bcrypt_limit():
    service = AuthService.__new__(AuthService)
    first = ("a" * 80) + "x"
    second = ("a" * 80) + "y"

    password_hash = service.hash_password(first)

    assert service.verify_password(first, password_hash)
    assert not service.verify_password(second, password_hash)
