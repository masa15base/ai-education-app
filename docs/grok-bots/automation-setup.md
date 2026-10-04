# Cursor Automations 設定チェックリスト

作成先: [cursor.com/automations](https://cursor.com/automations)  
リポジトリ: `masa15base/ai-education-app`（branch: `main`）  
モデル: 各 Bot とも **Grok 4.7**（effort は下表）

Teams の場合は **Run as: Service account**、Access: **Members can view** を推奨。

---

## 共通 Environment

FE / BE / QA は同一 Cloud Agent Environment を共有してよい。

最低限:

| 項目 | 内容 |
|------|------|
| Install | `frontend`: `npm ci` / `backend`: venv + `pip install -r requirements.txt` |
| ネットワーク | Heroku API・Firebase・必要なら npm registry（egress allowlist に注意） |
| Secrets | テスト用のみ。本番書き込み系は渡さない |
| Computer use | FE / QA で必須 |

PM は repo 読み取りのみでも可（PR 作成ツールは off）。

---

## 1) `manatomo-pm-grok`

| 項目 | 設定 |
|------|------|
| Model | Grok 4.7 · effort **medium** または **high** |
| Repositories | Single: `ai-education-app` @ `main` |
| Triggers | GitHub: **Issue label changed** = `bot/pm`；任意で Issue comment（`/pm` など） |
| Tools | Comment on PR/Issue 相当 ✅ · PR creation ❌ · Computer use ❌ · Memories 任意 · Slack 任意 |
| Instructions | [`prompts/pm.md`](./prompts/pm.md) 全文 |

動作確認: 空の Issue に `bot/pm` を付け、AC 付きに整形されること。

---

## 2) `manatomo-frontend-grok`

| 項目 | 設定 |
|------|------|
| Model | Grok 4.7 · effort **high** または **xhigh** |
| Repositories | Single: `ai-education-app` @ `main` |
| Triggers | GitHub: **Issue label changed** = `bot/frontend`；任意で PR comment に `frontend:` プレフィックス |
| Tools | PR creation ✅ · Comment ✅ · Computer use ✅ · Request reviewers 任意 · Approvals ❌ |
| Instructions | [`prompts/frontend.md`](./prompts/frontend.md) 全文 |

動作確認: AC 付き Issue に `bot/frontend` → Draft PR が `frontend/**` のみ変更。

---

## 3) `manatomo-backend-grok`

| 項目 | 設定 |
|------|------|
| Model | Grok 4.7 · effort **high** または **xhigh** |
| Repositories | Single: `ai-education-app` @ `main` |
| Triggers | GitHub: **Issue label changed** = `bot/backend` |
| Tools | PR creation ✅ · Comment ✅ · Request reviewers ✅ · Computer use 任意 · Approvals ❌ |
| Instructions | [`prompts/backend.md`](./prompts/backend.md) 全文 |

動作確認: API Issue に `bot/backend` → pytest 緑の Draft PR。`frontend/**` を触らない。

---

## 4) `manatomo-qa-grok`

| 項目 | 設定 |
|------|------|
| Model | Grok 4.7 · effort **high** |
| Repositories | Single: `ai-education-app` @ `main` |
| Triggers | GitHub: **Pull request label changed** = `bot/qa`；**Pull request pushed**（プロンプト内で `bot/qa` 付きのみ処理）；任意で **CI completed** |
| Tools | Comment ✅（inline 可）· Computer use ✅ · PR creation（テスト限定）任意 · Approvals ❌ |
| Instructions | [`prompts/qa.md`](./prompts/qa.md) 全文 |

動作確認: Draft PR に `bot/qa` → AC 検証コメントと `qa:pass` / `qa:fail`。

---

## プロンプト貼り付け手順

1. 各 `prompts/*.md` を開く
2. 「Automation Instructions」セクションを Automations の Prompt 欄へコピー
3. リポジトリ固有の例外（デプロイ禁止など）はプロンプト末尾の Hard Rules を消さない

## 運用上の注意

- **Fork PR は非対応** — 外部 fork からの PR では Automation が失敗する
- **ラベル競合** — 同一 Issue に `bot/frontend` と `bot/backend` を同時に付けない
- **無限ループ防止** — Bot が付けるラベル（`qa:pass` 等）を自分の起動トリガーにしない。PM は `bot/pm` を処理後に外す
- **コスト** — PM/QA は medium〜high、実装は high/xhigh。不要な `Pull request pushed` 全発火は避ける
- **人間の最終責任** — Merge・本番デプロイ・DB マイグレーション適用は人間

## セットアップ完了の定義

- [ ] 4 Automations が Active
- [ ] ラベル作成スクリプト実行済み
- [ ] Issue テンプレがリポジトリに入っている
- [ ] テスト Issue → PM → FE または BE → QA の通し確認が 1 回成功
- [ ] 各 Bot が Merge / 本番デプロイをしていないことを確認
