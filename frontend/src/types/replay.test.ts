import { describe, it, expect } from "vitest";
import { parseISOWithTZ, validateReplayAt, toCyJsonFromRows, TransactionRecordSchema } from "./replay";

describe("replay", () => {
  it("parseISOWithTZ Z", () => {
    const d = parseISOWithTZ("2024-01-01T00:00:00Z");
    expect(d.toISOString()).toBe("2024-01-01T00:00:00.000Z");
  });
  it("parseISOWithTZ +05:30", () => {
    const d = parseISOWithTZ("2024-01-01T05:30:00+05:30");
    expect(d.toISOString()).toBe("2024-01-01T00:00:00.000Z");
  });
  it("422 missing at", () => {
    const r = validateReplayAt(null);
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error.detail).toBe("Missing at");
    const r2 = validateReplayAt("");
    expect(r2.ok).toBe(false);
  });
  it("toCyJsonFromRows conversion produces nodes/edges", () => {
    const row = {
      timestamp: "2024-01-01T00:00:00Z",
      src_ip: "192.168.1.1",
      dst_ip: "10.0.0.1",
      src_port: 8333,
      dst_port: 8333,
      txid: "a".repeat(64),
      input_addresses: ["wallet_1"],
      output_addresses: ["wallet_2", "wallet_3"],
      input_amounts: [0.5],
      output_amounts: [0.3, 0.19],
      fee: 0.01,
      script_type: "P2PKH" as const,
      geo_country: "US",
      geo_asn: 15169,
    };
    const parsed = TransactionRecordSchema.safeParse(row);
    expect(parsed.success).toBe(true);
    const cy = toCyJsonFromRows([row as any]);
    // nodes: 2 ip +1 txid +3 wallets =6
    expect(cy.nodes.length).toBe(6);
    // edges: 1 p2p +1 input utxo +2 output utxo =4
    expect(cy.edges.length).toBe(4);
    expect(cy.positions).toBeDefined();
    expect(Object.keys(cy.positions!).length).toBe(6);
    // deterministic positions via hash -> grid
    const pos1 = cy.positions!["wallet_1"];
    expect(pos1.x).toBeGreaterThanOrEqual(0);
    expect(pos1.x).toBeLessThan(1000);
    // hash determinism
    const cy2 = toCyJsonFromRows([row as any]);
    expect(cy2.positions!["wallet_1"]).toEqual(pos1);
  });
  it("invalid txid rejected", () => {
    const bad = {
      timestamp: "2024-01-01T00:00:00Z",
      src_ip: "1.1.1.1",
      dst_ip: "2.2.2.2",
      src_port: 0,
      dst_port: 0,
      txid: "nothex",
      input_addresses: [],
      output_addresses: [],
      input_amounts: [],
      output_amounts: [],
      fee: 0.001,
      script_type: "P2PKH" as const,
      geo_country: "US",
      geo_asn: 1,
    };
    expect(TransactionRecordSchema.safeParse(bad).success).toBe(false);
  });
});
