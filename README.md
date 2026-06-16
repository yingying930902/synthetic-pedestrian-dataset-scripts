# Blender Synthetic Pedestrian Dataset Export Scripts

This repository contains Blender Python scripts used to create a 49-camera virtual camera layout, render multi-view pedestrian videos, and export camera parameters and frame-wise 3D body-joint trajectories.

The scripts are designed for a synthetic pedestrian dataset generated in Blender. They can be used to produce:

- rendered videos from multiple virtual cameras;
- camera intrinsic parameters;
- camera extrinsic parameters;
- world-coordinate 3D body-joint trajectories;
- camera-coordinate 3D body-joint trajectories.

All scripts are intended to be run inside Blender's Python environment.

## Dataset

The corresponding dataset is available on Zenodo:

**A synthetic dataset with ground-truth 3D joint trajectories for validating joint-level pedestrian trajectory extraction**

Dataset DOI: https://doi.org/10.5281/zenodo.20710735


## Repository files

| File | Purpose |
|---|---|
| `create_49_camera_layout.py` | Creates the 49-camera layout in Blender. |
| `render_videos_from_camera_collection.py` | Renders one MP4 video from each camera in the camera collection. |
| `export_camera_intrinsic_file.py` | Exports the camera intrinsic matrix `K` and image resolution to JSON. |
| `export_camera_extrinsic_file.py` | Exports camera extrinsic parameters to JSON. |
| `export_smpl24_joints_world_coordinates.py` | Exports one CSV file containing SMPL-24-format body joints in the dataset/world coordinate system. |
| `export_smpl24_joints_camera_coordinates.py` | Exports one CSV file per camera containing SMPL-24-format body joints in the OpenCV camera coordinate system. |

## Recommended workflow

A typical workflow is:

1. Create the 49-camera layout using `create_49_camera_layout.py`.
2. Set the scene resolution, frame rate, frame range, render engine, materials, lighting, and pedestrian animation in Blender.
3. Render videos from all cameras using `render_videos_from_camera_collection.py`.
4. Export camera intrinsics using `export_camera_intrinsic_file.py`.
5. Export camera extrinsics using `export_camera_extrinsic_file.py`.
6. Export world-coordinate joint trajectories using `export_smpl24_joints_world_coordinates.py`.
7. Export camera-coordinate joint trajectories using `export_smpl24_joints_camera_coordinates.py`.

The exact order can be adjusted, but the camera layout and animation should be finalized before exporting camera parameters or joint trajectories.

## Requirements

The scripts require Blender and should be run in Blender's Scripting workspace or through Blender's Python execution interface.

Required Blender modules:

```python
bpy
mathutils
```

Required standard Python modules:

```python
csv
json
math
os
pathlib
re
```

No external Python packages are required.

## 49-camera layout

Use:

```text
create_49_camera_layout.py
```

This script creates a collection named:

```python
CAMERA_COLLECTION_NAME = "CameraArray"
```

Existing cameras inside this collection are removed before the new cameras are created. Cameras outside this collection are not affected.

### Camera layout definition

The layout contains 49 cameras:

| Camera group | Parameters | Count |
|---|---:|---:|
| Ring cameras | Radii 4.0 m and 5.0 m; heights 1.0 m, 3.0 m, and 5.0 m; angles 0°, 30°, 60°, 90°, 120°, 150°, and 180° | 42 |
| Extra side cameras | Radius 3.0 m; heights 1.0 m, 3.0 m, and 5.0 m; angle 90° | 3 |
| Top-down cameras | Heights 4.0 m, 5.0 m, 6.0 m, and 7.0 m | 4 |
| **Total** |  | **49** |

The naming convention is:

```text
Camera_R4.0m_H1.0m_000
Camera_R4.0m_H1.0m_030
...
Camera_R5.0m_H5.0m_180

ExtraCam_R3.0m_H1.0m_090
ExtraCam_R3.0m_H3.0m_090
ExtraCam_R3.0m_H5.0m_090

TopDownCam_4.00m
TopDownCam_5.00m
TopDownCam_6.00m
TopDownCam_7.00m
```

