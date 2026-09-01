# FCPXML & XMEML Importer (Blender 5.2+ Extension)

An enhanced Blender extension for importing **Final Cut Pro X XML** (`.fcpxml`) and **Final Cut Pro 7 / Premiere Pro XML** (`.xmeml`) files into Blender's Video Sequence Editor (VSE) with full multi-track layout, native retiming, reverse playback, markers, and audio pitch correction.

![Blender 5.2+](https://img.shields.io/badge/Blender-5.2%2B-orange.svg)

---

## Features

- **Blender 5.2+ Native VSE Architecture**: Uses `scene.sequence_editor.strips`, `content_trim_start`, `content_trim_end`, and `frame_final_duration`.
- **Multi-Track & Layered Alignment**: Preserves dedicated audio channels and video tracks.
- **Native Retiming & Speed Factors**: Automatic speed calculation and reverse frame handling (`use_reverse_frames`).
- **Timeline Markers**: Imports markers with names and comments directly into scene timeline markers.
- **Smart Path Decoding & Media Resolver**: Decodes URL-encoded paths (`file://localhost/...`), handles absolute/relative paths, and fuzzy matches files in user-specified media search paths.

---

## Installation

### Method A: Via Personal Extension Repository (Recommended)
Add the extension repository in Blender:
* **URL**: `https://m-dr.github.io/blender-extensions/index.json`  
Then search for **FCPXML & XMEML Importer** in **Preferences > Get Extensions** and click **Install**.

### Method B: Install from Disk (.zip)
1. Download `fcpxml_import-1.2.0.zip` from the [Releases](https://github.com/m-dr/fcpxml_import/releases) page.
2. In Blender: **Preferences > Get Extensions > Install from Disk...**

---

## Usage

1. Switch to the **Video Editing** workspace.
2. Go to **File > Import > FCPXML / XMEML (.xml)**.
3. Select your `.xml` file and (optional) media search folder.

---

## License

GPL-3.0 License (see [LICENSE](LICENSE)).
