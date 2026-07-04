import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getAuth, onAuthStateChanged } from 'firebase/auth';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { LoggedOutCTA } from '@/components/LoggedOutCTA';
import { getApiBase } from '@/lib/apiBase';
import { subjectJa } from '@/lib/subjectJa';
import { ArrowLeft } from 'lucide-react';

interface HistoryItem {
  subject: string;
  level: number;
  score: number;
  updated_at: string;
  gained_xp?: number;
}

const History: React.FC = () => {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);

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
        const token = await user.getIdToken(true);
        const url = `${getApiBase()}/progress`;
        const res = await fetch(url, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const text = await res.text().catch(() => '');
        if (!res.ok) {
          throw new Error(`${res.status} ${text.slice(0, 200)}`);
        }
        const json = JSON.parse(text) as { items?: HistoryItem[] };
        const rows = Array.isArray(json.items) ? json.items : [];
        setHistory(rows);
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-lavender-light/40 via-white to-mint-light/40 p-4">
      <div className="max-w-4xl mx-auto space-y-4">
        {loggedIn === false && (
          <LoggedOutCTA
            title="学習履歴を見るにはログイン"
            description="履歴はサーバー（Heroku DB）に保存されます。ログイン後にホームからクイズに挑戦すると表示されます。"
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
              サーバー
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

            {loggedIn && history.length === 0 ? (
              <Card className="kid-card p-8 text-center text-gray-600">
                <p className="mb-4">まだサーバーに履歴がありません。ホームからクイズを始めよう。</p>
                <Button asChild className="kid-button">
                  <Link to="/">ホームへ</Link>
                </Button>
              </Card>
            ) : loggedIn ? (
              <Card className="kid-card overflow-x-auto">
                <table className="min-w-full text-sm md:text-base">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left px-4 py-3 font-semibold text-navy-dark">
                        科目
                      </th>
                      <th className="text-left px-4 py-3 font-semibold text-navy-dark">
                        Lv
                      </th>
                      <th className="text-left px-4 py-3 font-semibold text-navy-dark">
                        スコア %
                      </th>
                      <th className="text-left px-4 py-3 font-semibold text-navy-dark hidden sm:table-cell">
                        XP
                      </th>
                      <th className="text-left px-4 py-3 font-semibold text-navy-dark">
                        日時
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((item, idx) => (
                      <tr key={`${item.updated_at}-${idx}`} className="border-b border-gray-100">
                        <td className="px-4 py-3">{subjectJa(item.subject)}</td>
                        <td className="px-4 py-3">{item.level}</td>
                        <td className="px-4 py-3">{item.score}%</td>
                        <td className="px-4 py-3 hidden sm:table-cell text-gray-600">
                          {typeof item.gained_xp === 'number' ? `+${item.gained_xp}` : '—'}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          {new Date(item.updated_at).toLocaleString('ja-JP')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
};

export default History;
