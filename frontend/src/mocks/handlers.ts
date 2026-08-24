import graph80 from "./fixtures/graph-80.json";
import graph2000 from "./fixtures/graph-2000.json";
import replayRows from "./fixtures/replay-1000.json";
import geoCentroids from "./fixtures/geo-centroids.json";
import { parseISOWithTZ } from "@/types/replay";

type MockResponseInit = { status: number; body: unknown };

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function parseUrl(url: string) {
  // support relative url
  const u = new URL(url, "http://localhost");
  return u;
}

export async function mockFetch(input: string | URL | Request, init?: RequestInit): Promise<Response> {
  const urlStr = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
  const method = (init?.method ?? "GET").toUpperCase();
  const u = parseUrl(urlStr);
  const pathname = u.pathname;
  const searchParams = u.searchParams;

  // GET /api/graph/{id}?limit=...
  if (method === "GET" && pathname.startsWith("/api/graph/")) {
    const id = pathname.replace("/api/graph/", "").split("/")[0] ?? "";
    if (id === "invalid" || id === "") {
      return jsonResponse({ detail: "not found" }, 404);
    }
    const limitStr = searchParams.get("limit");
    const limit = limitStr ? parseInt(limitStr, 10) : 2000;
    // use graph-80 as default source; if limit >80 we could use graph-2000 but spec says slice by limit
    // choose dataset: if limit <=200 and id not requiring large, use graph-80 else graph-2000 for trunc test
    // For pagination correctness we use graph2000 when limit large to show trunc logic
    const src = limit > 80 ? (graph2000 as { nodes: unknown[]; edges: unknown[]; positions: Record<string, { x: number; y: number }> }) : (graph80 as { nodes: unknown[]; edges: unknown[]; positions: Record<string, { x: number; y: number }> });
    // but to keep deterministic with spec, default use graph-80 sliced, and for large we slice from graph-2000 if available
    // simpler: if requesting limit 2000 and dataset graph-80 has 80 nodes, we return 80 regardless – truncated false
    // For handler tests expecting truncate true at limit 2000, we use graph-2000 when explicitly testing?
    // We'll decide: if src is graph2000 we slice; else graph80
    // If total nodes > limit, truncate
    const nodes = (src.nodes as typeof graph80.nodes).slice(0, limit);
    const allowedIds = new Set(nodes.map((n) => n.id));
    const edges = (src.edges as typeof graph80.edges)
      .filter((e) => allowedIds.has(e.source) && allowedIds.has(e.target))
      .slice(0, limit * 2);
    const positions: Record<string, { x: number; y: number }> = {};
    for (const n of nodes) {
      const p = (src.positions as Record<string, { x: number; y: number }>)[n.id];
      if (p) positions[n.id] = p;
    }
    return jsonResponse({ nodes, edges, positions }, 200);
  }

  // GET /api/replay?at=ISO8601
  if (method === "GET" && pathname === "/api/replay") {
    let at = searchParams.get("at");
    if (!at) {
      return jsonResponse({ detail: "Missing at" }, 422);
    }
    // handle unencoded + decoded as space (browser query encoding)
    if (at.includes(" ") && !at.includes("+")) {
      at = at.replace(" ", "+");
    }
    let date: Date;
    try {
      date = parseISOWithTZ(at);
      if (Number.isNaN(date.getTime())) return jsonResponse({ detail: "Missing at" }, 422);
    } catch {
      return jsonResponse({ detail: "Missing at" }, 422);
    }
    // filter rows where timestamp <= at limit 1000
    const rows = (replayRows as { timestamp: string }[])
      .filter((r) => new Date(r.timestamp).getTime() <= date.getTime())
      .slice(0, 1000);
    return jsonResponse({ rows, count: rows.length, at }, 200);
  }

  // GET /api/geo/{ip}
  if (method === "GET" && pathname.startsWith("/api/geo/")) {
    const ip = decodeURIComponent(pathname.replace("/api/geo/", "").split("/")[0] ?? "");
    // find in centroids
    const found = (geoCentroids as typeof geoCentroids).find((c) => c.ip === ip);
    if (found) {
      return jsonResponse(found, 200);
    }
    // derived
    let h = 0;
    for (let i = 0; i < ip.length; i++) h = (h * 31 + ip.charCodeAt(i)) >>> 0;
    const lat = (h % 180) - 90 + Math.random() * 0.5;
    const lng = (h % 360) - 180 + Math.random() * 0.5;
    // hint only, never WHERE filter — radius is display hint per schema.sql
    return jsonResponse(
      {
        ip,
        country: "US",
        city: "Unknown",
        asn: 15169,
        lat: Math.round(lat * 100) / 100,
        lng: Math.round(lng * 100) / 100,
        radius: 500,
        accuracy_radius: 500,
        tier: "tier2",
      },
      200,
    );
  }

  // GET /api/alerts?limit=50
  if (method === "GET" && pathname === "/api/alerts") {
    const limitStr = searchParams.get("limit");
    const limit = limitStr ? parseInt(limitStr, 10) : 50;
    const alerts = [
      { id: "alert-123", p: 0.92, tier: "Critical", message: "High risk cluster", community_id: 1, ts: new Date().toISOString() },
      { id: "alert-124", p: 0.75, tier: "High", message: "Suspicious flow", community_id: 2, ts: new Date().toISOString() },
      { id: "alert-125", p: 0.6, tier: "Medium", message: "Anomaly detected", community_id: 3, ts: new Date().toISOString() },
    ].slice(0, Math.min(limit, 3));
    return jsonResponse(alerts, 200);
  }

  return jsonResponse({ detail: "not found" }, 404);
}

let originalFetch: typeof fetch | null = null;

export function installMockFetch(): void {
  if (originalFetch) return;
  originalFetch = globalThis.fetch;
  globalThis.fetch = mockFetch as unknown as typeof fetch;
}

export function restoreMockFetch(): void {
  if (originalFetch) {
    globalThis.fetch = originalFetch;
    originalFetch = null;
  }
}
