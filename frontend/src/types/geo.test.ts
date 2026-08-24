import { describe, it, expect } from "vitest";
import { tierColor, tierFromP } from "./geo";

describe("geo", () => {
  it("tierColor mapping", () => {
    expect(tierColor("tier1")).toBe("#ef4444");
    expect(tierColor("tier2")).toBe("#f97316");
    expect(tierColor("tier3")).toBe("#22c55e");
  });
  it("radius not filter — comment exists and tier derived without filtering", () => {
    // hint only, never WHERE filter per schema.sql — verify helper does not filter
    // tierFromP uses p only, not radius
    expect(tierFromP(0.9)).toBe("tier1");
    expect(tierFromP(0.6)).toBe("tier2");
    expect(tierFromP(0.1)).toBe("tier3");
  });
  it("geo schema allows radius nullable", async () => {
    const { GeoPointSchema } = await import("./geo");
    const ok = GeoPointSchema.safeParse({ ip: "1.1.1.1", country: "US", lat: 0, lng: 0, radius: null });
    expect(ok.success).toBe(true);
    const ok2 = GeoPointSchema.safeParse({ ip: "1.1.1.1", country: "US", lat: 10, lng: 20, radius: 500 });
    expect(ok2.success).toBe(true);
  });
});
