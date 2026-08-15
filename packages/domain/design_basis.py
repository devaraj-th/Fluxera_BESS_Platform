from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DesignBasis:
    rated_power_mw: float
    nominal_energy_mwh: float
    required_usable_energy_mwh: float
    duration_hours: float
    project_life_years: int
    availability_target_percent: float
    round_trip_efficiency_target_percent: float
    cycles_per_day: float
    use_case: str
    ac_dc_boundary: str
    response_time_seconds: float | None = None
    capacity_retention_final_year: int | None = None

    def validate(self) -> None:
        if min(self.rated_power_mw, self.nominal_energy_mwh, self.duration_hours) <= 0:
            raise ValueError("rated power, nominal energy, and duration must be positive")
        if self.project_life_years <= 0:
            raise ValueError("project life must be positive")
        if self.required_usable_energy_mwh > self.nominal_energy_mwh:
            raise ValueError(
                "usable energy cannot exceed nominal energy without an explicit exception"
            )
        for label, value in {
            "availability target": self.availability_target_percent,
            "round-trip efficiency target": self.round_trip_efficiency_target_percent,
        }.items():
            if not 0 <= value <= 100:
                raise ValueError(f"{label} must be between 0 and 100")
        if self.cycles_per_day < 0:
            raise ValueError("cycles per day cannot be negative")
        if (
            self.capacity_retention_final_year is not None
            and self.capacity_retention_final_year > self.project_life_years
        ):
            raise ValueError("capacity-retention year cannot exceed project life")
        expected_duration = self.nominal_energy_mwh / self.rated_power_mw
        if abs(expected_duration - self.duration_hours) > 0.05:
            raise ValueError("duration must agree with nominal energy divided by rated power")
        if "frequency_regulation" in self.use_case.lower() and not self.response_time_seconds:
            raise ValueError("frequency-regulation use cases require a response-time basis")
        if not self.ac_dc_boundary.strip():
            raise ValueError("AC/DC boundary is required")
