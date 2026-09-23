import { useEffect, useRef, useState, type CSSProperties } from "react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

type NumberTickerProps = {
  end: number;
  start?: number;
  duration?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
  style?: CSSProperties;
};

/**
 * Default variant — ported verbatim from shadcndashboard.dev/components/number-ticker
 * (number-ticker-01.tsx), ease-out-cubic count-up via requestAnimationFrame.
 * Triggers on mount; wrap in useCountUp (below) for scroll-triggered counting.
 */
export function NumberTicker({
  end,
  start = 0,
  duration = 2,
  decimals = 0,
  prefix = "",
  suffix = "",
  className = "",
  style,
}: NumberTickerProps) {
  const [value, setValue] = useState(start);
  const startTimeRef = useRef<number | null>(null);

  useEffect(() => {
    let frame: number;
    startTimeRef.current = null;

    const animate = (timestamp: number) => {
      if (!startTimeRef.current) startTimeRef.current = timestamp;

      const progress = timestamp - startTimeRef.current;
      const percent = Math.min(progress / (duration * 1000), 1);

      // ease-out cubic for smooth animation
      const eased = 1 - Math.pow(1 - percent, 3);

      const current = start + (end - start) * eased;
      setValue(current);

      if (percent < 1) {
        frame = requestAnimationFrame(animate);
      }
    };

    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [start, end, duration]);

  return (
    <span className={className} style={style}>
      {prefix}
      {value.toFixed(decimals)}
      {suffix}
    </span>
  );
}

/** Currency variant — same count-up, formatted with Intl.NumberFormat. */
export function NumberTickerCurrency({
  end,
  start = 0,
  duration = 2,
  currency = "USD",
  className = "",
}: {
  end: number;
  start?: number;
  duration?: number;
  currency?: string;
  className?: string;
}) {
  const [value, setValue] = useState(start);
  const startTimeRef = useRef<number | null>(null);

  useEffect(() => {
    let frame: number;
    startTimeRef.current = null;
    const animate = (timestamp: number) => {
      if (!startTimeRef.current) startTimeRef.current = timestamp;
      const percent = Math.min((timestamp - startTimeRef.current) / (duration * 1000), 1);
      const eased = 1 - Math.pow(1 - percent, 3);
      setValue(start + (end - start) * eased);
      if (percent < 1) frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [start, end, duration]);

  const formatted = new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 2 }).format(value);
  return <span className={className}>{formatted}</span>;
}

/**
 * Countdown variant — live decrementing duration display, ticking every
 * second via setInterval rather than requestAnimationFrame (a countdown
 * doesn't need 60fps, and setInterval is cheaper to keep running for hours).
 * `target` is the deadline; `unit` selects the display granularity.
 */
export function NumberTickerCountdown({
  target,
  unit = "seconds",
  className = "",
}: {
  target: Date;
  unit?: "seconds" | "days";
  className?: string;
}) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const interval = window.setInterval(() => setNow(Date.now()), unit === "seconds" ? 1000 : 60_000);
    return () => window.clearInterval(interval);
  }, [unit]);

  const remainingMs = Math.max(0, target.getTime() - now);

  if (unit === "days") {
    const totalDays = Math.floor(remainingMs / 86_400_000);
    const years = Math.floor(totalDays / 365);
    const days = totalDays % 365;
    return (
      <span className={className}>
        {years > 0 ? `${years}y ${days}d` : `${days}d`}
      </span>
    );
  }

  const totalSeconds = Math.floor(remainingMs / 1000);
  const hh = String(Math.floor(totalSeconds / 3600)).padStart(2, "0");
  const mm = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, "0");
  const ss = String(totalSeconds % 60).padStart(2, "0");
  return (
    <span className={className}>
      {hh}:{mm}:{ss}
    </span>
  );
}

/** Trend variant — colored up/down arrow + animated percentage. */
export function NumberTickerTrend({
  value,
  duration = 1.2,
  className = "",
}: {
  value: number; // signed, e.g. +18.4 or -6.2
  duration?: number;
  className?: string;
}) {
  const isUp = value >= 0;
  return (
    <span className={`inline-flex items-center gap-1 ${className}`} style={{ color: isUp ? "var(--risk-low)" : "var(--risk-critical)" }}>
      {isUp ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
      <NumberTicker end={Math.abs(value)} duration={duration} decimals={1} prefix={isUp ? "+" : "-"} suffix="%" />
    </span>
  );
}

/** Labeled variant — colored status dot + big number + muted label. */
export function NumberTickerLabeled({
  end,
  label,
  dotColor = "var(--accent)",
  duration = 1.2,
  className = "",
}: {
  end: number;
  label: string;
  dotColor?: string;
  duration?: number;
  className?: string;
}) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: dotColor }} />
      <NumberTicker end={end} duration={duration} className="text-lg font-semibold" style={{ color: "var(--text-primary)" }} />
      <span className="text-xs" style={{ color: "var(--text-muted)" }}>{label}</span>
    </span>
  );
}
