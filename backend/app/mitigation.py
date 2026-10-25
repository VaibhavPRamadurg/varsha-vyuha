"""Transparent, deterministic demonstration water-balance model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "mitigation_model_v1.yaml"
INTERVENTIONS = {"clean_drains", "deploy_pumps", "upgrade_drainage"}


@dataclass(frozen=True)
class MitigationModel:
    model_version: str
    time_step_hours: float
    interventions: dict[str, dict[str, Any]]
    thresholds: dict[str, float]

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "MitigationModel":
        configuration = yaml.safe_load(path.read_text(encoding="utf-8"))
        if configuration.get("provenance") != "synthetic":
            raise ValueError("Mitigation assumptions must remain explicitly synthetic")
        if set(configuration["interventions"]) != INTERVENTIONS:
            raise ValueError("Mitigation intervention configuration is incomplete")
        return cls(
            model_version=configuration["model_version"],
            time_step_hours=float(configuration["time_step_hours"]),
            interventions=configuration["interventions"],
            thresholds=configuration["severity_thresholds_storage_fraction"],
        )

    def scenario_catalogue(self) -> dict[str, Any]:
        return {
            "model_version": self.model_version,
            "provenance": "synthetic",
            "default_inputs": {"rainfall_intensity_mm_per_hour": 50, "rainfall_duration_hours": 3, "drain_blockage_percent": 0},
            "interventions": [
                {"id": key, **values, "provenance": "synthetic demonstration assumption"}
                for key, values in self.interventions.items()
            ],
            "disclaimer": "All catchments, capacities, and intervention effects are synthetic demonstration assumptions; results are modeled accumulation only, not predictions or official advice.",
        }

    def simulate(self, catchments: list[dict[str, Any]], intensity: float, duration: float, input_blockage_percent: float, selected: set[str]) -> dict[str, Any]:
        if not selected.issubset(INTERVENTIONS):
            raise ValueError("Unknown mitigation intervention")
        per_catchment = [self._simulate_catchment(feature, intensity, duration, input_blockage_percent, selected) for feature in catchments]
        total = round(sum(item["modeled_accumulated_water_m3"] for item in per_catchment), 3)
        affected = sum(item["modeled_accumulated_water_m3"] > 0.001 for item in per_catchment)
        return {
            "model_version": self.model_version,
            "provenance": "synthetic",
            "inputs": {
                "rainfall_intensity_mm_per_hour": intensity,
                "rainfall_duration_hours": duration,
                "drain_blockage_percent": input_blockage_percent,
                "selected_interventions": sorted(selected),
            },
            "intervention_assumptions": [
                {"id": key, **self.interventions[key], "provenance": "synthetic demonstration assumption"}
                for key in sorted(selected)
            ],
            "per_catchment": per_catchment,
            "affected_catchment_count": affected,
            "total_modeled_accumulation_m3": total,
            "disclaimer": "SYNTHETIC DEMO CATCHMENTS and demonstration assumptions. Modeled accumulation and ponding-depth equivalents only; not actual flood depth, a prediction, live drainage conditions, or official advice.",
        }

    def _simulate_catchment(self, feature: dict[str, Any], intensity: float, duration: float, input_blockage_percent: float, selected: set[str]) -> dict[str, Any]:
        props = feature["properties"]
        area = float(props["area_m2"])
        runoff_coefficient = float(props["runoff_coefficient"])
        base_drainage = float(props["base_drainage_capacity_m3_per_hour"])
        storage_capacity = float(props["ponding_storage_capacity_m3"])
        blockage = min(1.0, float(props["assumed_blockage_fraction"]) + input_blockage_percent / 100)
        if "clean_drains" in selected:
            blockage *= 1 - float(self.interventions["clean_drains"]["blockage_reduction_fraction"])
        if "upgrade_drainage" in selected:
            base_drainage *= float(self.interventions["upgrade_drainage"]["base_capacity_multiplier"])
        pump = float(self.interventions["deploy_pumps"]["added_capacity_m3_per_hour"]) if "deploy_pumps" in selected else 0.0
        effective_drainage = base_drainage * (1 - blockage) + pump
        stored = 0.0
        overflow = 0.0
        remaining = duration
        timeline = []
        cumulative_runoff = 0.0
        cumulative_drained = 0.0
        step = 0
        while remaining > 1e-9:
            dt = min(self.time_step_hours, remaining)
            runoff = intensity / 1000 * area * runoff_coefficient * dt
            drained = min(stored + runoff, effective_drainage * dt)
            pre_cap_storage = max(0.0, stored + runoff - drained)
            new_overflow = max(0.0, pre_cap_storage - storage_capacity)
            stored = min(pre_cap_storage, storage_capacity)
            overflow += new_overflow
            cumulative_runoff += runoff
            cumulative_drained += drained
            step += 1
            timeline.append({
                "hour": round(min(duration, step * self.time_step_hours), 3),
                "modeled_accumulated_water_m3": round(stored + overflow, 3),
                "stored_within_assumed_capacity_m3": round(stored, 3),
                "modeled_uncontained_excess_m3": round(overflow, 3),
            })
            remaining -= dt
        accumulated = stored + overflow
        return {
            "catchment_id": props["catchment_id"],
            "name": props["name"],
            "provenance": "synthetic",
            "modeled_accumulated_water_m3": round(accumulated, 3),
            "modeled_ponding_depth_equivalent_mm": round(accumulated / area * 1000, 3),
            "stored_within_assumed_capacity_m3": round(stored, 3),
            "modeled_uncontained_excess_m3": round(overflow, 3),
            "modeled_runoff_volume_m3": round(cumulative_runoff, 3),
            "modeled_drained_volume_m3": round(cumulative_drained, 3),
            "effective_drainage_capacity_m3_per_hour": round(effective_drainage, 3),
            "effective_assumed_blockage_fraction": round(blockage, 4),
            "severity_band": self._severity(accumulated / storage_capacity),
            "time_series": timeline,
        }

    def _severity(self, storage_fraction: float) -> str:
        if storage_fraction <= 0:
            return "none"
        if storage_fraction < self.thresholds["low"]:
            return "low"
        if storage_fraction < self.thresholds["medium"]:
            return "medium"
        if storage_fraction < self.thresholds["high"]:
            return "high"
        return "critical"
