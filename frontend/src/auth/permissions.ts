import type { UserRole } from "../types/api";

export type Permission =
  | "manage_users"
  | "configure_organization"
  | "view_scans"
  | "run_scans"
  | "analyze_risks"
  | "create_migration_plans"
  | "view_reports"
  | "export_findings"
  | "view_dashboard";

const ALL_PERMISSIONS: Permission[] = [
  "manage_users",
  "configure_organization",
  "view_scans",
  "run_scans",
  "analyze_risks",
  "create_migration_plans",
  "view_reports",
  "export_findings",
  "view_dashboard",
];

/** Mirrors backend/app/auth/permissions.py:ROLE_PERMISSIONS. UI-only — the
 * backend is the real enforcement point; this just decides what to show. */
const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  administrator: ALL_PERMISSIONS,
  security_analyst: [
    "view_scans",
    "run_scans",
    "analyze_risks",
    "create_migration_plans",
    "view_reports",
    "export_findings",
    "view_dashboard",
  ],
  auditor: ["view_scans", "view_reports", "export_findings", "view_dashboard"],
  viewer: ["view_scans", "view_dashboard"],
};

export function hasPermission(role: UserRole, permission: Permission): boolean {
  return ROLE_PERMISSIONS[role]?.includes(permission) ?? false;
}

export function hasAnyRole(role: UserRole, allowed: UserRole[]): boolean {
  return allowed.includes(role);
}
