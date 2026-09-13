import { getAuth } from 'firebase/auth';
import {
  checkNativeHealthAvailable,
  hasNativeHealthPermissionFlag,
  getNativeHealthSource,
  readNativeStepsWeek,
  requestNativeHealthPermissions,
  type NativeHealthSource,
} from './nativeHealth';
import { isNativeApp } from './platform';
import { syncStepsFromDevice } from './stepsApi';
import { jstYmd } from './stepsDisplay';

const THROTTLE_KEY = 'manatomo.health.autosync.v1';
const THROTTLE_MS = 15 * 60 * 1000;

export type NativeStepsSyncResult = {
  synced: boolean;
  todaySteps?: number;
  delta?: number;
  reason?: string;
  source?: NativeHealthSource;
};

function shouldAutoSyncNative(): boolean {
  try {
    const raw = localStorage.getItem(THROTTLE_KEY);
    if (!raw) return true;
    const last = Number(raw);
    if (!Number.isFinite(last)) return true;
    return Date.now() - last >= THROTTLE_MS;
  } catch {
    return true;
  }
}

export function markNativeAutoSynced(): void {
  try {
    localStorage.setItem(THROTTLE_KEY, String(Date.now()));
  } catch {
    /* ignore */
  }
}

export async function ensureNativeHealthReady(): Promise<boolean> {
  if (!isNativeApp()) return false;
  const availability = await checkNativeHealthAvailable();
  if (!availability.available) return false;
  if (hasNativeHealthPermissionFlag()) return true;
  return requestNativeHealthPermissions();
}

export async function syncNativeStepsToServer(opts?: {
  force?: boolean;
}): Promise<NativeStepsSyncResult> {
  const user = getAuth().currentUser;
  if (!user) return { synced: false, reason: 'not_logged_in' };
  if (!isNativeApp()) return { synced: false, reason: 'not_native' };
  if (!opts?.force && !shouldAutoSyncNative()) {
    return { synced: false, reason: 'throttled' };
  }

  const source = getNativeHealthSource();
  if (!source) return { synced: false, reason: 'unsupported_platform' };

  const ready = await ensureNativeHealthReady();
  if (!ready) return { synced: false, reason: 'permission_denied', source };

  try {
    const week = await readNativeStepsWeek(7);
    const days = week.filter((d) => d.steps > 0);
    if (days.length === 0) {
      const today = jstYmd();
      days.push({ ymd: today, steps: 0 });
    }

    const token = await user.getIdToken();
    const result = await syncStepsFromDevice(token, {
      source,
      days: days.map((d) => ({ ymd: d.ymd, steps: d.steps })),
    });
    markNativeAutoSynced();
    return {
      synced: true,
      todaySteps: result.today_steps,
      delta: result.delta_applied,
      source,
    };
  } catch (err) {
    return {
      synced: false,
      reason: err instanceof Error ? err.message : String(err),
      source,
    };
  }
}
