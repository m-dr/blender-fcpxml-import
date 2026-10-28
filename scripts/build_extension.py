#!/usr/bin/env python3
"""
Build compliant Blender extension .zip package with automatic release sanitization.
Strips '(DEV)' from blender_manifest.toml and bl_info when packing production archives.
"""
import hashlib
import json
import os
import re
import tomllib
import zipfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIST_DIR = os.path.join(REPO_ROOT, "dist")
MANIFEST_PATH = os.path.join(REPO_ROOT, "blender_manifest.toml")

INCLUDE_EXTENSIONS = {".py", ".toml", ".txt", ".md", ".json", ".png", ".svg"}
EXCLUDE_DIRS = {"scripts", "dist", "build", ".git", "__pycache__", ".github"}
EXCLUDE_FILES = {"AGENTS.md", "README.md", ".gitignore"}


def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def sanitize_manifest_text(text: str) -> str:
    """Strip (DEV) suffix from manifest name for production releases."""
    return re.sub(r'(name\s*=\s*"[^"]*?)\s*[\(\[]DEV[\)\]]', r'\1', text)


def sanitize_init_text(text: str) -> str:
    """Strip (DEV) suffix from bl_info name for production releases."""
    return re.sub(r'("name":\s*"[^"]*?)\s*[\(\[]DEV[\)\]]', r'\1', text)


def main():
    if not os.path.exists(MANIFEST_PATH):
        raise FileNotFoundError(f"Missing manifest: {MANIFEST_PATH}")

    with open(MANIFEST_PATH, "rb") as f:
        manifest = tomllib.load(f)

    ext_id = manifest["id"]
    version = manifest["version"]
    raw_name = manifest.get("name", ext_id)
    clean_name = re.sub(r'\s*[\(\[]DEV[\)\]]', '', raw_name).strip()

    os.makedirs(DIST_DIR, exist_ok=True)
    zip_filename = f"{ext_id}-{version}.zip"
    zip_path = os.path.join(DIST_DIR, zip_filename)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(REPO_ROOT):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]

            for file in files:
                if file in EXCLUDE_FILES or file.startswith("."):
                    continue
                _, ext = os.path.splitext(file)
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, REPO_ROOT)

                if file == "blender_manifest.toml" and rel_path == "blender_manifest.toml":
                    with open(full_path, "r", encoding="utf-8") as f_in:
                        content = sanitize_manifest_text(f_in.read())
                    z.writestr("blender_manifest.toml", content.encode("utf-8"))
                elif file == "__init__.py" and rel_path == "__init__.py":
                    with open(full_path, "r", encoding="utf-8") as f_in:
                        content = sanitize_init_text(f_in.read())
                    z.writestr("__init__.py", content.encode("utf-8"))
                elif ext.lower() in INCLUDE_EXTENSIONS or file in {"LICENSE"}:
                    z.write(full_path, arcname=rel_path)

    file_size = os.path.getsize(zip_path)
    file_hash = sha256_file(zip_path)

    print(f"Built package: {zip_path}")
    print(f"Size: {file_size} bytes")
    print(f"SHA-256: {file_hash}")

    index_entry = {
        "id": ext_id,
        "name": clean_name,
        "version": version,
        "type": manifest.get("type", "add-on"),
        "blender_version_min": manifest.get("blender_version_min", "5.2.0"),
        "archive_size": file_size,
        "archive_hash": file_hash,
    }
    print("\n--- Index Entry Snippet ---")
    print(json.dumps(index_entry, indent=2))


if __name__ == "__main__":
    main()
