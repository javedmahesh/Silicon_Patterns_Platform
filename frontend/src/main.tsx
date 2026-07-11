import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MsalProvider } from "@azure/msal-react";
import { broadcastResponseToMainFrame } from "@azure/msal-browser/redirect-bridge";

import "@fontsource-variable/inter";
import "@fontsource-variable/jetbrains-mono";
import "./index.css";

import App from "./App";
import { msalInstance } from "./lib/auth/msal";

/** True when this window is the MSAL sign-in popup returning from Microsoft —
 * the auth response (code or error + state) rides in the URL fragment/query. */
function isMicrosoftAuthResponse(): boolean {
  const params = new URLSearchParams(
    window.location.hash.startsWith("#") ? window.location.hash.slice(1) : window.location.search,
  );
  return params.has("state") && (params.has("code") || params.has("error"));
}

if (isMicrosoftAuthResponse()) {
  // Do NOT boot the SPA here: the router would strip the auth response from the
  // URL before the main window reads it. The redirect bridge posts the response
  // to the waiting opener over a BroadcastChannel and closes this popup.
  broadcastResponseToMainFrame().catch(() => undefined);
} else {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  });

  await msalInstance.initialize();

  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <MsalProvider instance={msalInstance}>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </QueryClientProvider>
      </MsalProvider>
    </StrictMode>,
  );
}
