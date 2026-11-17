import { createRequire } from "node:module";
import { readdir, readFile, stat } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const { marked } = createRequire(import.meta.url)("marked");
const root = fileURLToPath(new URL("../", import.meta.url));
const designDir = resolve(root, "docs/design");
const design = (await readdir(designDir)).filter((file) => file.endsWith(".md"));
const files = [
  ...design.map((file) => resolve(designDir, file)),
  ...["AGENTS.md", "CLAUDE.md", "CHANGELOG.md", "README.md", "docs/SpecThread-설치-매뉴얼.md"]
    .map((file) => resolve(root, file)),
];
const errors = [];
for (const file of files) {
  const source = await readFile(file, "utf8");
  if (!/^# [^\n]+\n/.test(source)) errors.push(`${file}: missing document title`);
  const fences = source.match(/^(?:```|~~~).*$/gm) ?? [];
  if (fences.length % 2 !== 0) errors.push(`${file}: unclosed code block`);
  const links = [];
  marked.walkTokens(marked.lexer(source), (token) => {
    if (token.type === "link" || token.type === "image") links.push(token.href);
  });
  for (const href of links) {
    const path = href.split(/[?#]/, 1)[0];
    if (!path || /^[a-z][a-z0-9+.-]*:/i.test(path) || path.startsWith("//")) continue;
    const target = resolve(dirname(file), decodeURIComponent(path));
    if (!await stat(target).catch(() => null)) errors.push(`${file}: missing link ${href}`);
  }
}

const index = await readFile(resolve(designDir, "README.md"), "utf8");
const version = index.match(/^# SpecThread 설계 (\d+\.\d+)$/m)?.[1];
const notes = await readFile(resolve(root, "CHANGELOG.md"), "utf8");
if (!version || notes.match(/^## (\d+\.\d+)$/m)?.[1] !== version) {
  errors.push("Design README and latest CHANGELOG versions must agree");
}
if (errors.length) throw new Error(errors.join("\n"));
console.log(`Checked ${files.length} Markdown documents and design version ${version}.`);
