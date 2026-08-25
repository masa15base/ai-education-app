import { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getAuth } from 'firebase/auth';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { ArrowLeft, Check, Lightbulb, Star } from 'lucide-react';
import { toast } from '@/hooks/use-toast';
import { postQuizComplete } from '@/lib/api';
import { getApiBase } from '@/lib/apiBase';
import { fetchCharacterFromServer } from '@/lib/characterState';
import { ENGLISH_VOCAB, englishFourOptions, englishVocabRowIndex } from '@/lib/englishQuizDynamic';
import { ensureMathFourOptions, mathQuestionParts } from '@/lib/mathQuizDynamic';
import { subjectJa } from '@/lib/subjectJa';
import { cn } from '@/lib/utils';

interface Question {
  id: string;
  subject: string;
  level: number;
  question_text: string;
  options: string[];
  correct_answer: string;
  hint: string;
  media: {
    image_url: string | null;
    audio_url: string | null;
  };
}

type WrongReview = {
  question_text: string;
  selected: string;
  correct: string;
  hint: string;
};

const MAX_LEVEL = 10;

const Quiz = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const subjectParam = queryParams.get('subject');
  const levelParam = queryParams.get('level');
  const needsSetup = !subjectParam || !levelParam;

  const subject = (subjectParam || 'math').toLowerCase();
  const initialLevel = Math.min(
    MAX_LEVEL,
    Math.max(1, parseInt(levelParam || '1', 10) || 1),
  );

  const [pickSubject, setPickSubject] = useState<'math' | 'english'>(
    subject === 'english' ? 'english' : 'math',
  );
  const [pickLevel, setPickLevel] = useState(initialLevel);

  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [score, setScore] = useState(0);
  const [answers, setAnswers] = useState<number[]>([]);
  const [level, setLevel] = useState(initialLevel);
  const [levelHistory, setLevelHistory] = useState<number[]>([initialLevel]);
  const quizSubmittedRef = useRef(false);
  const [resultSummary, setResultSummary] = useState<{
    pct: number;
    gained: number;
    streakDays?: number;
  } | null>(null);
  const [answerRevealed, setAnswerRevealed] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [streak, setStreak] = useState(0);
  const [bestStreak, setBestStreak] = useState(0);
  const [wrongReviews, setWrongReviews] = useState<WrongReview[]>([]);
  const [practiceMode, setPracticeMode] = useState(false);
  const [feedbackAnim, setFeedbackAnim] = useState<'pop' | 'shake' | null>(null);

  useEffect(() => {
    if (subjectParam === 'english' || subjectParam === 'math') {
      setPickSubject(subjectParam);
    }
    if (levelParam) {
      const n = Math.min(MAX_LEVEL, Math.max(1, parseInt(levelParam, 10) || 1));
      setPickLevel(n);
      setLevel(n);
      setLevelHistory([n]);
    }
  }, [subjectParam, levelParam]);

  const updateLevelHistory = (newLevel: number) => {
    setLevelHistory((prev) =>
      prev[prev.length - 1] !== newLevel ? [...prev, newLevel] : prev,
    );
  };

  const buildSampleQuestions = (subj: string, lvl: number, n = 5) => {
    const arr: Question[] = [];
    for (let i = 1; i <= n; i++) {
      if (subj.toLowerCase() === 'math') {
        const m = mathQuestionParts(lvl, i);
        arr.push({
          id: `${subj.toLowerCase()}-${lvl}-${i}`,
          subject: subj,
          level: lvl,
          question_text: m.question_text,
          options: m.options,
          correct_answer: m.correct_answer,
          hint: m.hint,
          media: { image_url: null, audio_url: null },
        });
      } else {
        const pos = englishVocabRowIndex(lvl, i);
        const [wordEn, jpCorrect, threeOpts, hint] = ENGLISH_VOCAB[pos];
        arr.push({
          id: `${subj.toLowerCase()}-${lvl}-${i}`,
          subject: subj,
          level: lvl,
          question_text: `"${wordEn}" の意味はどれ？`,
          options: englishFourOptions(lvl, i, jpCorrect, threeOpts),
          correct_answer: jpCorrect,
          hint,
          media: { image_url: null, audio_url: null },
        });
      }
    }
    return arr;
  };

  const isStaleEnglishPayload = (rows: Question[]): boolean => {
    if (subject.toLowerCase() !== 'english') return false;
    const catOnly = rows.every(
      (q) =>
        q.question_text.includes("'猫'") ||
        (q.question_text.includes('猫') && q.options.some((o) => o === 'cat')),
    );
    const uniqueTexts = new Set(rows.map((q) => q.question_text));
    return catOnly || uniqueTexts.size <= 1;
  };

  const resetRoundState = () => {
    quizSubmittedRef.current = false;
    setCurrentQuestion(0);
    setSelectedAnswer(null);
    setAnswerRevealed(false);
    setShowHint(false);
    setScore(0);
    setShowResult(false);
    setAnswers([]);
    setStreak(0);
    setBestStreak(0);
    setWrongReviews([]);
    setFeedbackAnim(null);
    setResultSummary(null);
  };

  useEffect(() => {
    if (needsSetup) return;

    const url = `${getApiBase()}/questions?subject=${subject}&level=${level}`;
    fetch(url)
      .then(async (res) => {
        const text = await res.text();
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${text.slice(0, 200)}`);
        }
        try {
          return JSON.parse(text);
        } catch {
          throw new Error(`Invalid JSON: ${text.slice(0, 200)}`);
        }
      })
      .then((raw) => {
        const data: Question[] = Array.isArray(raw)
          ? raw
          : Array.isArray(raw?.items)
            ? raw.items
            : [];

        if (!Array.isArray(data) || data.length === 0) {
          toast({ title: '次のレベルの問題が見つかりません', variant: 'destructive' });
          return;
        }
        let finalData = data.slice(0, 5);
        if (subject.toLowerCase() === 'math') {
          finalData = finalData.map(ensureMathFourOptions);
        }
        if (isStaleEnglishPayload(finalData)) {
          finalData = buildSampleQuestions(subject, level, 5);
          toast({
            title: '英語問題を更新しました',
            description: '新しい動的問題で出題します',
            duration: 2500,
          });
        }
        setPracticeMode(false);
        resetRoundState();
        setQuestions(finalData);
      })
      .catch((err) => {
        console.error('問題の取得に失敗しました', err);
        const msg = String(err || '');
        if (msg.includes('HTTP 404')) {
          const samples = buildSampleQuestions(subject, level, 5);
          setPracticeMode(false);
          resetRoundState();
          setQuestions(samples);
          toast({
            title: 'サンプル問題で開始します',
            description: 'バックエンドの /api/questions が未デプロイのため代替を使用',
          });
          return;
        }
        toast({ title: '問題の取得に失敗しました', description: msg, variant: 'destructive' });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset helpers stable per render
  }, [needsSetup, subject, level]);

  useEffect(() => {
    if (!showResult) {
      if (!practiceMode) {
        quizSubmittedRef.current = false;
      }
      if (!practiceMode) setResultSummary(null);
    }
  }, [showResult, practiceMode]);

  useEffect(() => {
    if (!showResult || questions.length === 0) return;
    if (answers.length !== questions.length) return;
    if (practiceMode) {
      setResultSummary((prev) => prev ?? { pct: Math.round((score / questions.length) * 100), gained: 0 });
      return;
    }
    if (quizSubmittedRef.current) return;
    quizSubmittedRef.current = true;

    const pct = questions.length ? Math.round((score / questions.length) * 100) : 0;
    const payload = {
      subject,
      level,
      answers: questions.map((q, i) => ({
        question_index: i + 1,
        question_id: q.id,
        selected_answer: q.options[answers[i]],
      })),
    };

    void (async () => {
      try {
        const auth = getAuth();
        const user = auth.currentUser;
        const token = user ? await user.getIdToken() : undefined;
        const res = await postQuizComplete(payload, token);
        const growthXp =
          typeof res.growth?.exp_gained === 'number' ? res.growth.exp_gained : 0;
        const progressXp =
          typeof res.gained_xp === 'number' ? res.gained_xp : 0;
        // 一本化後は gained_xp（progress / 日次上限）が正。growth は同値ミラー。
        const gained = progressXp > 0 ? progressXp : growthXp;
        setResultSummary({ pct, gained });

        if (res.saved) {
          await fetchCharacterFromServer();
          if (gained > 0) {
            toast({
              title: `${gained} 経験値をゲット！`,
              description: 'クラウドに保存したよ',
              duration: 2200,
            });
          } else {
            toast({
              title: '記録したよ！',
              description: 'きょうのクイズ経験値は上限（80）に達しているかも',
              duration: 2200,
            });
          }
        } else {
          toast({
            title: 'クイズ完了！',
            description: 'ログインすると結果と経験値をクラウドに保存できるよ',
            duration: 2800,
          });
        }
      } catch (e) {
        console.error(e);
        setResultSummary({ pct, gained: 0 });
        toast({
          title: 'サーバーへの結果送信に失敗',
          description: '通信を確認してね',
          variant: 'destructive',
        });
      }
    })();
  }, [showResult, questions, answers, subject, level, score, practiceMode]);

  const handleAnswerSelect = (answerIndex: number) => {
    if (answerRevealed) return;
    setSelectedAnswer(answerIndex);
    setAnswerRevealed(true);
    const q = questions[currentQuestion];
    const ok = q.options[answerIndex]?.trim() === q.correct_answer.trim();
    setFeedbackAnim(ok ? 'pop' : 'shake');
    if (ok) {
      setStreak((s) => {
        const next = s + 1;
        setBestStreak((b) => Math.max(b, next));
        return next;
      });
    } else {
      setStreak(0);
    }
  };

  const handleNextQuestion = () => {
    if (selectedAnswer === null) return;
    const currentQ = questions[currentQuestion];
    const selectedValue = currentQ.options[selectedAnswer];
    const isCorrect = selectedValue.trim() === currentQ.correct_answer.trim();

    if (isCorrect) {
      setScore((s) => s + 1);
    } else {
      setWrongReviews((prev) => [
        ...prev,
        {
          question_text: currentQ.question_text,
          selected: selectedValue,
          correct: currentQ.correct_answer,
          hint: currentQ.hint || '',
        },
      ]);
    }

    setAnswers((prev) => [...prev, selectedAnswer]);

    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion((i) => i + 1);
      setSelectedAnswer(null);
      setAnswerRevealed(false);
      setShowHint(false);
      setFeedbackAnim(null);
    } else {
      setShowResult(true);
    }
  };

  const goToLevel = (next: number) => {
    setLevel(next);
    updateLevelHistory(next);
    setPracticeMode(false);
    resetRoundState();
    navigate(`/quiz?subject=${subject}&level=${next}`);
  };

  const handleNextLevel = () => {
    if (score < questions.length) {
      toast({
        title: '全問正解で次のレベルに進めます',
        description: 'もう一度挑戦してみましょう',
      });
      return;
    }
    if (level < MAX_LEVEL) {
      goToLevel(level + 1);
      toast({ title: `レベル ${level + 1} に進みました！` });
    } else {
      toast({ title: 'レベル上限です', description: 'これ以上のレベルはありません' });
    }
  };

  const handlePrevLevel = () => {
    if (level > 1) {
      goToLevel(level - 1);
      toast({ title: `レベル ${level - 1} に戻りました` });
    } else {
      toast({ title: 'レベル1です', description: 'これ以上下のレベルはありません' });
    }
  };

  const handleRetryWrongs = () => {
    if (wrongReviews.length === 0) return;
    const texts = new Set(wrongReviews.map((w) => w.question_text));
    const retryQs = questions.filter((q) => texts.has(q.question_text));
    if (retryQs.length === 0) return;
    setPracticeMode(true);
    quizSubmittedRef.current = true;
    setQuestions(retryQs);
    setWrongReviews([]);
    setCurrentQuestion(0);
    setSelectedAnswer(null);
    setAnswerRevealed(false);
    setShowHint(false);
    setScore(0);
    setAnswers([]);
    setStreak(0);
    setBestStreak(0);
    setShowResult(false);
    setFeedbackAnim(null);
    toast({
      title: 'まちがえた問題だけもう一度！',
      description: '練習モード（経験値なし）',
    });
  };

  const startFromPicker = () => {
    navigate(`/quiz?subject=${pickSubject}&level=${pickLevel}`);
  };

  const currentIsCorrect = useMemo(() => {
    if (selectedAnswer === null || !questions[currentQuestion]) return false;
    return (
      questions[currentQuestion].options[selectedAnswer]?.trim() ===
      questions[currentQuestion].correct_answer.trim()
    );
  }, [selectedAnswer, questions, currentQuestion]);

  if (needsSetup) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-lavender-light via-mint-light to-sky-light p-4">
        <div className="flex items-center mb-6">
          <Button
            onClick={() => navigate('/')}
            variant="ghost"
            size="sm"
            className="text-navy-dark hover:bg-lavender-soft/20 rounded-full"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            戻る
          </Button>
        </div>
        <Card className="kid-card max-w-lg mx-auto text-center">
          <div className="text-5xl mb-3">🎯</div>
          <h2 className="text-2xl font-bold text-navy-dark mb-2">クイズを選ぼう</h2>
          <p className="text-gray-600 mb-6">教科とレベルをえらんでスタート！</p>

          <p className="font-bold text-navy-dark mb-2">教科</p>
          <div className="flex gap-3 justify-center mb-6">
            <Button
              type="button"
              onClick={() => setPickSubject('math')}
              className={cn(
                'text-lg px-6 py-5 rounded-2xl',
                pickSubject === 'math'
                  ? 'bg-sky-soft text-white'
                  : 'bg-white text-navy-dark border-2',
              )}
            >
              🧮 算数
            </Button>
            <Button
              type="button"
              onClick={() => setPickSubject('english')}
              className={cn(
                'text-lg px-6 py-5 rounded-2xl',
                pickSubject === 'english'
                  ? 'bg-sky-soft text-white'
                  : 'bg-white text-navy-dark border-2',
              )}
            >
              ✏️ 英語
            </Button>
          </div>

          <p className="font-bold text-navy-dark mb-2">レベル（1〜{MAX_LEVEL}）</p>
          <div className="flex flex-wrap gap-2 justify-center mb-8">
            {Array.from({ length: MAX_LEVEL }, (_, i) => i + 1).map((n) => (
              <Button
                key={n}
                type="button"
                size="sm"
                onClick={() => setPickLevel(n)}
                className={cn(
                  'w-10 h-10 rounded-full font-bold',
                  pickLevel === n
                    ? 'bg-lavender-soft text-white'
                    : 'bg-white text-navy-dark border',
                )}
              >
                {n}
              </Button>
            ))}
          </div>

          <Button onClick={startFromPicker} className="quiz-button w-full">
            {subjectJa(pickSubject)} レベル {pickLevel} をはじめる
          </Button>
        </Card>
      </div>
    );
  }

  if (showResult) {
    const levelPath = levelHistory.join(' → ');

    return (
      <div className="min-h-screen bg-gradient-to-br from-lavender-light via-mint-light to-sky-light p-4 flex items-center justify-center">
        <Card className="kid-card max-w-md w-full text-center">
          <div className="text-6xl mb-4 quiz-pop">🎉</div>
          <h2 className="text-2xl font-bold text-navy-dark mb-2">
            {practiceMode ? '練習完了！' : 'クイズ完了！'}
          </h2>
          <div className="text-4xl font-bold text-sky-soft mb-2">
            {score}/{questions.length}
          </div>
          <p className="text-gray-600 mb-1">問正解しました！</p>
          <p className="text-sm text-navy-dark mb-1">
            {subjectJa(subject)} · レベル {level}
          </p>
          <p className="text-sm text-navy-dark mb-2">レベル履歴: {levelPath}</p>
          <p className="text-sm font-bold text-orange-600 mb-4">
            連続正解ベスト {bestStreak} 問
          </p>

          {!practiceMode && (
            <div className="bg-gradient-to-r from-mint-light to-sky-light rounded-2xl p-4 mb-4">
              <Star className="h-8 w-8 text-lavender-soft mx-auto mb-2" />
              <p className="font-bold text-navy-dark">
                経験値 +{resultSummary?.gained ?? '—'} ゲット！
              </p>
              {resultSummary != null && (
                <p className="text-sm text-gray-700 mt-1">正答率 {resultSummary.pct}%</p>
              )}
            </div>
          )}
          {practiceMode && (
            <p className="text-sm text-gray-600 mb-4">練習モードのため経験値はつきません</p>
          )}

          {wrongReviews.length > 0 && (
            <div className="text-left bg-red-50 border border-red-100 rounded-2xl p-4 mb-4">
              <p className="font-bold text-red-800 mb-2 text-center">
                まちがえた問題（{wrongReviews.length}）
              </p>
              <ul className="space-y-3 max-h-48 overflow-y-auto text-sm">
                {wrongReviews.map((w, i) => (
                  <li key={i} className="border-b border-red-100 pb-2 last:border-0">
                    <p className="font-semibold text-navy-dark">{w.question_text}</p>
                    <p className="text-red-700">きみの答え: {w.selected}</p>
                    <p className="text-green-700">正解: {w.correct}</p>
                    {w.hint && <p className="text-gray-600 mt-1">ヒント: {w.hint}</p>}
                  </li>
                ))}
              </ul>
              <Button
                onClick={handleRetryWrongs}
                className="w-full mt-3 bg-yellow-200 text-navy-dark hover:bg-yellow-300"
              >
                まちがいだけもう一度
              </Button>
            </div>
          )}

          <div className="flex flex-col gap-3 mt-2">
            {!practiceMode && (
              <div className="flex justify-between gap-2">
                <Button
                  onClick={handlePrevLevel}
                  disabled={level <= 1}
                  className="w-1/3 bg-blue-200 text-navy-dark hover:bg-blue-300 text-xs sm:text-sm"
                >
                  前のレベル
                </Button>
                <Button
                  onClick={() => {
                    setPracticeMode(false);
                    resetRoundState();
                    navigate(`/quiz?subject=${subject}&level=${level}`);
                    toast({ title: `レベル ${level} を再チャレンジ！` });
                  }}
                  className="w-1/3 bg-yellow-200 text-navy-dark hover:bg-yellow-300 text-xs sm:text-sm"
                >
                  同じレベル
                </Button>
                <Button
                  onClick={handleNextLevel}
                  disabled={score < questions.length || level >= MAX_LEVEL}
                  className="w-1/3 bg-blue-200 text-navy-dark hover:bg-blue-300 text-xs sm:text-sm"
                >
                  次のレベル
                </Button>
              </div>
            )}

            {score < questions.length && !practiceMode && (
              <p className="text-xs text-red-500 text-center">
                全問正解で次のレベルに進めます
              </p>
            )}

            <Button
              onClick={() => navigate('/')}
              className="w-full bg-green-200 text-navy-dark hover:bg-green-300"
            >
              ホームに戻る
            </Button>
            <Button
              variant="outline"
              onClick={() => navigate('/quiz')}
              className="w-full rounded-full"
            >
              教科・レベルを選びなおす
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  const progress = questions.length
    ? ((currentQuestion + 1) / questions.length) * 100
    : 0;
  const q = questions[currentQuestion];

  return (
    <div className="min-h-screen bg-gradient-to-br from-lavender-light via-mint-light to-sky-light p-4">
      <div className="flex items-center justify-between mb-4 gap-2">
        <Button
          onClick={() => navigate('/')}
          variant="ghost"
          size="sm"
          className="text-navy-dark hover:bg-lavender-soft/20 rounded-full"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          戻る
        </Button>
        <div className="text-sm text-navy-dark font-bold text-right">
          {subjectJa(subject)} L{level}
          <span className="block text-xs font-semibold text-orange-600">
            連続 {streak}（ベスト {bestStreak}）
          </span>
        </div>
      </div>

      <div className="mb-2 text-center text-sm font-bold text-navy-dark">
        問題 {currentQuestion + 1} / {questions.length || '—'}
        {practiceMode && (
          <span className="ml-2 text-xs text-yellow-700">練習モード</span>
        )}
      </div>
      <div className="mb-6">
        <Progress value={progress} className="h-3 bg-lavender-light/50" />
      </div>

      <Card
        className={cn(
          'kid-card max-w-2xl mx-auto',
          feedbackAnim === 'pop' && answerRevealed && 'quiz-pop',
          feedbackAnim === 'shake' && answerRevealed && 'quiz-shake',
        )}
      >
        <div className="text-center mb-6">
          <div className="text-5xl mb-3">{answerRevealed ? (currentIsCorrect ? '✨' : '💦') : '🤔'}</div>
          <h2 className="text-2xl sm:text-3xl font-bold text-navy-dark mb-2">
            {q?.question_text}
          </h2>
          {streak >= 3 && !answerRevealed && (
            <p className="text-orange-600 font-bold animate-pulse">{streak} 問連続正解中！</p>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {q?.options.map((option, index) => {
            const isCorrect = option.trim() === (q?.correct_answer ?? '').trim();
            const isSelected = selectedAnswer === index;
            const showMarks = answerRevealed && selectedAnswer !== null;

            let mark: string | null = null;
            if (showMarks && isCorrect) mark = '○';
            if (showMarks && isSelected && !isCorrect) mark = '×';

            let btnClass =
              'p-6 text-xl rounded-2xl border-4 transition-all flex items-center justify-center gap-3 min-h-[4.5rem]';
            if (showMarks && isCorrect) {
              btnClass += ' bg-green-100 text-green-900 border-green-500 shadow-md';
            } else if (showMarks && isSelected && !isCorrect) {
              btnClass += ' bg-red-100 text-red-900 border-red-500 shadow-md';
            } else if (isSelected) {
              btnClass += ' bg-sky-soft text-white border-sky-soft shadow-lg scale-105';
            } else {
              btnClass += ' bg-white text-navy-dark border-gray-200 hover:border-sky-soft';
            }

            return (
              <Button
                key={index}
                onClick={() => handleAnswerSelect(index)}
                disabled={answerRevealed}
                className={btnClass}
                variant="outline"
              >
                {mark && (
                  <span
                    className={`text-3xl font-bold shrink-0 ${
                      mark === '○' ? 'text-green-600' : 'text-red-600'
                    }`}
                    aria-hidden
                  >
                    {mark}
                  </span>
                )}
                <span>{option}</span>
              </Button>
            );
          })}
        </div>

        {answerRevealed && selectedAnswer !== null && q && (
          <p
            className={`text-center text-lg font-bold mb-3 ${
              currentIsCorrect ? 'text-green-700' : 'text-red-700'
            }`}
          >
            {currentIsCorrect
              ? streak >= 3
                ? `○ 正解！ ${streak} 問連続！`
                : '○ 正解！'
              : `× 不正解 — 正解は「${q.correct_answer}」`}
          </p>
        )}

        {(showHint || (answerRevealed && !currentIsCorrect)) && q?.hint && (
          <div className="mb-4 rounded-2xl bg-amber-50 border border-amber-200 p-3 text-sm text-navy-dark">
            <p className="font-bold flex items-center justify-center gap-1 mb-1">
              <Lightbulb className="h-4 w-4 text-amber-600" />
              ヒント
            </p>
            <p className="text-center">{q.hint}</p>
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
          {!answerRevealed && q?.hint && (
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowHint(true)}
              className="rounded-full border-amber-300 text-amber-800"
            >
              <Lightbulb className="h-4 w-4 mr-1" />
              ヒントをみる
            </Button>
          )}
          <Button
            onClick={handleNextQuestion}
            disabled={selectedAnswer === null || !answerRevealed}
            className={`quiz-button ${
              selectedAnswer === null || !answerRevealed
                ? 'opacity-50 cursor-not-allowed'
                : ''
            }`}
          >
            {currentQuestion < questions.length - 1 ? '次の問題へ' : '結果を見る'}
            <Check className="h-5 w-5 ml-2" />
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default Quiz;
