import { readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { marked, Renderer } = require("marked");
const { instance } = require("@viz-js/viz");

const guide = new URL("../docs/design/SpecThread-설계와-실행-가이드.md", import.meta.url);
const output = new URL(guide.href.replace(/\.md$/, ".html"));
const markdown = await readFile(guide, "utf8");
const graphviz = await instance();
const renderer = new Renderer();
const sections = [];

const escape = (text) => text.replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[character]);

renderer.heading = function ({ depth, text, tokens }) {
  const heading = this.parser.parseInline(tokens);
  if (depth !== 2) return `<h${depth}>${heading}</h${depth}>\n`;
  const id = `section-${sections.length + 1}`;
  sections.push({ id, text });
  return `<h2 id="${id}">${heading}</h2>\n`;
};

function renderFlowchart(text) {
  const [header, ...lines] = text.trim().split("\n");
  const direction = { TD: "TB", TB: "TB", LR: "LR" }[header.match(/^flowchart (TD|TB|LR)$/)?.[1]];
  if (!direction) throw new Error(`Unsupported guide diagram: ${header}`);
  const node = '(\\w+)(?:\\["([^"]+)"\\]|\\{"([^"]+)"\\})?';
  const edgePattern = new RegExp(`^\\s*${node}\\s*-->(?:\\|([^|]+)\\|)?\\s*${node}\\s*$`);
  const nodes = new Map();
  const edges = [];
  for (const line of lines) {
    if (!line.trim()) continue;
    const match = line.match(edgePattern);
    if (!match) throw new Error(`Unsupported guide diagram edge: ${line}`);
    const [, from, fromText, fromDecision, label, to, toText, toDecision] = match;
    for (const [id, text, decision] of [[from, fromText, fromDecision], [to, toText, toDecision]]) {
      if (text || decision) {
        const definition = `${id} [label=${JSON.stringify(text || decision)}, shape=${decision ? "diamond" : "box"}]`;
        if (nodes.has(id) && nodes.get(id) !== definition) {
          throw new Error(`Conflicting guide diagram node: ${id}`);
        }
        nodes.set(id, definition);
      }
    }
    edges.push(`${from} -> ${to}${label ? ` [label=${JSON.stringify(label)}]` : ""}`);
  }
  const svg = graphviz.renderString(`digraph {
    graph [rankdir=${direction}, bgcolor=transparent, pad=0.15]
    node [style="rounded,filled", fillcolor="#ffffff", color="#567b75", fontname="sans-serif"]
    edge [color="#496a66", fontname="sans-serif", fontsize=11]
    ${[...nodes.values(), ...edges].join("\n")}
  }`, { format: "svg" }).replace(/^[\s\S]*?(<svg\b)/, "$1");
  return `<figure class="diagram" aria-label="Discovery 흐름도">${svg}</figure>\n`;
}

const renderCode = renderer.code.bind(renderer);
renderer.code = function (token) {
  return token.lang === "mermaid" ? renderFlowchart(token.text) : renderCode(token);
};

const body = marked.parse(markdown, { gfm: true, renderer });
const links = sections.map(({ id, text }) => `<li><a href="#${id}">${escape(text)}</a></li>`).join("");
const html = `<!doctype html>
<!-- Generated from the Markdown guide. Regenerate with scripts/render-design-guide.mjs. -->
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SpecThread 설계와 실행 가이드</title>
<style>
* { box-sizing: border-box; }
body { margin: 0; background: #f4f6f8; color: #172735; font: 16px/1.75 system-ui, sans-serif; }
.layout { max-width: 1320px; margin: auto; padding: 3rem 2rem; display: grid; grid-template-columns: 240px minmax(0, 1fr); gap: 2rem; align-items: start; }
nav { position: sticky; top: 1rem; max-height: calc(100vh - 2rem); overflow: auto; padding: 1rem; border-left: 3px solid #4c7372; font-size: .9rem; }
nav ul { padding-left: 1.25rem; }
main { background: white; padding: clamp(1rem, 4vw, 3.5rem); border: 1px solid #d6e0e3; border-radius: 12px; min-width: 0; }
h1, h2, h3 { line-height: 1.35; word-break: keep-all; }
h1 { font-size: clamp(1.8rem, 4vw, 2.8rem); margin: 0 0 .4rem; }
h2 { border-top: 1px solid #d6e0e3; margin-top: 2.4rem; padding-top: 1.6rem; }
a { color: #165d5a; text-underline-offset: .2em; }
a:focus-visible { outline: 2px solid #257c76; outline-offset: 3px; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .95rem; }
th, td { padding: .65rem .75rem; border-bottom: 1px solid #d6e0e3; text-align: left; vertical-align: top; overflow-wrap: anywhere; }
th { background: #eaf2f1; }
pre { background: #152d33; color: #f0f8fa; padding: 1rem; border-radius: 8px; overflow: auto; line-height: 1.55; }
code { font-family: ui-monospace, monospace; font-size: .9em; }
:not(pre) > code { padding: .1em .3em; background: #edf2f4; border-radius: 4px; overflow-wrap: anywhere; }
.diagram { margin: 1.25rem 0; padding: 1rem; border: 1px solid #cadbd9; border-radius: 12px; background: #f2f8f7; overflow-x: auto; }
.diagram svg { display: block; width: 100%; min-width: 44rem; height: auto; }
@media(max-width: 840px) { .layout { display: block; padding: 1rem; } nav { position: static; max-height: none; margin-bottom: 1rem; } th, td { padding: .45rem; } }
@media print { nav { display: none; } .layout { display: block; padding: 0; } main { padding: 0; border: 0; } pre { background: white; color: black; white-space: pre-wrap; } tr, .diagram { break-inside: avoid; } .diagram svg { min-width: 0; } }
</style>
</head>
<body><div class="layout"><nav aria-label="목차"><strong>목차</strong><ul>${links}</ul></nav><main>
${body}</main></div></body>
</html>
`;

if (process.argv.includes("--check")) {
  if (await readFile(output, "utf8") !== html) {
    console.error("HTML 가이드가 Markdown과 일치하지 않습니다. 다시 생성하세요.");
    process.exitCode = 1;
  }
} else {
  await writeFile(output, html, "utf8");
}
