#!/usr/bin/env python3
"""Acquire one official Mumbai reference layer and create demo-only grid data.

No processed or synthetic artifact is written into data/raw. Re-running the command
re-downloads the raw public-service snapshot deliberately; the manifest records its
checksum and access date.
"""

from __future__ import annotations

import hashlib
import json
import argparse
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
SYNTHETIC_DIR = ROOT / "data" / "synthetic"
MANIFEST_DIR = ROOT / "data" / "manifests"
BMC_FLOODING_SPOTS_URL = (
    "https://prsrvgisapp.mcgm.gov.in/server/rest/services/mcgm/"
    "MCGMGIS_Departments_Master_All_Layers/MapServer/344/query?"
    "where=1%3D1&outFields=*&f=geojson&outSR=4326"
)
BMC_LAYER_METADATA_URL = (
    "https://prsrvgisapp.mcgm.gov.in/server/rest/services/mcgm/"
    "MCGMGIS_Departments_Master_All_Layers/MapServer/344?f=pjson"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_bmc_flooding_spots(accessed_at: str) -> None:
    filename = "bmc_flooding_spots.geojson"
    target = RAW_DIR / filename
    request = Request(BMC_FLOODING_SPOTS_URL, headers={"User-Agent": "FloodShift-AI-MVP/0.1"})
    with urlopen(request, timeout=60) as response:
        payload = response.read()
    parsed = json.loads(payload)
    if parsed.get("type") != "FeatureCollection":
        raise ValueError("BMC service did not return a GeoJSON FeatureCollection")
    target.write_bytes(payload)
    write_json(
        MANIFEST_DIR / "bmc_flooding_spots.raw.manifest.json",
        {
            "file_name": f"data/raw/{filename}",
            "url": BMC_FLOODING_SPOTS_URL,
            "provider": "Municipal Corporation of Greater Mumbai (MCGM/BMC)",
            "access_date": accessed_at,
            "geographic_coverage": "Mumbai, Maharashtra, India; service-defined flooding-spot polygons",
            "period": "Undated hotspot/reference layer; not a real-time feed",
            "licence_terms_link": BMC_LAYER_METADATA_URL,
            "source_type": "observed",
            "sha256": sha256(target),
            "processing_steps": [
                "Downloaded unchanged as GeoJSON from the official public BMC GIS FeatureServer query endpoint.",
                "No filtering, geometry edits, or attribute edits were applied.",
                "Use only as historical/administrative hotspot evidence after human review of service metadata.",
            ],
            "limitations": [
                "The service does not expose event date, water depth, or real-time status in this artifact.",
                "This layer must not be presented as a current flood observation, forecast, or emergency warning.",
            ],
        },
    )


def build_synthetic_grid(accessed_at: str) -> None:
    """Create a compact Sion-Kurla-area visual demo grid; values are invented."""
    filename = "mumbai_sion_kurla_demo_grid_v1.geojson"
    target = SYNTHETIC_DIR / filename
    west, south, east, north = 72.865, 19.045, 72.915, 19.087
    columns, rows = 6, 5
    cell_width, cell_height = (east - west) / columns, (north - south) / rows
    features = []
    for row in range(rows):
        for col in range(columns):
            x0, y0 = west + col * cell_width, south + row * cell_height
            x1, y1 = x0 + cell_width, y0 + cell_height
            # Fixed values make demos repeatable. They are not measurements.
            elevation_proxy = round((((row * 3 + col * 5) % 10) + 1) / 10, 2)
            drainage_proxy = round((((row * 7 + col * 2) % 10) + 1) / 10, 2)
            synthetic_baseline_proxy = round((((row * 5 + col * 4) % 10) + 1) / 10, 2)
            features.append(
                {
                    "type": "Feature",
                    "id": f"MUM-DEMO-{row + 1:02d}-{col + 1:02d}",
                    "properties": {
                        "grid_id": f"MUM-DEMO-{row + 1:02d}-{col + 1:02d}",
                        "provenance": "SYNTHETIC_SCENARIO",
                        "demo_area": "Compact Sion-Kurla visual demo area",
                        "elevation_susceptibility": elevation_proxy,
                        "drainage_road_proximity_proxy": drainage_proxy,
                        "synthetic_baseline_susceptibility_proxy": synthetic_baseline_proxy,
                        "disclaimer": "Synthetic demo-only driver values; not measured terrain, drainage, or flood evidence.",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]],
                    },
                }
            )
    write_json(target, {"type": "FeatureCollection", "features": features})
    write_json(
        MANIFEST_DIR / "mumbai_sion_kurla_demo_grid_v1.synthetic.manifest.json",
        {
            "file_name": f"data/synthetic/{filename}",
            "url": "synthetic://floodshift-ai/mumbai/sion-kurla-demo-grid/v1",
            "provider": "FloodShift AI MVP demo generator",
            "access_date": accessed_at,
            "geographic_coverage": "Compact Sion-Kurla-area bounding box, Mumbai, Maharashtra, India",
            "period": "Not applicable; deterministic synthetic demo artifact",
            "licence_terms_link": "https://creativecommons.org/licenses/by/4.0/",
            "source_type": "synthetic",
            "sha256": sha256(target),
            "processing_steps": [
                "Generated deterministically by scripts/acquire_mumbai_reference_data.py.",
                "Created 30 square cells over a compact visual demo area.",
                "Assigned invented fixed driver proxies solely for scenario demonstration.",
            ],
            "limitations": [
                "All values and grid geometry are synthetic scenario material.",
                "Do not display as observed conditions, official forecast, or measured flood risk.",
            ],
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--synthetic-only",
        action="store_true",
        help="Generate only the local synthetic demo grid; do not contact BMC.",
    )
    args = parser.parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    accessed_at = datetime.now(UTC).date().isoformat()
    if not args.synthetic_only:
        fetch_bmc_flooding_spots(accessed_at)
    build_synthetic_grid(accessed_at)
    if args.synthetic_only:
        print("Generated synthetic Mumbai demo grid only.")
    else:
        print("Acquired official BMC flooding-spots snapshot and generated synthetic Mumbai demo grid.")


if __name__ == "__main__":
    main()
