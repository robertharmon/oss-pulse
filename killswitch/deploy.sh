#!/usr/bin/env bash
# Deploy, drill, or switch the billing kill switch for one project
# (backlog C9, docs/author_setup.md §2.3).
#
# Run by the AUTHOR in Cloud Shell, from the repo's killswitch/ folder. It
# needs billing and IAM permissions that agents never hold (ADR 0002 §2).
#
# Usage:
#   ./deploy.sh deploy <project-id> <dev|prod> [simulate|live]   # default: simulate
#   ./deploy.sh drill  <project-id> <dev|prod>                   # publish a fake over-budget message
#
# Prerequisites (author_setup §2.1): the Pub/Sub topic osp-budget-<env>
# exists and the project's budget is connected to it.
set -euo pipefail

usage() { sed -n '9,11p' "$0" >&2; exit 2; }
[[ $# -ge 3 ]] || usage
command=$1 project=$2 env=$3 mode=${4:-simulate}
[[ $env == dev || $env == prod ]] || usage
[[ $mode == simulate || $mode == live ]] || usage

region=us-central1
name=osp-killswitch-$env
topic=osp-budget-$env
sa=$name@$project.iam.gserviceaccount.com

deploy() {
  gcloud services enable --project="$project" \
    cloudfunctions.googleapis.com run.googleapis.com cloudbuild.googleapis.com \
    artifactregistry.googleapis.com eventarc.googleapis.com pubsub.googleapis.com \
    cloudbilling.googleapis.com

  if ! gcloud iam service-accounts describe "$sa" --project="$project" >/dev/null 2>&1; then
    gcloud iam service-accounts create "$name" --project="$project" \
      --display-name="oss-pulse billing kill switch ($env)"
  fi

  # Grants, exactly as docs/access_matrix.md §4 lists them.
  gcloud projects add-iam-policy-binding "$project" --condition=None \
    --member="serviceAccount:$sa" --role=roles/billing.projectManager
  gcloud projects add-iam-policy-binding "$project" --condition=None \
    --member="serviceAccount:$sa" --role=roles/browser
  billing_account=$(gcloud billing projects describe "$project" \
    --format='value(billingAccountName)')
  gcloud billing accounts add-iam-policy-binding "${billing_account#billingAccounts/}" \
    --member="serviceAccount:$sa" --role=roles/billing.viewer

  gcloud functions deploy "$name" --gen2 --project="$project" --region="$region" \
    --runtime=python311 --source=. --entry-point=stop_billing \
    --trigger-topic="$topic" --service-account="$sa" --trigger-service-account="$sa" \
    --no-allow-unauthenticated --max-instances=1 \
    --set-env-vars="KILLSWITCH_PROJECT_ID=$project,KILLSWITCH_MODE=$mode"

  gcloud run services add-iam-policy-binding "$name" --project="$project" \
    --region="$region" --member="serviceAccount:$sa" --role=roles/run.invoker

  echo "Deployed $name in $mode mode."
}

drill() {
  # A message shaped like a real budget notification, far over the budget.
  gcloud pubsub topics publish "$topic" --project="$project" --message='{
    "budgetDisplayName": "kill-switch drill", "alertThresholdExceeded": 1.0,
    "costAmount": 99.0, "costIntervalStart": "2026-01-01T00:00:00Z",
    "budgetAmount": 2.0, "budgetAmountType": "SPECIFIED_AMOUNT", "currencyCode": "USD"}'
  echo "Published. In a minute, check the function's logs for 'kill switch: simulated'"
  echo "(simulate mode) or 'kill switch: disabled' (live mode):"
  echo "  gcloud functions logs read $name --gen2 --project=$project --region=$region --limit=20"
}

case $command in
  deploy) deploy ;;
  drill) drill ;;
  *) usage ;;
esac
