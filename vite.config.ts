import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [
    react(),
    {
      name: "static-review-and-report-indexes",
      configureServer(server) {
        server.middlewares.use((req, _res, next) => {
          const [path, query] = (req.url || "").split("?");
          if (
            /^\/review\/(funding\/)?$/.test(path) ||
            /^\/reports\/[a-f0-9]{16}\/(se|us)\/$/.test(path)
          )
            req.url = path + "index.html" + (query ? "?" + query : "");
          next();
        });
      },
    },
  ],
  build: { outDir: "dist" },
  server: { port: 5173 },
});
