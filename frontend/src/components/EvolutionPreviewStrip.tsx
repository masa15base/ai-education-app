import { cn } from '@/lib/utils';
import { STAGE_EMOJI, stageLabel } from '@/lib/growthDisplay';

export type EvolutionPreviewItem = {
  key: string;
  label: string;
  emoji?: string;
  imageUrl: string;
  hint?: string;
  tone?: 'current' | 'next' | 'hero';
};

type Props = {
  items: EvolutionPreviewItem[];
  title?: string;
  className?: string;
  size?: 'md' | 'lg';
};

const toneClass: Record<NonNullable<EvolutionPreviewItem['tone']>, string> = {
  current: 'border-slate-300 bg-slate-50',
  next: 'border-blue-200 bg-blue-50',
  hero: 'border-slate-400 bg-slate-100',
};

export function EvolutionPreviewStrip({
  items,
  title = '進化プレビュー',
  className,
  size = 'lg',
}: Props) {
  if (!items.length) return null;

  const box = size === 'lg' ? 'h-36 w-36' : 'h-28 w-28';

  return (
    <div
      className={cn(
        'rounded-2xl bg-white p-4 border border-slate-200',
        className,
      )}
    >
      <p className="text-sm font-bold text-navy-dark mb-1">{title}</p>
      <p className="text-xs text-gray-600 mb-4">
        左から右へ成長していくよ。矢印の先が次の姿！
      </p>
      <div className="flex justify-center items-start gap-3 flex-wrap">
        {items.map((item, index) => (
          <div key={item.key} className="flex items-center gap-3">
            {index > 0 && (
              <span className="text-2xl text-slate-400 select-none" aria-hidden>
                →
              </span>
            )}
            <div className="text-center max-w-[9.5rem]">
              <p className="text-xs font-bold text-navy-dark mb-1">
                {item.emoji ? `${item.emoji} ` : ''}
                {item.label}
              </p>
              <div
                className={cn(
                  'mx-auto rounded-xl border-2 p-2 shadow-sm',
                  box,
                  toneClass[item.tone ?? 'next'],
                )}
              >
                <img
                  src={item.imageUrl}
                  alt={item.label}
                  className="h-full w-full object-contain"
                  style={{ imageRendering: 'pixelated' }}
                />
              </div>
              {item.hint && (
                <p className="text-[11px] text-gray-600 mt-2 leading-snug">{item.hint}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function buildPreviewItems(opts: {
  currentImageUrl?: string | null;
  currentStage?: string | null;
  currentHint?: string | null;
  nextImageUrl?: string | null;
  nextStage?: string | null;
  nextHint?: string | null;
  heroImageUrl?: string | null;
  heroHint?: string | null;
}): EvolutionPreviewItem[] {
  const items: EvolutionPreviewItem[] = [];
  if (opts.currentImageUrl) {
    const stage = opts.currentStage ?? 'baby';
    items.push({
      key: 'current',
      label: `いま（${stageLabel(stage)}）`,
      emoji: STAGE_EMOJI[stage] ?? '🌱',
      imageUrl: opts.currentImageUrl,
      hint: opts.currentHint ?? undefined,
      tone: 'current',
    });
  }
  if (opts.nextImageUrl) {
    const stage = opts.nextStage ?? 'child';
    items.push({
      key: 'next',
      label: `次（${stageLabel(stage)}）`,
      emoji: STAGE_EMOJI[stage] ?? '🐣',
      imageUrl: opts.nextImageUrl,
      hint: opts.nextHint ?? undefined,
      tone: 'next',
    });
  }
  if (opts.heroImageUrl) {
    items.push({
      key: 'hero',
      label: 'ヒーロー',
      emoji: STAGE_EMOJI.hero,
      imageUrl: opts.heroImageUrl,
      hint: opts.heroHint ?? 'マントと王冠の最終形',
      tone: 'hero',
    });
  }
  return items;
}
