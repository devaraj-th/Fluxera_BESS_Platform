from dataclasses import dataclass
from enum import StrEnum


class ModuleMode(StrEnum):
    PRE_BID = "pre_bid"
    BID_INTELLIGENCE = "bid_intelligence"


class ProcurementArchetype(StrEnum):
    EPC = "epc"
    EPC_PLUS_OM = "epc_plus_om"
    BOO_BESPA = "boo_bespa"
    RTE_ADJUSTED_BOO = "rte_adjusted_boo"
    SOLAR_PLUS_BESS_EPC = "solar_plus_bess_epc"
    RE_SUPPLY_WITH_ESS = "re_supply_with_ess"
    CUSTOM = "custom"


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
    location: str | None = None
    jurisdiction: str | None = None
    interconnection_voltage_kv: float | None = None
    delivery_point: str | None = None
    cod: str | None = None
    currency: str | None = None
    timezone: str | None = None
    contract_term_years: int | None = None
    total_contractual_cycles: float | None = None
    annual_throughput_mwh: float | None = None
    maximum_cycles_per_day: float | None = None
    partial_cycle_treatment: str | None = None
    soc_operating_window: str | None = None
    charge_duration_hours: float | None = None
    discharge_duration_hours: float | None = None
    cooling_recovery_time_hours: float | None = None
    operational_window: str | None = None
    charging_energy_provider: str | None = None
    dispatch_notice: str | None = None
    rte_measurement_point: str | None = None
    rte_frequency: str | None = None
    auxiliary_consumption_treatment: str | None = None
    availability_period: str | None = None
    planned_outage_exclusion: str | None = None
    grid_outage_exclusion: str | None = None
    capacity_test_method: str | None = None
    capacity_retention_trajectory: dict[int, float] | None = None
    end_of_life_retention_percent: float | None = None
    oversizing_allowed: bool | None = None
    augmentation_allowed: bool | None = None
    augmentation_mandatory: bool | None = None
    augmentation_payer: str | None = None
    replacement_allowed: bool | None = None
    augmentation_outage_treatment: str | None = None
    required_design_cycle_life: float | None = None
    warranty_cycle_requirement: float | None = None
    financial_evaluation_method: str | None = None
    reverse_auction_used: bool | None = None
    reverse_auction_parameter: str | None = None
    discount_rate_percent: float | None = None
    om_term_years: int | None = None
    om_escalation_percent: float | None = None
    rte_price_adjustment: str | None = None
    ld_structure: str | None = None
    aggregate_ld_cap_percent: float | None = None
    emd_amount: float | None = None
    pbg_amount: float | None = None
    vgf_treatment: str | None = None

    def validate(self) -> None:
        if min(self.rated_power_mw, self.nominal_energy_mwh, self.duration_hours) <= 0:
            raise ValueError("rated power, nominal energy, and duration must be positive")
        if self.project_life_years <= 0:
            raise ValueError("project life must be positive")
        if self.interconnection_voltage_kv is not None and self.interconnection_voltage_kv <= 0:
            raise ValueError("interconnection voltage must be positive")
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
        if self.contract_term_years is not None and self.contract_term_years <= 0:
            raise ValueError("contract term must be positive")
        if self.total_contractual_cycles is not None:
            if self.total_contractual_cycles < 0:
                raise ValueError("total contractual cycles cannot be negative")
            if self.contract_term_years is not None:
                expected_cycles = self.cycles_per_day * 365 * self.contract_term_years
                if abs(self.total_contractual_cycles - expected_cycles) > 1:
                    raise ValueError(
                        "total contractual cycles must agree with cycles per day and term"
                    )
        if (
            self.maximum_cycles_per_day is not None
            and self.maximum_cycles_per_day < self.cycles_per_day
        ):
            raise ValueError("maximum cycles per day cannot be below nominal cycles per day")
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
        if self.capacity_retention_trajectory is not None:
            for year, retention in self.capacity_retention_trajectory.items():
                if year <= 0 or year > self.project_life_years:
                    raise ValueError(
                        "capacity-retention trajectory year must be within project life"
                    )
                if not 0 <= retention <= 100:
                    raise ValueError(
                        "capacity-retention trajectory values must be between 0 and 100"
                    )
        if (
            self.end_of_life_retention_percent is not None
            and not 0 <= self.end_of_life_retention_percent <= 100
        ):
            raise ValueError("end-of-life retention must be between 0 and 100")
