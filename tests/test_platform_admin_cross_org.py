import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend.app.api.assets import list_assets
from backend.app.api.audit import list_audit_logs
from backend.app.api.dashboard import dashboard
from backend.app.api.enterprise import enterprise_overview
from backend.app.api.organizations import (
    create_organization,
    delete_organization,
    list_organizations,
)
from backend.app.api.risk import list_risks
from backend.app.api.users import create_user, list_users
from backend.app.auth.dependencies import require_platform_admin, resolve_org_id
from backend.app.auth.permissions import Role
from backend.app.auth.service import AuthenticationService
from backend.app.database import SessionLocal
from backend.app.models import AuditLog, Organization, User
from backend.app.schemas.auth import (
    OrganizationCreate,
    OrganizationDeleteRequest,
    RegisterRequest,
    UserCreate,
)

PASSWORD = "Correct-Horse-Battery-2026"


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


def test_platform_admin_view_as_org_reads_are_scoped_and_audit_logged():
    with SessionLocal() as db:
        platform_admin = _make_platform_admin(db)
        target_org = create_organization(
            OrganizationCreate(name="Viewed Org"), admin=platform_admin, db=db
        )

        def _count_entries() -> int:
            return len(
                list(db.scalars(select(AuditLog).where(AuditLog.organization_id == target_org.id)))
            )

        def _cross_org_actions() -> int:
            count_before = _count_entries()

            board = dashboard(db=db, user=platform_admin, organization_id=target_org.id)
            assert board is not None

            assets_page = list_assets(
                project_id=None,
                asset_type=None,
                severity=None,
                search=None,
                page=1,
                page_size=25,
                organization_id=target_org.id,
                db=db,
                user=platform_admin,
            )
            assert assets_page.items == []

            risks_page = list_risks(
                project_id=None,
                severity=None,
                page=1,
                page_size=25,
                organization_id=target_org.id,
                db=db,
                user=platform_admin,
            )
            assert risks_page.items == []

            overview = enterprise_overview(
                organization_id=target_org.id, user=platform_admin, db=db
            )
            assert overview.users == 0

            logs = list_audit_logs(
                organization_id=target_org.id, limit=100, user=platform_admin, db=db
            )
            assert all(True for _ in logs)

            return _count_entries() - count_before

        new_entries = _cross_org_actions()
        # Each of the four cross-org reads above (dashboard, assets, risks,
        # enterprise overview) records its own audit entry; list_audit_logs
        # itself adds one more for viewing another org's audit trail.
        assert new_entries == 5
        actions = {
            entry.action
            for entry in db.scalars(
                select(AuditLog).where(AuditLog.organization_id == target_org.id)
            )
        }
        assert actions == {
            "organization.created",
            "dashboard.viewed_cross_org",
            "assets.viewed_cross_org",
            "risks.viewed_cross_org",
            "enterprise_overview.viewed_cross_org",
            "audit_log.viewed_cross_org",
        }

        # An ordinary admin's organization_id override is ignored — they only
        # ever see their own org's data, and no cross-org audit entry appears.
        ordinary_admin = _register(db, "Cannot View Cross Org", "cannot-view-admin")
        own_board = dashboard(db=db, user=ordinary_admin, organization_id=target_org.id)
        assert own_board is not None
        assert _count_entries() == 6


def test_platform_admin_cannot_delete_own_organization():
    with SessionLocal() as db:
        platform_admin = _make_platform_admin(db)
        with pytest.raises(HTTPException) as excinfo:
            delete_organization(
                platform_admin.organization_id,
                OrganizationDeleteRequest(confirm_name="Platform Test Org"),
                admin=platform_admin,
                db=db,
            )
        assert excinfo.value.status_code == 400


def test_delete_organization_requires_exact_name_confirmation():
    with SessionLocal() as db:
        platform_admin = _make_platform_admin(db)
        target_org = create_organization(
            OrganizationCreate(name="Doomed Org"), admin=platform_admin, db=db
        )
        with pytest.raises(HTTPException) as excinfo:
            delete_organization(
                target_org.id,
                OrganizationDeleteRequest(confirm_name="wrong name"),
                admin=platform_admin,
                db=db,
            )
        assert excinfo.value.status_code == 400
        assert db.get(Organization, target_org.id) is not None


def test_delete_organization_cascades_and_is_audited_under_the_admins_own_org():
    with SessionLocal() as db:
        platform_admin = _make_platform_admin(db)
        target_org = create_organization(
            OrganizationCreate(name="Doomed Org For Real"), admin=platform_admin, db=db
        )
        member = create_user(
            UserCreate(
                username="doomed-analyst",
                email="doomed-analyst@example.test",
                password=PASSWORD,
                role=Role.SECURITY_ANALYST,
                organization_id=target_org.id,
            ),
            administrator=platform_admin,
            db=db,
        )

        delete_organization(
            target_org.id,
            OrganizationDeleteRequest(confirm_name="Doomed Org For Real"),
            admin=platform_admin,
            db=db,
        )

        assert db.get(Organization, target_org.id) is None
        assert db.get(User, member.id) is None
        assert (
            db.scalar(select(AuditLog).where(AuditLog.organization_id == target_org.id)) is None
        )
        deletion_entry = db.scalar(
            select(AuditLog).where(AuditLog.action == "organization.deleted")
        )
        assert deletion_entry is not None
        assert deletion_entry.organization_id == platform_admin.organization_id
        assert deletion_entry.event_metadata["deleted_organization_id"] == target_org.id

        with pytest.raises(HTTPException) as excinfo:
            delete_organization(
                "not-a-real-org-id",
                OrganizationDeleteRequest(confirm_name="whatever"),
                admin=platform_admin,
                db=db,
            )
        assert excinfo.value.status_code == 404
