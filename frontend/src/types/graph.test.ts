import { describe, it, expect } from "vitest";
import { GraphNodeSchema, GraphEdgeSchema, shapeForType, truncateByLimit } from "./graph";

describe("graph zod", () => {
  it("valid GraphNode passes", () => {
    const res = GraphNodeSchema.safeParse({ id: "wallet_0", type: "wallet", degree: 5, p: 0.9, x: 100, y: 200 });
    expect(res.success).toBe(true);
  });
  it("invalid type rejected", () => {
    const res = GraphNodeSchema.safeParse({ id: "x", type: "invalid" });
    expect(res.success).toBe(false);
  });
  it("invalid edge type rejected via zod 3.23", () => {
    const r = GraphEdgeSchema.safeParse({ source: "a", target: "b", type: "bad" });
    expect(r.success).toBe(false);
  });
  it("shapeForType mapping", () => {
    expect(shapeForType("ip")).toBe("diamond");
    expect(shapeForType("wallet")).toBe("ellipse");
    expect(shapeForType("txid")).toBe("rectangle");
  });
  it("truncateByLimit 2000 no trunc when under", () => {
    const nodes = Array.from({ length: 10 }, (_, i) => ({ id: `n${i}`, type: "wallet" as const }));
    const edges = [{ id: "e1", source: "n0", target: "n1", type: "p2p" as const }];
    const r = truncateByLimit(nodes, edges, 2000);
    expect(r.truncated).toBe(false);
    expect(r.total).toBe(10);
    expect(r.nodes.length).toBe(10);
  });
  it("truncateByLimit truncates and filters edges", () => {
    const nodes = Array.from({ length: 2500 }, (_, i) => ({ id: `n${i}`, type: "wallet" as const }));
    const edges = [
      { id: "e1", source: "n0", target: "n1", type: "p2p" as const },
      { id: "e2", source: "n0", target: "n3000", type: "p2p" as const },
    ];
    const r = truncateByLimit(nodes, edges, 2000);
    expect(r.truncated).toBe(true);
    expect(r.nodes.length).toBe(2000);
    expect(r.total).toBe(2500);
    expect(r.edges.length).toBe(1);
    expect(r.edges[0]!.id).toBe("e1");
  });
});
