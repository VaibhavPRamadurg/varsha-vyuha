# Historical data validation — Mumbai Sion–Kurla

Validated on 2026-10-24. Raw files were read only; neither file was changed, renamed, converted in place, or deleted.

## IMD rainfall NetCDF

| Field | Validation result |
| --- | --- |
| File | `data/raw/imd/imd_mumbai_sion_kurla_rainfall_2023_monsoon.nc` |
| Size | 22,732 bytes |
| SHA-256 | `c286bfb845d3876c74564dbaa30fae387c65f02aa7dba9d026110858bd9661a4` |
| Container/schema | NetCDF-4 / HDF5, CF-1.7; data is in the `/rain` group |
| Rainfall variable | `/rain/rain`, `float64`, `time × lat × lon` = `122 × 1 × 2`; `mm/day` |
| Coordinates / CRS | `lat` and `lon` in degrees north/east; `spatial_ref` is EPSG:4326 / WGS 84 |
| Timestamps | Daily, 2023-06-01 00:00:00 through 2023-09-30 00:00:00; 122 unique dates |
| Grid coordinates | latitude centre: 19.0; longitude centres: 72.75, 73.0 |
| Coverage | GeoTransform-derived outer extent: 18.875–19.125° N and 72.625–73.125° E; covers the 19.045–19.087° N, 72.865–72.915° E study area |
| Quality checks | 244/244 finite values, no missing values; range 0–288.143 mm/day; mean 25.203 mm/day |

The requested study box crosses the boundary between two 0.25° cells. It is therefore suitable only for coarse observed-gridded context, not neighbourhood or street-level rainfall. It does not establish flood depth, extent, probability, or an official warning.

## OpenStreetMap GeoJSON

| Field | Validation result |
| --- | --- |
| File | `data/raw/osm/mumbai_sion_kurla_osm_reference.geojson` |
| Size | 4,367,637 bytes |
| SHA-256 | `2c3a398405a64345a1d86016767907d87372e21d802a01f338b097f89e1b8e36` |
| Schema / CRS | GeoJSON `FeatureCollection`, 5,882 features; no explicit `crs` member, so RFC 7946 WGS 84 longitude/latitude coordinates apply |
| Export metadata | `overpass-turbo`; timestamp `2026-10-24T17:49:20Z`; source copyright text requires OpenStreetMap / ODbL attribution |
| Coverage | 19.0082618–19.1001103° N, 72.8368476–72.9618037° E; covers the Sion–Kurla study area |
| Geometry | 5,743 LineStrings, 31 Polygons, and 108 Points |
| Usable roads | 5,672 `highway`-tagged features (5,671 lines and 1 polygon) |
| Water context | 72 `waterway` lines and 22 water/natural-water polygons |
| Hospital validation | 116 hospital-tagged features (108 points, 8 polygons); retained only for validation and deliberately not served in Historical Evidence |

Data-quality limitations: 4,619 road features and 70 waterway features have no name; OSM is community-maintained, potentially incomplete or stale, and can contain feature duplication or inconsistent tagging. Roads/water are displayed only as `DERIVED FROM OPENSTREETMAP` reference context with `© OpenStreetMap contributors`; they are not navigation, emergency, facility-availability, or flood-status data.

## Processed artifacts

`scripts/process_mumbai_historical_evidence.py` reads the two immutable raw inputs and writes only:

- `data/processed/imd_mumbai_sion_kurla_2023_monsoon_summary.geojson` — two observed-grid-cell period summaries plus a study-area weighted summary (3,329.434 mm total; 27.290 mm/day mean).
- `data/processed/osm_sion_kurla_roads_water_reference.geojson` — 5,672 roads, 72 waterways, and 22 water bodies; hospitals are excluded.

Every raw and processed artifact has a checksum manifest in `data/manifests/`. Re-run the script followed by `python3 scripts/verify_data_manifests.py` after replacing either raw file.
