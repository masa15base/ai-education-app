import { getAuth } from "firebase/auth";
import { getApiBase } from "./apiBase";

export type QuizSessionTodayResponse = {
  has_session_today: boolean;
  latest: {
    subject: string;
    level: number;
    score: number;
    gained_xp: number;
    updated_at: string;
  } | null;
};

export async function fetchQuizSessionToday(): Promise<QuizSessionTodayResponse> {
  const headers: Record<string, string> = {};
  const u = getAuth().currentUser;
  if (u) headers.Authorization = `Bearer ${await u.getIdToken()}`;
  const res = await fetch(`${getApiBase()}/quiz/session-today`, { headers });
  if (!res.ok) {
    return { has_session_today: false, latest: null };
  }
  return (await res.json()) as QuizSessionTodayResponse;
}
