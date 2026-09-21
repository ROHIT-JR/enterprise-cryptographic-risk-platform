import { useEffect, useRef, useState } from "react";
import { api, authStorage } from "../api/client";

export interface ScanProgressEvent {
  type: "stage" | "asset" | "completed" | "failed";
  message: string;
  progress?: number;
  assets_discovered?: number;
  ts: number;
}

const MAX_EVENTS = 100;

/**
 * Live scan progress over Server-Sent Events.
 *
 * Uses `fetch` + a manual SSE line parser rather than the browser's native
 * `EventSource`, because `EventSource` cannot send the `Authorization`
 * header this API's JWT auth requires (and putting the token in the URL
 * as a query parameter would leak it into server logs and browser history).
 */
export function useScanProgress(scanId: string | null) {
  const [events, setEvents] = useState<ScanProgressEvent[]>([]);
  const [progress, setProgress] = useState<number | null>(null);
  const [done, setDone] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setEvents([]);
    setProgress(null);
    setDone(false);
    if (!scanId) return;

    const controller = new AbortController();
    controllerRef.current = controller;

    async function stream() {
      const token = authStorage.access();
      const response = await fetch(`${api.defaults.baseURL}/scans/${scanId}/stream`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        signal: controller.signal,
      });
      if (!response.body) return;

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done: streamEnded } = await reader.read();
        if (streamEnded) break;
        buffer += decoder.decode(value, { stream: true });

        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          const dataLine = frame.split("\n").find((line) => line.startsWith("data: "));
          if (!dataLine) continue;
          const event = JSON.parse(dataLine.slice("data: ".length)) as ScanProgressEvent;
          setEvents((previous) => [...previous.slice(-(MAX_EVENTS - 1)), event]);
          if (typeof event.progress === "number") setProgress(event.progress);
          if (event.type === "completed" || event.type === "failed") setDone(true);
        }
      }
    }

    stream().catch(() => {
      // The connection dropped or was aborted; the page's own scan polling
      // remains the source of truth for the final status either way.
    });

    return () => controller.abort();
  }, [scanId]);

  return { events, progress, done };
}
