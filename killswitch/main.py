"""Cloud Run functions entry point for the kill switch (deploy: killswitch/deploy.sh).

Wires the Pub/Sub CloudEvent and the real Cloud Billing API client to
`osp_killswitch.handler`. Settings come from environment variables set at
deploy time: KILLSWITCH_PROJECT_ID (required) and KILLSWITCH_MODE
(`simulate` or `live`; unset means simulate).
"""

import json
import os
from typing import Any

import functions_framework
from google.cloud import billing_v1

from osp_killswitch.handler import decide_and_act, parse_mode, parse_notification


class _CloudBillingClient:
    """Adapter from the Cloud Billing API to the handler's BillingClient."""

    def __init__(self, client: billing_v1.CloudBillingClient) -> None:
        self._client = client

    def billing_enabled(self, project_id: str) -> bool:
        info = self._client.get_project_billing_info(name=f"projects/{project_id}")
        return bool(info.billing_enabled)

    def unlink_billing(self, project_id: str) -> None:
        self._client.update_project_billing_info(
            name=f"projects/{project_id}",
            project_billing_info=billing_v1.ProjectBillingInfo(billing_account_name=""),
        )


@functions_framework.cloud_event
def stop_billing(cloud_event: Any) -> None:
    project_id = os.environ["KILLSWITCH_PROJECT_ID"]
    mode = parse_mode(os.environ.get("KILLSWITCH_MODE"))
    notification = parse_notification(cloud_event.data["message"]["data"].encode())
    with billing_v1.CloudBillingClient() as raw_client:
        action = decide_and_act(
            notification, project_id, mode, _CloudBillingClient(raw_client)
        )
    # One structured line per notification; Cloud Logging parses JSON stdout.
    print(
        json.dumps(
            {
                "severity": "WARNING" if action.value != "none" else "INFO",
                "message": f"kill switch: {action.value}",
                "project_id": project_id,
                "mode": mode.value,
                "cost_amount": notification.cost_amount,
                "budget_amount": notification.budget_amount,
                "currency": notification.currency,
                "budget": notification.budget_name,
            }
        )
    )
