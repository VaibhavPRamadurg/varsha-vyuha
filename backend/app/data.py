from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_DIR = BACKEND_DIR.parent
GRID_PATH = REPOSITORY_DIR / "data" / "synthetic" / "mumbai_sion_kurla_demo_grid_v2.geojson"
MANIFEST_DIR = REPOSITORY_DIR / "data" / "manifests"
IMD_SUMMARY_PATH = REPOSITORY_DIR / "data" / "processed" / "imd_mumbai_sion_kurla_2023_monsoon_summary.geojson"
OSM_CONTEXT_PATH = REPOSITORY_DIR / "data" / "processed" / "osm_sion_kurla_roads_water_reference.geojson"
EVIDENCE_DRIVERS_PATH = REPOSITORY_DIR / "data" / "processed" / "mumbai_sion_kurla_evidence_backed_scenario_drivers_v1.geojson"
CATCHMENTS_PATH = REPOSITORY_DIR / "data" / "synthetic" / "mumbai_sion_kurla_demo_catchments_v1.geojson"


def load_grid() -> dict[str, Any]:
    """Return only the packaged, explicitly synthetic 120-cell Mumbai v2 demo grid."""
    grid = json.loads(GRID_PATH.read_text(encoding="utf-8"))
    if grid.get("type") != "FeatureCollection":
        raise ValueError("Synthetic grid must be a GeoJSON FeatureCollection")
    for feature in grid.get("features", []):
        if feature.get("properties", {}).get("provenance") != "SYNTHETIC_SCENARIO":
            raise ValueError("Backend accepts only SYNTHETIC_SCENARIO fixture cells")
    return grid


def grid_cells() -> dict[str, dict[str, Any]]:
    """Join synthetic display geometry to independently derived evidence drivers.

    The synthetic grid remains only a stable scenario partition. Fixed score inputs
    are never read from its legacy synthetic properties.
    """
    grid = {feature["properties"]["grid_id"]: feature for feature in load_grid()["features"]}
    drivers = load_evidence_drivers()
    if set(grid) != set(drivers):
        raise ValueError("Evidence-backed driver cells do not exactly match the scenario grid")
    return {
        cell_id: {
            **feature,
            "properties": {
                "grid_id": cell_id,
                "grid_provenance": "synthetic",
                "evidence_drivers": drivers[cell_id]["properties"],
            },
        }
        for cell_id, feature in grid.items()
    }


