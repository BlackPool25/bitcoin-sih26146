import { describe, it, expect } from "vitest";
import { paginateGraph, formatTruncatedBadge } from "./pagination";
import type { GraphNode, GraphEdge } from "@/types/graph";

function makeNodes(n: number): GraphNode[] {
  return Array.from({ length: n }, (_, i) => ({ id: `n${i}`, type: "wallet" as const }));
}

describe("paginateGraph", () => {
  it("no truncation when under limit", () => {
    const nodes = makeNodes(10);
    const edges: GraphEdge[] = [{ id: "e1", source: "n0", target: "n1", type: "p2p" }];
    const r = paginateGraph(nodes, edges, 2000);
    expect(r.truncated).toBe(false);
    expect(r.total).toBe(10);
    expect(r.nodes.length).toBe(10);
    expect(r.edges.length).toBe(1);
  });
  it("slices nodes to limit and filters edges outside", () => {
    const nodes = makeNodes(2500);
    const edges: GraphEdge[] = [
      { id: "e1", source: "n0", target: "n1", type: "p2p" },
      { id: "e2", source: "n0", target: "n3000", type: "p2p" },
    ];
    const r = paginateGraph(nodes, edges, 2000);
    expect(r.truncated).toBe(true);
    expect(r.total).toBe(2500);
    expect(r.nodes.length).toBe(2000);
    expect(r.edges.length).toBe(1);
    expect(r.edges[0]!.id).toBe("e1");
  });
  it("handles 80 nodes no truncation", () => {
    const nodes = makeNodes(80);
    const edges: GraphEdge[] = [{ id: "e1", source: "n0", target: "n1", type: "utxo" }];
    const r = paginateGraph(nodes, edges, 2000);
    expect(r.truncated).toBe(false);
    expect(r.total).toBe(80);
  });
  it("handles 2000 exactly not truncated", () => {
    const nodes = makeNodes(2000);
    const r = paginateGraph(nodes, [], 2000);
    expect(r.truncated).toBe(false);
  });
  it("handles 273851 total truncated", () => {
    const nodes = makeNodes(273851);
    const r = paginateGraph(nodes, [], 2000);
    expect(r.truncated).toBe(true);
    expect(r.total).toBe(273851);
    expect(r.nodes.length).toBe(2000);
  });
  it("default limit 2000", () => {
    const nodes = makeNodes(3000);
    const r = paginateGraph(nodes, []);
    expect(r.nodes.length).toBe(2000);
  });
});

describe("formatTruncatedBadge", () => {
  it('formats as "showing 2000/273851"', () => {
    expect(formatTruncatedBadge(273851, 2000)).toBe("showing 2000/273851");
  });
  it('formats showing 80/80', () => {
    expect(formatTruncatedBadge(80, 80)).toBe("showing 80/80");
  });
  it('formats showing 2000/2000', () => {
    expect(formatTruncatedBadge(2000, 2000)).toBe("showing 2000/2000");
  });
});
