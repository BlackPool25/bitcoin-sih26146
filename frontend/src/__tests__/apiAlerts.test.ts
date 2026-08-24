import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { listAlerts, getEvidence, tierFromP } from "@/api/alerts";
import { getMockAlerts } from "@/mocks/alerts.mock";
import { getMockEvidence } from "@/mocks/evidence.mock";

// Helper to craft a mock Response-like for apiFetch
function mockJsonResponse(data: unknown, status = 200, ok = true): Response {
  const text = JSON.stringify(data);
  return {
    ok,
    status,
    headers: {
      get: (name: string) => (name.toLowerCase() === "content-type" ? "application/json" : null),
    },
    text: async () => text,
  } as unknown as Response;
}

function mockTextResponse(detail: string, status = 404): Response {
  return {
    ok: false,
    status,
    headers: {
      get: (name: string) => (name.toLowerCase() === "content-type" ? "application/json" : null),
    },
    text: async () => JSON.stringify({ detail }),
  } as unknown as Response;
}

const originalFetch = globalThis.fetch;

describe("api/alerts — listAlerts and getEvidence fallback", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("tierFromP maps correctly", () => {
    expect(tierFromP(0.95)).toBe("critical");
    expect(tierFromP(0.9)).toBe("high");
    expect(tierFromP(0.75)).toBe("high");
    expect(tierFromP(0.74)).toBe("medium");
    expect(tierFromP(0.5)).toBe("medium");
    expect(tierFromP(0.49)).toBe("low");
  });

  it("listAlerts fetch success returns alerts with correct query params", async () => {
    const alerts = getMockAlerts({ limit: 2 }).alerts.slice(0, 2);
    const payload = { alerts, count: 2, limit: 2, offset: 0 };
    const fetchSpy = vi.fn(async (url: RequestInfo | URL) => {
      const s = typeof url === "string" ? url : url.toString();
      expect(s).toContain("/api/alerts");
      expect(s).toContain("limit=2");
      expect(s).toContain("tier=high");
      expect(s).toContain("q=");
      return mockJsonResponse(payload);
    }) as unknown as typeof fetch;
    globalThis.fetch = fetchSpy;

    const res = await listAlerts({ limit: 2, tier: "high", q: "bc1q" });
    expect(res.alerts).toHaveLength(2);
    expect(res.limit).toBe(2);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("listAlerts handles bare array response (legacy mockFetch)", async () => {
    const alerts = getMockAlerts({ limit: 1 }).alerts;
    const fetchSpy = vi.fn(async () => mockJsonResponse(alerts)) as unknown as typeof fetch;
    globalThis.fetch = fetchSpy;
    const res = await listAlerts({ limit: 1 });
    expect(res.alerts).toHaveLength(1);
    expect(res.count).toBe(1);
  });

  it("listAlerts fallback to mock on network reject", async () => {
    const fetchSpy = vi.fn(async () => {
      throw new Error("Network down");
    }) as unknown as typeof fetch;
    globalThis.fetch = fetchSpy;
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const res = await listAlerts({ limit: 5, tier: "critical" });
    // mock fallback should return critical filtered mock (at least some)
    expect(res.alerts.length).toBeGreaterThan(0);
    for (const al of res.alerts) expect(al.tier).toBe("critical");
    expect(warnSpy).toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  it("listAlerts fallback on 404 response", async () => {
    const fetchSpy = vi.fn(async () => mockTextResponse("Not found", 404)) as unknown as typeof fetch;
    globalThis.fetch = fetchSpy;
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const res = await listAlerts({ limit: 3 });
    expect(res.alerts.length).toBe(3);
    expect(warnSpy).toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  it("listAlerts respects AbortSignal — abort propagates", async () => {
    const controller = new AbortController();
    controller.abort();
    const abortErr = Object.assign(new Error("Aborted"), { name: "AbortError" });
    const fetchSpy = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
      if (init?.signal?.aborted) throw abortErr;
      return mockJsonResponse({ alerts: [], count: 0, limit: 50, offset: 0 });
    }) as unknown as typeof fetch;
    globalThis.fetch = fetchSpy;
    await expect(listAlerts({}, { signal: controller.signal })).rejects.toThrow();
  });

  it("getEvidence fetch success returns evidence", async () => {
    const id = getMockAlerts({ limit: 1 }).alerts[0].alert_id;
    const evidence = getMockEvidence(id);
    expect(evidence).toBeDefined();
    const fetchSpy = vi.fn(async (url: RequestInfo | URL) => {
      const s = typeof url === "string" ? url : url.toString();
      expect(s).toContain(`/api/evidence/${id}`);
      return mockJsonResponse(evidence);
    }) as unknown as typeof fetch;
    globalThis.fetch = fetchSpy;
    const res = await getEvidence(id);
    expect(res.alert_id).toBe(id);
    expect(res.nl).toContain("flagged");
  });

  it("getEvidence fallback to mock on 404", async () => {
    const id = getMockAlerts({ limit: 1 }).alerts[0].alert_id;
    const fetchSpy = vi.fn(async () => mockTextResponse("Not found", 404)) as unknown as typeof fetch;
    globalThis.fetch = fetchSpy;
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const res = await getEvidence(id);
    expect(res.alert_id).toBe(id);
    expect(res.shap).toBeDefined();
    expect(warnSpy).toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  it("getEvidence fallback on network error with synthetic id", async () => {
    const id = "f".repeat(64); // valid 64hex but not in mockEvidenceMap → generates fallback
    const fetchSpy = vi.fn(async () => {
      throw new Error("timeout");
    }) as unknown as typeof fetch;
    globalThis.fetch = fetchSpy;
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const res = await getEvidence(id);
    expect(res.alert_id).toBe(id);
    expect(res.nl).toContain("flagged");
    warnSpy.mockRestore();
  });

  it("getEvidence throws when no mock fallback for invalid id", async () => {
    const id = "not-hex-id";
    const fetchSpy = vi.fn(async () => mockTextResponse("Not found", 404)) as unknown as typeof fetch;
    globalThis.fetch = fetchSpy;
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    await expect(getEvidence(id)).rejects.toThrow();
    warnSpy.mockRestore();
  });

  it("getEvidence respects AbortSignal", async () => {
    const controller = new AbortController();
    controller.abort();
    const abortErr = Object.assign(new Error("Aborted"), { name: "AbortError" });
    const fetchSpy = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
      if (init?.signal?.aborted) throw abortErr;
      return mockJsonResponse(getMockEvidence(getMockAlerts({ limit: 1 }).alerts[0].alert_id));
    }) as unknown as typeof fetch;
    globalThis.fetch = fetchSpy;
    await expect(getEvidence("a".repeat(64), controller.signal)).rejects.toThrow();
  });

  it("buildAlertsQuery defaults limit 50 and sort handling", async () => {
    // Check that default limit 50 is sent when not specified
    const captured: string[] = [];
    const fetchSpy = vi.fn(async (url: RequestInfo | URL) => {
      captured.push(typeof url === "string" ? url : url.toString());
      return mockJsonResponse({ alerts: [], count: 0, limit: 50, offset: 0 });
    }) as unknown as typeof fetch;
    globalThis.fetch = fetchSpy;
    await listAlerts({});
    expect(captured[0]).toContain("limit=50");
    captured.length = 0;
    await listAlerts({ sort: "-p", offset: 10, q: "test" });
    expect(captured[0]).toContain("sort=-p");
    expect(captured[0]).toContain("offset=10");
    expect(captured[0]).toContain("q=test");
  });
});
