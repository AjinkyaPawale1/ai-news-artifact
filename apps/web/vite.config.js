import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  base: process.env.GITHUB_PAGES === "true" ? "/ai-news-artifact/" : "/",
  plugins: [react()],
  build: {
    outDir: "../../dist",
    emptyOutDir: true,
  },
});
