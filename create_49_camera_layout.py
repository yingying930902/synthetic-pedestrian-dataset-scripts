"""
create_49_camera_layout.py

Create a 49-camera layout in Blender for synthetic pedestrian video rendering.

This script is intended to be run inside Blender's Python environment.

Camera layout:
    1. Ring cameras:
        - Radii: 4.0 m and 5.0 m
        - Heights: 1.0 m, 3.0 m, and 5.0 m
        - Viewing angles: 0°, 30°, 60°, 90°, 120°, 150°, and 180°
        - Total: 2 radii × 3 heights × 7 angles = 42 cameras

    2. Extra side cameras:
        - Radius/distance: 3.0 m
        - Heights: 1.0 m, 3.0 m, and 5.0 m
        - Viewing angle: 90°
        - Total: 3 cameras

    3. Top-down cameras:
        - Heights: 4.0 m, 5.0 m, 6.0 m, and 7.0 m
        - Total: 4 cameras

Total:
    42 + 3 + 4 = 49 cameras

Camera naming:
    Ring cameras:
        Camera_R4.0m_H1.0m_000
        Camera_R4.0m_H1.0m_030
        ...
        Camera_R5.0m_H5.0m_180

    Extra side cameras:
        ExtraCam_R3.0m_H1.0m_090
        ExtraCam_R3.0m_H3.0m_090
        ExtraCam_R3.0m_H5.0m_090

    Top-down cameras:
        TopDownCam_4.00m
        TopDownCam_5.00m
        TopDownCam_6.00m
        TopDownCam_7.00m

Camera optical setting:
    - Horizontal field of view: 92 degrees
    - Sensor width: 36 mm
    - Focal length is computed from the horizontal field of view.

Notes:
    - The script creates or reuses a collection named "CameraArray".
    - Existing cameras inside this collection are removed before new cameras are created.
    - Cameras outside this collection are not affected.
    - Ring cameras and ExtraCam look at (0, 0, 1).
    - TopDownCam cameras look at (0, 0, 0).
    - Blender units are assumed to be metres.
"""

import math

import bpy
from mathutils import Vector


# =============================================================================
# User settings
# =============================================================================

# Name of the camera collection.
CAMERA_COLLECTION_NAME = "CameraArray"

# Ring camera layout.
RING_RADII = [4.0, 5.0]
RING_HEIGHTS = [1.0, 3.0, 5.0]
RING_ANGLES_DEG = [0, 30, 60, 90, 120, 150, 180]

# Extra side-view cameras.
EXTRA_RADIUS = 3.0
EXTRA_HEIGHTS = [1.0, 3.0, 5.0]
EXTRA_ANGLE_DEG = 90

# Top-down cameras.
TOP_DOWN_HEIGHTS = [4.0, 5.0, 6.0, 7.0]

# All non-top-down cameras look at this point.
LOOK_AT = Vector((0.0, 0.0, 1.0))

# Top-down cameras look vertically down at this point.
TOP_DOWN_LOOK_AT = Vector((0.0, 0.0, 0.0))

# Camera display size in Blender viewport.
CAMERA_DISPLAY_SIZE = 0.6

# Camera optical settings.
HFOV_DEG = 92.0
SENSOR_WIDTH_MM = 36.0


# =============================================================================
# Helper functions
# =============================================================================

def focal_length_from_horizontal_fov(hfov_deg, sensor_width_mm):
    """
    Compute focal length in millimetres from horizontal field of view.

    Formula:
        f = (sensor_width / 2) / tan(hfov / 2)
    """
    hfov_rad = math.radians(hfov_deg)
    return (sensor_width_mm / 2.0) / math.tan(hfov_rad / 2.0)


LENS_MM = focal_length_from_horizontal_fov(HFOV_DEG, SENSOR_WIDTH_MM)


def get_or_create_collection_and_clear_cameras(collection_name):
    """
    Get or create a collection and remove old camera objects inside it.

    Only cameras in the target collection are removed. Objects in other
    collections are not affected.
    """
    if collection_name in bpy.data.collections:
        collection = bpy.data.collections[collection_name]

        for obj in list(collection.objects):
            if obj.type == "CAMERA":
                bpy.data.objects.remove(obj, do_unlink=True)
    else:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)

    return collection


