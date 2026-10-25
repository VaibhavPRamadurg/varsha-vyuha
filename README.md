# VarshaVyuha — Urban Flood Resilience Lab

VarshaVyuha is an explainable urban flood-resilience **decision-support prototype** for Mumbai, Maharashtra. It is not a flood forecast, official emergency warning, navigation system, or facility-availability service.

## Problem and solution

Flood decisions are hard to explain when rainfall, local susceptibility, drainage disruption, and map context are disconnected. VarshaVyuha makes those inputs inspectable in two deliberately separate modes:

- **Scenario Lab** — an offline-capable, deterministic 120-cell (12 × 10) scenario estimate. The map partition is synthetic, but its fixed drivers are evidence-backed: IMD 2023 rainfall (`OBSERVED`), Copernicus DEM relative elevation (`DERIVED`), and OSM water context (`DERIVED`). Drainage blockage remains a clearly labelled synthetic what-if input.
- **Historical Evidence** — verified observed IMD gridded-rainfall summary for 1 June–30 September 2023, plus roads/water context derived from OpenStreetMap. It never presents a risk score, prediction, flood extent, alert, route, shelter, or facility layer.
- **Mitigation Simulator** — a separate deterministic water-balance demonstration inside Scenario Lab. It uses 10 labelled `SYNTHETIC DEMO CATCHMENTS`, transparent assumed capacities, and versioned intervention effects to compare modeled accumulation only.

## Architecture

```text
React + TypeScript + Vite + Tailwind + MapLibre GL JS
                    │ local HTTP
                    ▼
             FastAPI API + risk engine
                    │
                    ▼
  versioned GeoJSON + YAML config + provenance manifests
```

The frontend is offline-friendly: MapLibre renders a dark local style plus local processed OSM vectors for Scenario Lab road/water reference context, so no raster tile service is required during a demo. FastAPI evaluates the deterministic scenario model in memory; no database or external live API is needed during a demo.

## MapLibre, 3D buildings, and offline behaviour

The default map is a locally styled MapLibre canvas with local processed OSM road/water vectors and the synthetic grid. It supports pan, zoom, pitch, rotation, hover, click-to-select, and a reduced-motion-aware initial camera movement. This is the reliable offline fallback; it does not fabricate building geometry or height.

Optional online Satellite + 3D context is available only when a deployer provides a MapTiler vector-style key:

```bash
# frontend/.env.local — never commit this file
VITE_MAPTILER_KEY=your_maptiler_key
```

With that variable set, the user can select **Satellite + 3D context**. It uses MapTiler’s attributable hybrid satellite/vector style and extrudes only provider building features with valid height/render-height data. **Offline vector context** remains the default. MapTiler/OpenStreetMap attribution remains visible in the map; satellite imagery is reference context only and does not change any scenario result. If the key is missing or online tiles/style loading fails, VarshaVyuha automatically returns to the local offline vector context with a clear status note. MapTiler is optional and is not used to represent rainfall, flood status, live conditions, or a prediction.

Copy `frontend/.env.example` to `frontend/.env.local`, then set `VITE_MAPTILER_KEY` locally. For Vercel/Netlify, configure that same environment variable in the frontend project settings and rebuild; never commit a real key. No key is required for local/offline operation.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Service health and scenario-model version. |
| `GET /layers` | Available synthetic, observed, and derived layer catalogue. |
| `GET /areas` | Scenario Lab grid area and valid cell IDs. |
| `POST /scenario/evaluate` | Evidence-backed scenario estimate with scores, bands, per-driver provenance, weights, and explanations. |
| `GET /metadata/datasets` | Checksum-verified packaged dataset metadata. |
| `GET /historical/evidence` | Observed IMD summary and derived OSM context for Historical Evidence. |
| `GET /reference-context` | Local OSM roads/water context for the Scenario Lab map. |
| `GET /mitigation/catchments` | Ten synthetic demo catchments and their transparent assumptions. |
| `GET /mitigation/scenarios` | Versioned intervention assumptions and default inputs. |
| `POST /mitigation/simulate` | Modeled accumulation for one set of synthetic assumptions. |
| `POST /mitigation/compare` | Baseline-versus-intervention modeled-accumulation comparison. |

`POST /scenario/evaluate` accepts `rainfall_multiplier`, `drainage_blockage_percent`, `selected_cell_ids`, and an optional `scenario_name`. The result is `provenance: "scenario_estimate"`; every contributing driver includes its own `observed`, `derived`, or `synthetic` provenance.

## Evidence-backed scenario-model integrity

The versioned YAML model combines historical rainfall baseline (`OBSERVED`, an IMD 2023 daily-gridded mean scaled by the multiplier), relative low-elevation susceptibility (`DERIVED` from Copernicus DEM GLO-30), water proximity/context (`DERIVED` from verified local OSM waterways/water bodies), and drainage blockage (`SYNTHETIC`, user input only). Roads are map context only, never a score driver. There is no synthetic baseline-susceptibility value or historic-flood proxy in the scoring path. The comparison panel compares scenario-model runs against the 1.0× observed-rainfall baseline and 0% synthetic blockage; it is explicitly not a forecast.

