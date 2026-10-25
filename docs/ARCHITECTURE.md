# VarshaVyuha — Urban Flood Resilience Lab · MVP Architecture

## Purpose and boundary

VarshaVyuha is an explainable, neighbourhood-scale urban flood-resilience **decision-support prototype** for Mumbai, Maharashtra, India. It uses a compact grid-based demo area for the MVP. It is not an official flood forecast, emergency warning system, or route/navigation guarantee. The product must remain usable in a live demo without external APIs.

## System shape

```text
React + TypeScript + Vite (MapLibre GL JS UI)
              |
              | HTTP / JSON
              v
FastAPI (validation, layer catalogue, deterministic risk engine)
              |
              v
Versioned CSV / GeoJSON + manifests + risk-model configuration
```

The frontend renders a local dark MapLibre style and local vector layers. An optional MapTiler vector style can add attributable 3D buildings only when a deployer provides `VITE_MAPTILER_KEY`; without it, the map remains offline-capable and does not invent buildings. The backend reads bundled, versioned artifacts and computes Scenario Lab outputs in memory. No database or runtime dependency on third-party services is required for the MVP.

## Repository layout

```text
frontend/                 React client
backend/                  FastAPI app, schemas, risk engine, tests
data/raw/                 untouched manual downloads; gitignored
data/processed/           reproducible observed/derived artifacts
data/synthetic/           demo-only scenario inputs/layers
data/manifests/           dataset provenance manifests
docs/                     product, data and deployment documentation
scripts/                  reproducible processing/validation utilities
```

## Data modes and provenance

Every layer and numeric value returned to the UI has a `provenance` value:

| Value | Meaning |
| --- | --- |
| `OBSERVED` | Downloaded measurements or historical evidence, shown with source and period. |
| `OFFICIAL_FORECAST` | Official forecast product, with provider and issue time. |
| `DERIVED` | Reproducibly calculated from named source datasets. |
| `SYNTHETIC_SCENARIO` | Clearly labelled demo/model input or output; never presented as measured fact. |

Historical Evidence only exposes downloaded observed datasets (and their source/date metadata). Scenario Lab retains a visibly synthetic grid and a synthetic blockage control, but its fixed drivers are evidence-backed. Its overall output is a `scenario_estimate`, never a prediction; each driver reports its own `observed`, `derived`, or `synthetic` provenance.

Each source artifact receives a JSON or YAML manifest with file name, URL, provider, access date, coverage, period, licence/terms URL, SHA-256, `source_type`, and processing steps. `data/raw/` is immutable to application code and excluded from Git.

## API surface (initial)

| Endpoint | Role |
| --- | --- |
| `GET /health` | Demo/deployment health check. |
| `GET /api/v1/metadata` | City, disclaimer, data-mode catalogue, model version. |
| `GET /api/v1/layers` | Available historical/derived/synthetic layer catalogue and manifests. |
| `GET /api/v1/layers/{layer_id}` | GeoJSON layer plus per-feature provenance. |
| `POST /api/v1/scenarios/evaluate` | Validated rainfall and blockage inputs; returns grid/ward risk features, drivers, explanations, and safer-facility/avoidance guidance. |

Pydantic schemas make provenance mandatory and reject unknown source types. The client should be able to run against a bundled sample response if the backend is unreachable during a presentation.

## Evidence-backed risk model v1.2

For each grid cell or ward, normalize inputs to `[0, 1]` and calculate:

```text
risk_score = 100 × (
  historical_rainfall_weight × observed_IMD_baseline_scaled_by_multiplier +
  relative_low_elevation_weight × Copernicus_DEM_relative_susceptibility +
  water_proximity_weight × OSM_water_context_proximity +
  drainage_blockage_weight × synthetic_user_input
)
```

The scenario-grid geometry is stable synthetic display structure only; its former fixed synthetic driver properties are not read by the model. Roads remain visual context and are not a risk proxy. Weights, thresholds, model identifier and assumptions are stored in a versioned configuration file. The response includes raw/normalized driver values, individual driver provenance/source, band (`low`, `medium`, `high`, `critical`), weights used, and a concise explanation. It makes no claim of predictive accuracy.

## Mitigation simulator

`data/synthetic/mumbai_sion_kurla_demo_catchments_v1.geojson` contains exactly 10 labelled `SYNTHETIC DEMO CATCHMENTS`; it is intentionally independent of surveyed hydrological boundaries. `backend/config/mitigation_model_v1.yaml` version-controls every intervention effect.

For each time step, the model adds `rainfall mm/hour ÷ 1000 × assumed area × runoff coefficient`, removes water through effective assumed drainage, clamps stored water at zero, and records excess beyond assumed ponding capacity. It reports modeled accumulation in m³, modeled ponding-depth equivalents, time series, and severity bands. A compare request evaluates the same inputs without and with selected interventions. Neither run is a prediction, flood-depth model, live drainage data, or official advice.

## UX safeguards

- Persistent, visible data-mode badge and “Not an official emergency warning” disclaimer.
- Historical Evidence and Scenario Lab are separate modes.
- Observed layers use a neutral/authoritative visual language; synthetic scenarios use a clearly differentiated pattern/label treatment.
- No facilities, routes, shelters, or avoidance guidance are shown in this MVP.
- Sources, access dates, periods and processing notes are available from the map UI.

## Quality and deployment

`pytest` covers risk bands, driver calculations, provenance contracts and API responses. Vitest + React Testing Library covers mode switching, disclaimer/badges, unavailable-backend fallback and key map/sidebar states. Deploy the static frontend to Vercel/Netlify and the FastAPI service to Render/Railway; bundle processed and synthetic demo data with the backend artifact.
