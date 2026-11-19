"""Red tests for the billing kill switch (backlog C9).

Spec: DECISIONS §1 (unlink billing when spend crosses the budget; dev $2,
prod $5), §6 (fail fast); ADR 0002 §1 (kill switch row); author_setup §2.3
(starts in simulate mode); Google's programmatic budget notification format
(base64 JSON; no action while costAmount <= budgetAmount).
"""

import base64
import json
from typing import Any

import pytest

from osp_killswitch.handler import (
    Action,
    BudgetNotification,
    Mode,
    decide_and_act,
    parse_mode,
    parse_notification,
)

PROJECT = "oss-pulse-dev-2026"


def encode(payload: Any) -> bytes:
    """Pub/Sub message data as a budget sends it: base64 of a JSON document."""
    return base64.b64encode(json.dumps(payload).encode("utf-8"))


def google_notification(**overrides: Any) -> dict[str, Any]:
    """A notification shaped like Google's documented example."""
    payload: dict[str, Any] = {
        "budgetDisplayName": "oss-pulse-dev kill switch",
        "alertThresholdExceeded": 1.0,
        "costAmount": 2.47,
        "costIntervalStart": "2026-11-01T08:00:00Z",
        "budgetAmount": 2.0,
        "budgetAmountType": "SPECIFIED_AMOUNT",
        "currencyCode": "USD",
    }
    payload.update(overrides)
    return payload


class BillingApiError(Exception):
    """Stands in for an error from the Cloud Billing API."""


class FakeBillingClient:
    """The Cloud Billing API, in memory: one project's billing link."""

    def __init__(
        self,
        enabled: bool = True,
        fail_on: str | None = None,
    ) -> None:
        self.enabled = {PROJECT: enabled}
        self.unlinked: list[str] = []
        self.fail_on = fail_on

    def billing_enabled(self, project_id: str) -> bool:
        if self.fail_on == "billing_enabled":
            raise BillingApiError("billing_enabled failed")
        return self.enabled[project_id]  # KeyError on the wrong project

    def unlink_billing(self, project_id: str) -> None:
        if self.fail_on == "unlink_billing":
            raise BillingApiError("unlink_billing failed")
        self.enabled[project_id] = False  # KeyError on the wrong project
        self.unlinked.append(project_id)


def notification(cost: float, budget: float) -> BudgetNotification:
    return BudgetNotification(
        cost_amount=cost,
        budget_amount=budget,
        currency="USD",
        budget_name="oss-pulse-dev kill switch",
    )


# --- parse_notification ---------------------------------------------------


def test_parses_google_notification() -> None:
    assert parse_notification(encode(google_notification())) == BudgetNotification(
        cost_amount=2.47,
        budget_amount=2.0,
        currency="USD",
        budget_name="oss-pulse-dev kill switch",
    )


def test_parses_notification_with_no_threshold_crossed() -> None:
    # Google sends routine notifications without alertThresholdExceeded;
    # they are still valid messages. Integer amounts are valid JSON numbers.
    payload = google_notification(costAmount=0, budgetAmount=5)
    del payload["alertThresholdExceeded"]
    parsed = parse_notification(encode(payload))
    assert parsed.cost_amount == 0.0
    assert parsed.budget_amount == 5.0


def _without(key: str) -> dict[str, Any]:
    payload = google_notification()
    del payload[key]
    return payload


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(b"%%% not base64 %%%", id="not-base64"),
        pytest.param(base64.b64encode(b"cost: 2.47"), id="not-json"),
        pytest.param(encode([2.47, 2.0]), id="json-not-an-object"),
        pytest.param(encode(_without("costAmount")), id="missing-costAmount"),
        pytest.param(encode(_without("budgetAmount")), id="missing-budgetAmount"),
        pytest.param(
            encode(google_notification(costAmount="lots")), id="text-costAmount"
        ),
        pytest.param(
            encode(google_notification(budgetAmount=None)), id="null-budgetAmount"
        ),
    ],
)
def test_malformed_notification_raises(data: bytes) -> None:
    with pytest.raises(ValueError):
        parse_notification(data)


# --- parse_mode -----------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, Mode.SIMULATE),  # unset: author_setup §2.3, starts in simulate
        ("", Mode.SIMULATE),
        ("simulate", Mode.SIMULATE),
        ("live", Mode.LIVE),
    ],
)
def test_parse_mode(value: str | None, expected: Mode) -> None:
    assert parse_mode(value) == expected


@pytest.mark.parametrize(
    "value", ["LIVE", "Live", " live", "true", "on", "simulated", "disabled"]
)
def test_unknown_mode_raises_rather_than_guessing(value: str) -> None:
    with pytest.raises(ValueError):
        parse_mode(value)


# --- decide_and_act -------------------------------------------------------


@pytest.mark.parametrize("mode", [Mode.SIMULATE, Mode.LIVE])
@pytest.mark.parametrize(
    ("cost", "budget"),
    [
        (1.50, 2.0),  # 1.50 < 2.00: under the dev cap
        (2.0, 2.0),  # 2.00 == 2.00: at the cap is not over it (Google's <=)
        (3.0, 5.0),  # 3.00 < 5.00: over $2 but under this (prod) budget
    ],
)
def test_within_budget_takes_no_action(cost: float, budget: float, mode: Mode) -> None:
    client = FakeBillingClient()
    assert decide_and_act(notification(cost, budget), PROJECT, mode, client) is (
        Action.NONE
    )
    assert client.unlinked == []
    assert client.enabled[PROJECT] is True


@pytest.mark.parametrize(
    ("cost", "budget"),
    [
        (2.01, 2.0),  # 2.01 > 2.00: one cent over the dev cap
        (5.30, 5.0),  # 5.30 > 5.00: over the prod cap
    ],
)
def test_over_budget_live_unlinks_billing_once(cost: float, budget: float) -> None:
    client = FakeBillingClient(enabled=True)
    action = decide_and_act(notification(cost, budget), PROJECT, Mode.LIVE, client)
    assert action is Action.DISABLED
    assert client.unlinked == [PROJECT]


def test_over_budget_simulate_only_logs() -> None:
    client = FakeBillingClient(enabled=True)
    # 2.47 > 2.00: over, but simulate mode must not touch billing.
    action = decide_and_act(notification(2.47, 2.0), PROJECT, Mode.SIMULATE, client)
    assert action is Action.SIMULATED
    assert client.unlinked == []
    assert client.enabled[PROJECT] is True


def test_over_budget_live_with_billing_already_off() -> None:
    # RUNBOOK §3.5: month-to-date spend stays over the cap, so notifications
    # keep arriving after the switch has fired.
    client = FakeBillingClient(enabled=False)
    action = decide_and_act(notification(2.47, 2.0), PROJECT, Mode.LIVE, client)
    assert action is Action.ALREADY_DISABLED
    assert client.unlinked == []


@pytest.mark.parametrize("failing_call", ["billing_enabled", "unlink_billing"])
def test_billing_api_error_propagates(failing_call: str) -> None:
    # Fail fast (DECISIONS §6): the error must reach Pub/Sub so it redelivers.
    client = FakeBillingClient(enabled=True, fail_on=failing_call)
    with pytest.raises(BillingApiError):
        decide_and_act(notification(2.47, 2.0), PROJECT, Mode.LIVE, client)
