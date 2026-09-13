# iOS 版（Capacitor + HealthKit）開発ガイド

まなとも iOS 版は **Capacitor** で既存 React UI をラップし、歩数は **HealthKit** から読み取って Heroku API に同期します。

## 前提（Mac 必須）

| ツール | 用途 |
|--------|------|
| **Xcode**（App Store） | ビルド・実機デバッグ |
| **CocoaPods** | Capacitor ネイティブプラグイン |
| **Apple Developer Program**（実機 / TestFlight / App Store） | コード署名・HealthKit |

## 初回セットアップ（コピペ用）

```bash
cd ~/ai-education-app
git pull origin cursor/native-health-connect-61ae

cd frontend
npm ci

# 1. CocoaPods（未インストールなら）
brew install cocoapods

# 2. Xcode 初回設定（未実施なら）
sudo xcodebuild -license accept

# 3. iOS Pod 依存関係
npm run setup:ios

# 4. ビルド + iOS sync
VITE_API_URL=https://ai-edu-app-backend-fb6ffb49064a.herokuapp.com/api npm run build:mobile:ios

# 5. Xcode を開く
npm run cap:ios
```

**重要:** Xcode では必ず `frontend/ios/App/App.xcworkspace` を開く（`.xcodeproj` ではない）。

## Firebase（ログイン）

1. [Firebase Console](https://console.firebase.google.com/) → プロジェクト `ai-education-app-9d7ae`
2. **iOS アプリを追加** — Bundle ID: `app.manatomo.education`
3. `GoogleService-Info.plist` をダウンロード
4. `frontend/ios/App/App/GoogleService-Info.plist` に配置（Xcode の App ターゲットにドラッグでも可）

### Google ログイン（redirect）の URL スキーム

`GoogleService-Info.plist` 内の `REVERSED_CLIENT_ID` を Xcode → **Info** → **URL Types** に追加:

- **Identifier**: `GoogleAuth`
- **URL Schemes**: `com.googleusercontent.apps.XXXXXXXX`（REVERSED_CLIENT_ID の値）

Firebase Console → **Authentication** → **Settings** → **Authorized domains** に `localhost` があることを確認。

## HealthKit（歩数）

リポジトリに以下を設定済み:

- `Info.plist` — `NSHealthShareUsageDescription` / `NSHealthUpdateUsageDescription`
- `App.entitlements` — `com.apple.developer.healthkit`

### Apple Developer Portal

1. https://developer.apple.com/account → **Identifiers** → `app.manatomo.education`
2. **HealthKit** capability を有効化
3. Xcode → **Signing & Capabilities** で HealthKit が表示されることを確認

### 動作確認

1. **実機**を USB 接続（シミュレータは HealthKit 歩数が制限される）
2. iPhone の **ヘルスケア** アプリに歩数データがあること
3. まなともでログイン → ホーム → **自動取り込み（ヘルスケア）** → 許可 → **今すぐ同期**

歩数は `POST /api/steps/sync-from-device`（`source: healthkit`）でサーバーに反映されます。

## よくあるエラー

| 症状 | 対処 |
|------|------|
| `CocoaPods is not installed` | `brew install cocoapods` → `npm run setup:ios` |
| `The sandbox is not in sync with the Podfile.lock` | `cd frontend && npm run setup:ios` |
| `Signing for "App" requires a development team` | Xcode → Signing → Team を選択（Apple ID） |
| HealthKit entitlement エラー | Developer Portal で App ID に HealthKit を追加 |
| 歩数が 0 のまま | 実機で試す / ヘルスケアの歩数共有を許可 |

## App Store 提出メモ

- **App Privacy** — 歩数（Health & Fitness）の収集・サーバー保存を申告
- **HealthKit 利用目的** — レビューノートに「学習キャラの成長演出用に歩数を読み取る」と記載
- プライバシーポリシー URL — `https://ai-education-app-9d7ae.web.app/privacypolicy.html`

## コマンド一覧

```bash
npm run setup:ios          # pod install
npm run build:mobile:ios   # Vite build + cap sync ios
npm run cap:ios            # Xcode を開く
npm run cap:sync:ios       # Web 資産のみ iOS に再コピー
```

Android と並行開発する場合:

```bash
# Android のみ
npm run build:mobile:android

# iOS のみ
npm run build:mobile:ios
```

両方 sync する場合（CocoaPods + Android SDK 両方必要）:

```bash
npm run build && cap sync
```
