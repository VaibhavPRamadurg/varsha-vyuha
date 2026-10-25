import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, vi } from "vitest";
import { App, RiskDetails } from "./App";
import { LaunchIntro } from "./LaunchIntro";
import { syntheticGrid } from "./grid";
import type { CellResult } from "./types";

vi.mock("./MapLibreMap", () => ({
  mapHasOnlineBuildings: false,
  mapHasSatelliteContext: false,
  MapLibreMap: ({ mode, contextStyle, roads, water, scenarioGrid, observedGrid, onSelect }: { mode: string; contextStyle: string; roads?: { features: unknown[] }; water?: { features: unknown[] }; scenarioGrid?: { features: Array<{ properties: { grid_id: string } }> }; observedGrid?: { features: unknown[] }; onSelect?: (cellId: string) => void }) => <div data-testid="maplibre-map" data-mode={mode} data-context-style={contextStyle}><span data-testid="roads-layer">{roads?.features.length ?? 0} roads</span><span data-testid="water-layer">{water?.features.length ?? 0} water</span>{scenarioGrid && <div data-testid="scenario-grid-overlay">{scenarioGrid.features.slice(0, 1).map((feature) => <button key={feature.properties.grid_id} onClick={() => onSelect?.(feature.properties.grid_id)}>{feature.properties.grid_id}</button>)}</div>}{observedGrid && <div data-testid="observed-grid-overlay">{observedGrid.features.length} observed</div>}</div>
}));

const cellIds = Array.from({ length: 120 }, (_, index) => `MUM-V2-${String(Math.floor(index / 12) + 1).padStart(2, "0")}-${String((index % 12) + 1).padStart(2, "0")}`);
const result: CellResult = { cell_id: "MUM-V2-01-01", risk_score: 42, risk_band: "medium", provenance: "scenario_estimate", model_version: "risk-model-v1.2.0-evidence-backed", weights: { historical_rainfall: 0.4 }, explanation: "Evidence-backed scenario explanation; not a flood forecast.", drivers: { historical_rainfall: { value: 0.5, weight: 0.4, weighted_contribution: 20, provenance: "observed", source: "IMD 2023 observed daily gridded rainfall" }, relative_low_elevation: { value: 0.2, weight: 0.25, weighted_contribution: 5, provenance: "derived", source: "Derived from Copernicus DEM GLO-30 cell statistics" }, water_proximity: { value: 0.3, weight: 0.2, weighted_contribution: 6, provenance: "derived", source: "Derived from local verified OSM waterways and water bodies" }, drainage_blockage: { value: 0.1, weight: 0.15, weighted_contribution: 1.5, provenance: "synthetic", source: "User-selected synthetic scenario input" } } };
const stressedResult: CellResult = { ...result, risk_score: 62, risk_band: "high" };
const historicalEvidence = { mode: "historical_evidence", provenance: "observed", disclaimer: "Observed gridded rainfall; not street-level rainfall or an official flood warning.", rainfall: { provenance: "observed", source_type: "observed", source: "India Meteorological Department", period: "2023-06-01 to 2023-09-30", units: "mm/day", study_area_weighted_total_mm: 3329.434, study_area_weighted_mean_mm_per_day: 27.29, grid: { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: null }] }, limitations: ["Two coarse IMD cells."] }, osm_context: { provenance: "derived", label: "DERIVED FROM OPENSTREETMAP", attribution: "© OpenStreetMap contributors", roads: { type: "FeatureCollection", features: [] }, water: { type: "FeatureCollection", features: [] }, limitations: ["Reference context only."] } } as const;
const referenceContext = { provenance: "derived", label: "DERIVED FROM OPENSTREETMAP", attribution: "© OpenStreetMap contributors", roads: { type: "FeatureCollection", features: [{ type: "Feature", properties: { reference_category: "road" }, geometry: null }] }, water: { type: "FeatureCollection", features: [{ type: "Feature", properties: { reference_category: "waterway" }, geometry: null }] }, limitations: ["Reference context only."] } as const;
const mitigationCatchments = { label: "SYNTHETIC DEMO CATCHMENTS", catchments: { type: "FeatureCollection", features: Array.from({ length: 10 }, (_, index) => ({ type: "Feature", properties: { catchment_id: `SK-DEMO-C${index + 1}` }, geometry: null })) } } as const;
const mitigationScenarios = { model_version: "mitigation-water-balance-v1.0.0", default_inputs: { rainfall_intensity_mm_per_hour: 50, rainfall_duration_hours: 3, drain_blockage_percent: 0 }, interventions: [{ id: "clean_drains", label: "Clean drains", description: "Demo cleaning assumption.", provenance: "synthetic demonstration assumption" }, { id: "deploy_pumps", label: "Deploy pumps", description: "Demo pump assumption.", provenance: "synthetic demonstration assumption" }, { id: "upgrade_drainage", label: "Upgrade drainage", description: "Demo upgrade assumption.", provenance: "synthetic demonstration assumption" }] } as const;
const mitigationComparison = { provenance: "synthetic", model_version: "mitigation-water-balance-v1.0.0", baseline: { total_modeled_accumulation_m3: 1500, affected_catchment_count: 8, per_catchment: [] }, with_interventions: { total_modeled_accumulation_m3: 900, affected_catchment_count: 5, per_catchment: [] }, percentage_modeled_reduction_vs_baseline: 40, disclaimer: "SYNTHETIC DEMO CATCHMENTS and demonstration assumptions." } as const;

