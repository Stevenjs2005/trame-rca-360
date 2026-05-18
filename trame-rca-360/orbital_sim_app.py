"""
orbital_app.py — Driver app for the orbital simulation.

Bridges render360.py (rendering) and orbital_sim.py (physics),
runs the trame server, and displays FPS benchmarking.

Run:
    /home/schm8173/dev/trame-rca-360/.venv/bin/python orbital_app.py --server
"""

import io
import base64
import time
import asyncio
import numpy as np
from PIL import Image

from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import vuetify3
from trame_rca.widgets import rca

import pynari as anari
import pynari as py
from render360 import render, get_device, add_sphere, make_matte, make_metal
from orbital_sim import r_e, r_j, t_arr, N

# ---------------------------------------------------------------------------
# Render settings
# ---------------------------------------------------------------------------
WIDTH  = 800 if not py.has_cuda_capable_gpu() else 1024
HEIGHT = WIDTH // 2
SPP    = 1

# Module-level state — plain Python variables
_running    = False
_sim_frame  = 0


# ---------------------------------------------------------------------------
# Orbital scene builder
# ---------------------------------------------------------------------------
def build_orbital_scene(earth_pos: tuple, jupiter_pos: tuple):
    device = get_device()

    ex, ez = float(earth_pos[0]),   float(earth_pos[1])
    jx, jz = float(jupiter_pos[0]), float(jupiter_pos[1])

    surfaces = [
        add_sphere(device, (0.0, 0.0, 0.0), 1.0,  make_metal(device, 1.0, 0.85, 0.1, roughness=0.15)),  # Sun
        add_sphere(device, (ex,  0.0, ez),  0.5,  make_matte(device, 0.2, 0.55, 0.9)),                   # Earth
        add_sphere(device, (jx,  0.0, jz),  0.8,  make_matte(device, 0.9, 0.35, 0.1)),                   # Super Jupiter
    ]

    world = device.newWorld()
    world.setParameterArray1D('surface', anari.SURFACE, surfaces)
    world.commitParameters()
    return world


def render_orbital_frame(frame_idx: int) -> np.ndarray:
    world = build_orbital_scene(
        earth_pos=  (float(r_e[frame_idx][0]), float(r_e[frame_idx][1])),
        jupiter_pos=(float(r_j[frame_idx][0]), float(r_j[frame_idx][1])),
    )
    pixels = render(WIDTH, HEIGHT, SPP, world=world)
    print(f"frame {frame_idx}: non-zero={np.count_nonzero(pixels[:,:,:3])} earth=({r_e[frame_idx][0]:.2f},{r_e[frame_idx][1]:.2f}) jup=({r_j[frame_idx][0]:.2f},{r_j[frame_idx][1]:.2f})")
    return pixels


def pixels_to_data_url(pixels: np.ndarray) -> str:
    img = Image.fromarray(pixels, mode='RGBA').convert('RGB')
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=75)
    b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f"data:image/jpeg;base64,{b64}"


# ---------------------------------------------------------------------------
# Trame app
# ---------------------------------------------------------------------------
def main():
    global _running, _sim_frame

    pixels   = render_orbital_frame(0)
    data_url = pixels_to_data_url(pixels)

    server = get_server()
    server.client_type = "vue3" # type: ignore
    state, ctrl = server.state, server.controller # type: ignore

    state.current_image  = data_url
    state.running        = False
    state.fps            = 0.0
    state.elapsed_years  = 0.0

    def tick():
        global _sim_frame
        t0     = time.perf_counter()
        pixels = render_orbital_frame(_sim_frame)
        dt     = time.perf_counter() - t0

        state.current_image  = pixels_to_data_url(pixels)
        state.fps            = round(1.0 / max(dt, 1e-9), 2)
        state.elapsed_years  = round(float(t_arr[_sim_frame]), 1)
        _sim_frame           = (_sim_frame + 1) % N

    async def render_loop():
        while True:
            if _running:
                tick()
                state.flush()
                await asyncio.sleep(0.01)
            else:
                await asyncio.sleep(0.05)

    @ctrl.add("on_server_ready")
    def start_loop(**kwargs):
        asyncio.ensure_future(render_loop())

    def toggle():
        global _running
        _running = not _running
        state.running = _running

    def step():
        global _running, _sim_frame
        _running = False
        state.running = False
        tick()
        state.flush()

    def reset():
        global _running, _sim_frame
        _running   = False
        _sim_frame = 0
        state.running = False
        state.elapsed_years = 0.0

    with SinglePageLayout(server) as layout:
        layout.title.set_text("Orbital Sim — 360 Barney Renderer")

        with layout.toolbar:
            vuetify3.VSpacer()
            vuetify3.VBtn(
                "{{ running ? '⏸ Pause' : '▶ Play' }}",
                click=toggle,
                color="primary",
                variant="tonal",
                classes="mx-1",
            )
            vuetify3.VBtn("Step →", click=step,  variant="tonal", classes="mx-1")
            vuetify3.VBtn("Reset",  click=reset, variant="tonal", classes="mx-1")
            vuetify3.VSpacer()
            vuetify3.VChip(
                "FPS: {{ fps }}  |  Year: {{ elapsed_years }}",
                color="secondary",
                variant="tonal",
            )
            vuetify3.VSpacer()

        with layout.content:
            rca.ImageDisplayArea360(
                static_image=("current_image",),
                style="width:100vw; height:calc(100vh - 64px);",
            )

    server.start() # type: ignore


if __name__ == "__main__":
    main()