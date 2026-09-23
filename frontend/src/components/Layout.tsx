import {
  Bell,
  Boxes,
  Building2,
  Atom,
  BrainCircuit,
  CircleDotDashed,
  GitBranch,
  LayoutDashboard,
  Landmark,
  Menu,
  LogOut,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  ScrollText,
  Radar,
  Route,
  ScanLine,
  Search,
  ShieldCheck,
  Sparkles,
  Sun,
  X,
  Activity,
  Gauge,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useTheme } from "../hooks/useTheme";
import type { UserRole } from "../types/api";

type NavSection = {
  label: string;
  items: {
    to: string;
    label: string;
    icon: React.ElementType;
    roles: UserRole[];
  }[];
};

const navSections: NavSection[] = [
  {
    label: "Discovery",
    items: [
      { to: "/",        label: "Dashboard",       icon: LayoutDashboard, roles: ["administrator", "security_analyst", "auditor", "viewer"] },
      { to: "/upload",  label: "Upload Center",   icon: ScanLine,        roles: ["administrator", "security_analyst"] },
      { to: "/assets",  label: "Asset Explorer",  icon: Boxes,           roles: ["administrator", "security_analyst", "auditor", "viewer"] },
      { to: "/graph",   label: "Knowledge Graph", icon: GitBranch,       roles: ["administrator", "security_analyst", "auditor", "viewer"] },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { to: "/risks",         label: "Risk Analysis",     icon: ShieldCheck,    roles: ["administrator", "security_analyst", "auditor", "viewer"] },
      { to: "/quantum-risk",  label: "Quantum Risk",      icon: Atom,           roles: ["administrator", "security_analyst", "auditor", "viewer"] },
      { to: "/intelligence",  label: "Asset Intelligence",icon: BrainCircuit,   roles: ["administrator", "security_analyst", "auditor", "viewer"] },
      { to: "/blast-radius",  label: "Blast Radius",      icon: CircleDotDashed,roles: ["administrator", "security_analyst", "auditor", "viewer"] },
    ],
  },
  {
    label: "Migration",
    items: [
      { to: "/migration", label: "Migration Planner",    icon: Route,    roles: ["administrator", "security_analyst"] },
      { to: "/pqc",       label: "PQC Recommendations",  icon: Sparkles, roles: ["administrator", "security_analyst"] },
      { to: "/benchmarks", label: "PQC Benchmarks",      icon: Gauge,    roles: ["administrator", "security_analyst", "auditor", "viewer"] },
    ],
  },
  {
    label: "Enterprise",
    items: [
      { to: "/operations", label: "Security Operations", icon: Radar,       roles: ["administrator", "security_analyst"] },
      { to: "/admin",      label: "Administration",      icon: Building2,   roles: ["administrator"] },
      { to: "/audit",      label: "Audit & Reports",     icon: ScrollText,  roles: ["administrator", "auditor"] },
      { to: "/validation", label: "Research Validation", icon: Activity,    roles: ["administrator", "security_analyst", "auditor", "viewer"] },
      { to: "/compliance", label: "NQM Compliance",      icon: Landmark,    roles: ["administrator", "security_analyst", "auditor", "viewer"] },
    ],
  },
];

function Brand({ collapsed }: { collapsed?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <div
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg"
        style={{ background: "var(--accent)" }}
      >
        <Radar className="h-4 w-4 text-white" strokeWidth={1.75} />
      </div>
      {!collapsed && (
        <div className="min-w-0">
          <p className="truncate font-mono text-xs font-bold tracking-widest" style={{ color: "var(--text-primary)" }}>
            ECDAT-X
          </p>
          <p className="truncate font-mono text-[9px] uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
            Crypto Intel Engine
          </p>
        </div>
      )}
    </div>
  );
}

