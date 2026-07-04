import { getApiBase } from "./apiBase";

export type StatsTimelineItem = {
  created_at: string;
  subject: string;
  level: number;
  score: number;
  kind: string;
};

export type StatsCharacterBrief = {
  display_name: string;
  experience: number;
  level: number;
  image_url: string | null;
};

export type StatsSummary = {
  database_configured: boolean;
  window_days: number;
  quiz_sessions_week: number;
  quiz_sessions_total: number;
  average_score_week: number;
  answers_count_week: number;
  answer_accuracy_week: number | null;
  character: StatsCharacterBrief | null;
  timeline: StatsTimelineItem[];
  steps_goal: number;
  steps_today: number | null;
  steps_ymd: string | null;
  steps_source: string | null;
};

export async function fetchStatsSummary(
  idToken: string | null | undefined,
  timelineLimit = 40,
): Promise<StatsSummary> {
  const headers: Record<string, string> = {};
  if (idToken) headers.Authorization = `Bearer ${idToken}`;
  const url = `${getApiBase()}/stats/summary?timeline_limit=${timelineLimit}`;
  const res = await fetch(url, { headers });
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(`${res.status} ${t || res.statusText}`);
  }
  return res.json() as Promise<StatsSummary>;
}
