import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

/** ローカル開発は自前バックエンド（Replicate 不要）を優先。Heroku 向けは BACKEND_PROXY_TARGET を指定 */
const defaultBackend = "http://127.0.0.1:8000";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const envDev = loadEnv("development", process.cwd(), "");
  const backendProxy =
    env.BACKEND_PROXY_TARGET ||
    envDev.BACKEND_PROXY_TARGET ||
    defaultBackend;

  const proxy = {
    "/api": {
      target: backendProxy,
      changeOrigin: true,
      secure: true,
    },
  };

  return {
    base: "/",
    server: {
      host: true,
      port: 5173,
      open: true,
      proxy,
    },
    preview: {
      port: 4173,
      proxy,
    },
    plugins: [
      react(),
      mode === "development" && componentTagger(),
    ].filter(Boolean),
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});
