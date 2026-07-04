import { getAuth } from "firebase/auth";
import { getApiBase } from "./apiBase";

/** メモリのみ（localStorage は使わない。本番は Heroku DB が正） */
let characterMemory: CharacterState | null = null;

export type CharacterState = {
  displayName: string;
  imageUrl: string | null;
  experience: number;
  heroPreviewUrl?: string | null;
  nextEvolutionPreviewUrl?: string | null;
};

export const DEFAULT_CHARACTER: CharacterState = {
  displayName: "みーちゃん",
  imageUrl: null,
  experience: 0,
};

export function levelFromExperience(xp: number): number {
  return Math.min(99, Math.max(1, 1 + Math.floor(xp / 100)));
}

export function progressInCurrentLevel(xp: number): number {
  return xp % 100;
}

function memoryOrDefault(): CharacterState {
  return characterMemory ? { ...characterMemory } : { ...DEFAULT_CHARACTER };
}

/** 画面表示用（ログイン直後は fetch するまでデフォルトのことがある） */
export function loadCharacter(): CharacterState {
  return memoryOrDefault();
}

export function setCharacterMemory(c: CharacterState | null): void {
  characterMemory = c ? { ...c } : null;
}

async function authHeader(): Promise<string | null> {
  const u = getAuth().currentUser;
  if (!u) return null;
  return `Bearer ${await u.getIdToken(true)}`;
}

/** ログイン中: GET /api/character。404 は「未登録」としてデフォルト表示用メモリにする */
export async function fetchCharacterFromServer(): Promise<boolean> {
  const h = await authHeader();
  if (!h) {
    setCharacterMemory(null);
    return false;
  }
  try {
    const r = await fetch(`${getApiBase()}/character`, {
      headers: { Authorization: h },
    });
    if (r.status === 404) {
      setCharacterMemory({ ...DEFAULT_CHARACTER });
      return true;
    }
    if (!r.ok) return false;
    const d = (await r.json()) as {
      display_name: string;
      image_url: string | null;
      experience: number;
    };
    setCharacterMemory({
      displayName: d.display_name,
      imageUrl: d.image_url,
      experience: d.experience,
    });
    return true;
  } catch {
    return false;
  }
}

/** @deprecated 互換名 — fetchCharacterFromServer を使う */
export async function pullCharacterFromServer(): Promise<boolean> {
  return fetchCharacterFromServer();
}

export async function pushCharacterToServer(c: CharacterState): Promise<boolean> {
  const h = await authHeader();
  if (!h) return false;
  try {
    const r = await fetch(`${getApiBase()}/character`, {
      method: "PUT",
      headers: { Authorization: h, "Content-Type": "application/json" },
      body: JSON.stringify({
        display_name: c.displayName,
        image_url: c.imageUrl,
        experience: c.experience,
        hero_preview_url: c.heroPreviewUrl ?? null,
        next_stage_preview_url: c.nextEvolutionPreviewUrl ?? null,
      }),
    });
    if (!r.ok) return false;
    const d = (await r.json()) as {
      display_name: string;
      image_url: string | null;
      experience: number;
    };
    setCharacterMemory({
      displayName: d.display_name,
      imageUrl: d.image_url,
      experience: d.experience,
      heroPreviewUrl: c.heroPreviewUrl ?? null,
      nextEvolutionPreviewUrl: c.nextEvolutionPreviewUrl ?? null,
    });
    return true;
  } catch {
    return false;
  }
}

export function patchCharacter(p: Partial<CharacterState>): CharacterState {
  const cur = memoryOrDefault();
  const next: CharacterState = {
    displayName: p.displayName ?? cur.displayName,
    imageUrl: p.imageUrl !== undefined ? p.imageUrl : cur.imageUrl,
    experience:
      p.experience !== undefined ? Math.max(0, p.experience) : cur.experience,
    heroPreviewUrl:
      p.heroPreviewUrl !== undefined ? p.heroPreviewUrl : cur.heroPreviewUrl,
    nextEvolutionPreviewUrl:
      p.nextEvolutionPreviewUrl !== undefined
        ? p.nextEvolutionPreviewUrl
        : cur.nextEvolutionPreviewUrl,
  };
  setCharacterMemory(next);
  return next;
}
