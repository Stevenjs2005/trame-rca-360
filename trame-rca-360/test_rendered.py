import io
import base64
import numpy as np
from PIL import Image
from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame_rca.widgets import rca
from render360 import render
import pynari as py
if __name__ == "__main__":
    # Adjust width/height and spp as needed.
    # Lower spp renders faster; increase for quality.
    WIDTH  = 800 if not py.has_cuda_capable_gpu() else 2048
    HEIGHT = WIDTH // 2
    SPP    = 16   if not py.has_cuda_capable_gpu() else 64
    pixel_array = render(width=WIDTH, height=HEIGHT, samples_per_pixel=SPP, output_path="public/output.png", randomize = False)
 
    #converting pixel array to png
    img = Image.fromarray(pixel_array, mode="RGBA").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    data_url = f"data:image/png;base64,{b64}"
  
    server = get_server()
    server.client_type = "vue3"  # type: ignore
 
    with SinglePageLayout(server) as layout:
        layout.title.set_text("360 Render Test")
 
        with layout.content:
            rca.ImageDisplayArea360(
                static_image=data_url,
                image_style={"width": "100vw", "height": "100vh"},
            )
 
    server.start()  # type: ignore