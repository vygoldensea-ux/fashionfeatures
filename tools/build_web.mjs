// Release build for the website: one minified ES module (three stays external via the importmap),
// minified CSS, hashed names; index.html rewritten with noindex + canonical + base.
//   node tools/build_web.mjs --out <dir>
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { createRequire } from 'module';
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const require = createRequire(import.meta.url);
const esbuild = require('esbuild');
const i = process.argv.indexOf('--out');
const out = path.resolve(i > 0 ? process.argv[i + 1] : path.join(root, 'dist'));
fs.mkdirSync(out, { recursive: true });
const res = await esbuild.build({ entryPoints: [path.join(root, 'src/main.js')], bundle: true, format: 'esm', minify: true, legalComments: 'none', external: ['three', 'three/addons/*'], write: false, target: ['es2020'] });
const js = res.outputFiles[0].text;
const h = (t) => crypto.createHash('sha1').update(t).digest('hex').slice(0, 10);
const jsName = `g.${h(js)}.js`;
for (const f of fs.readdirSync(out)) if (/^(g|s)\.[0-9a-f]{10}\.(js|css)$/.test(f)) fs.unlinkSync(path.join(out, f));
fs.writeFileSync(path.join(out, jsName), js);
const css = (await esbuild.transform(fs.readFileSync(path.join(root, 'styles.css'), 'utf8'), { loader: 'css', minify: true })).code;
const cssName = `s.${h(css)}.css`;
fs.writeFileSync(path.join(out, cssName), css);
let html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
html = html.replace('<link rel="stylesheet" href="styles.css">', `<link rel="stylesheet" href="${cssName}">`).replace('<script type="module" src="src/main.js"></script>', `<script type="module" src="${jsName}"></script>`);
html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<base href="/games/character-studio/">\n<meta name="robots" content="noindex">\n<link rel="canonical" href="https://goldenseastudios.com/character-studio">').replace('<title>Soft Body</title>', '<title>Character Studio</title>');
fs.writeFileSync(path.join(out, 'index.html'), html);
fs.rmSync(path.join(out, 'src'), { recursive: true, force: true });
fs.rmSync(path.join(out, 'styles.css'), { force: true });
fs.mkdirSync(path.join(out, 'assets'), { recursive: true });
for (const f of ['rigged.glb']) fs.copyFileSync(path.join(root, 'assets', f), path.join(out, 'assets', f));
fs.cpSync(path.join(root, 'vendor'), path.join(out, 'vendor'), { recursive: true });
console.log('built', jsName, (js.length / 1024).toFixed(0), 'KB', cssName, '→', out);
