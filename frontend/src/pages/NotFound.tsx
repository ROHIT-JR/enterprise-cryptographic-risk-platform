import { ArrowLeft, ShieldQuestion } from "lucide-react";
import { Link } from "react-router-dom";
import { Card } from "../components/ui";

export function NotFound() {
  return (
    <Card className="page-enter mx-auto mt-20 max-w-xl p-10 text-center">
      <ShieldQuestion className="mx-auto h-10 w-10" style={{ color: "var(--accent)" }} strokeWidth={1.5} />
      <p className="mt-6 font-mono text-[10px] font-bold uppercase tracking-[0.22em]" style={{ color: "var(--accent)" }}>404 Error</p>
      <h1 className="mt-2 text-2xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>This workspace view does not exist</h1>
      <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>Return to the cryptographic posture dashboard.</p>
      <Link
        to="/"
        className="interactive mt-6 inline-flex items-center gap-2 rounded-lg border px-4 py-2 font-mono text-xs font-semibold"
        style={{ borderColor: "var(--border)", background: "var(--bg-card)", color: "var(--text-secondary)" }}
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Return to Dashboard
      </Link>
    </Card>
  );
}
