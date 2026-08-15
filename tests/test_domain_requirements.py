from uuid import uuid4

import pytest
from packages.domain.requirements import (
    EvidenceReference,
    RequirementKey,
    RequirementState,
    can_transition,
    require_verifiable_evidence,
)


def test_requirement_key_has_stable_human_readable_shape() -> None:
    assert RequirementKey("CEB160-PER-0042").value == "CEB160-PER-0042"

    with pytest.raises(ValueError):
        RequirementKey("not-a-key")


def test_verified_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence"):
        require_verifiable_evidence(RequirementState.VERIFIED, ())

    require_verifiable_evidence(
        RequirementState.VERIFIED,
        (EvidenceReference(uuid4(), "The supplier shall provide a schedule."),),
    )


def test_final_requirement_cannot_be_reopened() -> None:
    assert can_transition(RequirementState.PROPOSED, RequirementState.VERIFIED)
    assert not can_transition(RequirementState.VERIFIED, RequirementState.PROPOSED)
    assert can_transition(RequirementState.VERIFIED, RequirementState.SUPERSEDED)
