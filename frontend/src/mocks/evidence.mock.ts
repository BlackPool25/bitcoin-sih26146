import type { Evidence, ShapMap } from "@/types/alert";
import { FEATS } from "@/types/alert";
import { mockAlerts } from "./alerts.mock";

// deterministic per-alert RNG derived from alert_id hash (so evidence is stable regardless of generation order)
function hashStr(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h;
}

function mulberry32(seed: number): () => number {
  let a = seed | 0;
  return function () {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const COUNTRIES = [
  "US",
  "CN",
  "RU",
  "DE",
  "JP",
  "GB",
  "IN",
  "BR",
  "CA",
  "AU",
  "FR",
  "KR",
  "NL",
  "SG",
  "TR",
  "NG",
  "ZA",
  "IR",
  "UA",
  "SE",
] as const;

function buildEvidenceForAlert(alertId: string, wallet: string, p: number, tier: string): Evidence {
  const seed = (hashStr(alertId) ^ 42) >>> 0;
  const rng = mulberry32(seed);

  const shap: ShapMap = {};
  const shapEntries: Array<[string, number]> = [];
  for (const feat of FEATS) {
    const v = rng() * 1 - 0.5;
    const rounded = Math.round(v * 10000) / 10000;
    shap[feat] = rounded;
    shapEntries.push([feat, rounded]);
  }
  shapEntries.sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const top_shap = shapEntries.slice(0, 3).map(([k]) => k);
  const why = top_shap[0] ?? "anomaly";

  // nl Jinja style
  const nl = `Wallet ${wallet.slice(0, 10)} flagged: ${why} \u2014 conf ${p.toFixed(2)} (${top_shap.join("+")})`;

  // geo_timeline 3-5 steps country path
  const steps = Math.floor(rng() * 3) + 3; // 3-5
  const geo_timeline = [];
  const baseMs = Date.now();
  for (let i = 0; i < steps; i++) {
    const country = COUNTRIES[Math.floor(rng() * COUNTRIES.length)] as string;
    const ts = new Date(baseMs - (steps - i) * 3600 * 1000).toISOString();
    const asn = Math.floor(rng() * (500000 - 1000 + 1)) + 1000;
    const lat = Math.round((rng() * 180 - 90) * 100) / 100;
    const lng = Math.round((rng() * 360 - 180) * 100) / 100;
    const radius = Math.floor(rng() * (500 - 10 + 1)) + 10;
    geo_timeline.push({ country, ts, asn, lat, lng, radius });
  }

  // amount_flow 5 points
  const amount_flow = [];
  for (let i = 0; i < 5; i++) {
    const ts = new Date(baseMs - (5 - i) * 3600 * 1000).toISOString();
    const amount = Math.round(rng() * 500000) / 100000; // 0-5
    amount_flow.push({ ts, amount });
  }

  // temporal_burst 5 buckets
  const bucketNames = ["0-5m", "5-10m", "10-30m", "30-60m", "60m+"];
  const temporal_burst = bucketNames.map((bucket) => ({
    bucket,
    count: Math.floor(rng() * 20),
  }));

  const radius_km = Math.floor(rng() * (500 - 10 + 1)) + 10;
  const accuracy_hint = { radius_km, is_hint: radius_km > 100 };
  const geo_inconsistent = rng() > 0.5;

  return {
    alert_id: alertId,
    p,
    tier: tier as Evidence["tier"],
    shap,
    top_shap,
    nl,
    geo_timeline,
    amount_flow,
    temporal_burst,
    accuracy_hint,
    geo_inconsistent,
  };
}

function buildMockEvidence(): Record<string, Evidence> {
  const map: Record<string, Evidence> = {};
  for (const al of mockAlerts) {
    map[al.alert_id] = buildEvidenceForAlert(al.alert_id, al.wallet, al.p, al.tier);
  }
  return map;
}

export const mockEvidenceMap: Record<string, Evidence> = buildMockEvidence();

// also export mockEvidence alias
export const mockEvidence = mockEvidenceMap;

export function getMockEvidence(id: string): Evidence | undefined {
  const found = mockEvidenceMap[id];
  if (found) return found;
  // fallback: generate synthetic evidence for unknown id if it looks like 64hex, else undefined
  if (!/^[a-f0-9]{64}$/.test(id)) return undefined;
  // generate fallback evidence with deterministic hash
  const wallet = `bc1q${id.slice(0, 30)}`;
  // derive p from hash [0.5,0.95]
  const h = hashStr(id);
  const p = Math.round((0.5 + (h % 45) / 100) * 100) / 100; // 0.5-0.95
  const tier = p > 0.9 ? "critical" : p >= 0.75 ? "high" : p >= 0.5 ? "medium" : "low";
  return buildEvidenceForAlert(id, wallet, p, tier as string);
}
