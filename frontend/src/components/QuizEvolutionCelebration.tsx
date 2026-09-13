import {
  EvolutionPreviewStrip,
  buildPreviewItems,
} from '@/components/EvolutionPreviewStrip';
import {
  STAGE_EMOJI,
  nextStageAfter,
  stageLabel,
  stagePreviewHint,
} from '@/lib/growthDisplay';
import { cn } from '@/lib/utils';

export type QuizEvolutionCelebrationData = {
  previousStage: string;
  newStage: string;
  imageUrl?: string | null;
  nextPreviewUrl?: string | null;
  heroPreviewUrl?: string | null;
};

type Props = {
  data: QuizEvolutionCelebrationData;
  className?: string;
};

export function QuizEvolutionCelebration({ data, className }: Props) {
  const prevLabel = stageLabel(data.previousStage);
  const newLabel = stageLabel(data.newStage);
  const prevEmoji = STAGE_EMOJI[data.previousStage] ?? '🌱';
  const newEmoji = STAGE_EMOJI[data.newStage] ?? '✨';
  const nextStage = nextStageAfter(data.newStage);

  const previewItems = buildPreviewItems({
    currentImageUrl: data.imageUrl ?? undefined,
    currentStage: data.newStage,
    currentHint: stagePreviewHint(data.newStage),
    nextImageUrl: data.nextPreviewUrl ?? undefined,
    nextStage: nextStage ?? undefined,
    nextHint: nextStage ? stagePreviewHint(nextStage) : undefined,
    heroImageUrl: data.heroPreviewUrl ?? undefined,
    heroHint: stagePreviewHint('hero'),
  });

  return (
    <div
      className={cn(
        'mb-4 rounded-2xl border-2 border-amber-300 bg-gradient-to-br from-amber-50 via-white to-mint-light/40 p-4 text-left shadow-md',
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <div className="text-center mb-3">
        <p className="text-4xl mb-2 quiz-pop" aria-hidden>
          ✨
        </p>
        <h3 className="text-xl font-bold text-navy-dark">進化したよ！</h3>
        <p className="text-sm font-semibold text-amber-800 mt-1">
          {prevEmoji} {prevLabel}
          <span className="mx-2 text-lavender-soft" aria-hidden>
            →
          </span>
          {newEmoji} {newLabel}
        </p>
      </div>

      {data.imageUrl && (
        <div className="mb-4 rounded-xl bg-white/90 border border-mint-soft/50 p-3 text-center">
          <p className="text-xs font-bold text-navy-dark mb-2">新しい姿</p>
          <img
            src={data.imageUrl}
            alt={`${newLabel}になったキャラ`}
            className="max-h-40 mx-auto rounded-xl border-2 border-sky-soft/40 shadow-sm"
            style={{ imageRendering: 'pixelated' }}
          />
        </div>
      )}

      {previewItems.length > 1 && (
        <EvolutionPreviewStrip
          title="この先の進化"
          size="md"
          items={previewItems.filter((item) => item.key !== 'current')}
        />
      )}

      {!data.imageUrl && (
        <p className="text-xs text-center text-gray-600 mt-2">
          手描きキャラを作ると、進化のたびに見た目も変わるよ！
        </p>
      )}
    </div>
  );
}
