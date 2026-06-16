"""
export_camera_extrinsic_file.py

Export camera extrinsic parameters from a Blender collection to a JSON file.

This script is intended to be run inside Blender's Python environment.

The exported extrinsics are expressed using:
    - Dataset/user world coordinate system
    - OpenCV camera coordinate system

Dataset/user world coordinate system:
    x_user =  x_blender
    y_user =  z_blender
    z_user = -y_blender

Dataset/user world origin in Blender world coordinates:
    ORIGIN_B = (0, 2, 0)

OpenCV camera coordinate system:
    +X right
    +Y down
    +Z forward

Output JSON fields for each camera:
    camera_name
    Rwc
    Twc
    Rcw
    Tcw
    T_wc_4x4
    T_cw_4x4

Definitions:
    Rwc, Twc:
        Transform a point from OpenCV camera coordinates to dataset/user world
        coordinates.

        P_world = Rwc @ P_camera + Twc

    Rcw, Tcw:
        Transform a point from dataset/user world coordinates to OpenCV camera
        coordinates.

        P_camera = Rcw @ P_world + Tcw

    T_wc_4x4:
        Homogeneous camera-to-world transformation matrix.

    T_cw_4x4:
        Homogeneous world-to-camera transformation matrix.

Notes:
    - Blender camera local coordinates are converted to OpenCV camera coordinates.
    - Blender units are assumed to be metres.
    - The script exports all camera objects in the selected collection, including
      cameras inside sub-collections.
"""

import json
import os
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


# =============================================================================
# User settings
# =============================================================================

# Name of the collection that contains the cameras to export.
COLLECTION_NAME = "CameraArray"

# Output JSON path.
# "//" means the folder where the current .blend file is saved.
JSON_PATH = bpy.path.abspath("//camera_extrinsic_file.json")

# Dataset/user-world origin expressed in Blender world coordinates.
ORIGIN_B = Vector((0.0, 2.0, 0.0))

# Numeric cleanup thresholds.
# Values with abs(x) < EPS_ZERO are written as 0.
# Values close to an integer within EPS_INT are snapped to that integer.
EPS_ZERO = 1e-9
EPS_INT = 1e-6


# =============================================================================
# Coordinate transforms
# =============================================================================

# Blender world -> dataset/user world.
# x_user =  x_blender
# y_user =  z_blender
# z_user = -y_blender
BLENDER_WORLD_TO_USER_WORLD = Matrix((
    (1.0,  0.0, 0.0),
    (0.0,  0.0, 1.0),
    (0.0, -1.0, 0.0),
))

# OpenCV camera -> Blender camera local coordinates.
#
# Blender camera local coordinates:
#     +X right, +Y up, -Z forward
#
# OpenCV camera coordinates:
#     +X right, +Y down, +Z forward
#
# Therefore:
#     x_blender_cam =  x_opencv_cam
#     y_blender_cam = -y_opencv_cam
#     z_blender_cam = -z_opencv_cam
OPENCV_CAMERA_TO_BLENDER_CAMERA = Matrix((
    (1.0,  0.0,  0.0),
    (0.0, -1.0,  0.0),
    (0.0,  0.0, -1.0),
))


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


def snap_vec(vector):
    """Apply snap_num to a 3D vector."""
    return Vector((
        snap_num(vector.x),
        snap_num(vector.y),
        snap_num(vector.z),
    ))


def snap_mat3(matrix):
    """Apply snap_num to a 3 x 3 matrix."""
    output = Matrix.Identity(3)
    for i in range(3):
        for j in range(3):
            output[i][j] = snap_num(matrix[i][j])
    return output


def mat3_to_list(matrix):
    """Convert a 3 x 3 matrix to a nested Python list."""
    return [[snap_num(matrix[i][j]) for j in range(3)] for i in range(3)]


def vec3_to_list(vector):
    """Convert a 3D vector to a Python list."""
    return [snap_num(vector.x), snap_num(vector.y), snap_num(vector.z)]


def mat4_from_rotation_translation(rotation, translation):
    """
    Build a 4 x 4 homogeneous transformation matrix from rotation and translation.
    """
    matrix = Matrix.Identity(4)

    for i in range(3):
        for j in range(3):
            matrix[i][j] = rotation[i][j]

    matrix[0][3] = translation.x
    matrix[1][3] = translation.y
    matrix[2][3] = translation.z

    return matrix


