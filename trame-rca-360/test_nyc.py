"""
test_nyc.py — Tests the NYC LiDAR point cloud rendering pipeline.
"""
from render360 import render, get_device, load_point_cloud, build_point_cloud_scene, build_scene_cardinals
import pynari as py
from PIL import Image


WIDTH  = 800 if not py.has_cuda_capable_gpu() else 2048
HEIGHT = WIDTH // 2
SPP    = 16  if not py.has_cuda_capable_gpu() else 64

device = get_device()

positions, colors = load_point_cloud(
    "/home/schm8173/dev/trame-rca-360/trame-rca-360/nyc_sample.laz",
    subsample=10
)

# Force center and scale here
positions -= positions.mean(axis=0)
scale = 20.0 / max(
    positions[:, 0].max() - positions[:, 0].min(),
    positions[:, 1].max() - positions[:, 1].min(),
    positions[:, 2].max() - positions[:, 2].min(),
)
positions *= scale

print(f"[debug] After scaling:")
print(f"[debug] X range: {positions[:, 0].min():.2f} to {positions[:, 0].max():.2f}")
print(f"[debug] Y range: {positions[:, 1].min():.2f} to {positions[:, 1].max():.2f}")
print(f"[debug] Z range: {positions[:, 2].min():.2f} to {positions[:, 2].max():.2f}")

import numpy as np
dists = np.linalg.norm(positions, axis=1)
print(f"[debug] Nearest point distance: {dists.min():.2f}")

RADIUS = 0.1
world = build_point_cloud_scene(device, positions, colors, radius=RADIUS)

pixels = render(WIDTH, HEIGHT, SPP,
                world=world,
                stereo=True,
                interpupillary_distance=0.5,
                output_path="/home/schm8173/dev/trame-rca-360/trame-rca-360/public/output.png")

print(f"Output shape: {pixels.shape}")
print(f"Rendered with radius={RADIUS}")
print(f"[debug] Pixel max value: {pixels.max()}")
print(f"[debug] Pixel min value: {pixels.min()}")