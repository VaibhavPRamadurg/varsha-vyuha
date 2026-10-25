import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import type { GeoJSONSource, Map as MapLibreMapInstance } from "maplibre-gl";
import mapLibreWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import type { FeatureCollection } from "geojson";
import type { RiskBand } from "./types";

export type MapMode = "scenario" | "historical";
export type ContextStyle = "offline" | "satellite";
type MapLayers = { context: boolean; grid: boolean; buildings: boolean };
type Props = {
  mode: MapMode; contextStyle: ContextStyle; roads?: FeatureCollection; water?: FeatureCollection;
  scenarioGrid?: FeatureCollection; observedGrid?: FeatureCollection; riskBands: Record<string, RiskBand>;
  selectedId?: string; layers: MapLayers; onSelect?: (cellId: string) => void; onStyleFallback?: () => void;
};

const MAPTILER_KEY = import.meta.env.VITE_MAPTILER_KEY as string | undefined;
maplibregl.setWorkerUrl(mapLibreWorkerUrl);
const EMPTY_FEATURES: FeatureCollection = { type: "FeatureCollection", features: [] };
const FALLBACK_STYLE: maplibregl.StyleSpecification = { version: 8, name: "FloodShift offline reference context", sources: {}, layers: [{ id: "city-canvas", type: "background", paint: { "background-color": "#081426" } }] };
const RISK_COLOURS: Record<RiskBand, string> = { low: "#36a8e8", medium: "#e8a646", high: "#f06b3a", critical: "#df3f65" };

