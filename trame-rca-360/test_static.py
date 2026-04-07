from pathlib import Path
from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame_rca.widgets import rca

server = get_server()
server.client_type = "vue3" #type: ignore

static_path = Path(__file__).parent / "public"
server.serve["/static"] = str(static_path) #type:ignore

with SinglePageLayout(server) as layout:
    layout.title.set_text("360 Test")

    with layout.content:
        rca.ImageDisplayArea360(
            static_image="/static/test.jpeg",
            image_style={"width": "100vw", "height": "100vh"},
        )

if __name__ == "__main__":
    server.start() #type: ignore