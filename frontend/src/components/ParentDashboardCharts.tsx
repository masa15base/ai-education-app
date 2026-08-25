import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';
import { Progress } from '@/components/ui/progress';
import type {
  StatsDailyActivity,
  StatsSubjectBreakdown,
} from '@/lib/statsApi';
import { formatChartDay } from '@/lib/parentDashboardInsights';
import { subjectJa } from '@/lib/subjectJa';

const weeklyChartConfig = {
  sessions: {
    label: 'クイズ回数',
    color: 'hsl(217 91% 60%)',
  },
} satisfies ChartConfig;

type WeeklyActivityChartProps = {
  data: StatsDailyActivity[];
  loading?: boolean;
};

export function WeeklyActivityChart({ data, loading }: WeeklyActivityChartProps) {
  const chartData = data.map((row) => ({
    label: formatChartDay(row.date),
    sessions: row.quiz_sessions,
    average_score: row.average_score,
  }));

  if (loading) {
    return (
      <p className="text-sm text-gray-500 py-8 text-center">グラフを読み込み中…</p>
    );
  }

  if (chartData.every((d) => d.sessions === 0)) {
    return (
      <p className="text-sm text-gray-600 py-6 text-center">
        今週のクイズ記録がまだありません。
      </p>
    );
  }

  return (
    <ChartContainer config={weeklyChartConfig} className="aspect-[2/1] w-full max-h-56">
      <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis
          dataKey="label"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
        />
        <YAxis
          allowDecimals={false}
          tickLine={false}
          axisLine={false}
          width={28}
        />
        <ChartTooltip
          content={
            <ChartTooltipContent
              formatter={(value, _name, item) => {
                const avg = item.payload?.average_score as number | null | undefined;
                const sessions = value as number;
                if (avg != null && sessions > 0) {
                  return [`${sessions} 回（平均 ${Math.round(avg)}%）`, 'クイズ'];
                }
                return [`${sessions} 回`, 'クイズ'];
              }}
            />
          }
        />
        <Bar dataKey="sessions" fill="var(--color-sessions)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ChartContainer>
  );
}

type SubjectBreakdownPanelProps = {
  rows: StatsSubjectBreakdown[];
  loading?: boolean;
};

export function SubjectBreakdownPanel({ rows, loading }: SubjectBreakdownPanelProps) {
  if (loading) {
    return (
      <p className="text-sm text-gray-500 py-8 text-center">読み込み中…</p>
    );
  }

  const active = rows.filter((r) => r.sessions_week > 0 || r.answers_count_week > 0);
  if (active.length === 0) {
    return (
      <p className="text-sm text-gray-600 py-6 text-center">
        教科別データはまだありません。
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {active.map((row) => {
        const label = subjectJa(row.subject);
        const accuracy =
          row.answer_accuracy_week ?? row.average_score_week ?? null;
        const pct = accuracy == null ? 0 : Math.min(100, Math.round(accuracy));
        return (
          <div key={row.subject} className="space-y-2">
            <div className="flex items-center justify-between text-sm gap-2">
              <span className="font-medium text-gray-800">{label}</span>
              <span className="text-gray-600 shrink-0">
                {row.sessions_week} 回
                {accuracy != null ? ` · ${Math.round(accuracy)}%` : ''}
              </span>
            </div>
            <Progress value={pct} className="h-2" />
            {row.answers_count_week > 0 && row.answer_accuracy_week != null && (
              <p className="text-xs text-gray-500">
                解答 {row.answers_count_week} 問 · 正答率 {Math.round(row.answer_accuracy_week)}%
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
