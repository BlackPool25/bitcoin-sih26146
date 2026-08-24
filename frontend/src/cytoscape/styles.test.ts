import { describe, it, expect } from "vitest";
import { getNodeStyle, getNodeSize, getEdgeStyle, stylesheet, CANVAS_RENDERER, PIXEL_RATIO } from "./styles";

describe("getNodeStyle", () => {
  it("maps ip -> diamond #ef4444", () => {
    const s = getNodeStyle("ip");
    expect(s.shape).toBe("diamond");
    expect(s.bg).toBe("#ef4444");
  });
  it("maps wallet -> ellipse #22c55e", () => {
    const s = getNodeStyle("wallet");
    expect(s.shape).toBe("ellipse");
    expect(s.bg).toBe("#22c55e");
  });
  it("maps txid -> rectangle #a855f7", () => {
    const s = getNodeStyle("txid");
    expect(s.shape).toBe("rectangle");
    expect(s.bg).toBe("#a855f7");
  });
});

describe("getNodeSize", () => {
  it("base 24 scaled by log1p and p, clamped 16-64", () => {
    // degree 0, p 0 => 24
    expect(getNodeSize(0, 0)).toBe(24);
    // degree 5, p 0.34 => 24 + ln(6)*6 + 6.8 => approx 24+10.75+6.8=41.55
    const s = getNodeSize(5, 0.34);
    expect(s).toBeGreaterThan(24);
    expect(s).toBeLessThan(64);
    // large degree and p should clamp to 64
    expect(getNodeSize(10000, 1)).toBe(64);
    // undefined degree/p handled
    expect(getNodeSize(undefined, undefined)).toBe(24);
  });
  it("clamps lower bound 16", () => {
    // negative not expected but clamp ensures >=16; with our formula min is 24, but test clamp logic
    expect(getNodeSize(0, -1)).toBeGreaterThanOrEqual(16);
  });
  it("uses Math.log1p formula exactly", () => {
    const degree = 10;
    const p = 0.5;
    const expected = Math.min(64, Math.max(16, 24 + Math.log1p(degree) * 6 + p * 20));
    expect(getNodeSize(degree, p)).toBe(expected);
  });
});

describe("getEdgeStyle", () => {
  it("returns haystack when count>500", () => {
    const s = getEdgeStyle(1, 1, 501);
    expect(s.curveStyle).toBe("haystack");
    expect(s.haystackRadius).toBe(0);
    expect(s.width).toBe(1);
    expect(s.opacity).toBe(0.6);
    expect(s.lineColor).toBe("#94a3b8");
  });
  it("returns haystack at 600 edges", () => {
    const s = getEdgeStyle(0.5, 2, 600);
    expect(s.curveStyle).toBe("haystack");
  });
  it("returns bezier when count <=500", () => {
    const s = getEdgeStyle(1, 2, 500);
    expect(s.curveStyle).toBe("bezier");
    expect(s.width).toBeCloseTo(1 + Math.log1p(1) * 1.5 + 2 / 5);
  });
  it("bezier width formula 1+log1p(weight)*1.5+amount/5", () => {
    const s = getEdgeStyle(2, 5, 100);
    const expected = 1 + Math.log1p(2) * 1.5 + 5 / 5;
    expect(s.width).toBeCloseTo(expected);
  });
  it("handles undefined weight/amount", () => {
    const s = getEdgeStyle(undefined, undefined, 100);
    expect(s.curveStyle).toBe("bezier");
    expect(s.width).toBe(1);
  });
});

describe("stylesheet", () => {
  it("contains node selectors for ip/wallet/txid", () => {
    const selectors = (stylesheet as unknown as { selector: string }[]).map((s) => s.selector);
    expect(selectors).toContain("node");
    expect(selectors).toContain('node[type="ip"]');
    expect(selectors).toContain('node[type="wallet"]');
    expect(selectors).toContain('node[type="txid"]');
  });
  it("contains edge and edge.p2p / .utxo / .temporal", () => {
    const selectors = (stylesheet as unknown as { selector: string }[]).map((s) => s.selector);
    expect(selectors).toContain("edge");
    expect(selectors).toContain("edge.p2p");
    expect(selectors).toContain("edge.utxo");
    expect(selectors).toContain("edge.temporal");
  });
  it("node base style has label data(label) and text properties", () => {
    const nodeStyle = (stylesheet as unknown as { selector: string; style: Record<string, unknown> }[]).find((s) => s.selector === "node");
    expect(nodeStyle).toBeDefined();
    expect(nodeStyle!.style["label"]).toBe("data(label)");
    expect(nodeStyle!.style["text-valign"]).toBe("center");
    expect(nodeStyle!.style["color"]).toBe("#fff");
    expect(nodeStyle!.style["text-outline-width"]).toBe(2);
    expect(nodeStyle!.style["text-outline-color"]).toBe("#000");
    expect(nodeStyle!.style["min-zoomed-font-size"]).toBe(8);
  });
  it("edge colors are correct", () => {
    const styles = stylesheet as unknown as { selector: string; style: Record<string, unknown> }[];
    const p2p = styles.find((s) => s.selector === "edge.p2p")!;
    const utxo = styles.find((s) => s.selector === "edge.utxo")!;
    const temporal = styles.find((s) => s.selector === "edge.temporal")!;
    expect(p2p.style["line-color"]).toBe("#ef4444");
    expect(utxo.style["line-color"]).toBe("#22c55e");
    expect(temporal.style["line-color"]).toBe("#a855f7");
  });
  it("ip diamond bg #ef4444, wallet ellipse #22c55e, txid rectangle #a855f7 via stylesheet", () => {
    const styles = stylesheet as unknown as { selector: string; style: Record<string, unknown> }[];
    const ip = styles.find((s) => s.selector === 'node[type="ip"]')!;
    const wallet = styles.find((s) => s.selector === 'node[type="wallet"]')!;
    const txid = styles.find((s) => s.selector === 'node[type="txid"]')!;
    expect(ip.style["shape"]).toBe("diamond");
    expect(ip.style["background-color"]).toBe("#ef4444");
    expect(wallet.style["shape"]).toBe("ellipse");
    expect(wallet.style["background-color"]).toBe("#22c55e");
    expect(txid.style["shape"]).toBe("rectangle");
    expect(txid.style["background-color"]).toBe("#a855f7");
  });
});

describe("constants", () => {
  it("PIXEL_RATIO is 1", () => {
    expect(PIXEL_RATIO).toBe(1);
  });
  it("CANVAS_RENDERER is canvas", () => {
    expect(CANVAS_RENDERER).toBe("canvas");
  });
});
