#!/usr/bin/env python3
"""Generate clearly synthetic demonstration catchments for the mitigation simulator."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/synthetic/mumbai_sion_kurla_demo_catchments_v1.geojson"
MANIFEST = ROOT / "data/manifests/mumbai_sion_kurla_demo_catchments_v1.synthetic.manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    west, south, east, north = 72.865, 19.045, 72.915, 19.087
    columns, rows = 5, 2
    width, height = (east - west) / columns, (north - south) / rows
    # Explicitly invented assumptions, varied only to make the demo comparison legible.
    assumptions = [
        (205_000, 0.66, 1_100, 0.24, 8_500), (214_000, 0.70, 1_220, 0.30, 9_100),
        (198_000, 0.62, 1_000, 0.20, 8_100), (220_000, 0.73, 1_260, 0.34, 9_400),
        (208_000, 0.68, 1_160, 0.27, 8_800), (212_000, 0.71, 1_180, 0.31, 9_000),
        (201_000, 0.64, 1_050, 0.22, 8_300), (225_000, 0.75, 1_300, 0.36, 9_700),
        (207_000, 0.67, 1_130, 0.26, 8_700), (218_000, 0.72, 1_240, 0.33, 9_300),
    ]
    features = []
    for index, (area, runoff, drainage, blockage, storage) in enumerate(assumptions):
        row, column = divmod(index, columns)
        x0, y0 = west + column * width, south + row * height
        x1, y1 = x0 + width, y0 + height
        catchment_id = f"SK-DEMO-C{index + 1:02d}"
        features.append({
            "type": "Feature", "id": catchment_id,
            "properties": {
                "catchment_id": catchment_id,
                "name": f"Synthetic demo catchment {index + 1}",
                "provenance": "SYNTHETIC_DEMO_CATCHMENT",
                "area_m2": area,
                "runoff_coefficient": runoff,
                "base_drainage_capacity_m3_per_hour": drainage,
                "assumed_blockage_fraction": blockage,
                "ponding_storage_capacity_m3": storage,
                "optional_pump_capacity_m3_per_hour": 0,
                "disclaimer": "Synthetic demo catchment and demonstration assumptions; not a surveyed drainage boundary or live drainage condition.",
            },
            "geometry": {"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]},
        })
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT, {"type": "FeatureCollection", "name": "Synthetic demo catchments for Sion–Kurla mitigation simulator", "provenance": "SYNTHETIC", "features": features})
    write_json(MANIFEST, {
        "file_name": "data/synthetic/mumbai_sion_kurla_demo_catchments_v1.geojson",
        "url": "synthetic://floodshift-ai/mumbai/sion-kurla-demo-catchments/v1",
        "provider": "FloodShift AI demonstration-model generator",
        "access_date": datetime.now(UTC).date().isoformat(),
        "geographic_coverage": "Ten synthetic rectangles across the compact Sion–Kurla study extent, Mumbai, Maharashtra, India",
        "period": "Not applicable; deterministic demonstration artifact",
        "licence_terms_link": "https://creativecommons.org/licenses/by/4.0/",
        "sha256": sha256(OUTPUT),
        "source_type": "synthetic",
        "processing_steps": [
            "Generated deterministically by scripts/generate_synthetic_demo_catchments.py.",
            "Created 10 labelled rectangles with transparent invented area, runoff, drainage, blockage, and storage assumptions.",
            "No surveyed drainage, catchment, pump, flood-depth, or live-condition information was used.",
        ],
        "limitations": [
            "These are not surveyed drainage boundaries or real drainage-capacity measurements.",
            "All hydraulic values and intervention effects are demonstration assumptions.",
            "Outputs are modeled accumulation and ponding-depth equivalents only, not actual flood depth, predictions, or official advice.",
        ],
        "artifact_role": "served_layer",
    })
    print(f"Generated {OUTPUT.relative_to(ROOT)} with {len(features)} SYNTHETIC DEMO CATCHMENTS.")


if __name__ == "__main__":
    main()
