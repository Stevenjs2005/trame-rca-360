"""
render360.py — Rendering module for 360 equirectangular images using barney/ANARI.

Owns the barney device as a module-level singleton so it persists across frames.
Other modules can call get_device() to build worlds using the same device instance.
"""

import ctypes
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


# ---------------------------------------------------------------------------
# Built-in scene builders
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


def build_random_scene(device):
    """Random coloured spheres scattered around the origin."""
    surfaces = []
    num_spheres = np.random.randint(5, 10)
    for _ in range(num_spheres):
        color    = np.random.random(3)
        signs    = np.random.choice([-1, 1], size=3)
        position = (color * signs * 8.0).tolist()
        surfaces.append(add_sphere(device, position, 1.5,
                                   make_matte(device, float(color[0]),
                                              float(color[1]), float(color[2]))))
    world = device.newWorld()
    world.setParameterArray1D('surface', anari.SURFACE, surfaces)
    world.commitParameters()
    return world




# ---------------------------------------------------------------------------
# Internal single-eye render
# ---------------------------------------------------------------------------
def _render_eye(device, world, width: int, height: int, samples_per_pixel: int, eye_offset_x: float) -> np.ndarray:
    """
    Renders one eye of a stereo pair.

    The omnidirectional camera is placed at (eye_offset_x, 0, 0) so that
    left/right eyes experience natural stereo parallax across the full
    equirectangular projection.

    @param eye_offset_x  - signed half-IPD: negative = left eye, positive = right eye
    @returns             - RGBA pixel array of shape (height, width, 4)
    """
    camera = device.newCamera('omnidirectional')
    camera.setParameter('position',  anari.float3, (eye_offset_x, 0.0, 0.0))
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

    del frame
    del renderer
    del camera

    return pixels


# ---------------------------------------------------------------------------
# Render function
# ---------------------------------------------------------------------------
def render(width: int, height: int, samples_per_pixel: int,
           output_path: str | None = None,
           world=None,
           stereo: bool = False,
           interpupillary_distance: float = 0.064) -> np.ndarray:
    """
    Renders a 360 equirectangular image (mono or stereo) using the shared
    barney device.

    Stereo output is top-bottom (left eye on top, right eye on bottom),
    which is the format expected by Babylon.js PhotoDome.MODE_TOPBOTTOM.
    The output image will be width x (height * 2) pixels.

    In Babylon.js, load the result with:
        const dome = new BABYLON.PhotoDome("dome", "output.png", {}, scene);
        dome.imageMode = BABYLON.PhotoDome.MODE_TOPBOTTOM;

    @param width                   - image width in pixels
    @param height                  - per-eye height (stereo output is height*2 tall;
                                     use width//2 for a standard equirectangular ratio)
    @param samples_per_pixel       - number of paths traced per pixel
    @param output_path             - optional path to save PNG output
    @param world                   - ANARI world object; defaults to cardinal scene
    @param stereo                  - if True, render a top-bottom stereo pair
    @param interpupillary_distance - eye separation in scene units (default 0.064 m)
    @returns                       - RGBA pixel array, shape (height, width, 4) mono
                                     or (height*2, width, 4) stereo
    """
    device = get_device()

    if world is None:
        world = build_scene_cardinals(device)

    assert world is not None

    if not stereo:
        # ---- mono path (original behaviour) --------------------------------
        pixels = _render_eye(device, world, width, height, samples_per_pixel,
                             eye_offset_x=0.0)
        del world
        if output_path is not None:
            Image.fromarray(pixels, mode="RGBA").convert("RGB").save(output_path)
            print(f"[pynari] Saved → {output_path}")
        return pixels

    # ---- stereo path -------------------------------------------------------
    half_ipd = interpupillary_distance / 2.0

    print("[pynari] Rendering left eye …")
    left  = _render_eye(device, world, width, height, samples_per_pixel,
                        eye_offset_x=-half_ipd)

    print("[pynari] Rendering right eye …")
    right = _render_eye(device, world, width, height, samples_per_pixel,
                        eye_offset_x=+half_ipd)

    del world

    # Stack top-bottom: left eye on top, right eye on bottom.
    # This matches Babylon.js PhotoDome.MODE_TOPBOTTOM convention.
    stereo_pixels = np.concatenate([left, right], axis=0)  # (height*2, width, 4)

    if output_path is not None:
        Image.fromarray(stereo_pixels, mode="RGBA").convert("RGB").save(output_path)
        print(f"[pynari] Saved stereo top-bottom → {output_path}")

    return stereo_pixels






def add_point_cloud(device, positions: np.ndarray, radius: float, mat):
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


def add_point_cloud_colored(device, positions: np.ndarray, colors: np.ndarray, radius: float):
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


def load_point_cloud(file_path: str, subsample: int = 1) -> tuple[np.ndarray, np.ndarray | None]:
    import os
    ext = os.path.splitext(file_path)[1].lower()

    if ext in ('.las', '.laz'):
        try:
            import laspy
        except ImportError:
            raise ImportError("Install laspy: pip install laspy[lazrs]")

        print(f"[pointcloud] Loading {ext} file: {file_path}")
        las = laspy.read(file_path)
        positions = np.stack([
            np.array(las.x, dtype=np.float32),
            np.array(las.z, dtype=np.float32),
            np.array(las.y, dtype=np.float32),  # removed negation
        ], axis=1)

        colors = None
        if hasattr(las, 'red') and hasattr(las, 'green') and hasattr(las, 'blue'):
            r = np.array(las.red,   dtype=np.float32)
            g = np.array(las.green, dtype=np.float32)
            b = np.array(las.blue,  dtype=np.float32)
            max_val = max(r.max(), g.max(), b.max())
            scale = 20.0 / max(
                positions[:, 0].max() - positions[:, 0].min(),
                positions[:, 1].max() - positions[:, 1].min(),
                positions[:, 2].max() - positions[:, 2].min(),
            )
            positions *= scale
            print(f"[pointcloud] Scaled by {scale:.4f} (1 unit = {1/scale:.2f} original units)")
            colors = np.stack([r / scale, g / scale, b / scale], axis=1)

    elif ext in ('.csv', '.txt', '.xyz'):
        print(f"[pointcloud] Loading text file: {file_path}")
        data = np.loadtxt(file_path, delimiter=',', dtype=np.float32)
        positions = data[:, :3]
        colors = None
        if data.shape[1] >= 6:
            colors = data[:, 3:6].astype(np.float32)
            if colors.max() > 1.0:
                colors /= 255.0
    else:
        raise ValueError(f"Unsupported format: {ext}")

    if subsample > 1:
        positions = positions[::subsample]
        if colors is not None:
            colors = colors[::subsample]
        print(f"[pointcloud] Subsampled to {len(positions):,} points")
    else:
        print(f"[pointcloud] Loaded {len(positions):,} points")

    centroid = positions.mean(axis=0)
    positions -= centroid
    print(f"[pointcloud] Centered at origin (was {centroid})")

    return positions, colors


def build_point_cloud_scene(device, positions: np.ndarray,
                             colors: np.ndarray | None = None,
                             radius: float = 0.05):
    print(f"[pointcloud] Building scene with {len(positions):,} points, radius={radius}")

    if colors is not None:
        surf = add_point_cloud_colored(device, positions, colors, radius)
    else:
        surf = add_point_cloud(device, positions, radius,
                               make_matte(device, 0.8, 0.8, 0.8))

    world = device.newWorld()
    world.setParameterArray1D('surface', anari.SURFACE, [surf])
    world.commitParameters()
    print("[pointcloud] Scene ready")
    return world