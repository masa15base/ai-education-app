import { isNativeApp, isAndroidApp, isIosApp } from './platform';
import { jstYmd } from './stepsDisplay';

export type NativeHealthSource = 'health_connect' | 'healthkit';

export type NativeHealthAvailability = {
  available: boolean;
  source: NativeHealthSource | null;
  reason?: string;
};

export type NativeHealthDay = {
  ymd: string;
  steps: number;
};

const PERM_KEY = 'manatomo.health.permissions.v1';

export function getNativeHealthSource(): NativeHealthSource | null {
  if (isAndroidApp()) return 'health_connect';
  if (isIosApp()) return 'healthkit';
  return null;
}

async function loadHealthModule() {
  const mod = await import('@capgo/capacitor-health');
  return mod.Health;
}

export function jstDayStartIso(ymd: string): string {
  return `${ymd}T00:00:00+09:00`;
}

export function jstDayEndIso(ymd: string): string {
  return `${ymd}T23:59:59.999+09:00`;
}

function sampleYmd(iso: string): string {
  return jstYmd(new Date(iso));
}

export async function checkNativeHealthAvailable(): Promise<NativeHealthAvailability> {
  const source = getNativeHealthSource();
  if (!isNativeApp() || !source) {
    return { available: false, source: null, reason: 'web' };
  }
  try {
    const Health = await loadHealthModule();
    const result = await Health.isAvailable();
    return {
      available: result.available,
      source,
      reason: result.reason,
    };
  } catch (err) {
    return {
      available: false,
      source,
      reason: err instanceof Error ? err.message : String(err),
    };
  }
}

export function hasNativeHealthPermissionFlag(): boolean {
  try {
    return localStorage.getItem(PERM_KEY) === '1';
  } catch {
    return false;
  }
}

export function markNativeHealthPermissionGranted(): void {
  try {
    localStorage.setItem(PERM_KEY, '1');
  } catch {
    /* ignore */
  }
}

export async function requestNativeHealthPermissions(): Promise<boolean> {
  if (!isNativeApp()) return false;
  try {
    const Health = await loadHealthModule();
    const availability = await Health.isAvailable();
    if (!availability.available) return false;

    await Health.requestAuthorization({
      read: ['steps'],
      write: [],
    });
    markNativeHealthPermissionGranted();
    return true;
  } catch {
    return false;
  }
}

export async function readNativeStepsForDay(ymd: string): Promise<number> {
  const Health = await loadHealthModule();
  const { samples } = await Health.queryAggregated({
    dataType: 'steps',
    startDate: jstDayStartIso(ymd),
    endDate: jstDayEndIso(ymd),
    bucket: 'day',
    aggregation: 'sum',
  });
  const match = samples.find((s) => sampleYmd(s.startDate) === ymd);
  if (match) return Math.round(Number(match.value) || 0);

  const fallback = await Health.readSamples({
    dataType: 'steps',
    startDate: jstDayStartIso(ymd),
    endDate: jstDayEndIso(ymd),
    limit: 500,
  });
  return fallback.samples.reduce(
    (sum, s) => sum + Math.round(Number(s.value) || 0),
    0,
  );
}

export async function readNativeStepsWeek(days = 7): Promise<NativeHealthDay[]> {
  const Health = await loadHealthModule();
  const endYmd = jstYmd();
  const endDate = new Date();
  const startDate = new Date(endDate.getTime() - days * 24 * 60 * 60 * 1000);

  const { samples } = await Health.queryAggregated({
    dataType: 'steps',
    startDate: startDate.toISOString(),
    endDate: endDate.toISOString(),
    bucket: 'day',
    aggregation: 'sum',
  });

  const byYmd = new Map<string, number>();
  for (const sample of samples) {
    const ymd = sampleYmd(sample.startDate);
    byYmd.set(ymd, Math.round(Number(sample.value) || 0));
  }

  const keys: string[] = [];
  for (let i = days - 1; i >= 0; i -= 1) {
    const d = new Date(endDate.getTime() - i * 24 * 60 * 60 * 1000);
    keys.push(jstYmd(d));
  }

  return keys.map((ymd) => ({
    ymd,
    steps: byYmd.get(ymd) ?? (ymd === endYmd ? 0 : byYmd.get(ymd) ?? 0),
  }));
}

export async function openNativeHealthSettings(): Promise<void> {
  if (!isAndroidApp()) return;
  const Health = await loadHealthModule();
  await Health.openHealthConnectSettings();
}

export function nativeHealthLabel(): string {
  if (isAndroidApp()) return 'Health Connect';
  if (isIosApp()) return 'ヘルスケア';
  return '端末の健康データ';
}
