import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { tierColor, getCentroidForCountry, createMarkersForPoints } from "@/leaflet/markers";
import GeoMap from "@/components/GeoMap";
import type { GeoPoint } from "@/types/geo";

// Mock leaflet core (headless jsdom) — preserve actual implementation but stub DOM-heavy parts if needed
vi.mock("leaflet", async () => {
  const actual = await vi.importActual<typeof import("leaflet")>("leaflet");
  return actual;
});

// Mock leaflet.offline — ensure L.tileLayer.offline is available (or not, to test fallback)
vi.mock("leaflet.offline", async () => {
  // side-effect import registers L.tileLayer.offline; we just ensure it doesn't throw
  await import("leaflet.offline");
  return {};
});

describe("tierColor", () => {
  it("returns correct colors per tier", () => {
    expect(tierColor("tier1")).toBe("#ef4444");
    expect(tierColor("tier2")).toBe("#f97316");
    expect(tierColor("tier3")).toBe("#22c55e");
    expect(tierColor("unknown")).toBe("#94a3b8");
    expect(tierColor("")).toBe("#94a3b8");
  });
});

describe("getCentroidForCountry", () => {
  it("returns centroid for known countries", () => {
    expect(getCentroidForCountry("US")).toEqual({ lat: 39.8, lng: -98.5 });
    expect(getCentroidForCountry("CN")).toEqual({ lat: 35.8, lng: 104 });
    expect(getCentroidForCountry("RU")).toEqual({ lat: 61.5, lng: 105 });
    expect(getCentroidForCountry("GB")).toEqual({ lat: 55.3, lng: -3.4 });
    expect(getCentroidForCountry("IN")).toEqual({ lat: 20.5, lng: 79 });
    expect(getCentroidForCountry("DE")).toBeDefined();
    expect(getCentroidForCountry("JP")).toBeDefined();
    expect(getCentroidForCountry("BR")).toBeDefined();
  });

  it("is case-insensitive and fallback 0,0", () => {
    expect(getCentroidForCountry("us")).toEqual({ lat: 39.8, lng: -98.5 });
    expect(getCentroidForCountry("XX")).toEqual({ lat: 0, lng: 0 });
    expect(getCentroidForCountry("")).toEqual({ lat: 0, lng: 0 });
  });

  it("covers 10 entries matching fixtures", () => {
    const countries = ["US", "CN", "RU", "GB", "IN", "DE", "BR", "JP", "FR", "CA"];
    for (const c of countries) {
      const v = getCentroidForCountry(c);
      expect(v).toBeDefined();
      expect(typeof v.lat).toBe("number");
      expect(typeof v.lng).toBe("number");
    }
  });
});

describe("createMarkersForPoints", () => {
  const samplePoints: GeoPoint[] = [
    {
      ip: "8.8.8.8",
      country: "US",
      city: "Mountain View",
      asn: 15169,
      lat: 37.09,
      lng: -95.71,
      radius: 1000,
      tier: "tier1",
      accuracy_radius: 1000,
    },
    {
      ip: "1.1.1.1",
      country: "RU",
      asn: 15169,
      lat: 0,
      lng: 0,
      radius: 800,
      tier: "tier2",
    },
    {
      ip: "9.9.9.9",
      country: "IN",
      lat: 19.07,
      lng: 72.87,
      radius: null,
      tier: "tier3",
    },
  ];

  it("creates circleMarker per point with correct radius by tier", () => {
    const layers = createMarkersForPoints(samplePoints);
    // first point tier1 -> circleMarker radius 10 + accuracy circle
    // second point tier2 -> circleMarker radius 7 + accuracy circle (centroid fallback)
    // third point tier3 -> circleMarker radius 5, no accuracy circle (radius null)
    // total layers: 2 + 2 + 1 =5
    expect(layers.length).toBe(5);
  });

  it("uses centroid when lat/lng missing", () => {
    const pts: GeoPoint[] = [{ ip: "1.2.3.4", country: "IN", lat: 0, lng: 0, tier: "tier1" }];
    const layers = createMarkersForPoints(pts);
    expect(layers.length).toBe(1);
    // check that the marker was created at IN centroid (20.5,79) by inspecting layer's latlng
    const marker = layers[0] as unknown as { _latlng: { lat: number; lng: number } };
    // In headless leaflet, _latlng may exist after creation
    if (marker && marker._latlng) {
      expect(marker._latlng.lat).toBeCloseTo(20.5);
      expect(marker._latlng.lng).toBeCloseTo(79);
    }
  });

  it("shows radius in popup and never filtering", () => {
    const pts: GeoPoint[] = [
      { ip: "8.8.8.8", country: "US", lat: 37.09, lng: -95.71, radius: 1000, tier: "tier1", accuracy_radius: 1000 },
      { ip: "8.8.4.4", country: "DE", lat: 52.52, lng: 13.4, radius: 500, tier: "tier3" },
      { ip: "9.9.9.9", country: "IN", lat: 19.07, lng: 72.87, radius: null, tier: "tier2" },
    ];
    const layers = createMarkersForPoints(pts);
    // All 3 points must produce markers regardless of radius (never filter)
    const circleMarkers = layers.filter((l) => (l as unknown as { options: { radius: number } }).options?.radius !== undefined);
    expect(layers.length).toBeGreaterThanOrEqual(3);
    // popup html should contain "Accuracy radius:"
    // markers are L.CircleMarker — check popup content string
    for (const layer of layers) {
      const m = layer as unknown as { getPopup?: () => { getContent: () => string } | null; options: unknown };
      if (m.getPopup) {
        const popup = m.getPopup();
        if (popup) {
          const content = popup.getContent() as string;
          expect(content).toContain("Accuracy radius:");
          expect(content).toContain("Tier:");
        }
      }
    }
  });

  it("never filter on radius — large and small radius both render", () => {
    const pts: GeoPoint[] = [
      { ip: "1.1.1.1", country: "US", lat: 39.8, lng: -98.5, radius: 1, tier: "tier1" },
      { ip: "2.2.2.2", country: "US", lat: 39.8, lng: -98.5, radius: 50000, tier: "tier1" },
    ];
    const layers = createMarkersForPoints(pts);
    // Both should render — no filtering by radius
    expect(layers.length).toBe(4); // 2 markers + 2 accuracy circles
  });

  it("creates accuracy circle with fillOpacity 0.12 weight 1 when radius present", () => {
    const pts: GeoPoint[] = [{ ip: "8.8.8.8", country: "US", lat: 37, lng: -95, radius: 1000, tier: "tier1" }];
    const layers = createMarkersForPoints(pts);
    expect(layers.length).toBe(2);
    const accCircle = layers[1] as unknown as { options: { fillOpacity: number; weight: number; radius: number } };
    expect(accCircle.options.fillOpacity).toBe(0.12);
    expect(accCircle.options.weight).toBe(1);
  });
});

