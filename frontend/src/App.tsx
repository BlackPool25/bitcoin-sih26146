import { useState, useRef, useEffect, useMemo } from "react";
import GraphView from "@/components/GraphView";
import GeoMap from "@/components/GeoMap";
import ReplaySlider from "@/components/ReplaySlider";
import AlertTable from "@/components/AlertTable";
import EvidencePanel from "@/components/EvidencePanel";
import type { CyJson } from "@/types/graph";
import type { GeoPoint } from "@/types/geo";
import { getCentroidForCountry } from "@/leaflet/markers";
import { toCyJsonFromRows } from "@/types/replay";
import type { TransactionRecord } from "@/types/replay";

export default function App() {
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [cyJson, setCyJson] = useState<CyJson | null>(null);
  const [graphLoading, setLoading] = useState(false);
  const [graphError, setError] = useState<string | null>(null);
  const [replayRows, setReplayRows] = useState<TransactionRecord[]>([]);
  const initialized = useRef(false);

  if (!initialized.current) {
    initialized.current = true;
  }

  useEffect(() => {
    document.documentElement.classList.add("dark");
  }, []);

  const searchParams = new URLSearchParams(window.location.search);
  const renderer = searchParams.get("renderer") ?? "cytoscape";

  // Fetch GET /api/graph/{id}?limit=2000 when selectedAlertId changes
  useEffect(() => {
    if (!selectedAlertId) {
      setCyJson(null);
      setError(null);
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    let cancelled = false;
    async function run() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/graph/${selectedAlertId}?limit=2000`, {
          signal: controller.signal,
        });
        if (cancelled || controller.signal.aborted) return;
        if (!res.ok) {
          if (res.status === 404) {
            // empty state for 404 / invalid id
            if (!cancelled) {
              setCyJson({ nodes: [], edges: [], positions: {} });
              setError(null);
            }
          } else {
            let detail = `Request failed ${res.status}`;
            try {
              const body = (await res.json()) as { detail?: string };
              if (body?.detail) detail = body.detail;
            } catch {
              // ignore
            }
            if (!cancelled) {
              setError(detail);
              setCyJson(null);
            }
          }
          return;
        }
        const data = (await res.json()) as unknown;
        if (cancelled || controller.signal.aborted) return;
        // handle {nodes,edges,positions} or {rows} or raw CyJson
        const d = data as Record<string, unknown>;
        if (Array.isArray(d["nodes"])) {
          const nodes = d["nodes"] as CyJson["nodes"];
          const edges = (d["edges"] as CyJson["edges"]) ?? [];
          const positions = (d["positions"] as CyJson["positions"]) ?? {};
          if (!cancelled) setCyJson({ nodes, edges, positions });
        } else if (Array.isArray(d["rows"])) {
          const rows = d["rows"] as TransactionRecord[];
          const cy = toCyJsonFromRows(rows);
          if (!cancelled) setCyJson(cy);
        } else {
          // fallback: treat as CyJson directly
          if (!cancelled) setCyJson(data as CyJson);
        }
      } catch (e: unknown) {
        if (cancelled) return;
        if (e instanceof DOMException && e.name === "AbortError") return;
        if ((e as { name?: string })?.name === "AbortError") return;
        if (controller.signal.aborted) return;
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled && !controller.signal.aborted) setLoading(false);
      }
    }
    void run();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [selectedAlertId]);

  // Derive GeoPoints from cyJson ip nodes or replayRows via country/ASN (no city truth)
  const derivedGeoPoints: GeoPoint[] = useMemo(() => {
    const points: GeoPoint[] = [];
    const seen = new Set<string>();
    if (cyJson?.nodes) {
      for (const n of cyJson.nodes) {
        if (n.type === "ip" && n.country) {
          if (seen.has(n.id)) continue;
          seen.add(n.id);
          const centroid = getCentroidForCountry(n.country);
          points.push({
            ip: n.id,
            country: n.country,
            asn: n.asn ?? null,
            lat: centroid.lat,
            lng: centroid.lng,
            radius: 500,
            tier: "tier2",
          });
        }
      }
    }
    for (const r of replayRows) {
      const src = (r as unknown as { src_ip: string }).src_ip;
      const dst = (r as unknown as { dst_ip: string }).dst_ip;
      const country = (r as unknown as { geo_country: string }).geo_country ?? "US";
      const asn = (r as unknown as { geo_asn: number }).geo_asn ?? null;
      for (const ip of [src, dst]) {
        if (!ip || seen.has(ip)) continue;
        seen.add(ip);
        const centroid = getCentroidForCountry(country);
        points.push({
          ip,
          country,
          asn,
          lat: centroid.lat,
          lng: centroid.lng,
          radius: 500,
          tier: "tier2",
        });
      }
    }
    return points;
  }, [cyJson, replayRows]);

  const selectedRef = useRef<string | null>(selectedAlertId);
  useEffect(() => {
    selectedRef.current = selectedAlertId;
  }, [selectedAlertId]);

  const handleReplayData = (data: { rows: unknown[]; count: number; at: string }) => {
    const rows = data.rows as TransactionRecord[];
    setReplayRows(rows);
    if (selectedRef.current !== null) return;
    setCyJson(toCyJsonFromRows(rows));
  };

  return (
    <div className="dark min-h-screen bg-background text-foreground antialiased">
      <div className="max-w-[1280px] mx-auto p-4 sm:p-6">
        <header className="mb-6 border-b border-border pb-4">
          <h1 className="text-2xl font-bold tracking-tight">SIH26146 — Investigator Console</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Viz Graph · M5 scaffold · Renderer: {renderer} | Selected: {selectedAlertId ?? "none"}
          </p>
        </header>

        {/* Dev mock alert list — 3 buttons for integration wiring */}
        <div className="mb-4 flex gap-2" data-testid="mock-alert-list">
          <button data-testid="alert-btn-alert-123" onClick={() => setSelectedAlertId("alert-123")} className="rounded border px-3 py-1 text-sm">
            alert-123
          </button>
          <button data-testid="alert-btn-alert-124" onClick={() => setSelectedAlertId("alert-124")} className="rounded border px-3 py-1 text-sm">
            alert-124
          </button>
          <button data-testid="alert-btn-alert-125" onClick={() => setSelectedAlertId("alert-125")} className="rounded border px-3 py-1 text-sm">
            alert-125
          </button>
          <button data-testid="alert-btn-invalid" onClick={() => setSelectedAlertId("invalid")} className="rounded border px-3 py-1 text-sm">
            invalid
          </button>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.7fr_1fr]">
          <AlertTable onSelectAlert={setSelectedAlertId} selectedAlertId={selectedAlertId} />
          <EvidencePanel alertId={selectedAlertId} />
        </div>

        <div className="mt-6 grid grid-cols-2 gap-4">
          <div>
            <GraphView cyJson={cyJson} selectedAlertId={selectedAlertId} limit={2000} />
            {graphLoading && <div data-testid="graph-loading">Loading...</div>}
            {graphError && <div data-testid="graph-error">{graphError}</div>}
            {!selectedAlertId && !graphLoading && !graphError && <div data-testid="graph-empty-select">Select an alert</div>}
            {selectedAlertId && !graphLoading && !graphError && cyJson && cyJson.nodes.length === 0 && <div data-testid="graph-empty">no subgraph</div>}
          </div>
          <GeoMap points={derivedGeoPoints} />
        </div>

        <div className="mt-6">
          <ReplaySlider onReplayData={handleReplayData} />
        </div>
      </div>
    </div>
  );
}
