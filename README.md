# FCPXML & XMEML Importer for Blender 5.2+

An enhanced Blender add-on for importing **Final Cut Pro XML** (`.fcpxml`) and **Final Cut Pro 7 / Premiere Pro XML** (`.xmeml`) files into Blender's Video Sequence Editor (VSE).

Forked and merged from:
- [tin2tin/fcpxml_import](https://github.com/tin2tin/fcpxml_import)
- [Omniscye/fcpxml_import-Optimized](https://github.com/Omniscye/fcpxml_import-Optimized/tree/enhanced-fcpxml-importer)

---

## Features

- **Blender 5.2 / 4.x / 3.x Support**: Updated to support modern Blender VSE `scene.sequence_editor.strips` API with legacy fallback.
- **Dual XML Format Parsing**: Supports both Final Cut Pro 7 / Premiere Pro XML (`<xmeml>`) and Final Cut Pro X XML (`<fcpxml>`).
- **Timeline Markers**: Automatically imports sequence timeline markers directly into Blender's scene markers (`scene.timeline_markers`).
- **Audio & Video Track Handling**: Creates `movie` strips for video clips and `sound` strips for audio clips with proper track/channel alignment.
- **Reusable File ID Resolution**: Resolves `<file id="...">` references across XML tracks.
- **Smart Path Decoding & Media Resolver**: Decodes URL-encoded paths (`file://localhost/E%3a/...`), strips URL schemes, and recursively matches filenames across custom search folders.

---

## Installation

1. Download or zip the `fcpxml_import` folder.
2. In Blender 5.2, go to **Edit > Preferences > Add-ons > Install...** (or **Extensions**).
3. Select `fcpxml_import` and enable **FCPXML & XMEML Importer**.

---

## Usage

1. Open Blender 5.2 and switch to the **Video Editing** workspace.
2. Go to **File > Import > FCPXML / XMEML (.xml)**.
3. Select your `.xml` file (e.g. `Nanovex Scene Structure.xml`).
4. Video strips, audio strips, and timeline markers will be populated into the Blender VSE.

---

## License

GPL-3.0 License
