from packages.domain.completeness import evaluate_rule_ids


def test_long_life_project_requires_verified_performance_coverage() -> None:
    assert evaluate_rule_ids(20, "capacity", set()) == ("capacity_retention_schedule",)
    assert evaluate_rule_ids(20, "capacity", {"PER"}) == ()


def test_frequency_regulation_requires_response_time_coverage() -> None:
    findings = evaluate_rule_ids(5, "frequency_regulation", set())
    assert findings == ("frequency_response_time",)
