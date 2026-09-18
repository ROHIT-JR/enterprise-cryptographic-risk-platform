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

export const severityStyles: Record<Severity, string> = {
  critical: "border-red-300    bg-red-50/90    text-red-900",
  high:     "border-orange-300 bg-orange-50/90 text-orange-950",
  medium:   "border-amber-300  bg-amber-50/90  text-amber-950",
  low:      "border-emerald-300 bg-emerald-50/90 text-emerald-950",
};

