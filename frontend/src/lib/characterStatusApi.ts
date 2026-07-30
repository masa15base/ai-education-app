import { getAuth } from 'firebase/auth';
import { getApiBase } from './apiBase';
import type { NextEvolutionInfo } from './growthDisplay';

export type CharacterGrowthStatus = {
  character_id: string;
  display_name: string;
  image_url: string | null;
  stage: string;
  stage_label: string;
  level: number;
  exp: number;
  character_exp: number;
  exp_in_level: number;
  exp_to_next: number;
  quiz_correct_count: number;
  quiz_total_count: number;
  quiz_streak_days: number;
  total_steps: number;
  daily_steps: number;
  login_streak_days: number;
  quiz_today: boolean;
  mood: string;
  home_action: string;
  message: string;
  next_evolution: NextEvolutionInfo;
  current_stage_image?: string | null;
  hero_preview_url?: string | null;
  next_stage_preview_url?: string | null;
  final_hero_preview?: string | null;
};

async function withToken(): Promise<string> {
  const user = getAuth().currentUser;
  if (!user) throw new Error('Not signed in');
  return user.getIdToken(true);
}

export async function fetchCharacterGrowthStatus(): Promise<CharacterGrowthStatus | null> {
  const user = getAuth().currentUser;
  if (!user) return null;
  const token = await withToken();
  const res = await fetch(`${getApiBase()}/character/status`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  return (await res.json()) as CharacterGrowthStatus;
}

export async function postCharacterActivity(body: {
  activity_type: string;
  is_correct?: boolean;
  steps?: number;
  goal_reached?: boolean;
}): Promise<void> {
  const user = getAuth().currentUser;
  if (!user) return;
  const token = await withToken();
  await fetch(`${getApiBase()}/character/activity`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      user_id: user.uid,
      ...body,
    }),
  });
}

export const HOME_ACTION_ANIM: Record<string, string> = {
  idle: 'animate-char-idle',
  walking: 'animate-char-walking',
  studying: 'animate-char-studying',
  cheering: 'animate-char-cheering',
  celebrating: 'animate-char-celebrating',
  sleeping: 'animate-char-sleeping',
};

/** @deprecated prefer STAGE_EMOJI from growthDisplay */
export { STAGE_EMOJI } from './growthDisplay';
