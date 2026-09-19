import { ArrowLeft, ShieldQuestion } from "lucide-react";
import { Link } from "react-router-dom";
import { Card } from "../components/ui";

export function NotFound() {
  return (
    <Card className="mx-auto mt-20 max-w-xl p-10 text-center">
      <ShieldQuestion className="mx-auto h-10 w-10 text-indigo-600" strokeWidth={1.5} />
      <p className="mt-6 font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-indigo-600">404 Error</p>
      <h1 className="mt-2 text-2xl font-bold tracking-tight text-zinc-950">This workspace view does not exist</h1>
      <p className="mt-2 text-sm text-zinc-500">Return to the cryptographic posture dashboard.</p>
      <Link
        to="/"
        className="mt-6 inline-flex items-center gap-2 rounded border border-zinc-200 bg-white px-4 py-2 font-mono text-xs font-semibold text-zinc-800 shadow-xs hover:bg-zinc-50 hover:text-zinc-950"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Return to Dashboard
      </Link>
    </Card>
  );
}

