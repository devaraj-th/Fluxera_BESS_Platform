import pytest
from packages.domain.design_basis import DesignBasis


def basis(**overrides: object) -> DesignBasis:
    values: dict[str, object] = {
        "rated_power_mw": 100.0,
        "nominal_energy_mwh": 400.0,
        "required_usable_energy_mwh": 380.0,
        "duration_hours": 4.0,
        "project_life_years": 20,
        "availability_target_percent": 98.0,
        "round_trip_efficiency_target_percent": 88.0,
        "cycles_per_day": 1.0,
        "use_case": "capacity",
        "ac_dc_boundary": "AC point of interconnection",
    }
    values.update(overrides)
    return DesignBasis(**values)  # type: ignore[arg-type]


def test_valid_design_basis_passes_deterministic_validation() -> None:
    basis().validate()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"duration_hours": 3.0}, "duration"),
        ({"availability_target_percent": 101.0}, "between"),
        ({"required_usable_energy_mwh": 401.0}, "usable energy"),
        ({"use_case": "frequency_regulation"}, "response-time"),
    ],
)
def test_invalid_design_basis_is_rejected(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        basis(**overrides).validate()
