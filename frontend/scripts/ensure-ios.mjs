import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const frontendRoot = join(dirname(fileURLToPath(import.meta.url)), '..');

try {
  require.resolve('@capacitor/core');
} catch {
  console.error('\nCapacitor 未インストール。先に `npm ci` を実行してください。\n');
  process.exit(1);
}

const pod = spawnSync('which', ['pod'], { encoding: 'utf8' });
if (pod.status !== 0) {
  console.error(`
CocoaPods が見つかりません（iOS ビルドに必須）。

  brew install cocoapods

詳細: docs/mobile-ios.md
`);
  process.exit(1);
}

const podfileLock = join(frontendRoot, 'ios/App/Podfile.lock');
const podsDir = join(frontendRoot, 'ios/App/Pods');
if (!existsSync(podfileLock) || !existsSync(podsDir)) {
  console.error(`
iOS の Pod 依存関係が未インストールです。

  cd frontend && npm run setup:ios

その後、もう一度 build:mobile:ios を実行してください。
`);
  process.exit(1);
}