Ring cameras and ExtraCam cameras look at:

```python
LOOK_AT = Vector((0.0, 0.0, 1.0))
```

Top-down cameras look at:

```python
TOP_DOWN_LOOK_AT = Vector((0.0, 0.0, 0.0))
```

All cameras are assigned the same optical settings by default:

```python
HFOV_DEG = 92.0
SENSOR_WIDTH_MM = 36.0
```

The focal length is computed from the horizontal field of view:

```python
f = (sensor_width / 2) / tan(hfov / 2)
```

## Rendering videos from all cameras

Use:

```text
render_videos_from_camera_collection.py
```

This script renders the full animation once from each camera in `CameraArray` and saves the results as MP4/H.264 videos.

Important settings:

```python
CAMERA_COLLECTION_NAME = "CameraArray"
OUTPUT_DIR = r"C:\Blender\all_49cams"
```

The script sorts cameras by name to keep the output order stable. By default, the output files are named as:

```text
01_Camera_R4.0m_H1.0m_000.mp4
02_Camera_R4.0m_H1.0m_030.mp4
...
```

Before running this script, check the Blender scene settings, including:

- frame range;
- frame rate;
- resolution;
- render engine;
- lighting and materials;
- pedestrian animation.

## Camera intrinsics

Use:

```text
export_camera_intrinsic_file.py
```

This script exports the image resolution and camera intrinsic matrix `K` to:

```python
JSON_PATH = bpy.path.abspath("//camera_intrinsic_file.json")
```

The output JSON contains only:

```json
{
  "resolution": [3840, 2160],
  "K": [
    [fx, 0.0, cx],
    [0.0, fy, cy],
    [0.0, 0.0, 1.0]
  ]
}
```

If all cameras share the same optical settings and render resolution, one intrinsic file is sufficient. By default, the script exports intrinsics from the active scene camera:

```python
USE_SCENE_CAMERA = True
```

To export from a named camera instead, set:

```python
USE_SCENE_CAMERA = False
CAMERA_NAME = "Camera_R4.0m_H1.0m_000"
```

The intrinsic matrix follows the standard pinhole camera model. Lens distortion is not exported. If no lens distortion is applied in Blender, this corresponds to an ideal synthetic pinhole camera.

## Camera extrinsics

Use:

```text
export_camera_extrinsic_file.py
```

This script exports extrinsic parameters for all cameras in:

```python
COLLECTION_NAME = "CameraArray"
```

The output JSON path is:

```python
JSON_PATH = bpy.path.abspath("//camera_extrinsic_file.json")
```

For each camera, the output fields are:

```text
camera_name
Rwc
Twc
Rcw
Tcw
T_wc_4x4
T_cw_4x4
```

Definitions:

```text
P_world  = Rwc @ P_camera + Twc
P_camera = Rcw @ P_world + Tcw
```

where:

- `P_world` is a 3D point in the dataset/world coordinate system;
- `P_camera` is a 3D point in the OpenCV camera coordinate system;
- `Rwc`, `Twc` represent camera-to-world transformation;
- `Rcw`, `Tcw` represent world-to-camera transformation.

The homogeneous transformations are:

```text
[P_world,  1]^T = T_wc_4x4 @ [P_camera, 1]^T
[P_camera, 1]^T = T_cw_4x4 @ [P_world,  1]^T
```

## Dataset/world coordinate system

The dataset/world coordinate system is converted from Blender world coordinates as:

```text
x_user =  x_blender
y_user =  z_blender
z_user = -y_blender
```

The dataset/world origin is defined in Blender world coordinates as:

```python
ORIGIN_B = Vector((0.0, 2.0, 0.0))
```

The transformation used in the world-coordinate joint export is:

```python
joint_world_u = BLENDER_TO_USER_WORLD @ (joint_world_b - ORIGIN_B)
```

The camera extrinsic export uses the same dataset/world coordinate definition.

## OpenCV camera coordinate system

Camera-coordinate outputs use the OpenCV camera coordinate convention:

```text
+X right
+Y down
+Z forward
```

Blender camera local coordinates are:

```text
+X right
+Y up
-Z forward
```

