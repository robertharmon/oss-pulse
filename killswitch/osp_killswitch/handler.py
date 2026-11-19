"""Budget notification → unlink billing, when spend is over the cap.

Reads:  one Cloud Billing budget notification (Pub/Sub message data: base64
        JSON with `costAmount` and `budgetAmount`), and the project's
        current billing state from the Cloud Billing API.
Writes: in `live` mode, removes the project's billing account
        (`billing_account_name = ""`), which stops every paid service in
        the project. In `simulate` mode (the default), only logs what it
        would do.

Fails fast (DECISIONS §6): a malformed message, a missing setting or an
API error raises, so Pub/Sub redelivers the message and the failure is
logged as an ERROR, which alerts.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class Mode(Enum):
    SIMULATE = "simulate"
    LIVE = "live"


class Action(Enum):
    NONE = "none"  # spend within the budget
    SIMULATED = "simulated"  # over budget, simulate mode: logged only
    ALREADY_DISABLED = "already_disabled"  # over budget, billing already off
    DISABLED = "disabled"  # over budget, billing unlinked now


@dataclass(frozen=True)
class BudgetNotification:
    cost_amount: float
    budget_amount: float
    currency: str
    budget_name: str


class BillingClient(Protocol):
    """The two Cloud Billing API calls the kill switch makes."""

    def billing_enabled(self, project_id: str) -> bool: ...

    def unlink_billing(self, project_id: str) -> None: ...


def parse_notification(data: bytes) -> BudgetNotification:
    """Decode a budget notification's message data (base64-encoded JSON)."""
    raise NotImplementedError


def parse_mode(value: str | None) -> Mode:
    """The kill switch's mode from its setting; unset means simulate."""
    raise NotImplementedError


def decide_and_act(
    notification: BudgetNotification,
    project_id: str,
    mode: Mode,
    client: BillingClient,
) -> Action:
    """Unlink billing (or pretend to) when spend is over the budget."""
    raise NotImplementedError
