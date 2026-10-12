// Swap the base-colour texture of a rigged character for a new image with the SAME UV layout.
//   node tools/apply_texture.mjs assets/rigged.glb texture-fix/new.png assets/rigged.glb
// The new image must be 2048x2048 (or any size with the same 1:1 layout as tim_basecolor_goc.png).
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import fs from 'fs';
const [src, img, dst] = process.argv.slice(2);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const doc = await io.read(src);
const mat = doc.getRoot().listMaterials()[0];
const tex = mat.getBaseColorTexture();
const data = fs.readFileSync(img);
const ext = img.toLowerCase().split('.').pop();
tex.setImage(data).setMimeType(ext === 'png' ? 'image/png' : ext === 'webp' ? 'image/webp' : 'image/jpeg');
await io.write(dst, doc);
console.log('applied', img, '→', dst, (fs.statSync(dst).size / 1e6).toFixed(1), 'MB');
