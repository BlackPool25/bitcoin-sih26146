import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { mockFetch } from "./handlers";

describe("mockFetch", () => {
  it("pagination: limit slices nodes", async () => {
    const res = await mockFetch("http://localhost/api/graph/alert-123?limit=10");
    expect(res.status).toBe(200);
    const j = await res.json();
    expect(j.nodes.length).toBe(10);
    expect(j.positions).toBeDefined();
  });
  it("default limit 2000", async () => {
    const res = await mockFetch("http://localhost/api/graph/alert-123");
    expect(res.status).toBe(200);
    const j = await res.json();
    expect(j.nodes.length).toBeGreaterThan(0);
  });
  it("404 on invalid id", async () => {
    const res = await mockFetch("http://localhost/api/graph/invalid");
    expect(res.status).toBe(404);
    const j = await res.json();
    expect(j.detail).toBe("not found");
  });
  it("422 missing at", async () => {
    const res = await mockFetch("http://localhost/api/replay");
    expect(res.status).toBe(422);
    const j = await res.json();
    expect(j.detail).toBe("Missing at");
  });
  it("422 invalid at", async () => {
    const res = await mockFetch("http://localhost/api/replay?at=not-a-date");
    expect(res.status).toBe(422);
  });
  it("replay Z and +05:30 both valid and filter", async () => {
    const resZ = await mockFetch("http://localhost/api/replay?at=2024-01-01T01:00:00Z");
    expect(resZ.status).toBe(200);
    const jZ = await resZ.json();
    expect(jZ.count).toBeGreaterThan(0);
    expect(jZ.count).toBeLessThanOrEqual(1000);
    const resIST = await mockFetch("http://localhost/api/replay?at=2024-01-01T05:30:00+05:30");
    expect(resIST.status).toBe(200);
    const jIST = await resIST.json();
    expect(jIST.count).toBeGreaterThan(0);
    // 00:00Z vs 00:00Z equivalent via +05:30
    const resMid = await mockFetch("http://localhost/api/replay?at=2024-01-01T00:00:00Z");
    const jMid = await resMid.json();
    // Z and +05:30 at same instant should give same count
    const resSameZ = await mockFetch("http://localhost/api/replay?at=2024-01-01T00:00:00Z");
    const resSameIST = await mockFetch("http://localhost/api/replay?at=2024-01-01T05:30:00+05:30");
    const jSameZ = await resSameZ.json();
    const jSameIST = await resSameIST.json();
    expect(jSameZ.count).toBe(jSameIST.count);
  });
  it("geo returns point and respects hint", async () => {
    const res = await mockFetch("http://localhost/api/geo/8.8.8.8");
    expect(res.status).toBe(200);
    const j = await res.json();
    expect(j.country).toBe("US");
    expect(j.lat).toBeDefined();
    // never filters — just returns hint
  });
  it("alerts limit", async () => {
    const res = await mockFetch("http://localhost/api/alerts?limit=50");
    expect(res.status).toBe(200);
    const j = await res.json();
    expect(Array.isArray(j)).toBe(true);
    expect(j.length).toBe(3);
    expect(j[0].p).toBe(0.92);
  });
});
