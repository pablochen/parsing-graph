/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_API_TIMEOUT: string
  // 필요에 따라 더 많은 환경변수 추가 가능
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}