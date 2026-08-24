export type CyJson = {
  nodes: { data: { id: string; label?: string } }[];
  edges: { data: { id: string; source: string; target: string } }[];
};

export type GeoPoint = {
  id: string;
  lat: number;
  lon: number;
  label?: string;
};
