import type { GraphNode } from "@/types/graph";

/**
 * hasPositions returns true if every node has defined x and y.
 * Also supports the optional positions record on CyJson (not used here but kept for completeness).
 */
export function hasPositions(nodes: GraphNode[]): boolean {
  if (nodes.length === 0) return false;
  return nodes.every((n) => typeof n.x === "number" && typeof n.y === "number");
}

export type PresetLayoutOptions = {
  name: "preset";
  fit: boolean;
  padding: number;
  animate: boolean;
};

export type FcoseLayoutOptions = {
  name: "fcose";
  quality: "default";
  randomize: boolean;
  animate: boolean;
  fit: boolean;
  padding: number;
  idealEdgeLength: number;
  nodeRepulsion: number;
};

export type LayoutOptions = PresetLayoutOptions | FcoseLayoutOptions;

/**
 * Deterministic layout selection:
 * - preset when nodeCount <= 1000 and hasPositions === true
 *   (leaves nodes at position x,y from data; no Math.random(); fcose seeded via randomize:false)
 * - fcose fallback otherwise
 */
export function getLayoutOptions(nodeCount: number, hasPos: boolean): LayoutOptions {
  const useFcose = nodeCount > 1000 || !hasPos;
  if (useFcose) {
    return {
      name: "fcose",
      quality: "default",
      randomize: false,
      animate: false,
      fit: true,
      padding: 24,
      idealEdgeLength: 100,
      nodeRepulsion: 4500,
    };
  }
  return {
    name: "preset",
    fit: true,
    padding: 24,
    animate: false,
  };
}

export const defaultLayout = { name: "preset" } as const;
export default getLayoutOptions;