def mat4_to_list(matrix):
    """Convert a 4 x 4 matrix to a nested Python list."""
    return [[snap_num(matrix[i][j]) for j in range(4)] for i in range(4)]


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
    Return all camera objects in the specified collection, including sub-collections.
    """
    collection = bpy.data.collections.get(collection_name)

    if collection is None:
        raise RuntimeError(f'Collection not found: "{collection_name}"')

    cameras = [
        obj
        for obj in iter_collection_objects_recursive(collection)
        if obj.type == "CAMERA"
    ]

    cameras.sort(key=lambda obj: obj.name)

    if not cameras:
        raise RuntimeError(f'No cameras found in collection "{collection_name}"')

    return cameras


# =============================================================================
# Core extrinsic computation
# =============================================================================

def compute_camera_extrinsics_opencv_userworld(camera):
    """
    Compute camera extrinsics in the dataset/user world and OpenCV camera
    coordinate systems.

    Blender provides the camera-to-world transform:

        X_world_blender = R_wc_blender @ X_camera_blender + T_wc_blender

    Blender camera local coordinates and OpenCV camera coordinates are related by:

        X_camera_blender = C @ X_camera_opencv

    where C is OPENCV_CAMERA_TO_BLENDER_CAMERA.

    Dataset/user world coordinates are defined as:

        X_world_user = A @ (X_world_blender - ORIGIN_B)

    where A is BLENDER_WORLD_TO_USER_WORLD.

    Therefore:

        X_world_user
            = A @ (R_wc_blender @ C @ X_camera_opencv
                   + T_wc_blender
                   - ORIGIN_B)

        Rwc = A @ R_wc_blender @ C
        Twc = A @ (T_wc_blender - ORIGIN_B)

    Then:

        Rcw = Rwc.T
        Tcw = -Rcw @ Twc
    """
    camera_to_world_blender = camera.matrix_world.copy()

    rotation_wc_blender = camera_to_world_blender.to_3x3()
    translation_wc_blender = camera_to_world_blender.to_translation()

    rotation_wc_user = (
        BLENDER_WORLD_TO_USER_WORLD
        @ rotation_wc_blender
        @ OPENCV_CAMERA_TO_BLENDER_CAMERA
    )

    translation_wc_user = BLENDER_WORLD_TO_USER_WORLD @ (
        translation_wc_blender - ORIGIN_B
    )

    rotation_cw_user = rotation_wc_user.transposed()
    translation_cw_user = -(rotation_cw_user @ translation_wc_user)

    rotation_wc_user = snap_mat3(rotation_wc_user)
    rotation_cw_user = snap_mat3(rotation_cw_user)
    translation_wc_user = snap_vec(translation_wc_user)
    translation_cw_user = snap_vec(translation_cw_user)

    transform_wc_4x4 = mat4_from_rotation_translation(
        rotation_wc_user,
        translation_wc_user,
    )

    transform_cw_4x4 = mat4_from_rotation_translation(
        rotation_cw_user,
        translation_cw_user,
    )

    return {
        "camera_name": camera.name,
        "Rwc": mat3_to_list(rotation_wc_user),
        "Twc": vec3_to_list(translation_wc_user),
        "Rcw": mat3_to_list(rotation_cw_user),
        "Tcw": vec3_to_list(translation_cw_user),
        "T_wc_4x4": mat4_to_list(transform_wc_4x4),
        "T_cw_4x4": mat4_to_list(transform_cw_4x4),
    }


# =============================================================================
# Main export
# =============================================================================

def export_camera_extrinsics():
    """
    Export camera extrinsics for all cameras in COLLECTION_NAME to JSON_PATH.
    """
    cameras = get_cameras_from_collection(COLLECTION_NAME)

    results = [
        compute_camera_extrinsics_opencv_userworld(camera)
        for camera in cameras
    ]

    output_path = Path(JSON_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as fp:
        json.dump(results, fp, indent=2)

    print("=" * 70)
    print("Camera extrinsics export finished")
    print(f"Collection:   {COLLECTION_NAME}")
    print(f"Camera count: {len(results)}")
    print(f"Output JSON:  {output_path}")
    print("World system: x_user=x_blender, y_user=z_blender, z_user=-y_blender")
    print("Camera system: OpenCV, +X right, +Y down, +Z forward")
    print("=" * 70)

    for index, result in enumerate(results[:5]):
        print(f"[{index:02d}] {result['camera_name']}")
        print("  Twc:", result["Twc"])
        print("  Tcw:", result["Tcw"])


# =============================================================================
# Run script
# =============================================================================

if __name__ == "__main__":
    export_camera_extrinsics()
