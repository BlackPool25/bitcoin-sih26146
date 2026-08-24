import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import type { CyJson } from "@/types/graph";
import graph80 from "@/mocks/fixtures/graph-80.json";

// Mock sigma to avoid WebGL in jsdom
vi.mock("sigma", () => {
  return {
    default: class MockSigma {
      graph: unknown;
      container: unknown;
      settings: unknown;
      constructor(graph: unknown, container: unknown, settings: unknown) {
        this.graph = graph;
        this.container = container;
        this.settings = settings;
      }
      kill() {}
    },
    Sigma: class MockSigma2 {
      kill() {}
    },
  };
});

import GraphView from "./GraphView";

describe("GraphView sigma renderer", () => {
  const originalLocation = window.location;

  beforeEach(() => {
    vi.stubGlobal("location", { ...originalLocation } as unknown as Location);
  });

  afterEach(() => {
    // restore search
    Object.defineProperty(window, "location", {
      value: originalLocation,
      writable: true,
    });
    vi.unstubAllGlobals();
  });

  it("default renders cytoscape view (no param)", () => {
    // ensure no renderer param
    Object.defineProperty(window, "location", {
      value: { ...originalLocation, search: "" } as unknown as Location,
      writable: true,
    });
    render(<GraphView cyJson={null} />);
    expect(screen.getByTestId("graph-view")).toBeInTheDocument();
    expect(screen.queryByTestId("sigma-view")).not.toBeInTheDocument();
  });

  it("mock window.location.search = ?renderer=sigma -> renders sigma-view", async () => {
    Object.defineProperty(window, "location", {
      value: { ...originalLocation, search: "?renderer=sigma" } as unknown as Location,
      writable: true,
    });
    render(<GraphView cyJson={graph80 as unknown as CyJson} />);
    expect(screen.getByTestId("sigma-view")).toBeInTheDocument();
    expect(screen.queryByTestId("graph-view")).not.toBeInTheDocument();
  });

  it("prop renderer=sigma overrides URL and renders sigma-view", () => {
    Object.defineProperty(window, "location", {
      value: { ...originalLocation, search: "" } as unknown as Location,
      writable: true,
    });
    render(<GraphView cyJson={graph80 as unknown as CyJson} renderer="sigma" />);
    expect(screen.getByTestId("sigma-view")).toBeInTheDocument();
  });

  it("prop renderer=cytoscape forces cytoscape even with ?renderer=sigma in URL", () => {
    Object.defineProperty(window, "location", {
      value: { ...originalLocation, search: "?renderer=sigma" } as unknown as Location,
      writable: true,
    });
    render(<GraphView cyJson={graph80 as unknown as CyJson} renderer="cytoscape" />);
    expect(screen.getByTestId("graph-view")).toBeInTheDocument();
  });

  it("sigma view renders with graph data without crashing", async () => {
    Object.defineProperty(window, "location", {
      value: { ...originalLocation, search: "?renderer=sigma" } as unknown as Location,
      writable: true,
    });
    render(<GraphView cyJson={graph80 as unknown as CyJson} />);
    const el = screen.getByTestId("sigma-view");
    expect(el).toBeInTheDocument();
    // wait for async sigma init
    await new Promise((r) => setTimeout(r, 50));
    expect(el).toBeInTheDocument();
  });
});
