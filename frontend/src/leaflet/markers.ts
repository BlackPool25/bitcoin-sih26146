import L from "leaflet";
import type { GeoPoint } from "@/types/geo";

export function tierColor(tier: string): string {
  switch (tier) {
    case "tier1":
      return "#ef4444";
    case "tier2":
      return "#f97316";
    case "tier3":
      return "#22c55e";
    default:
      return "#94a3b8";
  }
}

export type LatLng = { lat: number; lng: number };

const CENTROIDS: Record<string, LatLng> = {
  US: { lat: 39.8, lng: -98.5 },
  CN: { lat: 35.8, lng: 104 },
  RU: { lat: 61.5, lng: 105 },
  GB: { lat: 55.3, lng: -3.4 },
  IN: { lat: 20.5, lng: 79 },
  DE: { lat: 51.1657, lng: 10.4515 },
  JP: { lat: 36.2, lng: 138.2 },
  BR: { lat: -14.2, lng: -51.9 },
  FR: { lat: 46.2, lng: 2.2 },
  CA: { lat: 56.1, lng: -106.3 },
  AU: { lat: -25.27, lng: 133.77 },
  KR: { lat: 35.9, lng: 127.76 },
};

export function getCentroidForCountry(country: string): LatLng {
  const key = (country ?? "").toUpperCase().trim();
  return CENTROIDS[key] ?? { lat: 0, lng: 0 };
}

function tierRadius(tier?: string): number {
  if (tier === "tier1") return 10;
  if (tier === "tier2") return 7;
  return 5;
}

/**
 * Never filter on radius — radius is display-only hint for popup / accuracy circle.
 * All points are rendered regardless of radius value.
 */
export function createMarkersForPoints(points: GeoPoint[]): L.Layer[] {
  // Never filter on radius — add comment per spec
  const layers: L.Layer[] = [];
  for (const p of points) {
    // choose centroid lat/lng if missing else point lat/lng
    const hasLatLng =
      typeof p.lat === "number" &&
      typeof p.lng === "number" &&
      Number.isFinite(p.lat) &&
      Number.isFinite(p.lng) &&
      !(p.lat === 0 && p.lng === 0);
    const centroid = getCentroidForCountry(p.country ?? "");
    const lat = hasLatLng ? p.lat : centroid.lat;
    const lng = hasLatLng ? p.lng : centroid.lng;

    const tier = p.tier ?? "tier3";
    const color = tierColor(tier);
    const radius = tierRadius(tier);

    // radius hint: prefer accuracy_radius, fallback to radius
    const accRadius =
      (p as unknown as { accuracy_radius?: number | null }).accuracy_radius ??
      p.radius ??
      null;
    const radiusDisplay =
      accRadius !== null && accRadius !== undefined ? `${accRadius}` : "unknown";

    const marker = L.circleMarker([lat, lng], {
      radius,
      color,
      fillColor: color,
      fillOpacity: 0.85,
      weight: 2,
    });

    const popupHtml = `<b>${p.ip}</b><br/>Tier: ${tier}<br/>Accuracy radius: ${radiusDisplay} m<br/><small>${lat.toFixed(2)}, ${lng.toFixed(2)}</small>`;
    marker.bindPopup(popupHtml);

    layers.push(marker);

    // extra accuracy circle if radius present — display only, never filter
    if (accRadius !== null && accRadius !== undefined && Number.isFinite(accRadius) && accRadius > 0) {
      const accCircle = L.circle([lat, lng], {
        radius: accRadius,
        color,
        fillColor: color,
        fillOpacity: 0.12,
        weight: 1,
      });
      layers.push(accCircle);
    }
  }
  return layers;
}

export default createMarkersForPoints;
