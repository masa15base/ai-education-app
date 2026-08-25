export type HistoryItem = {
  subject: string;
  level: number;
  score: number;
  updated_at: string;
  gained_xp?: number;
  uid?: string;
};

export type HistorySubjectFilter = 'all' | 'math' | 'english';
export type HistoryLevelFilter = 'all' | number;

export function normalizeSubjectKey(subject: string): 'math' | 'english' | string {
  const s = subject.trim().toLowerCase();
  if (s === 'english' || s === '英語') return 'english';
  if (s === 'math' || s === '算数') return 'math';
  return s;
}

export function filterHistory(
  items: HistoryItem[],
  subject: HistorySubjectFilter,
  level: HistoryLevelFilter,
): HistoryItem[] {
  return items.filter((item) => {
    const key = normalizeSubjectKey(item.subject);
    if (subject !== 'all' && key !== subject) return false;
    if (level !== 'all' && item.level !== level) return false;
    return true;
  });
}

export function historySummary(items: HistoryItem[]) {
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const inWeek = items.filter((i) => {
    const t = Date.parse(i.updated_at);
    return !Number.isNaN(t) && t >= weekAgo;
  });
  const avgScore = items.length
    ? Math.round(items.reduce((s, i) => s + i.score, 0) / items.length)
    : 0;
  const bestScore = items.length ? Math.max(...items.map((i) => i.score)) : 0;
  const subjects = new Set(items.map((i) => normalizeSubjectKey(i.subject))).size;
  const totalXp = items.reduce((s, i) => s + (i.gained_xp ?? 0), 0);
  return {
    total: items.length,
    weekCount: inWeek.length,
    avgScore,
    bestScore,
    subjectCount: subjects,
    totalXp,
  };
}

export function quizRetryPath(item: HistoryItem): string {
  const subj = normalizeSubjectKey(item.subject);
  const subject = subj === 'english' ? 'english' : 'math';
  const level =
    item.score >= 100 ? Math.min(10, item.level + 1) : item.level;
  return `/quiz?subject=${encodeURIComponent(subject)}&level=${level}`;
}

export function retryLabel(item: HistoryItem): string {
  return item.score >= 100 ? '次のレベルへ' : 'もう一度';
}

export type ScoreTone = 'great' | 'good' | 'retry';

export function scoreTone(score: number): ScoreTone {
  if (score >= 85) return 'great';
  if (score >= 65) return 'good';
  return 'retry';
}

export const SCORE_TONE_CLASS: Record<ScoreTone, string> = {
  great: 'bg-green-100 text-green-800 border-green-200',
  good: 'bg-sky-100 text-sky-800 border-sky-200',
  retry: 'bg-amber-100 text-amber-900 border-amber-200',
};

export function distinctLevels(items: HistoryItem[]): number[] {
  const set = new Set(items.map((i) => i.level));
  return [...set].sort((a, b) => a - b);
}
