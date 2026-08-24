import Graph from "graphology";
import type { CyJson } from "@/types/graph";
import { getNodeSize, getNodeStyle } from "@/cytoscape/styles";

/**
 * Deterministic hash for string -> uint32.
 * Same algorithm as hashPosition but returns numeric hash for coordinate fallback.
 */
export function hash(str: string): number {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (h * 31 + str.charCodeAt(i)) >>> 0;
  }
  return h;
}

export function cyJsonToGraphology(cyJson: CyJson): {
  graph: Graph;
  nodeCount: number;
  edgeCount: number;
} {
  const graph = new Graph({ multi: false, allowSelfLoops: true, type: "mixed" });

  for (const n of cyJson.nodes) {
    const h = hash(n.id);
    // Use doubled id string for y fallback to decorrelate x/y (spec: hash(n.id*2)%600 ; we emulate via hash(n.id + n.id))
    const hy = hash(n.id + n.id);
    const x = n.x ?? h % 1000;
    const y = n.y ?? hy % 600;
    const size = getNodeSize(n.degree ?? 1, n.p ?? 0.5);
    const color = getNodeStyle(n.type).bg;
    // graphology node attributes
    graph.addNode(n.id, {
      label: n.label ?? n.id.slice(0, 8),
      x,
      y,
      size,
      color,
      type: n.type,
    });
  }

  let edgeCount = 0;
  for (const e of cyJson.edges) {
    if (!graph.hasNode(e.source) || !graph.hasNode(e.target)) continue;
    const attrs = {
      label: e.type,
      color: "#94a3b8",
      size: 1,
      type: e.type,
    };
    try {
      if (e.id) {
        // Use addEdgeWithKey when id provided to preserve edge key and avoid duplicate key errors
        if (!(graph as unknown as { hasEdge: (k: string) => boolean }).hasEdge(e.id)) {
          graph.addEdgeWithKey(e.id, e.source, e.target, attrs);
        } else {
          // duplicate id — fallback to auto key
          graph.addEdge(e.source, e.target, attrs);
        }
      } else {
        graph.addEdge(e.source, e.target, attrs);
      }
      edgeCount++;
    } catch {
      // duplicate edge (same source/target without multi) — skip or use merge
      // For multi:false, duplicate source/target pair throws; we try to add with unique key if possible
      // As fallback, skip duplicate
    }
  }

  return { graph, nodeCount: graph.order, edgeCount: graph.size };
}

export default cyJsonToGraphology;
