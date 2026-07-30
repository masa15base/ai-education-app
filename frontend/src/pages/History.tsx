import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getAuth, onAuthStateChanged } from 'firebase/auth';
import {
  ArrowLeft,
  BookOpen,
  Filter,
  RotateCcw,
  Star,
  TrendingUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { LoggedOutCTA } from '@/components/LoggedOutCTA';
import { fetchProgress } from '@/lib/api';
import {
  distinctLevels,
  filterHistory,
  historySummary,
  quizRetryPath,
  retryLabel,
  SCORE_TONE_CLASS,
  scoreTone,
  type HistoryItem,
  type HistoryLevelFilter,
  type HistorySubjectFilter,
} from '@/lib/historyDisplay';
import { subjectJa } from '@/lib/subjectJa';
import { cn } from '@/lib/utils';

const SUBJECT_FILTERS: { id: HistorySubjectFilter; label: string }[] = [
  { id: 'all', label: 'すべて' },
  { id: 'math', label: '算数' },
  { id: 'english', label: '英語' },
];

function SummaryCard({
  label,
  value,
  sub,
  icon: Icon,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: typeof BookOpen;
}) {
  return (
    <Card className="p-4 bg-white/90 border-gray-100">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-navy-dark mt-1">{value}</p>
          {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
        </div>
        <Icon className="h-5 w-5 text-sky-soft shrink-0" />
      </div>
    </Card>
  );
}

const History = () => {
  const navigate = useNavigate();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);
  const [subjectFilter, setSubjectFilter] = useState<HistorySubjectFilter>('all');
  const [levelFilter, setLevelFilter] = useState<HistoryLevelFilter>('all');

  useEffect(() => {
    const auth = getAuth();
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      setLoggedIn(!!user);
      setLoading(true);
      setError(null);
      if (!user) {
        setHistory([]);
        setLoading(false);
        return;
      }

      try {
        const data = await fetchProgress();
        setHistory(Array.isArray(data.items) ? data.items : []);
      } catch (e) {
        console.error(e);
        setError(
          e instanceof Error ? e.message : 'クラウドの履歴が取得できませんでした。',
        );
        setHistory([]);
      } finally {
        setLoading(false);
      }
    });

    return () => unsubscribe();
  }, []);

  const summary = useMemo(() => historySummary(history), [history]);
  const levelOptions = useMemo(() => distinctLevels(history), [history]);
  const filtered = useMemo(
    () => filterHistory(history, subjectFilter, levelFilter),
    [history, subjectFilter, levelFilter],
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-lavender-light/40 via-white to-mint-light/40 p-4">
      <div className="max-w-4xl mx-auto space-y-4">
        {loggedIn === false && (
          <LoggedOutCTA
            title="学習履歴を見るにはログイン"
            description="履歴はサーバーに保存されます。ログイン後にクイズを完了すると、ここに記録が表示されます。"
          />
        )}

        <div className="flex items-center gap-3 flex-wrap">
          <Button variant="outline" size="sm" asChild className="rounded-full">
            <Link to="/">
              <ArrowLeft className="h-4 w-4 mr-2 inline" />
              ホーム
            </Link>
          </Button>
          <h1 className="text-2xl font-bold text-navy-dark">学習履歴</h1>
          {loggedIn && (
            <span className="text-xs bg-sky-soft/30 text-navy-dark px-2 py-1 rounded-full">
              サーバー · {summary.total} 件
            </span>
          )}
        </div>

        {loading ? (
          <p className="text-gray-600">読み込み中…</p>
        ) : (
          <>
            {error && (
              <Card className="p-4 border-amber-200 bg-amber-50 text-sm text-amber-900">
                {error}
              </Card>
            )}

            {loggedIn && history.length > 0 && (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <SummaryCard
                    label="今週のクイズ"
                    value={`${summary.weekCount} 回`}
                    icon={BookOpen}
                  />
                  <SummaryCard
                    label="平均スコア"
                    value={`${summary.avgScore}%`}
                    icon={TrendingUp}
                  />
                  <SummaryCard
                    label="最高スコア"
                    value={`${summary.bestScore}%`}
                    icon={Star}
                  />
                  <SummaryCard
                    label="獲得 XP（合計）"
                    value={`+${summary.totalXp}`}
                    sub={`${summary.subjectCount} 教科`}
                    icon={Star}
                  />
                </div>

                <Card className="kid-card p-4 space-y-3">
                  <div className="flex items-center gap-2 text-sm font-bold text-navy-dark">
                    <Filter className="h-4 w-4" />
                    絞り込み
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {SUBJECT_FILTERS.map((f) => (
                      <Button
                        key={f.id}
                        type="button"
                        size="sm"
                        variant={subjectFilter === f.id ? 'default' : 'outline'}
                        className="rounded-full"
                        onClick={() => setSubjectFilter(f.id)}
                      >
                        {f.label}
                      </Button>
                    ))}
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs text-gray-500">レベル:</span>
                    <Button
                      type="button"
                      size="sm"
                      variant={levelFilter === 'all' ? 'default' : 'outline'}
                      className="rounded-full h-8"
                      onClick={() => setLevelFilter('all')}
                    >
                      すべて
                    </Button>
                    {levelOptions.map((lv) => (
                      <Button
                        key={lv}
                        type="button"
                        size="sm"
                        variant={levelFilter === lv ? 'default' : 'outline'}
                        className="rounded-full h-8 min-w-[2.5rem]"
                        onClick={() => setLevelFilter(lv)}
                      >
                        Lv.{lv}
                      </Button>
                    ))}
                  </div>
                  <p className="text-xs text-gray-500">
                    {filtered.length} 件表示
                    {(subjectFilter !== 'all' || levelFilter !== 'all') && (
                      <button
                        type="button"
                        className="ml-2 text-sky-600 underline"
                        onClick={() => {
                          setSubjectFilter('all');
                          setLevelFilter('all');
                        }}
                      >
                        リセット
                      </button>
                    )}
                  </p>
                </Card>
              </>
            )}

            {loggedIn && history.length === 0 ? (
              <Card className="kid-card p-8 text-center text-gray-600">
                <p className="mb-4">まだサーバーに履歴がありません。ホームからクイズを始めよう。</p>
                <Button asChild className="kid-button">
                  <Link to="/">ホームへ</Link>
                </Button>
              </Card>
            ) : loggedIn && filtered.length === 0 ? (
              <Card className="kid-card p-8 text-center text-gray-600">
                <p className="mb-4">この条件の履歴はありません。フィルタを変えてみてね。</p>
                <Button
                  variant="outline"
                  className="rounded-full"
                  onClick={() => {
                    setSubjectFilter('all');
                    setLevelFilter('all');
                  }}
                >
                  フィルタをリセット
                </Button>
              </Card>
            ) : loggedIn ? (
              <div className="space-y-3">
                {filtered.map((item, idx) => {
                  const tone = scoreTone(item.score);
                  return (
                    <Card
                      key={`${item.updated_at}-${item.subject}-${item.level}-${idx}`}
                      className="kid-card p-4"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2 mb-1">
                            <span className="font-bold text-navy-dark">
                              {subjectJa(item.subject)}
                            </span>
                            <span className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full">
                              Lv.{item.level}
                            </span>
                            <span
                              className={cn(
                                'text-xs font-bold px-2 py-0.5 rounded-full border',
                                SCORE_TONE_CLASS[tone],
                              )}
                            >
                              {item.score}%
                            </span>
                          </div>
                          <p className="text-sm text-gray-600">
                            {new Date(item.updated_at).toLocaleString('ja-JP')}
                          </p>
                          {typeof item.gained_xp === 'number' && item.gained_xp > 0 && (
                            <p className="text-xs text-green-700 mt-1">
                              経験値 +{item.gained_xp}
                            </p>
                          )}
                        </div>
                        <Button
                          size="sm"
                          className="rounded-full shrink-0"
                          onClick={() => navigate(quizRetryPath(item))}
                        >
                          <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                          {retryLabel(item)}
                        </Button>
                      </div>
                    </Card>
                  );
                })}
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
};

export default History;
