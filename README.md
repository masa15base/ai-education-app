# まなとも（AI Education App）

子どもの学習とキャラクター成長をつなぐ Web アプリです。  
**フロント**: React（Vite + TypeScript）+ Tailwind / shadcn UI + Firebase Authentication  
**バックエンド**: FastAPI + SQLAlchemy（MySQL / JawsDB が無い環境では一部が**プロセス内メモリ**にフォールバック）

---

## リポジトリ構成

| ディレクトリ | 役割 |
|--------------|------|
| `frontend/` | SPA。開発時は Vite の **プロキシ**で `/api` → バックエンドへ転送 |
| `backend/` | REST API（`app.main:app`） |
| `scripts/` | リポジトリ横断の運用・機能テストスクリプト |
| `docs/` | 仕様メモ（例: キャラ画像生成） |

---

## 主な機能（実装済み）

- **オンボーディング**: ログイン後、初回ユーザーは `/onboarding`（歓迎 → キャラ名 → Lv1 クイズ）。XP・学習履歴・カスタムキャラがある場合はスキップ。完了フラグは端末の `localStorage`（キー `manatomo.onboarding.v1`、uid 単位）
- **ホーム**: キャラ表示・名前編集・経験値バー、今日のクイズ導線、**歩数パネル**（週間グラフ・マイルストーン・デモ同期）。歩数本体は **ログイン時 `GET/PUT /api/steps/today` / `GET /api/steps/week`**（端末に歩数は保存しない）
- **クイズ**: `GET /api/questions` は **JawsDB の `questions` テーブル**を優先（教科・レベル一致で**ランダム**に最大 `limit` 件）。件数不足や DB 未設定時は従来の **動的生成（`quiz_engine`）** にフォールバック。完了時 **`POST /api/quiz/complete`**（Bearer 付き）で採点し、**`progress_entries` + `user_characters.experience`** を更新。XP は **単一付与経路**（日次上限 **80**）。1日に何回でも挑戦可。直近セッションは **`GET /api/quiz/session-today`**
- **問題バンク運用**: CSV 投入は `backend/scripts/upload_question_bank.py`（`--mode upsert|replace` / `--dry-run` / `--stats-only`）。統計は `GET /api/questions/bank-stats`。シード CSV は `backend/app/data/questions_level_10_final.csv`（算数・英語 × Lv1–10 × 各5問・4択）
- **成長記録**: `/character-log` と `/api/stats/summary` のタイムライン（サーバーのみ）
- **保護者ダッシュボード**: `GET /api/stats/summary`（週間クイズ `weekly_activity`・教科別 `subject_breakdown`・タイムライン・学習ヒント）、歩数週間チャート（`GET /api/steps/week`）、クイズ再挑戦リンク
- **学習履歴**: ログイン時 **`GET /api/progress`**（教科・レベルフィルタ、サマリー、再挑戦 / 次レベル導線）。未ログイン時は CTA
- **歩数ボーナス XP**: ログイン時 **`POST /api/character/sync-steps-xp`**（DB の歩数・冪等フラグで付与）
- **チャット**: `POST /api/chat/`（`OPENAI_API_KEY` あり: GPT‑4o mini、なし: サーバー側シンプル返答）、`GET /api/chat/capabilities`
- **接続テスト**: `/connection-test`（ヘルス・診断のカスケード、問題バンク統計、ログイン時は **進捗 GET・歩数 PUT 往復** も確認）
- **キャラクター画像生成**: 手書き写真 → 前処理（線画 PNG）→ カラー化（PNG）→ **確認画面でも前処理プレビュー（線の濃さヒント付き）** → OK でホームへ反映（要件は [docs/character-image-generation.md](docs/character-image-generation.md)）
- **ログイン / ログアウト**: Firebase、未ログイン時は共通 **`LoggedOutCTA`** で案内（履歴・成長記録・保護者画面など）

**データの保存先（本番想定）**: キャラ・クイズ進捗・歩数・経験値は **Heroku 接続の MySQL（JawsDB）** に集約。フロントは学習データ・歩数を **`localStorage` に永続化しない**（セッション中のメモリキャッシュのみ）。例外は **オンボーディング完了フラグ**（上記キー）のみ。

---

## 本番 DB マイグレーション（Heroku / JawsDB）

成長・歩数ボーナス用に **既存 DB へ列追加**が必要です（`create_all` は既存テーブルに列を足しません）。

