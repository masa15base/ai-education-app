import { getAuth } from 'firebase/auth';
import {
  fetchFitnessStatus,
  markFitnessAutoSynced,
  shouldAutoSyncFitness,
  syncFitnessSteps,
} from './fitnessApi';
import { prefersNativeHealthSync } from './platform';
import { syncNativeStepsToServer } from './stepsNativeSync';

export type StepsAutoSyncResult = {
  synced: boolean;
  todaySteps?: number;
  delta?: number;
  reason?: string;
  channel?: 'native' | 'google_fit';
};

/** ネイティブ優先: Health Connect / HealthKit → Web: Google Fit（15分間隔） */
export async function autoSyncStepsIfNeeded(): Promise<StepsAutoSyncResult> {
  const user = getAuth().currentUser;
  if (!user) return { synced: false, reason: 'not_logged_in' };

  if (prefersNativeHealthSync()) {
    const native = await syncNativeStepsToServer();
    return {
      synced: native.synced,
      todaySteps: native.todaySteps,
      delta: native.delta,
      reason: native.reason,
      channel: 'native',
    };
  }

  if (!shouldAutoSyncFitness()) {
    return { synced: false, reason: 'throttled', channel: 'google_fit' };
  }

  try {
    const token = await user.getIdToken();
    const status = await fetchFitnessStatus(token);
    if (!status.configured) {
      return { synced: false, reason: 'not_configured', channel: 'google_fit' };
    }
    if (!status.connected) {
      return { synced: false, reason: 'not_connected', channel: 'google_fit' };
    }

    const result = await syncFitnessSteps(token);
    markFitnessAutoSynced();
    return {
      synced: true,
      todaySteps: result.today_steps,
      delta: result.delta_applied,
      channel: 'google_fit',
    };
  } catch (err) {
    return {
      synced: false,
      reason: err instanceof Error ? err.message : String(err),
      channel: 'google_fit',
    };
  }
}

/** @deprecated autoSyncStepsIfNeeded を使用 */
export async function autoSyncFitnessStepsIfNeeded(): Promise<StepsAutoSyncResult> {
  return autoSyncStepsIfNeeded();
}
