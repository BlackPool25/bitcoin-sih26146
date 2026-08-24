import L from "leaflet";

export const OFFLINE_PLACEHOLDER = "/tiles/offline-placeholder.png";
export const TRANSPARENT_DATA_URL =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=";
export const FALLBACK_TILE_URL = "/fallback-tile.png";

/**
 * Ensures canvas fallback for tiles when offline chain fails.
 * Creates canvas tile placeholder if tiles fail, sets errorTileUrl to dataURL or offline placeholder.
 */
export function ensureCanvasFallback(map: L.Map): void {
  // Attach tileerror handler at map level to cover any tile layers (including those added later)
  // If a tile fails, its src will be swapped to canvas fallback via errorTileUrl logic.
  // This handler complements tileLayer's own tileerror handler and ensures canvas terminus.
  try {
    map.on("tileerror", (e: L.TileErrorEvent) => {
      const tile = e.tile as HTMLImageElement | undefined;
      if (!tile) return;
      // If tile src already is a fallback, don't loop
      if (tile.src === TRANSPARENT_DATA_URL || tile.src === OFFLINE_PLACEHOLDER || tile.src === FALLBACK_TILE_URL) {
        return;
      }
      // Final fallback is transparent canvas data URL — works without network
      // Alternatively offline placeholder image if available
      // Use data URL as guaranteed canvas fallback
      try {
        // Create a 1x1 transparent canvas as fallback (Leaflet.TileLayer.Fallback upscaled equivalent)
        const canvas = document.createElement("canvas");
        canvas.width = 256;
        canvas.height = 256;
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.fillStyle = "#e2e8f0";
          ctx.fillRect(0, 0, 256, 256);
          ctx.fillStyle = "#94a3b8";
          ctx.font = "12px sans-serif";
          ctx.fillText("offline", 100, 128);
          const dataUrl = canvas.toDataURL();
          tile.src = dataUrl;
          return;
        }
      } catch {
        // ignore canvas failure
      }
      tile.src = TRANSPARENT_DATA_URL;
    });
  } catch {
    // map may not support events in headless test env
  }

  // Also attempt to set errorTileUrl on existing TileLayers if not already set
  try {
    map.eachLayer((layer: L.Layer) => {
      const tl = layer as L.TileLayer & { options: L.TileLayerOptions & { errorTileUrl?: string } };
      if (tl && tl.options && "errorTileUrl" in tl.options) {
        if (!tl.options.errorTileUrl) {
          tl.options.errorTileUrl = TRANSPARENT_DATA_URL;
        }
      }
    });
  } catch {
    // ignore
  }
}

export function isOffline(): boolean {
  if (typeof navigator !== "undefined" && typeof navigator.onLine === "boolean") {
    return !navigator.onLine;
  }
  return false;
}

export default ensureCanvasFallback;
