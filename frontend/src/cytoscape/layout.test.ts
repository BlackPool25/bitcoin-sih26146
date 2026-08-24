import { describe, it, expect } from "vitest";
import { getLayoutOptions, hasPositions } from "./layout";
import type { GraphNode } from "@/types/graph";

describe("hasPositions", () => {
  it("returns true when all nodes have x,y", () => {
    const nodes: GraphNode[] = [
      { id: "a", type: "wallet", x: 10, y: 20 },
      { id: "b", type: "ip", x: 30, y: 40 },
    ];
    expect(hasPositions(nodes)).toBe(true);
  });
  it("returns false when any node missing x or y", () => {
    const nodes: GraphNode[] = [
      { id: "a", type: "wallet", x: 10, y: 20 },
      { id: "b", type: "ip" },
    ];
    expect(hasPositions(nodes)).toBe(false);
  });
  it("returns false for empty array", () => {
    expect(hasPositions([])).toBe(false);
  });
});

describe("getLayoutOptions", () => {
  it("returns preset when nodeCount<=1000 and hasPositions true", () => {
    const opts = getLayoutOptions(80, true);
    expect(opts.name).toBe("preset");
    expect(opts).toMatchObject({ fit: true, padding: 24, animate: false });
  });
  it("returns preset for 200 nodes with positions", () => {
    const opts = getLayoutOptions(200, true);
    expect(opts.name).toBe("preset");
  });
  it("returns fcose when nodeCount>1000 even with positions", () => {
    const opts = getLayoutOptions(1500, true);
    expect(opts.name).toBe("fcose");
    if (opts.name === "fcose") {
      expect(opts.randomize).toBe(false);
      expect(opts.animate).toBe(false);
      expect(opts.quality).toBe("default");
      expect(opts.idealEdgeLength).toBe(100);
      expect(opts.nodeRepulsion).toBe(4500);
      expect(opts.fit).toBe(true);
      expect(opts.padding).toBe(24);
    }
  });
  it("returns fcose when !hasPositions", () => {
    const opts = getLayoutOptions(80, false);
    expect(opts.name).toBe("fcose");
    expect((opts as unknown as { randomize: boolean }).randomize).toBe(false);
  });
  it("returns fcose for 1001 nodes without positions", () => {
    const opts = getLayoutOptions(1001, false);
    expect(opts.name).toBe("fcose");
  });
  it("is deterministic: same input same output, no Math.random", () => {
    const a = getLayoutOptions(80, true);
    const b = getLayoutOptions(80, true);
    expect(a).toEqual(b);
    // ensure no randomize true ever for preset path
    expect((a as unknown as { randomize?: boolean }).randomize).not.toBe(true);
  });
  it("fcose has animate false for >1K no animation", () => {
    const opts = getLayoutOptions(2000, false);
    expect(opts.animate).toBe(false);
  });
});
