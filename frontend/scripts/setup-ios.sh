#!/usr/bin/env bash
# CocoaPods で iOS ネイティブ依存関係をインストール
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IOS_APP="$ROOT/ios/App"

if ! command -v pod >/dev/null 2>&1; then
  echo ""
  echo "CocoaPods が見つかりません。Mac で以下のいずれかを実行してください:"
  echo ""
  echo "  brew install cocoapods"
  echo "  # または"
  echo "  sudo gem install cocoapods"
  echo ""
  echo "Xcode も App Store からインストールしてください。"
  exit 1
fi

if ! command -v xcodebuild >/dev/null 2>&1; then
  echo ""
  echo "Xcode / xcodebuild が見つかりません。"
  echo "App Store から Xcode をインストールし、一度起動してライセンスに同意してください:"
  echo "  sudo xcodebuild -license accept"
  exit 1
fi

echo "== pod install ($IOS_APP) =="
cd "$IOS_APP"
pod install

echo ""
echo "OK. 次のコマンドで Xcode を開けます:"
echo "  cd frontend && npm run cap:ios"
echo ""
echo "必ず App.xcworkspace を開いてください（App.xcodeproj ではない）。"
