import type { GraphNode, GraphEdge } from "@/types/graph";

export type PaginateResult = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  truncated: boolean;
  total: number;
};

/**
 * paginateGraph slices nodes to limit and filters edges to those whose
 * source and target are in the remaining node set.
 */
export function paginateGraph(
  nodes: GraphNode[],
  edges: GraphEdge[],
  limit = 2000,
): PaginateResult {
  const total = nodes.length;
  if (total <= limit) {
    return { nodes, edges, truncated: false, total };
  }
  const sliced = nodes.slice(0, limit);
  const allowed = new Set(sliced.map((n) => n.id));
  const filtered = edges.filter((e) => allowed.has(e.source) && allowed.has(e.target));
  return { nodes: sliced, edges: filtered, truncated: true, total };
}

/**
 * formatTruncatedBadge returns "showing 2000/273851" style string.
 */
export function formatTruncatedBadge(total: number, shown: number): string {
  return `showing ${shown}/${total}`;
}

// backwards compat — original paginate helper kept
export function paginate<T>(items: T[], page: number, pageSize: number): T[] {
  return items.slice(page * pageSize, (page + 1) * pageSize);
}

export default paginateGraph;
