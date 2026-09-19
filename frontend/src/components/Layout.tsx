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
  Gauge,
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
    ],
  },
];

function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-7 w-7 items-center justify-center rounded border border-zinc-700 bg-zinc-900 text-zinc-100">
        <Radar className="h-4 w-4 text-indigo-400" strokeWidth={1.75} />
      </div>
      <div>
        <p className="font-mono text-xs font-bold tracking-widest text-zinc-100">ECDAT-X</p>
        <p className="font-mono text-[9px] uppercase tracking-wider text-zinc-500">Crypto Intel Engine</p>
      </div>
    </div>
  );
}

function SidebarContent({ close, role }: { close?: () => void; role: UserRole }) {
  return (
    <div className="flex h-full flex-col bg-[#0c0d0e] text-zinc-400 border-r border-zinc-800/80">
      {/* Brand header */}
      <div className="flex h-12 items-center border-b border-zinc-800/80 px-4">
        <Brand />
      </div>

      {/* Nav groups */}
      <div className="flex-1 overflow-y-auto px-2 py-3 space-y-4">
        <nav aria-label="Primary navigation" className="space-y-4">
          {navSections.map((section) => {
            const visibleItems = section.items.filter((item) => item.roles.includes(role));
            if (visibleItems.length === 0) return null;
            return (
              <div key={section.label}>
                <p className="mb-1 px-2.5 font-mono text-[9px] font-semibold uppercase tracking-widest text-zinc-500">
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
                        `group flex items-center gap-2.5 rounded-sm py-1.5 pr-2.5 text-xs transition ${
                          isActive
                            ? "border-l-2 border-indigo-500 bg-zinc-800/70 pl-[10px] text-zinc-100 font-semibold"
                            : "pl-3 text-zinc-400 hover:bg-zinc-800/30 hover:text-zinc-200 font-normal"
                        }`
                      }
                    >
                      <Icon className="h-3.5 w-3.5 shrink-0 text-zinc-400 group-hover:text-zinc-200" strokeWidth={1.75} />
                      <span className="truncate">{label}</span>
                    </NavLink>
                  ))}
                </div>
              </div>
            );
          })}
        </nav>
      </div>

      {/* System status footer */}
      <div className="border-t border-zinc-800/80 p-3 bg-[#08090a]">
        <div className="flex items-center gap-2 text-[11px] font-mono text-zinc-300">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
          </span>
          <span className="font-semibold text-zinc-200">Engine Online</span>
          <span className="ml-auto text-[9px] text-zinc-500 uppercase">v0.3.0</span>
        </div>
        <p className="mt-1 font-mono text-[9px] text-zinc-500">Isolation: Tenant Org-1</p>
      </div>
    </div>
  );
}

export function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, logout } = useAuth();
  if (!user) return null;
  return (
    <div className="min-h-screen bg-[#fafafa] text-zinc-950 font-sans">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-56 flex-col lg:flex">
        <SidebarContent role={user.role} />
      </aside>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button className="absolute inset-0 bg-black/60 backdrop-blur-xs" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />
          <aside className="relative flex h-full w-60 flex-col shadow-2xl">
            <button className="absolute right-2 top-2.5 z-10 rounded p-1.5 text-zinc-400 hover:text-white" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
              <X className="h-4 w-4" />
            </button>
            <SidebarContent close={() => setMobileOpen(false)} role={user.role} />
          </aside>
        </div>
      )}

      <div className="lg:pl-56">
        {/* Top header */}
        <header className="sticky top-0 z-20 flex h-12 items-center justify-between border-b border-zinc-200 bg-white px-4 md:px-6">
          <button className="rounded p-1 text-zinc-600 hover:bg-zinc-100 lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
            <Menu className="h-4 w-4" />
          </button>
          <div className="hidden items-center gap-1.5 font-mono text-xs text-zinc-500 lg:flex">
            <span className="text-zinc-600">Organization workspace</span>
            <span className="text-zinc-300">/</span>
            <span className="font-semibold text-zinc-900">Cryptographic posture</span>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <span className="rounded border border-zinc-200 bg-zinc-50 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-zinc-600">
              {user.role.replace("_", " ")}
            </span>
            <div className="flex h-6 w-6 items-center justify-center rounded bg-zinc-900 font-mono text-[10px] font-bold text-white">
              {user.username.slice(0, 2).toUpperCase()}
            </div>
            <button onClick={() => void logout()} className="rounded p-1 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700" title="Sign out" aria-label="Sign out">
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
