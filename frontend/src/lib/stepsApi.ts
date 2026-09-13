import { getApiBase } from './apiBase';

export type StepsTodayResponse = {
  authenticated: boolean;
  today_ymd: string;
  goal_steps: number;
  steps: number | null;
  source: string;
  hint?: string | null;
};

export type StepsWeekDay = {
  date: string;
  steps: number;
  goal_reached: boolean;
};

export type StepsWeekResponse = {
  authenticated: boolean;
  today_ymd: string;
  goal_steps: number;
  source: string;
  days: StepsWeekDay[];
};

export async function fetchStepsToday(
  idToken: string | null | undefined,
): Promise<StepsTodayResponse> {
  const headers: Record<string, string> = {};
  if (idToken) headers.Authorization = `Bearer ${idToken}`;
  const res = await fetch(`${getApiBase()}/steps/today`, { headers });
  const text = await res.text();
  if (!res.ok) throw new Error(`${res.status} ${text.slice(0, 200)}`);
  return JSON.parse(text || '{}') as StepsTodayResponse;
}

export async function fetchStepsWeek(
  idToken: string | null | undefined,
): Promise<StepsWeekResponse> {
  const headers: Record<string, string> = {};
  if (idToken) headers.Authorization = `Bearer ${idToken}`;
  const res = await fetch(`${getApiBase()}/steps/week`, { headers });
  const text = await res.text();
  if (!res.ok) throw new Error(`${res.status} ${text.slice(0, 200)}`);
  return JSON.parse(text || '{}') as StepsWeekResponse;
}

export type StepsSyncDeviceResponse = {
  source: string;
  today_ymd: string;
  today_steps: number;
  delta_applied: number;
  synced_days: Array<{ date: string; steps: number; delta_applied: number }>;
};

export async function syncStepsFromDevice(
  idToken: string,
  body: {
    source: 'health_connect' | 'healthkit';
    days: Array<{ ymd: string; steps: number }>;
  },
): Promise<StepsSyncDeviceResponse> {
  const res = await fetch(`${getApiBase()}/steps/sync-from-device`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${idToken}`,
    },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`${res.status} ${text.slice(0, 200)}`);
  return JSON.parse(text || '{}') as StepsSyncDeviceResponse;
}

export async function putStepsToday(
  idToken: string,
  steps: number,
): Promise<{ today_ymd: string; steps: number; source: string }> {
  const res = await fetch(`${getApiBase()}/steps/today`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${idToken}`,
    },
    body: JSON.stringify({ steps }),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`${res.status} ${text.slice(0, 200)}`);
  return JSON.parse(text || '{}') as {
    today_ymd: string;
    steps: number;
    source: string;
  };
}