function SidebarContent({
  close,
  role,
  collapsed,
  onToggleCollapse,
}: {
  close?: () => void;
  role: UserRole;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}) {
  return (
    <div
      className="flex h-full flex-col"
      style={{ background: "var(--bg-sidebar)", borderRight: "1px solid var(--border)" }}
    >
      {/* Brand header */}
      <div className="flex h-12 items-center justify-between border-b px-3" style={{ borderColor: "var(--border)" }}>
        <Brand collapsed={collapsed} />
        {onToggleCollapse && (
          <button
            className="hidden shrink-0 rounded p-1.5 transition hover:bg-[var(--bg-hover)] lg:flex"
            style={{ color: "var(--text-muted)" }}
            onClick={onToggleCollapse}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <PanelLeftOpen className="h-3.5 w-3.5" /> : <PanelLeftClose className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>

      {/* Nav groups */}
      <div className="flex-1 overflow-y-auto px-2 py-3 space-y-4">
        <nav aria-label="Primary navigation" className="space-y-4">
          {navSections.map((section) => {
            const visibleItems = section.items.filter((item) => item.roles.includes(role));
            if (visibleItems.length === 0) return null;
            return (
              <div key={section.label}>
                {!collapsed && (
                  <p
                    className="mb-1 px-2.5 font-mono text-[9px] font-semibold uppercase tracking-widest"
                    style={{ color: "var(--text-muted)" }}
                  >
                    {section.label}
                  </p>
                )}
                <div className="space-y-0.5">
                  {visibleItems.map(({ to, label, icon: Icon }) => (
                    <NavLink
                      key={to}
                      to={to}
                      end={to === "/"}
                      onClick={close}
                      title={collapsed ? label : undefined}
                      className={({ isActive }) =>
                        `interactive group flex items-center gap-2.5 rounded-lg py-1.5 text-xs ${
                          collapsed ? "justify-center px-2" : "px-2.5"
                        } ${isActive ? "nav-active font-semibold" : "font-normal hover:bg-[var(--bg-hover)]"}`
                      }
                      style={({ isActive }) => ({
                        color: isActive ? "var(--text-primary)" : "var(--text-muted)",
                      })}
                    >
                      <Icon className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />
                      {!collapsed && <span className="truncate">{label}</span>}
                    </NavLink>
                  ))}
                </div>
              </div>
            );
          })}
        </nav>
      </div>

      {/* System status footer */}
      <div className="border-t p-3" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center gap-2 text-[11px] font-mono" style={{ color: "var(--text-secondary)" }}>
          <span className="relative flex h-1.5 w-1.5 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75" style={{ background: "var(--risk-low)" }} />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full" style={{ background: "var(--risk-low)" }} />
          </span>
          {!collapsed && (
            <>
              <span className="font-semibold" style={{ color: "var(--text-primary)" }}>Engine Online</span>
              <span className="ml-auto text-[9px] uppercase" style={{ color: "var(--text-muted)" }}>v0.3.0</span>
            </>
          )}
        </div>
        {!collapsed && (
          <p className="mt-1 font-mono text-[9px]" style={{ color: "var(--text-muted)" }}>Isolation: Tenant Org-1</p>
        )}
      </div>
    </div>
  );
}

export function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  if (!user) return null;
  return (
    <div className="min-h-screen font-sans" style={{ background: "var(--bg-app)", color: "var(--text-primary)" }}>
      {/* Desktop sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 hidden flex-col transition-[width] duration-200 lg:flex ${
          collapsed ? "w-16" : "w-56"
        }`}
      >
        <SidebarContent role={user.role} collapsed={collapsed} onToggleCollapse={() => setCollapsed((v) => !v)} />
      </aside>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button className="absolute inset-0 bg-black/60 backdrop-blur-xs" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />
          <aside className="relative flex h-full w-60 flex-col shadow-2xl">
            <button
              className="absolute right-2 top-2.5 z-10 rounded p-1.5 transition hover:bg-[var(--bg-hover)]"
              style={{ color: "var(--text-muted)" }}
              onClick={() => setMobileOpen(false)}
              aria-label="Close navigation"
            >
              <X className="h-4 w-4" />
            </button>
            <SidebarContent close={() => setMobileOpen(false)} role={user.role} />
          </aside>
        </div>
      )}

      <div className={`transition-[padding] duration-200 ${collapsed ? "lg:pl-16" : "lg:pl-56"}`}>
        {/* Top header */}
        <header
          className="sticky top-0 z-20 flex h-12 items-center gap-3 px-4 md:px-6"
          style={{ background: "var(--bg-topbar)", borderBottom: "1px solid var(--border)" }}
        >
          <button
            className="rounded p-1 transition hover:bg-[var(--bg-hover)] lg:hidden"
            style={{ color: "var(--text-secondary)" }}
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation"
          >
            <Menu className="h-4 w-4" />
          </button>

          {/* Search */}
          <div className="relative hidden max-w-xs flex-1 md:block">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
            <input
              type="text"
              placeholder="Search assets, findings, reports…"
              className="field !py-1.5 pl-8 text-xs"
              aria-label="Search"
            />
          </div>

          <div className="ml-auto flex items-center gap-1.5">
            <button
              className="rounded-lg p-1.5 transition hover:bg-[var(--bg-hover)]"
              style={{ color: "var(--text-secondary)" }}
              aria-label="Notifications"
              title="Notifications"
            >
              <Bell className="h-3.5 w-3.5" strokeWidth={1.75} />
            </button>

            <button
              className="rounded-lg p-1.5 transition hover:bg-[var(--bg-hover)]"
              style={{ color: "var(--text-secondary)" }}
              onClick={toggleTheme}
              aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
              title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            >
              {theme === "dark" ? <Sun className="h-3.5 w-3.5" strokeWidth={1.75} /> : <Moon className="h-3.5 w-3.5" strokeWidth={1.75} />}
            </button>

            <span
              className="ml-1 hidden rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider md:inline-block"
              style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
            >
              {user.role.replace("_", " ")}
            </span>
            <div
              className="flex h-6 w-6 items-center justify-center rounded-full font-mono text-[10px] font-bold"
              style={{ background: "var(--accent)", color: "var(--text-on-accent)" }}
            >
              {user.username.slice(0, 2).toUpperCase()}
            </div>
            <button
              onClick={() => void logout()}
              className="rounded-lg p-1.5 transition hover:bg-[var(--bg-hover)]"
              style={{ color: "var(--text-muted)" }}
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut className="h-3.5 w-3.5" strokeWidth={1.75} />
            </button>
          </div>
        </header>

        <main className="min-h-[calc(100vh-3rem)] p-4 md:p-6 lg:p-6">
          <div className="mx-auto max-w-[1440px]"><Outlet /></div>
        </main>
      </div>
    </div>
  );
}
