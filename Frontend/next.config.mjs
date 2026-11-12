import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const config = {
  distDir: process.env.MITRA_BUILD_DIR || ".next",
  turbopack: { root },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.MITRA_API_URL || "http://127.0.0.1:8000"}/api/v1/:path*`,
      },
    ];
  },
};
export default config;
