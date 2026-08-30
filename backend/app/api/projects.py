from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_permissions
from backend.app.auth.permissions import Permission
from backend.app.database import get_db
from backend.app.models import Project, User
from backend.app.schemas.project import ProjectCreate, ProjectResponse
from backend.app.services.tenant_service import resolve_organization_id

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Project]:
    statement = select(Project)
    if isinstance(user, User):
        statement = statement.where(Project.organization_id == user.organization_id)
    return list(db.scalars(statement.order_by(Project.updated_at.desc())))


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.RUN_SCANS))],
)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    organization_id = resolve_organization_id(db, user)
    existing = db.scalar(
        select(Project).where(
            Project.organization_id == organization_id,
            Project.name == payload.name.strip(),
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="A project with this name already exists")
    project = Project(organization_id=organization_id, **payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    project = db.get(Project, project_id)
    if not project or (
        isinstance(user, User) and project.organization_id != user.organization_id
    ):
        raise HTTPException(status_code=404, detail="Project not found")
    return project
