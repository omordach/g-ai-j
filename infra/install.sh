#!/usr/bin/env bash
set -euo pipefail

# --- Quick knobs (can be overridden by environment) ---
PROJECT_ID="${PROJECT_ID:-}"            # If empty, taken from .env (GCP_PROJECT_ID or PROJECT_ID)
REGION="${REGION:-europe-central2}"
SERVICE_NAME="${SERVICE_NAME:-g-ai-j}"
ARTIFACT_REPO="${ARTIFACT_REPO:-g-ai-j-repo}"
RUNTIME_SA_NAME="${RUNTIME_SA_NAME:-g-ai-j-runtime}"
DEPLOY_SA_NAME="${DEPLOY_SA_NAME:-g-ai-j-deployer}"
SOURCE_DIR="${SOURCE_DIR:-.}"           # app folder with Dockerfile
ENV_FILE="${ENV_FILE:-.env}"            # local .env path

# --- Pre-flight checks ---
if ! command -v gcloud >/dev/null; then
  echo "gcloud not found. Install Google Cloud SDK and authenticate."
  exit 1
fi
if ! command -v ansible-playbook >/dev/null; then
  echo "Ansible not found. Install Ansible 2.15+ (pipx install ansible-core)."
  exit 1
fi

# --- Run Ansible playbook locally ---
ansible-playbook -i "localhost," -c local infra/install.yml \
  -e project_id="${PROJECT_ID}" \
  -e region="${REGION}" \
  -e service_name="${SERVICE_NAME}" \
  -e artifact_repo="${ARTIFACT_REPO}" \
  -e runtime_sa_name="${RUNTIME_SA_NAME}" \
  -e deploy_sa_name="${DEPLOY_SA_NAME}" \
  -e source_dir="${SOURCE_DIR}" \
  -e env_file_path="${ENV_FILE}"

