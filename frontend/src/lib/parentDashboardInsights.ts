import type { StatsSubjectBreakdown, StatsSummary } from '@/lib/statsApi';
import { subjectJa } from '@/lib/subjectJa';

export type LearningInsight = {
  tip: string;
  focusSubject: string | null;
  focusLabel: string | null;
};

function weakestSubject(
  rows: StatsSubjectBreakdown[],
): StatsSubjectBreakdown | null {
  const active = rows.filter((r) => r.sessions_week > 0);
  if (active.length === 0) return null;

  const scored = active.map((row) => ({
    row,
    metric:
      row.answer_accuracy_week ??
      row.average_score_week ??
      null,
  }));

  const withMetric = scored.filter((s) => s.metric != null);
  if (withMetric.length === 0) return active[0] ?? null;

  withMetric.sort((a, b) => (a.metric ?? 100) - (b.metric ?? 100));
  return withMetric[0]?.row ?? null;
}

export function buildLearningInsight(summary: StatsSummary): LearningInsight {
  if (!summary.database_configured) {
    return {
      tip: 'データベース未接続のため、詳細ログはサーバー側にありません。（テスト環境でも同様です）',
      focusSubject: null,
      focusLabel: null,
    };
  }

  const acc = summary.answer_accuracy_week;
  const weak = weakestSubject(summary.subject_breakdown);

  if (acc == null && summary.quiz_sessions_week === 0) {
    return {
      tip: '今週のクイズ記録がまだありません。子どもモードから1回挑戦するとグラフに反映されます。',
      focusSubject: null,
      focusLabel: null,
    };
  }

  if (weak && summary.subject_breakdown.length >= 2) {
    const label = subjectJa(weak.subject);
    const metric =
      weak.answer_accuracy_week ?? weak.average_score_week ?? null;
    if (metric != null && metric < 85) {
      return {
        tip: `${label}が伸びしろです（今週 ${Math.round(metric)}%）。やさしいレベルから復習すると効果的です。`,
        focusSubject: weak.subject,
        focusLabel: label,
      };
    }
  }

  if (acc == null) {
    return {
      tip: '今週の解答ログがありません（クイズ完了 API で記録されます）。',
      focusSubject: null,
      focusLabel: null,
    };
  }
  if (acc < 65) {
    return {
      tip: '得意を伸ばす前に基本問題の復習が効果的です。間違えた問題の「もう一度」機能も活用できます。',
      focusSubject: weak?.subject ?? null,
      focusLabel: weak ? subjectJa(weak.subject) : null,
    };
  }
  if (acc < 85) {
    return {
      tip: '良い調子です。ミスが多い教科を週末に短時間復習すると定着しやすいです。',
      focusSubject: weak?.subject ?? null,
      focusLabel: weak ? subjectJa(weak.subject) : null,
    };
  }
  return {
    tip: 'とても安定しています。少しずつレベルを上げてチャレンジしてみましょう。',
    focusSubject: null,
    focusLabel: null,
  };
}

export function formatChartDay(dateYmd: string): string {
  const [y, m, d] = dateYmd.split('-').map(Number);
  if (!y || !m || !d) return dateYmd;
  return `${m}/${d}`;
}
