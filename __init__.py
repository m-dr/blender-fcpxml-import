import bpy
import xml.etree.ElementTree as ET
import os

bl_info = {
    "name": "FCPXML Importer (Full Featured)",
    "blender": (3, 0, 0),
    "category": "Sequencer",
    "description": "Imports FCPXML preserving track structure for video, audio, and text. Includes a dialog to find missing files.",
    "author": "tintwotin",
    "version": (1, 5, 0),
    "location": "File > Import > FCPXML (.xml)",
    "warning": "",
    "support": "COMMUNITY",
}

class FilePathIndex:
    def __init__(self, search_paths):
        self.search_paths = search_paths
        self.file_index = self.build_index(search_paths)
    
    def build_index(self, paths):
        file_index = {}
        for path in paths:
            if path and os.path.exists(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        lower_case_name = file.lower()
                        file_index[lower_case_name] = os.path.join(root, file)
        return file_index
    
    def find_file(self, filename):
        if not filename: return None
        lower_case_name = os.path.basename(filename.lower())
        return self.file_index.get(lower_case_name, None)

def parse_fcpxml(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    sequences = []
    
    for sequence in root.findall(".//sequence"):
        seq_name = sequence.find("name").text or "Unnamed Sequence"
        duration_node = sequence.find("duration")
        duration = int(duration_node.text) if duration_node is not None and duration_node.text.isdigit() else 1
        rate_node = sequence.find("rate/timebase")
        rate = int(rate_node.text) if rate_node is not None and rate_node.text.isdigit() else 30
        width_node = sequence.find(".//samplecharacteristics/width")
        width = int(width_node.text) if width_node is not None and width_node.text.isdigit() else 1920
        height_node = sequence.find(".//samplecharacteristics/height")
        height = int(height_node.text) if height_node is not None and height_node.text.isdigit() else 1080
        
        tracks = []
        for track in sequence.findall(".//track"):
            clips = []
            for clip in track.findall(".//clipitem"):
                clip_name = clip.find("name").text or "Unnamed Clip"
                start_node = clip.find("start")
                start = int(start_node.text) if start_node is not None and start_node.text.isdigit() else 0
                end_node = clip.find("end")
                end = int(end_node.text) if end_node is not None and end_node.text.isdigit() else start + 30
                
                duration_clip = end - start
                clip_type, text_content, file_path = "unknown", None, None
                
                text_node = clip.find("text")
                if text_node is not None:
                    clip_type, text_content = "text", text_node.text
                else:
                    path_node = clip.find(".//file/pathurl")
                    if path_node is not None:
                        file_path = path_node.text
                        if clip.find(".//media/video") is not None: clip_type = "video"
                        elif clip.find(".//media/audio") is not None: clip_type = "audio"

                clips.append({
                    "type": clip_type, "name": clip_name, "start": start,
                    "duration": duration_clip, "file_path": file_path,
                    "text_content": text_content,
                })
            tracks.append({"clips": clips})
        
        sequences.append({
            "name": seq_name, "duration": duration, "rate": rate,
            "width": width, "height": height, "tracks": tracks
        })
    return sequences

def configure_scene(context, width, height, fps, duration):
    scene = context.scene
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.fps = fps
    scene.frame_start = 0
    scene.frame_end = int(duration) if duration > 0 else 250
    if not scene.sequence_editor:
        scene.sequence_editor_create()

def import_fcpxml(context, filepath, report_error, search_paths=None):
    base_dir = os.path.dirname(filepath)
    sequences = parse_fcpxml(filepath)
    
    # Consolidate all search paths: the XML's directory is always first.
    all_search_paths = [base_dir]
    if search_paths:
        all_search_paths.extend(search_paths)
        
    file_index = FilePathIndex(all_search_paths)
    missing_files = {}
    
    for seq in sequences:
        configure_scene(context, seq['width'], seq['height'], seq['rate'], seq['duration'])
        vse = context.scene.sequence_editor
        
        for channel_idx, track in enumerate(seq['tracks'], start=1):
            for clip in track['clips']:
                if clip['type'] == 'text':
                    strip = vse.sequences.new_effect(
                        name=clip['name'], type='TEXT', channel=channel_idx,
                        frame_start=clip['start'], frame_end=clip['start'] + clip['duration']
                    )
                    strip.text = clip['text_content'] or clip['name']
                    strip.font_size = 30
                    strip.location = (0.5, 0.1)
                    strip.use_shadow = True
                    strip.shadow_color = (0, 0, 0, 0.8)
                    strip.use_outline = True
                    strip.outline_width = 0.1
                    strip.wrap_width = 0.7
                    strip.anchor_x = 'CENTER'
                    strip.anchor_y = 'TOP'
                    
                elif clip['type'] in ['video', 'audio']:
                    resolved_path = file_index.find_file(clip['file_path'])
                    if resolved_path and os.path.isfile(resolved_path):
                        if clip['type'] == 'video':
                            strip = vse.sequences.new_image(
                                name=clip['name'], filepath=resolved_path,
                                channel=channel_idx, frame_start=clip['start']
                            )
                            strip.frame_final_duration = clip['duration']
                        # Audio import logic can be added here if needed
                    else:
                        missing_files[clip['file_path'] or clip['name']] = all_search_paths
                        
    return {'FINISHED'}, missing_files

class FCPXMLImportOperator(bpy.types.Operator):
    bl_idname = "sequencer.import_fcpxml"
    bl_label = "Import FCPXML"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    search_path: bpy.props.StringProperty(
        name="Search Folder",
        description="Optional folder to search for missing media files",
        subtype='DIR_PATH'
    )
    
    def execute(self, context):
        search_paths = [self.search_path] if self.search_path else None
        
        result, missing_files = import_fcpxml(
            context, 
            self.filepath, 
            self.report,
            search_paths=search_paths
        )
        
        if missing_files:
            missing_list = ", ".join(set(missing_files.keys()))
            self.report({'WARNING'}, f"Still missing files: {missing_list}. Check console.")
            print("\n--- FCPXML IMPORTER: MISSING FILES ---")
            for file, paths in missing_files.items():
                print(f"File not found: {file}")
                print(f"  Searched in: {', '.join(paths)}")
            print("--------------------------------------\n")
            # Pop up the dialog again to allow user to choose another folder
            return self.invoke_search(context)
        
        self.report({'INFO'}, "FCPXML import successful.")
        return result
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def invoke_search(self, context):
        """This is called when files are missing to pop up the search dialog."""
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        """Draws the UI for the missing files dialog."""
        layout = self.layout
        layout.label(text="Some media files were not found.")
        layout.label(text="Please specify a folder to search in:")
        layout.prop(self, "search_path")

def menu_func_import(self, context):
    self.layout.operator(FCPXMLImportOperator.bl_idname, text="FCPXML (.xml)")

def register():
    bpy.utils.register_class(FCPXMLImportOperator)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(FCPXMLImportOperator)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
