import { useEffect, useState, useRef, useCallback } from "react";
import { getEvidence } from "@/api/alerts";
import type { Evidence } from "@/types/alert";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

// ---------------------------------------------------------------------------
// Props: support both naming conventions
// ---------------------------------------------------------------------------
export interface EvidencePanelProps {
  alertId?: string | null;
  selectedAlertId?: string | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function countryFlag(code: string): string {
  const upper = code.toUpperCase();
  if (upper.length !== 2) return "🏳️";
  const OFFSET = 0x1f1e6 - 65;
  const first = upper.charCodeAt(0) + OFFSET;
  const second = upper.charCodeAt(1) + OFFSET;
  try {
    return String.fromCodePoint(first, second);
  } catch {
    return "🏳️";
  }
}

function isAbortError(err: unknown): boolean {
  return (
    (err instanceof DOMException && err.name === "AbortError") ||
    (err instanceof Error && err.name === "AbortError")
  );
}

function tierBadgeVariant(tier: string | undefined): "critical" | "high" | "medium" | "low" | "default" {
  switch (tier) {
    case "critical":
      return "critical";
    case "high":
      return "high";
    case "medium":
      return "medium";
    case "low":
      return "low";
    default:
      return "default";
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function EvidencePanel(props: EvidencePanelProps): React.JSX.Element {
  const effectiveId: string | null = props.alertId ?? props.selectedAlertId ?? null;

  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const lastFetchedIdRef = useRef<string | null>(null);
  const [retryNonce, setRetryNonce] = useState<number>(0);

  const fetchEvidence = useCallback(
    async (id: string, signal: AbortSignal): Promise<void> => {
      setLoading(true);
      setError(null);
      try {
        const data = await getEvidence(id, signal);
        // only update if not aborted and still the expected id
        if (signal.aborted) return;
        setEvidence(data);
        lastFetchedIdRef.current = id;
      } catch (err) {
        if (isAbortError(err)) return;
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);
      } finally {
        if (!signal.aborted) setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    // null placeholder: reset, no fetch, abort previous
    if (effectiveId === null) {
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }
      lastFetchedIdRef.current = null;
      setEvidence(null);
      setLoading(false);
      setError(null);
      return;
    }

    // dedupe same id (already loaded and not in error/loading) — skip
    if (effectiveId === lastFetchedIdRef.current && evidence !== null && error === null && !loading) {
      return;
    }

    // abort previous fetch when alertId changes quickly
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;

    void fetchEvidence(effectiveId, controller.signal);

    return () => {
      controller.abort();
    };
    // retryNonce forces re-fetch on retry button
    // evidence/error/loading intentionally not added to avoid loop except dedupe check via ref
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveId, retryNonce, fetchEvidence]);

  const handleRetry = useCallback(() => {
    if (effectiveId === null) return;
    // force re-fetch even if deduped: clear last id
    lastFetchedIdRef.current = null;
    setRetryNonce((n) => n + 1);
  }, [effectiveId]);

  // -------------------------------------------------------------------------
  // Render: empty
  // -------------------------------------------------------------------------
  if (effectiveId === null) {
    return (
      <Card data-testid="evidence-panel" data-state="empty">
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground">Select an alert to view evidence</p>
        </CardContent>
      </Card>
    );
  }

  // -------------------------------------------------------------------------
  // Render: loading
  // -------------------------------------------------------------------------
  if (loading) {
    return (
      <Card data-testid="evidence-panel" data-state="loading">
        <CardHeader>
          <CardTitle className="text-base">Loading evidence…</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </CardContent>
      </Card>
    );
  }

  // -------------------------------------------------------------------------
  // Render: error
  // -------------------------------------------------------------------------
  if (error !== null) {
    return (
      <Card data-testid="evidence-panel" data-state="error">
        <CardHeader>
          <CardTitle className="text-base">Evidence</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
          <Button onClick={handleRetry} variant="outline" size="sm">
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  // -------------------------------------------------------------------------
  // Render: loaded (still might be null briefly after loading false but no evidence? fallback to empty)
  // -------------------------------------------------------------------------
  if (evidence === null) {
    return (
      <Card data-testid="evidence-panel" data-state="empty">
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground">Select an alert to view evidence</p>
        </CardContent>
      </Card>
    );
  }

  const shapWaterfallData = Object.entries(evidence.shap)
    .map(([feat, value]) => ({ feat, value }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, 10);

  const amountFlow = evidence.amount_flow ?? [];
  const geoTimeline = evidence.geo_timeline ?? [];
  const temporalBurst = evidence.temporal_burst ?? [];
  const accuracyHint = evidence.accuracy_hint;
  const isHint = accuracyHint?.is_hint === true;

  return (
    <Card data-testid="evidence-panel" data-state="loaded" className="overflow-hidden">
      <CardHeader className="space-y-2">
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          <span>Evidence {evidence.alert_id.slice(0, 8)}…</span>
          {evidence.p !== undefined && <span className="font-mono text-sm tabular-nums">p {evidence.p.toFixed(2)}</span>}
          {evidence.tier && (
            <Badge variant={tierBadgeVariant(evidence.tier)} className="capitalize">
              {evidence.tier}
            </Badge>
          )}
        </CardTitle>
        <div className="flex flex-wrap gap-2">
          {isHint && accuracyHint && (
            <Badge variant="outline" data-testid="accuracy-hint">
              Accuracy hint: ~{accuracyHint.radius_km}km radius — area not point
            </Badge>
          )}
          {evidence.geo_inconsistent && <Badge variant="destructive">Geo inconsistent</Badge>}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* nl Jinja string verbatim */}
        <p className="text-sm italic leading-relaxed">{evidence.nl}</p>

        {/* SHAP waterfall horizontal BarChart */}
        <div>
          <h4 className="mb-2 text-sm font-semibold">SHAP waterfall (top 10 by |value|)</h4>
          <div style={{ width: "100%", height: 320 }}>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={shapWaterfallData} layout="vertical" margin={{ left: 80, right: 16, top: 8, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="feat" type="category" width={120} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" fill="var(--chart-1, #3b82f6)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Amount flow AreaChart */}
        <div>
          <h4 className="mb-2 text-sm font-semibold">Amount flow</h4>
          {amountFlow.length > 0 ? (
            <div style={{ width: "100%", height: 200 }}>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={amountFlow} margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="ts"
                    tickFormatter={(v: string) => {
                      const d = new Date(v);
                      return Number.isNaN(d.getTime()) ? String(v).slice(11, 16) : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
                    }}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip
                    labelFormatter={(v: string) => {
                      const d = new Date(v);
                      return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleString();
                    }}
                  />
                  <Area type="monotone" dataKey="amount" stroke="var(--chart-2, #10b981)" fill="var(--chart-2, #10b981)" fillOpacity={0.3} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">No amount flow data</p>
          )}
        </div>

        {/* Geo timeline pill path */}
        <div>
          <h4 className="mb-2 text-sm font-semibold">Geo timeline</h4>
          {geoTimeline.length > 0 ? (
            <div className="flex flex-wrap items-center gap-2">
              {geoTimeline.map((pt, i) => (
                <span key={`${pt.country}-${pt.ts}-${i}`} className="inline-flex items-center gap-1 rounded-full border bg-muted px-2.5 py-1 text-xs">
                  <span aria-hidden="true">{countryFlag(pt.country)}</span>
                  <span className="font-medium">{pt.country}</span>
                  <small className="text-muted-foreground">{new Date(pt.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</small>
                  {i < geoTimeline.length - 1 && <span className="mx-1">→</span>}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">No geo timeline</p>
          )}
        </div>

        {/* Temporal burst BarChart */}
        <div>
          <h4 className="mb-2 text-sm font-semibold">Temporal burst</h4>
          {temporalBurst.length > 0 ? (
            <div style={{ width: "100%", height: 160 }}>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={temporalBurst} margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="var(--chart-3, #f59e0b)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">No temporal burst data</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// Named export for spec flexibility
export { EvidencePanel as EvidencePanelNamed };
