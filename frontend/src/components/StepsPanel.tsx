import { useEffect, useMemo, useRef, useState } from 'react';
import { getAuth } from 'firebase/auth';
import { Link } from 'react-router-dom';
import { Footprints, Trophy } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, XAxis, YAxis } from 'recharts';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';
import { toast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import {
  fetchStepsWeek,
  putStepsToday,
  type StepsWeekDay,
} from '@/lib/stepsApi';
import {
  countGoalDays,
  formatStepsDayLabel,
  jstYmd,
  popNewMilestones,
  stepsEncouragement,
  stepsProgressPct,
} from '@/lib/stepsDisplay';

const weekChartConfig = {
  steps: { label: '歩数', color: 'hsl(199 89% 48%)' },
  goal: { label: '目標', color: 'hsl(142 71% 45%)' },
} satisfies ChartConfig;

type StepsPanelProps = {
  todaySteps: number;
  stepsGoal: number;
  loggedIn: boolean;
  displayName: string;
  todayYmd?: string | null;
  refreshKey?: number;
  onStepsUpdated: (steps: number) => void;
  className?: string;
};

export function StepsWeekChart({
  days,
  loading,
}: {
  days: StepsWeekDay[];
  loading?: boolean;
}) {
  const chartData = days.map((d) => ({
    label: formatStepsDayLabel(d.date),
    steps: d.steps,
    goal_reached: d.goal_reached,
  }));

  if (loading) {
    return <p className="text-sm text-gray-500 text-center py-4">読み込み中…</p>;
  }

  return (
    <ChartContainer config={weekChartConfig} className="aspect-[2.2/1] w-full max-h-44">
      <BarChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={6} />
        <YAxis
          allowDecimals={false}
          tickLine={false}
          axisLine={false}
          width={36}
          tickFormatter={(v) => (v >= 1000 ? `${Math.round(v / 1000)}k` : String(v))}
        />
        <ChartTooltip
          content={
            <ChartTooltipContent
              formatter={(value, _name, item) => {
                const reached = item.payload?.goal_reached as boolean | undefined;
                const steps = value as number;
                const suffix = reached ? ' · 目標達成 🏆' : '';
                return [`${steps.toLocaleString()} 歩${suffix}`, 'その日'];
              }}
            />
          }
        />
        <Bar dataKey="steps" radius={[4, 4, 0, 0]}>
          {chartData.map((entry, i) => (
            <Cell
              key={`cell-${i}`}
              fill={
                entry.goal_reached
                  ? 'hsl(142 71% 45%)'
                  : 'var(--color-steps)'
              }
            />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
}

export function StepsPanel({
  todaySteps,
  stepsGoal,
  loggedIn,
  displayName,
  todayYmd,
  refreshKey = 0,
  onStepsUpdated,
  className,
}: StepsPanelProps) {
  const [weekDays, setWeekDays] = useState<StepsWeekDay[]>([]);
  const [weekLoading, setWeekLoading] = useState(false);
  const [celebrate, setCelebrate] = useState(false);
  const [busy, setBusy] = useState(false);
  const prevStepsRef = useRef(todaySteps);
  const prevGoalReachedRef = useRef(todaySteps >= stepsGoal);

  const pct = stepsProgressPct(todaySteps, stepsGoal);
  const stepsToGoal = Math.max(0, stepsGoal - todaySteps);
  const isGoalReached = todaySteps >= stepsGoal;
  const encouragement = stepsEncouragement(todaySteps, stepsGoal);
  const goalDaysThisWeek = useMemo(() => countGoalDays(weekDays), [weekDays]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setWeekLoading(true);
      try {
        const user = getAuth().currentUser;
        const token = user ? await user.getIdToken() : null;
        const week = await fetchStepsWeek(token);
        if (!cancelled) setWeekDays(week.days);
      } catch {
        if (!cancelled) setWeekDays([]);
      } finally {
        if (!cancelled) setWeekLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshKey, loggedIn]);

  useEffect(() => {
    const ymd = todayYmd ?? jstYmd();
    const prev = prevStepsRef.current;
    if (todaySteps !== prev) {
      const milestones = popNewMilestones(prev, todaySteps, stepsGoal, ymd);
      for (const m of milestones) {
        if (m.pct < 100) {
          toast({ title: m.message, duration: 2800 });
        }
      }
      prevStepsRef.current = todaySteps;
    }

    const wasReached = prevGoalReachedRef.current;
    if (isGoalReached && !wasReached) {
      setCelebrate(true);
      toast({
        title: '🏆 目標達成！',
        description: `${displayName}、${stepsGoal.toLocaleString()}歩クリア！ボーナス XP もチェックしてね`,
        duration: 4500,
      });
      const t = window.setTimeout(() => setCelebrate(false), 4000);
      prevGoalReachedRef.current = true;
      return () => window.clearTimeout(t);
    }
    if (!isGoalReached) {
      prevGoalReachedRef.current = false;
    }
  }, [todaySteps, stepsGoal, isGoalReached, displayName, todayYmd]);

  const adjustSteps = async (delta: number) => {
    const user = getAuth().currentUser;
    if (!user || busy) return;
    setBusy(true);
    try {
      const token = await user.getIdToken();
      const next = Math.max(0, Math.min(999_999, todaySteps + delta));
      const r = await putStepsToday(token, next);
      onStepsUpdated(r.steps);
    } catch {
      toast({
        title: '歩数の保存に失敗しました',
        variant: 'destructive',
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className={cn('kid-card text-center relative overflow-hidden', className)}>
      {celebrate && (
        <div className="steps-confetti pointer-events-none absolute inset-0 z-10" aria-hidden />
      )}

      <div className="text-4xl mb-2">👟</div>
      <h3 className="text-2xl font-bold text-navy-dark mb-1">今日の歩数</h3>
      <p className="text-sm text-lavender-soft font-bold mb-3">{encouragement}</p>

      {!loggedIn ? (
        <div className="space-y-3 mb-4">
          <p className="text-xs text-gray-500">
            ログインすると歩数をサーバーに保存できます。
          </p>
          <Button asChild variant="outline" size="sm" className="rounded-full">
            <Link to="/login">ログインして記録する</Link>
          </Button>
        </div>
      ) : (
        <p className="text-xs text-gray-500 mb-3">
          1000歩ごとに XP · 目標 {stepsGoal.toLocaleString()} 歩でボーナス（1日1回）
        </p>
      )}

      <div
        className={cn(
          'text-5xl font-bold text-sky-soft mb-3 transition-transform',
          celebrate && 'steps-celebrate-pop',
        )}
      >
        {todaySteps.toLocaleString()}
        <span className="text-lg font-normal text-gray-500 ml-1">歩</span>
      </div>

      {!isGoalReached ? (
        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-2 px-1">
            <span>{pct}%</span>
            <span>あと {stepsToGoal.toLocaleString()} 歩</span>
          </div>
          <Progress value={pct} className="h-4 bg-mint-soft/50 mb-1" />
          <div className="flex justify-between text-[10px] text-gray-400 px-0.5">
            <span>0</span>
            <span>25%</span>
            <span>50%</span>
            <span>75%</span>
            <span>🎯</span>
          </div>
        </div>
      ) : (
        <div
          className={cn(
            'bg-gradient-to-r from-mint-soft to-sky-soft rounded-2xl p-5 mb-4',
            celebrate && 'steps-celebrate-pop',
          )}
        >
          <Trophy className="h-10 w-10 mx-auto text-yellow-600 mb-2" />
          <p className="text-2xl font-bold text-navy-dark">目標達成！</p>
          <p className="text-base text-gray-700 mt-1">
            {displayName}が喜んでるよ！
          </p>
        </div>
      )}

      {loggedIn && (
        <>
          <div className="flex flex-wrap justify-center gap-2 mb-5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="rounded-full text-xs"
              disabled={busy}
              onClick={() => void adjustSteps(-300)}
            >
              −300
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="rounded-full text-xs"
              disabled={busy}
              onClick={() => void adjustSteps(500)}
            >
              +500
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="rounded-full text-xs"
              disabled={busy}
              onClick={() => void adjustSteps(1000)}
            >
              +1000
            </Button>
          </div>
          <p className="text-[11px] text-gray-400 mb-4">
            デモ用ボタン（HealthKit 連携は今後対応）
          </p>
        </>
      )}

      <div className="text-left border-t border-gray-100 pt-4 mt-2">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-bold text-navy-dark flex items-center gap-2">
            <Footprints className="h-4 w-4 text-sky-soft" />
            1週間の歩数
          </h4>
          {loggedIn && !weekLoading && (
            <span className="text-xs text-gray-500">
              目標達成 {goalDaysThisWeek} / 7 日
            </span>
          )}
        </div>
        <StepsWeekChart days={weekDays} loading={weekLoading} />
        <p className="text-[10px] text-gray-400 mt-2 text-center">
          緑 = 目標達成 · 日付は日本時間（JST）
        </p>
      </div>
    </Card>
  );
}
