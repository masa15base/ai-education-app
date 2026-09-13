import { getAuth } from 'firebase/auth';
import {
  fetchFitnessStatus,
  markFitnessAutoSynced,
  shouldAutoSyncFitness,
  syncFitnessSteps,
} from './fitnessApi';

export type StepsAutoSyncResult = {
  synced: boolean;
  todaySteps?: number;
  delta?: number;
  reason?: string;
};

/** Google Fit 連携済みなら歩数を自動同期（15分間隔） */
export async function autoSyncFitnessStepsIfNeeded(): Promise<StepsAutoSyncResult> {
  const user = getAuth().currentUser;
  if (!user) return { synced: false, reason: 'not_logged_in' };
  if (!shouldAutoSyncFitness()) return { synced: false, reason: 'throttled' };

  try {
    const token = await user.getIdToken();
    const status = await fetchFitnessStatus(token);
    if (!status.configured) return { synced: false, reason: 'not_configured' };
    if (!status.connected) return { synced: false, reason: 'not_connected' };

    const result = await syncFitnessSteps(token);
    markFitnessAutoSynced();
    return {
      synced: true,
      todaySteps: result.today_steps,
      delta: result.delta_applied,
    };
  } catch (err) {
    return {
      synced: false,
      reason: err instanceof Error ? err.message : String(err),
    };
  }
}
