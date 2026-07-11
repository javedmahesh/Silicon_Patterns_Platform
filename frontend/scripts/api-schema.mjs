/**
 * Generate (or verify) the typed API contract from the backend's OpenAPI schema.
 *
 *   node scripts/api-schema.mjs            # write src/lib/api/schema.ts
 *   node scripts/api-schema.mjs --check    # exit 1 if it would change (drift guard)
 *
 * The spec is produced offline by ../scripts/dump_openapi.py (no running server).
 * Set PYTHON=... if `python` is not the interpreter with the backend installed.
 */
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..", "..");
const dumpScript = resolve(repoRoot, "scripts", "dump_openapi.py");
const outFile = resolve(here, "..", "src", "lib", "api", "schema.ts");
const PYTHON = process.env.PYTHON ?? "python";

const BANNER = [
  "/**",
  " * AUTO-GENERATED — DO NOT EDIT BY HAND.",
  " * Mirrors the backend FastAPI OpenAPI schema (backend/schemas.py).",
  " * Regenerate:   cd frontend && npm run gen:api-schema",
  " * Verify (CI):  cd frontend && npm run check:api-schema",
  " * Friendly aliases live in src/lib/api/types.ts (which derives from this file).",
  " */",
  "",
].join("\n");

function loadSpec() {
  const json = execFileSync(PYTHON, [dumpScript, "-"], {
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  return JSON.parse(json);
}

const ast = await openapiTS(loadSpec());
const generated = BANNER + astToString(ast);

if (process.argv.includes("--check")) {
  let current = "";
  try {
    current = readFileSync(outFile, "utf8");
  } catch {
    /* missing file counts as drift */
  }
  if (current !== generated) {
    console.error(
      "✗ src/lib/api/schema.ts is out of date with the backend OpenAPI schema.\n" +
        "  Run:  npm run gen:api-schema   (then commit the result).",
    );
    process.exit(1);
  }
  console.log("✓ src/lib/api/schema.ts matches the backend OpenAPI schema.");
} else {
  writeFileSync(outFile, generated);
  console.log(`✓ Wrote ${outFile}`);
}
