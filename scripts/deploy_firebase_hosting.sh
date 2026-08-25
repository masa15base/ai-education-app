#!/usr/bin/env bash
# Firebase Hosting へフロントエンド（Vite SPA）をデプロイ
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_BASE="${VITE_API_URL:-https://ai-edu-app-backend-fb6ffb49064a.herokuapp.com/api}"
PROJECT="${FIREBASE_PROJECT:-ai-education-app-9d7ae}"

echo "== Build frontend (VITE_API_URL=${API_BASE}) =="
cd "$ROOT/frontend"
npm ci
VITE_API_URL="$API_BASE" npm run build

echo "== Deploy to Firebase Hosting (project: ${PROJECT}) =="
cd "$ROOT"
if ! command -v firebase >/dev/null 2>&1; then
  npx --yes firebase-tools deploy --only hosting --project "$PROJECT"
else
  firebase deploy --only hosting --project "$PROJECT"
fi

echo "Done. Site: https://${PROJECT}.web.app"
