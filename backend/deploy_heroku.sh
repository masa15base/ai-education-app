#!/bin/bash

# デプロイ用シェルスクリプト
# 実行方法: ./deploy_heroku.sh

APP_NAME="ai-edu-app-backend"
BRANCH="main"

echo "🚀 Heroku にデプロイを開始します..."

# 仮想環境を有効化
if [ -d "venv" ]; then
  source venv/bin/activate
  echo "✅ 仮想環境を有効化しました"
fi

# 変更を Git に追加
git add .
git commit -m "Deploy to Heroku" || echo "⚠️ コミット対象なし"

# Heroku に強制 push
git push https://git.heroku.com/$APP_NAME.git $BRANCH:main -f

echo "✅ デプロイ処理が完了しました"