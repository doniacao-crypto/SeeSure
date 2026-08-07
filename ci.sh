#!/usr/bin/env bash
# Per-repo CI shim (Option C, fleet-control-panel#133). The runner executes THIS
# file from the PR branch, but the real logic never comes from the PR branch —
# only this shim does; ci-lib.sh (+ ci/wflint.cjs) is fetched at a panel-pinned
# SHA from ibetterai/.github and passed in as $1.
#
# Runner contract:
#   $1           path to ci-lib.sh (pinned-SHA fetch)
#   CI_BASE_SHA  path-gating base sha (all-zeros for a first push — the lib's
#                fail-safe handles it; an UNSET var here is a runner bug → fail)
#   CI_HEAD_SHA  head sha
#   CI_EVENT     pull_request | push   (optional; npm build OpenNext skip)
#   CI_SKIP_BUILD 1 to skip `npm run build` (optional)
set -euo pipefail

LIB="${1:?usage: ci.sh <path-to-ci-lib.sh>}"
# shellcheck source=/dev/null
source "$LIB"

ci_detect_stack . >/dev/null
ci_main "$CI_STACK" "${CI_BASE_SHA:?CI_BASE_SHA is required}" "${CI_HEAD_SHA:?CI_HEAD_SHA is required}"
