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
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import type { UserRole } from "../types/api";

const navigation = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, roles: ["administrator", "security_analyst", "auditor", "viewer"] },
  { to: "/operations", label: "Security operations", icon: Radar, roles: ["administrator", "security_analyst"] },
  { to: "/admin", label: "Administration", icon: Building2, roles: ["administrator"] },
  { to: "/audit", label: "Audit & reports", icon: ScrollText, roles: ["administrator", "auditor"] },
  { to: "/upload", label: "Upload center", icon: ScanLine, roles: ["administrator", "security_analyst"] },
  { to: "/assets", label: "Asset explorer", icon: Boxes, roles: ["administrator", "security_analyst", "auditor", "viewer"] },
  { to: "/graph", label: "Knowledge graph", icon: GitBranch, roles: ["administrator", "security_analyst", "auditor", "viewer"] },
  { to: "/risks", label: "Risk analysis", icon: ShieldCheck, roles: ["administrator", "security_analyst", "auditor", "viewer"] },
  { to: "/quantum-risk", label: "Quantum risk", icon: Atom, roles: ["administrator", "security_analyst", "auditor", "viewer"] },
  { to: "/intelligence", label: "Asset intelligence", icon: BrainCircuit, roles: ["administrator", "security_analyst", "auditor", "viewer"] },
  { to: "/blast-radius", label: "Blast radius", icon: CircleDotDashed, roles: ["administrator", "security_analyst", "auditor", "viewer"] },
  { to: "/migration", label: "Migration planner", icon: Route, roles: ["administrator", "security_analyst"] },
  { to: "/pqc", label: "PQC recommendations", icon: Sparkles, roles: ["administrator", "security_analyst"] },
];

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="relative grid h-10 w-10 place-items-center overflow-hidden rounded-xl border border-brand-300/30 bg-brand-400/10 shadow-glow">
        <Radar className="h-5 w-5 text-brand-300" />
        <span className="absolute inset-x-1/2 top-0 h-full w-px bg-gradient-to-b from-transparent via-brand-300/70 to-transparent" />
      </div>
      <div>
        <p className="text-[15px] font-extrabold tracking-[0.16em] text-white">ECDAT-X</p>
        <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-500">Crypto intelligence</p>
      </div>
    </div>
  );
}

function SidebarContent({ close, role }: { close?: () => void; role: UserRole }) {
  return (
    <>
      <div className="border-b border-white/[0.07] px-6 py-6"><Brand /></div>
      <div className="flex-1 overflow-y-auto px-3 py-6">
        <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-600">Workspace</p>
        <nav className="space-y-1.5" aria-label="Primary navigation">
          {navigation.filter((item) => item.roles.includes(role)).map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={close}
              className={({ isActive }) =>
                `group flex items-center gap-3 rounded-xl px-3.5 py-3 text-sm font-medium transition ${
                  isActive
                    ? "bg-brand-400/10 text-brand-300 ring-1 ring-inset ring-brand-300/15"
                    : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-100"
                }`
              }
            >
              <Icon className="h-[18px] w-[18px]" />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
      <div className="m-4 rounded-xl border border-white/[0.06] bg-black/15 p-4">
        <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
          </span>
          Discovery engine ready
        </div>
        <p className="mt-2 text-[11px] leading-4 text-slate-600">Phase 3 · enterprise hardened</p>
      </div>
    </>
  );
}

export function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, logout } = useAuth();
  if (!user) return null;
  return (
    <div className="min-h-screen bg-ink-950 text-slate-100">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-white/[0.07] bg-ink-900/95 backdrop-blur-xl lg:flex">
        <SidebarContent role={user.role} />
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button className="absolute inset-0 bg-black/70" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />
          <aside className="relative flex h-full w-72 flex-col border-r border-white/10 bg-ink-900 shadow-2xl">
            <button className="absolute right-3 top-4 rounded-lg p-2 text-slate-400 hover:bg-white/5" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
              <X className="h-5 w-5" />
            </button>
            <SidebarContent close={() => setMobileOpen(false)} role={user.role} />
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-white/[0.06] bg-ink-950/80 px-5 backdrop-blur-xl md:px-8 lg:px-10">
          <button className="rounded-lg p-2 text-slate-300 hover:bg-white/5 lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
            <Menu className="h-5 w-5" />
          </button>
          <div className="hidden items-center gap-2 text-xs text-slate-500 lg:flex">
            <span>Organization workspace</span><span className="text-slate-700">/</span><span className="text-slate-300">Cryptographic posture</span>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <span className="hidden rounded-full border border-white/[0.07] bg-white/[0.03] px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400 sm:inline-flex">{user.role.replace("_", " ")}</span>
            <div className="grid h-8 w-8 place-items-center rounded-full bg-gradient-to-br from-brand-300 to-blue-500 text-xs font-extrabold text-ink-950">{user.username.slice(0, 2).toUpperCase()}</div>
            <button onClick={() => void logout()} className="rounded-lg p-2 text-slate-500 hover:bg-white/5 hover:text-slate-200" aria-label="Sign out"><LogOut className="h-4 w-4" /></button>
          </div>
        </header>
        <main className="relative min-h-[calc(100vh-4rem)] overflow-hidden px-5 py-8 md:px-8 lg:px-10 lg:py-10">
          <div className="pointer-events-none absolute right-[-12rem] top-[-18rem] h-[35rem] w-[35rem] rounded-full bg-brand-500/[0.055] blur-3xl" />
          <div className="relative mx-auto max-w-[1500px]"><Outlet /></div>
        </main>
      </div>
    </div>
  );
}
