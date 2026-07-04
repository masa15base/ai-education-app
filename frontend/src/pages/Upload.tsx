import { useEffect, useState } from 'react';
import { getAuth } from 'firebase/auth';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Camera, Upload, ArrowLeft, RefreshCw, Loader2 } from 'lucide-react';
import { toast } from '@/hooks/use-toast';
import {
  allowAnonymousMediaRequests,
  generateCharacterFromBase64,
  preprocessImageToBase64,
  readFileAsBase64,
  type PreprocessResult,
} from '@/lib/imageClient';
import { patchCharacter, pushCharacterToServer, setCharacterMemory, loadCharacter, levelFromExperience } from '@/lib/characterState';
import { getApiBase } from '@/lib/apiBase';
import {
  CHARACTER_INPUT_ACCEPT,
  CHARACTER_INPUT_FORMAT_LABEL,
  CHARACTER_OUTPUT,
  CHARACTER_PREPROCESS_OUTPUT,
  CHARACTER_MAX_UPLOAD_MB,
  isAllowedCharacterInputFile,
  type CharacterImageRequirements,
} from '@/lib/characterImageRequirements';

const UploadPage = () => {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>('');
  const [characterName, setCharacterName] = useState('');
  const [phase, setPhase] = useState<'form' | 'processing' | 'confirm'>('form');
  const [resultImage, setResultImage] = useState<string | null>(null);
  const [heroPreview, setHeroPreview] = useState<string | null>(null);
  const [nextPreview, setNextPreview] = useState<string | null>(null);
  const [pickedFeatures, setPickedFeatures] = useState<string[]>([]);
  const [visionInsight, setVisionInsight] = useState<string | null>(null);
  const [isRegenerating, setIsRegenerating] = useState(false);
  /** もう一度変換用（前処理済み base64・画像ファイルは保持） */
  const [preprocessedBase64, setPreprocessedBase64] = useState<string | null>(null);
  const [processedPreview, setProcessedPreview] = useState<string | null>(null);
  const [preprocessMeta, setPreprocessMeta] = useState<
    PreprocessResult['meta'] | null
  >(null);
  const [algoInfo, setAlgoInfo] = useState<{
    algorithm?: string;
    max_edge?: number;
    description?: string;
    tips?: string[];
    requirements?: CharacterImageRequirements;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetch(`${getApiBase()}/preprocess-image/info`)
      .then(async (r) => {
        if (!r.ok) return null;
        return (await r.json()) as {
          algorithm?: string;
          max_edge?: number;
          description?: string;
          tips?: string[];
          requirements?: CharacterImageRequirements;
        };
      })
      .then((data) => {
        if (!cancelled) setAlgoInfo(data);
      })
      .catch(() => {
        if (!cancelled) setAlgoInfo(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const resetToForm = (clearImage = false) => {
    setPhase('form');
    setResultImage(null);
    setHeroPreview(null);
    setNextPreview(null);
    setPickedFeatures([]);
    setVisionInsight(null);
    setIsRegenerating(false);
    if (clearImage) {
      setPreviewUrl('');
      setSelectedFile(null);
      setPreprocessedBase64(null);
      setProcessedPreview(null);
      setPreprocessMeta(null);
    }
  };

  /** 前処理済み base64（state または data URL プレビューから） */
  const getCachedPreprocessB64 = (): string | null => {
    if (preprocessedBase64) return preprocessedBase64;
    if (processedPreview?.includes('base64,')) {
      return processedPreview.split('base64,')[1] ?? null;
    }
    return null;
  };

  const showConfirmPanel = Boolean(
    previewUrl && characterName.trim() && resultImage && (phase === 'confirm' || isRegenerating),
  );
  const showDraftPanel = Boolean(
    previewUrl && characterName.trim() && !resultImage && phase !== 'confirm' && !isRegenerating,
  );

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (!isAllowedCharacterInputFile(file)) {
        toast({
          title: '対応していないファイル形式です',
          description: `${CHARACTER_INPUT_FORMAT_LABEL}。iPhone の HEIC は JPEG に変換してから選んでね。`,
          variant: 'destructive',
        });
        event.target.value = '';
        return;
      }
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      setResultImage(null);
      setPreprocessedBase64(null);
      setProcessedPreview(null);
      setPreprocessMeta(null);
      setPhase('form');
    }
  };

  const applyGenerationResult = (gen: Awaited<ReturnType<typeof generateCharacterFromBase64>>) => {
    const image = gen.current_stage_image ?? gen.image;
    setResultImage(image);
    setHeroPreview(gen.final_hero_preview ?? null);
    setNextPreview(gen.next_stage_preview ?? null);
    setPickedFeatures(
      gen.signature_features_ja?.length
        ? gen.signature_features_ja
        : [
            'FC RPG風 chibi',
            '32×32 正面向き',
            '元画像の髪色・服色を反映',
          ],
    );
    setVisionInsight(
      gen.generation_mode === 'famicom_sprite_spec'
        ? '固定デザインの少女ファミコン風キャラを生成しました'
        : null,
    );
  };

  const runGenerate = async (opts?: { reusePreprocess?: boolean; regenerate?: boolean }) => {
    if (!selectedFile || !characterName.trim()) {
      toast({
        title: 'エラー',
        description: '画像とキャラクター名を入力してください',
        variant: 'destructive',
      });
      return;
    }

    if (!getAuth().currentUser && !allowAnonymousMediaRequests()) {
      toast({
        title: 'ログインが必要です',
        description: '画像の前処理とキャラ生成はログイン後に使えます。',
        variant: 'destructive',
      });
      return;
    }

    const cachedB64 = getCachedPreprocessB64();
    const isRegenerateFlow = Boolean(opts?.regenerate && resultImage);
    const reusePreprocess = Boolean(
      opts?.reusePreprocess || opts?.regenerate || (opts?.regenerate === undefined && cachedB64),
    );

    if (isRegenerateFlow) {
      setIsRegenerating(true);
    } else {
      setPhase('processing');
    }
    try {
      let b64: string;
      let meta: PreprocessResult['meta'] | null = preprocessMeta;

      if (reusePreprocess && cachedB64) {
        b64 = cachedB64;
        if (!preprocessedBase64) {
          setPreprocessedBase64(b64);
        }
      } else {
        const preprocessed = await preprocessImageToBase64(selectedFile);
        b64 = preprocessed.imageBase64;
        meta = preprocessed.meta ?? null;
        setPreprocessedBase64(b64);
        setProcessedPreview(`data:image/png;base64,${b64}`);
        setPreprocessMeta(meta);
      }

      const char = loadCharacter();
      const originalB64 = await readFileAsBase64(selectedFile);
      const gen = await generateCharacterFromBase64(originalB64, {
        display_name: characterName.trim(),
        learning_level: levelFromExperience(char.experience),
      });
      applyGenerationResult(gen);
      setPhase('confirm');
      if (isRegenerateFlow) {
        toast({
          title: '再生成できたよ',
          description: '同じ手描きから、もう一度パーツを組み合わせました',
        });
      }
    } catch (error) {
      console.error(error);
      const msg = error instanceof Error ? error.message : String(error);
      toast({
        title: 'エラー',
        description: msg || '画像の処理またはキャラ生成に失敗しました',
        variant: 'destructive',
      });
      setPhase(resultImage ? 'confirm' : cachedB64 || getCachedPreprocessB64() ? 'form' : 'form');
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleRegenerate = () => {
    if (!resultImage) {
      void runGenerate();
      return;
    }
    void runGenerate({ reusePreprocess: true, regenerate: true });
  };

  const handleConfirmOk = async () => {
    if (!resultImage || !characterName.trim() || isRegenerating) return;
    setPhase('processing');
    try {
      const next = patchCharacter({
        displayName: characterName.trim(),
        imageUrl: resultImage,
        heroPreviewUrl: heroPreview,
        nextEvolutionPreviewUrl: nextPreview,
      });
      setCharacterMemory(next);
      const saved = await pushCharacterToServer(next);

      toast({
        title: 'キャラクターを登録したよ！',
        description: saved
          ? `${characterName.trim()} をホームに表示します`
          : `${characterName.trim()} を作ったよ（ログインするとクラウドにも保存できるよ）`,
      });
      navigate('/', {
        replace: true,
        state: { characterUpdated: true, displayName: characterName.trim() },
      });
    } catch (error) {
      console.error(error);
      const msg = error instanceof Error ? error.message : String(error);
      toast({
        title: '保存に失敗しました',
        description: msg,
        variant: 'destructive',
      });
      setPhase('confirm');
    }
  };

  const qualityHint = (() => {
    const ink = preprocessMeta?.inkRatio;
    if (ink == null) return null;
    if (!preprocessMeta?.hasContent || ink < 0.01) {
      return '線がかなり薄いです。濃いペン・明るい場所で撮り直すと良くなります。';
    }
    if (ink < 0.03) {
      return '線が少なめです。絵をもう少し大きく写すと精度が上がります。';
    }
    if (ink > 0.45) {
      return '黒が多めです。背景の影や机の模様が入っていないか確認してね。';
    }
    return '手書き線は良好です。このまま生成できます。';
  })();

  return (
    <div className="min-h-screen bg-gradient-to-br from-lavender-light via-mint-light to-sky-light p-4">
      {/* ヘッダー */}
      <div className="flex items-center mb-6">
        <Button 
          onClick={() => navigate('/')}
          variant="ghost"
          size="sm"
          className="mr-4 text-navy-dark hover:bg-lavender-soft/20 rounded-full"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          戻る
        </Button>
        <h1 className="text-3xl font-bold text-navy-dark">キャラクターを作ろう</h1>
      </div>

      <div className="max-w-2xl mx-auto">
        {/* アップロードエリア */}
        <Card className="kid-card mb-6">
          <h2 className="text-xl font-bold text-center mb-6 text-navy-dark">描いた絵をアップロードしよう！</h2>
          <div className="text-xs text-gray-600 bg-sky-50/80 border border-sky-200 rounded-xl p-3 mb-3">
            <p className="font-semibold text-navy-dark mb-1">画像のファイル形式</p>
            <ul className="space-y-1 list-disc pl-4">
              <li>
                <span className="font-medium">アップロード:</span> {CHARACTER_INPUT_FORMAT_LABEL}
              </li>
              <li>
                <span className="font-medium">サイズ上限:</span>{' '}
                {algoInfo?.requirements?.input?.max_bytes_human ?? `${CHARACTER_MAX_UPLOAD_MB}MB`}
              </li>
              <li>
                <span className="font-medium">前処理・生成結果:</span>{' '}
                {CHARACTER_PREPROCESS_OUTPUT} → {CHARACTER_OUTPUT}
              </li>
            </ul>
          </div>
          <div className="text-xs text-gray-600 bg-white/70 border border-gray-200 rounded-xl p-3 mb-4">
            <div className="flex items-center justify-between gap-2 mb-1">
              <p className="font-semibold text-gray-700">撮影のコツ</p>
              <Dialog>
                <DialogTrigger asChild>
                  <Button type="button" variant="outline" size="sm" className="rounded-full text-xs">
                    アルゴリズム詳細
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>手書き前処理アルゴリズム</DialogTitle>
                    <DialogDescription>
                      キャラ生成前に、手書き線を抽出してノイズを減らします。
                    </DialogDescription>
                  </DialogHeader>
                  <div className="text-sm text-gray-700 space-y-2">
                    <p>
                      <span className="font-semibold">方式:</span>{' '}
                      {algoInfo?.algorithm ?? 'binary_scribble_v3_famicom'}
                    </p>
                    <p>
                      <span className="font-semibold">最大サイズ:</span>{' '}
                      {algoInfo?.max_edge ?? 512}px
                    </p>
                    <p>
                      <span className="font-semibold">処理内容:</span>{' '}
                      {algoInfo?.description ??
                        'grayscale + autocontrast + denoise + threshold + trim + square + resize'}
                    </p>
                    {algoInfo?.requirements && (
                      <div className="border-t border-gray-200 pt-2 mt-2">
                        <p className="font-semibold mb-1">ファイル形式の要件</p>
                        <ul className="list-disc pl-5 space-y-1 text-xs">
                          <li>
                            入力:{' '}
                            {(algoInfo.requirements.input?.extensions ?? []).join(', ')}
                          </li>
                          <li>
                            最大: {algoInfo.requirements.input?.max_bytes_human ?? '8MB'}
                          </li>
                          <li>
                            出力: 前処理 {algoInfo.requirements.preprocess_output?.format ?? 'PNG'}
                            、キャラ {algoInfo.requirements.character_output?.format ?? 'PNG'}
                          </li>
                          {(algoInfo.requirements.input?.notes ?? []).map((note) => (
                            <li key={note}>{note}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <div>
                      <p className="font-semibold mb-1">きれいに検出するコツ</p>
                      <ul className="list-disc pl-5 space-y-1">
                        {(algoInfo?.tips?.length ? algoInfo.tips : [
                          '白い紙に濃いペンで描く',
                          '影が入らないように明るい場所で撮る',
                          '絵全体が写真に入るように撮る',
                        ]).map((tip) => (
                          <li key={tip}>{tip}</li>
                        ))}
                      </ul>
                    </div>
                    {preprocessMeta && (
                      <p className="text-xs text-gray-500">
                        直近画像の計測: 線の濃さ {Math.round((preprocessMeta.inkRatio ?? 0) * 100)}%
                        / しきい値 {preprocessMeta.threshold ?? '-'}
                      </p>
                    )}
                  </div>
                </DialogContent>
              </Dialog>
            </div>
            <ul className="space-y-1 list-disc pl-4">
              <li>白い紙に濃いペンで描く</li>
              <li>影が入りにくい明るい場所で撮る</li>
              <li>絵全体が切れないように写す</li>
            </ul>
          </div>
          
          {phase === 'confirm' && previewUrl ? (
            <div className="rounded-2xl border border-sky-soft/40 bg-white/60 p-4 text-left text-sm text-gray-600">
              <p className="font-semibold text-navy-dark mb-2">選択した手描き</p>
              <img
                src={previewUrl}
                alt="選択した手描き"
                className="max-h-32 mx-auto rounded-xl border border-gray-200"
              />
              <p className="text-xs mt-2 text-center">
                別の絵にする場合は、下の「別の画像を選び直す」から変更できます。
              </p>
            </div>
          ) : !previewUrl ? (
            <div className="border-4 border-dashed border-pink-soft/50 rounded-3xl p-12 text-center">
              <Camera className="h-16 w-16 text-pink-soft mx-auto mb-4" />
              <p className="text-gray-600 mb-2">絵の写真を撮るか、画像ファイルを選んでね</p>
              <p className="text-xs text-gray-500 mb-4">{CHARACTER_INPUT_FORMAT_LABEL}</p>
              <Label htmlFor="file-upload" className="kid-button cursor-pointer inline-block">
                <Upload className="h-5 w-5 mr-2 inline" />
                画像を選ぶ
              </Label>
              <Input 
                id="file-upload"
                type="file" 
                accept={CHARACTER_INPUT_ACCEPT}
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>
          ) : (
            <div className="text-center">
              <img 
                src={previewUrl} 
                alt="アップロードされた画像" 
                className="max-h-64 mx-auto rounded-2xl shadow-lg mb-4"
              />
              <Button 
                onClick={() => {
                  setPreviewUrl('');
                  setSelectedFile(null);
                  setProcessedPreview(null);
                  setPreprocessMeta(null);
                }}
                variant="outline"
                className="mb-4 border-lavender-soft/50 text-navy-dark hover:bg-lavender-soft/20 rounded-full"
              >
                別の画像を選ぶ
              </Button>
            </div>
          )}
        </Card>

        {/* キャラクター名入力 */}
        {previewUrl && (
          <Card className="kid-card mb-6">
            <h3 className="text-lg font-bold mb-4 text-navy-dark">キャラクターに名前をつけよう</h3>
            <Label htmlFor="character-name" className="text-base text-navy-dark">名前</Label>
            <Input 
              id="character-name"
              value={characterName}
              onChange={(e) => setCharacterName(e.target.value)}
              placeholder="例：ぴょんた"
              className="mt-2 text-lg p-3 rounded-2xl border-2 border-mint-soft/30 focus:border-sky-soft"
            />
          </Card>
        )}

        {/* 生成・確認 */}
        {showConfirmPanel && (
          <Card className="kid-card text-center border-2 border-mint-soft/60 relative">
            {isRegenerating && (
              <div
                className="absolute inset-0 z-10 flex flex-col items-center justify-center rounded-2xl bg-white/85 backdrop-blur-sm"
                aria-live="polite"
                aria-busy="true"
              >
                <Loader2 className="h-10 w-10 text-sky-soft animate-spin mb-2" />
                <p className="text-sm font-semibold text-navy-dark">再生成しています…</p>
              </div>
            )}
            <h3 className="text-2xl font-bold mb-2 text-navy-dark">
              ✨ {characterName.trim()} はこんな感じ！
            </h3>
            {visionInsight && (
              <p className="text-xs text-gray-600 mb-4">{visionInsight}</p>
            )}

            <div className="mb-6 rounded-2xl bg-white/80 border border-sky-soft/40 p-4">
              <p className="text-sm font-bold text-navy-dark mb-3">今の姿</p>
              <img
                src={resultImage}
                alt={`${characterName} 今の姿`}
                className={`max-h-72 mx-auto rounded-2xl border-4 border-sky-soft/40 shadow-lg bg-white ${isRegenerating ? 'opacity-40' : ''}`}
                style={{ imageRendering: 'pixelated' }}
              />
            </div>

            {(nextPreview || heroPreview) && (
              <div className="mb-6 rounded-2xl bg-amber-50/80 border border-amber-200 p-4">
                <p className="text-sm font-bold text-navy-dark mb-3">進化プレビュー</p>
                <div className="flex justify-center items-end gap-6 flex-wrap">
                  {nextPreview && (
                    <div className="text-center">
                      <p className="text-xs font-semibold text-gray-700 mb-2">次の進化</p>
                      <img
                        src={nextPreview}
                        alt="次の進化"
                        className="h-24 w-24 object-contain bg-white rounded-xl border-2 border-sky-soft/40"
                        style={{ imageRendering: 'pixelated' }}
                      />
                    </div>
                  )}
                  {heroPreview && (
                    <div className="text-center">
                      <p className="text-xs font-semibold text-amber-800 mb-2">最終ヒーロー</p>
                      <img
                        src={heroPreview}
                        alt="最終ヒーロー"
                        className="h-28 w-28 object-contain bg-white rounded-xl border-2 border-amber-300 shadow-md"
                        style={{ imageRendering: 'pixelated' }}
                      />
                    </div>
                  )}
                </div>
              </div>
            )}

            {pickedFeatures.length > 0 && (
              <div className="mb-6 rounded-2xl bg-mint-soft/30 border border-mint-soft p-4 text-left">
                <p className="text-sm font-bold text-navy-dark mb-2">反映した特徴</p>
                <ul className="flex flex-wrap gap-2 justify-center">
                  {pickedFeatures.map((f) => (
                    <li
                      key={f}
                      className="rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-navy-dark border border-sky-soft/40"
                    >
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-sm text-gray-700 mb-6">
              気に入ったら OK でホームに反映。別の見た目がよければ「再生成」を押してね。
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center mb-6">
              <Button
                onClick={() => void handleConfirmOk()}
                disabled={isRegenerating}
                className="kid-button text-lg py-5 px-10 bg-green-500 hover:bg-green-600"
              >
                OK（このキャラにする）
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={isRegenerating}
                className="rounded-full border-2 border-sky-soft text-navy-dark py-5 px-8 inline-flex items-center justify-center gap-2"
                onClick={() => void handleRegenerate()}
              >
                {isRegenerating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    再生成中…
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4" />
                    再生成
                  </>
                )}
              </Button>
            </div>
            <div className="border-t border-gray-200 pt-5">
              <p className="text-sm font-semibold text-navy-dark mb-3">やり直すとき</p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button
                  type="button"
                  variant="outline"
                  disabled={isRegenerating}
                  className="rounded-full border-2 border-navy-dark text-navy-dark"
                  onClick={() => resetToForm(true)}
                >
                  別の画像を選び直す
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  disabled={isRegenerating}
                  className="rounded-full text-gray-600"
                  onClick={() => resetToForm(false)}
                >
                  名前や画像を変えずに戻る
                </Button>
              </div>
            </div>
          </Card>
        )}

        {showDraftPanel && (
          <Card className="kid-card text-center">
            {processedPreview && phase === 'form' && (
              <div className="mb-4">
                <p className="text-sm text-gray-700 mb-2">
                  手書き検出プレビュー（線画抽出）
                </p>
                <img
                  src={processedPreview}
                  alt="前処理プレビュー"
                  className="max-h-40 mx-auto rounded-xl border border-gray-200"
                />
                <div className="mt-2">
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button type="button" variant="outline" size="sm" className="rounded-full text-xs">
                        プレビューを拡大
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-2xl">
                      <DialogHeader>
                        <DialogTitle>前処理プレビュー（拡大）</DialogTitle>
                        <DialogDescription>
                          手書き線を抽出した画像です。線が薄すぎる・黒つぶれが多すぎる場合は撮り直しがおすすめです。
                        </DialogDescription>
                      </DialogHeader>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div>
                          <p className="text-xs font-semibold text-gray-700 mb-1">原画像</p>
                          <img
                            src={previewUrl}
                            alt="原画像プレビュー拡大"
                            className="w-full max-h-[60vh] object-contain rounded-xl border border-gray-200 bg-white"
                          />
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-gray-700 mb-1">前処理後（線画）</p>
                          <img
                            src={processedPreview}
                            alt="前処理プレビュー拡大"
                            className="w-full max-h-[60vh] object-contain rounded-xl border border-gray-200 bg-white"
                          />
                        </div>
                      </div>
                      {preprocessMeta && (
                        <p className="text-xs text-gray-500">
                          線の濃さ: {Math.round((preprocessMeta.inkRatio ?? 0) * 100)}%
                          {' / '}
                          しきい値: {preprocessMeta.threshold ?? '-'}
                        </p>
                      )}
                    </DialogContent>
                  </Dialog>
                </div>
                {preprocessMeta && (
                  <div className="mt-2">
                    <p className="text-xs text-gray-500">
                      線の濃さ: {Math.round((preprocessMeta.inkRatio ?? 0) * 100)}%
                      {' / '}
                      しきい値: {preprocessMeta.threshold ?? '-'}
                    </p>
                    {qualityHint && (
                      <p className="text-xs mt-1 text-amber-700">
                        {qualityHint}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
            {phase === 'form' ? (
              <div>
                <h3 className="text-lg font-bold mb-4 text-navy-dark">
                  手書きをドット絵キャラにするよ！
                </h3>
                <Button
                  onClick={() => void runGenerate()}
                  className="kid-button text-xl py-6 px-8"
                >
                  ✨ キャラクターを作る ✨
                </Button>
              </div>
            ) : (
              <div>
                <div className="text-6xl mb-4 animate-wiggle">🎨</div>
                <h3 className="text-lg font-bold mb-2 text-navy-dark">
                  ドット絵に変換しています...
                </h3>
                <p className="text-gray-600">もう少し待ってね！</p>
                {preprocessMeta?.hasContent === false && (
                  <p className="text-xs text-amber-700 mt-2">
                    線が検出しづらい画像です。明るい場所で撮り直すと精度が上がります。
                  </p>
                )}
                <div className="mt-4 flex justify-center">
                  <div className="animate-pulse flex space-x-2">
                    <div className="w-3 h-3 bg-pink-soft rounded-full"></div>
                    <div className="w-3 h-3 bg-sky-soft rounded-full animation-delay-200"></div>
                    <div className="w-3 h-3 bg-mint-soft rounded-full animation-delay-400"></div>
                  </div>
                </div>
              </div>
            )}
          </Card>
        )}
      </div>
    </div>
  );
};

export default UploadPage;
