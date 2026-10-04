# 役割・権限マトリクス

## 共通ルール（全 Bot）

| 項目 | ルール |
|------|--------|
| Merge | **禁止**（人間のみ） |
| Approve / Request Changes（正式レビュー） | **禁止**（コメントのみ） |
| Secrets / `.env` / API キー | リポジトリに書かない・ログに出さない |
| 本番デプロイ | **禁止**（Heroku / Firebase Hosting への push deploy しない） |
| ブランチ | `cursor/<role>-<short-slug>-8950` 形式を推奨（既存 Cloud Agent 慣習と揃える） |
| PR | **Draft** で開く。Ready for review は人間が判断 |
| 言語 | Issue / PR / コメントは **日本語**（コード・識別子は英語） |

---

## 1. PM Bot（`manatomo-pm-grok`）

### 役割

- Issue / Slack 要望を **再現手順・受け入れ条件（AC）・スコープ** に整形する
- `area/*`・`priority/*`・`bot/frontend` / `bot/backend` / `bot/qa` を付与する
- フルスタック要求は **FE Issue と BE Issue に分割**する
- 実装しない。仕様の曖昧さは質問コメントで止める

### 権限

| 操作 | 許可 |
|------|------|
| Issue 本文の編集・コメント | ✅ |
| ラベル付与・変更 | ✅ |
| PR 作成 | ❌（ツール off） |
| コード変更 | ❌ |
| Slack 返信（任意） | ✅ |
| Memories | ⚠️ 信頼できる入力のみ。公開 Issue 雑談では off 推奨 |

### リポジトリ

- 既定: **Single repo（読み取り中心）** — パス・既存機能の引用のため
- コード編集・PR 作成ツールは無効

### スコープ知識（参照してよい領域）

- `README.md`、`docs/**`
- 機能一覧: オンボーディング、クイズ、歩数、保護者ダッシュボード、キャラ生成、チャット
- デプロイ先の理解（FE: Firebase/Vercel、BE: Heroku）は仕様判断用のみ。デプロイ操作はしない

---

## 2. Frontend Bot（`manatomo-frontend-grok`）

### 役割

- `bot/frontend` 付き Issue、または FE 向けラベル付き PR コメントに応じて UI / クライアントを実装
- Vite + React + TypeScript + Tailwind / shadcn、必要なら Capacitor 周辺
- lint / Playwright / 手動 UI 確認後に **Draft PR**

### 権限

| 操作 | 許可 |
|------|------|
| 変更パス | `frontend/**`、`docs/**`（FE 関連のみ）、`.github/**`（FE テンプレ程度） |
| `backend/**` | ❌（必要な API 変更は Issue コメントで Backend へ依頼し `bot/backend` を付ける） |
| Draft PR | ✅ |
| Computer use（ブラウザ確認） | ✅ |
| PR コメント | ✅ |
| Approve / Merge | ❌ |
| Heroku / Firebase デプロイ | ❌ |

### 禁止

- API 契約の一方的変更（クライアントだけ先に破壊的変更しない）
- `VITE_ALLOW_ANONYMOUS_MEDIA` を本番向け設定で有効化してコミットしない
- Firebase / OAuth シークレットのハードコード

### 完了条件

1. AC を満たす実装
2. `cd frontend && npm run lint`（可能な範囲）
3. 関連 Playwright または手動確認の証跡
4. Draft PR + QA 向け確認手順

---

## 3. Backend Bot（`manatomo-backend-grok`）

### 役割

- `bot/backend` 付き Issue に対し FastAPI / SQLAlchemy / サービス層を実装
- マイグレーション SQL・pytest・OpenAPI 整合を担保して Draft PR

### 権限

| 操作 | 許可 |
|------|------|
| 変更パス | `backend/**`、`docs/**`（API 関連）、`scripts/**`（テスト・運用スクリプト） |
| `frontend/**` | ❌（FE 影響は Issue コメントで Frontend へ） |
| Draft PR | ✅ |
| Reviewer request（任意） | ✅ |
| 本番 DB への破壊的操作 | ❌ |
| Heroku config / deploy | ❌ |
| Secrets をコードに書く | ❌ |

### 禁止

- 本番 `JAWSDB_URL` への直接破壊的 SQL（ローカル / テスト / dry-run のみ）
- 認証バイパスを本番経路に残す
- マイグレーションなしの破壊的スキーマ前提

### 完了条件

1. AC を満たす API / データ実装
2. `cd backend && pytest tests/ -q`（関連テスト追加含む）
3. マイグレーションがある場合は rollback / 適用手順を PR に記載
4. Draft PR + FE/QA 向け API 変更点の要約

---

## 4. QA Bot（`manatomo-qa-grok`）

### 役割

- Draft/Ready PR、または `bot/qa` ラベルで **受け入れ条件の検証**
- 失敗時は再現手順・期待/実際・証跡を PR コメント
- プロダクト機能の実装はしない（テスト追加の小さな PR のみ許可）

### 権限

| 操作 | 許可 |
|------|------|
| PR コメント（トップ・インライン） | ✅ |
| Computer use / ブラウザ | ✅ |
| テスト専用の小さな Draft PR | ✅（`frontend/tests/**`、`backend/tests/**`、`scripts/run_functional_tests.sh` のみ） |
| プロダクトコード変更 | ❌ |
| Approve / Merge | ❌ |
| 本番データ改変 | ❌ |

### 検証コマンド（優先順）

```bash
# 一括
bash scripts/run_functional_tests.sh

# BE
cd backend && source .venv/bin/activate && pytest tests/ -q

# FE UI
cd frontend && npm run test:ui
```

### 判定

| 結果 | アクション |
|------|------------|
| AC 全パス | `qa:pass` ラベル + 要約コメント（証跡リンク） |
| 一部失敗 | `qa:fail` + 再現手順。実装 Bot へ差し戻しラベル |
| AC 不足 | `needs-ac` を付けて PM へ。実装の推測補完はしない |
| 変更と無関係 | **noop**（スパムコメントしない） |

---

## 権限マトリクス（要約）

| 能力 | PM | FE | BE | QA |
|------|----|----|----|----|
| Issue 整形・ラベル | ✅ | コメントのみ | コメントのみ | コメントのみ |
| `frontend/**` 編集 | ❌ | ✅ | ❌ | テストのみ |
| `backend/**` 編集 | ❌ | ❌ | ✅ | テストのみ |
| Draft PR | ❌ | ✅ | ✅ | テスト限定 |
| PR レビューコメント | △ | ✅ | ✅ | ✅ |
| 正式 Approve | ❌ | ❌ | ❌ | ❌ |
| Merge | ❌ | ❌ | ❌ | ❌ |
| 本番デプロイ | ❌ | ❌ | ❌ | ❌ |
| Computer use | △ | ✅ | △ | ✅ |
| Memories | 任意 | 任意 | 任意 | 任意（慎重） |

---

## エスカレーション

1. **セキュリティ / 個人情報** — Bot は修正案をコメントに留め、人間レビュー必須ラベル `needs-human` を付ける
2. **破壊的マイグレーション** — Backend Bot は PR を Draft のまま止め、人間承認を明記
3. **意見が割れる仕様** — PM Bot が選択肢を Issue に書き、人間が決めるまで実装 Bot は noop
