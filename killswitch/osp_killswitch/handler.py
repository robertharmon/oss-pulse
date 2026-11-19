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

import base64
import binascii
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


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


def _amount(body: dict[str, Any], key: str) -> float:
    value = body.get(key)
    # bool is a subclass of int in Python; true/false isn't an amount.
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"budget notification: {key} must be a number, got {value!r}")
    return float(value)


def parse_notification(data: bytes) -> BudgetNotification:
    """Decode a budget notification's message data (base64-encoded JSON)."""
    try:
        body = json.loads(base64.b64decode(data, validate=True))
    except (binascii.Error, ValueError) as error:
        raise ValueError(f"budget notification: not base64 JSON ({error})") from error
    if not isinstance(body, dict):
        raise ValueError("budget notification: expected a JSON object")
    # Currency and name don't affect the decision; a missing one is logged
    # as "" rather than failing (which would make Pub/Sub redeliver forever).
    return BudgetNotification(
        cost_amount=_amount(body, "costAmount"),
        budget_amount=_amount(body, "budgetAmount"),
        currency=str(body.get("currencyCode", "")),
        budget_name=str(body.get("budgetDisplayName", "")),
    )


def parse_mode(value: str | None) -> Mode:
    """The kill switch's mode from its setting; unset means simulate."""
    if not value:
        return Mode.SIMULATE
    try:
        return Mode(value)
    except ValueError as error:
        raise ValueError(
            f"KILLSWITCH_MODE must be 'simulate' or 'live', got {value!r}"
        ) from error


def decide_and_act(
    notification: BudgetNotification,
    project_id: str,
    mode: Mode,
    client: BillingClient,
) -> Action:
    """Unlink billing (or pretend to) when spend is over the budget."""
    # Google's reference implementation: at or under budget, do nothing.
    if notification.cost_amount <= notification.budget_amount:
        return Action.NONE
    if not client.billing_enabled(project_id):
        return Action.ALREADY_DISABLED
    if mode is Mode.SIMULATE:
        return Action.SIMULATED
    client.unlink_billing(project_id)
    return Action.DISABLED
