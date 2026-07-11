/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Bundled variable fonts are CSS-only side-effect imports.
declare module "@fontsource-variable/inter";
declare module "@fontsource-variable/jetbrains-mono";