function response(data: unknown, ok = true) { return Promise.resolve({ ok, status: ok ? 200 : 500, json: async () => data }); }
function mockApi(failEvaluate = false) {
  const fetchMock = vi.fn((input: RequestInfo | URL, options?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/areas")) return response([{ cell_ids: cellIds }]);
    if (url.endsWith("/metadata/datasets")) return response({ datasets: [{ file_name: "fixture.geojson", provider: "FloodShift AI", source_type: "synthetic", geographic_coverage: "Mumbai", period: "N/A", limitations: ["Synthetic fixture only."] }], provenance: "synthetic" });
    if (url.endsWith("/health")) return response({ model_version: "risk-model-v1.2.0-evidence-backed", provenance: "scenario_estimate" });
    if (url.endsWith("/historical/evidence")) return response(historicalEvidence);
    if (url.endsWith("/reference-context")) return response(referenceContext);
    if (url.endsWith("/mitigation/catchments")) return response(mitigationCatchments);
    if (url.endsWith("/mitigation/scenarios")) return response(mitigationScenarios);
    if (url.endsWith("/mitigation/compare")) return response(mitigationComparison);
    const request = JSON.parse(String(options?.body ?? "{}")) as { rainfall_multiplier?: number; drainage_blockage_percent?: number };
    const stressed = request.rainfall_multiplier !== 1 || request.drainage_blockage_percent !== 0;
    return response(failEvaluate ? {} : { evaluated_cells: [stressed ? stressedResult : result], model_version: result.model_version, weights: result.weights, provenance: "scenario_estimate", scenario_name: null, inputs: { rainfall_multiplier: request.rainfall_multiplier ?? 1, drainage_blockage_percent: request.drainage_blockage_percent ?? 0, selected_cell_ids: cellIds }, disclaimer: "Scenario estimate" }, !failEvaluate);
  });
  vi.stubGlobal("fetch", fetchMock); return fetchMock;
}

beforeEach(() => { window.localStorage.setItem("floodshift-ai-tour-completed-v1", "true"); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); window.localStorage.clear(); });

test("uses the 12-column × 10-row v2 synthetic grid", () => {
  expect(syntheticGrid.features).toHaveLength(120);
  expect(syntheticGrid.features[0].properties.grid_id).toBe("MUM-V2-01-01");
  expect(syntheticGrid.features.at(-1)?.properties.grid_id).toBe("MUM-V2-10-12");
});

test("shows the VarshaVyuha launch intro and allows it to be skipped", () => {
  render(<LaunchIntro />);
  expect(screen.getByText("VarshaVyuha")).toBeInTheDocument();
  expect(screen.getByText("Urban Flood Resilience Lab")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Skip intro" }));
  expect(screen.queryByText("VarshaVyuha")).not.toBeInTheDocument();
});

test("shows disclaimer, scenario-estimate badge, offline style default, and missing-key fallback", async () => {
  mockApi(); render(<App />);
  expect(screen.getByText("Prototype — not an official emergency warning.")).toBeInTheDocument();
  expect(screen.getAllByText(/SCENARIO ESTIMATE/).length).toBeGreaterThan(0);
  expect(screen.getByTestId("maplibre-map")).toHaveAttribute("data-mode", "scenario");
  expect(screen.getByTestId("maplibre-map")).toHaveAttribute("data-context-style", "offline");
  expect(screen.getByText("Offline vector reference context ready")).toBeInTheDocument();
  expect(screen.getByRole("radio", { name: /Offline vector context/ })).toBeChecked();
  expect(screen.getByRole("radio", { name: /Satellite \+ 3D context/ })).toBeDisabled();
  expect(screen.getByText("MapTiler key unavailable")).toBeInTheDocument();
  expect(screen.getByLabelText("Map style and layers")).toHaveTextContent("3D buildings online source unavailable");
  expect(screen.getByText("DERIVED FROM OPENSTREETMAP")).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByText("Calculating scenario estimate…")).not.toBeInTheDocument());
  expect(screen.getByTestId("roads-layer")).toHaveTextContent("1 roads");
  expect(screen.getByTestId("water-layer")).toHaveTextContent("1 water");
  expect(screen.getByLabelText("Scenario risk summary")).toHaveTextContent("120-cell study area");
});

