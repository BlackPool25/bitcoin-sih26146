import { describe, it, expect } from "vitest";
import { cyJsonToGraphology, hash } from "./toGraphology";
import type { CyJson } from "@/types/graph";
import graph80 from "@/mocks/fixtures/graph-80.json";

describe("hash", () => {
  it("deterministic: same input same output", () => {
    expect(hash("wallet_0")).toBe(hash("wallet_0"));
  });
  it("different ids produce different hashes", () => {
    expect(hash("wallet_0")).not.toBe(hash("wallet_1"));
  });
  it("hash(n.id)%1000 in range", () => {
    const h = hash("192.168.1.1") % 1000;
    expect(h).toBeGreaterThanOrEqual(0);
    expect(h).toBeLessThan(1000);
  });
});

describe("cyJsonToGraphology", () => {
  it("80 nodes conversion gives graph.order ===80", () => {
    const data = graph80 as unknown as CyJson;
    const { graph, nodeCount, edgeCount } = cyJsonToGraphology(data);
    expect(graph.order).toBe(80);
    expect(nodeCount).toBe(80);
    expect(graph.size).toBeGreaterThan(0);
    expect(edgeCount).toBe(graph.size);
  });

  it("node attributes: label fallback, x/y, size, color, type", () => {
    const data: CyJson = {
      nodes: [
        { id: "n1", type: "wallet", degree: 5, p: 0.9 },
        { id: "n2", type: "ip", x: 123, y: 456, label: "custom label", degree: 2, p: 0.3 },
      ],
      edges: [],
    };
    const { graph } = cyJsonToGraphology(data);
    const a1 = graph.getNodeAttributes("n1");
    expect(a1.label).toBe("n1");
    expect(typeof a1.x).toBe("number");
    expect(typeof a1.y).toBe("number");
    expect(typeof a1.size).toBe("number");
    expect(a1.color).toBeTruthy();
    expect(a1.type).toBe("wallet");

    const a2 = graph.getNodeAttributes("n2");
    expect(a2.label).toBe("custom label");
    expect(a2.x).toBe(123);
    expect(a2.y).toBe(456);
    expect(a2.type).toBe("ip");
  });

  it("x/y fallback uses hash deterministically", () => {
    const data: CyJson = {
      nodes: [{ id: "wallet_0", type: "wallet" }],
      edges: [],
    };
    const { graph: g1 } = cyJsonToGraphology(data);
    const { graph: g2 } = cyJsonToGraphology(data);
    expect(g1.getNodeAttribute("wallet_0", "x")).toBe(g2.getNodeAttribute("wallet_0", "x"));
    expect(g1.getNodeAttribute("wallet_0", "y")).toBe(g2.getNodeAttribute("wallet_0", "y"));
  });

  it("edges only added if both nodes exist", () => {
    const data: CyJson = {
      nodes: [{ id: "a", type: "wallet" }],
      edges: [
        { source: "a", target: "missing", type: "p2p" },
        { source: "a", target: "a", type: "p2p", id: "self" },
      ],
    };
    const { graph } = cyJsonToGraphology(data);
    expect(graph.size).toBe(1);
    expect((graph as unknown as { hasEdge: (k: string) => boolean }).hasEdge("self")).toBe(true);
  });

  it("handle duplicate edges via addEdgeWithKey", () => {
    const data: CyJson = {
      nodes: [
        { id: "a", type: "wallet" },
        { id: "b", type: "wallet" },
      ],
      edges: [
        { id: "e1", source: "a", target: "b", type: "p2p" },
        { id: "e1", source: "a", target: "b", type: "p2p" }, // duplicate id
        { id: "e2", source: "a", target: "b", type: "utxo" }, // same pair but different id would still be duplicate in non-multi graph, should be handled gracefully
      ],
    };
    const { graph } = cyJsonToGraphology(data);
    // at least one edge exists, duplicate not crash
    expect(graph.size).toBeGreaterThanOrEqual(1);
    expect((graph as unknown as { hasEdge: (k: string) => boolean }).hasEdge("e1")).toBe(true);
  });

  it("edge attributes color/size/label", () => {
    const data: CyJson = {
      nodes: [
        { id: "a", type: "wallet" },
        { id: "b", type: "ip" },
      ],
      edges: [{ source: "a", target: "b", type: "temporal", id: "e1" }],
    };
    const { graph } = cyJsonToGraphology(data);
    const attrs = graph.getEdgeAttributes("e1");
    expect(attrs.label).toBe("temporal");
    expect(attrs.color).toBe("#94a3b8");
    expect(attrs.size).toBe(1);
    expect(attrs.type).toBe("temporal");
  });

  it("color per type uses getNodeStyle mapping", () => {
    const data: CyJson = {
      nodes: [
        { id: "ip1", type: "ip" },
        { id: "w1", type: "wallet" },
        { id: "t1", type: "txid" },
      ],
      edges: [],
    };
    const { graph } = cyJsonToGraphology(data);
    expect(graph.getNodeAttribute("ip1", "color")).toBe("#ef4444");
    expect(graph.getNodeAttribute("w1", "color")).toBe("#22c55e");
    expect(graph.getNodeAttribute("t1", "color")).toBe("#a855f7");
  });

  it("size uses getNodeSize(degree,p)", () => {
    const data: CyJson = {
      nodes: [{ id: "n", type: "wallet", degree: 10, p: 0.5 }],
      edges: [],
    };
    const { graph } = cyJsonToGraphology(data);
    const size = graph.getNodeAttribute("n", "size") as number;
    expect(size).toBeGreaterThanOrEqual(16);
    expect(size).toBeLessThanOrEqual(64);
  });
});
