# VarshaVyuha — Urban Flood Resilience Lab · 2-minute judge demo

## 0:00–0:20 — Problem

“Urban flood-resilience decisions need understandable context: rainfall stress, local susceptibility, drainage disruption, and the surrounding road/water network. Most tools either hide their reasoning or overstate certainty.”

## 0:20–0:40 — Solution

“VarshaVyuha is an explainable decision-support prototype for Mumbai. It keeps verified historical evidence separate from a clearly synthetic Scenario Lab.” Point out the permanent prototype disclaimer, the offline map, roads/water context, attribution, and the `SYNTHETIC SCENARIO` badge.

## 0:40–1:05 — Scenario comparison

Set rainfall to **2.0×** and drainage blockage to **50%**, then choose **Run scenario**. “This is a deterministic evidence-backed scenario estimate, not a forecast. The map recolours the 120-cell demo grid while local OSM roads and waterways remain visible underneath.” Point to **Scenario change from baseline**, which compares medium/high/critical counts with the 1.0× observed-rainfall baseline / 0% synthetic blockage baseline.

## 1:05–1:25 — Explainable cell result

Click a coloured cell. “Every score is 0–100 with a readable band and four transparent contributors: observed IMD historical rainfall, Copernicus DEM relative low elevation, OSM water proximity, and the user-selected synthetic drainage blockage. The provenance badge beside each driver makes that distinction explicit.”

## Mitigation Simulator — 20 seconds

Scroll below the selected-cell card. “This is a separate water-balance demonstration over 10 **SYNTHETIC DEMO CATCHMENTS**, not surveyed drainage boundaries.” Set a rainfall intensity and duration, select **Clean drains** and **Deploy pumps**, then choose **Compare with baseline**. Point to the before/after m³ metrics and chart: “These are modeled accumulation and ponding-depth equivalents under demonstration assumptions—not actual flood depth, live drainage conditions, or official mitigation advice.”

## 1:25–1:45 — Evidence integrity

Switch to **Historical Evidence**. “Here, the app shows observed IMD gridded rainfall for 1 June–30 September 2023 and OpenStreetMap roads/water as derived context. The view says exactly what it is not: street-level rainfall, a flood warning, or a risk estimate.”

## 1:45–2:00 — Limitations and next step

“VarshaVyuha does not issue alerts, predict floods, guarantee routes, or show facilities. The IMD grid is coarse, and OSM is reference context. Next, we would add reviewed local observations and validated municipal layers with the same manifest, checksum, source, and limitation discipline.”
