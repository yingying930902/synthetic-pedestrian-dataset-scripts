"""
export_smpl24_joints_world_coordinates.py

Export frame-wise SMPL-24-format 3D body-joint coordinates from a Blender
armature animation to a CSV file in a predefined dataset world coordinate system.

This script is intended to be run inside Blender's Python environment.

Output CSV columns:
    frame, time, joint id, joint name, X (m), Y (m), Z (m)

Coordinate system:
    The script first extracts joint positions in Blender world coordinates, then
    converts them to the dataset/user world coordinate system.

    Dataset/user world definition:
        x_user =  x_blender
        y_user =  z_blender
        z_user = -y_blender

    Dataset/user world origin in Blender world coordinates:
        ORIGIN_B = (0, 2, 0)

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
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


# =============================================================================
# User settings
# =============================================================================

# Name of the armature object in Blender.
# Change this if your armature has a different name.
ARMATURE_NAME = "CC_neutral_without_marker"

# Output CSV path.
# "//" means the folder where the current .blend file is saved.
OUTPUT_CSV = bpy.path.abspath("//smpl24_joints_world_coordinates.csv")

# Use relative time starting from 0 at the first exported frame.
# If False, time is calculated as frame / fps.
USE_RELATIVE_TIME = True

# Dataset/user-world origin expressed in Blender world coordinates.
ORIGIN_B = Vector((0.0, 2.0, 0.0))

# Blender world -> dataset/user world coordinate conversion.
# x_user =  x_blender
# y_user =  z_blender
# z_user = -y_blender
BLENDER_TO_USER_WORLD = Matrix((
    (1.0,  0.0, 0.0),
    (0.0,  0.0, 1.0),
    (0.0, -1.0, 0.0),
))


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


def validate_inputs():
    """Validate armature name and joint mapping."""
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


def blender_world_to_user_world(point_b):
    """Convert a point from Blender world coordinates to dataset/user world coordinates."""
    return BLENDER_TO_USER_WORLD @ (point_b - ORIGIN_B)


def export_world_joint_csv():
    """Export frame-wise SMPL-24-format 3D joints to CSV in dataset/user world coordinates."""
    scene = bpy.context.scene
    armature = validate_inputs()

    frame_start, frame_end = get_scene_frame_range(scene)
    fps = get_scene_fps(scene)
    total_frames = frame_end - frame_start + 1

    output_path = Path(OUTPUT_CSV)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    header = [
        "frame",
        "time",
        "joint id",
        "joint name",
        "X (m)",
        "Y (m)",
        "Z (m)",
    ]

    rows = []
    missing_bones = set()

    print("=" * 70)
    print("Export SMPL-24-format joints in dataset/user world coordinates")
    print(f"Armature: {ARMATURE_NAME}")
    print(f"Frame range: {frame_start} -> {frame_end} ({total_frames} frames)")
    print(f"FPS: {fps}")
    print(f"Output CSV: {output_path}")
    print("Coordinate system: x_user=x_blender, y_user=z_blender, z_user=-y_blender")
    print("=" * 70)

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
            joint_world_u = blender_world_to_user_world(joint_world_b)

            rows.append([
                int(frame_index),
                float(time_value),
                int(joint_id),
                joint_name,
                float(joint_world_u.x),
                float(joint_world_u.y),
                float(joint_world_u.z),
            ])

    with output_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(header)
        writer.writerows(rows)

    expected_rows = total_frames * 24

    print("=" * 70)
    print("Export finished")
    print(f"Expected rows: {expected_rows}")
    print(f"Actual rows:   {len(rows)}")
    print(f"Saved to:      {output_path}")

    if missing_bones:
        print("Missing bones:")
        for bone_name in sorted(missing_bones):
            print(f"  - {bone_name}")

    print("=" * 70)


# =============================================================================
# Run script
# =============================================================================

if __name__ == "__main__":
    export_world_joint_csv()
