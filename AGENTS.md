# Agent Operating Guide: FCPXML & XMEML Importer

This repository contains the **FCPXML & XMEML Importer** extension for Blender 5.2+.

---

## 1. Structure
- `blender_manifest.toml`: Extension manifest for Blender 5.2+.
- `__init__.py`: Full importer implementation.
- `scripts/build_extension.py`: Builder that packages `dist/fcpxml_import-<version>.zip`.

---

## 2. Release SOP for Agents
1. Verify version numbers in `blender_manifest.toml` and `__init__.py`.
2. Run `python scripts/build_extension.py` to produce distribution zip.
3. Test registration:
   ```bash
   blender --background --factory-startup --python-expr "import sys, importlib.util; spec = importlib.util.spec_from_file_location('fcpxml_import', '__init__.py'); mod = importlib.util.module_from_spec(spec); mod.register(); mod.unregister()"
   ```
4. Commit and push tag:
   ```bash
   git commit -am "Release v<version>"
   git tag v<version>
   git push origin main --tags
   ```
