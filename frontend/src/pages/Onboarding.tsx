import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getAuth, onAuthStateChanged } from 'firebase/auth';
import { ArrowLeft, Sparkles, Star } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { toast } from '@/hooks/use-toast';
import {
  DEFAULT_CHARACTER,
  fetchCharacterFromServer,
  loadCharacter,
  patchCharacter,
  pushCharacterToServer,
} from '@/lib/characterState';
import {
  isValidBuddyName,
  markOnboardingComplete,
  normalizeBuddyName,
} from '@/lib/onboarding';
import { cn } from '@/lib/utils';
import { subjectJa } from '@/lib/subjectJa';

type Step = 'welcome' | 'name' | 'quiz';

const Onboarding = () => {
  const navigate = useNavigate();
  const [uid, setUid] = useState<string | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [step, setStep] = useState<Step>('welcome');
  const [name, setName] = useState(DEFAULT_CHARACTER.displayName);
  const [busy, setBusy] = useState(false);
  const [pickSubject, setPickSubject] = useState<'math' | 'english'>('math');

  useEffect(() => {
    const unsub = onAuthStateChanged(getAuth(), (user) => {
      setUid(user?.uid ?? null);
      setAuthReady(true);
      if (!user) {
        navigate('/login', { replace: true });
      }
    });
    return () => unsub();
  }, [navigate]);

  useEffect(() => {
    if (!uid) return;
    void (async () => {
      await fetchCharacterFromServer();
      const c = loadCharacter();
      if (c.displayName) setName(c.displayName);
    })();
  }, [uid]);

  const finishAndGo = (path: string) => {
    if (uid) markOnboardingComplete(uid);
    navigate(path, { replace: true });
  };

  const saveName = async () => {
    const buddy = normalizeBuddyName(name);
    if (!isValidBuddyName(buddy)) {
      toast({
        title: 'なまえを入れてね',
        description: '1〜20文字で入力してね',
        variant: 'destructive',
      });
      return;
    }
    setBusy(true);
    try {
      const next = patchCharacter({ displayName: buddy });
      const ok = await pushCharacterToServer(next);
      if (!ok) {
        toast({
          title: 'なまえの保存に失敗したよ',
          description: '通信を確認して、もういちど試してね',
          variant: 'destructive',
        });
        return;
      }
      toast({ title: `${buddy}、よろしくね！`, duration: 2000 });
      setStep('quiz');
    } finally {
      setBusy(false);
    }
  };

  const startFirstQuiz = () => {
    finishAndGo(`/quiz?subject=${pickSubject}&level=1`);
  };

  if (!authReady) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-lavender-light via-mint-light to-sky-light">
        <p className="text-navy-dark font-bold">じゅんび中…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-lavender-light via-mint-light to-sky-light p-4">
      <div className="max-w-lg mx-auto">
        <div className="flex items-center justify-between mb-4">
          <Button
            variant="ghost"
            size="sm"
            className="rounded-full text-navy-dark"
            onClick={() => {
              if (step === 'name') setStep('welcome');
              else if (step === 'quiz') setStep('name');
              else navigate('/');
            }}
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            もどる
          </Button>
          <div className="flex gap-1.5">
            {(['welcome', 'name', 'quiz'] as Step[]).map((s, i) => (
              <span
                key={s}
                className={cn(
                  'h-2 w-6 rounded-full transition-colors',
                  step === s
                    ? 'bg-sky-soft'
                    : i <
                        (['welcome', 'name', 'quiz'] as Step[]).indexOf(step)
                      ? 'bg-mint-soft'
                      : 'bg-white/70',
                )}
              />
            ))}
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="rounded-full text-xs text-gray-500"
            onClick={() => finishAndGo('/')}
          >
            スキップ
          </Button>
        </div>

        {step === 'welcome' && (
          <Card className="kid-card text-center">
            <div className="text-6xl mb-4">🌟</div>
            <h1 className="text-3xl font-bold text-navy-dark mb-2">
              まなともへようこそ！
            </h1>
            <p className="text-gray-600 mb-6 leading-relaxed">
              クイズやさんぽで、ともだちキャラが育つよ。
              <br />
              まずはなまえを決めて、はじめてのクイズにちょうせんしよう！
            </p>
            <ul className="text-left text-sm text-navy-dark space-y-2 mb-8 bg-white/60 rounded-2xl p-4">
              <li className="flex gap-2">
                <Sparkles className="h-4 w-4 text-lavender-soft shrink-0 mt-0.5" />
                なまえをつける
              </li>
              <li className="flex gap-2">
                <Star className="h-4 w-4 text-sky-soft shrink-0 mt-0.5" />
                はじめてのクイズ（レベル1）
              </li>
            </ul>
            <Button className="quiz-button w-full" onClick={() => setStep('name')}>
              はじめる
            </Button>
          </Card>
        )}

        {step === 'name' && (
          <Card className="kid-card text-center">
            <div className="text-5xl mb-3">✏️</div>
            <h2 className="text-2xl font-bold text-navy-dark mb-2">
              キャラのなまえは？
            </h2>
            <p className="text-sm text-gray-600 mb-6">
              あとからホームでもかえられるよ
            </p>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={20}
              placeholder="みーちゃん"
              className="text-center text-xl font-bold h-14 mb-2 border-2 border-navy-dark/20"
              onKeyDown={(e) => {
                if (e.key === 'Enter') void saveName();
              }}
            />
            <p className="text-xs text-gray-500 mb-6">{normalizeBuddyName(name).length}/20</p>
            <Button
              className="quiz-button w-full"
              disabled={busy}
              onClick={() => void saveName()}
            >
              {busy ? 'ほぞん中…' : 'このなまえでOK'}
            </Button>
          </Card>
        )}

        {step === 'quiz' && (
          <Card className="kid-card text-center">
            <div className="text-5xl mb-3">🎯</div>
            <h2 className="text-2xl font-bold text-navy-dark mb-2">
              はじめてのクイズ
            </h2>
            <p className="text-sm text-gray-600 mb-6">
              やさしいレベル1からスタート！教科をえらんでね
            </p>
            <div className="flex gap-3 justify-center mb-8">
              <Button
                type="button"
                onClick={() => setPickSubject('math')}
                className={cn(
                  'text-lg px-6 py-6 rounded-2xl',
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
                  'text-lg px-6 py-6 rounded-2xl',
                  pickSubject === 'english'
                    ? 'bg-sky-soft text-white'
                    : 'bg-white text-navy-dark border-2',
                )}
              >
                ✏️ 英語
              </Button>
            </div>
            <Button className="quiz-button w-full mb-3" onClick={startFirstQuiz}>
              {subjectJa(pickSubject)} レベル1 をはじめる
            </Button>
            <Button
              variant="outline"
              className="w-full rounded-full"
              onClick={() => finishAndGo('/')}
            >
              ホームでゆっくり決める
            </Button>
            <p className="text-xs text-gray-500 mt-4">
              キャラの絵はホームの「新しいキャラを作る」からいつでもOK
            </p>
            <Button variant="link" className="text-xs mt-1" asChild>
              <Link to="/upload" onClick={() => uid && markOnboardingComplete(uid)}>
                さきにキャラをつくる
              </Link>
            </Button>
          </Card>
        )}
      </div>
    </div>
  );
};

export default Onboarding;
