from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def payload(**overrides: object) -> dict[str, object]:
    return {
        "rainfall_intensity_mm_per_hour": 50,
        "rainfall_duration_hours": 3,
        "drain_blockage_percent": 20,
        "selected_interventions": [],
        **overrides,
    }


def test_catchment_catalogue_is_explicitly_synthetic_and_has_ten_features() -> None:
    response = client.get("/mitigation/catchments")
    assert response.status_code == 200
    assert response.json()["label"] == "SYNTHETIC DEMO CATCHMENTS"
    assert len(response.json()["catchments"]["features"]) == 10


def test_zero_rainfall_has_no_new_runoff_or_accumulation() -> None:
    response = client.post("/mitigation/simulate", json=payload(rainfall_intensity_mm_per_hour=0))
    assert response.status_code == 200
    for item in response.json()["per_catchment"]:
        assert item["modeled_runoff_volume_m3"] == 0
        assert item["modeled_accumulated_water_m3"] == 0


def test_higher_rainfall_cannot_reduce_accumulation() -> None:
    lower = client.post("/mitigation/simulate", json=payload(rainfall_intensity_mm_per_hour=25)).json()
    higher = client.post("/mitigation/simulate", json=payload(rainfall_intensity_mm_per_hour=80)).json()
    assert higher["total_modeled_accumulation_m3"] >= lower["total_modeled_accumulation_m3"]


def test_interventions_improve_or_preserve_outcome_and_capacity_cannot_harm() -> None:
    baseline = client.post("/mitigation/compare", json=payload()).json()
    upgraded_only = client.post("/mitigation/compare", json=payload(selected_interventions=["upgrade_drainage"])).json()
    improved = client.post("/mitigation/compare", json=payload(selected_interventions=["clean_drains", "deploy_pumps", "upgrade_drainage"])).json()
    assert upgraded_only["with_interventions"]["total_modeled_accumulation_m3"] <= upgraded_only["baseline"]["total_modeled_accumulation_m3"]
    assert improved["with_interventions"]["total_modeled_accumulation_m3"] <= improved["baseline"]["total_modeled_accumulation_m3"]
    assert improved["percentage_modeled_reduction_vs_baseline"] >= 0
    base_by_id = {item["catchment_id"]: item for item in baseline["baseline"]["per_catchment"]}
    upgrade_by_id = {item["catchment_id"]: item for item in improved["with_interventions"]["per_catchment"]}
    for catchment_id, base in base_by_id.items():
        assert upgrade_by_id[catchment_id]["effective_drainage_capacity_m3_per_hour"] >= base["effective_drainage_capacity_m3_per_hour"]
        assert upgrade_by_id[catchment_id]["modeled_accumulated_water_m3"] <= base["modeled_accumulated_water_m3"]


def test_each_individual_intervention_measurably_improves_a_non_zero_rainfall_run() -> None:
    for intervention in ["clean_drains", "deploy_pumps", "upgrade_drainage"]:
        comparison = client.post("/mitigation/compare", json=payload(selected_interventions=[intervention])).json()
        assert comparison["with_interventions"]["total_modeled_accumulation_m3"] < comparison["baseline"]["total_modeled_accumulation_m3"]
        assert comparison["percentage_modeled_reduction_vs_baseline"] > 0


def test_mass_balance_and_non_negative_storage() -> None:
    result = client.post("/mitigation/simulate", json=payload()).json()
    for item in result["per_catchment"]:
        assert item["stored_within_assumed_capacity_m3"] >= 0
        assert item["modeled_uncontained_excess_m3"] >= 0
        assert item["modeled_runoff_volume_m3"] == round(
            item["modeled_drained_volume_m3"] + item["stored_within_assumed_capacity_m3"] + item["modeled_uncontained_excess_m3"], 3
        )


def test_api_validation_and_comparison_result_contract() -> None:
    invalid = client.post("/mitigation/simulate", json=payload(rainfall_duration_hours=0))
    assert invalid.status_code == 422
    comparison = client.post("/mitigation/compare", json=payload(selected_interventions=["clean_drains"])).json()
    assert comparison["provenance"] == "synthetic"
    assert "baseline" in comparison and "with_interventions" in comparison
    assert len(comparison["baseline"]["per_catchment"]) == 10
    assert "demonstration assumptions" in comparison["disclaimer"]
