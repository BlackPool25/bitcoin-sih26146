import { z } from "zod";

export const GeoPointSchema = z.object({
  ip: z.string(),
  country: z.string(),
  city: z.string().optional(),
  asn: z.number().nullable().optional(),
  lat: z.number(),
  lng: z.number(),
  radius: z.number().nullable().optional(),
  tier: z.string().optional(),
  accuracy_radius: z.number().optional(),
});
export type GeoPoint = z.infer<typeof GeoPointSchema>;

export const GeoRecordSchema = GeoPointSchema.extend({
  fetched_at: z.string().optional(),
});
export type GeoRecord = z.infer<typeof GeoRecordSchema>;

// Tier derived from geo_country/geo_asn or p value
// hint only, never WHERE filter — radius is display opacity hint per schema.sql

export type Tier = "tier1" | "tier2" | "tier3";

export function tierFromP(p: number): Tier {
  if (p >= 0.8) return "tier1";
  if (p >= 0.5) return "tier2";
  return "tier3";
}

export function tierFromCountryAsn(country: string, asn?: number | null): Tier {
  // deterministic stub: hash country+asn to tier
  const s = `${country}-${asn ?? 0}`;
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  const m = h % 3;
  if (m === 0) return "tier1";
  if (m === 1) return "tier2";
  return "tier3";
}

export function tierColor(tier: string): string {
  switch (tier) {
    case "tier1":
      return "#ef4444";
    case "tier2":
      return "#f97316";
    case "tier3":
      return "#22c55e";
    default:
      return "#22c55e";
  }
}

// NOTE: radius / accuracy_radius is hint only, never WHERE filter per schema.sql