test("shows a loading state then an API error state", async () => {
  mockApi(true); render(<App />);
  expect(screen.getByText("Calculating scenario estimate…")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("API request failed"));
});

test("renders evidence-backed driver provenance and no-selection guidance", () => {
  const { rerender } = render(<RiskDetails result={undefined} />);
  expect(screen.getByText(/Select any scenario grid cell/)).toBeInTheDocument();
  rerender(<RiskDetails result={result} />);
  expect(screen.getByText(/42.00/)).toBeInTheDocument();
  expect(screen.getByText("Historical rainfall baseline")).toBeInTheDocument();
  expect(screen.getByText("Water proximity / context")).toBeInTheDocument();
  expect(screen.getByText("OBSERVED")).toBeInTheDocument();
  expect(screen.getAllByText("DERIVED")).toHaveLength(2);
  expect(screen.getByText("SYNTHETIC INPUT")).toBeInTheDocument();
  expect(screen.getByText(/Evidence-backed scenario explanation/)).toBeInTheDocument();
});

test("shows a scenario change from baseline after a non-baseline scenario run", async () => {
  mockApi(); render(<App />);
  await waitFor(() => expect(screen.queryByText("Calculating scenario estimate…")).not.toBeInTheDocument());
  expect(screen.queryByLabelText("Scenario change from baseline")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Rainfall multiplier"), { target: { value: "2" } });
  fireEvent.click(screen.getByRole("button", { name: "Run scenario" }));
  await waitFor(() => expect(screen.getByLabelText("Scenario change from baseline")).toBeInTheDocument());
  expect(screen.getByText("Counts compare scenario-model runs only; not a forecast.")).toBeInTheDocument();
});

test("submits controls, resets them, and opens details from a MapLibre grid click", async () => {
  const fetchMock = mockApi(); render(<App />);
  await waitFor(() => expect(screen.queryByText("Calculating scenario estimate…")).not.toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: "MUM-V2-01-01" }));
  expect(screen.getByText(/42.00/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Rainfall multiplier"), { target: { value: "2" } });
  fireEvent.change(screen.getByLabelText("Drainage blockage"), { target: { value: "50" } });
  fireEvent.click(screen.getByRole("button", { name: "Run scenario" }));
  await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/scenario/evaluate"))).toBe(true));
  const scenarioCall = fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/scenario/evaluate")).at(-1);
  const request = scenarioCall?.[1] as RequestInit;
  expect(JSON.parse(String(request.body))).toMatchObject({ rainfall_multiplier: 2, drainage_blockage_percent: 50 });
  fireEvent.click(screen.getByRole("button", { name: "Reset" }));
  await waitFor(() => expect(screen.getByLabelText("Rainfall multiplier")).toHaveValue("1"));
});

test("renders local reference context and synthetic grid overlay together", async () => {
  mockApi(); render(<App />);
  await waitFor(() => expect(screen.queryByText("Calculating scenario estimate…")).not.toBeInTheDocument());
  expect(screen.getByTestId("maplibre-map")).toBeInTheDocument();
  expect(screen.getByTestId("scenario-grid-overlay")).toBeInTheDocument();
  expect(screen.getByText("Roads & water context")).toBeInTheDocument();
  expect(screen.getByText("Synthetic risk grid")).toBeInTheDocument();
});

test("separates observed Historical Evidence from the synthetic map mode", async () => {
  const fetchMock = mockApi(); render(<App />);
  await waitFor(() => expect(screen.queryByText("Calculating scenario estimate…")).not.toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: "Historical Evidence" }));
  await waitFor(() => expect(screen.getByText("Observed gridded rainfall; not street-level rainfall or an official flood warning.")).toBeInTheDocument());
  expect(screen.getByTestId("maplibre-map")).toHaveAttribute("data-mode", "historical");
  expect(screen.getByTestId("observed-grid-overlay")).toBeInTheDocument();
  expect(screen.getByText(/OBSERVED DATA/)).toBeInTheDocument();
  expect(screen.queryByText("SCENARIO ESTIMATE")).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/historical/evidence", undefined);
});

