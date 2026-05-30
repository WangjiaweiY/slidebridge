import { copyFileSync, cpSync, mkdirSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const sourceRoot = join(root, "node_modules", "openseadragon");
const targetRoot = join(root, "slidebridge", "server", "static", "vendor", "openseadragon");

rmSync(targetRoot, { force: true, recursive: true });
mkdirSync(join(targetRoot, "images"), { recursive: true });

copyFileSync(
  join(sourceRoot, "build", "openseadragon", "openseadragon.min.js"),
  join(targetRoot, "openseadragon.min.js")
);
copyFileSync(
  join(sourceRoot, "LICENSE.txt"),
  join(targetRoot, "LICENSE.txt")
);
cpSync(
  join(sourceRoot, "build", "openseadragon", "images"),
  join(targetRoot, "images"),
  { recursive: true }
);

console.log(`Vendored OpenSeadragon assets into ${targetRoot}`);
