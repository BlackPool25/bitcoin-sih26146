import { z } from "zod";

export const GraphNodeTypeSchema = z.enum(["ip", "wallet", "txid"]);
export type GraphNodeType = z.infer<typeof GraphNodeTypeSchema>;

export const GraphEdgeTypeSchema = z.enum(["p2p", "utxo", "temporal"]);
export type GraphEdgeType = z.infer<typeof GraphEdgeTypeSchema>;

export const GraphNodeSchema = z.object({
  id: z.string(),
  type: GraphNodeTypeSchema,
  country: z.string().nullable().optional(),
  asn: z.number().nullable().optional(),
  community_id: z.number().nullable().optional(),
  degree: z.number().optional(),
  p: z.number().optional(),
  x: z.number().optional(),
  y: z.number().optional(),
  label: z.string().optional(),
});
export type GraphNode = z.infer<typeof GraphNodeSchema>;

export const GraphEdgeSchema = z.object({
  id: z.string().optional(),
  source: z.string(),
  target: z.string(),
  type: GraphEdgeTypeSchema,
  amount: z.number().optional(),
  ts: z.string().optional(),
  weight: z.number().optional(),
});
export type GraphEdge = z.infer<typeof GraphEdgeSchema>;

export const CyJsonSchema = z.object({
  nodes: z.array(GraphNodeSchema),
  edges: z.array(GraphEdgeSchema),
  positions: z.record(z.object({ x: z.number(), y: z.number() })).optional(),
});
export type CyJson = z.infer<typeof CyJsonSchema>;

export function shapeForType(t: GraphNodeType): "diamond" | "ellipse" | "rectangle" {
  switch (t) {
    case "ip":
      return "diamond";
    case "wallet":
      return "ellipse";
    case "txid":
      return "rectangle";
  }
}

export function truncateByLimit(
  nodes: GraphNode[],
  edges: GraphEdge[],
  limit = 2000,
): { nodes: GraphNode[]; edges: GraphEdge[]; truncated: boolean; total: number } {
  const total = nodes.length;
  if (nodes.length <= limit) {
    return { nodes, edges, truncated: false, total };
  }
  const truncatedNodes = nodes.slice(0, limit);
  const allowedIds = new Set(truncatedNodes.map((n) => n.id));
  const truncatedEdges = edges.filter((e) => allowedIds.has(e.source) && allowedIds.has(e.target));
  return { nodes: truncatedNodes, edges: truncatedEdges, truncated: true, total };
}
