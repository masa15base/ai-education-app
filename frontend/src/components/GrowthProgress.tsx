import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import {
  GROWTH_STAGES,
  STAGE_EMOJI,
  STAGE_LABEL_JA,
  evolutionRequirements,
  formatRequirementValue,
  requirementHint,
  stageIndex,
  stageLabel,
  type NextEvolutionInfo,
  type GrowthStageId,
} from "@/lib/growthDisplay";

type Props = {
  currentStage: string;
  nextEvolution?: NextEvolutionInfo | null;
  compact?: boolean;
  className?: string;
};

export function GrowthStageRoadmap({
  currentStage,
  nextEvolution,
  compact = false,
  className,
}: Props) {
  const idx = stageIndex(currentStage);
  return (
    <div className={cn("w-full", className)}>
      <p className={cn("font-bold text-navy-dark mb-3", compact ? "text-sm" : "text-base")}>
        成長の道すじ
      </p>
      <div className="flex items-center justify-between gap-1 overflow-x-auto pb-1">
        {GROWTH_STAGES.map((id, i) => {
          const reached = i <= idx;
          const current = i === idx;
          return (
            <div key={id} className="flex items-center flex-1 min-w-0">
              <div
                className={cn(
                  "flex flex-col items-center text-center px-1 flex-1",
                  current && "scale-110",
                )}
              >
                <span
                  className={cn(
                    "text-2xl sm:text-3xl rounded-full w-12 h-12 flex items-center justify-center border-2",
                    reached
                      ? "bg-mint-soft/40 border-mint-soft"
                      : "bg-gray-100 border-gray-200 opacity-50",
                    current && "ring-2 ring-lavender-soft border-lavender-soft",
                  )}
                  aria-hidden
                >
                  {STAGE_EMOJI[id]}
                </span>
                <span
                  className={cn(
                    "text-[10px] sm:text-xs mt-1 font-bold truncate w-full",
                    current ? "text-lavender-soft" : reached ? "text-navy-dark" : "text-gray-400",
                  )}
                >
                  {STAGE_LABEL_JA[id as GrowthStageId]}
                </span>
                {current && (
                  <span className="text-[10px] text-lavender-soft font-bold">いま</span>
                )}
              </div>
              {i < GROWTH_STAGES.length - 1 && (
                <div
                  className={cn(
                    "h-1 w-3 sm:w-5 rounded-full shrink-0",
                    i < idx ? "bg-mint-soft" : "bg-gray-200",
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
      {nextEvolution?.complete ? (
        <p className="text-center text-sm font-bold text-amber-700 mt-3">
          ヒーローまで進化したよ！すごい！
        </p>
      ) : nextEvolution?.next_stage ? (
        <p className="text-center text-sm text-navy-dark mt-3">
          次は{" "}
          <span className="font-bold text-sky-soft">
            {nextEvolution.next_stage_label || stageLabel(nextEvolution.next_stage)}
          </span>{" "}
          だよ
        </p>
      ) : null}
    </div>
  );
}

export function EvolutionProgressCard({
  nextEvolution,
  className,
}: {
  nextEvolution?: NextEvolutionInfo | null;
  className?: string;
}) {
  const navigate = useNavigate();
  if (!nextEvolution || nextEvolution.complete) {
    return (
      <div
        className={cn(
          "rounded-2xl bg-gradient-to-r from-amber-50 to-yellow-50 border border-amber-200 p-4 text-center",
          className,
        )}
      >
        <p className="text-3xl mb-2">🏆</p>
        <p className="font-bold text-amber-800">最高ステージ到達！</p>
        <p className="text-sm text-amber-900/80 mt-1">
          クイズや歩数で、さらに強くなれるよ
        </p>
      </div>
    );
  }

  const reqs = evolutionRequirements(nextEvolution);
  const nextName =
    nextEvolution.next_stage_label || stageLabel(nextEvolution.next_stage);

  return (
    <div
      className={cn(
        "rounded-2xl bg-sky-soft/25 border border-sky-soft/40 p-4 text-left text-navy-dark",
        className,
      )}
    >
      <p className="font-bold mb-1">次の進化まで</p>
      <p className="text-sm mb-3">
        目標: <span className="font-bold text-sky-700">{nextName}</span>
      </p>
      <ul className="space-y-3">
        {reqs.map((req) => {
          const hint = requirementHint(req);
          const pct = Math.round((req.progress || 0) * 100);
          return (
            <li key={req.key}>
              <div className="flex justify-between text-xs font-bold mb-1 gap-2">
                <span>
                  {req.done ? "✓ " : ""}
                  {req.label}
                </span>
                <span className={req.done ? "text-green-700" : "text-orange-700"}>
                  {formatRequirementValue(req)}
                </span>
              </div>
              <Progress value={pct} className="h-2 bg-white/70" />
              {!req.done && (
                <div className="mt-1 flex justify-between items-center">
                  <span className="text-[11px] text-gray-600">
                    あと{" "}
                    {req.key === "has_character_image"
                      ? "画像が必要"
                      : req.key === "total_steps"
                        ? `${Number(req.remaining).toLocaleString()} 歩`
                        : req.key === "quiz_streak_days"
                          ? `${req.remaining} 日`
                          : req.key === "character_exp"
                            ? `${req.remaining} EXP`
                            : `${req.remaining} 問`}
                  </span>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs rounded-full"
                    onClick={() => navigate(hint.path)}
                  >
                    {hint.cta}
                  </Button>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
