#!/usr/bin/env bash
# Publish DT Orch images as public GHCR packages (shared release workflow step).
# Customers pull without a GitHub token; git source repos stay private.
set -euo pipefail

PACKAGE="${1:?Package name (e.g. dt-orch-api)}"
OWNER="${2:?GitHub owner/org}"

gh_cmd() {
  if command -v gh >/dev/null 2>&1; then
    gh "$@"
    return
  fi

  local candidate
  for candidate in \
    "${GH_BIN:-}" \
    "/c/Program Files/GitHub CLI/gh.exe" \
    "/mnt/c/Program Files/GitHub CLI/gh.exe" \
    "${PROGRAMFILES:-}/GitHub CLI/gh.exe" \
    "${ProgramFiles:-}/GitHub CLI/gh.exe"; do
    if [ -n "${candidate}" ] && [ -x "${candidate}" ]; then
      "${candidate}" "$@"
      return
    fi
  done

  echo "ERROR: GitHub CLI (gh) not found in PATH." >&2
  echo "Install gh or set GH_BIN to the gh executable path." >&2
  return 127
}

is_publicly_pullable() {
  local token response code
  response="$(curl -fsS "https://ghcr.io/token?service=ghcr.io&scope=repository:${OWNER}/${PACKAGE}:pull" 2>/dev/null || true)"
  token="$(printf '%s' "${response}" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')"
  [ -n "${token}" ] || return 1

  code="$(curl -fsS -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${token}" \
    -H "Accept: application/vnd.oci.image.index.v1+json" \
    "https://ghcr.io/v2/${OWNER}/${PACKAGE}/manifests/latest" 2>/dev/null || echo "000")"
  [ "${code}" = "200" ]
}

resolve_package_api() {
  local path
  # No leading slash: Git Bash on Windows rewrites /orgs/... to a filesystem path.
  for path in \
    "orgs/${OWNER}/packages/container/${PACKAGE}" \
    "users/${OWNER}/packages/container/${PACKAGE}" \
    "user/packages/container/${PACKAGE}"; do
    if gh_cmd api "${path}" &>/dev/null; then
      echo "${path}"
      return 0
    fi
  done
  return 1
}

if is_publicly_pullable; then
  echo "GHCR package ${OWNER}/${PACKAGE} is already public (verified via registry)."
  exit 0
fi

if API_PATH="$(resolve_package_api)"; then
  VISIBILITY="$(gh_cmd api "${API_PATH}" --jq '.visibility' 2>/dev/null || echo private)"
  if [ "${VISIBILITY}" = "public" ]; then
    echo "GHCR package ${OWNER}/${PACKAGE} is already public."
    exit 0
  fi

  if gh_cmd api --method PATCH "${API_PATH}" -f visibility=public 2>/dev/null; then
    echo "GHCR package ${OWNER}/${PACKAGE} is public."
    exit 0
  fi

  echo "WARN: GitHub API could not update visibility (GITHUB_TOKEN may lack write:packages)." >&2
fi

if is_publicly_pullable; then
  echo "GHCR package ${OWNER}/${PACKAGE} is public (registry pull OK)."
  exit 0
fi

echo "ERROR: Could not set GHCR package ${OWNER}/${PACKAGE} to public." >&2
echo "Add repo secret PACKAGES_TOKEN (classic PAT with write:packages), or set visibility manually:" >&2
echo "  https://github.com/users/${OWNER}/packages/container/package/${PACKAGE}" >&2
exit 1
