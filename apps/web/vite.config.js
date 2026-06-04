import { defineConfig } from "vite";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  base: process.env.GITHUB_PAGES === "true" ? "/ai-news-artifact/" : "/",
  server: {
    host: "127.0.0.1",
  },
  esbuild: {
    jsx: "automatic",
  },
  build: {
    outDir: "../../dist",
    emptyOutDir: true,
  },
});
