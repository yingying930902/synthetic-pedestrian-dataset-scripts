"""
export_smpl24_joints_camera_coordinates.py

Export frame-wise SMPL-24-format 3D body-joint coordinates from a Blender
armature animation to separate CSV files in each camera coordinate system.

This script is intended to be run inside Blender's Python environment.

Output:
    One CSV file is created for each camera.

Output CSV columns:
    frame, time, joint id, joint name, X (m), Y (m), Z (m)

Output file naming:
    <camera_name>_joint_file.csv

Coordinate system:
    Joint positions are first extracted in Blender world coordinates, then
    transformed into each camera's local coordinate system.

    Blender camera local coordinate:
        +X right
        +Y up
        -Z forward

    OpenCV camera coordinate used in the exported CSV:
        +X right
        +Y down
        +Z forward

    Conversion from Blender camera coordinate to OpenCV camera coordinate:
        x_cv =  x_blender_camera
        y_cv = -y_blender_camera
        z_cv = -z_blender_camera

Joint extraction method:
    For each pose bone:
        bone_mat_world = armature.matrix_world @ pose_bone.matrix
        joint_world_b  = bone_mat_world @ Vector((0, 0, 0))

Notes:
    - The exported joint order follows the SMPL-24 joint order.
    - The actual joint locations are taken from the Character Creator skeleton
      using a predefined CC-bone-to-SMPL24 mapping.
    - Blender units are assumed to be metres.
"""

import csv
import re
from pathlib import Path

import bpy
from mathutils import Vector


# =============================================================================
# User settings
# =============================================================================

# Name of the armature object in Blender.
# Change this if your armature has a different name.
ARMATURE_NAME = "CC_neutral_without_marker"

# Output folder.
# "//" means the folder where the current .blend file is saved.
OUTPUT_FOLDER = bpy.path.abspath("//camera_coordinate_joint_files")

# Use relative time starting from 0 at the first exported frame.
# If False, time is calculated as frame / fps.
USE_RELATIVE_TIME = True

# Camera name prefixes to export.
# Set CAMERA_PREFIXES = None if you want to export all camera objects.
CAMERA_PREFIXES = ["Camera_", "ExtraCam_", "TopDownCam_"]


# =============================================================================
# SMPL-24 joint names and Character Creator bone mapping
# =============================================================================

SMPL24_NAMES = [
    "pelvis", "left_hip", "right_hip",
    "spine1", "left_knee", "right_knee",
    "spine2", "left_ankle", "right_ankle",
    "spine3", "left_foot", "right_foot",
    "neck", "left_collar", "right_collar",
    "head", "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_hand", "right_hand",
]

CC_BONES = [
    "CC_Base_Hip",            # 0  pelvis
    "CC_Base_L_Thigh",        # 1  left_hip
    "CC_Base_R_Thigh",        # 2  right_hip

    "CC_Base_Waist",          # 3  spine1
    "CC_Base_L_Calf",         # 4  left_knee
    "CC_Base_R_Calf",         # 5  right_knee

    "CC_Base_Spine01",        # 6  spine2
    "CC_Base_L_Foot",         # 7  left_ankle
    "CC_Base_R_Foot",         # 8  right_ankle

    "CC_Base_Spine02",        # 9  spine3
    "CC_Base_L_ToeBase",      # 10 left_foot
    "CC_Base_R_ToeBase",      # 11 right_foot

    "CC_Base_NeckTwist01",    # 12 neck
    "CC_Base_L_Clavicle",     # 13 left_collar
    "CC_Base_R_Clavicle",     # 14 right_collar

    "CC_Base_Head",           # 15 head
    "CC_Base_L_Upperarm",     # 16 left_shoulder
    "CC_Base_R_Upperarm",     # 17 right_shoulder

    "CC_Base_L_Forearm",      # 18 left_elbow
    "CC_Base_R_Forearm",      # 19 right_elbow

    "CC_Base_L_Hand",         # 20 left_wrist
    "CC_Base_R_Hand",         # 21 right_wrist

    "CC_Base_L_Mid1",         # 22 left_hand, finger proxy
    "CC_Base_R_Mid1",         # 23 right_hand, finger proxy
]


# =============================================================================
# Helper functions
# =============================================================================

def get_scene_frame_range(scene):
    """Return the inclusive frame range of the current Blender scene."""
    return int(scene.frame_start), int(scene.frame_end)


def get_scene_fps(scene):
    """Return the effective scene frame rate."""
    return float(scene.render.fps / scene.render.fps_base)


def safe_filename(name):
    """Make a string safe for use as a Windows/macOS/Linux file name."""
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def validate_armature():
    """Validate and return the target armature object."""
    if len(SMPL24_NAMES) != 24:
        raise ValueError(f"SMPL24_NAMES must contain 24 entries, got {len(SMPL24_NAMES)}.")

    if len(CC_BONES) != 24:
        raise ValueError(f"CC_BONES must contain 24 entries, got {len(CC_BONES)}.")

    if ARMATURE_NAME not in bpy.data.objects:
        raise RuntimeError(f"Armature object not found: '{ARMATURE_NAME}'")

    armature = bpy.data.objects[ARMATURE_NAME]

    if armature.type != "ARMATURE":
        raise RuntimeError(
            f"Object '{ARMATURE_NAME}' is not an armature. "
            f"Current object type: {armature.type}"
        )

    return armature


