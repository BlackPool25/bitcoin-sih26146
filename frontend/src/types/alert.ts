import { z } from "zod";

// 20 countries enum per synthetic generator
export const COUNTRIES = [
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
export type Country = (typeof COUNTRIES)[number];

// 38 SHAP feature names: 15 network + 15 chain + 8 temporal (PROTOTYPE_DECISIONS_FINAL §2 Part5)
export const FEATS = [
  // Network 40% (15)
  "unique_peers",
  "asn_entropy",
  "port_entropy",
  "geo_distance_variance_km",
  "inv_jitter_std",
  "peer_degree",
  "asn_hopping_rate",
  "port_anomaly_score",
  "country_diversity",
  "p2p_burst_count",
  "rtt_proxy_ms",
  "uptime_hours",
  "tor_flag",
  "accuracy_radius_mean",
  "ws_reconnects",
  // Chain 40% (15)
  "fan_in",
  "fan_out",
  "output_amount_variance",
  "fee_sat_per_vb",
  "script_type_hist_P2WPKH_ratio",
  "input_count",
  "output_dispersion_gini",
  "utxo_age_blocks",
  "peel_depth",
  "mixer_score",
  "coinjoin_prob",
  "change_addr_likelihood",
  "dust_outputs",
  "op_return_flag",
  "value_median",
  // Temporal 20% (8)
  "burst_5m_count",
  "burst_1h_count",
  "inter_tx_interval_std",
  "modularity_delta",
  "hour_entropy",
  "day_of_week_entropy",
  "community_size",
  "betweenness_z",
] as const;
export type FeatName = (typeof FEATS)[number];

// Tier: API uses lower-case, UI maps to Critical/High/Medium/Low
export const TierSchema = z.enum(["critical", "high", "medium", "low"]);
export type Tier = z.infer<typeof TierSchema>;

export const AlertSchema = z.object({
  alert_id: z.string().regex(/^[a-f0-9]{64}$/),
  rank: z.number().int().min(1).max(50),
  wallet: z.string(),
  txid: z.string().regex(/^[a-f0-9]{64}$/),
  p: z.number().min(0).max(1),
  tier: TierSchema,
  why: z.string(),
  geo_country: z.string(),
  geo_asn: z.number().int().min(0),
  timestamp: z.string().refine((v) => !Number.isNaN(Date.parse(v)), { message: "Invalid ISO8601" }),
});
export type Alert = z.infer<typeof AlertSchema> & {
  // extra optional fields mirrored from synthetic injection for debugging (not in openapi required)
  injection_label?: string;
  risk_tier?: string;
};

export const GeoTimelineEntrySchema = z.object({
  country: z.string(),
  ts: z.string().refine((v) => !Number.isNaN(Date.parse(v))),
  asn: z.number().int().optional(),
  lat: z.number().optional(),
  lng: z.number().optional(),
  radius: z.number().optional(),
});
export type GeoTimelineEntry = z.infer<typeof GeoTimelineEntrySchema>;

export const AmountFlowPointSchema = z.object({
  ts: z.string().refine((v) => !Number.isNaN(Date.parse(v))),
  amount: z.number(),
});
export type AmountFlowPoint = z.infer<typeof AmountFlowPointSchema>;

export const TemporalBurstBucketSchema = z.object({
  bucket: z.string(),
  count: z.number().int().min(0),
});
export type TemporalBurstBucket = z.infer<typeof TemporalBurstBucketSchema>;

export const AccuracyHintSchema = z.object({
  radius_km: z.number().int().min(0),
  is_hint: z.boolean(),
});
export type AccuracyHint = z.infer<typeof AccuracyHintSchema>;

export const ShapMapSchema = z.record(z.string(), z.number());
export type ShapMap = Record<string, number>;

export const EvidenceSchema = z.object({
  alert_id: z.string().regex(/^[a-f0-9]{64}$/),
  p: z.number().min(0).max(1).optional(),
  tier: TierSchema.optional(),
  shap: ShapMapSchema,
  top_shap: z.array(z.string()).optional(),
  nl: z.string(),
  geo_timeline: z.array(GeoTimelineEntrySchema).optional(),
  amount_flow: z.array(AmountFlowPointSchema).optional(),
  temporal_burst: z.array(TemporalBurstBucketSchema).optional(),
  accuracy_hint: AccuracyHintSchema.optional(),
  geo_inconsistent: z.boolean().optional(),
});
export type Evidence = z.infer<typeof EvidenceSchema>;

export function tierFromP(p: number): Tier {
  if (p > 0.9) return "critical";
  if (p >= 0.75) return "high";
  if (p >= 0.5) return "medium";
  return "low";
}

export function tierLabel(t: Tier): string {
  switch (t) {
    case "critical":
      return "Critical";
    case "high":
      return "High";
    case "medium":
      return "Medium";
    case "low":
      return "Low";
  }
}
