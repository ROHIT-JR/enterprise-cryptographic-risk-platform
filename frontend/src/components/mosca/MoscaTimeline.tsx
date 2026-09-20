import { computeMosca } from "../../utils/mosca";

interface MoscaTimelineProps {
  dataLifetime: number;
  migrationTime: number;
  quantumArrivalYear: number;
  currentYear: number;
}

const WIDTH = 800;
const HEIGHT = 190;
const PAD_LEFT = 30;
const PAD_RIGHT = 30;
const AXIS_Y = 150;

export function MoscaTimeline({ dataLifetime, migrationTime, quantumArrivalYear, currentYear }: MoscaTimelineProps) {
  const { lhs, yearsUntilQuantum, verdict } = computeMosca(dataLifetime, migrationTime, quantumArrivalYear, currentYear);
  const maxRange = Math.max(lhs, yearsUntilQuantum) * 1.2 || 10;
  const chartWidth = WIDTH - PAD_LEFT - PAD_RIGHT;
  const yearToX = (yearsFromNow: number) => PAD_LEFT + (yearsFromNow / maxRange) * chartWidth;

  const zoneX = yearToX(yearsUntilQuantum);
  const xBarEnd = yearToX(dataLifetime);
  const yBarEnd = yearToX(migrationTime);
  const lhsX = yearToX(lhs);

  const ticks = Array.from({ length: 5 }, (_, i) => {
    const yearsFromNow = (maxRange / 4) * i;
    return { yearsFromNow, year: Math.round(currentYear + yearsFromNow), x: yearToX(yearsFromNow) };
  });

  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-full w-full" role="img" aria-label="Mosca inequality timeline">
      {/* safe / danger background zones */}
      <rect x={PAD_LEFT} y={20} width={Math.max(zoneX - PAD_LEFT, 0)} height={AXIS_Y - 20} fill="rgba(5,150,105,0.06)" />
      <rect x={zoneX} y={20} width={Math.max(WIDTH - PAD_RIGHT - zoneX, 0)} height={AXIS_Y - 20} fill="rgba(220,38,38,0.06)" />

      {/* axis */}
      <line x1={PAD_LEFT} y1={AXIS_Y} x2={WIDTH - PAD_RIGHT} y2={AXIS_Y} stroke="#e2e8f0" />
      {ticks.map((tick) => (
        <g key={tick.year}>
          <line x1={tick.x} y1={AXIS_Y} x2={tick.x} y2={AXIS_Y + 6} stroke="#cbd5e1" />
          <text x={tick.x} y={AXIS_Y + 20} textAnchor="middle" fontSize="10" fill="currentColor" className="text-slate-500">
            {tick.year}
          </text>
        </g>
      ))}

      {/* X bar: data lifetime */}
      <defs>
        <linearGradient id="mosca-x-gradient" x1="0" x2="1">
          <stop offset="0%" stopColor="#4f46e5" stopOpacity="0.85" />
          <stop offset="100%" stopColor="#4f46e5" stopOpacity="0.3" />
        </linearGradient>
      </defs>
      <rect x={PAD_LEFT} y={44} width={Math.max(xBarEnd - PAD_LEFT, 2)} height={16} rx={8} fill="url(#mosca-x-gradient)" />
      <text x={PAD_LEFT} y={38} fontSize="11" fontWeight={600} fill="#4338ca">
        X · Data lifetime ({dataLifetime}y)
      </text>

      {/* Y bar: migration time */}
      <rect x={PAD_LEFT} y={76} width={Math.max(yBarEnd - PAD_LEFT, 2)} height={16} rx={8} fill="#d97706" fillOpacity={0.7} />
      <text x={PAD_LEFT} y={70} fontSize="11" fontWeight={600} fill="#b45309">
        Y · Migration time ({migrationTime}y)
      </text>

      {/* combined X+Y marker */}
      <line x1={lhsX} y1={30} x2={lhsX} y2={AXIS_Y} stroke="#94a3b8" strokeDasharray="4 3" strokeWidth={1.5} />
      <text x={lhsX} y={22} textAnchor="middle" fontSize="10" fill="#475569">
        Protected until Y{Math.round(lhs)}
      </text>

      {/* Z marker: quantum arrival */}
      <line x1={zoneX} y1={16} x2={zoneX} y2={AXIS_Y} stroke="#dc2626" strokeWidth={2} />
      <text x={zoneX} y={108} textAnchor="middle" fontSize="11" fontWeight={700} fill="#dc2626">
        Q-Day
      </text>
      <text x={zoneX} y={122} textAnchor="middle" fontSize="9" fill="#dc2626">
        {quantumArrivalYear}
      </text>

      {/* verdict banner */}
      <text x={PAD_LEFT} y={HEIGHT - 6} fontSize="12" fontWeight={700} fill={verdict === "critical" ? "#dc2626" : "#059669"}>
        {verdict === "critical"
          ? `⚠ CRITICAL — X+Y (${Math.round(lhs)}) exceeds years until quantum (${yearsUntilQuantum})`
          : `✓ SAFE — X+Y (${Math.round(lhs)}) fits within years until quantum (${yearsUntilQuantum})`}
      </text>
    </svg>
  );
}
