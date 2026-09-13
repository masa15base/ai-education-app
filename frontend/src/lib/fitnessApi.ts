import { getApiBase } from './apiBase';

export type FitnessStatus = {
  configured: boolean;
  connected: boolean;
  provider?: string | null;
  last_sync_at?: string | null;
  hint?: string | null;
};

export type FitnessSyncResult = {
  provider: string;
  today_ymd: string;
  today_steps: number;
  imported_today: number;
  delta_applied: number;
  synced_days: Array<{ date: string; steps: number; imported: number }>;
};

async function authHeaders(token: string): Promise<Record<string, string>> {
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

export async function fetchFitnessStatus(token: string): Promise<FitnessStatus> {
  const res = await fetch(`${getApiBase()}/fitness/status`, {
    headers: await authHeaders(token),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`${res.status} ${text.slice(0, 200)}`);
  return JSON.parse(text || '{}') as FitnessStatus;
}

export async function fetchFitnessConnectUrl(token: string): Promise<string> {
  const res = await fetch(`${getApiBase()}/fitness/connect-url`, {
    headers: await authHeaders(token),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`${res.status} ${text.slice(0, 200)}`);
  const body = JSON.parse(text || '{}') as { url?: string };
  if (!body.url) throw new Error('connect url missing');
  return body.url;
}

export async function syncFitnessSteps(token: string): Promise<FitnessSyncResult> {
  const res = await fetch(`${getApiBase()}/fitness/sync`, {
    method: 'POST',
    headers: await authHeaders(token),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`${res.status} ${text.slice(0, 200)}`);
  return JSON.parse(text || '{}') as FitnessSyncResult;
}

export async function disconnectFitness(token: string): Promise<void> {
  const res = await fetch(`${getApiBase()}/fitness/disconnect`, {
    method: 'DELETE',
    headers: await authHeaders(token),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${text.slice(0, 200)}`);
  }
}

const AUTO_SYNC_KEY = 'manatomo.fitness.lastAutoSyncMs';
const AUTO_SYNC_INTERVAL_MS = 15 * 60 * 1000;

export function shouldAutoSyncFitness(): boolean {
  const raw = sessionStorage.getItem(AUTO_SYNC_KEY);
  if (!raw) return true;
  const last = Number(raw);
  if (!Number.isFinite(last)) return true;
  return Date.now() - last >= AUTO_SYNC_INTERVAL_MS;
}

export function markFitnessAutoSynced(): void {
  sessionStorage.setItem(AUTO_SYNC_KEY, String(Date.now()));
}
