import { Capacitor } from '@capacitor/core';

export type AppPlatform = 'web' | 'android' | 'ios';

export function getAppPlatform(): AppPlatform {
  const p = Capacitor.getPlatform();
  if (p === 'android' || p === 'ios') return p;
  return 'web';
}

export function isNativeApp(): boolean {
  return Capacitor.isNativePlatform();
}

export function isAndroidApp(): boolean {
  return Capacitor.getPlatform() === 'android';
}

export function isIosApp(): boolean {
  return Capacitor.getPlatform() === 'ios';
}

/** ネイティブアプリでは Health Connect / HealthKit を優先する */
export function prefersNativeHealthSync(): boolean {
  return isNativeApp();
}
