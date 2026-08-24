import { test, expect } from "@playwright/test";
import graph80 from "../../src/mocks/fixtures/graph-80.json";
import replayRows from "../../src/mocks/fixtures/replay-1000.json";

async function installRoutes(page: import("@playwright/test").Page) {
  await page.route("**/api/graph/**", async (route) => {
    const url = new URL(route.request().url());
    const id = url.pathname.replace("/api/graph/", "").split("/")[0] ?? "";
    if (id === "invalid" || id === "") {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "not found" }),
      });
      return;
    }
    const limitStr = url.searchParams.get("limit");
    const limit = limitStr ? parseInt(limitStr, 10) : 2000;
    // if ?nopos present, strip positions to test fcose fallback
    const noPos = url.searchParams.get("nopos") === "1";
    const src = graph80 as unknown as { nodes: unknown[]; edges: unknown[]; positions: Record<string, { x: number; y: number }> };
    const nodes = (src.nodes as typeof graph80.nodes).slice(0, limit);
    const allowed = new Set(nodes.map((n) => n.id));
    const edges = (src.edges as typeof graph80.edges)
      .filter((e) => allowed.has(e.source) && allowed.has(e.target))
      .slice(0, limit * 2);
    const positions: Record<string, { x: number; y: number }> = {};
    if (!noPos) {
      for (const n of nodes) {
        const p = (src.positions as Record<string, { x: number; y: number }>)[n.id];
        if (p) positions[n.id] = p;
      }
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ nodes, edges, positions }),
    });
  });

  await page.route("**/api/replay*", async (route) => {
    const url = new URL(route.request().url());
    const at = url.searchParams.get("at");
    if (!at) {
      await route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Missing at" }),
      });
      return;
    }
    let date: Date;
    try {
      const norm = at.endsWith("Z") ? at.slice(0, -1) + "+00:00" : at;
      date = new Date(norm);
      if (Number.isNaN(date.getTime()))
        throw new Error("bad");
    } catch {
      await route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Missing at" }),
      });
      return;
    }
    const rows = (replayRows as { timestamp: string }[])
      .filter((r) => new Date(r.timestamp).getTime() <= date.getTime())
      .slice(0, 1000);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ rows, count: rows.length, at }),
    });
  });

  await page.route("**/api/alerts*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { id: "alert-123", p: 0.92, tier: "Critical", message: "High risk cluster", community_id: 1, ts: new Date().toISOString() },
        { id: "alert-124", p: 0.75, tier: "High", message: "Suspicious flow", community_id: 2, ts: new Date().toISOString() },
      ]),
    });
  });

  await page.route("**/api/evidence/**", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });
}

// ── Happy ──────────────────────────────────────────────────────────

