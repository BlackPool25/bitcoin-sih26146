import { useEffect, useRef } from "react";
import L from "leaflet";
import type { GeoPoint } from "@/types/geo";
import { createTileLayer } from "@/leaflet/tileLayer";
import { createMarkersForPoints } from "@/leaflet/markers";
import { ensureCanvasFallback } from "@/leaflet/fallback";

export type GeoMapProps = {
  points?: GeoPoint[] | null;
  center?: [number, number];
  zoom?: number;
  height?: number;
};

export default function GeoMap({ points, center = [20.5, 79], zoom = 4, height = 400 }: GeoMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersGroupRef = useRef<L.LayerGroup | null>(null);

  // Mount map once
  useEffect(() => {
    if (!containerRef.current) return;
    if (mapRef.current) return;

    const map = L.map(containerRef.current, {
      center,
      zoom,
      preferCanvas: true,
      zoomSnap: 0.25,
    });

    mapRef.current = map;

    // Add tile layer via createTileLayer (offline chain: IndexedDB -> OSM -> Fallback -> canvas)
    try {
      createTileLayer(map);
    } catch {
      // fallback: ensure OSM layer still present even if offline helper fails
      try {
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          attribution: "© OpenStreetMap contributors",
          crossOrigin: true,
          errorTileUrl: "/fallback-tile.png",
        }).addTo(map);
      } catch {
        // ignore in headless
      }
    }

    // ensure canvas fallback
    try {
      ensureCanvasFallback(map);
    } catch {
      // ignore
    }

    // init markers group
    try {
      const group = L.layerGroup().addTo(map);
      markersGroupRef.current = group;
      // initial points (including 0 rows / null / empty — still show map, no crash)
      // Handle geo_cache 0 rows case: points derived from TransactionRecord geo_country/geo_asn via fixtures still renders centroids
      if (points && points.length > 0) {
        const layers = createMarkersForPoints(points);
        for (const layer of layers) group.addLayer(layer);
      }
    } catch {
      // ignore headless failures
    }

    // ensure leaflet container has correct size
    setTimeout(() => {
      try {
        map.invalidateSize();
      } catch {
        // ignore
      }
    }, 0);

    return () => {
      try {
        map.remove();
      } catch {
        // ignore
      }
      mapRef.current = null;
      markersGroupRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update when points change: clear old markers LayerGroup, add new
  useEffect(() => {
    const map = mapRef.current;
    const group = markersGroupRef.current;
    if (!map || !group) return;

    try {
      group.clearLayers();
    } catch {
      // ignore
    }

    // Handle points null/empty: still show map with OSM tile, no markers, no crash
    if (!points || points.length === 0) return;

    try {
      // Never filter on radius — radius is display hint only
      const layers = createMarkersForPoints(points);
      for (const layer of layers) group.addLayer(layer);
    } catch {
      // ignore
    }
  }, [points]);

  // Update view if center/zoom props change
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    try {
      map.setView(center, zoom);
    } catch {
      // ignore
    }
  }, [center, zoom]);

  return (
    <div
      data-testid="geo-map"
      ref={containerRef}
      style={{
        height,
        width: "100%",
        border: "1px solid #e2e8f0",
        borderRadius: 8,
        overflow: "hidden",
      }}
    />
  );
}
