/** 成長ステージ表示用の共通定義・整形 */

export const GROWTH_STAGES = ["egg", "baby", "child", "student", "hero"] as const;
export type GrowthStageId = (typeof GROWTH_STAGES)[number];

export const STAGE_LABEL_JA: Record<GrowthStageId, string> = {
  egg: "たまご",
  baby: "ベビー",
  child: "こども",
  student: "がくせい",
  hero: "ヒーロー",
};

export const STAGE_EMOJI: Record<string, string> = {
  egg: "🥚",
  baby: "🌱",
  child: "🐣",
  student: "📚",
  hero: "⭐",
};

export type EvolutionRequirement = {
  key: string;
  label: string;
  required: number | boolean;
  current: number | boolean;
  remaining: number;
  progress: number;
  done: boolean;
};

export type NextEvolutionInfo = {
  next_stage?: string | null;
  next_stage_label?: string | null;
  current_stage?: string;
  current_stage_label?: string;
  complete?: boolean;
  requirements?: EvolutionRequirement[];
  remaining_exp?: number;
  required_exp?: number;
  remaining_character_exp?: number;
  required_character_exp?: number;
  remaining_quiz_correct_count?: number;
  remaining_total_steps?: number;
  remaining_quiz_streak_days?: number;
  remaining_has_character_image?: number;
  [key: string]: unknown;
};

export function stageLabel(stage: string | null | undefined): string {
  if (!stage) return "—";
  return STAGE_LABEL_JA[stage as GrowthStageId] ?? stage;
}

export function stageIndex(stage: string | null | undefined): number {
  const i = GROWTH_STAGES.indexOf((stage || "egg") as GrowthStageId);
  return i >= 0 ? i : 0;
}

/** API の next_evolution から要件リストを組み立て（旧フィールド互換） */
export function evolutionRequirements(
  next: NextEvolutionInfo | null | undefined,
): EvolutionRequirement[] {
  if (!next || next.complete) return [];
  if (Array.isArray(next.requirements) && next.requirements.length > 0) {
    return next.requirements;
  }

  const rows: EvolutionRequirement[] = [];
  if (typeof next.remaining_has_character_image === "number") {
    const remaining = next.remaining_has_character_image;
    rows.push({
      key: "has_character_image",
      label: "キャラ画像",
      required: true,
      current: remaining === 0,
      remaining,
      progress: remaining === 0 ? 1 : 0,
      done: remaining === 0,
    });
  }
  const expRem =
    typeof next.remaining_exp === "number"
      ? next.remaining_exp
      : typeof next.remaining_character_exp === "number"
        ? next.remaining_character_exp
        : null;
  const expReq =
    typeof next.required_exp === "number"
      ? next.required_exp
      : typeof next.required_character_exp === "number"
        ? Number(next.required_character_exp)
        : null;
  if (expRem != null && expReq != null) {
    const current = Math.max(0, expReq - expRem);
    rows.push({
      key: "character_exp",
      label: "経験値",
      required: expReq,
      current,
      remaining: expRem,
      progress: expReq ? Math.min(1, current / expReq) : 1,
      done: expRem === 0,
    });
  }
  if (typeof next.remaining_quiz_correct_count === "number") {
    const rem = next.remaining_quiz_correct_count;
    const req = Number(next.required_quiz_correct_count ?? rem);
    const current = Math.max(0, req - rem);
    rows.push({
      key: "quiz_correct_count",
      label: "クイズ正解",
      required: req,
      current,
      remaining: rem,
      progress: req ? Math.min(1, current / req) : 1,
      done: rem === 0,
    });
  }
  if (typeof next.remaining_total_steps === "number") {
    const rem = next.remaining_total_steps;
    const req = Number(next.required_total_steps ?? rem);
    const current = Math.max(0, req - rem);
    rows.push({
      key: "total_steps",
      label: "累計歩数",
      required: req,
      current,
      remaining: rem,
      progress: req ? Math.min(1, current / req) : 1,
      done: rem === 0,
    });
  }
  if (typeof next.remaining_quiz_streak_days === "number") {
    const rem = next.remaining_quiz_streak_days;
    const req = Number(next.required_quiz_streak_days ?? rem);
    const current = Math.max(0, req - rem);
    rows.push({
      key: "quiz_streak_days",
      label: "クイズ連続日数",
      required: req,
      current,
      remaining: rem,
      progress: req ? Math.min(1, current / req) : 1,
      done: rem === 0,
    });
  }
  return rows;
}

export function requirementHint(req: EvolutionRequirement): {
  cta: string;
  path: string;
} {
  switch (req.key) {
    case "has_character_image":
      return { cta: "キャラをつくる", path: "/upload" };
    case "quiz_correct_count":
    case "quiz_streak_days":
    case "character_exp":
      return { cta: "クイズに挑戦", path: "/quiz" };
    case "total_steps":
      return { cta: "ホームで歩数", path: "/" };
    default:
      return { cta: "ホームへ", path: "/" };
  }
}

export function formatRequirementValue(req: EvolutionRequirement): string {
  if (req.key === "has_character_image") {
    return req.done ? "できてる ✓" : "まだだよ";
  }
  const cur = typeof req.current === "number" ? req.current : 0;
  const need = typeof req.required === "number" ? req.required : 0;
  if (req.key === "total_steps") {
    return `${cur.toLocaleString()} / ${need.toLocaleString()} 歩`;
  }
  if (req.key === "character_exp") {
    return `${cur} / ${need} EXP`;
  }
  if (req.key === "quiz_correct_count") {
    return `${cur} / ${need} 問`;
  }
  if (req.key === "quiz_streak_days") {
    return `${cur} / ${need} 日`;
  }
  return `${cur} / ${need}`;
}