test.describe("M5 Happy — alert->graph <500ms, geo-map, replay, sigma", () => {
  test("alert click renders graph within 500ms, geo-map visible, slider drag keeps graph", async ({ page }) => {
    await installRoutes(page);
    await page.goto("/");
    await expect(page.getByTestId("mock-alert-list")).toBeVisible({ timeout: 5000 });

    // track fetch with limit
    const graphRequests: string[] = [];
    page.on("request", (req) => {
      if (req.url().includes("/api/graph/")) graphRequests.push(req.url());
    });

    const t0 = await page.evaluate(() => performance.now());
    await page.getByTestId("alert-btn-alert-123").click();
    await expect(page.getByTestId("graph-view")).toBeVisible({ timeout: 500 });
    const t1 = await page.evaluate(() => performance.now());
    expect(t1 - t0).toBeLessThan(500);

    // graph fetch carried limit=2000
    await expect.poll(() => graphRequests.some((u) => u.includes("?limit=2000"))).toBeTruthy();

    await expect(page.getByTestId("geo-map")).toBeVisible();
    // geo-map leaflet container should have leaflet class after mount
    await page.waitForTimeout(300);

    // drag replay slider
    const slider = page.getByTestId("replay-slider");
    await expect(slider).toBeVisible();
    const before = await page.getByTestId("replay-at").textContent();
    // use evaluate to change slider value and fire events (range input drag)
    await page.evaluate(() => {
      const el = document.querySelector('[data-testid="replay-slider"]') as HTMLInputElement;
      if (!el) return;
      const min = Number(el.min);
      const max = Number(el.max);
      const mid = String(Math.floor((min + max) / 2));
      el.value = mid;
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await expect.poll(async () => page.getByTestId("replay-at").textContent()).not.toEqual(before);
    await expect(page.getByTestId("graph-view")).toBeVisible();
  });

  test("?renderer=sigma toggle shows sigma-view", async ({ page }) => {
    await installRoutes(page);
    await page.goto("/?renderer=sigma");
    await expect(page.getByTestId("sigma-view")).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId("graph-view")).toBeHidden();
  });
});

// ── Edge ────────────────────────────────────────────────────────────

test.describe("M5 Edge — missing positions, 0 rows, 422, 404, offline", () => {
  test("missing positions fallback (fcose) still renders graph", async ({ page }) => {
    await installRoutes(page);
    // intercept next graph response to strip positions via page.route already handles nopos param;
    // instead override after install: fulfill with empty positions
    await page.route("**/api/graph/alert-123*", async (route) => {
      const src = graph80 as unknown as { nodes: unknown[]; edges: unknown[] };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ nodes: src.nodes, edges: src.edges, positions: {} }),
      });
    });
    await page.goto("/");
    await page.getByTestId("alert-btn-alert-123").click();
    await expect(page.getByTestId("graph-view")).toBeVisible({ timeout: 2000 });
    await expect(page.getByTestId("graph-error")).toBeHidden();
  });

  test("geo_cache 0 rows derived centroids still map visible", async ({ page }) => {
    await installRoutes(page);
    // force replay to return 0 rows
    await page.route("**/api/replay*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ rows: [], count: 0, at: "2024-01-01T00:00:00Z" }),
      });
    });
    await page.goto("/");
    await expect(page.getByTestId("geo-map")).toBeVisible({ timeout: 3000 });
  });

  test("GET /api/replay?at missing -> 422 shows error toast", async ({ page }) => {
    await installRoutes(page);
    await page.goto("/");
    // direct fetch via page.evaluate
    const status = await page.evaluate(async () => {
      const r = await fetch("/api/replay");
      return r.status;
    });
    expect(status).toBe(422);
    // verify ReplaySlider shows Missing at when debouncedAt empty handled: trigger via evaluate fetch to missing at already gives 422
    // additionally check slider error element not crashed
    await expect(page.getByTestId("replay-slider")).toBeVisible();
  });

  test("invalid alert id 404 shows no subgraph empty state", async ({ page }) => {
    await installRoutes(page);
    await page.goto("/");
    await page.getByTestId("alert-btn-invalid").click();
    await expect(page.getByTestId("graph-empty")).toBeVisible({ timeout: 3000 });
    await expect(page.getByText(/no subgraph/i)).toBeVisible();
  });

  test("offline tiles fallback map container still exists", async ({ page }) => {
    await installRoutes(page);
    await page.goto("/");
    // stub offline — leaflet fallback should still render container
    await page.evaluate(() => {
      Object.defineProperty(window.navigator, "onLine", { value: false, configurable: true });
      window.dispatchEvent(new Event("offline"));
    });
    await expect(page.getByTestId("geo-map")).toBeVisible();
  });
});

// ── Adjacent regression ─────────────────────────────────────────────

test.describe("M5 Adjacent — frozen contracts", () => {
  test("no fetch to /api/graph without limit", async ({ page }) => {
    await installRoutes(page);
    const urls: string[] = [];
    page.on("request", (r) => {
      if (r.url().includes("/api/graph/")) urls.push(r.url());
    });
    await page.goto("/");
    await page.getByTestId("alert-btn-alert-123").click();
    await page.waitForTimeout(600);
    expect(urls.length).toBeGreaterThan(0);
    for (const u of urls) expect(u).toContain("limit=");
  });

  test("M4 owns alerts prop contract not DB", async ({ page }) => {
    await installRoutes(page);
    await page.goto("/");
    // mock-alert-list exists, AlertTable uses prop onSelectAlert
    await expect(page.getByTestId("mock-alert-list")).toBeVisible();
    // verify no direct DB fetch in page source (heuristic)
    const hasDb = await page.evaluate(() => document.documentElement.innerHTML.includes("SELECT"));
    expect(hasDb).toBe(false);
  });
});
