import type { GraphNodeType } from "@/types/graph";

export const CANVAS_RENDERER = "canvas" as const;
export const PIXEL_RATIO = 1 as const;

// --- getNodeStyle ---
export function getNodeStyle(type: GraphNodeType): { shape: string; bg: string } {
  switch (type) {
    case "ip":
      return { shape: "diamond", bg: "#ef4444" };
    case "wallet":
      return { shape: "ellipse", bg: "#22c55e" };
    case "txid":
      return { shape: "rectangle", bg: "#a855f7" };
  }
}

// --- getNodeSize ---
// base 24 scaled by Math.log1p(degree)*6 + p*20, clamped 16-64
export function getNodeSize(degree: number | undefined, p: number | undefined): number {
  const d = degree ?? 0;
  const prob = p ?? 0;
  const raw = 24 + Math.log1p(d) * 6 + prob * 20;
  return Math.min(64, Math.max(16, raw));
}

// --- getEdgeStyle ---
export type EdgeStyle = {
  curveStyle: "haystack" | "bezier";
  haystackRadius?: number;
  width: number;
  opacity: number;
  lineColor: string;
};

export function getEdgeStyle(
  weight: number | undefined,
  amount: number | undefined,
  count: number,
): EdgeStyle {
  if (count > 500) {
    return {
      curveStyle: "haystack",
      haystackRadius: 0,
      width: 1,
      opacity: 0.6,
      lineColor: "#94a3b8",
    };
  }
  const w = weight ?? 0;
  const a = amount ?? 0;
  const width = 1 + Math.log1p(w) * 1.5 + a / 5;
  return {
    curveStyle: "bezier",
    width,
    opacity: 0.6,
    lineColor: "#94a3b8",
  };
}

// --- stylesheet ---
// selectors: node, node[type="ip"] etc, edge, edge.p2p / .utxo / .temporal
export const stylesheet: unknown[] = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "text-valign": "center",
      "text-halign": "center",
      color: "#fff",
      "text-outline-width": 2,
      "text-outline-color": "#000",
      "min-zoomed-font-size": 8,
      "font-size": 10,
      width: 32,
      height: 32,
      "background-color": "#64748b",
      shape: "ellipse",
      "border-width": 1,
      "border-color": "#334155",
    },
  },
  {
    selector: 'node[type="ip"]',
    style: {
      shape: "diamond",
      "background-color": "#ef4444",
    },
  },
  {
    selector: 'node[type="wallet"]',
    style: {
      shape: "ellipse",
      "background-color": "#22c55e",
    },
  },
  {
    selector: 'node[type="txid"]',
    style: {
      shape: "rectangle",
      "background-color": "#a855f7",
    },
  },
  {
    selector: "edge",
    style: {
      width: 1,
      "line-color": "#94a3b8",
      "curve-style": "bezier",
      opacity: 0.6,
      "target-arrow-shape": "none",
    },
  },
  {
    selector: "edge.p2p",
    style: {
      "line-color": "#ef4444",
    },
  },
  {
    selector: "edge.utxo",
    style: {
      "line-color": "#22c55e",
    },
  },
  {
    selector: "edge.temporal",
    style: {
      "line-color": "#a855f7",
    },
  },
  // haystack performance class for >500 edges — applied dynamically via getEdgeStyle
  {
    selector: "edge.haystack",
    style: {
      "curve-style": "haystack",
      "haystack-radius": 0,
      width: 1,
      opacity: 0.6,
      "line-color": "#94a3b8",
    },
  },
];

export default stylesheet;
