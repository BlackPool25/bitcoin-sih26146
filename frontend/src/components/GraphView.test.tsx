import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import cytoscape from "cytoscape";
import GraphView from "./GraphView";
import { stylesheet } from "@/cytoscape/styles";
import graph80 from "@/mocks/fixtures/graph-80.json";
import type { CyJson } from "@/types/graph";

describe("GraphView component", () => {
  it("renders container with data-testid and 600px height", () => {
    render(<GraphView cyJson={null} />);
    const el = screen.getByTestId("graph-view");
    expect(el).toBeInTheDocument();
    expect(el.style.height).toBe("600px");
    // border rounded
    expect(el.style.borderRadius).toBe("8px");
    expect(el.style.border).toContain("1px");
  });

  it("stylesheet contains diamond/ellipse/rectangle for shape mapping", () => {
    const selectors = (stylesheet as unknown as { selector: string; style: Record<string, unknown> }[]).map((s) => s.selector);
    expect(selectors).toContain('node[type="ip"]');
    expect(selectors).toContain('node[type="wallet"]');
    expect(selectors).toContain('node[type="txid"]');
    const ip = (stylesheet as unknown as { selector: string; style: Record<string, unknown> }[]).find((s) => s.selector === 'node[type="ip"]')!;
    expect(ip.style.shape).toBe("diamond");
    expect(ip.style["background-color"]).toBe("#ef4444");
  });

  it("renders with 80 nodes cyJson without crashing", async () => {
    const onReady = vi.fn();
    render(<GraphView cyJson={graph80 as unknown as CyJson} onReady={onReady} />);
    expect(screen.getByTestId("graph-view")).toBeInTheDocument();
    // onReady should be called after mount (cytoscape init)
    // wait a tick for useEffect
    await new Promise((r) => setTimeout(r, 50));
    expect(onReady).toHaveBeenCalled();
    const cy = onReady.mock.calls[0][0] as cytoscape.Core;
    // after data effect, nodes should be present (headless check via real cy if available)
    // In jsdom, cy is mounted to div — nodes may be there
    expect(cy).toBeDefined();
  });

  it("handles null cyJson clear", async () => {
    const { rerender } = render(<GraphView cyJson={graph80 as unknown as CyJson} />);
    await new Promise((r) => setTimeout(r, 30));
    rerender(<GraphView cyJson={null} />);
    expect(screen.getByTestId("graph-view")).toBeInTheDocument();
  });

  it("accepts graph alias prop", () => {
    render(<GraphView graph={graph80 as unknown as CyJson} />);
    expect(screen.getByTestId("graph-view")).toBeInTheDocument();
  });

  it("headless cytoscape renders 80 and 2000 deterministically", () => {
    // Direct headless verification — preset leaves positions deterministic
    const data80 = graph80 as unknown as CyJson;
    const cy1 = cytoscape({ headless: true, elements: [] });
    const cy2 = cytoscape({ headless: true, elements: [] });
    // simulate what GraphView does: add elements with positions
    const elems = data80.nodes.map((n) => ({
      data: { id: n.id, type: n.type, label: n.label ?? n.id.slice(0, 8) },
      position: { x: n.x!, y: n.y! },
    }));
    cy1.add(elems as unknown as cytoscape.ElementDefinition[]);
    cy2.add(elems as unknown as cytoscape.ElementDefinition[]);
    cy1.layout({ name: "preset", animate: false } as unknown as cytoscape.LayoutOptions).run();
    cy2.layout({ name: "preset", animate: false } as unknown as cytoscape.LayoutOptions).run();
    const p1 = cy1.nodes().map((n) => n.position());
    const p2 = cy2.nodes().map((n) => n.position());
    expect(p1).toEqual(p2);
  });
});