test("completes, stores, and replays the first-time tour", async () => {
  window.localStorage.removeItem("floodshift-ai-tour-completed-v1");
  mockApi(); render(<App />);
  await waitFor(() => expect(screen.getByRole("dialog")).toBeInTheDocument());
  expect(screen.getByRole("heading", { name: "Welcome to VarshaVyuha" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(screen.getByRole("heading", { name: "Scenario Lab" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Skip" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(window.localStorage.getItem("floodshift-ai-tour-completed-v1")).toBe("true");
  fireEvent.click(screen.getByRole("button", { name: "How it works" }));
  expect(screen.getByRole("dialog")).toBeInTheDocument();
});

test("shows plain-language help for scenario inputs and provenance terms", async () => {
  mockApi(); render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Help: Rainfall multiplier" }));
  expect(screen.getByRole("tooltip")).toHaveTextContent("Scales the 2023 observed IMD historical baseline.");
  fireEvent.click(screen.getByRole("button", { name: "Help: Drainage blockage" }));
  expect(screen.getAllByRole("tooltip").at(-1)).toHaveTextContent("This is a scenario input, not a live measurement.");
  fireEvent.click(screen.getByRole("button", { name: "Help: Synthetic Scenario" }));
  expect(screen.getByText("A transparent what-if calculation that combines documented evidence drivers with a synthetic drainage input; not an official forecast.")).toBeInTheDocument();
  await waitFor(() => expect(screen.getAllByRole("tooltip").at(-1)?.getAttribute("style")).toContain("left"));
});

test("renders the synthetic mitigation simulator and compares interventions with baseline", async () => {
  mockApi(); render(<App />);
  await waitFor(() => expect(screen.getByRole("heading", { name: "Mitigation Simulator" })).toBeInTheDocument());
  expect(screen.getByText(/SYNTHETIC DEMO CATCHMENTS/)).toBeInTheDocument();
  fireEvent.click(screen.getByLabelText(/Clean drains/));
  fireEvent.click(screen.getByRole("button", { name: "Compare with baseline" }));
  await waitFor(() => expect(screen.getByText("Baseline modeled accumulation")).toBeInTheDocument());
  expect(screen.getByText("40.0%")).toBeInTheDocument();
  expect(screen.getByText(/modeled accumulation and a modeled ponding-depth equivalent only/)).toBeInTheDocument();
});

test("shows a baseline-only mitigation result until an intervention is selected", async () => {
  mockApi(); render(<App />);
  await waitFor(() => expect(screen.getByRole("button", { name: "View baseline" })).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: "View baseline" }));
  await waitFor(() => expect(screen.getByText("Baseline modeled accumulation")).toBeInTheDocument());
  expect(screen.getByText("Select one or more interventions to calculate an after-mitigation result.")).toBeInTheDocument();
  expect(screen.queryByText("After interventions")).not.toBeInTheDocument();
});

test("sends changed mitigation inputs and presents each intervention as a comparison", async () => {
  const fetchMock = mockApi(); render(<App />);
  await waitFor(() => expect(screen.getByRole("button", { name: "View baseline" })).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText("Mitigation rainfall intensity"), { target: { value: "30" } });
  fireEvent.change(screen.getByLabelText("Mitigation rainfall duration"), { target: { value: "4" } });
  fireEvent.change(screen.getByLabelText("Mitigation drain blockage"), { target: { value: "20" } });
  for (const label of ["Clean drains", "Deploy pumps", "Upgrade drainage"]) {
    fireEvent.click(screen.getByLabelText(new RegExp(label)));
    fireEvent.click(screen.getByRole("button", { name: "Compare with baseline" }));
    await waitFor(() => expect(screen.getByText("40.0%")).toBeInTheDocument());
    expect(screen.getByText("Simulation updated for 30 mm/hour · 4 hours · 20% blockage.")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(new RegExp(label)));
  }
  const call = fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/mitigation/compare")).at(-1);
  expect(JSON.parse(String((call?.[1] as RequestInit).body))).toMatchObject({ rainfall_intensity_mm_per_hour: 30, rainfall_duration_hours: 4, drain_blockage_percent: 20 });
});
