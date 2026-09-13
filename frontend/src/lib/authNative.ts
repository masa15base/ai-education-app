import type { Auth, AuthProvider, UserCredential } from 'firebase/auth';
import {
  getRedirectResult,
  signInWithPopup,
  signInWithRedirect,
} from 'firebase/auth';
import { isNativeApp } from './platform';

export async function signInWithProviderAdaptive(
  auth: Auth,
  provider: AuthProvider,
): Promise<UserCredential | null> {
  if (isNativeApp()) {
    await signInWithRedirect(auth, provider);
    return null;
  }
  return signInWithPopup(auth, provider);
}

export async function completeRedirectSignIn(
  auth: Auth,
): Promise<UserCredential | null> {
  if (!isNativeApp()) return null;
  try {
    return await getRedirectResult(auth);
  } catch {
    return null;
  }
}
