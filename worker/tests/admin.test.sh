#!/usr/bin/env bash
# Smoke tests for the Worker admin API.
#
# Usage:
#   WORKER_URL=https://ois-discovery.example.workers.dev \
#   ADMIN_API_KEY=your-key-here \
#   bash worker/tests/admin.test.sh
#
# Requires: curl, bash 4+

set -euo pipefail

BASE="${WORKER_URL:?WORKER_URL env var required (e.g. https://ois-discovery.example.workers.dev)}"
KEY="${ADMIN_API_KEY:?ADMIN_API_KEY env var required}"
AUTH="Authorization: Bearer ${KEY}"
PASS=0
FAIL=0

check() {
  local desc="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then
    echo "  PASS: $desc"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $desc — expected HTTP $expected, got $actual"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== OIS Admin API Smoke Tests ==="
echo "Server: $BASE"
echo ""

# ── /admin/stats ──────────────────────────────────────────────────────────────

echo "--- GET /admin/stats ---"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH" "$BASE/admin/stats")
check "GET /admin/stats → 200" "200" "$STATUS"

BODY=$(curl -s -H "$AUTH" "$BASE/admin/stats")
echo "  Body: $BODY"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer wrong-key-xxx" "$BASE/admin/stats")
check "GET /admin/stats wrong key → 401" "401" "$STATUS"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/admin/stats")
check "GET /admin/stats no auth → 401" "401" "$STATUS"

# ── /admin/identities ─────────────────────────────────────────────────────────

echo ""
echo "--- GET /admin/identities ---"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH" "$BASE/admin/identities")
check "GET /admin/identities → 200" "200" "$STATUS"

BODY=$(curl -s -H "$AUTH" "$BASE/admin/identities?limit=5")
echo "  Body (limit=5): $BODY"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "$AUTH" "$BASE/admin/identities?q=test&limit=10")
check "GET /admin/identities?q=test → 200" "200" "$STATUS"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "$AUTH" "$BASE/admin/identities?limit=5&offset=0")
check "GET /admin/identities paginated → 200" "200" "$STATUS"

# ── DELETE /admin/identity/:symbol_id ─────────────────────────────────────────

echo ""
echo "--- DELETE /admin/identity/:symbol_id ---"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE -H "$AUTH" "$BASE/admin/identity/nonexistent-symbol")
check "DELETE /admin/identity/nonexistent → 404" "404" "$STATUS"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE -H "Authorization: Bearer wrong-key" "$BASE/admin/identity/test")
check "DELETE /admin/identity wrong key → 401" "401" "$STATUS"

# ── DELETE /identity (self-delete) ────────────────────────────────────────────

echo ""
echo "--- DELETE /identity (self-delete) ---"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE -H "Content-Type: application/json" \
  -d '{"symbol_id":"test","challenge_token":"000000","assertion":{}}' \
  "$BASE/identity")
check "DELETE /identity missing assertion fields → 422" "422" "$STATUS"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE -H "Content-Type: application/json" -d '{}' \
  "$BASE/identity")
check "DELETE /identity empty body → 422" "422" "$STATUS"

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
