import type { User } from "firebase/auth";
import { sendEmailVerification, type ActionCodeSettings } from "firebase/auth";
import { auth } from "@/firebaseConfig";

/** 確認メールのリンクから戻る先（Firebase Console の「承認済みドメイン」に含めること） */
export function emailVerificationContinueUrl(): string {
  const origin = window.location.origin.replace(/\/$/, "");
  return `${origin}/login?emailVerified=1`;
}

export function emailVerificationActionCodeSettings(): ActionCodeSettings {
  return {
    url: emailVerificationContinueUrl(),
    handleCodeInApp: false,
  };
}

export async function sendAccountVerificationEmail(user: User): Promise<void> {
  auth.languageCode = "ja";
  await sendEmailVerification(user, emailVerificationActionCodeSettings());
}

export function firebaseAuthErrorMessage(code: string, fallback: string): string {
  switch (code) {
    case "auth/too-many-requests":
      return "送信回数が多すぎます。しばらく待ってから「確認メールを再送」を押してください。";
    case "auth/invalid-continue-uri":
    case "auth/unauthorized-continue-uri":
      return "戻り先 URL が Firebase に登録されていません。Console の「承認済みドメイン」にこのサイトのドメイン（例: localhost）を追加してください。";
    case "auth/operation-not-allowed":
      return "メール/パスワード認証が無効です。Firebase Console で有効にしてください。";
    case "auth/network-request-failed":
      return "ネットワークエラーです。接続を確認してください。";
    default:
      return fallback;
  }
}