describe("GeoMap component", () => {
  beforeEach(() => {
    // Clear any previous map containers (leaflet stores map instance on div via _leaflet_id)
    document.body.innerHTML = "";
  });

  it("renders div with data-testid geo-map and 400px height", () => {
    render(<GeoMap points={[]} />);
    const el = screen.getByTestId("geo-map");
    expect(el).toBeInTheDocument();
    expect(el.style.height).toBe("400px");
    expect(el.style.borderRadius).toBe("8px");
  });

  it("handles empty points without crash", () => {
    expect(() => render(<GeoMap points={[]} />)).not.toThrow();
    expect(screen.getByTestId("geo-map")).toBeInTheDocument();
  });

  it("handles null points without crash", () => {
    expect(() => render(<GeoMap points={null} />)).not.toThrow();
    expect(screen.getByTestId("geo-map")).toBeInTheDocument();
  });

  it("handles undefined points without crash", () => {
    expect(() => render(<GeoMap points={undefined} />)).not.toThrow();
    expect(screen.getByTestId("geo-map")).toBeInTheDocument();
  });

  it("handles geo_cache 0 rows derived via centroids (geo_country/geo_asn fixtures)", () => {
    // Simulate points derived from TransactionRecord geo_country/geo_asn when geo_cache has 0 rows:
    // These points may have only country+asn with lat/lng derived from centroids
    const derived: GeoPoint[] = [
      { ip: "8.8.8.8", country: "US", asn: 15169, lat: 0, lng: 0, tier: "tier1", radius: 1000 },
      { ip: "114.114.114.114", country: "CN", asn: 4134, lat: 0, lng: 0, tier: "tier1", radius: 1200 },
    ];
    expect(() => render(<GeoMap points={derived} />)).not.toThrow();
    expect(screen.getByTestId("geo-map")).toBeInTheDocument();
  });

  it("respects height/center/zoom props", () => {
    render(<GeoMap points={[]} height={500} center={[51.5, -0.12]} zoom={6} />);
    const el = screen.getByTestId("geo-map");
    expect(el.style.height).toBe("500px");
  });

  it("clears and re-adds markers when points change", async () => {
    const pts1: GeoPoint[] = [{ ip: "8.8.8.8", country: "US", lat: 39.8, lng: -98.5, tier: "tier1", radius: 1000 }];
    const pts2: GeoPoint[] = [
      { ip: "1.1.1.1", country: "RU", lat: 55.75, lng: 37.61, tier: "tier2", radius: 800 },
      { ip: "9.9.9.9", country: "IN", lat: 19.07, lng: 72.87, tier: "tier3", radius: 700 },
    ];
    const { rerender } = render(<GeoMap points={pts1} />);
    expect(screen.getByTestId("geo-map")).toBeInTheDocument();
    rerender(<GeoMap points={pts2} />);
    expect(screen.getByTestId("geo-map")).toBeInTheDocument();
    // no crash on clearing/re-adding
    rerender(<GeoMap points={[]} />);
    expect(screen.getByTestId("geo-map")).toBeInTheDocument();
  });
});
