import { getAuth } from 'firebase/auth';
import { fetchProgress } from '@/lib/api';
import {
  DEFAULT_CHARACTER,
  fetchCharacterFromServer,
  loadCharacter,
} from '@/lib/characterState';

const STORAGE_KEY = 'manatomo.onboarding.v1';

type OnboardingStore = Record<string, { completedAt: string }>;

function readStore(): OnboardingStore {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as OnboardingStore;
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function writeStore(store: OnboardingStore) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  } catch {
    /* ignore quota */
  }
}

export function isOnboardingComplete(uid: string): boolean {
  if (!uid) return false;
  return Boolean(readStore()[uid]?.completedAt);
}

export function markOnboardingComplete(uid: string): void {
  if (!uid) return;
  const store = readStore();
  store[uid] = { completedAt: new Date().toISOString() };
  writeStore(store);
}

export function clearOnboardingComplete(uid: string): void {
  if (!uid) return;
  const store = readStore();
  delete store[uid];
  writeStore(store);
}

/**
 * 既存ユーザー（経験値あり / 学習履歴あり）は自動で完了扱いにしてスキップ。
 * 初回・ほぼ未使用ユーザーだけオンボーディングへ。
 */
export async function resolveNeedsOnboarding(uid: string): Promise<boolean> {
  if (!uid) return false;
  if (isOnboardingComplete(uid)) return false;

  await fetchCharacterFromServer();
  const char = loadCharacter();
  if (char.experience > 0) {
    markOnboardingComplete(uid);
    return false;
  }
  if (
    char.imageUrl &&
    char.displayName.trim() &&
    char.displayName !== DEFAULT_CHARACTER.displayName
  ) {
    markOnboardingComplete(uid);
    return false;
  }

  try {
    const progress = await fetchProgress();
    if (Array.isArray(progress.items) && progress.items.length > 0) {
      markOnboardingComplete(uid);
      return false;
    }
  } catch {
    /* オフライン等はオンボーディングを出す（安全側） */
  }

  return true;
}

export async function resolvePostLoginPath(): Promise<'/onboarding' | '/'> {
  const user = getAuth().currentUser;
  if (!user) return '/';
  const needs = await resolveNeedsOnboarding(user.uid);
  return needs ? '/onboarding' : '/';
}

export function normalizeBuddyName(raw: string): string {
  return raw.trim().replace(/\s+/g, ' ').slice(0, 20);
}

export function isValidBuddyName(name: string): boolean {
  const n = normalizeBuddyName(name);
  return n.length >= 1 && n.length <= 20;
}
