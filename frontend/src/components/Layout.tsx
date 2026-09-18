import {
  Boxes,
  Building2,
  Atom,
  BrainCircuit,
  CircleDotDashed,
  GitBranch,
  LayoutDashboard,
  Menu,
  LogOut,
  ScrollText,
  Radar,
  Route,
  ScanLine,
  ShieldCheck,
  Sparkles,
  X,
  Activity,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
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
    ],
  },
  {
    label: "Enterprise",
    items: [
      { to: "/operations", label: "Security Operations", icon: Radar,       roles: ["administrator", "security_analyst"] },
      { to: "/admin",      label: "Administration",      icon: Building2,   roles: ["administrator"] },
      { to: "/audit",      label: "Audit & Reports",     icon: ScrollText,  roles: ["administrator", "auditor"] },
      { to: "/validation", label: "Research Validation", icon: Activity,    roles: ["administrator", "security_analyst", "auditor", "viewer"] },
    ],
  },
];

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="grid h-9 w-9 place-items-center rounded-xl border border-blue-200 bg-blue-50">
        <Radar className="h-4.5 w-4.5 text-blue-600" />
      </div>
      <div>
        <p className="text-[14px] font-extrabold tracking-[0.14em] text-slate-900">ECDAT-X</p>
        <p className="text-[9px] font-semibold uppercase tracking-[0.14em] text-slate-400">Crypto intelligence</p>
      </div>
    </div>
  );
}

function SidebarContent({ close, role }: { close?: () => void; role: UserRole }) {
  return (
    <>
      <div className="border-b border-slate-100 px-5 py-5"><Brand /></div>
      <div className="flex-1 overflow-y-auto px-3 py-4">
        <nav className="space-y-4" aria-label="Primary navigation">
          {navSections.map((section) => {
            const visibleItems = section.items.filter((item) => item.roles.includes(role));
            if (visibleItems.length === 0) return null;
            return (
              <div key={section.label}>
                <p className="mb-1.5 px-3 text-[9.5px] font-bold uppercase tracking-[0.20em] text-slate-400">
                  {section.label}
                </p>
                <div className="space-y-0.5">
                  {visibleItems.map(({ to, label, icon: Icon }) => (
                    <NavLink
                      key={to}
                      to={to}
                      end={to === "/"}
                      onClick={close}
                      className={({ isActive }) =>
                        `group flex items-center gap-2.5 rounded-lg py-2 pr-3 text-[13px] font-medium transition ${
                          isActive
                            ? "border-l-2 border-blue-500 bg-blue-50 pl-[14px] text-blue-700"
                            : "pl-4 text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                        }`
                      }
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      {label}
                    </NavLink>
                  ))}
                </div>
              </div>
            );
          })}
        </nav>
      </div>
      {/* System status footer */}
      <div className="m-3 rounded-xl border border-slate-200 bg-slate-50 p-3.5">
        <div className="flex items-center gap-2 text-xs font-medium text-slate-600">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
          Discovery engine ready
        </div>
        <p className="mt-1.5 text-[10px] leading-4 text-slate-400">Phase 3 · enterprise hardened</p>
      </div>
    </>
  );
}

export function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, logout } = useAuth();
  if (!user) return null;
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-slate-200 bg-white lg:flex">
        <SidebarContent role={user.role} />
      </aside>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button className="absolute inset-0 bg-slate-900/30" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />
          <aside className="relative flex h-full w-64 flex-col border-r border-slate-200 bg-white shadow-xl">
            <button className="absolute right-3 top-4 rounded-lg p-2 text-slate-400 hover:bg-slate-100" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
              <X className="h-5 w-5" />
            </button>
            <SidebarContent close={() => setMobileOpen(false)} role={user.role} />
          </aside>
        </div>
      )}

      <div className="lg:pl-60">
        {/* Top header */}
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-slate-200 bg-white px-5 md:px-8 lg:px-8">
          <button className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
            <Menu className="h-5 w-5" />
          </button>
          <div className="hidden items-center gap-1.5 text-xs text-slate-400 lg:flex">
            <span>Organization workspace</span>
            <span className="text-slate-300">/</span>
            <span className="text-slate-600">Cryptographic posture</span>
          </div>
          <div className="ml-auto flex items-center gap-2.5">
            <span className="hidden rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500 sm:inline-flex">
              {user.role.replace("_", " ")}
            </span>
            <div className="grid h-8 w-8 place-items-center rounded-full bg-blue-600 text-xs font-extrabold text-white">
              {user.username.slice(0, 2).toUpperCase()}
            </div>
            <button onClick={() => void logout()} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label="Sign out">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </header>

        <main className="min-h-[calc(100vh-3.5rem)] px-5 py-8 md:px-8 lg:px-8 lg:py-8">
          <div className="mx-auto max-w-[1440px]"><Outlet /></div>
        </main>
      </div>
    </div>
  );
}
