import io
import base64
import numpy as np
from PIL import Image
from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame_rca.widgets import rca
from trame.widgets import vuetify3
from render360 import render
import pynari as py

NUM_RENDERS = 5

if __name__ == "__main__":
    WIDTH  = 800 if not py.has_cuda_capable_gpu() else 2048
    HEIGHT = WIDTH // 2
    SPP    = 16  if not py.has_cuda_capable_gpu() else 64

    # Pre-render all scenes
    data_urls = []
    for i in range(NUM_RENDERS):
        print(f"[test] Rendering scene {i + 1}/{NUM_RENDERS} …")
        pixel_array = render(width=WIDTH, height=HEIGHT, samples_per_pixel=SPP, randomize=True)
        img = Image.fromarray(pixel_array, mode="RGBA").convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        data_urls.append(f"data:image/png;base64,{b64}")
    print(data_urls)
        
    # Trame app
    server = get_server()
    server.client_type = "vue3"  # type: ignore
    state = server.state # type: ignore
    state.current_index = 0
    state.current_image = data_urls[0]

    @state.change("current_index")
    def on_index_change(current_index, **kwargs):
        state.current_image = data_urls[current_index]
        print(data_urls[current_index][22:100] + "\n")

    def next_scene():
        state.current_index = (state.current_index + 1) % NUM_RENDERS  # type: ignore
    def prev_scene():
        state.current_index = (state.current_index - 1) % NUM_RENDERS # type: ignore

    with SinglePageLayout(server) as layout:
        layout.title.set_text("360 Render Test")

        with layout.toolbar:
            vuetify3.VBtn("← Prev", click=prev_scene)
            vuetify3.VBtn("Next →", click=next_scene)

        with layout.content:
            rca.ImageDisplayArea360(
                static_image=("current_image",),
                image_style={"width": "100vw", "height": "100vh"},
            )

    server.start()  # type: ignore