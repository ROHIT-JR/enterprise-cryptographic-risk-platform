from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.project import Project
from backend.app.models.scan import Scan


def get_or_create_project(
    db: Session,
    *,
    name: str,
    criticality: str = "medium",
    description: str | None = None,
    organization_id: str,
) -> Project:
    normalized = " ".join(name.split())
    project = db.scalar(
        select(Project).where(
            Project.organization_id == organization_id, Project.name == normalized
        )
    )
    if project:
        if criticality and project.criticality != criticality:
            project.criticality = criticality
        if description and not project.description:
            project.description = description
        db.flush()
        return project
    project = Project(
        organization_id=organization_id,
        name=normalized,
        criticality=criticality,
        description=description,
    )
    db.add(project)
    db.flush()
    return project


def create_scan(
    db: Session,
    *,
    project: Project,
    source_type: str,
    target: str,
) -> Scan:
    scan = Scan(
        organization_id=project.organization_id,
        project_id=project.id,
        source_type=source_type,
        target=target,
        status="queued",
        progress=0,
    )
    db.add(scan)
    db.flush()
    return scan
