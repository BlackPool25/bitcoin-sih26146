import { describe, it, expect } from "vitest";
import cytoscape from "cytoscape";
import { applyCyJsonUpdate, hashPosition, buildElements } from "./update";
import type { CyJson } from "@/types/graph";
import graph80 from "@/mocks/fixtures/graph-80.json";
import graph2000 from "@/mocks/fixtures/graph-2000.json";

describe("hashPosition", () => {
  it("deterministic: same id same pos, no Math.random", () => {
    const a = hashPosition("wallet_0");
    const b = hashPosition("wallet_0");
    expect(a).toEqual(b);
  });
  it("different ids produce different positions", () => {
    const a = hashPosition("wallet_0");
    const b = hashPosition("wallet_1");
    expect(a).not.toEqual(b);
  });
});

describe("buildElements", () => {
  it("uses haystack class when count>500", () => {
    const nodes = (graph80 as unknown as CyJson).nodes.slice(0, 10);
    const edges = Array.from({ length: 600 }, (_, i) => ({
      id: `e${i}`,
      source: nodes[0]!.id,
      target: nodes[1]!.id,
      type: "p2p" as const,
    }));
    const elems = buildElements(nodes, edges, true);
    const edgeElems = elems.filter((e) => (e as unknown as { data: { source: string } }).data.source);
    expect(edgeElems[0]!.classes).toContain("haystack");
  });
  it("no haystack when count<=500", () => {
    const nodes = (graph80 as unknown as CyJson).nodes.slice(0, 10);
    const edges = Array.from({ length: 100 }, (_, i) => ({
      id: `e${i}`,
      source: nodes[0]!.id,
      target: nodes[1]!.id,
      type: "p2p" as const,
    }));
    const elems = buildElements(nodes, edges, false);
    const edgeElems = elems.filter((e) => (e as unknown as { data: { source: string } }).data.source);
    expect(edgeElems[0]!.classes).not.toContain("haystack");
  });
});

describe("applyCyJsonUpdate headless", () => {
  it("renders 80 nodes preset deterministic (same positions on re-run)", () => {
    const cy1 = cytoscape({ headless: true, elements: [] });
    const cy2 = cytoscape({ headless: true, elements: [] });
    const data = graph80 as unknown as CyJson;
    applyCyJsonUpdate(cy1, data);
    applyCyJsonUpdate(cy2, data);
    expect(cy1.nodes().length).toBe(80);
    expect(cy2.nodes().length).toBe(80);
    // preset leaves nodes at x,y from data — compare positions
    const pos1 = cy1.nodes().map((n) => n.position());
    const pos2 = cy2.nodes().map((n) => n.position());
    expect(pos1).toEqual(pos2);
  });

  it("renders 2000 nodes without animation via fcose fallback", () => {
    const cy = cytoscape({ headless: true, elements: [] });
    const data = graph2000 as unknown as CyJson;
    const res = applyCyJsonUpdate(cy, data);
    expect(cy.nodes().length).toBe(2000);
    expect(res.truncated).toBe(false);
    expect(res.total).toBe(2000);
  });

  it("truncates >2000 and filters edges", () => {
    const cy = cytoscape({ headless: true, elements: [] });
    const nodes = Array.from({ length: 2500 }, (_, i) => ({
      id: `n${i}`,
      type: "wallet" as const,
      x: i,
      y: i,
      degree: 1,
      p: 0.5,
    }));
    const edges = [
      { id: "e1", source: "n0", target: "n1", type: "p2p" as const },
      { id: "e2", source: "n0", target: "n3000", type: "p2p" as const },
    ];
    const data: CyJson = { nodes, edges };
    const res = applyCyJsonUpdate(cy, data, 2000);
    expect(res.truncated).toBe(true);
    expect(cy.nodes().length).toBe(2000);
    expect(cy.edges().length).toBe(1);
  });

  it("haystack when edges>500", () => {
    const cy = cytoscape({ headless: true, elements: [] });
    const nodes = Array.from({ length: 10 }, (_, i) => ({
      id: `n${i}`,
      type: "wallet" as const,
      x: i * 10,
      y: i * 10,
    }));
    const edges = Array.from({ length: 600 }, (_, i) => ({
      id: `e${i}`,
      source: "n0",
      target: "n1",
      type: "p2p" as const,
      weight: 1,
      amount: 1,
    }));
    applyCyJsonUpdate(cy, { nodes, edges });
    // all edges should have haystack class
    const firstEdge = cy.edges()[0]!;
    expect(firstEdge.hasClass("haystack")).toBe(true);
  });

  it("bezier when edges <=500 no haystack", () => {
    const cy = cytoscape({ headless: true, elements: [] });
    const nodes = Array.from({ length: 10 }, (_, i) => ({
      id: `n${i}`,
      type: "wallet" as const,
      x: i * 10,
      y: i * 10,
    }));
    const edges = Array.from({ length: 100 }, (_, i) => ({
      id: `e${i}`,
      source: "n0",
      target: "n1",
      type: "p2p" as const,
    }));
    applyCyJsonUpdate(cy, { nodes, edges });
    const firstEdge = cy.edges()[0]!;
    expect(firstEdge.hasClass("haystack")).toBe(false);
  });
});
