import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import App from "./App";
import { mockFetch, restoreMockFetch } from "./mocks/handlers";
import { toCyJsonFromRows } from "./types/replay";

describe("App integration M4 Sync selectedAlertId", () => {
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    restoreMockFetch();
    fetchSpy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const urlStr =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : (input as Request).url;
      if (urlStr.includes("/api/alerts")) {
        return new Response(JSON.stringify({ detail: "not found" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (urlStr.includes("/api/evidence/")) {
        return new Response(JSON.stringify({ detail: "not found" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        });
      }
      return mockFetch(urlStr, init);
    });
    globalThis.fetch = fetchSpy as unknown as typeof fetch;
  });

  afterEach(() => {
    restoreMockFetch();
    vi.restoreAllMocks();
  });

  it("null selectedAlertId shows Select an alert and no graph fetch", async () => {
    render(<App />);
    expect(screen.getByTestId("graph-empty-select")).toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 400));
    const graphCalls = (fetchSpy.mock.calls as unknown as [string][]).filter(
      (c) => String(c[0]).includes("/api/graph/"),
    );
    expect(graphCalls.length).toBe(0);
    expect(screen.getByTestId("graph-view")).toBeInTheDocument();
  });

  it("selectedAlertId change triggers GET /api/graph/{id}?limit=2000 and populates GraphView", async () => {
    render(<App />);
    fireEvent.click(screen.getByTestId("alert-btn-alert-123"));
    await waitFor(
      () => {
        const calls = (fetchSpy.mock.calls as unknown as [string][]).map((c) => String(c[0]));
        expect(calls.find((u) => u.includes("/api/graph/alert-123?limit=2000"))).toBeDefined();
      },
      { timeout: 3000 },
    );
    await waitFor(() => expect(screen.queryByTestId("graph-loading")).not.toBeInTheDocument(), {
      timeout: 3000,
    });
    expect(screen.queryByTestId("graph-empty-select")).not.toBeInTheDocument();
    expect(screen.queryByTestId("graph-empty")).not.toBeInTheDocument();
    expect(screen.getByTestId("graph-view")).toBeInTheDocument();
  });

  it("invalid id 404 shows no subgraph empty state", async () => {
    render(<App />);
    fireEvent.click(screen.getByTestId("alert-btn-invalid"));
    await waitFor(
      () => {
        const calls = (fetchSpy.mock.calls as unknown as [string][]).map((c) => String(c[0]));
        expect(calls.some((u) => u.includes("/api/graph/invalid?limit=2000"))).toBe(true);
      },
      { timeout: 3000 },
    );
    await waitFor(() => expect(screen.getByTestId("graph-empty")).toBeInTheDocument(), {
      timeout: 3000,
    });
    expect(screen.getByText(/no subgraph/i)).toBeInTheDocument();
  });

  it("ReplaySlider -> GraphView lifts cy.json via toCyJsonFromRows", async () => {
    render(<App />);
    await waitFor(
      () => {
        const calls = (fetchSpy.mock.calls as unknown as [string][]).map((c) => String(c[0]));
        expect(calls.some((u) => u.includes("/api/replay?at="))).toBe(true);
      },
      { timeout: 3000 },
    );
    await new Promise((r) => setTimeout(r, 350));
    expect(screen.getByTestId("graph-view")).toBeInTheDocument();
    expect(screen.getByTestId("geo-map")).toBeInTheDocument();
    const res = await mockFetch("http://localhost/api/replay?at=2024-01-01T01:00:00Z");
    const data = (await res.json()) as { rows: unknown[]; count: number; at: string };
    expect(data.rows.length).toBeGreaterThan(0);
    const cy = toCyJsonFromRows(data.rows as never);
    expect(cy.nodes.length).toBeGreaterThan(0);
    expect(cy.positions).toBeDefined();
  });

  it("clears cyJson when deselecting after selection", async () => {
    render(<App />);
    fireEvent.click(screen.getByTestId("alert-btn-alert-123"));
    await waitFor(
      () => {
        const calls = (fetchSpy.mock.calls as unknown as [string][]).map((c) => String(c[0]));
        expect(calls.some((u) => u.includes("/api/graph/alert-123"))).toBe(true);
      },
      { timeout: 5000 },
    );
    await waitFor(() => expect(screen.queryByTestId("graph-loading")).not.toBeInTheDocument(), {
      timeout: 5000,
    });
    fireEvent.click(screen.getByTestId("alert-btn-invalid"));
    await waitFor(() => expect(screen.getByTestId("graph-empty")).toBeInTheDocument(), {
      timeout: 5000,
    });
    fireEvent.click(screen.getByTestId("alert-btn-alert-124"));
    await waitFor(() => expect(screen.queryByTestId("graph-empty")).not.toBeInTheDocument(), {
      timeout: 5000,
    });
  }, 20000);
});
