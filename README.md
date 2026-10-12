# fashionfeatures

Real-time 3D character viewer for the browser, with soft-body ("jelly") physics on chest and hips, live sliders, camera presets and poses. Built with three.js, no build step needed to run.

Live version: https://goldenseastudios.com/character-studio (by Golden Sea Studios)

## Run locally

```bash
python3 -m http.server 8080
```

Open http://localhost:8080. Add `?lang=en` for the English HUD.

## What's inside

| Path | What it is |
|---|---|
| `index.html`, `styles.css` | Page and HUD |
| `src/main.js` | Scene, camera presets, sliders, character loading |
| `src/soft.js` | Soft-body spring simulation driving the chest/hip bones |
| `src/anim.js` | Procedural idle and pose animation |
| `assets/rigged.glb` | Rigged character used by the viewer |
| `assets/model.glb` | Unrigged source mesh |
| `vendor/` | three.js and addons (pinned copy) |
| `tools/` | Asset pipeline: rigging (`rig.py`, Blender), decimation/simplify, texture repair scripts, web release build |
| `posetest.html`, `inspect.html` | Dev pages for checking poses and model data |
| `models/tim/` | The character as standalone 3D files: `tim_rigged.glb`, `tim_rigged.fbx` (textures embedded) and the PNG texture maps in `textures/` |

## 3D model

`models/tim/` holds the character "Tím" (Violet) for use in Blender, Unity, Unreal or any glTF/FBX viewer:

- ~160k triangles, one material, A-pose, Y up, facing +Z, 20-bone humanoid-style rig (spine, neck, head, arms, legs, plus chest and hip bones driven by the soft-body sim)
- Textures: base color 2048 px, normal and metal/roughness 1024 px

## Release build

```bash
cd tools && npm install
node build_web.mjs --out ../dist
```

Produces one minified, hashed ES module plus CSS; three.js stays external via the import map.

## Rights

© Golden Sea Studios. All rights reserved. The code and the 3D character are shared for viewing and reference; ask before reusing them in your own products.
