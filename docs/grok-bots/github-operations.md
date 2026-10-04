# GitHub 運用設計

対象リポジトリ: [`masa15base/ai-education-app`](https://github.com/masa15base/ai-education-app)  
既定ブランチ: `main`

## ラベル体系

`scripts/setup_github_labels.sh` / `.github/labels.yml` で管理する。

### エリア

| ラベル | 用途 |
|--------|------|
| `area/frontend` | UI / Vite / Capacitor |
| `area/backend` | FastAPI / DB / 外部 API |
| `area/docs` | ドキュメントのみ |
| `area/infra` | デプロイ・環境・CI |

### Bot ハンドオフ（トリガー用）

| ラベル | 誰が付ける | 誰が反応 |
|--------|------------|----------|
| `bot/pm` | 人間 | PM Bot |
| `bot/frontend` | PM（または人間） | Frontend Bot |
| `bot/backend` | PM（または人間） | Backend Bot |
| `bot/qa` | 人間 / 実装 Bot（PR 準備完了時） | QA Bot |

### 優先度・状態

| ラベル | 意味 |
|--------|------|
| `priority/p0` | 本番影響・学習データ破損リスク |
| `priority/p1` | 主要導線の不具合・期限あり |
| `priority/p2` | 通常 |
| `priority/p3` | 改善・任意 |
| `needs-ac` | 受け入れ条件不足 |
| `needs-human` | Bot 停止・人間判断必須 |
| `blocked` | 外部依存で待機 |
| `qa:pass` | QA 検証成功 |
| `qa:fail` | QA 検証失敗 |
| `size/xs`〜`size/l` | 見積もり（任意） |

既存の GitHub デフォルトラベル（`bug` / `enhancement` 等）も併用してよい。

## Issue ライフサイクル

```text
[人間] Issue 作成 or Slack 要望
   → label: bot/pm
[PM] AC・再現・分割・area/*・priority/*
   → label: bot/frontend and/or bot/backend
[FE/BE] 実装 → Draft PR（closes #N）
   → PR に bot/qa（または ready 後に人間が付与）
[QA] 検証 → qa:pass / qa:fail
[人間] Review → Ready → Merge
```

### Issue 必須要素（PM が担保）

1. **背景**（1〜3 行）
2. **再現手順**（Bug）または **ユーザーストーリー**（Feature）
3. **受け入れ条件（AC）** — チェックリスト形式
4. **対象パス / API**（分かる範囲）
5. **Out of scope**
6. **FE/BE 分割**（必要ならリンク付き子 Issue）

テンプレ: `.github/ISSUE_TEMPLATE/feature.yml` / `bug.yml`

## ブランチ命名

```text
cursor/<role>-<short-slug>-8950
```

例:

- `cursor/frontend-steps-panel-a11y-8950`
- `cursor/backend-quiz-xp-cap-8950`
- `cursor/qa-playwright-onboarding-8950`

ルール:

- 小文字・ハイフンのみ
- `main` から分岐
- 1 Issue = 1 実装ブランチ（FE/BE 分割時は Issue も分ける）

## コミット / PR

### コミットメッセージ

短く Imperative でも日本語でも可。変更の「なぜ」が分かる一文。

例: `fix quiz XP daily cap when bank questions reuse IDs`

### PR タイトル

```text
[<area>] <要約>
```

例: `[frontend] 歩数パネルの週間グラフ空状態を改善`

### PR 本文（必須）

テンプレ: `.github/PULL_REQUEST_TEMPLATE.md`

- 関連 Issue（`Closes #123`）
- AC 対応表
- テスト結果
- 画面証跡（FE/QA）
- リスク / マイグレーション
- QA 向け確認手順

### Draft のまま残す条件

- テスト失敗
- AC 未達
- `needs-human` / 破壊的マイグレーション
- FE/BE の相手側未完了で結合できない

## Bot 間ハンドオフ詳細

### PM → 実装

1. Issue に AC チェックリストを書く
2. `area/frontend` または `area/backend` を付与
3. `bot/pm` を外し、`bot/frontend` / `bot/backend` を付与
4. 両方必要な場合は **Issue を 2 つに分割**し、相互リンク。同じラベルを 1 Issue に両方付けない（競合防止）

### 実装 → QA

実装 Bot が Draft PR を開いたら PR 本文に「QA 手順」を書き、ラベル `bot/qa` を PR に付与（または人間が Ready 時に付与）。

### QA → 実装（差し戻し）

1. `qa:fail` + 再現コメント
2. `bot/qa` を外す
3. 該当側に再度 `bot/frontend` または `bot/backend` を付ける（PR コメントでメンション相当の指示）

### QA → 人間

`qa:pass` 後、人間がレビューして Merge。Bot は Merge しない。

## CODEOWNERS / 保護ブランチ（推奨）

現状未設定のため、段階導入を推奨:

1. `main` を Protected Branch に（PR 必須、直 push 禁止）
2. 任意で `CODEOWNERS`:
   - `/frontend/` → フロント担当
   - `/backend/` → バック担当
3. Bot の Approve は使わない（Cursor の Approval Agents を使う場合は別ポリシーファイルで管理）

## CI との関係

README ロードマップ通り、CI 自動化は今後の課題。それまでの QA Bot はローカル相当コマンドを Cloud Agent 環境で実行する。

推奨（別 PR で導入可）:

- Backend: `pytest`
- Frontend: `npm run lint` + Playwright smoke
- QA Bot トリガーに `CI completed` を追加し、失敗時のみ深掘り

## `@cursor` との使い分け

| 手段 | 用途 |
|------|------|
| Automations（本 4 Bot） | ラベル / PR イベントでの定常ハンドオフ |
| Issue/PR で `@cursor` | その場の対話的依頼（アドホック） |
| Bugbot / Security Agents | 汎用バグ・脆弱性レビュー（役割 Bot と重複させない） |

Grok 4 Bot は **製品開発の役割分担**、Bugbot は **横断レビュー** と位置づける。