def add_to_collection_only(obj, target_collection):
    """
    Link an object only to the target collection.

    This removes the object from any other collections, including the root scene
    collection, then links it to the target collection.
    """
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)

    target_collection.objects.link(obj)


def look_at(obj, target):
    """
    Rotate an object so that its local -Z axis points to the target.

    Blender cameras look along their local -Z axis.
    """
    direction = target - obj.location

    if direction.length == 0:
        raise ValueError(f"Camera '{obj.name}' is located at its look-at target.")

    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_camera_properties(camera):
    """
    Set shared camera display and optical properties.
    """
    camera.data.display_size = CAMERA_DISPLAY_SIZE
    camera.data.lens = LENS_MM
    camera.data.sensor_width = SENSOR_WIDTH_MM


def format_angle(angle_deg):
    """
    Format angle as a 3-digit string, for example 0 -> 000 and 30 -> 030.
    """
    return f"{int(angle_deg):03d}"


def create_camera(location, name, look_at_target, collection):
    """
    Create one camera, set its properties and orientation, and move it into the
    target collection.
    """
    bpy.ops.object.camera_add(location=location)
    camera = bpy.context.active_object

    setup_camera_properties(camera)
    camera.name = name
    look_at(camera, look_at_target)
    add_to_collection_only(camera, collection)

    return camera


# =============================================================================
# Main camera creation
# =============================================================================

def create_49_camera_layout():
    """
    Create the full 49-camera layout.
    """
    camera_collection = get_or_create_collection_and_clear_cameras(
        CAMERA_COLLECTION_NAME
    )

    created_cameras = []

    # -------------------------------------------------------------------------
    # 1. Ring cameras: 42 cameras
    # -------------------------------------------------------------------------
    for radius in RING_RADII:
        for height in RING_HEIGHTS:
            for angle_deg in RING_ANGLES_DEG:
                theta = math.radians(angle_deg)

                # The ring is defined in Blender's X-Y horizontal plane.
                x = radius * math.cos(theta)
                y = radius * math.sin(theta)
                z = height

                camera_name = (
                    f"Camera_R{radius:.1f}m_"
                    f"H{height:.1f}m_"
                    f"{format_angle(angle_deg)}"
                )

                camera = create_camera(
                    location=(x, y, z),
                    name=camera_name,
                    look_at_target=LOOK_AT,
                    collection=camera_collection,
                )

                created_cameras.append(camera)

    # -------------------------------------------------------------------------
    # 2. Extra side cameras: 3 cameras
    # -------------------------------------------------------------------------
    theta = math.radians(EXTRA_ANGLE_DEG)
    x = EXTRA_RADIUS * math.cos(theta)
    y = EXTRA_RADIUS * math.sin(theta)

    for height in EXTRA_HEIGHTS:
        z = height

        camera_name = (
            f"ExtraCam_R{EXTRA_RADIUS:.1f}m_"
            f"H{height:.1f}m_"
            f"{format_angle(EXTRA_ANGLE_DEG)}"
        )

        camera = create_camera(
            location=(x, y, z),
            name=camera_name,
            look_at_target=LOOK_AT,
            collection=camera_collection,
        )

        created_cameras.append(camera)

    # -------------------------------------------------------------------------
    # 3. Top-down cameras: 4 cameras
    # -------------------------------------------------------------------------
    for height in TOP_DOWN_HEIGHTS:
        camera_name = f"TopDownCam_{height:.2f}m"

        camera = create_camera(
            location=(0.0, 0.0, height),
            name=camera_name,
            look_at_target=TOP_DOWN_LOOK_AT,
            collection=camera_collection,
        )

        created_cameras.append(camera)

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("=" * 70)
    print("49-camera layout creation finished")
    print(f"Collection:      {CAMERA_COLLECTION_NAME}")
    print(f"Camera count:    {len(created_cameras)}")
    print("Expected count:  49")
    print(f"HFOV:            {HFOV_DEG:.2f} degrees")
    print(f"Sensor width:    {SENSOR_WIDTH_MM:.2f} mm")
    print(f"Focal length:    {LENS_MM:.4f} mm")
    print("=" * 70)

    if len(created_cameras) != 49:
        raise RuntimeError(
            f"Unexpected camera count: {len(created_cameras)}. Expected 49."
        )

    return created_cameras


# =============================================================================
# Run script
# =============================================================================

if __name__ == "__main__":
    create_49_camera_layout()