```bash
# Homebrew MySQL 9 などで mysql_native_password が使えない場合は PyMySQL ヘルパー:
#   python backend/scripts/run_jawsdb_sql.py backend/scripts/heroku_add_growth_columns.sql
mysql "$JAWSDB_URL" < backend/scripts/heroku_add_growth_columns.sql
```

- `user_characters`: `steps_growth_ymd`, `steps_xp_paid_tier`, `steps_xp_goal_bonus`
- `progress_entries`: `gained_xp`（クイズ日次 XP 上限の集計用）
- 成長統計テーブル: `user_character_growth_stats`（スクリプト内の定義に従う）

---

## 歩数 API（スケッチ・方針）

| メソッド | パス | 認証 | 説明 |
|----------|------|------|------|
| `GET` | `/api/steps/today` | **任意**（Bearer なし可） | 未ログイン: `authenticated: false`, `steps: null`。ログイン済: 当日（**サーバー UTC の YYYY-MM-DD**）の歩数。DB 無し時はメモリ。 |
| `PUT` | `/api/steps/today` | **必須** | JSON `{ "steps": number }` で当日を上書き（手入力・ホームのデモ同期用）。 |
| `GET` | `/api/steps/week` | **任意** | 直近 7 日分の歩数・目標達成日など（ホーム / 保護者ダッシュボード用）。 |

**将来**: HealthKit / Health Connect などはブラウザから直接取れないため、**ネイティブ連携 or 別バッチ**がこの API に `PUT` / サーバー側ジョブで流し込む想定。現状は「子どもホームのデモボタン」と同じ値をクラウドに残す用途。

---

## 環境変数（バックエンド）

`.env` は **Git にコミットしない**こと。

| 変数 | 用途 |
|------|------|
| `JAWSDB_URL` | MySQL 接続（無い場合は DB 依存機能がメモリフォールバック） |
| `FIREBASE_CREDENTIALS_JSON` | Firebase Admin（本番では ID トークン検証に使用） |
| `OPENAI_API_KEY` | チャット AI（無い場合はシンプル返答モード）・手書きキャラ解析 Vision（`CHARACTER_VISION_ENABLED=1` 時） |
| `CHARACTER_VISION_ENABLED` | `0` で手書き解析をルールベースのみに（既定 `1`） |
| `CHARACTER_VISION_MODEL` | Vision モデル（既定 `gpt-4o-mini`） |
| `REPLICATE_API_TOKEN` | キャラ画像生成など |
| `FRONTEND_ORIGINS` | CORS 許可オリジン（カンマ区切り） |
| `FRONTEND_ORIGIN_REGEX` | 追加で許可する正規表現（空で無効化可） |

---

## 環境変数（フロント）

| 変数 | 用途 |
|------|------|
| `VITE_DEV_API_PROXY` | `false` のとき開発でも `VITE_API_URL` に直接アクセス |
| `VITE_API_URL` | 例: `https://xxx.herokuapp.com/api`（末尾 `/api`） |
| `VITE_ALLOW_ANONYMOUS_MEDIA` | `1` / `true` で未ログイン時の前処理・キャラ生成を許可（**E2E / 開発用**。本番では未設定） |
| `BACKEND_PROXY_TARGET`（`vite.config` / `frontend` ルート） | dev サーバの `/api` プロキシ先（既定で Heroku URL あり） |

---

## ローカル起動

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- ヘルス: `http://127.0.0.1:8000/api/health`
- OpenAPI: `http://127.0.0.1:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

- 既定: `http://localhost:5173`（ポート競合時は 5174 など）
- ブラウザは **`/api/...` のみ**叩き、Vite がバックエンドへプロキシ（CORS 問題を避ける）

---

## テスト

### 一括（推奨）

backend pytest + frontend Playwright + Heroku smoke をまとめて実行:

```bash
bash scripts/run_functional_tests.sh
```

- Heroku API ベースは環境変数 `HEROKU_API_BASE` で上書き可（既定: 本番 `/api`）
- Smoke は `/health`・`/questions/bank-stats`・`/questions?subject=math&level=1` を確認

### バックエンドのみ

```bash
cd backend
source .venv/bin/activate
pytest tests/ -q
```

### フロント UI（Playwright）

```bash
cd frontend
npm run test:ui
# 見出し付き: npm run test:ui:headed
```

