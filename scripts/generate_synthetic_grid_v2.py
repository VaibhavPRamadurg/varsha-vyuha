#!/usr/bin/env python3
"""Generate the versioned 120-cell, demo-only Sion–Kurla Scenario Lab fixture.

This script never reads or writes data/raw and intentionally leaves v1 untouched.
It supplies only a stable synthetic display partition; fixed score drivers are
derived separately from verified IMD, Copernicus DEM, and OSM artifacts.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_DIR = ROOT / "data" / "synthetic"
MANIFEST_DIR = ROOT / "data" / "manifests"
FILENAME = "mumbai_sion_kurla_demo_grid_v2.geojson"


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    west, south, east, north = 72.865, 19.045, 72.915, 19.087
    columns, rows = 12, 10
    cell_width, cell_height = (east - west) / columns, (north - south) / rows
    features: list[dict[str, object]] = []
    for row in range(rows):
        for column in range(columns):
            x0, y0 = west + column * cell_width, south + row * cell_height
            x1, y1 = x0 + cell_width, y0 + cell_height
            grid_id = f"MUM-V2-{row + 1:02d}-{column + 1:02d}"
            features.append(
                {
                    "type": "Feature",
                    "id": grid_id,
                    "properties": {
                        "grid_id": grid_id,
                        "provenance": "SYNTHETIC_SCENARIO",
                        "demo_area": "Compact Sion-Kurla visual demo area",
                        "disclaimer": "Synthetic scenario-grid geometry only; fixed score drivers are stored in a separate evidence-backed artifact.",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]],
                    },
                }
            )
    target = SYNTHETIC_DIR / FILENAME
    write_json(target, {"type": "FeatureCollection", "features": features})
    write_json(
        MANIFEST_DIR / "mumbai_sion_kurla_demo_grid_v2.synthetic.manifest.json",
        {
            "file_name": f"data/synthetic/{FILENAME}",
            "url": "synthetic://floodshift-ai/mumbai/sion-kurla-demo-grid/v2",
            "provider": "FloodShift AI MVP demo generator",
            "access_date": datetime.now(UTC).date().isoformat(),
            "geographic_coverage": "Compact Sion-Kurla-area bounding box, Mumbai, Maharashtra, India",
            "period": "Not applicable; deterministic synthetic demo artifact",
            "licence_terms_link": "https://creativecommons.org/licenses/by/4.0/",
            "source_type": "synthetic",
            "sha256": checksum(target),
            "processing_steps": [
                "Generated deterministically by scripts/generate_synthetic_grid_v2.py.",
                "Created 120 square cells (12 columns × 10 rows) over the same compact Sion–Kurla demo extent as v1.",
                "Contains only stable synthetic grid geometry and identifiers; it has no fixed score-driver values.",
            ],
            "limitations": [
                "Grid geometry and identifiers are synthetic scenario material; fixed score drivers are not stored here.",
                "Smaller cells improve scenario-map granularity only; they do not provide street-level accuracy or turn this model into a forecast.",
                "Do not display as observed conditions, official forecast, or measured flood risk.",
                "Drainage blockage is supplied separately as a clearly labelled synthetic scenario input.",
            ],
        },
    )
    print(f"Generated {target.relative_to(ROOT)} with {len(features)} synthetic cells.")


if __name__ == "__main__":
    main()
