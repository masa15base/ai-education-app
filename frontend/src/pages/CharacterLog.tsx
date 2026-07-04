import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAuth, onAuthStateChanged } from 'firebase/auth';
import { LoggedOutCTA } from '@/components/LoggedOutCTA';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ArrowLeft, Calendar, Star, TrendingUp } from 'lucide-react';
import {
  DEFAULT_CHARACTER,
  fetchCharacterFromServer,
  loadCharacter,
  levelFromExperience,
  progressInCurrentLevel,
  type CharacterState,
} from '@/lib/characterState';
import { fetchStatsSummary, type StatsTimelineItem } from '@/lib/statsApi';
import { subjectJa } from '@/lib/subjectJa';

type Row = {
  key: string;
  atMs: number;
  dateShort: string;
  level: number;
  scorePct: number;
  subjectRaw: string;
};

function serverTimelineToRows(server: StatsTimelineItem[]): Row[] {
  return server
    .map((s) => {
      const atMs = Date.parse(s.created_at);
      if (Number.isNaN(atMs)) return null;
      return {
        key: `${s.created_at}-${s.subject}-${s.level}`,
        atMs,
        dateShort: new Date(s.created_at).toLocaleDateString('ja-JP'),
        level: s.level,
        scorePct: Math.round(s.score),
        subjectRaw: s.subject,
      } as Row;
    })
    .filter((x): x is Row => x !== null)
    .sort((a, b) => b.atMs - a.atMs);
}

const CharacterLog = () => {
  const navigate = useNavigate();
  const [character, setCharacter] = useState<CharacterState>(() => loadCharacter());
  const level = levelFromExperience(character.experience);
  const xpBar = progressInCurrentLevel(character.experience);
  const xpToNext = Math.max(0, 100 - xpBar);

  const [serverTimeline, setServerTimeline] = useState<StatsTimelineItem[]>([]);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);

  useEffect(() => {
    const unsub = onAuthStateChanged(getAuth(), (u) => setLoggedIn(!!u));
    return () => unsub();
  }, []);

  useEffect(() => {
    void fetchCharacterFromServer().then(() => setCharacter(loadCharacter()));
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const user = getAuth().currentUser;
        const token = user ? await user.getIdToken() : null;
        const sum = await fetchStatsSummary(token, 50);
        if (!cancelled) {
          setServerTimeline(sum.timeline || []);
          setStatsError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setServerTimeline([]);
          setStatsError(e instanceof Error ? e.message : String(e));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const growthHistory = useMemo(
    () => serverTimelineToRows(serverTimeline),
    [serverTimeline],
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-kid-pink/30 via-kid-blue/20 to-kid-yellow/20 p-4">
      <div className="flex items-center mb-6">
        <Button
          onClick={() => navigate('/')}
          variant="ghost"
          size="sm"
          className="mr-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          戻る
        </Button>
        <h1 className="text-3xl font-bold text-kid-purple">
          {character.displayName || DEFAULT_CHARACTER.displayName}の成長記録
        </h1>
      </div>

      <div className="max-w-4xl mx-auto">
        {loggedIn === false && (
          <div className="mb-4">
            <LoggedOutCTA
              title="クラウドの成長タイムラインを見るにはログイン"
              description="ログインするとサーバー（Heroku DB）に保存されたクイズ履歴が表示されます。"
            />
          </div>
        )}
        {statsError && (
          <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 mb-4">
            サーバーの履歴は読み込めませんでした: {statsError}
          </p>
        )}

        <Card className="kid-card mb-6 text-center">
          {character.imageUrl ? (
            <img
              src={character.imageUrl}
              alt={character.displayName}
              className="w-48 h-48 mx-auto mb-4 object-contain rounded-2xl"
            />
          ) : (
            <div className="text-8xl mb-4 animate-bounce-gentle">😺</div>
          )}
          <h2 className="text-2xl font-bold text-kid-purple mb-2">
            現在の{character.displayName}
          </h2>
          <div className="flex justify-center items-center gap-4 text-lg">
            <div className="flex items-center">
              <Star className="h-5 w-5 text-kid-yellow mr-1" />
              <span>レベル {level}</span>
            </div>
            <div className="flex items-center">
              <TrendingUp className="h-5 w-5 text-kid-green mr-1" />
              <span>
                経験値 {xpBar}/100（次のレベルまであと {xpToNext}）
              </span>
            </div>
          </div>
        </Card>

        <div className="space-y-4">
          <h3 className="text-xl font-bold text-kid-purple mb-4 flex items-center">
            <Calendar className="h-6 w-6 mr-2" />
            クイズの記録（サーバー）
          </h3>

          {growthHistory.length === 0 ? (
            <Card className="kid-card text-center py-12 text-gray-600">
              まだクイズの履歴がありません。ホームからクイズに挑戦してみよう！
            </Card>
          ) : (
            growthHistory.map((entry) => (
              <Card key={entry.key} className="kid-card">
                <div className="flex flex-col md:flex-row items-center gap-6">
                  <div className="text-center">
                    <div className="text-sm text-gray-600 mb-1">{entry.dateShort}</div>
                    <div className="bg-kid-yellow rounded-full px-3 py-1 text-sm font-bold">
                      Lv.{entry.level}
                    </div>
                    <div className="text-xs text-gray-500 mt-2">クラウド</div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-4xl" aria-hidden>
                      📚
                    </div>
                    <div className="text-2xl text-kid-purple">→</div>
                    <div className="text-4xl" aria-hidden>
                      🎉
                    </div>
                  </div>

                  <div className="flex-1 text-center md:text-left">
                    <h4 className="font-bold text-kid-purple mb-2">
                      {subjectJa(entry.subjectRaw)} のクイズを {entry.scorePct}% でクリア
                    </h4>
                    <div className="text-sm text-gray-600">
                      教科: {subjectJa(entry.subjectRaw)} ／ 難易度レベル {entry.level}
                    </div>
                  </div>

                  <div className="text-center">
                    <div className="text-2xl mb-1">⭐</div>
                    <div className="text-xs text-kid-green font-bold">おつかれ！</div>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>

        <Card className="kid-card mt-6 text-center">
          <h3 className="text-lg font-bold text-kid-purple mb-4">次の成長まで</h3>
          <div className="text-4xl mb-2">🎯</div>
          <p className="text-gray-600 mb-4">
            次のレベルまで、あと <span className="font-bold text-kid-purple">{xpToNext}</span>{' '}
            の経験値が必要だよ！
            <br />
            クイズや歩数ボーナスで経験値がたまるよ。
          </p>
          <Button onClick={() => navigate('/quiz')} className="kid-button">
            今すぐクイズに挑戦！
          </Button>
        </Card>
      </div>
    </div>
  );
};

export default CharacterLog;
