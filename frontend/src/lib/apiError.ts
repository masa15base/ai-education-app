/** FastAPI の { detail: string | object } などを短い日本語向けメッセージにする */
export function formatApiErrorMessage(
  status: number,
  bodyText: string,
  fallback: string,
): string {
  let detail = bodyText;
  try {
    const j = JSON.parse(bodyText) as { detail?: unknown };
    if (typeof j.detail === "string") {
      detail = j.detail;
    } else if (Array.isArray(j.detail)) {
      detail = j.detail.map((d) => JSON.stringify(d)).join("; ");
    } else if (j.detail != null) {
      detail = String(j.detail);
    }
  } catch {
    /* plain text */
  }

  if (status === 401) {
    return "ログインが必要です。ログインし直してからもう一度お試しください。";
  }
  if (status === 422 && detail.includes("quality check failed")) {
    return "キャラの形を認識できませんでした。白い紙に濃いペンで、顔全体が写るように描いてからもう一度お試しください。";
  }
  if (status === 400 && detail.includes("character image")) {
    return "キャラ画像の作成に失敗しました。別の画像で試してください。";
  }
  if (status === 503 && detail.toLowerCase().includes("replicate")) {
    return "サーバーが古い設定のままです。フロントでローカル生成に切り替えます。バックエンドを最新版に更新してください。";
  }
  if (status === 429) {
    return "リクエストが多すぎます。1分ほど待ってからもう一度お試しください。";
  }
  if (detail && detail.length < 280) {
    return detail;
  }
  return fallback;
}
