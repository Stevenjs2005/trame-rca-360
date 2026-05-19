"""
render360.py — Rendering module for 360 equirectangular images using barney/ANARI.

Owns the barney device as a module-level singleton so it persists across frames.
Other modules can call get_device() to build worlds using the same device instance.
"""

import os
import glob
import numpy as np
from PIL import Image
import pynari as anari

# ---------------------------------------------------------------------------
# Module-level device singleton
# ---------------------------------------------------------------------------
_device = None

def get_device():
    """
    Returns the shared barney ANARI device, creating it if necessary.
    Call this from other modules to build worlds with the same device instance.
    """
    global _device
    if _device is None:
        _device = anari.newDevice("barney", "default")
        if anari.has_cuda_capable_gpu():
            print("[pynari] CUDA GPU detected — full quality")
        else:
            print("[pynari] No CUDA GPU — running on CPU")
    return _device


# ---------------------------------------------------------------------------
# Material helpers
# ---------------------------------------------------------------------------
def make_matte(device, r: float, g: float, b: float):
    mat = device.newMaterial('matte')
    mat.setParameter('color', anari.float3, (r, g, b))
    mat.commitParameters()
    return mat


def make_metal(device, r: float, g: float, b: float, roughness: float = 0.1):
    mat = device.newMaterial('physicallyBased')
    mat.setParameter('baseColor', anari.float3, (r, g, b))
    mat.setParameter('metallic',  anari.FLOAT32, 1.0)
    mat.setParameter('roughness', anari.FLOAT32, roughness)
    mat.commitParameters()
    return mat


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def add_sphere(device, pos: tuple, radius: float, mat):
    geom = device.newGeometry('sphere')
    geom.setParameter('vertex.position', anari.ARRAY1D,
                      device.newArray1D(anari.FLOAT32_VEC3,
                                        np.array([pos], dtype=np.float32)))
    geom.setParameter('radius', anari.FLOAT32, radius)
    geom.commitParameters()

    surf = device.newSurface()
    surf.setParameter('geometry', anari.GEOMETRY, geom)
    surf.setParameter('material', anari.MATERIAL, mat)
    surf.commitParameters()
    return surf


def add_point_cloud(device, positions: np.ndarray, radius: float, mat):
    """Render a point cloud as uniformly coloured spheres."""
    positions = positions.astype(np.float32)
    geom = device.newGeometry('sphere')
    geom.setParameter('vertex.position', anari.ARRAY1D,
                      device.newArray1D(anari.FLOAT32_VEC3, positions))
    geom.setParameter('radius', anari.FLOAT32, radius)
    geom.commitParameters()

    surf = device.newSurface()
    surf.setParameter('geometry', anari.GEOMETRY, geom)
    surf.setParameter('material', anari.MATERIAL, mat)
    surf.commitParameters()
    return surf


def add_point_cloud_colored(device, positions: np.ndarray,
                             colors: np.ndarray, radius: float):
    """Render a point cloud with per-point RGB colors."""
    positions = positions.astype(np.float32)
    colors    = colors.astype(np.float32)

    geom = device.newGeometry('sphere')
    geom.setParameter('vertex.position', anari.ARRAY1D,
                      device.newArray1D(anari.FLOAT32_VEC3, positions))
    geom.setParameter('vertex.color', anari.ARRAY1D,
                      device.newArray1D(anari.FLOAT32_VEC3, colors))
    geom.setParameter('radius', anari.FLOAT32, radius)
    geom.commitParameters()

    mat = device.newMaterial('matte')
    mat.setParameter('color', anari.STRING, 'color')
    mat.commitParameters()

    surf = device.newSurface()
    surf.setParameter('geometry', anari.GEOMETRY, geom)
    surf.setParameter('material', anari.MATERIAL, mat)
    surf.commitParameters()
    return surf


# ---------------------------------------------------------------------------
# Built-in test scene builders
# ---------------------------------------------------------------------------
def build_scene_cardinals(device):
    """Six coloured spheres in cardinal directions — useful for testing 360 coverage."""
    r = 12.0
    surfaces = [
        add_sphere(device, ( r,  0,  0), 1.5, make_matte(device, 0.9, 0.2, 0.2)),  # right  — red
        add_sphere(device, (-r,  0,  0), 1.5, make_matte(device, 0.2, 0.5, 0.9)),  # left   — blue
        add_sphere(device, ( 0,  0,  r), 0.3, make_matte(device, 0.2, 0.8, 0.3)),  # front  — green
        add_sphere(device, ( 0,  0, -r), 2.0, make_matte(device, 0.9, 0.7, 0.1)),  # back   — yellow
        add_sphere(device, ( 0,  r,  0), 1.5, make_metal(device, 0.9, 0.9, 0.9)),  # up     — silver
        add_sphere(device, ( 0, -r,  0), 1.5, make_metal(device, 0.8, 0.6, 0.1)),  # down   — gold
    ]
    world = device.newWorld()
    world.setParameterArray1D('surface', anari.SURFACE, surfaces)
    world.commitParameters()
    return world


