import type { Core } from "cytoscape";
import type { CyJson } from "@/types/graph";
import { getLayoutOptions, hasPositions } from "./layout";
import { getNodeSize } from "./styles";
import { paginateGraph } from "./pagination";
import { toCyJsonFromRows } from "@/types/replay";
import type { TransactionRecord } from "@/types/replay";

/**
 * Deterministic hash grid fallback when x/y missing.
 * No Math.random() — purely deterministic based on id hash.
 */
export function hashPosition(id: string): { x: number; y: number } {
  let h = 0;
  for (let i = 0; i < id.length; i++) {
    h = (h * 31 + id.charCodeAt(i)) >>> 0;
  }
  // grid 1000x600 viewport, deterministic placement
  const x = (h % 1000) + (h % 7) * 13;
  const y = ((h >>> 10) % 600) + (h % 11) * 7;
  return { x, y };
}

export function buildElements(
  nodes: CyJson["nodes"],
  edges: CyJson["edges"],
  useHaystack: boolean,
) {
  const nodeEles = nodes.map((n) => {
    const pos = n.x != null && n.y != null ? { x: n.x, y: n.y } : hashPosition(n.id);
    const size = getNodeSize(n.degree, n.p);
    return {
      data: {
        id: n.id,
        type: n.type,
        label: n.label ?? n.id.slice(0, 8),
        degree: n.degree,
      },
      position: pos,
      classes: n.type,
      style: {
        width: size,
        height: size,
      },
    };
  });

  const edgeEles = edges.map((e) => {
    const id = e.id ?? `${e.source}-${e.target}`;
    const classes = [e.type, useHaystack ? "haystack" : ""].filter(Boolean).join(" ");
    return {
      data: {
        id,
        source: e.source,
        target: e.target,
        type: e.type,
        weight: e.weight,
      },
      classes,
    };
  });

  return [...nodeEles, ...edgeEles];
}

/**
 * applyCyJsonUpdate — batch remove+add+layout, diff-friendly if cy populated.
 * Applies pagination internally if nodes exceed 2000.
 */
export function applyCyJsonUpdate(
  cy: Core,
  next: CyJson,
  limit = 2000,
): { truncated: boolean; total: number; shown: number } {
  const paginated = paginateGraph(next.nodes, next.edges, limit);
  const useHaystack = paginated.edges.length > 500;
  const elems = buildElements(paginated.nodes, paginated.edges, useHaystack);

  cy.batch(() => {
    cy.elements().remove();
    cy.add(elems as unknown as Parameters<Core["add"]>[0]);
  });

  const hasPos = hasPositions(paginated.nodes);
  const layoutOpts = getLayoutOptions(cy.nodes().length, hasPos) as unknown as Parameters<Core["layout"]>[0];
  try {
    const layout = cy.layout(layoutOpts);
    layout.run();
  } catch {
    // fcose may not be registered in headless/test — fallback to preset
    const preset = { name: "preset", fit: true, padding: 24, animate: false } as unknown as Parameters<Core["layout"]>[0];
    cy.layout(preset).run();
  }

  try {
    cy.fit(undefined, 24);
  } catch {
    // headless cytoscape may not support fit
  }

  return { truncated: paginated.truncated, total: paginated.total, shown: paginated.nodes.length };
}

export function convertReplayRowsToCyJson(rows: TransactionRecord[]) {
  return toCyJsonFromRows(rows);
}

export default applyCyJsonUpdate;
