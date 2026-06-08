import { defineConfig } from "vite";
import { fileURLToPath, URL } from "node:url";
import { cpSync, existsSync, readFileSync } from "node:fs";
import { resolve, sep } from "node:path";

const archiveDir = fileURLToPath(new URL("../../data/archive", import.meta.url));
const outputDir = fileURLToPath(new URL("../../dist", import.meta.url));

function archiveAssets() {
  return {
    name: "archive-assets",
    configureServer(server) {
      server.middlewares.use("/archive", (request, response, next) => {
        const relativePath = decodeURIComponent((request.url ?? "").split("?")[0]).replace(/^\/+/, "");
        const target = resolve(archiveDir, relativePath);
        if (!target.startsWith(`${archiveDir}${sep}`) || !existsSync(target)) {
          next();
          return;
        }
        response.setHeader("Content-Type", "application/json; charset=utf-8");
        response.end(readFileSync(target));
      });
    },
    closeBundle() {
      cpSync(archiveDir, resolve(outputDir, "archive"), { recursive: true });
    },
  };
}

export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  base: process.env.GITHUB_PAGES === "true" ? "/ai-news-artifact/" : "/",
  server: {
    host: "127.0.0.1",
  },
  esbuild: {
    jsx: "automatic",
  },
  plugins: [archiveAssets()],
  build: {
    outDir: outputDir,
    emptyOutDir: true,
  },
});
