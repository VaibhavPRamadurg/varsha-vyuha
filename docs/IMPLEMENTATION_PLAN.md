# VarshaVyuha — Urban Flood Resilience Lab · Phased Implementation Plan

## Phase 0 — Product and data contract (this phase)

- Target confirmed: Mumbai, Maharashtra; compact square grid cells for the MVP demo geography.
- Approve architecture, provenance conventions and model disclaimer.
- Define initial source candidates and licence/terms constraints before downloading data.

**Exit criterion:** approved architecture and a city-specific source plan.

## Phase 1 — Repository and deterministic backend foundation

- Create frontend/backend/data/docs/scripts structure and Git ignore rules protecting `data/raw/`.
- Add FastAPI app, Pydantic API contracts, provenance enums, model configuration and health/metadata endpoints.
- Implement the deterministic risk engine with unit tests and a packaged fallback fixture.

**Exit criterion:** API can calculate a transparent scenario entirely from local fixture data.

## Phase 2 — Data pipeline and integrity

- Add source-manifest schema, checksum validation and reproducible processing scripts.
- Download/manual-ingest approved datasets without modifying raw inputs.
- Produce processed map layers and clearly isolated synthetic demo layers.

**Exit criterion:** every served layer has validated provenance and a manifest.

## Phase 3 — Map experience

- Build the React/Tailwind/Leaflet shell with city map, mode selector, persistent disclaimer and provenance badge.
- Implement Historical Evidence with source/date panels.
- Implement Scenario Lab controls, risk layer, drivers/explanations, facilities and avoidance areas.
- Add client-side local fallback if the API is unavailable.

**Exit criterion:** end-to-end demo works offline with synthetic scenario data clearly marked.

## Phase 4 — Verification and presentation readiness

- Add API, risk-model and key UI-state tests.
- Validate accessibility, visual distinction between observed and synthetic data, and unsupported-claim wording.
- Add deployment configuration, runbook, data dictionary and demo script.

**Exit criterion:** reproducible deployment and a resilient live-demo flow.

## Decisions required before Phase 1

1. Target city and state.
2. Geography: wards, regular grid cells, or both.
3. Whether the initial demo uses only synthetic scenario data until real sources are approved, or includes specific downloaded historical datasets.
4. Preferred hosting pair: Vercel + Render, Netlify + Railway, or another approved combination.