def load_evidence_drivers() -> dict[str, dict[str, Any]]:
    """Load only the checksum-verified derived fixed drivers used by the model."""
    artifact = json.loads(EVIDENCE_DRIVERS_PATH.read_text(encoding="utf-8"))
    if artifact.get("provenance") != "DERIVED" or artifact.get("source_type") != "derived":
        raise ValueError("Scenario driver artifact must be explicitly derived")
    required = {
        "historical_rainfall_relative",
        "relative_low_elevation_susceptibility",
        "water_proximity_susceptibility",
        "driver_provenance",
    }
    expected_provenance = {
        "historical_rainfall": "observed",
        "relative_low_elevation": "derived",
        "water_proximity": "derived",
        "drainage_blockage": "synthetic",
    }
    output: dict[str, dict[str, Any]] = {}
    for feature in artifact.get("features", []):
        properties = feature.get("properties", {})
        if not required.issubset(properties) or properties.get("driver_provenance") != expected_provenance:
            raise ValueError("Evidence driver artifact is incomplete or has invalid per-driver provenance")
        if any("synthetic_baseline" in key or "road_proximity" in key for key in properties):
            raise ValueError("Synthetic baseline and road-proximity drivers are prohibited")
        output[properties["grid_id"]] = feature
    if len(output) != 120:
        raise ValueError("Expected 120 evidence-backed scenario driver records")
    return output


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verified_dataset_metadata() -> list[dict[str, Any]]:
    """Expose served artifacts only when their checksums still match manifests.

    Raw-input manifests remain versioned and are checked by the offline verifier,
    but they are intentionally not served: production deployments package only
    reviewed processed/synthetic artifacts and never the local raw downloads.
    """
    datasets: list[dict[str, Any]] = []
    for manifest_path in sorted(MANIFEST_DIR.glob("*.manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("artifact_role") == "raw_input":
            continue
        artifact = REPOSITORY_DIR / manifest["file_name"]
        if not artifact.is_file() or _sha256(artifact) != manifest["sha256"]:
            raise ValueError(f"Dataset manifest checksum verification failed: {manifest_path.name}")
        datasets.append(manifest)
    return datasets


def load_historical_evidence() -> dict[str, Any]:
    """Return observed rainfall and clearly derived OSM context, never scenarios."""
    imd = json.loads(IMD_SUMMARY_PATH.read_text(encoding="utf-8"))
    osm = json.loads(OSM_CONTEXT_PATH.read_text(encoding="utf-8"))
    if imd.get("provenance") != "OBSERVED" or osm.get("provenance") != "DERIVED FROM OPENSTREETMAP":
        raise ValueError("Historical evidence artifacts have unexpected provenance")
    roads = [feature for feature in osm["features"] if feature["properties"]["reference_category"] == "road"]
    water = [feature for feature in osm["features"] if feature["properties"]["reference_category"] != "road"]
    return {
        "mode": "historical_evidence",
        "provenance": "observed",
        "disclaimer": "Observed gridded rainfall; not street-level rainfall or an official flood warning.",
        "rainfall": {
            "provenance": "observed",
            "source_type": "observed",
            "source": "India Meteorological Department (IMD), Climate Research & Services, Pune",
            "period": imd["period"],
            "units": imd["units"],
            "study_area_weighted_total_mm": imd["study_area_weighted_total_mm"],
            "study_area_weighted_mean_mm_per_day": imd["study_area_weighted_mean_mm_per_day"],
            "grid": {key: imd[key] for key in ("type", "name", "features")},
            "limitations": [
                "The study area is represented by two 0.25° IMD grid cells, not local street-level observations.",
                "The values summarize 1 June–30 September 2023 and do not describe flood extent or flood risk.",
            ],
        },
        "osm_context": {
            "provenance": "derived",
            "label": "DERIVED FROM OPENSTREETMAP",
            "attribution": "© OpenStreetMap contributors",
            "roads": {"type": "FeatureCollection", "features": roads},
            "water": {"type": "FeatureCollection", "features": water},
            "limitations": [
                "Reference context only; roads and water features do not indicate flood conditions, routes, or facility availability.",
                "OpenStreetMap is community-maintained and may be incomplete or stale.",
            ],
        },
    }


def load_reference_context() -> dict[str, Any]:
    """Return only locally packaged OSM roads/water for the Scenario Lab map."""
    evidence = load_historical_evidence()
    return {
        "provenance": "derived",
        "label": evidence["osm_context"]["label"],
        "attribution": evidence["osm_context"]["attribution"],
        "roads": evidence["osm_context"]["roads"],
        "water": evidence["osm_context"]["water"],
        "limitations": evidence["osm_context"]["limitations"],
    }


def load_mitigation_catchments() -> dict[str, Any]:
    """Load only explicitly synthetic demo catchments and their assumptions."""
    collection = json.loads(CATCHMENTS_PATH.read_text(encoding="utf-8"))
    features = collection.get("features", [])
    required = {
        "catchment_id", "area_m2", "runoff_coefficient", "base_drainage_capacity_m3_per_hour",
        "assumed_blockage_fraction", "ponding_storage_capacity_m3", "optional_pump_capacity_m3_per_hour",
    }
    if len(features) != 10:
        raise ValueError("Expected exactly 10 SYNTHETIC DEMO CATCHMENTS")
    for feature in features:
        properties = feature.get("properties", {})
        if properties.get("provenance") != "SYNTHETIC_DEMO_CATCHMENT" or not required.issubset(properties):
            raise ValueError("Catchment artifact lacks required synthetic-demo assumptions")
    return collection
