"""
export_camera_intrinsic_file.py

Export camera intrinsic parameters from Blender to a JSON file.

This script is intended to be run inside Blender's Python environment.

Purpose:
    Export image resolution and camera intrinsic matrix K for one selected
    Blender camera. If all cameras share the same optical settings, exporting
    the intrinsics from one representative camera is sufficient.

Output JSON fields:
    resolution
    K

Output example:
    {
      "resolution": [3840, 2160],
      "K": [
        [fx, 0.0, cx],
        [0.0, fy, cy],
        [0.0, 0.0, 1.0]
      ]
    }

Coordinate convention:
    The intrinsic matrix K follows the standard pinhole camera model:

        s [u, v, 1]^T = K [X/Z, Y/Z, 1]^T

    where:
        fx, fy = focal lengths in pixels
        cx, cy = principal point in pixels

Notes:
    - The script assumes a pinhole camera model.
    - Lens distortion is not exported. If no distortion is applied in Blender,
      this is consistent with an ideal synthetic camera.
    - Blender units do not affect the intrinsic matrix.
"""

import json
from pathlib import Path

import bpy


# =============================================================================
# User settings
# =============================================================================

# Option 1:
# Export intrinsics from the active scene camera.
# If this is True, CAMERA_NAME is ignored.
USE_SCENE_CAMERA = True

# Option 2:
# Export intrinsics from a named camera.
# Used only when USE_SCENE_CAMERA = False.
CAMERA_NAME = "Camera_R4.0m_H1.0m_000"

# Output JSON path.
# "//" means the folder where the current .blend file is saved.
JSON_PATH = bpy.path.abspath("//camera_intrinsic_file.json")

# Numeric cleanup thresholds.
EPS_ZERO = 1e-9
EPS_INT = 1e-6


# =============================================================================
# Helper functions
# =============================================================================

def snap_num(value, eps_zero=EPS_ZERO, eps_int=EPS_INT):
    """
    Clean small floating-point numerical noise for more readable JSON output.
    """
    value = float(value)

    if abs(value) < eps_zero:
        return 0.0

    rounded = round(value)
    if abs(value - rounded) < eps_int:
        return float(rounded)

    return value


def get_render_resolution(scene):
    """
    Return effective render resolution in pixels.

    Blender resolution is affected by resolution_percentage.
    """
    scale = scene.render.resolution_percentage / 100.0

    width = int(round(scene.render.resolution_x * scale))
    height = int(round(scene.render.resolution_y * scale))

    return width, height


def get_target_camera(scene):
    """
    Return the camera used for intrinsic export.
    """
    if USE_SCENE_CAMERA:
        camera = scene.camera
        if camera is None:
            raise RuntimeError(
                "USE_SCENE_CAMERA is True, but no active scene camera is set."
            )
        return camera

    if CAMERA_NAME not in bpy.data.objects:
        raise RuntimeError(f'Camera object not found: "{CAMERA_NAME}"')

    camera = bpy.data.objects[CAMERA_NAME]

    if camera.type != "CAMERA":
        raise RuntimeError(
            f'Object "{CAMERA_NAME}" is not a camera. Current type: {camera.type}'
        )

    return camera


def compute_intrinsic_matrix(camera, scene):
    """
    Compute the 3 x 3 camera intrinsic matrix K from Blender camera settings.

    This follows Blender's pinhole camera model and accounts for:
        - focal length
        - sensor size
        - sensor fit
        - render resolution
        - pixel aspect ratio
        - principal point shift

    Returned K is:
        [[fx, 0,  cx],
         [0,  fy, cy],
         [0,  0,  1 ]]
    """
    camera_data = camera.data

    width_px, height_px = get_render_resolution(scene)

    pixel_aspect_ratio = (
        scene.render.pixel_aspect_x / scene.render.pixel_aspect_y
    )

    sensor_fit = camera_data.sensor_fit

    if sensor_fit == "AUTO":
        if width_px >= height_px:
            sensor_fit = "HORIZONTAL"
        else:
            sensor_fit = "VERTICAL"

    if sensor_fit == "VERTICAL":
        # Sensor height is the reference dimension.
        sensor_size_mm = camera_data.sensor_height
        fy = camera_data.lens * height_px / sensor_size_mm
        fx = fy / pixel_aspect_ratio
    else:
        # Sensor width is the reference dimension.
        sensor_size_mm = camera_data.sensor_width
        fx = camera_data.lens * width_px / sensor_size_mm
        fy = fx * pixel_aspect_ratio

    # Principal point.
    # Blender shift_x and shift_y are expressed relative to the view size.
    # Positive shift_x moves the frame horizontally.
    # The signs below follow the common Blender-to-CV intrinsic export convention.
    cx = width_px * (0.5 - camera_data.shift_x)
    cy = height_px * (0.5 + camera_data.shift_y)

    K = [
        [snap_num(fx), 0.0, snap_num(cx)],
        [0.0, snap_num(fy), snap_num(cy)],
        [0.0, 0.0, 1.0],
    ]

    return K


def export_camera_intrinsics():
    """
    Export image resolution and intrinsic matrix K to JSON.
    """
    scene = bpy.context.scene
    camera = get_target_camera(scene)

    width_px, height_px = get_render_resolution(scene)
    K = compute_intrinsic_matrix(camera, scene)

    output = {
        "resolution": [int(width_px), int(height_px)],
        "K": K,
    }

    output_path = Path(JSON_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as fp:
        json.dump(output, fp, indent=2)

    print("=" * 70)
    print("Camera intrinsic export finished")
    print(f"Camera:        {camera.name}")
    print(f"Resolution:    {width_px} x {height_px}")
    print(f"Lens:          {camera.data.lens:.6f} mm")
    print(f"Sensor width:  {camera.data.sensor_width:.6f} mm")
    print(f"Sensor height: {camera.data.sensor_height:.6f} mm")
    print(f"Sensor fit:    {camera.data.sensor_fit}")
    print("K:")
    for row in K:
        print(" ", row)
    print(f"Output JSON:   {output_path}")
    print("=" * 70)


# =============================================================================
# Run script
# =============================================================================

if __name__ == "__main__":
    export_camera_intrinsics()
