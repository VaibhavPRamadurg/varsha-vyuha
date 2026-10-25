#!/usr/bin/env python3
"""Derive evidence-backed scenario drivers without mutating any raw input.

This produces a *driver artifact*, not a flood map.  The Scenario Lab retains a
synthetic grid geometry and synthetic drainage-blockage control, while rainfall,
relative elevation, and water context are reproducibly derived from documented
local inputs.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.mask import mask
from shapely import transform
from shapely.geometry import shape
from pyproj import Transformer


ROOT = Path(__file__).resolve().parents[1]
RAW_DEM = ROOT / "data/raw/copernicus_dem/Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
IMD = ROOT / "data/processed/imd_mumbai_sion_kurla_2023_monsoon_summary.geojson"
OSM = ROOT / "data/processed/osm_sion_kurla_roads_water_reference.geojson"
GRID = ROOT / "data/synthetic/mumbai_sion_kurla_demo_grid_v2.geojson"
OUTPUT = ROOT / "data/processed/mumbai_sion_kurla_evidence_backed_scenario_drivers_v1.geojson"
MANIFEST = ROOT / "data/manifests/mumbai_sion_kurla_evidence_backed_scenario_drivers_v1.derived.manifest.json"
RAW_MANIFEST = ROOT / "data/manifests/copernicus_dem_glo30_mumbai.raw.manifest.json"

DEM_URL = "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N19_00_E072_00_DEM/Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
DEM_LICENCE = "https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM"
ACCESS_DATE = "2026-10-25"
WATER_DISTANCE_CAP_METRES = 1500.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def weighted_rainfall(cell_geometry: Any, imd_features: list[dict[str, Any]]) -> float:
    weighted_value = 0.0
    total_area = 0.0
    for feature in imd_features:
        overlap = cell_geometry.intersection(shape(feature["geometry"]))
        if overlap.is_empty:
            continue
        # All shapes are in longitude/latitude; only relative overlaps are needed.
        area = overlap.area
        weighted_value += area * float(feature["properties"]["rainfall_mean_mm_per_day"])
        total_area += area
    if total_area <= 0:
        raise ValueError("A scenario grid cell is outside the verified IMD coverage")
    return weighted_value / total_area


def cell_dem_mean(dataset: rasterio.DatasetReader, cell_geometry: Any) -> float:
    values, _ = mask(dataset, [cell_geometry.__geo_interface__], crop=True, filled=False)
    band = values[0]
    usable = band.compressed() if np.ma.isMaskedArray(band) else band.ravel()
    usable = usable[np.isfinite(usable)]
    if usable.size == 0:
        raise ValueError("Copernicus DEM has no valid pixel values in a scenario grid cell")
    return float(np.mean(usable))


def main() -> None:
    required = (RAW_DEM, IMD, OSM, GRID)
    if not all(path.is_file() for path in required):
        missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
        raise SystemExit(f"Missing required artifact(s): {', '.join(missing)}")

    grid = read_geojson(GRID)
    imd = read_geojson(IMD)
    osm = read_geojson(OSM)
    if len(grid.get("features", [])) != 120:
        raise ValueError("Expected the versioned 120-cell synthetic grid")
    if any(feature["properties"].get("provenance") != "SYNTHETIC_SCENARIO" for feature in grid["features"]):
        raise ValueError("Grid artifact must remain explicitly synthetic")
    if any(feature["properties"].get("provenance") != "OBSERVED" for feature in imd["features"]):
        raise ValueError("IMD summary must retain observed provenance")

    water_geometries = [
        shape(feature["geometry"])
        for feature in osm["features"]
        if feature["properties"].get("reference_category") in {"waterway", "water_body"}
    ]
    if not water_geometries:
        raise ValueError("Verified OSM context has no waterways or water bodies")
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True).transform
    projected_water = [transform(geometry, to_utm, interleaved=False) for geometry in water_geometries]

    raw_records: list[dict[str, Any]] = []
    with rasterio.open(RAW_DEM) as dem:
        if str(dem.crs) != "EPSG:4326" or dem.count != 1 or dem.width != 3600 or dem.height != 3600:
            raise ValueError("Copernicus DEM metadata does not match the expected GLO-30 geographic COG")
        for feature in grid["features"]:
            geometry = shape(feature["geometry"])
            projected_centroid = transform(geometry.centroid, to_utm, interleaved=False)
            distance = min(projected_centroid.distance(water) for water in projected_water)
            raw_records.append({
                "grid_id": feature["properties"]["grid_id"],
                "geometry": feature["geometry"],
                "rainfall": weighted_rainfall(geometry, imd["features"]),
                "elevation": cell_dem_mean(dem, geometry),
                "water_distance": float(distance),
            })

    rainfall_max = max(record["rainfall"] for record in raw_records)
    elevation_min = min(record["elevation"] for record in raw_records)
    elevation_max = max(record["elevation"] for record in raw_records)
    if rainfall_max <= 0 or elevation_max <= elevation_min:
        raise ValueError("Evidence driver normalization has no usable variation")

    features: list[dict[str, Any]] = []
    for record in raw_records:
        # Lower relative DSM elevation is more susceptible. This is an evidence
        # proxy only: Copernicus GLO-30 is a surface model, not a drainage survey.
        low_elevation = (elevation_max - record["elevation"]) / (elevation_max - elevation_min)
        water_proximity = max(0.0, 1 - min(record["water_distance"], WATER_DISTANCE_CAP_METRES) / WATER_DISTANCE_CAP_METRES)
        features.append({
            "type": "Feature",
            "id": record["grid_id"],
            "geometry": record["geometry"],
            "properties": {
                "grid_id": record["grid_id"],
                "provenance": "DERIVED",
                "historical_rainfall_baseline_mm_per_day": round(record["rainfall"], 4),
                "historical_rainfall_relative": round(record["rainfall"] / rainfall_max, 6),
                "relative_low_elevation_susceptibility": round(low_elevation, 6),
                "copernicus_dem_mean_surface_elevation_m": round(record["elevation"], 3),
                "water_distance_to_verified_osm_context_m": round(record["water_distance"], 2),
                "water_proximity_susceptibility": round(water_proximity, 6),
                "driver_provenance": {
                    "historical_rainfall": "observed",
                    "relative_low_elevation": "derived",
                    "water_proximity": "derived",
                    "drainage_blockage": "synthetic",
                },
                "driver_sources": {
                    "historical_rainfall": "IMD 2023 observed daily gridded rainfall",
                    "relative_low_elevation": "Derived from Copernicus DEM GLO-30 cell statistics",
                    "water_proximity": "Derived from local verified OSM waterways and water bodies",
                    "drainage_blockage": "User-selected synthetic scenario input",
                },
                "limitations": "Evidence-backed inputs are coarse/proxy indicators; this artifact is not flood evidence, a prediction, or an official warning.",
            },
        })

    collection = {
        "type": "FeatureCollection",
        "name": "Evidence-backed scenario drivers for the Sion–Kurla 120-cell grid",
        "provenance": "DERIVED",
        "source_type": "derived",
        "model_input_role": "Evidence-backed fixed inputs only; drainage blockage remains a synthetic scenario input.",
        "features": features,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT, collection)

    write_json(RAW_MANIFEST, {
        "file_name": "data/raw/copernicus_dem/Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif",
        "url": DEM_URL,
        "provider": "Copernicus DEM GLO-30 Public via AWS Open Data",
        "access_date": ACCESS_DATE,
        "geographic_coverage": "1° × 1° tile: 19–20° N, 72–73° E; covers the Sion–Kurla study area",
        "period": "Copernicus DEM 2021 release; static elevation product",
        "licence_terms_link": DEM_LICENCE,
        "sha256": sha256(RAW_DEM),
        "source_type": "observed",
        "processing_steps": [
            "Downloaded unchanged from the documented public Copernicus DEM GLO-30 AWS object into data/raw/copernicus_dem/.",
            "Validated as a single-band EPSG:4326 Cloud Optimized GeoTIFF with 3600 × 3600 pixels at 1 arc-second spacing.",
            "The raw GeoTIFF is never modified or served by the application.",
        ],
        "limitations": [
            "Copernicus DEM GLO-30 is a Digital Surface Model and can include buildings, infrastructure, and vegetation.",
            "Its nominal 30 m resolution does not establish street-level drainage or flood elevation.",
            "Terrain input is used only as a relative susceptibility proxy, never as a flood forecast or official warning.",
        ],
        "artifact_role": "raw_input",
    })
    write_json(MANIFEST, {
        "file_name": f"data/processed/{OUTPUT.name}",
        "url": DEM_URL,
        "provider": "FloodShift AI reproducible processing of IMD, Copernicus DEM GLO-30, and OpenStreetMap inputs",
        "access_date": ACCESS_DATE,
        "geographic_coverage": "120 synthetic Scenario Lab cells across the Sion–Kurla study extent, Mumbai, Maharashtra, India",
        "period": "IMD rainfall: 2023-06-01 to 2023-09-30; DEM: Copernicus 2021 release; OSM: local verified export",
        "licence_terms_link": DEM_LICENCE,
        "sha256": sha256(OUTPUT),
        "source_type": "derived",
        "processing_steps": [
            "Read the immutable v2 synthetic grid geometry but ignored all its synthetic fixed driver values.",
            "Area-weighted each grid cell against IMD observed 2023 daily-rainfall mean values.",
            "Calculated mean Copernicus GLO-30 surface elevation within each grid cell and normalized relative low-elevation susceptibility across the study area.",
            "Calculated centroid-to-nearest verified OSM waterway/water-body distance in EPSG:32643 and capped normalized water proximity at 1500 m.",
            "Did not use roads as a score driver; drainage blockage is intentionally excluded because it is supplied only at scenario evaluation time.",
        ],
        "limitations": [
            "IMD rainfall is a coarse 0.25° observed grid and cannot resolve 120 local cells independently.",
            "Copernicus GLO-30 is a surface model, not a drainage, hydrodynamic, or surveyed street-elevation dataset.",
            "OSM water features are community-maintained reference context and may be incomplete or stale.",
            "Derived drivers support transparent scenario exploration only; they are not flood evidence, a prediction, or an official warning.",
        ],
        "input_artifacts": [
            {"file_name": "data/raw/imd/imd_mumbai_sion_kurla_rainfall_2023_monsoon.nc", "sha256": sha256(ROOT / "data/raw/imd/imd_mumbai_sion_kurla_rainfall_2023_monsoon.nc")},
            {"file_name": "data/raw/copernicus_dem/Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif", "sha256": sha256(RAW_DEM)},
            {"file_name": "data/raw/osm/mumbai_sion_kurla_osm_reference.geojson", "sha256": sha256(ROOT / "data/raw/osm/mumbai_sion_kurla_osm_reference.geojson")},
        ],
        "attribution": "© OpenStreetMap contributors for the water-context source",
        "artifact_role": "served_layer",
    })
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(features)} evidence-backed driver records.")


if __name__ == "__main__":
    main()
