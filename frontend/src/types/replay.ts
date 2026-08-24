import { z } from "zod";
import type { CyJson, GraphEdge, GraphNode } from "./graph";

export const TransactionRecordSchema = z.object({
  timestamp: z.string().refine((v) => !Number.isNaN(Date.parse(v)), { message: "Invalid timestamp ISO" }),
  src_ip: z.string(),
  dst_ip: z.string(),
  src_port: z.number().int().min(0).max(65535),
  dst_port: z.number().int().min(0).max(65535),
  txid: z.string().regex(/^[a-f0-9]{64}$/),
  input_addresses: z.array(z.string()),
  output_addresses: z.array(z.string()),
  input_amounts: z.array(z.number()),
  output_amounts: z.array(z.number()),
  fee: z.number().refine((v) => typeof v === "number" && !Number.isNaN(v) && typeof v === "number", { message: "fee must be number" }),
  script_type: z.enum(["P2PKH", "P2SH", "P2WPKH", "P2WSH", "unknown"]),
  geo_country: z.string(),
  geo_asn: z.number().int(),
});
export type TransactionRecord = z.infer<typeof TransactionRecordSchema>;

export const ReplayResponseSchema = z.object({
  rows: z.array(TransactionRecordSchema),
  count: z.number().int(),
  at: z.string(),
});
export type ReplayResponse = z.infer<typeof ReplayResponseSchema>;

// helper for 422 shape
export type Replay422 = { detail: string };

export function parseISOWithTZ(s: string): Date {
  // Handles Z -> +00:00 and +05:30 via Date
  // Normalize Z to +00:00 is not needed for Date, but ensure both valid
  let norm = s.trim();
  if (norm.endsWith("Z")) {
    norm = norm.slice(0, -1) + "+00:00";
  }
  const d = new Date(norm);
  if (Number.isNaN(d.getTime())) {
    // fallback try original
    const d2 = new Date(s);
    if (!Number.isNaN(d2.getTime())) return d2;
    throw new Error(`Invalid ISO date: ${s}`);
  }
  return d;
}

export function validateReplayAt(at: string | null | undefined): { ok: true; date: Date } | { ok: false; error: Replay422 } {
  if (at == null || at === "") {
    return { ok: false, error: { detail: "Missing at" } };
  }
  try {
    const d = parseISOWithTZ(at);
    if (Number.isNaN(d.getTime())) return { ok: false, error: { detail: "Missing at" } };
    return { ok: true, date: d };
  } catch {
    return { ok: false, error: { detail: "Missing at" } };
  }
}

// deterministic hash
function hashStr(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) >>> 0;
  }
  return h;
}

export function toCyJsonFromRows(rows: TransactionRecord[]): CyJson {
  const nodesMap = new Map<string, GraphNode>();
  const edges: GraphEdge[] = [];
  const positions: Record<string, { x: number; y: number }> = {};

  function ensureNode(id: string, type: "ip" | "wallet" | "txid", extra: Partial<GraphNode> = {}) {
    if (!nodesMap.has(id)) {
      const node: GraphNode = { id, type, ...extra };
      nodesMap.set(id, node);
      const h = hashStr(id);
      const x = h % 1000;
      const y = (h * 2) % 600;
      positions[id] = { x, y };
      node.x = x;
      node.y = y;
    }
  }

  for (const r of rows) {
    // ip nodes
    ensureNode(r.src_ip, "ip", { country: r.geo_country, asn: r.geo_asn });
    ensureNode(r.dst_ip, "ip", { country: r.geo_country, asn: r.geo_asn });
    // txid node
    ensureNode(r.txid, "txid", { label: r.txid.slice(0, 8) });
    // wallet nodes
    for (const addr of r.input_addresses) ensureNode(addr, "wallet");
    for (const addr of r.output_addresses) ensureNode(addr, "wallet");

    // p2p edge src_ip -> dst_ip
    edges.push({ id: `p2p-${r.txid}-${r.src_ip}-${r.dst_ip}`, source: r.src_ip, target: r.dst_ip, type: "p2p", ts: r.timestamp });
    // utxo edges: wallet -> txid (inputs)
    for (let i = 0; i < r.input_addresses.length; i++) {
      const addr = r.input_addresses[i]!;
      const amt = r.input_amounts[i] ?? 0;
      edges.push({ id: `utxo-in-${r.txid}-${addr}`, source: addr, target: r.txid, type: "utxo", amount: amt });
    }
    // txid -> wallet (outputs)
    for (let i = 0; i < r.output_addresses.length; i++) {
      const addr = r.output_addresses[i]!;
      const amt = r.output_amounts[i] ?? 0;
      edges.push({ id: `utxo-out-${r.txid}-${addr}`, source: r.txid, target: addr, type: "utxo", amount: amt });
    }
  }

  return { nodes: Array.from(nodesMap.values()), edges, positions };
}
