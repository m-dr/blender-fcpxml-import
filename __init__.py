import bpy
import xml.etree.ElementTree as ET
import os
import urllib.parse
import logging
from typing import List, Dict, Any, Tuple, Optional

bl_info = {
    "name": "FCPXML & XMEML Importer",
    "author": "tintwotin, Omniscye, Antigravity",
    "version": (2, 2, 0),
    "blender": (3, 0, 0),
    "location": "File > Import > FCPXML / XMEML (.xml)",
    "description": "Imports FCP7 XML (.xmeml) and FCPX XML (.fcpxml) files preserving track structure, markers, video, audio, and text.",
    "warning": "",
    "category": "Sequencer",
    "support": "COMMUNITY",
}

class MediaResolver:
    def __init__(self, search_paths: List[str]):
        self.search_paths = [p for p in search_paths if p and os.path.exists(p)]
        self.file_cache = {}
        self._build_file_cache()
    
    def _add_dir_to_cache(self, directory: str):
        if not os.path.exists(directory):
            return
        for root, _, files in os.walk(directory):
            for filename in files:
                norm_name = os.path.normcase(filename)
                if norm_name not in self.file_cache:
                    self.file_cache[norm_name] = os.path.normpath(os.path.join(root, filename))

    def _build_file_cache(self):
        for path in self.search_paths:
            self._add_dir_to_cache(path)
    
    @staticmethod
    def clean_url_path(pathurl: str) -> Tuple[str, str]:
        if not pathurl:
            return "", ""
        decoded = urllib.parse.unquote(pathurl)
        parsed = urllib.parse.urlparse(decoded)
        
        path = ""
        if parsed.scheme == "file":
            netloc = parsed.netloc
            p_path = parsed.path
            if netloc and len(netloc) == 2 and netloc[1] == ":":
                path = netloc + p_path
            elif netloc and netloc.lower() != "localhost":
                path = netloc + p_path
            else:
                path = p_path
                
            if len(path) > 3 and path[0] == "/" and path[2] == ":":
                path = path[1:]
        else:
            path = decoded
            for prefix in ["file://localhost/", "file:///", "file://"]:
                if path.startswith(prefix):
                    path = path[len(prefix):]
                    break
            if len(path) > 3 and path[0] == "/" and path[2] == ":":
                path = path[1:]

        path = os.path.normpath(path)
        filename = os.path.basename(path)
        return path, filename

    def resolve_media_path(self, original_pathurl: str, clip_name: str = "") -> str:
        clean_path, filename = self.clean_url_path(original_pathurl)
        
        # 1. Direct file check on clean_path
        if clean_path and os.path.isfile(clean_path):
            return clean_path
        
        # 2. Add directory of clean_path to search paths if it exists
        if clean_path:
            clean_dir = os.path.dirname(clean_path)
            if clean_dir and os.path.exists(clean_dir) and clean_dir not in self.search_paths:
                self.search_paths.append(clean_dir)
                self._add_dir_to_cache(clean_dir)
                if os.path.isfile(clean_path):
                    return clean_path
        
        # 3. Match filename in file cache
        if filename:
            norm_fn = os.path.normcase(filename)
            if norm_fn in self.file_cache:
                return self.file_cache[norm_fn]
        
        # 4. Match clip_name in file cache
        if clip_name:
            norm_cn = os.path.normcase(clip_name)
            if norm_cn in self.file_cache:
                return self.file_cache[norm_cn]
        
        # 5. Substring / partial match
        if filename:
            norm_fn = os.path.normcase(filename)
            for name, full_path in self.file_cache.items():
                if norm_fn in name or name in norm_fn:
                    return full_path
                    
        return ""

