# Mumbai MVP data-source register

## Acquired for the offline demo

| Artifact | Classification | Status | Notes |
| --- | --- | --- | --- |
| `mumbai_sion_kurla_demo_grid_v1.geojson` | `synthetic` | Included, retained | Original deterministic 30-cell grid and invented driver proxies. It is retained for version history and is not used by the current UI. |
| `mumbai_sion_kurla_demo_grid_v2.geojson` | `synthetic` | Included, current Scenario Lab fixture | Deterministic 120-cell (12 × 10) display partition with no fixed score-driver values. Smaller cells improve visual granularity only; they do not create street-level accuracy or evidence. |
| `mumbai_sion_kurla_demo_catchments_v1.geojson` | `synthetic` | Included, mitigation simulator fixture | Ten labelled `SYNTHETIC DEMO CATCHMENTS` with invented area/runoff/drainage/storage assumptions. They are not surveyed drainage boundaries. |
| `imd_mumbai_sion_kurla_rainfall_2023_monsoon.nc` | `observed` | Local immutable raw input | IMD daily 0.25° gridded rainfall, 1 June–30 September 2023. The Sion–Kurla area overlaps two coarse cells; it is not street-level rainfall or a flood warning. |
| `imd_mumbai_sion_kurla_2023_monsoon_summary.geojson` | `derived` | Included processed artifact | Period summary and grid-cell footprints derived from the verified IMD raw input; no risk calculation is performed. |
| `mumbai_sion_kurla_osm_reference.geojson` | `observed` | Local immutable raw input | OpenStreetMap snapshot exported by overpass-turbo on 2026-10-24. Required attribution: © OpenStreetMap contributors; ODbL applies. |
| `osm_sion_kurla_roads_water_reference.geojson` | `derived` | Included processed artifact | Retained real roads, waterways, and water-body geometry only. It is reference context, not a route, facility, or flood-status layer. |
| `Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif` | `observed` | Local immutable raw input | Public Copernicus DEM GLO-30 GeoTIFF for 19–20°N / 72–73°E. It covers Sion–Kurla; it is a surface model and can include built/vegetated features. |
| `mumbai_sion_kurla_evidence_backed_scenario_drivers_v1.geojson` | `derived` | Included processed artifact | Cell-level IMD baseline rainfall, Copernicus relative low-elevation susceptibility, and OSM water proximity. Roads are excluded from scoring; blockage is supplied only as a synthetic scenario input. |

## Approved acquisition candidate — not yet included

| Source | Intended use | Why it is not yet served |
| --- | --- | --- |
| [BMC Flooding Spots GIS layer](https://prsrvgisapp.mcgm.gov.in/server/rest/services/mcgm/MCGMGIS_Departments_Master_All_Layers/MapServer/344?f=pjson) | Historical/administrative hotspot reference, `observed` | On 2026-10-24, the Python TLS validation failed for the public endpoint and the provider response retrieved by curl was malformed JSON. No raw artifact or manifest was accepted, rather than weakening validation or misrepresenting corrupt data. |

## Candidate sources for a later human-approved refresh

- [IMD Mumbai rainfall information](https://mausam.imd.gov.in/mumbai/rainfall_info.php): official source; determine download terms and station/period coverage before adding data.
- [MCGM Climate Action Plan vulnerability assessment](https://portal.mcgm.gov.in/irj/go/km/docs/documents/Environment/Climate/VULNERABILITY%20ASSESSMENT%20REPORT%20-%20MCAP.pdf): contextual documentation only until an explicit downloadable geospatial dataset and licence are identified.

Historical Evidence serves only verified IMD observed-gridded rainfall and clearly attributed derived OpenStreetMap context. It does not substitute synthetic scenario material for observed evidence.
