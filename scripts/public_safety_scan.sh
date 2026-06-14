#!/usr/bin/env bash
set -euo pipefail

patterns=(
  "Tredence"
  "OneDrive"
  "C:\\\\Users"
  "Classification"
  "Leadership Only"
  "ANTHROPIC_API_KEY"
  "DATABRICKS_TOKEN"
  "SNOWFLAKE_PRIVATE"
  "LANGCHAIN_API_KEY"
  "MEM0_API_KEY"
  "sk-[A-Za-z0-9]"
  "dapi[A-Za-z0-9]"
)

files=$(git ls-files \
  ':!:frontend/package-lock.json' \
  ':!:frontend/node_modules/**' \
  ':!:frontend/dist/**' \
  ':!:backend/phantom.db' \
  ':!:backend/**/*.egg-info/**' \
  ':!:backend/**/__pycache__/**')

if [[ -z "${files}" ]]; then
  echo "No tracked files to scan."
  exit 0
fi

for pattern in "${patterns[@]}"; do
  if grep -E -n -I "${pattern}" ${files}; then
    echo "Public-safety scan failed on pattern: ${pattern}" >&2
    exit 1
  fi
done

echo "Public-safety scan passed."

