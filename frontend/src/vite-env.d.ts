/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ALLOW_ANONYMOUS_MEDIA?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
