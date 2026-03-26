import { execFileSync, execSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendDir, "..");
const backendExportScript = path.join(repoRoot, "backend", "scripts", "export_openapi.py");
const generatedDir = path.join(frontendDir, "lib", "generated");
const openapiJsonPath = path.join(generatedDir, "openapi.json");
const apiSchemaTsPath = path.join(generatedDir, "api-schema.ts");

mkdirSync(generatedDir, { recursive: true });

const pythonCommand = process.platform === "win32" ? "python" : "python3";
const openapiJson = execFileSync(pythonCommand, [backendExportScript], {
  cwd: frontendDir,
  encoding: "utf8",
});
writeFileSync(openapiJsonPath, openapiJson);

const openapiTypescriptCommand =
  process.platform === "win32"
    ? path.join(frontendDir, "node_modules", ".bin", "openapi-typescript.cmd")
    : path.join(frontendDir, "node_modules", ".bin", "openapi-typescript");
const quotedGenerator = `"${openapiTypescriptCommand}" "${openapiJsonPath}" -o "${apiSchemaTsPath}"`;
execSync(quotedGenerator, { cwd: frontendDir, stdio: "inherit" });
