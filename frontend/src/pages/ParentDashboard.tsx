import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAuth, onAuthStateChanged, type User } from 'firebase/auth';
import { LoggedOutCTA } from '@/components/LoggedOutCTA';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import {
  ArrowLeft,
  Calendar,
  BookOpen,
  Activity,
  Star,
  TrendingUp,
} from 'lucide-react';
import { fetchStatsSummary, type StatsSummary } from '@/lib/statsApi';
import {
  DEFAULT_CHARACTER,
  levelFromExperience,
  progressInCurrentLevel,
} from '@/lib/characterState';
import {
  fetchCharacterGrowthStatus,
  type CharacterGrowthStatus,
} from '@/lib/characterStatusApi';
import {
  EvolutionProgressCard,
  GrowthStageRoadmap,
} from '@/components/GrowthProgress';
import { STAGE_EMOJI, stageLabel } from '@/lib/growthDisplay';
import { subjectJa } from '@/lib/subjectJa';
import {
  SubjectBreakdownPanel,
  WeeklyActivityChart,
} from '@/components/ParentDashboardCharts';
import { StepsWeekChart } from '@/components/StepsPanel';
import { buildLearningInsight } from '@/lib/parentDashboardInsights';
import { fetchStepsWeek, type StepsWeekDay } from '@/lib/stepsApi';
import { countGoalDays } from '@/lib/stepsDisplay';

function emptySummary(): StatsSummary {
  return {
    database_configured: false,
    window_days: 7,
    quiz_sessions_week: 0,
    quiz_sessions_total: 0,
    average_score_week: 0,
    answers_count_week: 0,
    answer_accuracy_week: null,
    character: null,
    timeline: [],
    weekly_activity: [],
    subject_breakdown: [],
    steps_goal: 5000,
    steps_today: null,
    steps_ymd: null,
    steps_source: null,
  };
}