function setSource(map: MapLibreMapInstance, id: string, data?: FeatureCollection) { const source = map.getSource(id) as GeoJSONSource | undefined; if (source && data) source.setData(data); }
function setVisibility(map: MapLibreMapInstance, layerIds: string[], visible: boolean) { layerIds.forEach((id) => { if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", visible ? "visible" : "none"); }); }
function riskColourExpression(riskBands: Record<string, RiskBand>): maplibregl.ExpressionSpecification | string { const pairs = Object.entries(riskBands).flatMap(([id, band]) => [id, RISK_COLOURS[band]]); return pairs.length ? ["match", ["get", "grid_id"], ...pairs, "#64748b"] as unknown as maplibregl.ExpressionSpecification : "#64748b"; }
function styleFor(contextStyle: ContextStyle) { return contextStyle === "satellite" && MAPTILER_KEY ? `https://api.maptiler.com/maps/hybrid/style.json?key=${encodeURIComponent(MAPTILER_KEY)}` : FALLBACK_STYLE; }

export function MapLibreMap({ mode, contextStyle, roads, water, scenarioGrid, observedGrid, riskBands, selectedId, layers, onSelect, onStyleFallback }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMapInstance | undefined>(undefined);
  const previousSelected = useRef<string | undefined>(undefined);
  const previousHover = useRef<string | undefined>(undefined);
  const fallbackIssued = useRef(false);
  const latest = useRef({ mode, roads, water, scenarioGrid, observedGrid, riskBands, selectedId, layers, onSelect, onStyleFallback });
  latest.current = { mode, roads, water, scenarioGrid, observedGrid, riskBands, selectedId, layers, onSelect, onStyleFallback };

  useEffect(() => {
    if (!container.current || mapRef.current) return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const map = new maplibregl.Map({ container: container.current, style: styleFor(contextStyle), center: [72.89, 19.066], zoom: 14.4, pitch: 45, bearing: -12, minZoom: 11, maxZoom: 18, maxBounds: [[72.84, 19.025], [72.94, 19.105]], attributionControl: false });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: true, visualizePitch: true }), "top-right");
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 110, unit: "metric" }), "bottom-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");

    const addFloodShiftLayers = () => {
      const current = latest.current;
      if (map.getSource("fs-roads")) return;
      map.addSource("fs-roads", { type: "geojson", data: current.roads ?? EMPTY_FEATURES });
      map.addSource("fs-water", { type: "geojson", data: current.water ?? EMPTY_FEATURES });
      map.addSource("fs-scenario-grid", { type: "geojson", data: current.scenarioGrid ?? EMPTY_FEATURES, promoteId: "grid_id" });
      map.addSource("fs-observed-grid", { type: "geojson", data: current.observedGrid ?? EMPTY_FEATURES });
      map.addSource("fs-study-boundary", { type: "geojson", data: { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[[72.865, 19.045], [72.915, 19.045], [72.915, 19.087], [72.865, 19.087], [72.865, 19.045]]] } }] } });
      map.addLayer({ id: "fs-water-fill", type: "fill", source: "fs-water", paint: { "fill-color": "#117fc4", "fill-opacity": 0.52 } });
      map.addLayer({ id: "fs-water-line", type: "line", source: "fs-water", paint: { "line-color": "#55c9f5", "line-width": 2.1, "line-opacity": 0.9 } });
      map.addLayer({ id: "fs-roads-casing", type: "line", source: "fs-roads", paint: { "line-color": "#090f1d", "line-width": ["interpolate", ["linear"], ["zoom"], 11, 0.8, 16, 4.2], "line-opacity": 0.7 } });
      map.addLayer({ id: "fs-roads", type: "line", source: "fs-roads", paint: { "line-color": "#8090a6", "line-width": ["interpolate", ["linear"], ["zoom"], 11, 0.5, 16, 2.4], "line-opacity": 0.72 } });
      map.addLayer({ id: "fs-observed-fill", type: "fill", source: "fs-observed-grid", paint: { "fill-color": "#43d3bf", "fill-opacity": 0.24 } });
      map.addLayer({ id: "fs-observed-line", type: "line", source: "fs-observed-grid", paint: { "line-color": "#76ead5", "line-width": 1.7 } });
      const hatch = new Uint8Array(8 * 8 * 4);
      for (let row = 0; row < 8; row += 1) for (let column = 0; column < 8; column += 1) if ((column - row + 8) % 6 === 0) { const pixel = (row * 8 + column) * 4; hatch[pixel] = 225; hatch[pixel + 1] = 240; hatch[pixel + 2] = 255; hatch[pixel + 3] = 120; }
      map.addImage("fs-synthetic-hatch", { width: 8, height: 8, data: hatch });
      map.addLayer({ id: "fs-grid-fill", type: "fill", source: "fs-scenario-grid", paint: { "fill-color": riskColourExpression(current.riskBands), "fill-opacity": 0.47 } });
      map.addLayer({ id: "fs-grid-hatch", type: "fill", source: "fs-scenario-grid", paint: { "fill-pattern": "fs-synthetic-hatch", "fill-opacity": 0.28 } });
      map.addLayer({ id: "fs-grid-outline", type: "line", source: "fs-scenario-grid", paint: { "line-color": "#eef7ff", "line-width": ["case", ["boolean", ["feature-state", "selected"], false], 2.7, 0.95], "line-opacity": 0.9 } });
      map.addLayer({ id: "fs-study-boundary", type: "line", source: "fs-study-boundary", paint: { "line-color": "#d6e7ff", "line-width": 1.2, "line-dasharray": [3, 2], "line-opacity": 0.7 } });
      if (contextStyle === "satellite") {
        const baseLayer = map.getStyle().layers?.find((layer) => { const candidate = layer as { source?: string; "source-layer"?: string }; return candidate["source-layer"] === "building" && candidate.source; }) as { source?: string; "source-layer"?: string } | undefined;
        if (baseLayer?.source && baseLayer["source-layer"]) { map.addLayer({ id: "fs-3d-buildings", type: "fill-extrusion", source: baseLayer.source, "source-layer": baseLayer["source-layer"], minzoom: 14, paint: { "fill-extrusion-color": "#2e4058", "fill-extrusion-height": ["coalesce", ["get", "render_height"], ["get", "height"], 0], "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], ["get", "min_height"], 0], "fill-extrusion-opacity": 0.62 } }); map.moveLayer("fs-3d-buildings", "fs-grid-fill"); }
      }
      map.on("click", "fs-grid-fill", (event: maplibregl.MapLayerMouseEvent) => { const cellId = event.features?.[0]?.properties?.grid_id; if (cellId) latest.current.onSelect?.(cellId); });
      map.on("mouseenter", "fs-grid-fill", (event: maplibregl.MapLayerMouseEvent) => { map.getCanvas().style.cursor = "pointer"; const id = event.features?.[0]?.id; if (typeof id === "string" || typeof id === "number") { previousHover.current = String(id); map.setFeatureState({ source: "fs-scenario-grid", id }, { hover: true }); } });
      map.on("mouseleave", "fs-grid-fill", () => { map.getCanvas().style.cursor = ""; const hoveredId = previousHover.current; if (hoveredId) map.setFeatureState({ source: "fs-scenario-grid", id: hoveredId }, { hover: false }); previousHover.current = undefined; });
      map.fitBounds([[72.865, 19.045], [72.915, 19.087]], { padding: { top: 108, right: 330, bottom: 120, left: 340 }, maxZoom: 14.5, duration: reducedMotion ? 0 : 1500, essential: !reducedMotion });
      applyLayerVisibility(map, current.mode, current.layers, current.selectedId);
    };
    map.on("load", addFloodShiftLayers);
    if (contextStyle === "satellite") map.on("error", () => { if (!fallbackIssued.current) { fallbackIssued.current = true; latest.current.onStyleFallback?.(); } });
    return () => { map.remove(); mapRef.current = undefined; };
  }, [contextStyle]);

  useEffect(() => { const map = mapRef.current; if (!map || !map.isStyleLoaded()) return; setSource(map, "fs-roads", roads); setSource(map, "fs-water", water); setSource(map, "fs-scenario-grid", scenarioGrid); setSource(map, "fs-observed-grid", observedGrid); }, [roads, water, scenarioGrid, observedGrid]);
  useEffect(() => { const map = mapRef.current; if (!map?.isStyleLoaded() || !map.getLayer("fs-grid-fill")) return; map.setPaintProperty("fs-grid-fill", "fill-color", riskColourExpression(riskBands)); }, [riskBands]);
  useEffect(() => { const map = mapRef.current; if (!map?.isStyleLoaded()) return; applyLayerVisibility(map, mode, layers, selectedId); }, [layers, mode, selectedId]);
  useEffect(() => { const map = mapRef.current; if (!map?.isStyleLoaded() || previousSelected.current === selectedId) return; const priorId = previousSelected.current; if (priorId) map.setFeatureState({ source: "fs-scenario-grid", id: priorId }, { selected: false }); if (selectedId) map.setFeatureState({ source: "fs-scenario-grid", id: selectedId }, { selected: true }); previousSelected.current = selectedId; }, [selectedId]);
  return <div ref={container} className="maplibre-canvas" data-testid="maplibre-map" data-context-style={contextStyle} aria-label="Interactive Mumbai map" />;
}

function applyLayerVisibility(map: MapLibreMapInstance, mode: MapMode, layers: MapLayers, selectedId?: string) {
  setVisibility(map, ["fs-roads", "fs-roads-casing", "fs-water-fill", "fs-water-line", "fs-study-boundary"], layers.context);
  setVisibility(map, ["fs-grid-fill", "fs-grid-hatch", "fs-grid-outline"], layers.grid && mode === "scenario");
  setVisibility(map, ["fs-observed-fill", "fs-observed-line"], mode === "historical");
  setVisibility(map, ["fs-3d-buildings"], Boolean(MAPTILER_KEY && layers.buildings && mode !== "historical"));
  if (selectedId) map.setFeatureState({ source: "fs-scenario-grid", id: selectedId }, { selected: true });
}

export const mapHasOnlineBuildings = Boolean(MAPTILER_KEY);
export const mapHasSatelliteContext = Boolean(MAPTILER_KEY);
