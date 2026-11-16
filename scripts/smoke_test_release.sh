#!/usr/bin/env bash
set -Eeuo pipefail

# Public release smoke test. This script is read-only: it does not create users,
# bookings, parcels, or other application data.
: "${APP_BASE_URL:?Set APP_BASE_URL to the public HTTPS application URL}"
command -v curl >/dev/null 2>&1 || { echo "curl is required." >&2; exit 1; }

BASE_URL="${APP_BASE_URL%/}"
if [[ "$BASE_URL" != https://* ]]; then
  echo "APP_BASE_URL must use HTTPS. Do not run this against a public HTTP endpoint." >&2
  exit 1
fi

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/timedrop-smoke.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

request() {
  local path="$1"
  local expected="$2"
  local label="$3"
  local status
  status="$(curl --silent --show-error --location --max-time "${CURL_MAX_TIME_SECONDS:-15}" \
    --output "$TMP_DIR/body" --dump-header "$TMP_DIR/headers" \
    --write-out '%{http_code}' "$BASE_URL$path")"
  if [[ "$status" != "$expected" ]]; then
    echo "FAIL: $label returned HTTP $status (expected $expected)." >&2
    sed -n '1,20p' "$TMP_DIR/body" >&2
    exit 1
  fi
  echo "PASS: $label (HTTP $status)"
}

header_present() {
  local name="$1"
  if ! grep -Eiq "^$name:[[:space:]]*[^[:space:]]" "$TMP_DIR/headers"; then
    echo "FAIL: required response header $name is missing." >&2
    exit 1
  fi
  echo "PASS: response header $name"
}

echo "Checking public frontend..."
request "/" "200" "Frontend"
header_present "content-security-policy"
header_present "strict-transport-security"
header_present "x-content-type-options"
header_present "referrer-policy"
header_present "x-frame-options"
header_present "permissions-policy"

echo "Checking API readiness through the public reverse proxy..."
request "/health/ready" "200" "API readiness"
if ! grep -Eq '"status"[[:space:]]*:[[:space:]]*"ready"' "$TMP_DIR/body"; then
  echo "FAIL: readiness response did not report status=ready." >&2
  exit 1
fi
if ! grep -Eq '"database"[[:space:]]*:[[:space:]]*"ok"' "$TMP_DIR/body"; then
  echo "FAIL: readiness response did not report database=ok." >&2
  exit 1
fi
echo "PASS: API and database readiness payload"

echo "Checking that the operations health endpoint rejects anonymous access..."
status="$(curl --silent --show-error --location --max-time "${CURL_MAX_TIME_SECONDS:-15}" \
  --output "$TMP_DIR/body" --write-out '%{http_code}' \
  "$BASE_URL/api/v1/operations/system-health")"
if [[ "$status" != "401" && "$status" != "403" ]]; then
  echo "FAIL: anonymous operations health request returned HTTP $status (expected 401 or 403)." >&2
  exit 1
fi
echo "PASS: operations health endpoint requires authentication (HTTP $status)"

echo "TimeDrop release smoke checks passed."
