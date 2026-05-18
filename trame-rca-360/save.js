    // //set initial dome texture
    // setDomeTexture(url) {
    //   if (!this.dome) return;

    //   if (this.dome.texture) {
    //     this.dome.texture.dispose();
    //   }

    //   this.dome.texture = new BABYLON.Texture(
    //     url,
    //     this.scene,
    //     true,
    //     false,
    //     BABYLON.Texture.TRILINEAR_SAMPLINGMODE
    //   );
    // },


    # ---------------------------------------------------------------------------
# Render function
# ---------------------------------------------------------------------------

# def render(width: int, height: int, samples_per_pixel: int,
#            output_path: str | None = None,
#            world=None) -> np.ndarray:
#     """
#     Renders a 360 equirectangular image using the shared barney device.

#     @param width             - image width in pixels
#     @param height            - image height (should be width // 2 for equirectangular)
#     @param samples_per_pixel - number of paths traced per pixel
#     @param output_path       - optional path to save PNG output
#     @param world             - ANARI world object to render; defaults to cardinal scene
#     @returns                 - RGBA pixel array of shape (height, width, 4)
#     """
#     device = get_device()

#     if world is None:
#         world = build_scene_cardinals(device)

#     assert world is not None

#     camera = device.newCamera('omnidirectional')
#     camera.setParameter('position',  anari.float3, (0.0, 0.0, 0.0))
#     camera.setParameter('up',        anari.float3, (0.0, 1.0, 0.0))
#     camera.setParameter('direction', anari.float3, (0.0, 0.0, -1.0))
#     camera.setParameter('layout',    anari.STRING, 'equirectangular')
#     camera.commitParameters()

#     renderer = device.newRenderer('default')
#     renderer.setParameter('pixelSamples', anari.INT32, samples_per_pixel)
#     renderer.commitParameters()

#     frame = device.newFrame()
#     frame.setParameter('size',          anari.uint2,     [width, height])
#     frame.setParameter('channel.color', anari.DATA_TYPE, anari.UFIXED8_RGBA_SRGB)
#     frame.setParameter('renderer',      anari.RENDERER,  renderer)
#     frame.setParameter('camera',        anari.CAMERA,    camera)
#     frame.setParameter('world',         anari.WORLD,     world)
#     frame.commitParameters()

#     frame.render()

#     pixels = np.array(frame.get('channel.color'))

#     del frame
#     del renderer
#     del camera
#     del world

#     if output_path is not None:
#         Image.fromarray(pixels, mode="RGBA").convert("RGB").save(output_path)
#         print(f"[pynari] Saved → {output_path}")

#     return pixels