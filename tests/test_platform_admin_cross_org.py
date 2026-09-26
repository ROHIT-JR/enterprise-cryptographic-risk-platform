import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend.app.api.organizations import create_organization, list_organizations
from backend.app.api.users import create_user, list_users
from backend.app.auth.dependencies import require_platform_admin, resolve_org_id
from backend.app.auth.permissions import Role
from backend.app.auth.service import AuthenticationService
from backend.app.database import SessionLocal
from backend.app.models import Organization, User
from backend.app.schemas.auth import OrganizationCreate, RegisterRequest, UserCreate

PASSWORD = "Correct-Horse-Battery-2026"  # gitleaks:allow — test fixture, not a real credential


def _register(db, organization: str, username: str) -> User:
    AuthenticationService().register(
        db,
        RegisterRequest(
            organization_name=organization,
            industry="Technology",
            username=username,
            email=f"{username}@example.test",
            password=PASSWORD,
        ),
    )
    return db.scalar(select(User).where(User.username == username))


def _make_platform_admin(db) -> User:
    user = _register(db, "Platform Test Org", "platform-test-admin")
    user.is_platform_admin = True
    db.commit()
    db.refresh(user)
    return user


def test_require_platform_admin_gate():
    with SessionLocal() as db:
        ordinary_admin = _register(db, "Ordinary Org", "ordinary-admin")
        with pytest.raises(HTTPException) as excinfo:
            require_platform_admin(user=ordinary_admin)
        assert excinfo.value.status_code == 403

        platform_admin = _make_platform_admin(db)
        assert require_platform_admin(user=platform_admin) is platform_admin


def test_resolve_org_id_only_grants_override_to_platform_admin():
    with SessionLocal() as db:
        ordinary_admin = _register(db, "Resolve Org", "resolve-admin")
        platform_admin = _make_platform_admin(db)

        # Non-admin always gets their own org, regardless of what they ask for.
        assert resolve_org_id(ordinary_admin, "some-other-org-id") == ordinary_admin.organization_id
        assert resolve_org_id(ordinary_admin, None) == ordinary_admin.organization_id

        # Platform admin gets the override only when they explicitly ask for one.
        assert resolve_org_id(platform_admin, None) == platform_admin.organization_id
        assert resolve_org_id(platform_admin, "target-org-id") == "target-org-id"


def test_platform_admin_can_create_organization_and_duplicate_is_rejected():
    with SessionLocal() as db:
        platform_admin = _make_platform_admin(db)
        created = create_organization(
            OrganizationCreate(name="Brand New Bank", industry="Financial Services"),
            admin=platform_admin,
            db=db,
        )
        assert created.name == "Brand New Bank"
        assert db.get(Organization, created.id) is not None

        with pytest.raises(HTTPException) as excinfo:
            create_organization(
                OrganizationCreate(name="Brand New Bank"), admin=platform_admin, db=db
            )
        assert excinfo.value.status_code == 409

        listed = list_organizations(_=platform_admin, db=db)
        assert any(org.name == "Brand New Bank" for org in listed)


def test_platform_admin_creates_user_in_another_org_ordinary_admin_cannot():
    with SessionLocal() as db:
        platform_admin = _make_platform_admin(db)
        target_org = create_organization(
            OrganizationCreate(name="Target Org For Users"), admin=platform_admin, db=db
        )

        cross_org_user = create_user(
            UserCreate(
                username="target-analyst",
                email="target-analyst@example.test",
                password=PASSWORD,
                role=Role.SECURITY_ANALYST,
                organization_id=target_org.id,
            ),
            administrator=platform_admin,
            db=db,
        )
        assert cross_org_user.organization_id == target_org.id

        listed = list_users(organization_id=target_org.id, administrator=platform_admin, db=db)
        assert {u.username for u in listed} == {"target-analyst"}

        # An ordinary admin's organization_id is silently ignored — they can
        # only ever create users in their own org, never anyone else's.
        ordinary_admin = _register(db, "Cannot Cross Org", "cannot-cross-admin")
        escaped_user = create_user(
            UserCreate(
                username="should-stay-local",
                email="should-stay-local@example.test",
                password=PASSWORD,
                role=Role.VIEWER,
                organization_id=target_org.id,
            ),
            administrator=ordinary_admin,
            db=db,
        )
        assert escaped_user.organization_id == ordinary_admin.organization_id
        assert escaped_user.organization_id != target_org.id

        # Same for listing — the organization_id query param is ignored for them.
        own_org_listing = list_users(
            organization_id=target_org.id, administrator=ordinary_admin, db=db
        )
        assert all(u.organization_id == ordinary_admin.organization_id for u in own_org_listing)
