import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { onAuthStateChanged, signOut } from "firebase/auth";
import { auth } from "@/firebaseConfig";

function isUnverifiedEmailPasswordUser(user: import("firebase/auth").User): boolean {
  return (
    Boolean(user.email) &&
    !user.emailVerified &&
    user.providerData.some((p) => p.providerId === "password")
  );
}

/** メール新規登録ユーザーは認証完了まで自動ログイン状態を維持しない */
export function EmailVerificationGate({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (user) => {
      if (!user) return;
      if (!isUnverifiedEmailPasswordUser(user)) return;
      void (async () => {
        await signOut(auth);
        if (location.pathname !== "/login") {
          navigate("/login", { replace: true });
        }
      })();
    });
    return () => unsub();
  }, [location.pathname, navigate]);

  return <>{children}</>;
}
