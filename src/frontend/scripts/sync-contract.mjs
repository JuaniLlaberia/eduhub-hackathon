// Copies contract C4 (OpenAPI) and C6 (JSON fixtures) from src/shared into the app, then generates the TS types.
// Run after every contract change: `npm run contract:sync`. Never edit the generated files by hand.
import { execFileSync } from "node:child_process";
import { cpSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const appDir = join(dirname(fileURLToPath(import.meta.url)), "..");
const sharedDir = join(appDir, "..", "shared");
const fixturesSrc = join(sharedDir, "eduhub_shared", "fixtures");
const fixturesDest = join(appDir, "src", "lib", "api", "fixtures");
const openapi = join(sharedDir, "contracts", "openapi.json");
const schemaDest = join(appDir, "src", "lib", "api", "schema.d.ts");

rmSync(fixturesDest, { recursive: true, force: true });
mkdirSync(fixturesDest, { recursive: true });
for (const file of readdirSync(fixturesSrc).filter((f) => f.endsWith(".json"))) {
  cpSync(join(fixturesSrc, file), join(fixturesDest, file));
}

execFileSync("npx", ["openapi-typescript", openapi, "-o", schemaDest], { cwd: appDir, stdio: "inherit" });
console.log(`Synced fixtures to ${fixturesDest}`);
