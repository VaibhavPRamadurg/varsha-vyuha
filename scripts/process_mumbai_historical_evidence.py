#!/usr/bin/env python3
"""Build packaged historical-evidence derivatives without changing data/raw.

Inputs are a manually downloaded IMD NetCDF file and an OpenStreetMap GeoJSON
snapshot. Outputs are deliberately limited to an observed rainfall summary and
derived roads/water reference context; no flood-risk or facility layer is made.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
from netCDF4 import Dataset, num2date


ROOT = Path(__file__).resolve().parents[1]
RAW_IMD = ROOT / "data/raw/imd/imd_mumbai_sion_kurla_rainfall_2023_monsoon.nc"
RAW_OSM = ROOT / "data/raw/osm/mumbai_sion_kurla_osm_reference.geojson"
PROCESSED = ROOT / "data/processed"
MANIFESTS = ROOT / "data/manifests"
ACCESS_DATE = "2026-10-24"
IMD_SOURCE_URL = "https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html"
OSM_SOURCE_URL = "https://www.openstreetmap.org/"
OSM_LICENCE_URL = "https://www.openstreetmap.org/copyright"
STUDY_BOUNDS = {"west": 72.865, "south": 19.045, "east": 72.915, "north": 19.087}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rectangle(west: float, south: float, east: float, north: float) -> dict[str, Any]:
    return {
        "type": "Polygon",
        "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
    }


def overlap_area_fraction(west: float, south: float, east: float, north: float) -> float:
    overlap_width = max(0.0, min(east, STUDY_BOUNDS["east"]) - max(west, STUDY_BOUNDS["west"]))
    overlap_height = max(0.0, min(north, STUDY_BOUNDS["north"]) - max(south, STUDY_BOUNDS["south"]))
    return (overlap_width * overlap_height) / ((east - west) * (north - south))


def process_imd() -> tuple[Path, dict[str, Any]]:
    """Summarise daily observed rainfall by the two covering IMD grid cells."""
    with Dataset(RAW_IMD) as source:
        if "rain" not in source.groups:
            raise ValueError("Expected /rain NetCDF group was not found")
        group = source.groups["rain"]
        for name in ("lat", "lon", "time", "rain", "spatial_ref"):
            if name not in group.variables:
                raise ValueError(f"Expected IMD variable is missing: {name}")
        rain_variable = group.variables["rain"]
        if rain_variable.dimensions != ("time", "lat", "lon") or rain_variable.units != "mm/day":
            raise ValueError("IMD rainfall schema is not the expected daily time/lat/lon mm/day layout")
        latitudes = np.asarray(group.variables["lat"][:], dtype=float)
        longitudes = np.asarray(group.variables["lon"][:], dtype=float)
        rainfall = np.asarray(rain_variable[:], dtype=float)
        time_variable = group.variables["time"]
        timestamps = num2date(
            time_variable[:], time_variable.units, calendar=getattr(time_variable, "calendar", "standard"),
            only_use_cftime_datetimes=False, only_use_python_datetimes=True,
        )
        if str(timestamps[0].date()) != "2023-06-01" or str(timestamps[-1].date()) != "2023-09-30":
            raise ValueError("IMD file does not cover the requested 1 June–30 September 2023 period")
        transform = [float(value) for value in group.variables["spatial_ref"].getncattr("GeoTransform").split()]

    west_origin, pixel_width, _, north_origin, _, pixel_height = transform
    features: list[dict[str, Any]] = []
    weighted_total = 0.0
    weighted_mean = 0.0
    total_overlap = 0.0
    for lat_index, latitude in enumerate(latitudes):
        # GeoTransform is authoritative for pixel edges; coordinate arrays are centres.
        north = north_origin + lat_index * pixel_height
        south = north + pixel_height
        south, north = min(south, north), max(south, north)
        for lon_index, longitude in enumerate(longitudes):
            west = west_origin + lon_index * pixel_width
            east = west + pixel_width
            values = rainfall[:, lat_index, lon_index]
            if not np.isfinite(values).all():
                raise ValueError("IMD file has missing rainfall values in the requested period")
            fraction = overlap_area_fraction(west, south, east, north)
            total = float(np.sum(values))
            mean = float(np.mean(values))
            if fraction:
                weighted_total += total * fraction
                weighted_mean += mean * fraction
                total_overlap += fraction
            features.append({
                "type": "Feature",
                "id": f"IMD-2023-MONSOON-{lat_index + 1}-{lon_index + 1}",
                "properties": {
                    "grid_cell_id": f"IMD-2023-MONSOON-{lat_index + 1}-{lon_index + 1}",
                    "provenance": "OBSERVED",
                    "source_type": "observed",
                    "source": "India Meteorological Department (IMD), Climate Research & Services, Pune",
                    "period": "2023-06-01 to 2023-09-30",
                    "units": "mm/day",
                    "rainfall_total_mm": round(total, 3),
                    "rainfall_mean_mm_per_day": round(mean, 3),
                    "observation_count": int(values.size),
                    "latitude_center": float(latitude),
                    "longitude_center": float(longitude),
                    "study_area_overlap_fraction": round(fraction, 6),
                    "limitations": "0.25° gridded rainfall; not street-level rainfall and not an official flood warning.",
                },
                "geometry": rectangle(west, south, east, north),
            })
    if total_overlap <= 0:
        raise ValueError("The requested Sion–Kurla study area is outside the IMD grid coverage")
    output = PROCESSED / "imd_mumbai_sion_kurla_2023_monsoon_summary.geojson"
    summary = {
        "type": "FeatureCollection",
        "name": "Observed IMD gridded rainfall summary, Mumbai Sion–Kurla study area",
        "provenance": "OBSERVED",
        "source_type": "derived",
        "source_dataset": RAW_IMD.name,
        "period": "2023-06-01 to 2023-09-30",
        "units": "mm/day",
        "study_area_weighted_mean_mm_per_day": round(weighted_mean / total_overlap, 3),
        "study_area_weighted_total_mm": round(weighted_total / total_overlap, 3),
        "features": features,
    }
    write_json(output, summary)
    return output, summary


def process_osm() -> tuple[Path, dict[str, int]]:
    """Retain only real OSM transport and water context, never facilities."""
    source = json.loads(RAW_OSM.read_text(encoding="utf-8"))
    if source.get("type") != "FeatureCollection" or not isinstance(source.get("features"), list):
        raise ValueError("OSM input is not a GeoJSON FeatureCollection")
    output_features: list[dict[str, Any]] = []
    counts = {"roads": 0, "waterways": 0, "water_bodies": 0}
    for feature in source["features"]:
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry")
        if not geometry:
            continue
        category: str | None = None
        if properties.get("highway"):
            category = "road"
            counts["roads"] += 1
        elif properties.get("waterway"):
            category = "waterway"
            counts["waterways"] += 1
        elif properties.get("water") or properties.get("natural") == "water":
            category = "water_body"
            counts["water_bodies"] += 1
        if not category:
            continue
        output_properties = {
            "provenance": "DERIVED FROM OPENSTREETMAP",
            "source_type": "derived",
            "reference_category": category,
            "osm_id": properties.get("@id") or feature.get("id"),
            "name": properties.get("name"),
            "highway": properties.get("highway"),
            "waterway": properties.get("waterway"),
            "water": properties.get("water"),
            "natural": properties.get("natural"),
            "attribution": "© OpenStreetMap contributors",
        }
        output_features.append({
            "type": "Feature",
            "id": feature.get("id"),
            "properties": {key: value for key, value in output_properties.items() if value is not None},
            "geometry": geometry,
        })
    if not counts["roads"] or not (counts["waterways"] or counts["water_bodies"]):
        raise ValueError("OSM input does not contain both roads and water reference features")
    output = PROCESSED / "osm_sion_kurla_roads_water_reference.geojson"
    write_json(output, {
        "type": "FeatureCollection",
        "name": "Sion–Kurla roads and water reference context derived from OpenStreetMap",
        "provenance": "DERIVED FROM OPENSTREETMAP",
        "source_type": "derived",
        "attribution": "© OpenStreetMap contributors",
        "features": output_features,
    })
    return output, counts


def write_manifests(imd_output: Path, osm_output: Path, osm_counts: dict[str, int]) -> None:
    write_json(MANIFESTS / "imd_mumbai_sion_kurla_rainfall_2023_monsoon.raw.manifest.json", {
        "file_name": "data/raw/imd/imd_mumbai_sion_kurla_rainfall_2023_monsoon.nc",
        "url": IMD_SOURCE_URL,
        "provider": "India Meteorological Department (IMD), Climate Research & Services, Pune",
        "access_date": ACCESS_DATE,
        "geographic_coverage": "IMD 0.25° grid subset: 18.875–19.125° N, 72.625–73.125° E; covers the Sion–Kurla study area",
        "period": "2023-06-01 to 2023-09-30 (122 daily records)",
        "licence_terms_link": IMD_SOURCE_URL,
        "sha256": sha256(RAW_IMD),
        "source_type": "observed",
        "processing_steps": [
            "Manually downloaded unchanged into data/raw/imd/.",
            "Validated as CF-1.7 NetCDF-4 with /rain/rain in mm/day before processing.",
            "Raw artifact is never served by the application or modified by this script.",
        ],
        "limitations": [
            "The source is 0.25° gridded rainfall, not a station or street-level measurement.",
            "The compact study area crosses two very coarse grid cells; values cannot resolve neighbourhood variability.",
            "Observed rainfall is not an official flood warning, flood extent, or risk prediction.",
            "The IMD download page supplies a citation but the raw file contains no machine-readable licence text; users must follow IMD terms and citation guidance.",
        ],
        "artifact_role": "raw_input",
    })
    write_json(MANIFESTS / "osm_mumbai_sion_kurla_reference.raw.manifest.json", {
        "file_name": "data/raw/osm/mumbai_sion_kurla_osm_reference.geojson",
        "url": OSM_SOURCE_URL,
        "provider": "OpenStreetMap contributors (export generated by overpass-turbo)",
        "access_date": ACCESS_DATE,
        "geographic_coverage": "Mumbai reference export bounding box: 19.0082618–19.1001103° N, 72.8368476–72.9618037° E; covers the Sion–Kurla study area",
        "period": "OpenStreetMap snapshot exported 2026-10-24T17:49:20Z",
        "licence_terms_link": OSM_LICENCE_URL,
        "sha256": sha256(RAW_OSM),
        "source_type": "observed",
        "processing_steps": [
            "Manually downloaded unchanged into data/raw/osm/.",
            "Validated as RFC 7946 GeoJSON in WGS 84 longitude/latitude coordinates.",
            "Raw artifact is never served by the application or modified by this script.",
        ],
        "limitations": [
            "OpenStreetMap is community-maintained and may be incomplete, stale, duplicated, or differently tagged.",
            "This export has no explicit CRS member; RFC 7946 GeoJSON defaults to WGS 84 longitude/latitude.",
            "OpenStreetMap context is not an official navigation, emergency, facility, or flood-status source.",
        ],
        "artifact_role": "raw_input",
    })
    write_json(MANIFESTS / "imd_mumbai_sion_kurla_2023_monsoon_summary.derived.manifest.json", {
        "file_name": f"data/processed/{imd_output.name}",
        "url": IMD_SOURCE_URL,
        "provider": "FloodShift AI processing of India Meteorological Department observed gridded rainfall",
        "access_date": ACCESS_DATE,
        "geographic_coverage": "Two IMD 0.25° cells overlapping the Sion–Kurla study area, Mumbai, Maharashtra, India",
        "period": "2023-06-01 to 2023-09-30 (122 daily records)",
        "licence_terms_link": IMD_SOURCE_URL,
        "sha256": sha256(imd_output),
        "source_type": "derived",
        "processing_steps": [
            "Read data/raw/imd/imd_mumbai_sion_kurla_rainfall_2023_monsoon.nc without changing it.",
            "Validated the /rain/rain daily mm/day variable and exact requested time period.",
            "Summed and averaged each observed grid-cell time series and emitted its GeoTransform-derived polygon extent.",
            "Calculated a study-area-overlap weighted summary for display; no risk score, flood extent, or prediction was calculated.",
        ],
        "limitations": [
            "Derived display summary of observed 0.25° gridded rainfall; not street-level rainfall.",
            "This is not an official flood warning or a flood prediction.",
        ],
        "input_artifacts": [{"file_name": "data/raw/imd/imd_mumbai_sion_kurla_rainfall_2023_monsoon.nc", "sha256": sha256(RAW_IMD)}],
        "artifact_role": "served_layer",
    })
    write_json(MANIFESTS / "osm_sion_kurla_roads_water_reference.derived.manifest.json", {
        "file_name": f"data/processed/{osm_output.name}",
        "url": OSM_SOURCE_URL,
        "provider": "FloodShift AI processing of OpenStreetMap contributors data",
        "access_date": ACCESS_DATE,
        "geographic_coverage": "Sion–Kurla context in the downloaded Mumbai OpenStreetMap export",
        "period": "OpenStreetMap snapshot exported 2026-10-24T17:49:20Z",
        "licence_terms_link": OSM_LICENCE_URL,
        "sha256": sha256(osm_output),
        "source_type": "derived",
        "processing_steps": [
            "Read data/raw/osm/mumbai_sion_kurla_osm_reference.geojson without changing it.",
            f"Retained {osm_counts['roads']} highway-tagged road features, {osm_counts['waterways']} waterway features, and {osm_counts['water_bodies']} water-body polygons.",
            "Removed hospitals and all other feature categories from the served context layer.",
            "Copied source geometries without simplification and added provenance plus attribution fields.",
        ],
        "limitations": [
            "DERIVED FROM OPENSTREETMAP context only; it does not establish flood conditions, routes, or facility availability.",
            "OpenStreetMap contributors attribution and ODbL terms must remain visible.",
        ],
        "attribution": "© OpenStreetMap contributors",
        "input_artifacts": [{"file_name": "data/raw/osm/mumbai_sion_kurla_osm_reference.geojson", "sha256": sha256(RAW_OSM)}],
        "artifact_role": "served_layer",
    })


def main() -> None:
    if not RAW_IMD.is_file() or not RAW_OSM.is_file():
        raise SystemExit("Both immutable raw inputs must exist before processing.")
    PROCESSED.mkdir(parents=True, exist_ok=True)
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    imd_output, imd_summary = process_imd()
    osm_output, osm_counts = process_osm()
    write_manifests(imd_output, osm_output, osm_counts)
    print(
        f"Wrote {imd_output.relative_to(ROOT)} ({len(imd_summary['features'])} observed grid cells) and "
        f"{osm_output.relative_to(ROOT)} ({sum(osm_counts.values())} derived OSM features)."
    )


if __name__ == "__main__":
    main()
