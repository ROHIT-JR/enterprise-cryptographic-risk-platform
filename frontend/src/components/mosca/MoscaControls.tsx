import { QUANTUM_PRESETS } from "../../utils/mosca";

interface MoscaControlsProps {
  dataLifetime: number;
  migrationTime: number;
  quantumArrivalYear: number;
  onDataLifetimeChange: (value: number) => void;
  onMigrationTimeChange: (value: number) => void;
  onQuantumArrivalYearChange: (value: number) => void;
}

function Slider({
  label,
  value,
  min,
  max,
  step = 1,
  suffix,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  suffix: string;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block">
      <div className="mb-2 flex items-center justify-between text-xs">
        <span className="font-medium text-slate-500">{label}</span>
        <span className="font-mono text-indigo-600">
          {value}
          {suffix}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-indigo-600"
      />
    </label>
  );
}

export function MoscaControls({
  dataLifetime,
  migrationTime,
  quantumArrivalYear,
  onDataLifetimeChange,
  onMigrationTimeChange,
  onQuantumArrivalYearChange,
}: MoscaControlsProps) {
  return (
    <div className="space-y-5">
      <Slider label="Data lifetime (X)" value={dataLifetime} min={1} max={50} suffix=" years" onChange={onDataLifetimeChange} />
      <Slider label="Migration time (Y)" value={migrationTime} min={1} max={10} suffix=" years" onChange={onMigrationTimeChange} />
      <Slider
        label="Quantum arrival (Z)"
        value={quantumArrivalYear}
        min={2028}
        max={2045}
        suffix=""
        onChange={onQuantumArrivalYearChange}
      />
      <div className="flex flex-wrap gap-2 pt-1">
        {QUANTUM_PRESETS.map((preset) => (
          <button
            key={preset.label}
            onClick={() => onQuantumArrivalYearChange(preset.year)}
            className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
              quantumArrivalYear === preset.year
                ? "border-indigo-200 bg-indigo-50 text-indigo-700"
                : "border-slate-200 bg-white text-slate-500 hover:border-slate-300 hover:bg-slate-50"
            }`}
          >
            {preset.label} ({preset.year})
          </button>
        ))}
      </div>
    </div>
  );
}
