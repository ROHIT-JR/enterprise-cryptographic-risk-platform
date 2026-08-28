import { ArrowLeft, ShieldQuestion } from "lucide-react";
import { Link } from "react-router-dom";
import { Card } from "../components/ui";

export function NotFound() {
  return <Card className="mx-auto mt-20 max-w-xl p-10 text-center"><ShieldQuestion className="mx-auto h-10 w-10 text-brand-300" /><p className="mt-6 text-[10px] font-bold uppercase tracking-[0.22em] text-brand-300">404</p><h1 className="mt-2 text-2xl font-semibold text-white">This workspace view does not exist</h1><p className="mt-3 text-sm text-slate-500">Return to the cryptographic posture dashboard.</p><Link to="/" className="mt-6 inline-flex items-center gap-2 rounded-lg border border-white/10 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-white/5"><ArrowLeft className="h-4 w-4" /> Dashboard</Link></Card>;
}

