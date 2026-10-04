# まなとも Grok Bot 設計（PM / Frontend / Backend / QA）

Cursor Automations 上で **Grok** を使う 4 つの専門 Bot の設計書です。  
1 本の万能プロンプトではなく、**トリガー・権限・書き込み面・プロンプトを役割ごとに分離**します。

| Bot | 主な仕事 | コード変更 | 既定モデル |
|-----|----------|------------|------------|
| **PM** | Issue 整形・受け入れ条件・ラベル振り分け | 原則なし | Grok 4.7（medium/high） |
| **Frontend** | `frontend/` 実装・UI 確認・Draft PR | あり（FE のみ） | Grok 4.7（high/xhigh） |
| **Backend** | `backend/` API・DB・テスト・Draft PR | あり（BE のみ） | Grok 4.7（high/xhigh） |
| **QA** | AC 検証・回帰・PR コメント・証跡 | テスト限定のみ | Grok 4.7（high） |

## ドキュメント構成

| ファイル | 内容 |
|----------|------|
| [roles-and-permissions.md](./roles-and-permissions.md) | 役割・権限マトリクス・禁止事項 |
| [github-operations.md](./github-operations.md) | ラベル、ブランチ、ハンドオフ、PR 運用 |
| [automation-setup.md](./automation-setup.md) | Cursor Automations 設定チェックリスト |
| [prompts/pm.md](./prompts/pm.md) | PM Bot プロンプト（貼り付け用） |
| [prompts/frontend.md](./prompts/frontend.md) | Frontend Bot プロンプト |
| [prompts/backend.md](./prompts/backend.md) | Backend Bot プロンプト |
| [prompts/qa.md](./prompts/qa.md) | QA Bot プロンプト |

関連 GitHub 資産:

- `.github/labels.yml` — ラベル定義
- `.github/ISSUE_TEMPLATE/` — Feature / Bug テンプレ
- `.github/PULL_REQUEST_TEMPLATE.md` — PR テンプレ
- `scripts/setup_github_labels.sh` — ラベル一括作成

## 全体フロー

```text
人間 or Slack / Issue
        │
        ▼
   ┌─────────┐
   │ PM Bot  │  要件整理 → AC → ラベル bot/frontend or bot/backend
   └────┬────┘
        │
   ┌────┴────────────────────┐
   ▼                         ▼
Frontend Bot            Backend Bot
(Draft PR)              (Draft PR)
   │                         │
   └──────────┬──────────────┘
              ▼
          QA Bot
   (AC 検証・コメント・証跡)
              │
              ▼
        人間が Merge
```

## 設計原則

1. **書き込み面を分離** — FE と BE が同じ PR で競合しない。フルスタックは PM が Issue を分割する。
2. **Merge は人間のみ** — Bot は Draft PR・コメント・レビュア依頼まで。Approve/Merge しない。
3. **足りない AC では noop** — 実装 Bot は受け入れ条件が無い Issue では何もしない（または質問コメントのみ）。
4. **ラベルがハンドオフ** — PM が付けた `bot/frontend` / `bot/backend` / `bot/qa` が各 Bot の起動条件。
5. **証跡必須** — FE/QA はスクリーンショットまたは録画、BE はテスト結果を PR/コメントに残す。

## 初回セットアップ（最短）

1. `bash scripts/setup_github_labels.sh` でラベルを作成
2. [cursor.com/automations](https://cursor.com/automations) で 4 Automations を作成
3. 各 `prompts/*.md` を Instructions に貼り付け
4. [automation-setup.md](./automation-setup.md) の Tools / Triggers を設定
5. テスト Issue に `bot/pm` → `bot/frontend` と付けて一連の流れを確認
