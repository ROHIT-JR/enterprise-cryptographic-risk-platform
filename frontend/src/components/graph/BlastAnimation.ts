import type { Severity } from "../../types/api";

/**
 * Animation frames per issue #69's spec:
 *   0 — idle
 *   1 (0-300ms)   — focus node compromised (pulse + glow ring)
 *   2 (300-600ms) — direct (degree-1) dependents affected
 *   3 (600-900ms) — degree-2 dependents affected
 *   4 (900-1200ms)— degree-3+ dependents affected, hold + show impact summary
 */
export type AnimFrame = 0 | 1 | 2 | 3 | 4;

export const FRAME_DURATIONS_MS = [300, 300, 300, 300] as const; // frame 1 -> 2 -> 3 -> 4

/** Maps a node's BFS degree from the focus asset to the frame it lights up on. */
export function frameForDegree(degree: number): AnimFrame {
  if (degree <= 0) return 1;
  if (degree === 1) return 2;
  if (degree === 2) return 3;
  return 4;
}

/** Falls back to the degree-based color band when a node has no real severity of its own. */
function severityForFrame(frame: AnimFrame): Severity {
  if (frame <= 1) return "critical";
  if (frame === 2) return "high";
  if (frame === 3) return "medium";
  return "low";
}

export interface NodeAnimState {
  impacted: boolean;
  dimmed: boolean;
  glow: boolean;
  effectiveSeverity: Severity | null;
}

export function nodeAnimState(params: {
  isFocus: boolean;
  degree: number;
  realSeverity: Severity | null | undefined;
  currentFrame: AnimFrame;
}): NodeAnimState {
  const { isFocus, degree, realSeverity, currentFrame } = params;
  if (currentFrame === 0) {
    return { impacted: false, dimmed: false, glow: false, effectiveSeverity: realSeverity ?? null };
  }
  const nodeFrame = frameForDegree(isFocus ? 0 : degree);
  const active = currentFrame >= nodeFrame;
  return {
    impacted: active,
    dimmed: !active,
    glow: active,
    effectiveSeverity: active ? (realSeverity ?? severityForFrame(nodeFrame)) : (realSeverity ?? null),
  };
}

export interface EdgeAnimState {
  stroke: string;
  strokeWidth: number;
  dashed: boolean;
  animated: boolean;
}

export function edgeAnimState(params: { minDegree: number; currentFrame: AnimFrame }): EdgeAnimState {
  const { minDegree, currentFrame } = params;
  if (currentFrame === 0) {
    return { stroke: "var(--text-muted)", strokeWidth: 1.2, dashed: false, animated: false };
  }
  const edgeFrame = frameForDegree(minDegree);
  const active = currentFrame >= edgeFrame;
  if (!active) {
    return { stroke: "var(--border)", strokeWidth: 1, dashed: false, animated: false };
  }
  return {
    stroke: `var(--risk-${severityForFrame(edgeFrame)})`,
    strokeWidth: 2,
    dashed: true,
    animated: true,
  };
}
