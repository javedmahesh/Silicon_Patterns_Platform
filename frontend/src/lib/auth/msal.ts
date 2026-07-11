/**
 * Microsoft Entra ID (MSAL) client config — Authorization Code + PKCE, the standard
 * flow for a Single-Page Application (no client secret ever touches the browser).
 * redirectUri is the current origin so this works unmodified in any environment
 * that's registered as a redirect URI on the App Registration (locally that's
 * http://localhost:5173, matching MICROSOFT_REDIRECT_URI in the root .env).
 */
import { PublicClientApplication, type Configuration } from "@azure/msal-browser";

const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_MICROSOFT_CLIENT_ID ?? "",
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_MICROSOFT_TENANT_ID ?? ""}`,
    redirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: "sessionStorage",
  },
};

export const msalInstance = new PublicClientApplication(msalConfig);

/** openid+profile+email are enough to get the ID token claims the backend needs
 * (email/name/oid) — no API scope/access token is required for /auth/microsoft. */
export const MSAL_LOGIN_REQUEST = { scopes: ["openid", "profile", "email"] };
