import { readFile, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const rootDir = dirname(dirname(fileURLToPath(import.meta.url)));
const requiredFiles = [
  "index.html",
  "src/app.js",
  "src/api/importJobs.js",
  "src/api/master.js",
  "src/lib/apiClient.js",
  "src/screens/importPreviewScreen.js",
  "src/styles.css",
];

for (const file of requiredFiles) {
  await stat(join(rootDir, file));
  await readFile(join(rootDir, file), "utf8");
}

console.log("frontend build check completed");
