"""
moving_sphere_test.py — Simple test: one sphere moving back and forth.

Run:
    /home/schm8173/dev/trame-rca-360/.venv/bin/python moving_sphere_test.py --server
"""

import io
import base64
import time
import asyncio
import math
import numpy as np
from PIL import Image

from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import vuetify3
from trame_rca.widgets import rca

import pynari as anari
import pynari as py
from render360 import render, get_device, add_sphere, make_matte,load_point_cloud, build_point_cloud_scene


# ---------------------------------------------------------------------------
# Render settings
# ---------------------------------------------------------------------------
WIDTH  = 800
HEIGHT = WIDTH // 2
SPP    = 32

# Module-level state — plain Python variables, not trame state
_t       = 0.0
_running = False


def build_moving_sphere_scene(t: float):
    """One red sphere oscillating left-right at z=-5."""
    device = get_device()
    x = math.sin(t) * 4.0
    surfaces = [
        add_sphere(device, (x, 0.0, -5.0), 1.0, make_matte(device, 0.9, 0.2, 0.2)),
    ]
    world = device.newWorld()
    world.setParameterArray1D('surface', anari.SURFACE, surfaces)
    world.commitParameters()
    return world


def render_frame(t: float) -> str:
    pixels = render(WIDTH, HEIGHT, SPP, world=build_moving_sphere_scene(t), stereo=True,output_path= "./public/output.png")
    img = Image.fromarray(pixels, mode='RGBA').convert('RGB')
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=75)
    b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f"data:image/jpeg;base64,{b64}"


def main():
#     global _t, _running

#     server = get_server()
#     server.client_type = "vue3"  # type: ignore
#     state, ctrl = server.state, server.controller # type: ignore

#     state.current_image = render_frame(_t)
#     state.fps           = 0.0
#     state.running       = False
    
#     async def render_loop():
#         global _t, _running
#         print("render_loop started")
#         while True:
#             print(f"loop tick: _running={_running}")
#             if _running:
#                 t0 = time.perf_counter()
#                 state.current_image = render_frame(_t)
#                 dt = time.perf_counter() - t0
#                 state.fps = round(1.0 / max(dt, 1e-9), 1)
#                 _t += 0.05
#                 state.flush()
#                 await asyncio.sleep(0.01)
#             else:
#                 await asyncio.sleep(1.0)

#     @ctrl.add("on_server_ready")
#     def start_loop(**kwargs):
#         print("SERVER READY - starting loop")
#         asyncio.ensure_future(render_loop())

#     def toggle():
#         global _running
#         _running = not _running
#         state.running = _running
#         print(f"toggle called, _running={_running}")

#     def step():
#         global _t, _running
#         _running = False
#         state.running = False
#         state.current_image = render_frame(_t)
#         _t += 0.05
#         state.flush()

#     def reset():
#         global _t, _running
#         _running = False
#         state.running = False
#         _t = 0.0
#         state.current_image = render_frame(_t)
#         state.flush()

#     with SinglePageLayout(server) as layout:
#         layout.title.set_text("Moving Sphere Test")

#         with layout.toolbar:
#             vuetify3.VSpacer()
#             vuetify3.VBtn(
#                 "{{ running ? '⏸ Pause' : '▶ Play' }}",
#                 click=toggle,
#                 color="primary",
#                 variant="tonal",
#                 classes="mx-1",
#             )
#             vuetify3.VBtn("Step →", click=step,  variant="tonal", classes="mx-1")
#             vuetify3.VBtn("Reset",  click=reset, variant="tonal", classes="mx-1")
#             vuetify3.VSpacer()
#             vuetify3.VChip(
#                 "FPS: {{ fps }}",
#                 color="secondary",
#                 variant="tonal",
#             )
#             vuetify3.VSpacer()

#         with layout.content:
#             rca.ImageDisplayArea360(
#                 static_image=("current_image",),
#                 style="width:100vw; height:calc(100vh - 64px);",
#             )

#     server.start() # type: ignore


# if __name__ == "__main__":
#     main()

    device = get_device()

    # Start with heavy subsampling — tune down once pipeline is confirmed
    positions, colors = load_point_cloud("my_data.laz", subsample=500)

    world = build_point_cloud_scene(device, positions, colors, radius=0.05)

    pixels = render(WIDTH, HEIGHT, SPP, world=world, stereo=True,
                    interpupillary_distance=0.64,output_path="/home/schm8173/dev/trame-rca-360/trame-rca-360/public/output.png")