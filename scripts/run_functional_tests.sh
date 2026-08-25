#!/usr/bin/env bash
# 機能テスト一括実行（backend pytest + frontend Playwright + Heroku smoke）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="${HEROKU_API_BASE:-https://ai-edu-app-backend-fb6ffb49064a.herokuapp.com/api}"

echo "== Backend pytest =="
cd "$ROOT/backend"
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pytest tests/ -q --tb=line

echo "== Frontend Playwright =="
cd "$ROOT/frontend"
npx playwright test

echo "== Heroku smoke =="
curl -sfS "$API/health" | tee /tmp/manatomo-health.json
echo
curl -sfS "$API/questions/bank-stats" | tee /tmp/manatomo-bank.json
echo
curl -sfS "$API/questions?subject=math&level=1&limit=2" | tee /tmp/manatomo-questions.json
echo
python3 - <<'PY'
import json
h=json.load(open("/tmp/manatomo-health.json"))
b=json.load(open("/tmp/manatomo-bank.json"))
q=json.load(open("/tmp/manatomo-questions.json"))
assert h.get("ok") is True, h
assert b.get("database_configured") is True, b
assert int(b.get("total") or 0) >= 5, b
assert isinstance(q, list) and len(q) >= 1, q
assert "options" in q[0] and len(q[0]["options"]) == 4, q[0]
print("Heroku smoke OK")
PY

echo "All functional checks passed."
