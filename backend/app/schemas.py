from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rainfall_multiplier: float = Field(ge=0, le=3, description="0–3× baseline rainfall severity")
    drainage_blockage_percent: float = Field(ge=0, le=100, description="0–100% synthetic drainage blockage")
    selected_cell_ids: list[str] = Field(min_length=1, max_length=120)
    scenario_name: str | None = Field(default=None, max_length=80)


class LayerSummary(BaseModel):
    id: str
    name: str
    format: Literal["GeoJSON"]
    feature_count: int
    provenance: Literal["synthetic", "observed", "derived"]
    source_type: Literal["observed", "official_forecast", "derived", "synthetic"]
    visual_treatment: str


class AreaSummary(BaseModel):
    id: str
    name: str
    city: str
    state: str
    grid_cell_count: int
    cell_ids: list[str]
    provenance: Literal["synthetic"]


class MitigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rainfall_intensity_mm_per_hour: float = Field(ge=0, le=300)
    rainfall_duration_hours: float = Field(gt=0, le=24)
    drain_blockage_percent: float = Field(ge=0, le=100)
    selected_interventions: list[Literal["clean_drains", "deploy_pumps", "upgrade_drainage"]] = Field(default_factory=list, max_length=3)
