import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);

const packages = ['@capacitor/core', '@capacitor/cli'];

for (const name of packages) {
  try {
    require.resolve(name);
  } catch {
    console.error(`
Capacitor が見つかりません (${name})。

ブランチ切り替え後は frontend で依存関係を入れ直してください:

  cd frontend
  npm ci

その後、もう一度 build:mobile を実行してください。
`);
    process.exit(1);
  }
}
