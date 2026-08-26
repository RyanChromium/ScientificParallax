from scientific_parallax.step0.benchmark import run_negative_control


def test_contradictory_control_loses_under_disagreement_selection() -> None:
    result = run_negative_control(1729)
    assert result["selection_strategy"] == "max_disagreement"
    assert result["first_query_below_prior"] == 1
    assert float(result["final_posterior"]) < float(result["initial_posterior"])
    assert float(result["true_final_posterior"]) > 0.99
