export type RiskBand = "low" | "medium" | "high" | "critical";

export interface Driver {
  value: number;
  weight: number;
  weighted_contribution: number;
  provenance: "observed" | "derived" | "synthetic";
  source: string;
}

export interface CellResult {
  cell_id: string;
  risk_score: number;
  risk_band: RiskBand;
  drivers: Record<string, Driver>;
  explanation: string;
  model_version: string;
  weights: Record<string, number>;
  provenance: "scenario_estimate";
}

export interface ScenarioResponse {
  scenario_name: string | null;
  inputs: {
    rainfall_multiplier: number;
    drainage_blockage_percent: number;
    selected_cell_ids: string[];
    scenario_name?: string | null;
  };
  model_version: string;
  weights: Record<string, number>;
  provenance: "scenario_estimate";
  disclaimer: string;
  evaluated_cells: CellResult[];
}

export interface DatasetManifest {
  file_name: string;
  provider: string;
  source_type: string;
  geographic_coverage: string;
  period: string;
  limitations?: string[];
}

export interface HistoricalEvidence {
  mode: "historical_evidence";
  provenance: "observed";
  disclaimer: string;
  rainfall: {
    provenance: "observed";
    source_type: "observed";
    source: string;
    period: string;
    units: string;
    study_area_weighted_total_mm: number;
    study_area_weighted_mean_mm_per_day: number;
    grid: GeoJSON.FeatureCollection;
    limitations: string[];
  };
  osm_context: {
    provenance: "derived";
    label: "DERIVED FROM OPENSTREETMAP";
    attribution: string;
    roads: GeoJSON.FeatureCollection;
    water: GeoJSON.FeatureCollection;
    limitations: string[];
  };
}

export interface ReferenceContext {
  provenance: "derived";
  label: "DERIVED FROM OPENSTREETMAP";
  attribution: string;
  roads: GeoJSON.FeatureCollection;
  water: GeoJSON.FeatureCollection;
  limitations: string[];
}

export type MitigationIntervention = "clean_drains" | "deploy_pumps" | "upgrade_drainage";

export interface MitigationCatchmentResult {
  catchment_id: string;
  name: string;
  modeled_accumulated_water_m3: number;
  modeled_ponding_depth_equivalent_mm: number;
  severity_band: "none" | "low" | "medium" | "high" | "critical";
  time_series: Array<{ hour: number; modeled_accumulated_water_m3: number }>;
}

export interface MitigationRun {
  total_modeled_accumulation_m3: number;
  affected_catchment_count: number;
  per_catchment: MitigationCatchmentResult[];
}

export interface MitigationComparison {
  provenance: "synthetic";
  model_version: string;
  baseline: MitigationRun;
  with_interventions: MitigationRun;
  percentage_modeled_reduction_vs_baseline: number;
  disclaimer: string;
}

export interface MitigationScenarios {
  model_version: string;
  default_inputs: { rainfall_intensity_mm_per_hour: number; rainfall_duration_hours: number; drain_blockage_percent: number };
  interventions: Array<{ id: MitigationIntervention; label: string; description: string; provenance: string }>;
  disclaimer: string;
}
