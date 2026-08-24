import { useEffect, useRef, useState } from "react";
import { parseISOWithTZ } from "@/types/replay";

export type ReplayData = {
  rows: unknown[];
  count: number;
  at: string;
};

export type ReplaySliderProps = {
  min?: string;
  max?: string;
  stepMs?: number;
  value?: string;
  onChange?: (at: string) => void;
  onReplayData?: (data: { rows: unknown[]; count: number; at: string }) => void;
  fetchFn?: typeof fetch;
};

const DEFAULT_MIN = "2024-01-01T00:00:00Z";
const DEFAULT_MAX = "2024-01-01T02:00:00Z";
const DEBOUNCE_MS = 180;

function safeParseMs(iso: string, fallback: number): number {
  if (!iso) return fallback;
  try {
    return parseISOWithTZ(iso).getTime();
  } catch {
    return fallback;
  }
}

function toDisplayISO(iso: string): string {
  if (!iso) return "";
  try {
    return new Date(parseISOWithTZ(iso).getTime()).toISOString();
  } catch {
    try {
      return new Date(iso).toISOString();
    } catch {
      return iso;
    }
  }
}

export default function ReplaySlider({
  min,
  max,
  stepMs = 60000,
  value,
  onChange,
  onReplayData,
  fetchFn,
}: ReplaySliderProps) {
  const resolvedMin = min ?? DEFAULT_MIN;
  const resolvedMax = max ?? DEFAULT_MAX;

  const [at, setAt] = useState<string>(() => {
    if (value !== undefined) return value;
    return resolvedMin;
  });
  const [debouncedAt, setDebouncedAt] = useState<string>(at);
  const [count, setCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  // sync when value prop changes externally
  useEffect(() => {
    if (value !== undefined && value !== at) {
      setAt(value);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  // min/max in ms
  const minMs = safeParseMs(resolvedMin, Date.parse(DEFAULT_MIN));
  const maxMs = safeParseMs(resolvedMax, Date.parse(DEFAULT_MAX));
  const atMs = (() => {
    if (!at) return minMs;
    const v = safeParseMs(at, Number.NaN);
    if (Number.isNaN(v)) return minMs;
    return v;
  })();

  // debounce 180ms
  useEffect(() => {
    const t = setTimeout(() => setDebouncedAt(at), DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [at]);

  // fetch effect with abort
  useEffect(() => {
    // abort previous
    if (abortRef.current) {
      abortRef.current.abort();
    }

    // handle empty -> 422 without fetch
    if (!debouncedAt || debouncedAt.trim() === "") {
      setLoading(false);
      setError("Missing at");
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;
    const fetcher: typeof fetch = fetchFn ?? fetch;

    let cancelled = false;

    async function run() {
      setLoading(true);
      setError(null);
      try {
        const url = `/api/replay?at=${encodeURIComponent(debouncedAt)}`;
        const res = await fetcher(url, { signal: controller.signal });
        if (cancelled || controller.signal.aborted) return;
        if (!res.ok) {
          let detail = `Request failed ${res.status}`;
          try {
            const body = (await res.json()) as { detail?: string };
            if (body?.detail) detail = body.detail;
          } catch {
            // ignore json parse
          }
          if (res.status === 422) {
            setError(detail);
          } else {
            setError(detail);
          }
          setLoading(false);
          return;
        }
        const data = (await res.json()) as { rows: unknown[]; count: number; at: string };
        if (cancelled || controller.signal.aborted) return;
        const c = typeof data.count === "number" ? data.count : (data.rows?.length ?? 0);
        // cap display at 1000 but keep actual count (spec says handle limit 1000)
        setCount(c);
        onReplayData?.({ rows: data.rows, count: c, at: data.at });
        setLoading(false);
      } catch (e: unknown) {
        if (cancelled) return;
        if (e instanceof DOMException && e.name === "AbortError") {
          return;
        }
        if ((e as { name?: string })?.name === "AbortError") {
          return;
        }
        if (controller.signal.aborted) return;
        setError(e instanceof Error ? e.message : String(e));
        setLoading(false);
      }
    }

    run();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [debouncedAt, fetchFn, onReplayData]);

  const handleSlider = (e: React.ChangeEvent<HTMLInputElement>) => {
    const ms = Number(e.target.value);
    const nextDate = new Date(ms);
    const nextISO = nextDate.toISOString();
    setAt(nextISO);
    onChange?.(nextISO);
  };

  const displayISO = toDisplayISO(at);

  return (
    <div>
      <input
        type="range"
        data-testid="replay-slider"
        min={minMs}
        max={maxMs}
        step={stepMs}
        value={atMs}
        onChange={handleSlider}
      />
      <span data-testid="replay-at">{displayISO}</span>
      <span data-testid="replay-count">{count}</span>
      {loading && <span data-testid="replay-loading">loading</span>}
      {error && <div data-testid="replay-error">{error}</div>}
    </div>
  );
}
