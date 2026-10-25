import type { Feature, FeatureCollection, Polygon } from "geojson";

export type GridFeature = Feature<Polygon, { grid_id: string; provenance: "SYNTHETIC_SCENARIO" }>;

// Geometry mirrors the bundled v2 120-cell synthetic fixture. No external basemap or network is needed.
const west = 72.865;
const south = 19.045;
const east = 72.915;
const north = 19.087;
const columns = 12;
const rows = 10;

const features: GridFeature[] = Array.from({ length: rows * columns }, (_, index) => {
  const row = Math.floor(index / columns);
  const column = index % columns;
  const x0 = west + column * ((east - west) / columns);
  const y0 = south + row * ((north - south) / rows);
  const x1 = x0 + ((east - west) / columns);
  const y1 = y0 + ((north - south) / rows);
  return {
    type: "Feature",
    properties: { grid_id: `MUM-V2-${String(row + 1).padStart(2, "0")}-${String(column + 1).padStart(2, "0")}`, provenance: "SYNTHETIC_SCENARIO" },
    geometry: { type: "Polygon", coordinates: [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]] }
  };
});

export const syntheticGrid: FeatureCollection<Polygon, GridFeature["properties"]> = { type: "FeatureCollection", features };
