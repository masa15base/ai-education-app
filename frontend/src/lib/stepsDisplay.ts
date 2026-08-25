const MILESTONE_KEY = 'manatomo.steps.milestones.v1';

/** 日本時間（Asia/Tokyo）の YYYY-MM-DD */
export function jstYmd(date: Date = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date);
}

export function stepsProgressPct(steps: number, goal: number): number {
  if (goal <= 0) return 0;
  return Math.min(100, Math.round((steps / goal) * 100));
}

export function stepsEncouragement(steps: number, goal: number): string {
  const pct = stepsProgressPct(steps, goal);
  const remaining = Math.max(0, goal - steps);
  if (pct >= 100) return 'すごい！きょうの目標クリア！';
  if (pct >= 75) return `あと ${remaining.toLocaleString()} 歩！ラストスパート！`;
  if (pct >= 50) return '半分こえた！この調子でいこう！';
  if (pct >= 25) return 'いい感じ！歩いてるね〜';
  if (steps > 0) return 'スタートしたね！少しずつでOK！';
  return '今日もうごこう！さんぽもいいよ〜';
}

export function formatStepsDayLabel(dateYmd: string): string {
  const [, m, d] = dateYmd.split('-').map(Number);
  if (!m || !d) return dateYmd;
  return `${m}/${d}`;
}

type MilestoneToast = { pct: number; message: string };

const MILESTONES: MilestoneToast[] = [
  { pct: 25, message: '25% クリア！いい調子だよ' },
  { pct: 50, message: '半分達成！がんばってるね' },
  { pct: 75, message: '75%！あと少し！' },
  { pct: 100, message: '目標達成！🏆 すごい！' },
];

function loadMilestones(ymd: string): number[] {
  try {
    const raw = localStorage.getItem(MILESTONE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Record<string, number[]>;
    return Array.isArray(parsed[ymd]) ? parsed[ymd] : [];
  } catch {
    return [];
  }
}

function saveMilestone(ymd: string, pct: number) {
  try {
    const raw = localStorage.getItem(MILESTONE_KEY);
    const parsed = (raw ? JSON.parse(raw) : {}) as Record<string, number[]>;
    const prev = Array.isArray(parsed[ymd]) ? parsed[ymd] : [];
    if (prev.includes(pct)) return;
    parsed[ymd] = [...prev, pct];
    localStorage.setItem(MILESTONE_KEY, JSON.stringify(parsed));
  } catch {
    /* ignore */
  }
}

/** 新しく跨いだマイルストーン（25/50/75/100）を返す。同日1回だけ toast 用。 */
export function popNewMilestones(
  prevSteps: number,
  nextSteps: number,
  goal: number,
  ymd: string,
): MilestoneToast[] {
  const prevPct = stepsProgressPct(prevSteps, goal);
  const nextPct = stepsProgressPct(nextSteps, goal);
  const shown = loadMilestones(ymd);
  const hit: MilestoneToast[] = [];

  for (const m of MILESTONES) {
    if (nextPct >= m.pct && prevPct < m.pct && !shown.includes(m.pct)) {
      saveMilestone(ymd, m.pct);
      hit.push(m);
    }
  }
  return hit;
}

export function countGoalDays(days: { goal_reached: boolean }[]): number {
  return days.filter((d) => d.goal_reached).length;
}
