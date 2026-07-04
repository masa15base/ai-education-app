import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getAuth } from 'firebase/auth';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { ArrowLeft, Check, Star } from 'lucide-react';
import { toast } from '@/hooks/use-toast';
import { postQuizComplete } from '@/lib/api';
import { getApiBase } from '@/lib/apiBase';
import { fetchCharacterFromServer } from '@/lib/characterState';
import { ENGLISH_VOCAB, englishFourOptions, englishVocabRowIndex } from '@/lib/englishQuizDynamic';
import { ensureMathFourOptions, mathQuestionParts } from '@/lib/mathQuizDynamic';

interface Question {
  id: string;
  subject: string;
  level: number;
  question_text: string;
  options: string[];
  correct_answer: string; // 正解
  hint: string;
  media: {
    image_url: string | null;
    audio_url: string | null;
  };
}

const Quiz = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const subject = queryParams.get('subject') || 'math';
  const initialLevel = parseInt(queryParams.get('level') || '1');

  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [score, setScore] = useState(0);
  const [answers, setAnswers] = useState<number[]>([]);
  const [level, setLevel] = useState(initialLevel);
  const [levelHistory, setLevelHistory] = useState<number[]>([initialLevel]);
  const quizSubmittedRef = useRef(false);
  /** 結果画面で表示する正答率・獲得XP（useEffect 内計算値とズレさせないため state に保持） */
  const [resultSummary, setResultSummary] = useState<{
    pct: number;
    gained: number;
  } | null>(null);
  /** 選択後に正解・不正解マーク（○×）を表示 */
  const [answerRevealed, setAnswerRevealed] = useState(false);

  const updateLevelHistory = (newLevel: number) => {
    if (levelHistory[levelHistory.length - 1] !== newLevel) {
      setLevelHistory(prev => [...prev, newLevel]);
    }
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
        q.question_text.includes('猫') && q.options.some((o) => o === 'cat'),
    );
    const uniqueTexts = new Set(rows.map((q) => q.question_text));
    return catOnly || uniqueTexts.size <= 1;
  };

  useEffect(() => {
    const url = `${getApiBase()}/questions?subject=${subject}&level=${level}`;
    console.log("📡 Fetch:", url);

    fetch(url)
      .then(async (res) => {
        const text = await res.text();
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${text.slice(0, 200)}`);
        }
        try {
          return JSON.parse(text);
        } catch (e) {
          throw new Error(`Invalid JSON: ${text.slice(0, 200)}`);
        }
      })
      .then((raw) => {
        console.log("✅ Raw questions payload:", raw);
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
        quizSubmittedRef.current = false;
        setQuestions(finalData);
        setCurrentQuestion(0);
        setSelectedAnswer(null);
        setAnswerRevealed(false);
        setScore(0);
        setShowResult(false);
        setAnswers([]);
      })
      .catch((err) => {
        console.error('問題の取得に失敗しました', err);
        const msg = String(err || '');
        if (msg.includes('HTTP 404')) {
          // Fallback to local sample questions if backend route is not available
          const samples = buildSampleQuestions(subject, level, 5);
          quizSubmittedRef.current = false;
          setQuestions(samples);
          setCurrentQuestion(0);
          setSelectedAnswer(null);
          setAnswerRevealed(false);
          setScore(0);
          setShowResult(false);
          setAnswers([]);
          toast({ title: 'サンプル問題で開始します', description: 'バックエンドの /api/questions が未デプロイのため代替を使用', variant: 'default' });
          return;
        }
        toast({ title: '問題の取得に失敗しました', description: msg, variant: 'destructive' });
      });
  }, [subject, level]);

  useEffect(() => {
    if (!showResult) {
      quizSubmittedRef.current = false;
      setResultSummary(null);
    }
  }, [showResult]);

  useEffect(() => {
    if (!showResult || questions.length === 0) return;
    if (answers.length !== questions.length) return;
    if (quizSubmittedRef.current) return;
    quizSubmittedRef.current = true;

    const pct = questions.length
      ? Math.round((score / questions.length) * 100)
      : 0;

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
        const gained = typeof res.gained_xp === 'number' ? res.gained_xp : 0;
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
              title: '今日はクイズの経験値が上限に達したよ',
              description: '採点はサーバーに記録したよ',
              duration: 2200,
            });
          }
          toast({
            title: 'サーバーに記録しました',
            description: `採点 ${res.score_percent}%（${res.correct}/${res.total} 問正解）`,
          });
        } else {
          toast({
            title: 'クイズ完了！',
            description:
              'ログインすると結果と経験値をクラウドに保存できるよ',
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
  }, [showResult, questions, answers, subject, level, score]);

  const handleAnswerSelect = (answerIndex: number) => {
    if (answerRevealed) return;
    setSelectedAnswer(answerIndex);
    setAnswerRevealed(true);
  };

  const handleNextQuestion = () => {
    if (selectedAnswer === null) return;
    const currentQ = questions[currentQuestion];
    const selectedValue = currentQ.options[selectedAnswer];
    const isCorrect = selectedValue.trim() === currentQ.correct_answer.trim();

    if (isCorrect) {
      setScore(s => s + 1);
    }

    setAnswers(prev => [...prev, selectedAnswer]);

    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(i => i + 1);
      setSelectedAnswer(null);
      setAnswerRevealed(false);
    } else {
      setShowResult(true);
    }
  };

  const handleNextLevel = () => {
    if (score < questions.length) {
      toast({ title: '全問正解で次のレベルに進めます', description: 'もう一度挑戦してみましょう' });
      return;
    }
    if (level < 10) {
      const next = level + 1;
      setLevel(next);
      updateLevelHistory(next);
      setCurrentQuestion(0);
      setSelectedAnswer(null);
      setAnswerRevealed(false);
      setScore(0);
      setShowResult(false);
      setAnswers([]);
      toast({ title: `レベル ${next} に進みました！` });
      navigate(`/quiz?subject=${subject}&level=${next}`);
    } else {
      toast({ title: 'レベル上限です', description: 'これ以上のレベルはありません' });
    }
  };

  const handlePrevLevel = () => {
    if (level > 1) {
      const prev = level - 1;
      setLevel(prev);
      updateLevelHistory(prev);
      setCurrentQuestion(0);
      setSelectedAnswer(null);
      setAnswerRevealed(false);
      setScore(0);
      setShowResult(false);
      setAnswers([]);
      toast({ title: `レベル ${prev} に戻りました` });
      navigate(`/quiz?subject=${subject}&level=${prev}`);
    } else {
      toast({ title: 'レベル1です', description: 'これ以上下のレベルはありません' });
    }
  };

  const handleFinishQuiz = () => navigate('/');

  if (showResult) {
    const levelPath = levelHistory.join(' → ');

    return (
      <div className="min-h-screen bg-gradient-to-br from-lavender-light via-mint-light to-sky-light p-4 flex items-center justify-center">
        <Card className="kid-card max-w-md w-full text-center">
          <div className="text-6xl mb-4">🎉</div>
          <h2 className="text-2xl font-bold text-navy-dark mb-4">クイズ完了！</h2>
          <div className="text-4xl font-bold text-sky-soft mb-2">{score}/{questions.length}</div>
          <p className="text-gray-600 mb-2">問正解しました！</p>
          <p className="text-sm text-navy-dark mb-4">レベル履歴: {levelPath}</p>

          <div className="bg-gradient-to-r from-mint-light to-sky-light rounded-2xl p-4 mb-6">
            <Star className="h-8 w-8 text-lavender-soft mx-auto mb-2" />
            <p className="font-bold text-navy-dark">
              経験値 +{resultSummary?.gained ?? "—"} ゲット！
            </p>
            {resultSummary != null && (
              <p className="text-sm text-gray-700 mt-1">
                正答率 {resultSummary.pct}%
              </p>
            )}
          </div>

          <div className="flex flex-col gap-3 mt-4">
            <div className="flex justify-between gap-2">
              <Button onClick={handlePrevLevel} disabled={level <= 1} className="w-1/3 bg-blue-200 text-navy-dark hover:bg-blue-300">
                前のレベルへ
              </Button>

              <Button
                onClick={() => {
                  setCurrentQuestion(0);
                  setSelectedAnswer(null);
                  setAnswerRevealed(false);
                  setScore(0);
                  setShowResult(false);
                  setAnswers([]);
                  toast({ title: `レベル ${level} を再チャレンジ！` });
                  navigate(`/quiz?subject=${subject}&level=${level}`);
                }}
                className="w-1/3 bg-yellow-200 text-navy-dark hover:bg-yellow-300"
              >
                同じレベルを再挑戦
              </Button>

              <Button
                onClick={handleNextLevel}
                disabled={score < questions.length || level >= 10}
                className="w-1/3 bg-blue-200 text-navy-dark hover:bg-blue-300"
              >
                次のレベルへ
              </Button>
            </div>

            {score < questions.length && (
              <p className="text-xs text-red-500 mt-1 text-center">全問正解で次のレベルに進めます</p>
            )}

            <div className="text-center">
              <Button onClick={handleFinishQuiz} className="w-full bg-green-200 text-navy-dark hover:bg-green-300">
                ホームに戻る
              </Button>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  const progress = questions.length ? ((currentQuestion + 1) / questions.length) * 100 : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-lavender-light via-mint-light to-sky-light p-4">
      <div className="flex items-center justify-between mb-6">
        <Button
          onClick={() => navigate('/')}
          variant="ghost"
          size="sm"
          className="text-navy-dark hover:bg-lavender-soft/20 rounded-full"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          戻る
        </Button>
        <div className="text-sm text-navy-dark font-bold">
          問題 {currentQuestion + 1} / {questions.length}（レベル {level}）
        </div>
      </div>

      <div className="mb-6">
        <Progress value={progress} className="h-3 bg-lavender-light/50" />
      </div>

      <Card className="kid-card max-w-2xl mx-auto">
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">🤔</div>
          <h2 className="text-3xl font-bold text-navy-dark mb-4">
            {questions[currentQuestion]?.question_text}
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {questions[currentQuestion]?.options.map((option, index) => {
            const q = questions[currentQuestion];
            const isCorrect =
              option.trim() === (q?.correct_answer ?? '').trim();
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
              btnClass +=
                ' bg-white text-navy-dark border-gray-200 hover:border-sky-soft';
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

        {answerRevealed && selectedAnswer !== null && questions[currentQuestion] && (
          <p
            className={`text-center text-lg font-bold mb-4 ${
              questions[currentQuestion].options[selectedAnswer]?.trim() ===
              questions[currentQuestion].correct_answer.trim()
                ? 'text-green-700'
                : 'text-red-700'
            }`}
          >
            {questions[currentQuestion].options[selectedAnswer]?.trim() ===
            questions[currentQuestion].correct_answer.trim()
              ? '○ 正解！'
              : `× 不正解 — 正解は「${questions[currentQuestion].correct_answer}」`}
          </p>
        )}

        <div className="text-center">
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