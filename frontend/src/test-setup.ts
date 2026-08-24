import "@testing-library/jest-dom";

// Mock canvas for cytoscape in jsdom — cytoscape renderer requires 2d context for label metrics + drawing
if (typeof HTMLCanvasElement !== "undefined") {
  const noop = () => {};
  const createMockContext = (canvas: HTMLCanvasElement) => {
    const base: Record<string, unknown> = {
      canvas,
      font: "",
      fillStyle: "",
      strokeStyle: "",
      textAlign: "left",
      textBaseline: "alphabetic",
      lineWidth: 1,
      globalAlpha: 1,
      globalCompositeOperation: "source-over",
      shadowBlur: 0,
      shadowColor: "",
      shadowOffsetX: 0,
      shadowOffsetY: 0,
      measureText: () => ({ width: 10, actualBoundingBoxAscent: 0, actualBoundingBoxDescent: 0 }),
      fillText: noop,
      strokeText: noop,
      save: noop,
      restore: noop,
      translate: noop,
      rotate: noop,
      scale: noop,
      clearRect: noop,
      fillRect: noop,
      strokeRect: noop,
      beginPath: noop,
      closePath: noop,
      moveTo: noop,
      lineTo: noop,
      arc: noop,
      ellipse: noop,
      rect: noop,
      quadraticCurveTo: noop,
      bezierCurveTo: noop,
      arcTo: noop,
      stroke: noop,
      fill: noop,
      clip: noop,
      setTransform: noop,
      resetTransform: noop,
      transform: noop,
      setLineDash: noop,
      getLineDash: () => [] as number[],
      createLinearGradient: () => ({ addColorStop: noop }),
      createRadialGradient: () => ({ addColorStop: noop }),
      createPattern: () => null,
      drawImage: noop,
      getImageData: () => ({ data: new Uint8ClampedArray(4) }),
      putImageData: noop,
    };
    return new Proxy(base, {
      get(target, prop) {
        if (prop in target) return target[prop as string];
        return noop;
      },
      set(target, prop, value) {
        target[prop as string] = value;
        return true;
      },
    }) as unknown as CanvasRenderingContext2D;
  };

  HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, type: string) {
    if (type === "2d") return createMockContext(this);
    return null;
  } as unknown as typeof HTMLCanvasElement.prototype.getContext;
}

// Mock ResizeObserver for cytoscape viewport handling in jsdom
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

import "fake-indexeddb/auto";

import("leaflet")
  .then((L) => {
    const canvasProto = (L as unknown as { Canvas: { prototype: Record<string, unknown> } }).Canvas?.prototype;
    if (canvasProto) {
      const origClear = canvasProto._clear as ((...args: unknown[]) => unknown) | undefined;
      if (origClear) {
        canvasProto._clear = function (this: unknown, ...args: unknown[]) {
          const self = this as { _ctx?: unknown };
          if (!self._ctx) return;
          return (origClear as unknown as (this: unknown, ...a: unknown[]) => unknown).apply(this, args);
        };
      }
      const origRedraw = canvasProto._redraw as ((...args: unknown[]) => unknown) | undefined;
      if (origRedraw) {
        canvasProto._redraw = function (this: unknown, ...args: unknown[]) {
          const self = this as { _ctx?: unknown };
          if (!self._ctx) return;
          return (origRedraw as unknown as (this: unknown, ...a: unknown[]) => unknown).apply(this, args);
        };
      }
    }
  })
  .catch(() => {});
