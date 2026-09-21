import asyncio

from sqlalchemy import select

from backend.app.database import SessionLocal
from backend.app.models import Project, Scan
from backend.app.seed import seed_india_payments_contingency_scan


def test_contingency_scan_produces_a_real_completed_scan():
    with SessionLocal() as db:
        scan = asyncio.run(seed_india_payments_contingency_scan(db))

        assert scan is not None
        assert scan.status == "completed"
        assert scan.summary["assets_discovered"] >= 40


def test_contingency_scan_is_idempotent():
    with SessionLocal() as db:
        first = asyncio.run(seed_india_payments_contingency_scan(db))
        second = asyncio.run(seed_india_payments_contingency_scan(db))

        assert first.id == second.id


def test_contingency_scan_project_is_queryable_like_any_other_project():
    with SessionLocal() as db:
        asyncio.run(seed_india_payments_contingency_scan(db))

        project = db.scalar(
            select(Project).where(
                Project.name == "India Payments Platform (Pre-Scanned Fallback)"
            )
        )
        assert project is not None

        scan = db.scalar(select(Scan).where(Scan.project_id == project.id))
        assert scan is not None
        assert scan.status == "completed"
