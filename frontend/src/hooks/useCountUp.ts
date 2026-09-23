import { useEffect, useRef, useState } from "react";

/**
 * Scroll-triggered wrapper around NumberTicker's count-up. NumberTicker
 * itself animates on mount (matches the shadcndashboard.dev source verbatim);
 * this hook adds the IntersectionObserver trigger for KPI numbers that are
 * already in the DOM before they scroll into view (verified live behavior
 * on shadcndashboard.dev/ui-blocks — see issue #67).
 *
 * Usage: const { visible, ref } = useCountUp(); <div ref={ref}>{visible && <NumberTicker end={42} />}</div>
 */
export function useCountUp(threshold = 0.3) {
  const [visible, setVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold]);

  return { visible, ref };
}
