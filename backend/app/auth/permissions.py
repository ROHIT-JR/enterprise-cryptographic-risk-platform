from enum import StrEnum


class Role(StrEnum):
    ADMINISTRATOR = "administrator"
    SECURITY_ANALYST = "security_analyst"
    AUDITOR = "auditor"
    VIEWER = "viewer"


class Permission(StrEnum):
    MANAGE_USERS = "manage_users"
    CONFIGURE_ORGANIZATION = "configure_organization"
    VIEW_SCANS = "view_scans"
    RUN_SCANS = "run_scans"
    ANALYZE_RISKS = "analyze_risks"
    CREATE_MIGRATION_PLANS = "create_migration_plans"
    VIEW_REPORTS = "view_reports"
    EXPORT_FINDINGS = "export_findings"
    VIEW_DASHBOARD = "view_dashboard"


ROLE_PERMISSIONS = {
    Role.ADMINISTRATOR: set(Permission),
    Role.SECURITY_ANALYST: {
        Permission.VIEW_SCANS,
        Permission.RUN_SCANS,
        Permission.ANALYZE_RISKS,
        Permission.CREATE_MIGRATION_PLANS,
        Permission.VIEW_REPORTS,
        Permission.EXPORT_FINDINGS,
        Permission.VIEW_DASHBOARD,
    },
    Role.AUDITOR: {
        Permission.VIEW_SCANS,
        Permission.VIEW_REPORTS,
        Permission.EXPORT_FINDINGS,
        Permission.VIEW_DASHBOARD,
    },
    Role.VIEWER: {Permission.VIEW_SCANS, Permission.VIEW_DASHBOARD},
}


def has_permissions(role: str, permissions: set[Permission]) -> bool:
    try:
        granted = ROLE_PERMISSIONS[Role(role)]
    except (ValueError, KeyError):
        return False
    return permissions.issubset(granted)
