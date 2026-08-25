import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { auth } from "@/firebaseConfig";
import type { User } from "firebase/auth";
import {
  applyActionCode,
  onAuthStateChanged,
  signOut,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  GoogleAuthProvider,
  FacebookAuthProvider,
  TwitterAuthProvider,
  signInWithPopup,
} from "firebase/auth";
import {
  firebaseAuthErrorMessage,
  sendAccountVerificationEmail,
} from "@/lib/emailVerification";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { toast } from "@/hooks/use-toast";
import { saveProgress } from "@/lib/api";
import { fetchCharacterFromServer } from "@/lib/characterState";
import { resolvePostLoginPath } from "@/lib/onboarding";

const loginInputClass =
  "mb-3 border-2 border-black bg-white text-black placeholder:text-gray-600 focus-visible:ring-black focus-visible:border-black";

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionUser, setSessionUser] = useState<User | null>(() => auth.currentUser);
  const [pendingVerificationEmail, setPendingVerificationEmail] = useState<string | null>(
    null,
  );

  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    const mode = searchParams.get("mode");
    const oobCode = searchParams.get("oobCode");
    if (oobCode && mode === "verifyEmail") {
      void (async () => {
        try {
          await applyActionCode(auth, oobCode);
          toast({
            title: "メール認証が完了しました",
            description: "メールとパスワードでログインしてください。",
          });
        } catch (error: unknown) {
          const code =
            typeof error === "object" && error && "code" in error
              ? String((error as { code?: string }).code)
              : "";
          const msg = error instanceof Error ? error.message : String(error);
          toast({
            title: "認証リンクが無効です",
            description: firebaseAuthErrorMessage(code, msg),
            variant: "destructive",
          });
        } finally {
          setSearchParams({}, { replace: true });
        }
      })();
      return;
    }
    if (searchParams.get("emailVerified") === "1") {
      toast({
        title: "メール認証が完了しました",
        description: "この画面から「メールでログイン」してください。",
      });
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (user) => {
      if (user?.email && !user.emailVerified && user.providerData.some((p) => p.providerId === "password")) {
        setSessionUser(null);
        return;
      }
      setSessionUser(user);
    });
    return () => unsub();
  }, []);

  const handleLogout = async () => {
    try {
      setBusy(true);
      await signOut(auth);
      setPendingVerificationEmail(null);
      toast({ title: "ログアウトしました" });
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      toast({ title: "ログアウト失敗", description: msg, variant: "destructive" });
    } finally {
      setBusy(false);
    }
  };

  const afterAuthSuccess = async () => {
    const pulled = await fetchCharacterFromServer();
    const dest = await resolvePostLoginPath();
    toast({
      title: "ログインしました",
      description:
        dest === "/onboarding"
          ? "はじめてガイドへ進むよ"
          : pulled
            ? "クラウドのキャラ情報を読み込みました"
            : "ホームであそんでね",
    });
    navigate(dest, { replace: true });
  };

  const ensureEmailVerifiedForLogin = async (user: User): Promise<boolean> => {
    await user.reload();
    if (user.emailVerified) {
      return true;
    }
    await signOut(auth);
    setPendingVerificationEmail(user.email ?? email.trim());
    toast({
      title: "メール認証が完了していません",
      description:
        "登録時に届いた確認メールのリンクを開いてから、「メールでログイン」をもう一度押してください。",
      variant: "destructive",
    });
    return false;
  };

  const handleEmailLogin = async () => {
    const trimmed = email.trim();
    if (!trimmed) {
      toast({ title: "メールアドレスを入力してください", variant: "destructive" });
      return;
    }
    try {
      setBusy(true);
      const cred = await signInWithEmailAndPassword(auth, trimmed, password);
      const ok = await ensureEmailVerifiedForLogin(cred.user);
      if (!ok) return;
      setPendingVerificationEmail(null);
      await afterAuthSuccess();
    } catch (error: unknown) {
      const code =
        typeof error === "object" && error && "code" in error
          ? String((error as { code?: string }).code)
          : "";
      let description = error instanceof Error ? error.message : String(error);
      if (code === "auth/invalid-credential" || code === "auth/wrong-password") {
        description = "メールアドレスまたはパスワードが違います。";
      } else if (code === "auth/user-not-found") {
        description = "アカウントが見つかりません。新規登録から作成してください。";
      }
      toast({ title: "ログインできませんでした", description, variant: "destructive" });
    } finally {
      setBusy(false);
    }
  };

  const handleEmailSignUp = async () => {
    const trimmed = email.trim();
    if (!trimmed) {
      toast({ title: "メールアドレスを入力してください", variant: "destructive" });
      return;
    }
    if (password.length < 6) {
      toast({
        title: "パスワードが短すぎます",
        description: "Firebase の仕様で 6 文字以上が必要です",
        variant: "destructive",
      });
      return;
    }
    try {
      setBusy(true);
      const cred = await createUserWithEmailAndPassword(auth, trimmed, password);
      try {
        await sendAccountVerificationEmail(cred.user);
      } catch (mailErr: unknown) {
        const mailCode =
          typeof mailErr === "object" && mailErr && "code" in mailErr
            ? String((mailErr as { code?: string }).code)
            : "";
        const mailMsg = mailErr instanceof Error ? mailErr.message : String(mailErr);
        await signOut(auth);
        setPendingVerificationEmail(trimmed);
        toast({
          title: "アカウントは作成しましたが、確認メールの送信に失敗しました",
          description: firebaseAuthErrorMessage(mailCode, mailMsg),
          variant: "destructive",
        });
        return;
      }
      await signOut(auth);
      setPendingVerificationEmail(trimmed);
      toast({
        title: "確認メールを送信しました",
        description:
          "数分待っても届かない場合は迷惑メールを確認し、「確認メールを再送」を押してください。",
      });
    } catch (error: unknown) {
      const code =
        typeof error === "object" && error && "code" in error
          ? String((error as { code?: string }).code)
          : "";
      let description = error instanceof Error ? error.message : String(error);
      if (code === "auth/email-already-in-use") {
        description =
          "このメールは既に登録されています。確認メールが届いていれば認証後にログイン、なければ「メールでログイン」を試してください。";
      } else if (code === "auth/invalid-email") {
        description = "メールアドレスの形式を確認してください。";
      } else if (code === "auth/weak-password") {
        description = "より長いパスワードにしてください。";
      } else if (code) {
        description = firebaseAuthErrorMessage(code, description);
      }
      toast({ title: "新規登録できませんでした", description, variant: "destructive" });
    } finally {
      setBusy(false);
    }
  };

  const handleResendVerification = async () => {
    const trimmed = (pendingVerificationEmail ?? email).trim();
    if (!trimmed || !password) {
      toast({
        title: "再送にはメールとパスワードが必要です",
        description: "登録時と同じパスワードを入力してから押してください。",
        variant: "destructive",
      });
      return;
    }
    try {
      setBusy(true);
      const cred = await signInWithEmailAndPassword(auth, trimmed, password);
      if (cred.user.emailVerified) {
        setPendingVerificationEmail(null);
        await afterAuthSuccess();
        return;
      }
      await sendAccountVerificationEmail(cred.user);
      await signOut(auth);
      setPendingVerificationEmail(trimmed);
      toast({
        title: "確認メールを再送しました",
        description:
          "迷惑メール・プロモーションを確認してください。届かない場合は Firebase Console のテンプレート設定を確認してください。",
      });
    } catch (error: unknown) {
      const code =
        typeof error === "object" && error && "code" in error
          ? String((error as { code?: string }).code)
          : "";
      const msg = error instanceof Error ? error.message : String(error);
      await signOut(auth).catch(() => undefined);
      toast({
        title: "再送できませんでした",
        description: firebaseAuthErrorMessage(code, msg),
        variant: "destructive",
      });
    } finally {
      setBusy(false);
    }
  };

  const handleGoogleLogin = async () => {
    const provider = new GoogleAuthProvider();
    try {
      setBusy(true);
      await signInWithPopup(auth, provider);
      setPendingVerificationEmail(null);
      await afterAuthSuccess();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      toast({ title: "Google ログイン失敗", description: msg, variant: "destructive" });
    } finally {
      setBusy(false);
    }
  };

  const handleFacebookLogin = async () => {
    const provider = new FacebookAuthProvider();
    try {
      setBusy(true);
      await signInWithPopup(auth, provider);
      setPendingVerificationEmail(null);
      await afterAuthSuccess();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      toast({ title: "Facebook ログイン失敗", description: msg, variant: "destructive" });
    } finally {
      setBusy(false);
    }
  };

  const handleTwitterLogin = async () => {
    const provider = new TwitterAuthProvider();
    try {
      setBusy(true);
      await signInWithPopup(auth, provider);
      setPendingVerificationEmail(null);
      await afterAuthSuccess();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      toast({ title: "X ログイン失敗", description: msg, variant: "destructive" });
    } finally {
      setBusy(false);
    }
  };

  const handleTestSave = async () => {
    try {
      setBusy(true);
      const user = auth.currentUser;
      if (!user) {
        toast({ title: "先にログインしてください", variant: "destructive" });
        return;
      }
      await saveProgress({ subject: "math", level: 1, score: 100 });
      toast({ title: "テスト保存 OK", description: "進捗をサーバーに送りました" });
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      toast({ title: "保存に失敗", description: msg, variant: "destructive" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 p-4">
      <Card className="w-full max-w-md p-8 shadow-xl rounded-2xl bg-white">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-black">まなともログイン</h1>
          <p className="text-xs text-gray-600 mt-2">
            ログインするとキャラ・経験値をクラウドへ保存できます。
            <br />
            はじめての人は、なまえ設定とクイズ案内（オンボーディング）に進みます。
            <br />
            メール新規登録では確認メールのリンクを開いてからログインしてください。
          </p>
          <p className="text-xs text-amber-800 mt-2 text-left bg-amber-50 border border-amber-200 rounded-lg p-2">
            メールが届かないとき: Firebase Console → Authentication →
            「メールアドレスによるログイン」を有効化、Settings →
            「承認済みドメイン」に <strong>{typeof window !== "undefined" ? window.location.hostname : "localhost"}</strong>{" "}
            を追加、Templates で送信元を確認してください。
          </p>
        </div>

        <Button variant="outline" className="w-full mb-4 border-black text-black" asChild>
          <Link to="/">ホームへ戻る</Link>
        </Button>

        {pendingVerificationEmail && (
          <Card className="p-4 mb-6 border-amber-400 bg-amber-50 space-y-3">
            <p className="text-sm font-medium text-black">メール認証のお願い</p>
            <p className="text-xs text-gray-800 break-all">
              <span className="font-semibold">{pendingVerificationEmail}</span>
              あてに確認メールを送りました。リンクを開いたあと「メールでログイン」してください。
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="border-black text-black"
              disabled={busy}
              onClick={() => void handleResendVerification()}
            >
              確認メールを再送
            </Button>
          </Card>
        )}

        {sessionUser && (
          <Card className="p-4 mb-6 border-emerald-400 bg-emerald-50/90 space-y-3">
            <p className="text-sm text-black font-medium">いまログイン中</p>
            <p className="text-xs text-gray-800 break-all">
              {sessionUser.displayName?.trim() ||
                sessionUser.email?.trim() ||
                `UID ${sessionUser.uid.slice(0, 8)}…`}
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={busy}
                onClick={() => void handleLogout()}
              >
                ログアウト
              </Button>
              <Button type="button" variant="outline" size="sm" className="border-black" asChild>
                <Link to="/">ホームへ</Link>
              </Button>
            </div>
          </Card>
        )}

        <label className="block text-sm font-medium text-black mb-1" htmlFor="login-email">
          メールアドレス
        </label>
        <Input
          id="login-email"
          type="email"
          autoComplete="email"
          placeholder="name@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={loginInputClass}
        />
        <label className="block text-sm font-medium text-black mb-1" htmlFor="login-password">
          パスワード
        </label>
        <Input
          id="login-password"
          type="password"
          autoComplete="current-password"
          placeholder="6文字以上"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={`${loginInputClass} mb-4`}
        />
        <Button
          className="w-full mb-3 bg-black text-white hover:bg-gray-800"
          onClick={() => void handleEmailLogin()}
          disabled={busy}
        >
          メールでログイン
        </Button>
        <Button
          variant="outline"
          className="w-full mb-4 border-2 border-black text-black hover:bg-gray-100"
          onClick={() => void handleEmailSignUp()}
          disabled={busy}
        >
          はじめての方（メールで新規登録）
        </Button>

        <div className="flex items-center my-4">
          <hr className="flex-grow border-gray-400" />
          <span className="px-2 text-gray-600 text-sm">または</span>
          <hr className="flex-grow border-gray-400" />
        </div>

        <Button
          className="w-full mb-2 bg-red-500 hover:bg-red-600 text-white"
          onClick={() => void handleGoogleLogin()}
          disabled={busy}
        >
          Googleでログイン
        </Button>
        <Button
          className="w-full mb-2 bg-blue-800 hover:bg-blue-900 text-white"
          onClick={() => void handleFacebookLogin()}
          disabled={busy}
        >
          Facebookでログイン
        </Button>
        <Button
          className="w-full bg-black hover:bg-gray-900 text-white"
          onClick={() => void handleTwitterLogin()}
          disabled={busy}
        >
          X(旧Twitter)でログイン
        </Button>

        <Button
          variant="secondary"
          className="w-full mt-4"
          onClick={() => void handleTestSave()}
          disabled={busy}
        >
          テスト保存（進捗）
        </Button>
        <Button
          variant="outline"
          className="w-full mt-2 border-black text-black"
          onClick={() => navigate("/history")}
          disabled={busy}
        >
          学習履歴
        </Button>
      </Card>
    </div>
  );
}

export default Login;