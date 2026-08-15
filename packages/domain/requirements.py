import re
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class RequirementState(StrEnum):
    PROPOSED = "proposed"
    VERIFIED = "verified"
    REJECTED = "rejected"
    CLARIFICATION_REQUIRED = "clarification_required"
    SUPERSEDED = "superseded"


class TaxonomyCode(StrEnum):
    ADM = "ADM"
    ELG = "ELG"
    PRJ = "PRJ"
    TEC = "TEC"
    GRD = "GRD"
    SAF = "SAF"
    TST = "TST"
    PER = "PER"
    COM = "COM"
    CON = "CON"
    SCH = "SCH"
    OAM = "OAM"
    WAR = "WAR"
    LIF = "LIF"
    DOC = "DOC"


_KEY_PATTERN = re.compile(r"^[A-Z]{3}\d{3}-[A-Z]{3}-\d{4}$")


@dataclass(frozen=True, slots=True)
class RequirementKey:
    value: str

    def __post_init__(self) -> None:
        if not _KEY_PATTERN.fullmatch(self.value):
            raise ValueError("requirement key must match XXX000-XXX-0000")


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    evidence_span_id: UUID
    exact_text: str

    def __post_init__(self) -> None:
        if not self.exact_text.strip():
            raise ValueError("verified evidence must preserve exact text")


def can_transition(current: RequirementState, target: RequirementState) -> bool:
    if current in {RequirementState.VERIFIED, RequirementState.SUPERSEDED}:
        return target == RequirementState.SUPERSEDED
    return target in {
        RequirementState.VERIFIED,
        RequirementState.REJECTED,
        RequirementState.CLARIFICATION_REQUIRED,
    }


def require_verifiable_evidence(
    state: RequirementState, evidence: tuple[EvidenceReference, ...]
) -> None:
    if state == RequirementState.VERIFIED and not evidence:
        raise ValueError("a verified requirement needs at least one evidence span")
