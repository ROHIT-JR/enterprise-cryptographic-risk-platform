import { AlertTriangle } from "lucide-react";

const DELAY_SCENARIOS_YEARS = [0, 1, 2, 4];
// "Every year of delay adds ~1.5 years of quantum exposure due to
// compounding dependency complexity" — carried over verbatim from issue #25.
const COMPOUNDING_FACTOR = 1.5;

export function CostOfDelay({
  currentYear,
  baseCompletionYear,
  qDayYear,
}: {
  currentYear: number;
  baseCompletionYear: number;
  qDayYear: number;
}) {
  const rows = DELAY_SCENARIOS_YEARS.map((delay) => {
    const startYear = currentYear + delay;
    const completionYear = baseCompletionYear + delay + delay * (COMPOUNDING_FACTOR - 1);
    const exposureWindow = Math.max(0, Math.round((completionYear - qDayYear) * 10) / 10);
    return { delay, startYear, completionYear: Math.round(completionYear), exposureWindow };
  });

  return (
    <div>
      <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "var(--border)" }}>
        <table className="w-full text-left text-xs">
          <thead>
            <tr style={{ background: "var(--bg-hover)" }}>
              <th className="px-3 py-2.5 font-mono text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>If migration starts</th>
              <th className="px-3 py-2.5 font-mono text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Completion by</th>
              <th className="px-3 py-2.5 font-mono text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Data exposure window</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={row.delay} style={{ background: index % 2 === 1 ? "var(--bg-hover)" : "transparent", borderTop: "1px solid var(--border)" }}>
                <td className="px-3 py-2.5 font-medium" style={{ color: "var(--text-primary)" }}>
                  {row.delay === 0 ? `Today (${row.startYear})` : `${row.startYear} (+${row.delay}yr delay)`}
                </td>
                <td className="px-3 py-2.5 tabular-nums" style={{ color: "var(--text-secondary)" }}>{row.completionYear}</td>
                <td className="px-3 py-2.5">
                  <span
                    className="inline-flex items-center gap-1 tabular-nums font-semibold"
                    style={{ color: row.exposureWindow > 0 ? "var(--risk-critical)" : "var(--risk-low)" }}
                  >
                    {row.exposureWindow > 0 && <AlertTriangle className="h-3 w-3" />}
                    {row.exposureWindow > 0 ? `~${row.exposureWindow} years at risk` : "0 years (safe)"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2.5 text-xs italic" style={{ color: "var(--text-muted)" }}>
        Every year of delay adds approximately {COMPOUNDING_FACTOR} years of quantum exposure due to compounding dependency complexity.
      </p>
    </div>
  );
}