## Mitigation simulator integrity

The mitigation feature is separate from the risk score. It applies a time-stepped water balance to 10 `SYNTHETIC DEMO CATCHMENTS`: `runoff = rainfall depth × assumed area × assumed runoff coefficient`. Effective drainage is assumed base capacity reduced by blockage, plus optional assumed pump capacity. Storage never becomes negative; excess beyond assumed storage is retained as modeled uncontained excess for mass-balance transparency.

Clean drains, deploy pumps, and upgrade drainage are versioned **demonstration assumptions** in `backend/config/mitigation_model_v1.yaml`. Results are modeled accumulated water in m³ and modeled ponding-depth equivalents only—not actual flood depth, live drainage conditions, predictions, or official mitigation advice.

The v2 grid divides the same study extent into 120 smaller synthetic cells. That improves visual scenario-map granularity only; it does **not** provide street-level accuracy, observed neighbourhood conditions, or a forecast.

## Data provenance and limitations

- `data/raw/` contains immutable manual downloads and is never altered by application code.
- `data/processed/` contains reproducible IMD, Copernicus DEM, and OSM derivatives; `data/synthetic/` contains only demo material, including the stable scenario-grid partition.
- Every artifact has a JSON manifest with source, period, access date, licence/terms link, processing history, source type, and SHA-256 checksum.
- Historical Evidence labels IMD as observed gridded rainfall and says: “Observed gridded rainfall; not street-level rainfall or an official flood warning.” IMD coverage is a coarse 0.25° grid, not local gauges.
- OSM roads/water are `DERIVED FROM OPENSTREETMAP` context with `© OpenStreetMap contributors` attribution. They are not routing, emergency, or facility data.
- Copernicus DEM GLO-30 is a public 30 m surface model. Its relative elevation is a coarse susceptibility proxy only: it can include buildings, infrastructure, and vegetation and does not establish drainage or street-level flood elevation.
- No flood prediction, official alert, evacuation route, hospital, shelter, flood extent, or measured neighbourhood flood-risk claim is made.
- Mitigation catchments are not surveyed drainage boundaries. Their areas, capacities, blockage fractions, and intervention effects are synthetic demo assumptions; no budget optimizer or export is included.

See [data source register](docs/DATA_SOURCES.md), [historical validation](docs/HISTORICAL_DATA_VALIDATION.md), and [architecture](docs/ARCHITECTURE.md).

## Local setup

Open two terminals at the repository root.

```bash
# Terminal 1: API
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r backend/requirements.txt
PYTHONPATH=backend uvicorn app.main:app --reload
```

```bash
# Terminal 2: dashboard
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The dashboard calls `http://127.0.0.1:8000` by default; set `VITE_API_BASE_URL` before starting Vite to point elsewhere.

Do **not** open `frontend/index.html` with `file://`; Vite must serve the app for module loading and configuration to work.

## Data processing and checks

```bash
# Recreate processed evidence only after manually placing verified raw files in data/raw/
python3 scripts/process_mumbai_historical_evidence.py

# Recreate evidence-backed fixed scenario drivers from IMD, Copernicus DEM, and OSM.
# This never modifies data/raw/.
python3 scripts/process_evidence_backed_scenario_drivers.py

# Recreate the v2 120-cell synthetic Scenario Lab fixture (does not alter v1 or data/raw/)
python3 scripts/generate_synthetic_grid_v2.py

# Recreate the 10 synthetic demo catchments (does not alter data/raw/)
python3 scripts/generate_synthetic_demo_catchments.py

# Verify every manifest and referenced artifact checksum
python3 scripts/verify_data_manifests.py

# Backend and frontend checks
PYTHONPATH=backend pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
```

The demo flow is in [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md); manual acceptance checks are in [docs/MANUAL_QA_CHECKLIST.md](docs/MANUAL_QA_CHECKLIST.md).

## Deployment overview

Release configurations are included but nothing has been deployed. Use `render.yaml` for Render **or** `railway.json` for Railway, and `vercel.json` for the Vite frontend. FastAPI reads a comma-separated `ALLOWED_FRONTEND_ORIGINS` environment variable, while retaining local Vite origins for development. Vercel needs `VITE_API_BASE_URL` and, optionally, `VITE_MAPTILER_KEY`; these are build-time frontend variables and must be set in Vercel before deployment. See the exact environment values, GitHub first-commit commands, deployment order, and public smoke-test checklist in [the deployment guide](docs/DEPLOYMENT.md).

## Pre-submission checklist

- [ ] GitHub repository includes README, manifests, and reproducible commands.
- [ ] Deployed frontend/API URL is configured and tested.
- [ ] Demo video shows Scenario Lab, baseline comparison, cell explanation, Historical Evidence, attribution, and disclaimer.
- [ ] Screenshots show both data modes, layer toggles, provenance labels, and limitations.
- [ ] Project description says decision-support prototype—not prediction, official warning, or navigation.
- [ ] Citations and acknowledgements match each manifest.
