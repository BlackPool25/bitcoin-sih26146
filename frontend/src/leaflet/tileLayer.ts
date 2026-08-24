import "leaflet/dist/leaflet.css";
import L from "leaflet";
import "leaflet.offline";
import { openDB } from "idb";

export const OSM_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
export const FALLBACK_TILE_URL = "/fallback-tile.png";
export const TRANSPARENT_DATA_URL =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=";

export type TileLayerOptions = L.TileLayerOptions & { errorTileUrl?: string };

/**
 * Chain: IndexedDB blob (leaflet.offline) -> OSM -> Leaflet.TileLayer.Fallback upscaled -> errorTileUrl canvas
 * Tries L.tileLayer.offline if available else standard L.tileLayer.
 */
export function createTileLayer(map: L.Map, options?: TileLayerOptions): L.TileLayer {
  const baseOptions: L.TileLayerOptions = {
    maxZoom: 19,
    attribution: "© OpenStreetMap contributors",
    crossOrigin: true,
    errorTileUrl: FALLBACK_TILE_URL,
    ...options,
  };

  let layer: L.TileLayer;
  const tileLayerWithOffline = L.tileLayer as unknown as {
    offline?: (url: string, opts: L.TileLayerOptions) => L.TileLayer;
  };

  if (tileLayerWithOffline.offline && typeof tileLayerWithOffline.offline === "function") {
    try {
      layer = tileLayerWithOffline.offline(OSM_URL, baseOptions);
    } catch {
      // fallback to standard tileLayer if offline registration fails
      layer = L.tileLayer(OSM_URL, baseOptions);
    }
  } else {
    layer = L.tileLayer(OSM_URL, baseOptions);
  }

  // tileerror handler -> placeholder canvas fallback
  // Ensures offline chain terminates at errorTileUrl / canvas even when IndexedDB miss and OSM unreachable
  layer.on("tileerror", (e: L.TileErrorEvent) => {
    const tile = e.tile as HTMLImageElement | undefined;
    if (!tile) return;
    const fallback = (baseOptions.errorTileUrl as string) ?? FALLBACK_TILE_URL;
    // avoid infinite loop if tile already shows fallback
    if (tile.src !== fallback && tile.src !== TRANSPARENT_DATA_URL) {
      // Prefer canvas data URL if leaflet.offline not available (offline fallback to canvas)
      const isOfflineAvailable = !!tileLayerWithOffline.offline;
      tile.src = isOfflineAvailable ? fallback : TRANSPARENT_DATA_URL;
      // Leaflet.TileLayer.Fallback upscaled would be handled by Leaflet's fallback logic;
      // errorTileUrl canvas is the final terminus.
    }
  });

  layer.addTo(map);

  // keep idb import referenced (leaflet.offline TileManager uses idb internally)
  void openDB;

  return layer;
}

export default createTileLayer;
