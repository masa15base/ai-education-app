# Agent guide — まなとも（ai-education-app）

このリポジトリで動く Cloud Agents / Grok Bots 向けの共通ガイドです。  
役割別の詳細は [docs/grok-bots/README.md](docs/grok-bots/README.md) を正本とします。

## 役割分担

| Role | Paths | Opens PR? |
|------|-------|-----------|
| PM | Issue only | No |
| Frontend | `frontend/**` | Draft yes |
| Backend | `backend/**`, `scripts/**` | Draft yes |
| QA | verify; tests-only PRs | Tests only |

## Hard rules

- Never merge to `main`. Never approve your own (or peer bot) PRs as a substitute for humans.
- Never deploy to production (Heroku / Firebase Hosting / Vercel) from an automation run.
- Never commit secrets (`.env`, API keys, `FIREBASE_CREDENTIALS_JSON`, DB URLs).
- Do not put learning progress / steps into `localStorage` (onboarding completion flag only).
- Same Issue must not carry both `bot/frontend` and `bot/backend` at once — split issues.
- Prefer Japanese for Issue/PR/comments; English for code identifiers.

## Commands

```bash
# Backend tests
cd backend && source .venv/bin/activate && pytest tests/ -q

# Frontend UI tests
cd frontend && npm run test:ui

# Combined functional checks
bash scripts/run_functional_tests.sh
```

## Branch naming

`cursor/<role>-<short-slug>-8950` (lowercase, hyphens).

## Docs map

- Product/README: `README.md`
- Character image pipeline: `docs/character-image-generation.md`
- Mobile: `docs/mobile-native.md`, `docs/mobile-ios.md`
- Grok Bots design: `docs/grok-bots/`
