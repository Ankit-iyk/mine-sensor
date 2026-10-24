from ai_engine.evaluation import run_all


def test_training_partition_includes_only_event_free_wide_conditions(monkeypatch):
    calls = []

    def fake_generate(scenario, seed, noise_model):
        calls.append((scenario, seed, noise_model))
        return [{
            "scenario": scenario,
            "noise_model": noise_model,
            "seed": seed,
            "is_event": False,
        }]

    def fake_extract(readings):
        source = readings[0]
        return [
            {
                "scenario": source["scenario"],
                "noise_model": source["noise_model"],
                "seed": source["seed"],
                "is_event": False,
            }
            for _ in range(run_all._TRAIN_KEEP_EVERY)
        ]

    monkeypatch.setattr(run_all, "generate_episode", fake_generate)
    monkeypatch.setattr(run_all, "extract_backend_features", fake_extract)

    rows = run_all._training_features(seeds=1)

    assert len(calls) == 30 * 3
    assert { (scenario, noise) for scenario, _, noise in calls } == {
        ("normal", "simulator"),
        ("baseline_drift", "simulator"),
        ("normal", "distribution_shift"),
    }
    assert all(row["seed"] >= run_all._TRAIN_SEED_BASE for row in rows)
    assert all(not row["is_event"] for row in rows)
    assert {row["noise_model"] for row in rows} == {"simulator", "distribution_shift"}


def test_report_refresh_preserves_signed_forest_value_intervals():
    row = {
        "method": "forest_added_value",
        "f1_ci95_low": -0.03,
        "f1_ci95_high": -0.01,
    }

    run_all._bound_confidence_intervals(row)

    assert row["f1_ci95_low"] == -0.03
    assert row["f1_ci95_high"] == -0.01
