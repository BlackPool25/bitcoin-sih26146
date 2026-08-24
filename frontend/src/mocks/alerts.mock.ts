import type { Alert, Tier } from "@/types/alert";
import { COUNTRIES, FEATS, tierFromP } from "@/types/alert";

// deterministic RNG seed 42 (mulberry32)
function mulberry32(seed: number): () => number {
  let a = seed | 0;
  return function () {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rng = mulberry32(42);

// helpers
function randomHex64(): string {
  let s = "";
  for (let i = 0; i < 64; i++) {
    s += Math.floor(rng() * 16).toString(16);
  }
  return s;
}

function randomInt(min: number, max: number): number {
  return Math.floor(rng() * (max - min + 1)) + min;
}

const LABELS = ["normal", "peel", "mixer", "coinjoin", "structuring", "ransomware", "bridge", "high_fee", "asn_hop"] as const;

// Cache base time for deterministic offsets but relative to now
const BASE_MS = Date.now();

// Build 50 alerts sorted p desc
function buildMockAlerts(): Alert[] {
  const alerts: Alert[] = [];

  // pre-generate hex ids deterministically
  // we also need shap-derived why but we compute shap here to derive top feat
  for (let i = 0; i < 50; i++) {
    const hex = randomHex64();
    const txid = hex;
    const alert_id = hex;
    // p = 0.95 - i*0.0086 plus small jitter [-0.003,0.003]
    const jitter = (rng() - 0.5) * 0.006;
    let rawP = 0.95 - i * 0.0086 + jitter;
    // clamp to [0.52,0.95] per spec
    if (rawP > 0.95) rawP = 0.95;
    if (rawP < 0.52) rawP = 0.52 + (rng() * 0.01);
    // round to 2 decimals for test S-HAPPY-01
    const p = Math.round(rawP * 100) / 100;
    const tier: Tier = tierFromP(p);
    const wallet = `bc1q${hex.slice(0, 30)}`;
    const geo_country = COUNTRIES[i % COUNTRIES.length] as string;
    // also add some randomization but keep deterministic
    const geoCountryRandom = COUNTRIES[randomInt(0, COUNTRIES.length - 1)] as string;
    const finalCountry = i < 20 ? geo_country : geoCountryRandom;
    const geo_asn = randomInt(1000, 500000);
    const timestamp = new Date(BASE_MS - i * 3600 * 1000).toISOString();
    const injection_label = LABELS[randomInt(0, LABELS.length - 1)] as string;
    const risk_tier = tier;

    // generate shap values for why derivation (same rng state as evidence)
    // we need to generate 38 values to pick top 3
    const shapVals: Array<[string, number]> = [];
    for (const feat of FEATS) {
      const v = rng() * 1 - 0.5; // [-0.5,0.5]
      shapVals.push([feat, Math.round(v * 10000) / 10000]);
    }
    shapVals.sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
    const top_shap = shapVals.slice(0, 3).map(([k]) => k);
    const why = top_shap[0] ?? "anomaly";

    alerts.push({
      alert_id,
      rank: i + 1,
      wallet,
      txid,
      p,
      tier,
      why,
      geo_country: finalCountry,
      geo_asn,
      timestamp,
      injection_label,
      risk_tier,
    } as Alert & { injection_label: string; risk_tier: string });
  }

  // Ensure sorted p desc (already descending, but re-sort to handle jitter)
  alerts.sort((a, b) => b.p - a.p);
  // re-rank after sort
  alerts.forEach((al, idx) => {
    al.rank = idx + 1;
  });

  // Ensure uniqueness of alert_id/txid
  const seen = new Set<string>();
  for (const al of alerts) {
    if (seen.has(al.alert_id)) {
      // regenerate hex for duplicate (unlikely)
      let newHex: string;
      do {
        newHex = randomHex64();
      } while (seen.has(newHex));
      al.alert_id = newHex;
      al.txid = newHex;
      al.wallet = `bc1q${newHex.slice(0, 30)}`;
    }
    seen.add(al.alert_id);
  }

  return alerts;
}

export const mockAlerts: Alert[] = buildMockAlerts();

export function getMockAlerts(params?: {
  tier?: string;
  q?: string;
  sort?: string;
  limit?: number;
  offset?: number;
}): { alerts: Alert[]; count: number } {
  let filtered = [...mockAlerts];

  if (params?.tier) {
    const t = params.tier.toLowerCase();
    filtered = filtered.filter((a) => a.tier === t);
  }

  if (params?.q) {
    const q = params.q.toLowerCase();
    filtered = filtered.filter((a) => {
      const hay = `${a.alert_id} ${a.txid} ${a.wallet} ${a.why} ${a.geo_country} ${a.tier}`.toLowerCase();
      return hay.includes(q);
    });
  }

  if (params?.sort) {
    const s = params.sort;
    if (s === "p") {
      filtered.sort((a, b) => a.p - b.p);
    } else if (s === "-p") {
      filtered.sort((a, b) => b.p - a.p);
    } else if (s === "rank") {
      filtered.sort((a, b) => a.rank - b.rank);
    }
  }

  const count = filtered.length;
  const offset = params?.offset ?? 0;
  const limit = params?.limit ?? 50;
  const paged = filtered.slice(offset, offset + limit);
  return { alerts: paged, count };
}
