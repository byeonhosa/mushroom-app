from types import SimpleNamespace

import pytest

from app import crud


def _existing_in_house():
    return SimpleNamespace(
        spawn_type="IN_HOUSE_GRAIN",
        grain_type_id=1,
        grain_kg=6.5,
        vermiculite_kg=1.2,
        water_kg=5.1,
    )


def test_purchased_spawn_normalization_clears_in_house_fields():
    data = {
        "spawn_type": "PURCHASED_BLOCK",
        "grain_type_id": 1,
        "grain_kg": 5.0,
        "vermiculite_kg": 1.0,
        "water_kg": 4.0,
        "supplement_kg": 0.3,
        "sterilization_run_id": 9,
    }
    normalized = crud._normalize_spawn_batch_data(data)
    assert normalized["grain_type_id"] is None
    assert normalized["grain_kg"] is None
    assert normalized["vermiculite_kg"] is None
    assert normalized["water_kg"] is None
    assert normalized["supplement_kg"] is None
    assert normalized["sterilization_run_id"] is None


def test_in_house_spawn_requires_recipe_fields():
    with pytest.raises(ValueError, match="IN_HOUSE_GRAIN requires"):
        crud._normalize_spawn_batch_data({"spawn_type": "IN_HOUSE_GRAIN", "grain_kg": 6.0})


def test_in_house_update_can_reuse_existing_required_fields():
    normalized = crud._normalize_spawn_batch_data(
        {"spawn_type": "IN_HOUSE_GRAIN", "supplement_kg": 0.2},
        existing=_existing_in_house(),
    )
    assert normalized["supplement_kg"] == 0.2


def test_compute_spawn_recipe_metrics_sets_expected_values():
    spawn = SimpleNamespace(grain_kg=6.5, vermiculite_kg=1.5, water_kg=5.0, supplement_kg=0.5)
    enriched = crud._compute_spawn_recipe_metrics(spawn)
    assert enriched.hydration_ratio == pytest.approx(5.0 / 8.5, rel=1e-9)
    assert enriched.expected_added_water_wb_pct == pytest.approx((5.0 / 13.5) * 100.0, rel=1e-9)


def test_compute_spawn_recipe_metrics_handles_missing_inputs():
    spawn = SimpleNamespace(grain_kg=None, vermiculite_kg=1.0, water_kg=2.0, supplement_kg=0.0)
    enriched = crud._compute_spawn_recipe_metrics(spawn)
    assert enriched.hydration_ratio is None
    assert enriched.expected_added_water_wb_pct is None


def test_compute_spawn_recipe_metrics_zero_dry_mass_gives_no_hydration_and_100_wb():
    spawn = SimpleNamespace(grain_kg=0.0, vermiculite_kg=0.0, water_kg=3.0, supplement_kg=0.0)
    enriched = crud._compute_spawn_recipe_metrics(spawn)
    assert enriched.hydration_ratio is None
    assert enriched.expected_added_water_wb_pct == pytest.approx(100.0, rel=1e-9)
