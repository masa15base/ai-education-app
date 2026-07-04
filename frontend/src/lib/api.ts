// src/lib/api.ts
import { auth } from "../firebaseConfig";
import { getApiBase } from "./apiBase";

async function withIdToken(): Promise<string> {
  const user = auth.currentUser;
  if (!user) throw new Error("Not signed in");
  // true で強制リフレッシュ（期限切れ対策）
  return await user.getIdToken(true);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await withIdToken();
  const res = await fetch(`${getApiBase()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// --------- 進捗API ----------
export type Item = {
  uid?: string;
  subject: string;
  level: number;
  score: number;
  updated_at?: string;
};

// 保存（UPSERT）
export function saveProgress(input: {
  subject: string;
  level: number;
  score: number;
}) {
  return request<{ status: "ok"; uid: string }>(`/progress`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

// 履歴取得（subject 未指定で全件）
export function fetchProgress(subject?: string) {
  const q = subject ? `?subject=${encodeURIComponent(subject)}` : "";
  return request<{ items: Item[] }>(`/progress${q}`, { method: "GET" });
}

// --------- 動的クイズ完了（ログイン時は Bearer 付きで保存）---------
export type QuizAnswerPayload = {
  question_index: number;
  selected_answer: string;
  /** DB の questions.id。付与時はサーバー採点が DB 優先になる */
  question_id?: string;
};

export type QuizCompletePayload = {
  subject: string;
  level: number;
  answers: QuizAnswerPayload[];
};

export async function postQuizComplete(
  body: QuizCompletePayload,
  idToken?: string | null,
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (idToken) headers["Authorization"] = `Bearer ${idToken}`;
  const res = await fetch(`${getApiBase()}/quiz/complete`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${text || res.statusText}`);
  }
  return res.json() as Promise<{
    score_percent: number;
    correct: number;
    total: number;
    saved: boolean;
    details: unknown[];
    gained_xp: number;
    experience?: number | null;
    level?: number | null;
  }>;
}

export type SyncStepsXpResult = {
  xp_gained: number;
  detail: string[];
  display_name: string;
  image_url: string | null;
  experience: number;
  level: number;
};

/** 歩数ボーナス XP をサーバーで計算・付与（DB 冪等） */
export function postSyncStepsXp(goalSteps = 5000) {
  return request<SyncStepsXpResult>(`/character/sync-steps-xp`, {
    method: "POST",
    body: JSON.stringify({ goal_steps: goalSteps }),
  });
}