const ParentDashboard = () => {
  const navigate = useNavigate();
  const offlineChar = DEFAULT_CHARACTER;

  const [firebaseUser, setFirebaseUser] = useState<User | null>(() =>
    getAuth().currentUser,
  );

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<StatsSummary>(emptySummary());
  const [growthStatus, setGrowthStatus] = useState<CharacterGrowthStatus | null>(
    null,
  );
  const [stepsWeek, setStepsWeek] = useState<StepsWeekDay[]>([]);
  const [stepsWeekLoading, setStepsWeekLoading] = useState(false);

  useEffect(() => {
    const unsub = onAuthStateChanged(getAuth(), setFirebaseUser);
    return () => unsub();
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setLoading(true);
      setError(null);
      try {
        const token = firebaseUser
          ? await firebaseUser.getIdToken()
          : null;
        const data = await fetchStatsSummary(token, 40);
        if (!cancelled) {
          setSummary(data);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
          setSummary(emptySummary());
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [firebaseUser]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      if (!firebaseUser) {
        setGrowthStatus(null);
        return;
      }
      const st = await fetchCharacterGrowthStatus();
      if (!cancelled) setGrowthStatus(st);
    })();
    return () => {
      cancelled = true;
    };
  }, [firebaseUser]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      if (!firebaseUser) {
        setStepsWeek([]);
        return;
      }
      setStepsWeekLoading(true);
      try {
        const token = await firebaseUser.getIdToken();
        const week = await fetchStepsWeek(token);
        if (!cancelled) setStepsWeek(week.days);
      } catch {
        if (!cancelled) setStepsWeek([]);
      } finally {
        if (!cancelled) setStepsWeekLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [firebaseUser]);

  const charFromApi = summary.character;
  const displayChar = charFromApi
    ? {
        name: charFromApi.display_name,
        level: charFromApi.level,
        xp: charFromApi.experience,
        imageUrl: charFromApi.image_url ?? null,
      }
    : {
        name: offlineChar.displayName,
        level: levelFromExperience(offlineChar.experience),
        xp: offlineChar.experience,
        imageUrl: offlineChar.imageUrl,
      };

  const weeklyCompletionTarget = Math.max(7, summary.window_days);
  const quizWeekProgressPct = Math.min(
    100,
    (summary.quiz_sessions_week / weeklyCompletionTarget) * 100,
  );

  const recentActivities = useMemo(() => summary.timeline.slice(0, 8), [summary.timeline]);
  const stepsGoalDaysWeek = useMemo(() => countGoalDays(stepsWeek), [stepsWeek]);

  const learningInsight = useMemo(
    () =>
      buildLearningInsight({
        ...summary,
        weekly_activity: summary.weekly_activity ?? [],
        subject_breakdown: summary.subject_breakdown ?? [],
      }),
    [summary],
  );

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <Button
            onClick={() => navigate('/')}
            variant="ghost"
            size="sm"
            className="mr-4"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            子どもモードに戻る
          </Button>
          <h1 className="text-2xl font-bold text-gray-800">保護者ダッシュボード</h1>
        </div>
        <div className="text-sm text-gray-600">
          最終更新:{' '}
          {loading ? '読み込み中…' : new Date().toLocaleString('ja-JP')}
        </div>
      </div>

      {error && (
        <div className="max-w-6xl mx-auto mb-4 text-sm text-red-700 bg-red-50 border border-red-100 rounded-lg px-4 py-3">
          統計の取得に失敗しました: {error}
        </div>
      )}

      <div className="max-w-6xl mx-auto">
        {!firebaseUser && (
          <div className="mb-4">
            <LoggedOutCTA
              title="保護者ダッシュボードはログイン後がおすすめ"
              description="クラウドの学習統計や「きょうの歩数」（子どもホームのデモと同期）を見るにはログインが必要です。今はこの端末のキャラ情報と空の統計だけ表示しています。"
            />
          </div>
        )}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card className="p-6 bg-blue-50 border-blue-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-blue-600 font-medium">今週のクイズ</p>
                <p className="text-2xl font-bold text-blue-800">
                  {loading ? '…' : summary.quiz_sessions_week}
                </p>
                <p className="text-xs text-blue-700 mt-1">累計 {summary.quiz_sessions_total} セッション</p>
              </div>
              <BookOpen className="h-8 w-8 text-blue-500" />
            </div>
          </Card>

          <Card className="p-6 bg-green-50 border-green-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-green-600 font-medium">今週の平均スコア</p>
                <p className="text-2xl font-bold text-green-800">
                  {loading ? '…' : `${Math.round(summary.average_score_week)}%`}
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-500" />
            </div>
          </Card>

          <Card className="p-6 bg-purple-50 border-purple-200">
            <div className="flex items-center justify-between">
              <div className="min-w-0 flex-1">
                <p className="text-sm text-purple-600 font-medium">きょうの歩数</p>
                {!firebaseUser ? (
                  <p className="text-xs text-purple-800 mt-2">ログインすると表示</p>
                ) : loading ? (
                  <p className="text-sm font-bold text-purple-800 mt-1">読み込み中…</p>
                ) : (
                  <>
                    <p className="text-2xl font-bold text-purple-800 mt-1">
                      {(summary.steps_today ?? 0).toLocaleString()} 歩
                    </p>
                    <p className="text-xs text-purple-700 mt-1">
                      目標 {summary.steps_goal.toLocaleString()} 歩（サーバー日付{' '}
                      {summary.steps_ymd ?? '—'} · UTC · {summary.steps_source ?? '—'}）
                    </p>
                    <Progress
                      value={Math.min(
                        100,
                        ((summary.steps_today ?? 0) / summary.steps_goal) * 100,
                      )}
                      className="h-2 mt-2"
                    />
                  </>
                )}
                <p className="text-xs text-purple-600 mt-2">
                  HealthKit / Health Connect の自動取り込みは今後対応予定
                </p>
              </div>
              <Activity className="h-8 w-8 text-purple-500 shrink-0 ml-2" />
            </div>
          </Card>

          <Card className="p-6 bg-yellow-50 border-yellow-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-yellow-600 font-medium">キャラレベル</p>
                <p className="text-2xl font-bold text-yellow-800">
                  {growthStatus?.level ?? displayChar.level}
                </p>
                <p className="text-xs text-yellow-800 mt-1">
                  {growthStatus
                    ? `${STAGE_EMOJI[growthStatus.stage] ?? ''} ${growthStatus.stage_label}`
                    : `XP ${displayChar.xp}`}
                </p>
              </div>
              <Star className="h-8 w-8 text-yellow-500" />
            </div>
          </Card>
        </div>

        {growthStatus && (
          <Card className="p-6 mb-6 border-indigo-100 bg-indigo-50/40">
            <h3 className="text-lg font-bold text-gray-800 mb-2">
              キャラ成長サマリ
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              {displayChar.name} · ステージ{' '}
              <span className="font-bold">
                {STAGE_EMOJI[growthStatus.stage]} {growthStatus.stage_label}
              </span>
              {growthStatus.next_evolution?.next_stage && (
                <>
                  {' '}
                  → 次は{' '}
                  <span className="font-bold text-indigo-700">
                    {growthStatus.next_evolution.next_stage_label ||
                      stageLabel(growthStatus.next_evolution.next_stage)}
                  </span>
                </>
              )}
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4 text-sm">
              <div className="rounded-lg bg-white p-3 border">
                <p className="text-gray-500 text-xs">クイズ正解（累計）</p>
                <p className="font-bold text-lg">{growthStatus.quiz_correct_count}</p>
              </div>
              <div className="rounded-lg bg-white p-3 border">
                <p className="text-gray-500 text-xs">クイズ連続日数</p>
                <p className="font-bold text-lg">{growthStatus.quiz_streak_days}</p>
              </div>
              <div className="rounded-lg bg-white p-3 border">
                <p className="text-gray-500 text-xs">累計歩数</p>
                <p className="font-bold text-lg">
                  {growthStatus.total_steps.toLocaleString()}
                </p>
              </div>
              <div className="rounded-lg bg-white p-3 border">
                <p className="text-gray-500 text-xs">ログイン連続</p>
                <p className="font-bold text-lg">{growthStatus.login_streak_days}</p>
              </div>
            </div>
            <GrowthStageRoadmap
              currentStage={growthStatus.stage}
              nextEvolution={growthStatus.next_evolution}
              compact
              className="mb-4 bg-white rounded-xl p-3 border"
            />
            <EvolutionProgressCard nextEvolution={growthStatus.next_evolution} />
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <Card className="p-6">
            <h3 className="text-lg font-bold mb-1 flex items-center">
              <TrendingUp className="h-5 w-5 mr-2 text-blue-500" />
              週間クイズ（直近7日）
            </h3>
            <p className="text-xs text-gray-500 mb-4">日付はサーバー UTC 基準</p>
            <WeeklyActivityChart
              data={summary.weekly_activity ?? []}
              loading={loading}
            />
          </Card>

          <Card className="p-6">
            <h3 className="text-lg font-bold mb-1 flex items-center">
              <Activity className="h-5 w-5 mr-2 text-purple-500" />
              週間歩数（直近7日）
            </h3>
            <p className="text-xs text-gray-500 mb-2">
              {firebaseUser
                ? `目標達成 ${stepsGoalDaysWeek} / 7 日 · 目標 ${summary.steps_goal.toLocaleString()} 歩`
                : 'ログインすると表示されます'}
            </p>
            {firebaseUser ? (
              <StepsWeekChart days={stepsWeek} loading={stepsWeekLoading} />
            ) : (
              <p className="text-sm text-gray-600 py-6 text-center">
                子どもアカウントでログインすると週間グラフが表示されます。
              </p>
            )}
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <Card className="p-6 lg:col-span-2">
            <h3 className="text-lg font-bold mb-4 flex items-center">
              <BookOpen className="h-5 w-5 mr-2 text-indigo-500" />
              教科別（今週）
            </h3>
            <SubjectBreakdownPanel
              rows={summary.subject_breakdown ?? []}
              loading={loading}
            />
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="p-6">
            <h3 className="text-lg font-bold mb-4 flex items-center">
              <BookOpen className="h-5 w-5 mr-2 text-blue-500" />
              学習進捗
            </h3>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>今週のクイズ回数（目安）</span>
                  <span>{summary.quiz_sessions_week} / {weeklyCompletionTarget} 回</span>
                </div>
                <Progress value={quizWeekProgressPct} className="h-2" />
              </div>

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>今週の平均スコア</span>
                  <span>{Math.round(summary.average_score_week)}%</span>
                </div>
                <Progress value={Math.min(100, Math.round(summary.average_score_week))} className="h-2" />
              </div>

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>今週の正答率（解答ログ）</span>
                  <span>
                    {summary.answer_accuracy_week == null ? '—' : `${Math.round(summary.answer_accuracy_week)}%`}
                  </span>
                </div>
                <Progress
                  value={
                    summary.answer_accuracy_week == null
                      ? 0
                      : Math.min(100, Math.round(summary.answer_accuracy_week))
                  }
                  className="h-2"
                />
              </div>

              <div className="bg-blue-50 rounded-lg p-4 mt-4">
                <h4 className="font-medium text-blue-800 mb-2">学習アドバイス</h4>
                <p className="text-sm text-blue-700">{learningInsight.tip}</p>
                {learningInsight.focusSubject && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3 rounded-full"
                    onClick={() =>
                      navigate(
                        `/quiz?subject=${encodeURIComponent(learningInsight.focusSubject!)}`,
                      )
                    }
                  >
                    {learningInsight.focusLabel}のクイズへ
                  </Button>
                )}
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-lg font-bold mb-4 flex items-center">
              <Calendar className="h-5 w-5 mr-2 text-gray-500" />
              最近の活動（クイズ）
            </h3>

            {recentActivities.length === 0 ? (
              <p className="text-sm text-gray-600">
                クイズの記録がまだありません。子どもアカウントでクイズを完了すると表示されます。
              </p>
            ) : (
              <div className="space-y-3">
                {recentActivities.map((row) => (
                  <div
                    key={`${row.created_at}-${row.subject}-${row.level}-${row.score}`}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg gap-3"
                  >
                    <div className="min-w-0">
                      <p className="font-medium text-gray-800">
                        {subjectJa(row.subject)} クイズ
                      </p>
                      <p className="text-sm text-gray-600">
                        {new Date(row.created_at).toLocaleDateString('ja-JP')} ・ Lv.{row.level}
                      </p>
                    </div>
                    <div className="text-right shrink-0 flex flex-col items-end gap-1">
                      <p className="text-sm font-medium text-gray-800">スコア {row.score}%</p>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs text-blue-700"
                        onClick={() =>
                          navigate(
                            `/quiz?subject=${encodeURIComponent(row.subject)}&level=${row.level}`,
                          )
                        }
                      >
                        同じ条件で挑戦
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card className="p-6 lg:col-span-2">
            <h3 className="text-lg font-bold mb-4 flex items-center">
              <Star className="h-5 w-5 mr-2 text-yellow-500" />
              キャラクター状況
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center">
                {displayChar.imageUrl ? (
                  <img
                    src={displayChar.imageUrl}
                    alt={displayChar.name}
                    className="w-36 h-36 mx-auto mb-2 object-contain rounded-2xl"
                  />
                ) : (
                  <div className="text-6xl mb-2">😺</div>
                )}
                <h4 className="font-bold text-gray-800">{displayChar.name}</h4>
                <p className="text-sm text-gray-600">レベル {displayChar.level}</p>
              </div>

              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>次レベルまで</span>
                    <span>{progressInCurrentLevel(displayChar.xp)}/100</span>
                  </div>
                  <Progress value={progressInCurrentLevel(displayChar.xp)} className="h-2" />
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>総経験値</span>
                    <span>{displayChar.xp}</span>
                  </div>
                </div>
                <p className="text-xs text-gray-600">
                  ログイン済みかつサーバーにキャラがあれば、その値が優先表示されます。
                </p>
              </div>

              <div className="bg-yellow-50 rounded-lg p-4">
                <h4 className="font-medium text-yellow-800 mb-2">データソース</h4>
                <ul className="text-sm text-yellow-700 space-y-1">
                  <li>・クイズ: /api/quiz/complete と /api/progress</li>
                  <li>
                    ・サーバー状態:{' '}
                    {summary.database_configured ? 'DB 連携済み' : 'DB 未設定（開発メモリ等）'}
                  </li>
                </ul>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default ParentDashboard;
