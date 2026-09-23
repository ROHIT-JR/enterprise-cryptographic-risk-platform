import type { ReactNode } from "react";
import { cn } from "../utils/cn";

type ShineBorderProps = {
  children: ReactNode;
  className?: string;
  borderWidth?: number;
  duration?: number;
  /** Tailwind gradient-stop classes, e.g. "from-blue-500 via-red-500 to-teal-400". */
  gradient?: string;
};

/**
 * Ported from shadcndashboard.dev/components/shine-border (shine-border-01.tsx):
 * a continuously rotating conic gradient clipped to a border-width ring via
 * Tailwind's built-in `animate-spin`, no custom @property/keyframe needed.
 *
 * Reserve for exactly one "top pick" element per screen (the #1 TOPSIS
 * recommendation, the single highest-severity asset) — see issue #67.
 */
export function ShineBorder({
  children,
  className,
  borderWidth = 2,
  duration = 3,
  gradient = "from-[var(--risk-low)] via-[var(--accent)] to-[var(--risk-high)]",
}: ShineBorderProps) {
  return (
    <div className={cn("relative rounded-2xl", className)} style={{ padding: borderWidth }}>
      {/* Animated gradient layer */}
      <div className="absolute inset-0 overflow-hidden rounded-2xl">
        <div
          className={cn("absolute -inset-full animate-spin bg-conic blur-sm", gradient)}
          style={{ animationDuration: `${duration}s` }}
        />
      </div>
      <div className="relative rounded-2xl" style={{ background: "var(--bg-card)" }}>
        {children}
      </div>
    </div>
  );
}
