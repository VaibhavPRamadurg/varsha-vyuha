import type { DatasetManifest, HistoricalEvidence, MitigationComparison, MitigationIntervention, MitigationScenarios, ReferenceContext, ScenarioResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) throw new Error(`API request failed (${response.status})`);
  return response.json() as Promise<T>;
}

export const api = {
  areas: () => request<Array<{ cell_ids: string[] }>>("/areas"),
  health: () => request<{ model_version: string; provenance: string }>("/health"),
  datasets: () => request<{ datasets: DatasetManifest[]; provenance: string }>("/metadata/datasets"),
  historicalEvidence: () => request<HistoricalEvidence>("/historical/evidence"),
  referenceContext: () => request<ReferenceContext>("/reference-context"),
  mitigationCatchments: () => request<{ label: string; catchments: GeoJSON.FeatureCollection }>("/mitigation/catchments"),
  mitigationScenarios: () => request<MitigationScenarios>("/mitigation/scenarios"),
  mitigationCompare: (input: { rainfall_intensity_mm_per_hour: number; rainfall_duration_hours: number; drain_blockage_percent: number; selected_interventions: MitigationIntervention[] }) => request<MitigationComparison>("/mitigation/compare", {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(input)
  }),
  evaluate: (input: { rainfall_multiplier: number; drainage_blockage_percent: number; selected_cell_ids: string[]; scenario_name?: string }) =>
    request<ScenarioResponse>("/scenario/evaluate", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(input)
    })
};