def is_target_camera(obj):
    """Return True if the object is a camera selected for export."""
    if obj.type != "CAMERA":
        return False

    if CAMERA_PREFIXES is None:
        return True

    return any(obj.name.startswith(prefix) for prefix in CAMERA_PREFIXES)


def get_target_cameras():
    """Return all target cameras sorted by name."""
    cameras = [obj for obj in bpy.data.objects if is_target_camera(obj)]
    cameras = sorted(cameras, key=lambda obj: obj.name)

    if not cameras:
        raise RuntimeError(
            "No target cameras found. Please check CAMERA_PREFIXES or camera names."
        )

    return cameras


def extract_joint_position_blender_world(armature, pose_bone):
    """
    Extract one joint position in Blender world coordinates.

    This preserves the original extraction style:
        bone_mat_world = armature.matrix_world @ pose_bone.matrix
        joint_world_b  = bone_mat_world @ Vector((0, 0, 0))
    """
    bone_mat_world = armature.matrix_world @ pose_bone.matrix
    joint_world_b = bone_mat_world @ Vector((0.0, 0.0, 0.0))
    return joint_world_b


def blender_camera_to_opencv_camera(point_cam_b):
    """
    Convert a point from Blender camera coordinates to OpenCV camera coordinates.

    Blender camera coordinate:
        +X right, +Y up, -Z forward

    OpenCV camera coordinate:
        +X right, +Y down, +Z forward
    """
    return Vector((
        point_cam_b.x,
        -point_cam_b.y,
        -point_cam_b.z,
    ))


def blender_world_to_opencv_camera(point_world_b, camera):
    """
    Convert a point from Blender world coordinates to OpenCV camera coordinates
    for a given camera.
    """
    world_to_camera_b = camera.matrix_world.inverted()
    point_cam_b = world_to_camera_b @ point_world_b
    point_cam_cv = blender_camera_to_opencv_camera(point_cam_b)
    return point_cam_cv


def export_camera_joint_csv_files():
    """
    Export frame-wise SMPL-24-format 3D joints to one CSV file per camera.
    """
    scene = bpy.context.scene
    armature = validate_armature()
    cameras = get_target_cameras()

    frame_start, frame_end = get_scene_frame_range(scene)
    fps = get_scene_fps(scene)
    total_frames = frame_end - frame_start + 1

    output_folder = Path(OUTPUT_FOLDER)
    output_folder.mkdir(parents=True, exist_ok=True)

    header = [
        "frame",
        "time",
        "joint id",
        "joint name",
        "X (m)",
        "Y (m)",
        "Z (m)",
    ]

    missing_bones = set()
    expected_rows_per_camera = total_frames * 24

    print("=" * 70)
    print("Export SMPL-24-format joints in each camera coordinate system")
    print(f"Armature: {ARMATURE_NAME}")
    print(f"Frame range: {frame_start} -> {frame_end} ({total_frames} frames)")
    print(f"FPS: {fps}")
    print(f"Number of cameras: {len(cameras)}")
    print(f"Output folder: {output_folder}")
    print("Camera convention: OpenCV, +X right, +Y down, +Z forward")
    print("=" * 70)

    for camera in cameras:
        rows = []
        print(f"Processing camera: {camera.name}")

        for frame in range(frame_start, frame_end + 1):
            scene.frame_set(frame)
            bpy.context.view_layer.update()

            frame_index = frame - frame_start
            time_value = frame_index / fps if USE_RELATIVE_TIME else frame / fps

            for joint_id, (joint_name, bone_name) in enumerate(zip(SMPL24_NAMES, CC_BONES)):
                if bone_name not in armature.pose.bones:
                    if bone_name not in missing_bones:
                        print(f"Missing pose bone '{bone_name}'. This joint will be skipped.")
                        missing_bones.add(bone_name)
                    continue

                pose_bone = armature.pose.bones[bone_name]

                joint_world_b = extract_joint_position_blender_world(armature, pose_bone)
                joint_camera_cv = blender_world_to_opencv_camera(joint_world_b, camera)

                rows.append([
                    int(frame_index),
                    float(time_value),
                    int(joint_id),
                    joint_name,
                    float(joint_camera_cv.x),
                    float(joint_camera_cv.y),
                    float(joint_camera_cv.z),
                ])

        output_name = f"{safe_filename(camera.name)}_joint_file.csv"
        output_path = output_folder / output_name

        with output_path.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.writer(fp)
            writer.writerow(header)
            writer.writerows(rows)

        print(f"Saved: {output_path}")
        print(f"Rows:  {len(rows)} / expected {expected_rows_per_camera}")

    print("=" * 70)
    print("Export finished")
    print(f"Output folder: {output_folder}")

    if missing_bones:
        print("Missing bones:")
        for bone_name in sorted(missing_bones):
            print(f"  - {bone_name}")

    print("=" * 70)


# =============================================================================
# Run script
# =============================================================================

if __name__ == "__main__":
    export_camera_joint_csv_files()
