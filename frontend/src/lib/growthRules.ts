/** 歩数目標（UI・サーバの steps API と揃える） */
export const DEFAULT_STEPS_GOAL = 5000;

/** ホームのキャラ枠用: Lv に応じた見た目段階 */
export function characterVisualTier(level: number): 1 | 2 | 3 {
  if (level >= 16) return 3;
  if (level >= 6) return 2;
  return 1;
}
