import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useMsal } from "@azure/msal-react";
import { AuthError, BrowserAuthErrorCodes } from "@azure/msal-browser";

import { apiErrorDetail, apiErrorMessage } from "@/lib/api/client";
import { api } from "@/lib/api/endpoints";
import { MSAL_LOGIN_REQUEST } from "@/lib/auth/msal";
import { useAuth } from "@/lib/auth/store";

const DOMAIN = "siliconpatterns.com";

/** Lifecycle/auth error codes the backend returns (see backend/services.py's
 * _lifecycle_error) mapped to a human-readable, non-enumerating message. */
const STATUS_MESSAGE: Record<string, string> = {
  account_pending: "Your account is pending admin approval. You'll be able to sign in once it's approved.",
  account_rejected: "Your access request was declined. Contact an administrator if you believe this is a mistake.",
  account_disabled: "This account has been disabled. Contact an administrator.",
  account_deleted: "This account no longer exists.",
  forbidden_domain: `Only @${DOMAIN} accounts may sign in.`,
  invalid_microsoft_token: "Could not verify your Microsoft sign-in. Please try again.",
};

function backendErrorMessage(e: unknown): string {
  const code = apiErrorDetail(e)?.code;
  return (code && STATUS_MESSAGE[code]) || apiErrorMessage(e);
}

export function LoginPage() {
  const { isAuthed, setSession } = useAuth();
  const { instance } = useMsal();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (isAuthed) return <Navigate to="/" replace />;

  async function signIn() {
    setError(null);
    setBusy(true);
    let idToken: string;
    try {
      idToken = (await instance.loginPopup(MSAL_LOGIN_REQUEST)).idToken;
    } catch (e) {
      // The popup itself failed — cancelled, closed, or blocked by the browser.
      // MSAL's own AuthError.errorMessage is already a reasonable user-facing string.
      if (e instanceof AuthError && e.errorCode === BrowserAuthErrorCodes.userCancelled) {
        setBusy(false);
        return; // not an error worth showing
      }
      setError(e instanceof AuthError ? e.errorMessage : "Could not open the Microsoft sign-in window.");
      setBusy(false);
      return;
    }
    try {
      const res = await api.auth.microsoft(idToken);
      setSession(res.token, res.user);
      navigate("/", { replace: true });
    } catch (e) {
      setError(backendErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-base px-4">
      <div className="w-full max-w-sm rounded-lg border border-line bg-surface p-8">
        <div className="mb-1 text-13 font-medium tracking-wide text-accent">SILICON PATTERNS</div>
        <h1 className="text-18 text-fg">Sign in to the platform</h1>
        <p className="mt-2 text-13 text-fg-muted">
          Use your <span className="text-fg">@{DOMAIN}</span> Microsoft 365 account. New accounts need
          administrator approval before they can sign in.
        </p>

        <button
          type="button"
          onClick={signIn}
          disabled={busy}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-md border border-line bg-control px-4 py-2 text-13 text-fg hover:bg-raised disabled:opacity-60"
        >
          <MicrosoftLogo />
          {busy ? "Signing in…" : "Sign in with Microsoft"}
        </button>

        {error && <p className="mt-4 text-12 text-danger">{error}</p>}
      </div>
    </div>
  );
}

function MicrosoftLogo() {
  return (
    <svg width="16" height="16" viewBox="0 0 21 21" aria-hidden="true">
      <rect x="1" y="1" width="9" height="9" fill="#f25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
      <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
      <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
    </svg>
  );
}
