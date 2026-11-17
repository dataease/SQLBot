import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";
const root = fileURLToPath(new URL(".", import.meta.url));
const frontend = path.resolve(root, "../../../../frontend");
const require = createRequire(path.join(frontend, "package.json"));
const { createServer } = await import(require.resolve("vite"));
const { default: vue } = await import(require.resolve("@vitejs/plugin-vue"));
const { default: svg } = await import(require.resolve("vite-svg-loader"));
const bridge = path.join(root, "bridge.mjs");
const server = await createServer({
  configFile: false,
  root,
  cacheDir: "../../output/model-discovery-vite",
  plugins: [vue(), svg()],
  resolve: {
    alias: [
      ...["@/utils/request"].map((find) => ({ find, replacement: bridge })),
      { find: "@", replacement: path.join(frontend, "src") },
      ...[
        "vue",
        "pinia",
        "vue-i18n",
        "element-plus-secondary",
        "axios",
        "json-bigint",
      ].map((name) => ({
        find: name,
        replacement: path.join(frontend, "node_modules", name),
      })),
    ],
  },
  define: { "import.meta.env.VITE_API_BASE_URL": JSON.stringify("/api/v1") },
  server: {
    host: "127.0.0.1",
    port: 4231,
    strictPort: true,
    fs: { allow: [root, frontend] },
  },
});
await server.listen();
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, async () => {
    await server.close();
    process.exit();
  });