# ---------------------------------------------------------------------------
# Point cloud loading
# ---------------------------------------------------------------------------
def load_point_cloud(file_path: str, subsample: int = 1) -> tuple[np.ndarray, np.ndarray | None]:
    """
    Load a single .las/.laz or text point cloud file.

    Returns raw UTM coordinates (not yet centered or scaled) so that
    load_point_cloud_tiles can center the full merged cloud correctly in
    float64 before any axis remapping or scaling is applied.

    @param file_path  - path to .las, .laz, .csv, .txt, or .xyz file
    @param subsample  - take every Nth point (1 = all points)
    @returns          - (positions [N,3] float64, colors [N,3] float32 or None)
                        positions are raw [x_easting, y_northing, z_elevation]
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext in ('.las', '.laz'):
        try:
            import laspy
        except ImportError:
            raise ImportError("Install laspy: pip install laspy[lazrs]")

        las = laspy.read(file_path)

        # Store as raw [easting, northing, elevation] in float64.
        # Axis remapping to ANARI space happens after centering in
        # load_point_cloud_tiles to avoid float32 precision loss on UTM coords.
        positions = np.stack([
            np.array(las.x, dtype=np.float64),
            np.array(las.y, dtype=np.float64),
            np.array(las.z, dtype=np.float64),
        ], axis=1)

        colors = None
        if hasattr(las, 'red') and hasattr(las, 'green') and hasattr(las, 'blue'):
            r = np.array(las.red,   dtype=np.float32)
            g = np.array(las.green, dtype=np.float32)
            b = np.array(las.blue,  dtype=np.float32)
            # LAS colors are 16-bit (0–65535); normalize to [0, 1]
            max_val = 65535.0 if r.max() > 255 else 255.0
            colors = np.stack([r / max_val, g / max_val, b / max_val],
                              axis=1).astype(np.float32)

    elif ext in ('.csv', '.txt', '.xyz'):
        data = np.loadtxt(file_path, delimiter=',', dtype=np.float64)
        positions = data[:, :3]
        colors = None
        if data.shape[1] >= 6:
            colors = data[:, 3:6].astype(np.float32)
            if colors.max() > 1.0:
                colors /= 255.0
    else:
        raise ValueError(f"Unsupported point cloud format: {ext}")

    if subsample > 1:
        positions = positions[::subsample]
        if colors is not None:
            colors = colors[::subsample]

    return positions.astype(np.float32), colors


def load_point_cloud_tiles(folder_path: str, pattern: str = "*.las",
                           subsample: int = 1) -> tuple[np.ndarray, np.ndarray | None]:
    """
    Load and merge all point cloud tiles from a folder into a single cloud.

    Processing order:
      1. Load all tiles as raw float64 UTM coordinates
      2. Center using the spatial midpoint (immune to uneven tile point density)
      3. Remap axes: LAS [easting, northing, elevation] → ANARI [X, Y(up), Z]
      4. Scale uniformly so the horizontal extent = 40 scene units

    @param folder_path  - folder containing point cloud tile files
    @param pattern      - glob pattern (default: *.las)
    @param subsample    - take every Nth point per tile (1 = all points)
    @returns            - (positions [N,3] float32, colors [N,3] float32 or None)
                          positions are centered at origin, scaled to ~40 units wide
    """
    files = sorted(glob.glob(os.path.join(folder_path, pattern)))
    if not files:
        raise FileNotFoundError(
            f"No files matching '{pattern}' found in {folder_path}")

    print(f"[pointcloud] Found {len(files)} tile(s) in {folder_path}")

    all_positions = []
    all_colors    = []
    has_colors    = True

    for i, f in enumerate(files):
        positions, colors = load_point_cloud(f, subsample=subsample)
        all_positions.append(positions)
        if colors is not None and has_colors:
            all_colors.append(colors)
        else:
            has_colors = False
        print(f"[pointcloud]   tile {i+1}/{len(files)}: {len(positions):,} points")

    # Merge in float64 to preserve precision with large UTM coordinates
    positions = np.concatenate(all_positions, axis=0).astype(np.float64)
    colors    = np.concatenate(all_colors, axis=0) if has_colors and all_colors else None

    print(f"[pointcloud] Total: {len(positions):,} points across {len(files)} tiles")

    # Step 1: center using spatial midpoint in float64.
    # Using midpoint rather than mean avoids skew from unevenly dense tiles.
    centroid = np.array([
        (positions[:, 0].max() + positions[:, 0].min()) / 2,  # easting
        (positions[:, 1].max() + positions[:, 1].min()) / 2,  # northing
        (positions[:, 2].max() + positions[:, 2].min()) / 2,  # elevation
    ])
    positions -= centroid
    print(f"[pointcloud] Centered (midpoint was {centroid})")

    # Step 2: remap axes for ANARI coordinate system
    # LAS:   x=easting,  y=northing, z=elevation
    # ANARI: x=right,    y=up,       z=depth
    positions = np.stack([
        positions[:, 0],   # easting   → ANARI X
        positions[:, 2],   # elevation → ANARI Y (up)
        positions[:, 1],   # northing  → ANARI Z
    ], axis=1).astype(np.float32)

    # Step 3: uniform scale so horizontal extent = 40 scene units
    xz_extent = max(
        positions[:, 0].max() - positions[:, 0].min(),
        positions[:, 2].max() - positions[:, 2].min(),
    )
    if xz_extent > 0:
        xz_scale = 40.0 / xz_extent
        positions *= xz_scale
        print(f"[pointcloud] Scaled by {xz_scale:.6f} (scene width = 40 units)")
        print(f"[pointcloud] Final extents — "
              f"X: {positions[:,0].min():.2f}→{positions[:,0].max():.2f}, "
              f"Y: {positions[:,1].min():.2f}→{positions[:,1].max():.2f}, "
              f"Z: {positions[:,2].min():.2f}→{positions[:,2].max():.2f}")

    return positions, colors


# ---------------------------------------------------------------------------
# Point cloud scene builder
# ---------------------------------------------------------------------------
def build_point_cloud_scene(device, positions: np.ndarray,
                             colors: np.ndarray | None = None,
                             radius: float = 0.015) -> tuple:
    """
    Build an ANARI world from a merged point cloud.

    Places the camera at the vertical midpoint of the cloud so terrain
    fills both the upper and lower hemispheres of the 360 view.

    @param device     - ANARI device
    @param positions  - [N,3] float32, already centered and scaled
    @param colors     - [N,3] float32 in [0,1], or None for grey
    @param radius     - sphere radius per point in scene units (default 0.015)
    @returns          - (world, camera_y) — pass camera_y into render()
    """
    print(f"[pointcloud] Building scene: {len(positions):,} points, radius={radius}")

    if colors is not None:
        surf = add_point_cloud_colored(device, positions, colors, radius)
    else:
        surf = add_point_cloud(device, positions, radius,
                               make_matte(device, 0.8, 0.8, 0.8))

    ambient = device.newLight('ambient')
    ambient.setParameter('irradiance', anari.FLOAT32, 2.0)
    ambient.commitParameters()

    world = device.newWorld()
    world.setParameterArray1D('surface', anari.SURFACE, [surf])
    world.setParameterArray1D('light',   anari.LIGHT,   [ambient])
    world.commitParameters()

    # Camera at vertical midpoint so terrain fills both hemispheres
    camera_y = float((positions[:, 1].max() + positions[:, 1].min()) / 2)
    print(f"[pointcloud] Camera Y = {camera_y:.3f} "
          f"(cloud Y: {positions[:,1].min():.2f} → {positions[:,1].max():.2f})")
    print("[pointcloud] Scene ready")

    return world, camera_y


# ---------------------------------------------------------------------------
# Internal single-eye render
# ---------------------------------------------------------------------------
def _render_eye(device, world, width: int, height: int,
                samples_per_pixel: int, eye_offset_x: float,
                camera_y: float = 0.0) -> np.ndarray:
    """
    Renders one eye of a stereo pair.

    @param eye_offset_x  - signed half-IPD: negative = left, positive = right
    @param camera_y      - vertical camera position in scene units
    @returns             - RGBA pixel array, shape (height, width, 4)
    """
    camera = device.newCamera('omnidirectional')
    camera.setParameter('position',  anari.float3, (eye_offset_x, camera_y, 0.0))
    camera.setParameter('up',        anari.float3, (0.0, 1.0, 0.0))
    camera.setParameter('direction', anari.float3, (0.0, 0.0, -1.0))
    camera.setParameter('layout',    anari.STRING, 'equirectangular')
    camera.commitParameters()

    renderer = device.newRenderer('default')
    renderer.setParameter('pixelSamples', anari.INT32, samples_per_pixel)
    renderer.commitParameters()

    frame = device.newFrame()
    frame.setParameter('size',          anari.uint2,     [width, height])
    frame.setParameter('channel.color', anari.DATA_TYPE, anari.UFIXED8_RGBA_SRGB)
    frame.setParameter('renderer',      anari.RENDERER,  renderer)
    frame.setParameter('camera',        anari.CAMERA,    camera)
    frame.setParameter('world',         anari.WORLD,     world)
    frame.commitParameters()

    frame.render()
    pixels = np.array(frame.get('channel.color'))

    del frame, renderer, camera
    return pixels


# ---------------------------------------------------------------------------
# Render function
# ---------------------------------------------------------------------------
def render(width: int, height: int, samples_per_pixel: int,
           output_path: str | None = None,
           world=None,
           camera_y: float = 0.0,
           stereo: bool = False,
           interpupillary_distance: float = 0.064) -> np.ndarray:
    """
    Renders a 360 equirectangular image (mono or stereo) using the shared
    barney device.

    Stereo output is top-bottom (left eye on top, right eye on bottom),
    matching Babylon.js PhotoDome.MODE_TOPBOTTOM. Output is width × (height×2).

    In Babylon.js:
        const dome = new BABYLON.PhotoDome("dome", "output.png", {}, scene);
        dome.imageMode = BABYLON.PhotoDome.MODE_TOPBOTTOM;

    @param width                   - image width in pixels
    @param height                  - per-eye height (stereo output = height*2 tall)
    @param samples_per_pixel       - ray samples per pixel
    @param output_path             - optional PNG save path
    @param world                   - ANARI world; defaults to cardinal test scene
    @param camera_y                - vertical camera position (from build_point_cloud_scene)
    @param stereo                  - True = top-bottom stereo pair, False = mono
    @param interpupillary_distance - eye separation in scene units (default 0.064)
    @returns                       - RGBA array (height, width, 4) or (height*2, width, 4)
    """
    device = get_device()

    if world is None:
        world = build_scene_cardinals(device)

    if not stereo:
        pixels = _render_eye(device, world, width, height,
                             samples_per_pixel, eye_offset_x=0.0, camera_y=camera_y)
        del world
        if output_path:
            Image.fromarray(pixels, mode="RGBA").convert("RGB").save(output_path)
            print(f"[pynari] Saved → {output_path}")
        return pixels

    half_ipd = interpupillary_distance / 2.0

    print("[pynari] Rendering left eye …")
    left  = _render_eye(device, world, width, height, samples_per_pixel,
                        eye_offset_x=-half_ipd, camera_y=camera_y)

    print("[pynari] Rendering right eye …")
    right = _render_eye(device, world, width, height, samples_per_pixel,
                        eye_offset_x=+half_ipd, camera_y=camera_y)

    del world

    # Left eye on top, right eye on bottom — Babylon.js MODE_TOPBOTTOM convention
    stereo_pixels = np.concatenate([left, right], axis=0)

    if output_path:
        Image.fromarray(stereo_pixels, mode="RGBA").convert("RGB").save(output_path)
        print(f"[pynari] Saved stereo top-bottom → {output_path}")

    return stereo_pixels


# ---------------------------------------------------------------------------
# Convenience: render a point cloud folder in one call
# ---------------------------------------------------------------------------
def render_point_cloud(
    las_folder: str,
    output_path: str,
    width: int                     = 4096,
    height: int                    = 2048,
    samples_per_pixel: int         = 16,
    subsample: int                 = 1,
    point_radius: float            = 0.015,
    stereo: bool                   = True,
    interpupillary_distance: float = 0.064,
) -> None:
    """
    One-shot function: load all .las tiles from a folder and render a
    360 stereo equirectangular image ready for Babylon.js PhotoDome.

    Example:
        from render360 import render_point_cloud
        render_point_cloud(
            las_folder  = "ForTommyAndSteven/PointCloud/spc",
            output_path = "output_stereo.png",
        )

    @param las_folder              - folder containing .las tile files
    @param output_path             - path to save the output PNG
    @param width                   - image width in pixels (default 4096)
    @param height                  - per-eye height in pixels (default 2048)
    @param samples_per_pixel       - ray samples per pixel (default 16)
    @param subsample               - take every Nth point; 1 = full cloud (default 1)
    @param point_radius            - sphere radius per point in scene units (default 0.015)
    @param stereo                  - True = stereo pair, False = mono (default True)
    @param interpupillary_distance - eye separation in scene units (default 0.064)
    """
    device = get_device()

    print(f"[render_point_cloud] Loading tiles from: {las_folder}")
    positions, colors = load_point_cloud_tiles(
        las_folder, pattern="*.las", subsample=subsample)

    world, camera_y = build_point_cloud_scene(
        device, positions, colors, radius=point_radius)

    render(
        width=width,
        height=height,
        samples_per_pixel=samples_per_pixel,
        output_path=output_path,
        world=world,
        camera_y=camera_y,
        stereo=stereo,
        interpupillary_distance=interpupillary_distance,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    render_point_cloud(
        las_folder  = "ForTommyAndSteven/PointCloud/spc",
        output_path = "/home/schm8173/dev/trame-rca-360/trame-rca-360/public/output.png",
    )