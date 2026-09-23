import type { Severity } from "../types/api";

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en", { notation: value > 9999 ? "compact" : "standard" }).format(value);
}

export function relativeTime(value: string | null): string {
  if (!value) return "Not completed";
  const seconds = Math.round((new Date(value).getTime() - Date.now()) / 1000);
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  const ranges: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31_536_000],
    ["month", 2_592_000],
    ["day", 86_400],
    ["hour", 3_600],
    ["minute", 60],
  ];
  for (const [unit, divisor] of ranges) {
    if (Math.abs(seconds) >= divisor) return formatter.format(Math.round(seconds / divisor), unit);
  }
  return formatter.format(seconds, "second");
}

// Token-based (theme-aware) — resolves against --risk-* in index.css rather
// than hardcoded Tailwind color scales, so severity badges read correctly in
// both light and dark theme without a separate dark: variant per severity.
export const severityStyles: Record<Severity, string> = {
  critical: "border-[var(--risk-critical)]/35 bg-[var(--risk-critical)]/10 text-[var(--risk-critical)]",
  high:     "border-[var(--risk-high)]/35     bg-[var(--risk-high)]/10     text-[var(--risk-high)]",
  medium:   "border-[var(--risk-medium)]/35   bg-[var(--risk-medium)]/10   text-[var(--risk-medium)]",
  low:      "border-[var(--risk-low)]/35      bg-[var(--risk-low)]/10      text-[var(--risk-low)]",
};

export const severityHexColors: Record<Severity, string> = {
  critical: "#dc2626",
  high:     "#ea580c",
  medium:   "#d97706",
  low:      "#16a34a",
};

