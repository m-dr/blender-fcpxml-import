#!/usr/bin/env python3
"""
Build compliant Blender 5.2+ extension .zip package.
"""
import hashlib
import json
import os
import tomllib
import zipfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIST_DIR = os.path.join(REPO_ROOT, "dist")
MANIFEST_PATH = os.path.join(REPO_ROOT, "blender_manifest.toml")

INCLUDE_EXTENSIONS = {".py", ".toml", ".txt", ".md", ".json", ".png", ".svg", ".xml"}
EXCLUDE_DIRS = {"scripts", "dist", "build", ".git", "__pycache__", ".github"}
EXCLUDE_FILES = {"AGENTS.md", "README.md", ".gitignore"}


def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def main():
    if not os.path.exists(MANIFEST_PATH):
        raise FileNotFoundError(f"Missing manifest: {MANIFEST_PATH}")

    with open(MANIFEST_PATH, "rb") as f:
        manifest = tomllib.load(f)

    ext_id = manifest["id"]
    version = manifest["version"]
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
                if ext.lower() in INCLUDE_EXTENSIONS or file in {"LICENSE", "blender_manifest.toml"}:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, REPO_ROOT)
                    z.write(full_path, arcname=rel_path)

    file_size = os.path.getsize(zip_path)
    file_hash = sha256_file(zip_path)

    print(f"Built package: {zip_path}")
    print(f"Size: {file_size} bytes")
    print(f"SHA-256: {file_hash}")

    index_entry = {
        "id": ext_id,
        "name": manifest.get("name", ext_id),
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
