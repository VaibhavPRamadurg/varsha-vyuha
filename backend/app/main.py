from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .data import grid_cells, load_grid, load_historical_evidence, load_mitigation_catchments, load_reference_context, verified_dataset_metadata
from .mitigation import MitigationModel
from .risk import RiskModel
from .schemas import AreaSummary, LayerSummary, MitigationRequest, ScenarioRequest
from .settings import allowed_frontend_origins


app = FastAPI(
    title="FloodShift AI Simulation API",
    version="0.1.0",
    description="Synthetic, deterministic urban flood-resilience demo. Not an official emergency warning.",
)
app.add_middleware(
    CORSMiddleware,
    # Local Vite origins remain available; deployment origins come from the
    # comma-separated ALLOWED_FRONTEND_ORIGINS environment variable.
    allow_origins=allowed_frontend_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
)
MODEL = RiskModel.load()
MITIGATION_MODEL = MitigationModel.load()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "provenance": "scenario_estimate", "model_version": MODEL.model_version}


@app.get("/layers", response_model=list[LayerSummary])
def layers() -> list[LayerSummary]:
    grid = load_grid()
    return [
        LayerSummary(
            id="mumbai-sion-kurla-demo-grid-v2",
            name="Mumbai compact 120-cell demo grid",
            format="GeoJSON",
            feature_count=len(grid["features"]),
            provenance="synthetic",
            source_type="synthetic",
            visual_treatment="synthetic scenario styling required",
        ),
        LayerSummary(
            id="imd-mumbai-sion-kurla-2023-monsoon-observed-summary",
            name="Observed IMD gridded rainfall summary (1 June–30 September 2023)",
            format="GeoJSON",
            feature_count=2,
            provenance="observed",
            source_type="derived",
            visual_treatment="neutral observed-rainfall styling; never risk colours",
        ),
        LayerSummary(
            id="osm-sion-kurla-roads-water-derived-context",
            name="Sion–Kurla roads and water reference context",
            format="GeoJSON",
            feature_count=5766,
            provenance="derived",
            source_type="derived",
            visual_treatment="DERIVED FROM OPENSTREETMAP with visible attribution",
        ),
    ]


@app.get("/areas", response_model=list[AreaSummary])
def areas() -> list[AreaSummary]:
    cells = grid_cells()
    return [
        AreaSummary(
            id="mumbai-sion-kurla-demo-area",
            name="Compact Sion-Kurla visual demo area",
            city="Mumbai",
            state="Maharashtra",
            grid_cell_count=len(cells),
            cell_ids=sorted(cells),
            provenance="synthetic",
        )
    ]


@app.get("/metadata/datasets")
def dataset_metadata() -> dict[str, object]:
    return {"datasets": verified_dataset_metadata(), "provenance": "mixed"}


@app.get("/historical/evidence")
def historical_evidence() -> dict[str, object]:
    return load_historical_evidence()


@app.get("/reference-context")
def reference_context() -> dict[str, object]:
    return load_reference_context()


@app.get("/mitigation/catchments")
def mitigation_catchments() -> dict[str, object]:
    catchments = load_mitigation_catchments()
    return {
        "provenance": "synthetic",
        "label": "SYNTHETIC DEMO CATCHMENTS",
        "catchments": catchments,
        "disclaimer": "Not surveyed drainage boundaries. Assumptions are for demonstration only and do not describe live drainage conditions.",
    }


@app.get("/mitigation/scenarios")
def mitigation_scenarios() -> dict[str, object]:
    return MITIGATION_MODEL.scenario_catalogue()


@app.post("/mitigation/simulate")
def mitigation_simulate(request: MitigationRequest) -> dict[str, object]:
    catchments = load_mitigation_catchments()["features"]
    return MITIGATION_MODEL.simulate(
        catchments,
        request.rainfall_intensity_mm_per_hour,
        request.rainfall_duration_hours,
        request.drain_blockage_percent,
        set(request.selected_interventions),
    )


@app.post("/mitigation/compare")
def mitigation_compare(request: MitigationRequest) -> dict[str, object]:
    catchments = load_mitigation_catchments()["features"]
    baseline = MITIGATION_MODEL.simulate(
        catchments, request.rainfall_intensity_mm_per_hour, request.rainfall_duration_hours,
        request.drain_blockage_percent, set(),
    )
    intervention = MITIGATION_MODEL.simulate(
        catchments, request.rainfall_intensity_mm_per_hour, request.rainfall_duration_hours,
        request.drain_blockage_percent, set(request.selected_interventions),
    )
    baseline_total = baseline["total_modeled_accumulation_m3"]
    reduction = 0.0 if baseline_total == 0 else round((baseline_total - intervention["total_modeled_accumulation_m3"]) / baseline_total * 100, 2)
    return {
        "provenance": "synthetic",
        "model_version": MITIGATION_MODEL.model_version,
        "baseline": baseline,
        "with_interventions": intervention,
        "percentage_modeled_reduction_vs_baseline": reduction,
        "disclaimer": "SYNTHETIC DEMO CATCHMENTS and demonstration assumptions. This comparison reports modeled accumulation only, not actual flood depth, a prediction, or official advice.",
    }


@app.post("/scenario/evaluate")
def evaluate_scenario(request: ScenarioRequest) -> dict[str, object]:
    cells = grid_cells()
    unknown = sorted(set(request.selected_cell_ids) - cells.keys())
    if unknown:
        raise HTTPException(status_code=422, detail={"message": "Unknown synthetic cell IDs", "cell_ids": unknown})
    results = [
        MODEL.evaluate(cells[cell_id], request.rainfall_multiplier, request.drainage_blockage_percent)
        for cell_id in request.selected_cell_ids
    ]
    return {
        "scenario_name": request.scenario_name,
        "inputs": request.model_dump(),
        "model_version": MODEL.model_version,
        "weights": MODEL.weights,
        "provenance": "scenario_estimate",
        "disclaimer": "Scenario-based estimate using documented observed and derived drivers plus a synthetic drainage-blockage input; not a prediction, official flood forecast, emergency warning, or navigation guarantee.",
        "evaluated_cells": results,
    }
