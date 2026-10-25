from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "risk_model_v1.yaml"


@dataclass(frozen=True)
class RiskModel:
    model_version: str
    provenance: str
    description: str
    weights: dict[str, float]
    normalization: dict[str, float]
    risk_bands: dict[str, float]

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "RiskModel":
        configuration = yaml.safe_load(path.read_text(encoding="utf-8"))
        weights = configuration["weights"]
        if round(sum(weights.values()), 8) != 1.0:
            raise ValueError("Risk model weights must sum to 1.0")
        if configuration["provenance"] != "scenario_estimate":
            raise ValueError("This model must remain an explicitly labelled scenario estimate")
        return cls(
            model_version=configuration["model_version"],
            provenance=configuration["provenance"],
            description=configuration["description"],
            weights=weights,
            normalization=configuration["normalization"],
            risk_bands=configuration["risk_bands"],
        )

    def evaluate(self, cell: dict[str, Any], rainfall_multiplier: float, blockage_percent: float) -> dict[str, Any]:
        properties = cell["properties"]
        evidence = properties["evidence_drivers"]
        rainfall = min(
            float(evidence["historical_rainfall_relative"]) * rainfall_multiplier / self.normalization["rainfall_multiplier_at_max"],
            1.0,
        )
        blockage = blockage_percent / self.normalization["drainage_blockage_percent_at_max"]
        driver_values = {
            "historical_rainfall": rainfall,
            "relative_low_elevation": float(evidence["relative_low_elevation_susceptibility"]),
            "water_proximity": float(evidence["water_proximity_susceptibility"]),
            "drainage_blockage": blockage,
        }
        drivers = {
            key: {
                "value": round(value, 4),
                "weight": self.weights[key],
                "weighted_contribution": round(value * self.weights[key] * 100, 2),
                "provenance": evidence["driver_provenance"][key],
                "source": evidence["driver_sources"][key],
            }
            for key, value in driver_values.items()
        }
        score = round(sum(item["weighted_contribution"] for item in drivers.values()), 2)
        band = self.risk_band(score)
        dominant = max(drivers, key=lambda key: drivers[key]["weighted_contribution"])
        explanation = self.explanation(properties["grid_id"], band, dominant, rainfall_multiplier, blockage_percent)
        return {
            "cell_id": properties["grid_id"],
            "risk_score": score,
            "risk_band": band,
            "drivers": drivers,
            "explanation": explanation,
            "model_version": self.model_version,
            "weights": self.weights,
            "provenance": "scenario_estimate",
        }

    def risk_band(self, score: float) -> str:
        if score < self.risk_bands["low"]:
            return "low"
        if score < self.risk_bands["medium"]:
            return "medium"
        if score < self.risk_bands["high"]:
            return "high"
        return "critical"

    @staticmethod
    def explanation(cell_id: str, band: str, dominant: str, rainfall_multiplier: float, blockage_percent: float) -> str:
        label = dominant.replace("_", " ")
        return (
            f"{cell_id} is {band} in this scenario-based estimate. Its largest score contribution is {label}; "
            f"the calculation applies {rainfall_multiplier:g}× to observed 2023 IMD baseline rainfall and uses "
            f"{blockage_percent:g}% synthetic drainage blockage. This is not a prediction, flood forecast, or emergency warning."
        )
