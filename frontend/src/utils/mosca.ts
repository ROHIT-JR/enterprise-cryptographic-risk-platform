export interface MoscaComputation {
  lhs: number;
  yearsUntilQuantum: number;
  verdict: "critical" | "safe";
}

/** Client-side mirror of risk_engine/mosca_model.py MoscaModel.simulate(). */
export function computeMosca(
  dataLifetime: number,
  migrationTime: number,
  quantumArrivalYear: number,
  currentYear: number,
): MoscaComputation {
  const yearsUntilQuantum = Math.max(quantumArrivalYear - currentYear, 1);
  const lhs = dataLifetime + migrationTime;
  return { lhs, yearsUntilQuantum, verdict: lhs > yearsUntilQuantum ? "critical" : "safe" };
}

export const QUANTUM_PRESETS = [
  { label: "Optimistic", year: 2040 },
  { label: "Moderate", year: 2035 },
  { label: "Pessimistic", year: 2030 },
  { label: "NSA Deadline", year: 2035 },
] as const;
