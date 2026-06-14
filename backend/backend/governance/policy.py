from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyDecision:
    read_only: bool
    requires_approval: bool


def phase_one_policy() -> PolicyDecision:
    return PolicyDecision(read_only=True, requires_approval=False)

