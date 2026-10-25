# Manual QA checklist

Run with FastAPI on `http://127.0.0.1:8000` and Vite on `http://127.0.0.1:5173`. Use the Vite URL, never `file://frontend/index.html`.

## Scenario Lab

- [ ] Header shows VarshaVyuha, Urban Flood Resilience Lab, Mumbai, and “Prototype — not an official emergency warning.”
- [ ] `SYNTHETIC SCENARIO` remains visible and Scenario Lab never calls its results a forecast.
- [ ] Map supports pan/zoom; its solid risk legend, study boundary, OSM attribution, and both layer toggles are readable.
- [ ] Toggle **Reference context — OSM roads and water** and **Synthetic risk grid** independently; roads stay muted grey and water blue.
- [ ] Confirm the semi-transparent synthetic grid remains clickable while road/water context is visible beneath it.
- [ ] Change rainfall to 2.0× and blockage to 50%, run the scenario, and confirm the map, cell counts, and selected-cell details update.
- [ ] Confirm **Synthetic scenario change from baseline** appears only after a non-baseline run, compares medium/high/critical cells against 1.0× / 0%, and says it is not a forecast.
- [ ] Click a cell and confirm score, band, explanation, and all four contributors appear: **Historical rainfall baseline** (OBSERVED), **Relative low-elevation susceptibility** (DERIVED), **Water proximity / context** (DERIVED), and **Drainage blockage** (SYNTHETIC INPUT).
- [ ] In Scenario Lab, scroll to **Mitigation Simulator** and confirm the `SYNTHETIC DEMO CATCHMENTS` label and demonstration-assumptions disclaimer are visible.
- [ ] Change mitigation rainfall, duration, and blockage; select an intervention, choose **Compare with baseline**, and confirm before/after m³, affected-catchment counts, percentage modeled reduction, and chart appear.
- [ ] Confirm mitigation language says “modeled accumulation” and never calls results actual flood depth, a prediction, live drainage conditions, or official advice.
- [ ] Reset and confirm sliders return to 1.0× and 0%, the comparison panel disappears, and baseline results reload.

## Historical Evidence

- [ ] Switch to **Historical Evidence** and confirm there is no synthetic risk grid, score, scenario control, flood extent, facility, shelter, route, or alert.
- [ ] Confirm IMD source, 1 June–30 September 2023 period, units, limitations, and “Observed gridded rainfall; not street-level rainfall or an official flood warning.”
- [ ] Confirm roads/water are labelled `DERIVED FROM OPENSTREETMAP` and retain `© OpenStreetMap contributors` attribution.

## Resilience and final review

- [ ] Stop the API, refresh Vite, and confirm a clear error/retry state; restart the API and confirm Retry recovers.
- [ ] Open Data & Method in both modes and confirm provenance, model version/weights, and limitations are legible.
- [ ] Confirm no browser-console errors and no claim of predictive accuracy, official warning status, navigation, or facility availability.
