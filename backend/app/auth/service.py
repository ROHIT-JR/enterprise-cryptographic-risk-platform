from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.auth.passwords import hash_password, verify_password
from backend.app.auth.permissions import Role
from backend.app.auth.tokens import create_token, decode_token, token_digest
from backend.app.config import get_settings
from backend.app.models import Organization, RefreshToken, User
from backend.app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from backend.app.services.audit_service import record_audit


class AuthenticationService:
    def register(self, db: Session, payload: RegisterRequest) -> TokenResponse:
        organization_name = " ".join(payload.organization_name.split())
        if db.scalar(
            select(Organization).where(func.lower(Organization.name) == organization_name.lower())
        ):
            raise HTTPException(status_code=409, detail="Organization already exists")
        organization = Organization(name=organization_name, industry=payload.industry)
        db.add(organization)
        db.flush()
        user = User(
            organization_id=organization.id,
            username=payload.username.strip(),
            email=payload.email.lower(),
            password_hash=hash_password(payload.password),
            role=Role.ADMINISTRATOR.value,
        )
        db.add(user)
        db.flush()
        record_audit(
            db,
            action="organization.created",
            organization_id=organization.id,
            user=user,
            metadata={"organization": organization.name},
        )
        response = self._issue_pair(db, user)
        db.commit()
        return response

    def login(self, db: Session, payload: LoginRequest) -> TokenResponse:
        organization = db.scalar(
            select(Organization).where(
                func.lower(Organization.name) == payload.organization.lower()
            )
        )
        user = None
        if organization:
            user = db.scalar(
                select(User).where(
                    User.organization_id == organization.id,
                    func.lower(User.username) == payload.username.lower(),
                )
            )
        credentials_valid = user and verify_password(payload.password, user.password_hash)
        if not user or not user.is_active or not credentials_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid organization, username, or password",
            )
        record_audit(
            db,
            action="user.login",
            organization_id=user.organization_id,
            user=user,
            metadata={},
        )
        response = self._issue_pair(db, user)
        db.commit()
        return response

    def refresh(self, db: Session, token: str) -> TokenResponse:
        try:
            claims = decode_token(token)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
        stored = db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_digest(token))
        )
        now = datetime.now(UTC)
        if (
            claims.get("type") != "refresh"
            or not stored
            or stored.revoked_at
            or stored.expires_at.replace(tzinfo=UTC) <= now
        ):
            raise HTTPException(status_code=401, detail="Refresh token is expired or revoked")
        user = db.get(User, claims["sub"])
        if not user or not user.is_active or user.organization_id != claims["org"]:
            raise HTTPException(status_code=401, detail="Refresh token user is unavailable")
        stored.revoked_at = now
        response = self._issue_pair(db, user)
        db.commit()
        return response

    def revoke(self, db: Session, token: str, user: User) -> None:
        stored = db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_digest(token),
                RefreshToken.user_id == user.id,
            )
        )
        if stored and not stored.revoked_at:
            stored.revoked_at = datetime.now(UTC)
        record_audit(
            db,
            action="user.logout",
            organization_id=user.organization_id,
            user=user,
            metadata={},
        )
        db.commit()

    def _issue_pair(self, db: Session, user: User) -> TokenResponse:
        config = get_settings()
        access, _, _ = create_token(
            user_id=user.id,
            organization_id=user.organization_id,
            role=user.role,
            token_type="access",
        )
        refresh, expires, _ = create_token(
            user_id=user.id,
            organization_id=user.organization_id,
            role=user.role,
            token_type="refresh",
        )
        db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=token_digest(refresh),
                expires_at=expires,
            )
        )
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=config.access_token_minutes * 60,
            user=UserResponse.model_validate(user),
        )
