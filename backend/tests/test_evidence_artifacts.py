"""Regression checks for the reproducible IMD + DEM + OSM scenario inputs."""

from __future__ import annotations

import json
from pathlib import Path

import rasterio


ROOT = Path(__file__).resolve().parents[2]
RAW_DEM = ROOT / "data/raw/copernicus_dem/Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
DRIVERS = ROOT / "data/processed/mumbai_sion_kurla_evidence_backed_scenario_drivers_v1.geojson"


def test_copernicus_dem_raw_input_covers_study_area_at_glo30_spacing() -> None:
    with rasterio.open(RAW_DEM) as dataset:
        assert str(dataset.crs) == "EPSG:4326"
        assert dataset.count == 1
        assert dataset.width == dataset.height == 3600
        assert dataset.bounds.left <= 72.865 < dataset.bounds.right
        assert dataset.bounds.bottom <= 19.045 < dataset.bounds.top
        assert dataset.res == (1 / 3600, 1 / 3600)


def test_processed_drivers_retain_imd_dem_and_osm_lineage() -> None:
    artifact = json.loads(DRIVERS.read_text(encoding="utf-8"))
    assert artifact["provenance"] == "DERIVED"
    assert len(artifact["features"]) == 120
    properties = artifact["features"][0]["properties"]
    assert properties["historical_rainfall_baseline_mm_per_day"] > 0
    assert properties["copernicus_dem_mean_surface_elevation_m"] > 0
    assert properties["water_distance_to_verified_osm_context_m"] >= 0
    assert properties["driver_sources"] == {
        "historical_rainfall": "IMD 2023 observed daily gridded rainfall",
        "relative_low_elevation": "Derived from Copernicus DEM GLO-30 cell statistics",
        "water_proximity": "Derived from local verified OSM waterways and water bodies",
        "drainage_blockage": "User-selected synthetic scenario input",
    }
