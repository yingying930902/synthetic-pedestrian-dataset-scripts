"""
render_videos_from_camera_collection.py

Batch-render one animation video from each camera in a Blender camera collection.

This script is intended to be run inside Blender's Python environment.

Purpose:
    Given a Blender scene with an animated pedestrian and a set of virtual
    cameras, this script renders the full animation once from each camera view
    and saves the outputs as MP4/H.264 video files.

Default behavior:
    - Reads cameras from a collection named "CameraArray".
    - Sorts cameras by name for stable output ordering.
    - Saves one MP4 file per camera.
    - Output file naming:
        01_<camera_name>.mp4
        02_<camera_name>.mp4
        ...
    - Uses MP4 container with H.264 video codec.
    - Disables audio.

Notes:
    - This script renders animation, not still images.
    - The scene frame range, frame rate, resolution, render engine, lighting,
      materials, and animation should be configured in Blender before running.
    - Existing video files with the same names may be overwritten by Blender.
"""

import os
import re
from pathlib import Path

import bpy


# =============================================================================
# User settings
# =============================================================================

# Name of the collection containing the cameras to render.
CAMERA_COLLECTION_NAME = "CameraArray"

# Output folder for rendered videos.
# Change this path for your own dataset or speed condition.
OUTPUT_DIR = r"C:\Blender\all_49cams"

# Render output format.
VIDEO_CONTAINER = "MPEG4"
VIDEO_CODEC = "H264"

# Blender FFMPEG quality settings.
CONSTANT_RATE_FACTOR = "HIGH"
FFMPEG_PRESET = "GOOD"

# If True, cameras are sorted by name before rendering.
SORT_CAMERAS_BY_NAME = True

# If True, include a two-digit index before the camera name.
ADD_INDEX_PREFIX = True


# =============================================================================
# Helper functions
# =============================================================================

def safe_filename(name):
    """
    Convert an object name into a file-system-safe name.
    """
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def iter_collection_objects_recursive(collection):
    """
    Iterate through all objects in a collection and its sub-collections.
    """
    for obj in collection.objects:
        yield obj

    for child in collection.children:
        yield from iter_collection_objects_recursive(child)


def get_cameras_from_collection(collection_name):
    """
    Return all camera objects in the specified collection, including cameras in
    nested sub-collections.
    """
    collection = bpy.data.collections.get(collection_name)

    if collection is None:
        raise RuntimeError(f'Collection not found: "{collection_name}"')

    cameras = [
        obj
        for obj in iter_collection_objects_recursive(collection)
        if obj.type == "CAMERA"
    ]

    if SORT_CAMERAS_BY_NAME:
        cameras.sort(key=lambda cam: cam.name)

    if not cameras:
        raise RuntimeError(f'No cameras found in collection "{collection_name}"')

    return cameras


def setup_video_render_settings(scene):
    """
    Configure Blender render output as MP4/H.264 video.
    """
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = VIDEO_CONTAINER
    scene.render.ffmpeg.codec = VIDEO_CODEC
    scene.render.ffmpeg.constant_rate_factor = CONSTANT_RATE_FACTOR
    scene.render.ffmpeg.ffmpeg_preset = FFMPEG_PRESET

    # Disable audio to avoid audio-related export issues.
    scene.render.ffmpeg.audio_codec = "NONE"


def make_output_path(output_dir, camera, index=None):
    """
    Create an output path for one camera video.
    """
    camera_name = safe_filename(camera.name)

    if ADD_INDEX_PREFIX and index is not None:
        filename = f"{index:02d}_{camera_name}.mp4"
    else:
        filename = f"{camera_name}.mp4"

    return Path(output_dir) / filename


# =============================================================================
# Main rendering function
# =============================================================================

def render_videos_from_camera_collection():
    """
    Render the full scene animation once from each camera in the target
    collection.
    """
    scene = bpy.context.scene

    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    setup_video_render_settings(scene)

    cameras = get_cameras_from_collection(CAMERA_COLLECTION_NAME)

    print("=" * 70)
    print("Batch video rendering from camera collection")
    print(f"Camera collection: {CAMERA_COLLECTION_NAME}")
    print(f"Camera count:      {len(cameras)}")
    print(f"Output folder:     {output_dir}")
    print(f"Frame range:       {scene.frame_start} -> {scene.frame_end}")
    print(f"Resolution:        {scene.render.resolution_x} x {scene.render.resolution_y}")
    print(f"Frame rate:        {scene.render.fps / scene.render.fps_base}")
    print(f"Video format:      {VIDEO_CONTAINER} / {VIDEO_CODEC}")
    print("=" * 70)

    for index, camera in enumerate(cameras, start=1):
        scene.camera = camera

        output_path = make_output_path(output_dir, camera, index)
        scene.render.filepath = str(output_path)

        location = camera.matrix_world.translation
        print(
            f"[{index:02d}/{len(cameras):02d}] Rendering {camera.name} "
            f"at location ({location.x:.3f}, {location.y:.3f}, {location.z:.3f})"
        )
        print(f"Output: {output_path}")

        bpy.ops.render.render(animation=True, write_still=False)

    print("=" * 70)
    print("All camera videos have been rendered.")
    print(f"Output folder: {output_dir}")
    print("=" * 70)


# =============================================================================
# Run script
# =============================================================================

if __name__ == "__main__":
    render_videos_from_camera_collection()
