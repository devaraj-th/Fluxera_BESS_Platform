from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CompletenessRule:
    rule_id: str
    version: str
    taxonomy: str
    severity: str
    explanation: str
    suggested_action: str


RULES = (
    CompletenessRule(
        rule_id="capacity_retention_schedule",
        version="1.0",
        taxonomy="PER",
        severity="high",
        explanation=(
            "A project life of ten years or more requires a verified year-wise "
            "capacity-retention requirement."
        ),
        suggested_action=(
            "Add a measurable capacity-retention schedule with annual milestones and "
            "test conditions."
        ),
    ),
    CompletenessRule(
        rule_id="frequency_response_time",
        version="1.0",
        taxonomy="PER",
        severity="high",
        explanation="Frequency-regulation use requires a verified response-time requirement.",
        suggested_action=(
            "State a maximum response time, measurement boundary, and verification method."
        ),
    ),
)


def evaluate_rule_ids(
    project_life_years: int, use_case: str, verified_taxonomies: set[str]
) -> tuple[str, ...]:
    missing: list[str] = []
    if project_life_years >= 10 and "PER" not in verified_taxonomies:
        missing.append("capacity_retention_schedule")
    if "frequency_regulation" in use_case.lower() and "PER" not in verified_taxonomies:
        missing.append("frequency_response_time")
    return tuple(missing)