class FCPXMLParser:
    @staticmethod
    def parse(filepath: str) -> List[Dict[str, Any]]:
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            tag = root.tag.lower()
            
            if tag == "xmeml":
                return FCPXMLParser._parse_xmeml(root)
            elif tag == "fcpxml":
                return FCPXMLParser._parse_fcpxml(root)
            else:
                sequences = root.findall(".//sequence")
                if sequences:
                    return FCPXMLParser._parse_xmeml(root)
                return []
        except Exception as e:
            logging.error(f"XML Parsing Exception: {e}")
            return []

    @staticmethod
    def _parse_xmeml(root: ET.Element) -> List[Dict[str, Any]]:
        sequences = []
        for sequence in root.findall(".//sequence"):
            seq_name = sequence.findtext("name") or "Unnamed Sequence"
            
            duration_text = sequence.findtext("duration")
            duration = int(duration_text) if duration_text and duration_text.isdigit() else 0
            
            tb_text = sequence.findtext("rate/timebase")
            timebase = int(tb_text) if tb_text and tb_text.isdigit() else 30
            ntsc = (sequence.findtext("rate/ntsc") or "").upper() == "TRUE"
            fps = (timebase * 1000 / 1001) if ntsc else float(timebase)
            
            w_text = sequence.findtext(".//samplecharacteristics/width")
            h_text = sequence.findtext(".//samplecharacteristics/height")
            width = int(w_text) if w_text and w_text.isdigit() else 1920
            height = int(h_text) if h_text and h_text.isdigit() else 1080
            
            # Sequence markers directly under sequence
            seq_markers = []
            for m in sequence.findall("marker"):
                name = m.findtext("name") or ""
                comment = m.findtext("comment") or ""
                in_f = m.findtext("in")
                out_f = m.findtext("out")
                if in_f is not None and in_f.lstrip("-").isdigit():
                    seq_markers.append({
                        "name": name,
                        "comment": comment,
                        "in": int(in_f),
                        "out": int(out_f) if out_f and out_f.lstrip("-").isdigit() else -1
                    })

            # Registry for reusable <file id="..."> elements
            file_registry = {}
            for f in sequence.findall(".//file"):
                f_id = f.get("id")
                if f_id:
                    if f_id not in file_registry:
                        file_registry[f_id] = {}
                    purl = f.findtext("pathurl")
                    fname = f.findtext("name")
                    dur = f.findtext("duration")
                    if purl:
                        file_registry[f_id]["pathurl"] = purl
                    if fname:
                        file_registry[f_id]["name"] = fname
                    if dur and dur.isdigit():
                        file_registry[f_id]["duration"] = int(dur)

            tracks = []

            # Parse video tracks
            video_tracks = sequence.findall(".//media/video/track")
            for t_idx, track in enumerate(video_tracks, start=1):
                clips = FCPXMLParser._extract_xmeml_clips(track, "video", file_registry)
                if clips:
                    tracks.append({"track_type": "video", "track_num": t_idx, "clips": clips})

            # Parse audio tracks
            audio_tracks = sequence.findall(".//media/audio/track")
            for t_idx, track in enumerate(audio_tracks, start=1):
                clips = FCPXMLParser._extract_xmeml_clips(track, "audio", file_registry)
                if clips:
                    tracks.append({"track_type": "audio", "track_num": t_idx, "clips": clips})

            # Fallback for generic tracks if media/video or media/audio not specified
            if not tracks:
                generic_tracks = sequence.findall(".//track")
                for t_idx, track in enumerate(generic_tracks, start=1):
                    clips = FCPXMLParser._extract_xmeml_clips(track, "video", file_registry)
                    if clips:
                        tracks.append({"track_type": "video", "track_num": t_idx, "clips": clips})

            sequences.append({
                "name": seq_name,
                "duration": duration,
                "timebase": timebase,
                "fps": fps,
                "width": width,
                "height": height,
                "markers": seq_markers,
                "tracks": tracks
            })
        return sequences

    @staticmethod
    def _extract_xmeml_clips(track: ET.Element, default_media_type: str, file_registry: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        clips = []
        for clip in track.findall("clipitem"):
            clip_name = clip.findtext("name") or "Unnamed Clip"
            start = int(clip.findtext("start") or 0)
            end = int(clip.findtext("end") or 0)
            in_frame = int(clip.findtext("in") or 0)
            out_frame = int(clip.findtext("out") or (end - start + in_frame))
            dur_clip = end - start if (end > start) else (out_frame - in_frame)
            
            clip_type = default_media_type
            text_content = None
            pathurl = ""

            text_node = clip.find("text")
            if text_node is not None:
                clip_type = "text"
                text_content = text_node.text
            else:
                file_elem = clip.find("file")
                if file_elem is not None:
                    f_id = file_elem.get("id")
                    purl = file_elem.findtext("pathurl")
                    if purl:
                        pathurl = purl
                    elif f_id and f_id in file_registry:
                        pathurl = file_registry[f_id].get("pathurl", "")

            clip_markers = []
            for cm in clip.findall("marker"):
                cname = cm.findtext("name") or ""
                ccomment = cm.findtext("comment") or ""
                cin = cm.findtext("in")
                cout = cm.findtext("out")
                if cin is not None and cin.lstrip("-").isdigit():
                    clip_markers.append({
                        "name": cname,
                        "comment": ccomment,
                        "in": int(cin),
                        "out": int(cout) if cout and cout.lstrip("-").isdigit() else -1
                    })

            clips.append({
                "type": clip_type,
                "name": clip_name,
                "start": start,
                "end": end,
                "in_frame": in_frame,
                "out_frame": out_frame,
                "duration": dur_clip,
                "file_path": pathurl,
                "text_content": text_content,
                "markers": clip_markers
            })
        return clips

    @staticmethod
    def _parse_fcpxml(root: ET.Element) -> List[Dict[str, Any]]:
        resources = {}
        for asset in root.findall(".//resources/asset"):
            aid = asset.get("id")
            src = asset.get("src", "")
            name = asset.get("name", "")
            resources[aid] = {"src": src, "name": name}

        format_res = {}
        for fmt in root.findall(".//resources/format"):
            fid = fmt.get("id")
            w = int(fmt.get("width") or 1920)
            h = int(fmt.get("height") or 1080)
            format_res[fid] = {"width": w, "height": h}

        sequences = []
        for seq in root.findall(".//sequence"):
            seq_name = seq.get("name") or "Unnamed Sequence"
            fmt_id = seq.get("format")
            
            width = format_res.get(fmt_id, {}).get("width", 1920) if fmt_id else 1920
            height = format_res.get(fmt_id, {}).get("height", 1080) if fmt_id else 1080
            fps = 30.0

            seq_markers = []
            for m in seq.findall(".//marker"):
                seq_markers.append({
                    "name": m.get("value") or m.get("comment") or "Marker",
                    "comment": m.get("comment") or "",
                    "in": 0,
                    "out": -1
                })

            tracks = []
            spine = seq.find("spine")
            if spine is not None:
                clips = []
                for child in spine:
                    tag_name = child.tag
                    c_name = child.get("name") or "Clip"
                    ref = child.get("ref")
                    pathurl = resources.get(ref, {}).get("src", "") if ref else ""
                    
                    clip_type = "video"
                    if tag_name in ["asset-clip", "clip", "video"]:
                        clip_type = "video"
                    elif tag_name in ["audio"]:
                        clip_type = "audio"
                    elif tag_name in ["title"]:
                        clip_type = "text"

                    clips.append({
                        "type": clip_type,
                        "name": c_name,
                        "start": 0,
                        "end": 30,
                        "in_frame": 0,
                        "out_frame": 30,
                        "duration": 30,
                        "file_path": pathurl,
                        "text_content": child.get("name"),
                        "markers": []
                    })
                if clips:
                    tracks.append({"track_type": "video", "track_num": 1, "clips": clips})

            sequences.append({
                "name": seq_name,
                "duration": 100,
                "timebase": 30,
                "fps": fps,
                "width": width,
                "height": height,
                "markers": seq_markers,
                "tracks": tracks
            })
        return sequences

class FCPXMLImporter:
    @staticmethod
    def configure_scene(context, width: int, height: int, fps: float, duration: int):
        scene = context.scene
        scene.render.resolution_x = width
        scene.render.resolution_y = height
        
        if abs(fps - 29.97) < 0.05:
            scene.render.fps = 30
            scene.render.fps_base = 1001 / 1000
        elif abs(fps - 23.976) < 0.05:
            scene.render.fps = 24
            scene.render.fps_base = 1001 / 1000
        elif abs(fps - 59.94) < 0.05:
            scene.render.fps = 60
            scene.render.fps_base = 1001 / 1000
        else:
            scene.render.fps = int(round(fps)) if fps > 0 else 30
            scene.render.fps_base = 1.0

        scene.frame_start = 1
        scene.frame_end = int(duration) if duration > 0 else 250
        
        if not scene.sequence_editor:
            scene.sequence_editor_create()

    @staticmethod
    def import_sequence(context, sequence: Dict[str, Any], media_resolver: MediaResolver) -> Tuple[List[str], int]:
        FCPXMLImporter.configure_scene(
            context,
            sequence['width'],
            sequence['height'],
            sequence['fps'],
            sequence['duration']
        )
        
        vse = context.scene.sequence_editor
        strips = getattr(vse, 'strips', getattr(vse, 'sequences', None))
        
        # Import Timeline Markers
        for marker in sequence.get("markers", []):
            m_name = marker["name"] if (marker["name"] and marker["name"] != "None") else (marker["comment"] or "Marker")
            frame_pos = marker["in"]
            context.scene.timeline_markers.new(name=m_name, frame=frame_pos)

        missing_files = []
        imported_clips_count = 0

        # Separate clips into video, audio, and text
        video_clips = []
        audio_clips = []
        text_clips = []

        for track in sequence.get("tracks", []):
            t_type = track.get("track_type", "video")
            for clip in track.get("clips", []):
                c_type = clip.get("type", t_type)
                if c_type == "text":
                    text_clips.append(clip)
                elif c_type == "video" or t_type == "video":
                    video_clips.append(clip)
                elif c_type == "audio" or t_type == "audio":
                    audio_clips.append(clip)

        # Deduplicate identical video clips (same file, start, in_frame, duration)
        unique_video_clips = []
        seen_video = set()
        for clip in video_clips:
            key = (clip.get("file_path"), clip.get("start"), clip.get("in_frame"), clip.get("duration"))
            if key not in seen_video:
                seen_video.add(key)
                unique_video_clips.append(clip)

        # Deduplicate identical audio clips (e.g. exploded stereo tracks A1/A2 from Premiere)
        unique_audio_clips = []
        seen_audio = set()
        for clip in audio_clips:
            key = (clip.get("file_path"), clip.get("start"), clip.get("in_frame"), clip.get("duration"))
            if key not in seen_audio:
                seen_audio.add(key)
                unique_audio_clips.append(clip)

        # Layout in Blender VSE:
        # Channel 1: Audio strip(s) (SOUND)
        # Channel 2: Video strip(s) (MOVIE)
        # Channel 3+: Text / Overlay strips (TEXT)

        # 1. Import Audio Strips on Channel 1
        for clip in unique_audio_clips:
            resolved_path = media_resolver.resolve_media_path(clip["file_path"], clip["name"])
            if resolved_path and os.path.isfile(resolved_path):
                strip = strips.new_sound(
                    name=clip["name"],
                    filepath=resolved_path,
                    channel=1,
                    frame_start=clip["start"]
                )
                strip.frame_offset_start = clip["in_frame"]
                strip.frame_final_duration = clip["duration"]
                imported_clips_count += 1
            else:
                missing_files.append(clip["file_path"] or clip["name"])

        # 2. Import Video Strips on Channel 2
        for clip in unique_video_clips:
            resolved_path = media_resolver.resolve_media_path(clip["file_path"], clip["name"])
            if resolved_path and os.path.isfile(resolved_path):
                strip = strips.new_movie(
                    name=clip["name"],
                    filepath=resolved_path,
                    channel=2,
                    frame_start=clip["start"]
                )
                strip.frame_offset_start = clip["in_frame"]
                strip.frame_final_duration = clip["duration"]
                imported_clips_count += 1
            else:
                missing_files.append(clip["file_path"] or clip["name"])

        # 3. Import Text Strips on Channel 3
        for clip in text_clips:
            strip = strips.new_effect(
                name=clip["name"],
                type="TEXT",
                channel=3,
                frame_start=clip["start"],
                length=clip["duration"]
            )
            strip.text = clip["text_content"] or clip["name"]
            strip.font_size = 30
            imported_clips_count += 1

        return missing_files, imported_clips_count

class SEQUENCER_OT_import_fcpxml(bpy.types.Operator):
    """Import FCPXML & XMEML files preserving video, audio, text, and markers"""
    bl_idname = "sequencer.import_fcpxml"
    bl_label = "Import FCPXML / XMEML"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    search_path: bpy.props.StringProperty(
        name="Search Folder",
        description="Optional folder to search for missing media files",
        subtype='DIR_PATH'
    )
    
    def execute(self, context):
        base_dir = os.path.dirname(self.filepath)
        search_paths = [base_dir]
        if self.search_path:
            search_paths.append(self.search_path)
            
        media_resolver = MediaResolver(search_paths)
        sequences = FCPXMLParser.parse(self.filepath)
        
        if not sequences:
            self.report({'ERROR'}, "Failed to parse FCPXML/XMEML sequence from file.")
            return {'CANCELLED'}

        missing_files = []
        total_clips = 0
        
        for sequence in sequences:
            missing, count = FCPXMLImporter.import_sequence(context, sequence, media_resolver)
            missing_files.extend(missing)
            total_clips += count
            
        if missing_files:
            missing_unique = list(set(missing_files))
            self.report({'WARNING'}, f"Imported {total_clips} clips. Missing media for {len(missing_unique)} files: {', '.join(missing_unique)}")
        else:
            self.report({'INFO'}, f"FCPXML import successful! Created {total_clips} strips.")
            
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

def menu_func_import(self, context):
    self.layout.operator(SEQUENCER_OT_import_fcpxml.bl_idname, text="FCPXML / XMEML (.xml)")

def register():
    bpy.utils.register_class(SEQUENCER_OT_import_fcpxml)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(SEQUENCER_OT_import_fcpxml)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
