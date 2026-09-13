# ネイティブアプリ（Capacitor）開発ガイド

まなともは **Web（Firebase Hosting）** と **ネイティブ（Capacitor）** の二刀流です。  
歩数の自動取り込みは **ネイティブを正** とし、Android は **Health Connect**、iOS は **HealthKit** を使います。

## アーキテクチャ

```
┌─────────────────────────────────────┐
│  Capacitor WebView（既存 React UI）   │
│  ├─ Android: Health Connect 読取   │
│  └─ iOS: HealthKit 読取             │
└──────────────┬──────────────────────┘
               │ Bearer（Firebase ID Token）
               ▼
┌─────────────────────────────────────┐
│  Heroku FastAPI                      │
│  POST /api/steps/sync-from-device    │
│  merge_steps_for_day (monotonic max) │
└─────────────────────────────────────┘
```

- **Web ブラウザ**: Google Fit REST（〜2026 年末）— 移行期間のフォールバック
- **ネイティブ APK/IPA**: Health Connect / HealthKit → サーバー同期（OAuth 不要）

## 前提

- Node.js 18+
- **Android**: Android Studio、JDK 17、SDK 26+
- **iOS**: Xcode、CocoaPods（Mac のみ）
- Firebase プロジェクトに **Android / iOS アプリ**を追加（`google-services.json` / `GoogleService-Info.plist`）

## 初回セットアップ

**ブランチ切り替え後は必ず `npm ci` を実行してください。**  
未実行だと `@capacitor/core` が見つからず Vite ビルドが失敗します。

```bash
cd frontend
npm ci                                    # ← 必須（checkout 直後に忘れがち）
VITE_API_URL=https://ai-edu-app-backend-fb6ffb49064a.herokuapp.com/api npm run build:mobile:android
npm run cap:android                       # Android Studio を開く（未インストール時は下記参照）
```

### よくあるエラー

| 症状 | 原因 | 対処 |
|------|------|------|
| `@capacitor/core` が見つからない | `npm ci` 未実行 | `cd frontend && npm ci` |
| `CocoaPods is not installed` | iOS 同期が走った | **Android のみ**なら `build:mobile:android` を使う（iOS 不要） |
| `Unable to launch Android Studio` | Android Studio 未インストール | 下記「Android Studio のインストール」を参照 |

`npm run cap:android` が `could not determine executable to run` になる場合も、ほぼ同じ原因（`npm ci` 未実行）です。

### 環境変数（モバイルビルド）

`.env.production` またはビルド時:

```bash
VITE_API_URL=https://ai-edu-app-backend-fb6ffb49064a.herokuapp.com/api
```

### Android Studio のインストール（Mac）

1. https://developer.android.com/studio から **Android Studio** をダウンロード・インストール
2. 初回起動ウィザードで **Android SDK**（API 26 以上）を入れる
3. ターミナルで `npm run cap:android` が使えるようになる

Android Studio を別の場所に入れた場合:

```bash
export CAPACITOR_ANDROID_STUDIO_PATH="/Applications/Android Studio.app"
```

手動で開く場合: Android Studio → **Open** → `frontend/android` フォルダを選択。

### Android ビルド手順

1. Firebase Console で Android アプリ（`app.manatomo.education`）を登録
2. `google-services.json` を `frontend/android/app/` に配置
3. `npm run build:mobile:android`（Vite ビルド + Android のみ sync）
4. `npm run cap:android` または Android Studio で `frontend/android` を開く
5. 実機またはエミュレータで **Run ▶**

Health Connect は Android 14+ に同梱。それ以前は Play Store から「Health Connect by Android」をインストール。

### iOS

1. Firebase Console で iOS アプリを登録
2. `GoogleService-Info.plist` を `frontend/ios/App/App/` に配置
3. Xcode で **HealthKit** capability を有効化
4. `npm run cap:ios` で Xcode を開き Run

## 歩数同期フロー

1. ログイン後、ホーム表示 / タブ復帰時に `autoSyncStepsIfNeeded()`（15 分間隔）
2. ネイティブでは `@capgo/capacitor-health` で直近 7 日分を集計
3. `POST /api/steps/sync-from-device` に `{ source, days[] }` を送信
4. サーバーは既存値より大きい場合のみ反映（`source`: `health_connect` | `healthkit`）

## 認証（ネイティブ）

WebView では `signInWithPopup` が使えないため、ソーシャルログインは **redirect** 方式です（`authNative.ts`）。  
Firebase Console の **承認済みドメイン** に `localhost` を追加してください。

## Google Fit との関係

[Google Fit 移行ガイド](https://developer.android.com/health-and-fitness/health-connect/migration/fit) に従い:

| クライアント | 歩数 API |
|-------------|----------|
| ネイティブ Android | Health Connect |
| ネイティブ iOS | HealthKit |
| Web ブラウザ | Google Fit REST（移行期）→ 将来 Google Health API |

新規 Android 開発は **Health Connect を正** とし、Google Fit OAuth は Web 専用のレガシー経路として残しています。

## よく使うコマンド

```bash
cd frontend
npm run dev              # Web 開発
npm run build:mobile     # dist + cap sync
npx cap run android      # CLI から実機実行（環境次第）
```

## Play Store / App Store

- Health Connect: プライバシーポリシー必須（`android/.../privacypolicy.html` 参照）
- Play Console: **Health apps declaration** の提出
- データセーフティフォーム: 歩数の収集・サーバー保存を申告
