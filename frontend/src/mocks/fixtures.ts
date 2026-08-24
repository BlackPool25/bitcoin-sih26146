import type { CyJson, GeoPoint } from "@/types";

export const mockGraph: CyJson = {
  nodes: [{ data: { id: "n1", label: "node1" } }],
  edges: [{ data: { id: "e1", source: "n1", target: "n1" } }],
};

export const mockGeoPoints: GeoPoint[] = [{ id: "p1", lat: 28.6, lon: 77.2, label: "Delhi" }];

export { mockAlerts, getMockAlerts } from "./alerts.mock";
export { mockEvidence, mockEvidenceMap, getMockEvidence } from "./evidence.mock";
