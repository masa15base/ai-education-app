import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { getAuth, onAuthStateChanged, signOut } from 'firebase/auth';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import { Star, Camera, User, Edit2, Check, X } from 'lucide-react';
import { toast } from '@/hooks/use-toast';
import {
  DEFAULT_CHARACTER,
  fetchCharacterFromServer,
  loadCharacter,
  levelFromExperience,
  patchCharacter,
  progressInCurrentLevel,
  pushCharacterToServer,
  setCharacterMemory,
  type CharacterState,
} from '@/lib/characterState';
import { characterVisualTier, DEFAULT_STEPS_GOAL } from '@/lib/growthRules';
import { cn } from '@/lib/utils';
import { fetchQuizSessionToday } from '@/lib/cloudQuizApi';
import { postSyncStepsXp } from '@/lib/api';
import { fetchStepsToday, putStepsToday } from '@/lib/stepsApi';
import {
  fetchCharacterGrowthStatus,
  HOME_ACTION_ANIM,
  STAGE_EMOJI,
  type CharacterGrowthStatus,
} from '@/lib/characterStatusApi';

const Index = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [character, setCharacter] = useState<CharacterState>(() =>
    loadCharacter(),
  );
  const [imgBroken, setImgBroken] = useState(false);
  /** サーバ歩数・クイズ状態の再取得トリガー */
  const [uiTick, setUiTick] = useState(0);
  const [isEditingName, setIsEditingName] = useState(false);
  const [tempName, setTempName] = useState(character.displayName);
  const [authHint, setAuthHint] = useState<string | null>(null);
  const [stepsGoal, setStepsGoal] = useState(DEFAULT_STEPS_GOAL);
  const [todaySteps, setTodaySteps] = useState(0);
  const [pullSettled, setPullSettled] = useState(false);
  const [quizToday, setQuizToday] = useState<{
    has_session_today: boolean;
    latest: {
      subject: string;
      level: number;
      score: number;
      gained_xp: number;
      updated_at: string;
    } | null;
  } | null>(null);
  const [growthStatus, setGrowthStatus] = useState<CharacterGrowthStatus | null>(
    null,
  );

  const characterLevel =
    growthStatus?.level ?? levelFromExperience(character.experience);
  const xpIntoLevel =
    growthStatus?.exp_in_level ??
    progressInCurrentLevel(character.experience);
  const experienceToNext =
    growthStatus?.exp_to_next ?? 100 - xpIntoLevel;
  const growthStage = growthStatus?.stage ?? (character.imageUrl ? 'baby' : 'egg');
  const growthStageLabel =
    growthStatus?.stage_label ??
    (growthStage === 'egg' ? 'たまご' : growthStage);
  const homeAction = growthStatus?.home_action ?? 'idle';
  const homeAnim =
    HOME_ACTION_ANIM[homeAction] ?? HOME_ACTION_ANIM.idle;
  const buddyMessage =
    growthStatus?.message ?? '今日も一緒にチャレンジしよう！';
  const heroPreviewUrl =
    growthStatus?.final_hero_preview ??
    growthStatus?.hero_preview_url ??
    character.heroPreviewUrl ??
    null;
  const nextPreviewUrl =
    growthStatus?.next_stage_preview_url ??
    character.nextEvolutionPreviewUrl ??
    null;
  const nextStageName = String(
    growthStatus?.next_evolution?.next_stage ?? '',
  );

  useEffect(() => {
    void (async () => {
      try {
        const ok = await fetchCharacterFromServer();
        if (ok) setCharacter(loadCharacter());
      } finally {
        setPullSettled(true);
      }
    })();
  }, []);

  useEffect(() => {
    const st = location.state as { characterUpdated?: boolean; displayName?: string } | null;
    if (!st?.characterUpdated) return;
    void (async () => {
      await fetchCharacterFromServer();
      setCharacter(loadCharacter());
      setImgBroken(false);
      if (st.displayName) {
        toast({
          title: `${st.displayName} がホームに登場！`,
          description: '作ったキャラを上に表示しています',
        });
      }
      navigate(location.pathname, { replace: true, state: {} });
    })();
  }, [location.state, location.pathname, navigate]);

  const syncStepsFromServerIfAuthed = useCallback(async () => {
    const u = getAuth().currentUser;
    if (!u) return;
    try {
      const token = await u.getIdToken();
      const snap = await fetchStepsToday(token);
      if (snap.authenticated && typeof snap.steps === 'number') {
        setTodaySteps(snap.steps);
        if (
          typeof snap.goal_steps === 'number' &&
          snap.goal_steps >= 1000
        ) {
          setStepsGoal(snap.goal_steps);
        }
        setUiTick((x) => x + 1);
      }
    } catch {
      /* 同期失敗はホーム表示を阻害しない */
    }
  }, []);

  useEffect(() => {
    const unsub = onAuthStateChanged(getAuth(), (user) => {
      if (!user) {
        setAuthHint(null);
        setTodaySteps(0);
        setQuizToday(null);
        return;
      }
      const label =
        user.displayName?.trim() ||
        user.email?.trim() ||
        `UID ${user.uid.slice(0, 6)}…`;
      setAuthHint(label);
      void syncStepsFromServerIfAuthed();
    });
    return () => unsub();
  }, [syncStepsFromServerIfAuthed]);

  useEffect(() => {
    const bump = () => {
      setUiTick((t) => t + 1);
      void syncStepsFromServerIfAuthed();
    };
    document.addEventListener('visibilitychange', bump);
    window.addEventListener('focus', bump);
    return () => {
      document.removeEventListener('visibilitychange', bump);
      window.removeEventListener('focus', bump);
    };
  }, [syncStepsFromServerIfAuthed]);

  useEffect(() => {
    setImgBroken(false);
  }, [character.imageUrl]);

  useEffect(() => {
    void uiTick;
    if (!authHint) {
      setQuizToday(null);
      return;
    }
    void fetchQuizSessionToday().then(setQuizToday);
    void fetchCharacterGrowthStatus().then(setGrowthStatus);
  }, [authHint, uiTick]);

  /** 歩数ボーナス XP（サーバー DB で冪等） */
  useEffect(() => {
    if (!pullSettled || !authHint) return;
    let cancelled = false;
    void (async () => {
      try {
        const res = await postSyncStepsXp(stepsGoal);
        if (cancelled || res.xp_gained <= 0) return;
        await fetchCharacterFromServer();
        if (!cancelled) setCharacter(loadCharacter());
        toast({
          title: `歩数ボーナス +${res.xp_gained} XP`,
          description: res.detail.join(' · '),
          duration: 3200,
        });
      } catch {
        /* DB 未設定や未ログイン時は無視 */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [pullSettled, uiTick, stepsGoal, authHint]);

  const hasQuizToday = quizToday?.has_session_today ?? false;
  const todayQuizSnap = quizToday?.latest
    ? {
        at: quizToday.latest.updated_at,
        gainedXp: quizToday.latest.gained_xp,
        scorePercent: quizToday.latest.score,
        subject: quizToday.latest.subject,
        level: quizToday.latest.level,
      }
    : null;

  const stepsToGoal = Math.max(0, stepsGoal - todaySteps);
  const isStepsGoalReached = todaySteps >= stepsGoal;

  const handleViewProgress = () => {
    navigate('/character-log');
  };

  const handleParentMode = () => {
    navigate('/parent-dashboard');
  };

  const handleLogout = async () => {
    try {
      await signOut(getAuth());
      setCharacterMemory(null);
      setCharacter({ ...DEFAULT_CHARACTER });
      setTodaySteps(0);
      setQuizToday(null);
      toast({ title: 'ログアウトしました' });
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      toast({
        title: 'ログアウトに失敗しました',
        description: msg,
        variant: 'destructive',
      });
    }
  };

  const handleEditName = () => {
    setTempName(character.displayName);
    setIsEditingName(true);
  };

  const handleSaveName = () => {
    if (!tempName.trim()) return;
    const next = patchCharacter({ displayName: tempName.trim() });
    setCharacter(next);
    setIsEditingName(false);
    void pushCharacterToServer(next);
    toast({
      title: '名前を変更しました！',
      description: `キャラクターの名前が「${tempName.trim()}」になりました`,
    });
  };

  const handleCancelEdit = () => {
    setTempName(character.displayName);
    setIsEditingName(false);
  };

  const displayName = character.displayName || DEFAULT_CHARACTER.displayName;

  return (
    <div className="min-h-screen bg-gradient-to-br from-lavender-soft via-mint-soft to-sky-soft p-4">
      <div className="flex justify-between items-center mb-6 flex-wrap gap-2">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-lavender-soft to-sky-soft bg-clip-text text-transparent">
          まなとも
        </h1>
        <div className="flex flex-col items-end gap-1">
          {authHint && (
            <span className="text-xs text-navy-dark/70 max-w-[14rem] truncate" title={authHint}>
              ログイン中: {authHint}
            </span>
          )}
          <div className="flex flex-wrap gap-2 justify-end">
            {authHint ? (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="rounded-full"
                onClick={() => void handleLogout()}
              >
                ログアウト
              </Button>
            ) : (
              <Button variant="outline" size="sm" asChild className="rounded-full">
                <Link to="/login">ログイン</Link>
              </Button>
            )}
            <Button
              onClick={handleParentMode}
              className="kid-button py-2 px-4 text-sm"
            >
              <User className="h-4 w-4 mr-2" />
              保護者モード
            </Button>
            <Button variant="outline" size="sm" asChild className="rounded-full text-xs">
              <Link to="/connection-test">接続テスト</Link>
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto space-y-8">
        <Card className="kid-card text-center relative overflow-hidden">
          <div className="flex flex-wrap justify-center gap-2 mb-3">
            <span className="rounded-full bg-lavender-soft/40 px-3 py-1 text-sm font-bold text-navy-dark">
              {STAGE_EMOJI[growthStage] ?? '✨'} {growthStageLabel}
            </span>
            {growthStatus?.mood && (
              <span className="rounded-full bg-mint-soft/50 px-3 py-1 text-xs text-navy-dark">
                mood: {growthStatus.mood}
              </span>
            )}
          </div>
          <p className="text-lg font-bold text-navy-dark mb-4 px-2">{buddyMessage}</p>
          <div className="character-display w-64 h-64 mx-auto mb-6 flex items-center justify-center relative">
            {homeAction === 'studying' && (
              <span className="absolute top-2 left-4 text-2xl animate-pulse-gentle z-10">
                📕
              </span>
            )}
            {homeAction === 'studying' && (
              <span className="absolute top-4 right-4 text-2xl animate-pulse-gentle z-10">
                ✏️
              </span>
            )}
            {homeAction === 'celebrating' && (
              <>
                <span className="absolute top-1 left-6 text-xl animate-wiggle z-10">
                  ✨
                </span>
                <span className="absolute top-3 right-6 text-xl animate-wiggle z-10">
                  ⭐
                </span>
              </>
            )}
            {homeAction === 'sleeping' && (
              <span className="absolute top-2 right-6 text-lg font-bold text-sky-soft z-10 animate-pulse-gentle">
                Zzz
              </span>
            )}
            <div
              className={cn(
                'flex items-center justify-center transition-transform duration-500 ease-out',
                homeAnim,
                characterVisualTier(characterLevel) === 1 && 'scale-[0.92]',
                characterVisualTier(characterLevel) === 2 &&
                  'scale-100 drop-shadow-md',
                characterVisualTier(characterLevel) === 3 &&
                  'scale-105 drop-shadow-lg ring-4 ring-amber-200/70 rounded-3xl p-1',
              )}
            >
              {character.imageUrl && !imgBroken ? (
                <img
                  src={character.imageUrl}
                  alt={displayName}
                  className="max-h-full max-w-full object-contain rounded-2xl shadow-inner image-rendering-pixelated"
                  style={{ imageRendering: 'pixelated' }}
                  onError={() => setImgBroken(true)}
                />
              ) : (
                <div className="text-8xl select-none">
                  {STAGE_EMOJI[growthStage] ?? '🥚'}
                </div>
              )}
            </div>
            <div className="level-badge">Lv.{characterLevel}</div>
          </div>

          <div className="mb-4">
            {!isEditingName ? (
              <div className="flex items-center justify-center gap-2">
                <h2 className="text-3xl font-bold text-navy-dark">
                  {displayName}
                </h2>
                <Button onClick={handleEditName} variant="ghost" size="sm">
                  <Edit2 className="h-4 w-4 text-gray-500" />
                </Button>
              </div>
            ) : (
              <div className="flex items-center justify-center gap-2 max-w-xs mx-auto">
                <Input
                  value={tempName}
                  onChange={(e) => setTempName(e.target.value)}
                  className="text-center text-xl font-bold border-2 border-sky-soft/30 focus:border-sky-soft rounded-2xl"
                  placeholder="キャラクター名"
                  maxLength={10}
                />
                <Button onClick={handleSaveName} variant="ghost" size="sm">
                  <Check className="h-4 w-4 text-green-500" />
                </Button>
                <Button onClick={handleCancelEdit} variant="ghost" size="sm">
                  <X className="h-4 w-4 text-gray-400" />
                </Button>
              </div>
            )}
          </div>

          <div className="mb-6">
            <Button onClick={handleViewProgress} className="kid-button py-2 px-4">
              <Star className="h-4 w-4 mr-2" />
              {displayName}の成長記録を見る
            </Button>
          </div>

          <div className="mb-6">
            <div className="flex justify-between text-lg mb-3 text-navy-dark">
              <span className="font-bold">経験値（EXP）</span>
              <span className="font-bold">{xpIntoLevel}/100</span>
            </div>
            <div className="relative bg-gray-200 rounded-full h-4 overflow-hidden">
              <div
                className="experience-bar rounded-full"
                style={{ width: `${xpIntoLevel}%` }}
              ></div>
            </div>
            <p className="text-lg font-bold text-lavender-soft mt-2">
              レベルアップまであと{experienceToNext} EXP！
            </p>
          </div>

          {(heroPreviewUrl || nextPreviewUrl) && (
            <div className="mb-5 rounded-2xl bg-gradient-to-r from-amber-50 to-lavender-soft/30 p-4 border border-amber-200/60">
              <p className="text-sm font-bold text-navy-dark mb-3">
                🎮 進化ロードマップ — ここまで育てよう！
              </p>
              <div className="flex justify-center items-end gap-3 flex-wrap">
                <div className="text-center">
                  <p className="text-xs text-gray-600 mb-1">いま</p>
                  {character.imageUrl && !imgBroken ? (
                    <img
                      src={character.imageUrl}
                      alt="現在"
                      className="h-16 w-16 object-contain bg-white rounded-lg border-2 border-mint-soft"
                      style={{ imageRendering: 'pixelated' }}
                    />
                  ) : (
                    <span className="text-3xl">{STAGE_EMOJI[growthStage]}</span>
                  )}
                </div>
                {nextPreviewUrl && (
                  <>
                    <span className="text-xl text-lavender-soft">→</span>
                    <div className="text-center">
                      <p className="text-xs text-gray-600 mb-1">
                        次{nextStageName ? `（${nextStageName}）` : ''}
                      </p>
                      <img
                        src={nextPreviewUrl}
                        alt="次の進化"
                        className="h-16 w-16 object-contain bg-white rounded-lg border-2 border-sky-soft/50 opacity-90"
                        style={{ imageRendering: 'pixelated' }}
                      />
                    </div>
                  </>
                )}
                {heroPreviewUrl && (
                  <>
                    <span className="text-xl text-amber-400">→</span>
                    <div className="text-center">
                      <p className="text-xs font-bold text-amber-700 mb-1">
                        ヒーロー
                      </p>
                      <img
                        src={heroPreviewUrl}
                        alt="最終進化"
                        className="h-20 w-20 object-contain bg-white rounded-lg border-2 border-amber-300 shadow-sm"
                        style={{ imageRendering: 'pixelated' }}
                      />
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {growthStatus && !growthStatus.next_evolution?.complete && (
            <div className="mb-4 rounded-2xl bg-sky-soft/30 p-4 text-left text-sm text-navy-dark">
              <p className="font-bold mb-2">進化ゲージ</p>
              <p className="font-bold mb-2">
                次の進化:{' '}
                {String(growthStatus.next_evolution?.next_stage ?? '—')}
              </p>
              <ul className="space-y-1 list-disc list-inside">
                {(typeof growthStatus.next_evolution?.remaining_exp ===
                  'number' ||
                  typeof growthStatus.next_evolution
                    ?.remaining_character_exp === 'number') && (
                  <li>
                    EXP あと{' '}
                    {Number(
                      growthStatus.next_evolution.remaining_exp ??
                        growthStatus.next_evolution.remaining_character_exp,
                    )}{' '}
                    （必要{' '}
                    {growthStatus.next_evolution.required_exp ??
                      growthStatus.next_evolution.required_character_exp}
                    ）
                  </li>
                )}
                {typeof growthStatus.next_evolution
                  ?.remaining_quiz_correct_count === 'number' && (
                  <li>
                    クイズ正解 あと{' '}
                    {growthStatus.next_evolution.remaining_quiz_correct_count}
                    問
                  </li>
                )}
                {typeof growthStatus.next_evolution?.remaining_total_steps ===
                  'number' && (
                  <li>
                    累計歩数 あと{' '}
                    {Number(
                      growthStatus.next_evolution.remaining_total_steps,
                    ).toLocaleString()}
                    歩
                  </li>
                )}
              </ul>
            </div>
          )}

          {growthStatus && (
            <div className="grid grid-cols-2 gap-2 text-xs text-navy-dark/90 mb-2">
              <div className="rounded-xl bg-mint-soft/30 p-2">
                <p className="font-bold">きょうのクイズ</p>
                <p>{growthStatus.quiz_today ? '挑戦済み ✓' : 'まだだよ'}</p>
                <p>正解 {growthStatus.quiz_correct_count} 問</p>
              </div>
              <div className="rounded-xl bg-lavender-soft/30 p-2">
                <p className="font-bold">きょうの歩数</p>
                <p>{growthStatus.daily_steps.toLocaleString()} 歩</p>
                <p>累計 {growthStatus.total_steps.toLocaleString()} 歩</p>
              </div>
            </div>
          )}
        </Card>

        <Card className="kid-card text-center">
          <div className="text-6xl mb-4 animate-wiggle">💬</div>
          <h3 className="text-2xl font-bold text-navy-dark mb-4">
            {displayName}が話しかけてるよ！
          </h3>
          <Button onClick={() => navigate('/chat')} className="chat-bubble">
            おはなしする 💫
          </Button>
          <p className="text-gray-600 mt-4 text-lg">{buddyMessage}</p>
        </Card>

        <Card className="kid-card text-center">
          <div className="text-4xl mb-4">🧮</div>
          <h3 className="text-2xl font-bold text-navy-dark mb-4">
            今日のクイズ
          </h3>
          <p className="text-lg text-navy-dark mb-4 font-bold">
            何回でも挑戦できるよ！{displayName}を成長させよう
          </p>
          {hasQuizToday && todayQuizSnap && (
            <div className="bg-gradient-to-r from-lavender-soft/40 to-mint-soft/40 rounded-2xl p-3 mb-4 text-sm text-navy-dark">
              <p className="font-semibold">きょうの直近クイズ</p>
              <p>
                {todayQuizSnap.subject === 'english' ? '英語' : '算数'} L
                {todayQuizSnap.level} · 正答率 {todayQuizSnap.scorePercent}%
                {todayQuizSnap.gainedXp != null && todayQuizSnap.gainedXp > 0
                  ? ` · +${Math.round(todayQuizSnap.gainedXp)} XP`
                  : ''}
              </p>
            </div>
          )}
          <div className="flex flex-col md:flex-row justify-center gap-4">
            <Button
              onClick={() => navigate('/quiz?subject=math&level=1')}
              className="quiz-button text-xl py-6 px-10"
            >
              🧮 算数クイズ
            </Button>
            <Button
              onClick={() => navigate('/quiz?subject=english&level=1')}
              className="quiz-button text-xl py-6 px-10"
            >
              ✏️ 英語クイズ
            </Button>
          </div>
          <div className="mt-4">
            <Button variant="outline" size="sm" asChild className="rounded-full">
              <Link to="/history">学習履歴を一覧で見る</Link>
            </Button>
          </div>
          <p className="text-xs text-gray-500 mt-4">
            {authHint
              ? 'ログイン中はクイズのたびにサーバーへ記録されます。経験値には1日あたりの上限があります。'
              : 'ログインすると結果と経験値をクラウドに保存できます。'}
          </p>
        </Card>

        <Card className="kid-card text-center">
          <div className="text-4xl mb-4">👟</div>
          <h3 className="text-2xl font-bold text-navy-dark mb-4">今日の歩数</h3>
          <p className="text-xs text-gray-500 mb-2">
            {authHint
              ? '歩数はサーバー（Heroku / JawsDB）に保存されます（日付はサーバー UTC）。'
              : '歩数を記録するにはログインしてください。'}
            <span className="block mt-1 text-navy-dark/80">
              1000歩ごとに少し XP・目標達成でボーナス XP（きょう1日分）
            </span>
          </p>
          <div className="text-5xl font-bold text-sky-soft mb-4">
            {todaySteps.toLocaleString()}
          </div>
          {!isStepsGoalReached ? (
            <div>
              <p className="text-xl font-bold text-lavender-soft mb-4">
                あと{stepsToGoal.toLocaleString()}歩でごほうび！
              </p>
              <Progress
                value={Math.min(100, (todaySteps / stepsGoal) * 100)}
                className="h-4 bg-mint-soft/50 mb-4"
              />
              <div className="flex flex-wrap justify-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="rounded-full text-xs"
                  onClick={() => {
                    const u = getAuth().currentUser;
                    if (!u) return;
                    void (async () => {
                      const t = await u.getIdToken();
                      const next = Math.max(0, todaySteps - 300);
                      try {
                        const r = await putStepsToday(t, next);
                        setTodaySteps(r.steps);
                        setUiTick((x) => x + 1);
                      } catch {
                        /* ignore */
                      }
                    })();
                  }}
                >
                  −300（デモ）
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="rounded-full text-xs"
                  onClick={() => {
                    const u = getAuth().currentUser;
                    if (!u) return;
                    void (async () => {
                      const t = await u.getIdToken();
                      const next = todaySteps + 1000;
                      try {
                        const r = await putStepsToday(t, next);
                        setTodaySteps(r.steps);
                        setUiTick((x) => x + 1);
                      } catch {
                        /* ignore */
                      }
                    })();
                  }}
                >
                  +1000（デモ）
                </Button>
              </div>
            </div>
          ) : (
            <div className="bg-gradient-to-r from-mint-soft to-sky-soft rounded-2xl p-6">
              <div className="text-6xl mb-2">🏆</div>
              <p className="text-2xl font-bold text-navy-dark">目標達成！</p>
              <p className="text-lg text-gray-700">
                {displayName}が喜んでるよ！
              </p>
            </div>
          )}
        </Card>

        <Card className="kid-card text-center">
          <h3 className="text-2xl font-bold text-navy-dark mb-6">
            きみだけの新しいキャラをつくろう！
          </h3>
          <div className="steps-visual mb-6">
            <div className="text-center">
              <div className="text-4xl mb-2">✏️</div>
              <p className="text-sm font-bold text-navy-dark">描く</p>
            </div>
            <div className="text-2xl text-lavender-soft">→</div>
            <div className="text-center">
              <div className="text-4xl mb-2">📸</div>
              <p className="text-sm font-bold text-navy-dark">写真をとる</p>
            </div>
            <div className="text-2xl text-lavender-soft">→</div>
            <div className="text-center">
              <div className="text-4xl mb-2">✨</div>
              <p className="text-sm font-bold text-navy-dark">AIで進化！</p>
            </div>
          </div>
          <Button
            onClick={() => navigate('/upload')}
            className="kid-button w-full"
          >
            <Camera className="h-6 w-6 mr-3" />
            新しいキャラを作る
          </Button>
        </Card>
      </div>
    </div>
  );
};

export default Index;