- 設定: `frontend/playwright.config.ts`（preview `4173`、ビルド時 `VITE_ALLOW_ANONYMOUS_MEDIA=1`）
- 主なスペック: `tests/ui/smoke.spec.ts` / `integration.spec.ts` / `features.spec.ts`（オンボーディング・履歴・バンク統計・保護者ダッシュボードなど）

### 手動確認の目安

1. ログイン → 初回なら `/onboarding`（名前 → Lv1 クイズ）
2. 算数 / 英語クイズ完了 → XP・履歴に反映
3. 履歴: フィルタ・再挑戦・次レベル
4. ホーム: 歩数パネル（週間・マイルストーン）
5. 保護者ダッシュボード: 週間チャート・教科別・学習ヒント
6. キャラ作成: 前処理プレビュー → OK でホーム反映

---

## API 一覧（抜粋）

| メソッド | パス | 概要 |
|----------|------|------|
| `GET` | `/api/health` | OK。`?include_diagnostic=true` で DB 疎通など |
| `GET` | `/api/diagnostic` | 診断別名 |
| `GET` | `/api/questions` | クイズ問題（**DB `questions` 優先・ランダム**、不足時は動的生成） |
| `GET` | `/api/questions/bank-stats` | 問題バンク件数・レベル不足（gaps）・`ready_for_quiz` |
| `POST` / `GET` | `/api/progress` | 学習履歴（要 Bearer） |
| `GET` / `PUT` | `/api/character` | キャラ（要 Bearer） |
| `POST` | `/api/quiz/complete` | クイズ完了（採点・セッション保存・日次上限付き XP） |
| `GET` | `/api/quiz/session-today` | 当日の直近クイズセッション |
| `GET` | `/api/stats/summary` | 統計サマリー（Bearer 任意）。`weekly_activity` / `subject_breakdown` / タイムライン。ログイン時は **`steps_today` / `steps_ymd` / `steps_source`** も同梱 |
| `GET` / `PUT` | `/api/steps/today` | 当日歩数（GET 任意、PUT 要 Bearer） |
| `GET` | `/api/steps/week` | 直近 7 日の歩数サマリー |
| `POST` | `/api/character/sync-steps-xp` | 歩数ボーナス XP（要 Bearer・冪等） |
| `POST` | `/api/chat/` | チャット |
| `GET` | `/api/chat/capabilities` | OpenAI 有無 |
| `GET` | `/api/preprocess-image/info` | 前処理・**画像形式要件**（`requirements`） |
| `POST` | `/api/preprocess-image` | 手書き画像アップロード → 線画 **PNG**（base64） |
| `POST` | `/api/generate-character` | 前処理 PNG → カラーキャラ **PNG**（data URL） |

### キャラクター画像のファイル形式（要約）

| 段階 | 形式 |
|------|------|
| **アップロード（入力）** | JPEG / PNG（推奨）、WebP / GIF / BMP。最大 8MB。HEIC・PDF・動画は不可 |
| **前処理・生成（出力）** | **PNG**（`image/png`）。キャラは data URL base64 |

詳細: [docs/character-image-generation.md](docs/character-image-generation.md)

---

## セキュリティ

- API キー・DB URL はリポジトリに含めない。
- 本番では **Firebase Admin で ID トークン検証**（`FIREBASE_CREDENTIALS_JSON`）。開発のみ未設定時は JWT の `sub` を緩く参照する経路あり — 本番では必ず Admin を設定すること。
- `VITE_ALLOW_ANONYMOUS_MEDIA` は本番フロントに載せないこと。

---

## 問題バンク（CSV → JawsDB）

```bash
cd backend
source .venv/bin/activate
export JAWSDB_URL="$(heroku config:get JAWSDB_URL -a ai-edu-app-backend)"

# 検証のみ
python scripts/upload_question_bank.py --dry-run

# 追記・更新（推奨）
python scripts/upload_question_bank.py --mode upsert

# 全消しして入れ直し
python scripts/upload_question_bank.py --mode replace

# カバレッジ確認
python scripts/upload_question_bank.py --stats-only
# または GET /api/questions/bank-stats
```

シード再生成: `python app/scripts/generate_questions_csv.py`

---

## 今後のロードマップ（例）

- 歩数: ウェアラブル / OS ヘルス API からの**自動取り込みパイプライン**
- チャット: 学習コンテキスト連携・履歴保存・保護者向け要約（プライバシー方針とセット）
- キャラ進化ビジュアルの本実装
- CI（pytest + Playwright）の自動化
- 課金・B2B などはプロダクト方針に応じて

---

## Author

Masakazu Nakamura
