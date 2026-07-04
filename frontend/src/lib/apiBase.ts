/**
 * API のベース URL（末尾に /api は含めない想定）。
 *
 * **開発サーバー（vite）ではデフォルトで `/api`** にし、`vite.config` のプロキシでバックエンドへ中継する。
 * これでブラウザは同一オリジン（localhost:5173 → /api）にだけアクセスするため Heroku の CORS 設定によらず動く。
 *
 * Heroku に**直接**ブラウザから叩く（プロキシを使わない）場合は開発時に環境変数で無効化:
 *   `.env.development.local` に `VITE_DEV_API_PROXY=false` と `VITE_API_URL=https://....herokuapp.com/api`
 */
export function getApiBase(): string {
  const noProxy =
    import.meta.env.VITE_DEV_API_PROXY === "false" ||
    import.meta.env.VITE_DEV_API_PROXY === "0";

  if (import.meta.env.DEV && !noProxy) {
    return "/api";
  }

  const raw = import.meta.env.VITE_API_URL?.trim();
  if (raw) return raw.replace(/\/$/, "");

  return "http://localhost:8000/api";
}

/** 同上。呼び出し時に評価。 */
export function getApiOriginForStaticPath(): string {
  const base = getApiBase();
  if (base.startsWith("/")) return typeof window !== "undefined" ? window.location.origin : "";
  try {
    return new URL(base).origin;
  } catch {
    return "";
  }
}
