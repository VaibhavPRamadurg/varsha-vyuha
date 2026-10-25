from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_is_explicitly_a_scenario_estimate() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["provenance"] == "scenario_estimate"


def test_local_vite_origin_is_allowed_to_call_the_api() -> None:
    response = client.options(
        "/scenario/evaluate",
        headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_v2_fixture_layer_and_area_have_one_hundred_twenty_synthetic_cells() -> None:
    layers = client.get("/layers").json()
    areas = client.get("/areas").json()
    assert layers[0]["id"] == "mumbai-sion-kurla-demo-grid-v2"
    assert layers[0]["feature_count"] == 120
    assert layers[0]["provenance"] == "synthetic"
    assert areas[0]["grid_cell_count"] == 120
    assert len(areas[0]["cell_ids"]) == 120
    assert areas[0]["cell_ids"][0] == "MUM-V2-01-01"


def test_dataset_metadata_exposes_checksum_verified_served_artifacts() -> None:
    response = client.get("/metadata/datasets")
    assert response.status_code == 200
    payload = response.json()
    assert payload["provenance"] == "mixed"
    paths = {dataset["file_name"] for dataset in payload["datasets"]}
    assert "data/synthetic/mumbai_sion_kurla_demo_grid_v2.geojson" in paths
    assert "data/processed/imd_mumbai_sion_kurla_2023_monsoon_summary.geojson" in paths
    assert "data/processed/osm_sion_kurla_roads_water_reference.geojson" in paths
    assert "data/processed/mumbai_sion_kurla_evidence_backed_scenario_drivers_v1.geojson" in paths
    assert not any(path.startswith("data/raw/") for path in paths)


def test_historical_evidence_keeps_observed_rainfall_separate_from_scenarios() -> None:
    response = client.get("/historical/evidence")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "historical_evidence"
    assert payload["provenance"] == "observed"
    assert payload["disclaimer"] == "Observed gridded rainfall; not street-level rainfall or an official flood warning."
    assert payload["rainfall"]["period"] == "2023-06-01 to 2023-09-30"
    assert payload["rainfall"]["units"] == "mm/day"
    assert len(payload["rainfall"]["grid"]["features"]) == 2
    assert all(feature["properties"]["provenance"] == "OBSERVED" for feature in payload["rainfall"]["grid"]["features"])
    assert payload["osm_context"]["label"] == "DERIVED FROM OPENSTREETMAP"
    assert payload["osm_context"]["attribution"] == "© OpenStreetMap contributors"
    assert len(payload["osm_context"]["roads"]["features"]) == 5672
    assert len(payload["osm_context"]["water"]["features"]) == 94
    assert "evaluated_cells" not in payload


def test_reference_context_serves_only_derived_osm_roads_and_water() -> None:
    response = client.get("/reference-context")
    assert response.status_code == 200
    payload = response.json()
    assert payload["provenance"] == "derived"
    assert payload["label"] == "DERIVED FROM OPENSTREETMAP"
    assert payload["attribution"] == "© OpenStreetMap contributors"
    assert len(payload["roads"]["features"]) == 5672
    assert len(payload["water"]["features"]) == 94
    assert "rainfall" not in payload


def test_scenario_contains_evidence_backed_drivers_with_per_driver_provenance() -> None:
    response = client.post(
        "/scenario/evaluate",
        json={
            "rainfall_multiplier": 1.5,
            "drainage_blockage_percent": 40,
            "selected_cell_ids": ["MUM-V2-01-01"],
            "scenario_name": "Monsoon stress test",
        },
    )
    assert response.status_code == 200
    result = response.json()["evaluated_cells"][0]
    assert result["provenance"] == "scenario_estimate"
    assert 0 <= result["risk_score"] <= 100
    assert set(result["drivers"]) == {
        "historical_rainfall",
        "relative_low_elevation",
        "water_proximity",
        "drainage_blockage",
    }
    assert result["drivers"]["historical_rainfall"]["provenance"] == "observed"
    assert result["drivers"]["relative_low_elevation"]["provenance"] == "derived"
    assert result["drivers"]["water_proximity"]["provenance"] == "derived"
    assert result["drivers"]["drainage_blockage"]["provenance"] == "synthetic"
    assert "road" not in result["drivers"]
    assert "baseline_susceptibility" not in result["drivers"]
    assert "not a prediction" in result["explanation"]
    assert result["model_version"] == response.json()["model_version"]
    assert sum(result["weights"].values()) == 1.0


def test_evidence_drivers_are_real_or_derived_and_have_no_synthetic_fixed_fallback() -> None:
    from app.data import grid_cells

    cell = grid_cells()["MUM-V2-01-01"]
    evidence = cell["properties"]["evidence_drivers"]
    assert evidence["historical_rainfall_baseline_mm_per_day"] > 0
    assert evidence["copernicus_dem_mean_surface_elevation_m"] > 0
    assert evidence["water_distance_to_verified_osm_context_m"] >= 0
    assert evidence["driver_provenance"] == {
        "historical_rainfall": "observed",
        "relative_low_elevation": "derived",
        "water_proximity": "derived",
        "drainage_blockage": "synthetic",
    }
    assert not any("synthetic_baseline" in key or "road_proximity" in key for key in evidence)


def test_higher_rainfall_never_lowers_risk_when_other_inputs_match() -> None:
    cell_ids = client.get("/areas").json()[0]["cell_ids"]
    base_request = {
        "drainage_blockage_percent": 35,
        "selected_cell_ids": cell_ids,
    }
    lower = client.post("/scenario/evaluate", json={**base_request, "rainfall_multiplier": 0.75})
    higher = client.post("/scenario/evaluate", json={**base_request, "rainfall_multiplier": 2.25})
    assert lower.status_code == higher.status_code == 200
    lower_scores = {item["cell_id"]: item["risk_score"] for item in lower.json()["evaluated_cells"]}
    higher_scores = {item["cell_id"]: item["risk_score"] for item in higher.json()["evaluated_cells"]}
    assert all(higher_scores[cell_id] >= lower_score for cell_id, lower_score in lower_scores.items())


def test_invalid_input_and_unknown_cell_are_rejected() -> None:
    invalid = client.post(
        "/scenario/evaluate",
        json={"rainfall_multiplier": 3.1, "drainage_blockage_percent": 0, "selected_cell_ids": ["MUM-V2-01-01"]},
    )
    unknown = client.post(
        "/scenario/evaluate",
        json={"rainfall_multiplier": 1, "drainage_blockage_percent": 0, "selected_cell_ids": ["NOT-A-CELL"]},
    )
    assert invalid.status_code == 422
    assert unknown.status_code == 422