The conversion from Blender camera local coordinates to OpenCV camera coordinates is:

```python
x_cv =  x_blender_camera
y_cv = -y_blender_camera
z_cv = -z_blender_camera
```

## World-coordinate joint export

Use:

```text
export_smpl24_joints_world_coordinates.py
```

This script exports one CSV file:

```python
OUTPUT_CSV = bpy.path.abspath("//smpl24_joints_world_coordinates.csv")
```

Important setting:

```python
ARMATURE_NAME = "CC_neutral_without_marker"
```

Change `ARMATURE_NAME` to match the actual armature object name in the Blender scene.

## Camera-coordinate joint export

Use:

```text
export_smpl24_joints_camera_coordinates.py
```

This script exports one CSV file per camera to:

```python
OUTPUT_FOLDER = bpy.path.abspath("//camera_coordinate_joint_files")
```

Each output file is named as:

```text
<camera_name>_joint_file.csv
```

By default, the script exports cameras whose names start with:

```python
CAMERA_PREFIXES = ["Camera_", "ExtraCam_", "TopDownCam_"]
```

To export all camera objects in the scene, set:

```python
CAMERA_PREFIXES = None
```

## Joint definition

The joint trajectory scripts export 24 body joints following the SMPL-24 joint order:

```text
0  pelvis
1  left_hip
2  right_hip
3  spine1
4  left_knee
5  right_knee
6  spine2
7  left_ankle
8  right_ankle
9  spine3
10 left_foot
11 right_foot
12 neck
13 left_collar
14 right_collar
15 head
16 left_shoulder
17 right_shoulder
18 left_elbow
19 right_elbow
20 left_wrist
21 right_wrist
22 left_hand
23 right_hand
```

The joint positions are extracted from the Character Creator armature using a predefined bone-to-joint mapping. Therefore, the exported joints are SMPL-24-format joints derived from the Character Creator skeleton, rather than joints computed directly from an SMPL mesh joint regressor.

The extraction method is:

```python
bone_mat_world = armature.matrix_world @ pose_bone.matrix
joint_world_b = bone_mat_world @ Vector((0.0, 0.0, 0.0))
```

This means that each joint position is taken from the local origin of the corresponding pose bone transformed into Blender world coordinates.

## Output CSV format for joint trajectories

The world-coordinate and camera-coordinate joint scripts use the same CSV structure:

| Column | Description |
|---|---|
| `frame` | Zero-based frame index. |
| `time` | Time in seconds. By default, this starts from 0 at the first exported frame. |
| `joint id` | SMPL-24 joint index. |
| `joint name` | SMPL-24 joint name. |
| `X (m)` | X coordinate in metres. |
| `Y (m)` | Y coordinate in metres. |
| `Z (m)` | Z coordinate in metres. |

Example:

```csv
frame,time,joint id,joint name,X (m),Y (m),Z (m)
0,0.0,0,pelvis,0.0000,0.9500,0.1200
0,0.0,1,left_hip,-0.0800,0.9100,0.1000
```

Each CSV should contain:

```text
number of frames × 24
```

data rows, excluding the header.

## Consistency between world joints, camera joints, and extrinsics

The world-coordinate joint files, camera-coordinate joint files, and camera extrinsic file are intended to be geometrically consistent.

For a joint point exported in the dataset/world coordinate system, the corresponding camera-coordinate point should satisfy:

```text
P_camera = Rcw @ P_world + Tcw
```

or:

```text
[P_camera, 1]^T = T_cw_4x4 @ [P_world, 1]^T
```

Small numerical differences may occur because of floating-point precision.

## How to run the scripts in Blender

1. Open the `.blend` file containing the animated armature and scene.
2. Open the **Scripting** workspace in Blender.
3. Load one script at a time.
4. Check the user settings at the top of the script.
5. Run the script.
6. Check the Blender console for printed information and output paths.

Important settings to check include:

```python
CAMERA_COLLECTION_NAME = "CameraArray"
COLLECTION_NAME = "CameraArray"
ARMATURE_NAME = "CC_neutral_without_marker"
OUTPUT_DIR = r"C:\Blender\all_49cams"
```
