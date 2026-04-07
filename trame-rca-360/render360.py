import numpy as np
from PIL import Image
import pynari as anari
import ctypes



def add_sphere(device, pos, radius, mat):
    geom = device.newGeometry('sphere')
    geom.setParameter('vertex.position', anari.ARRAY1D, device.newArray1D(anari.FLOAT32_VEC3, np.array([pos], dtype=np.float32)))
    geom.setParameter('radius', anari.FLOAT32, radius)
    geom.commitParameters()

    surf = device.newSurface()
    surf.setParameter('geometry', anari.GEOMETRY, geom)
    surf.setParameter('material', anari.MATERIAL, mat)
    surf.commitParameters()
    return surf


def make_matte(device, r, g, b):
    mat = device.newMaterial('matte')
    mat.setParameter('color', anari.float3, (r, g, b))
    mat.commitParameters()
    return mat


def make_metal(device, r, g, b, roughness=0.1):
    mat = device.newMaterial('physicallyBased')
    mat.setParameter('baseColor', anari.float3, (r, g, b))
    mat.setParameter('metallic',  anari.FLOAT32, 1.0)
    mat.setParameter('roughness', anari.FLOAT32, roughness)
    mat.commitParameters()
    return mat


def build_scene(device):
    surfaces = []
    r = 12.0  # distance from centre

    # one sphere in each cardinal direction and up/down
    surfaces.append(add_sphere(device, ( r,  0,  0), 1.5, make_matte(device, 0.9, 0.2, 0.2)))  # right  — red
    surfaces.append(add_sphere(device, (-r,  0,  0), 1.5, make_matte(device, 0.2, 0.5, 0.9)))  # left   — blue
    surfaces.append(add_sphere(device, ( 0,  0,  r), .3, make_matte(device, 0.2, 0.8, 0.3)))  # front  — green
    surfaces.append(add_sphere(device, ( 0,  0, -r), 2, make_matte(device, 0.9, 0.7, 0.1)))  # back   — yellow
    surfaces.append(add_sphere(device, ( 0,  r,  0), 1.5, make_metal(device, 0.9, 0.9, 0.9)))  # up     — silver
    surfaces.append(add_sphere(device, ( 0, -r,  0), 1.5, make_metal(device, 0.8, 0.6, 0.1)))  # down   — gold

    world = device.newWorld()
    world.setParameterArray1D('surface', anari.SURFACE, surfaces)
    world.commitParameters()

    return world
def build_random_scene(device):
    surfaces = []
    num_spheres = np.random.randint(5,10)
    for i in range(num_spheres):
        color = np.random.random(3)                          
        signs = np.random.choice([-1, 1], size = 3)         
        position = color * signs * 8.0                      
        surfaces.append(add_sphere(
            device, position.tolist(), 1.5, make_matte(device, color[0], color[1], color[2])
        ))

    world = device.newWorld()
    world.setParameterArray1D('surface', anari.SURFACE, surfaces)
    world.commitParameters()
    return world

def render(width, height, samples_per_pixel, output_path=None, randomize = False):
    """
    Renders a 360 equirectangular image.
    @param camera_position - anari.float3, camera_position[0] - x coord, camera_position[1] - y coord, camera_position[2] - z coord
    @param camera_direction - anari.float3, camera_direction[0] - x coord, camera_direction[1] - y coord, camera_direction[2] - z coord
    @param width -  int, width of camera aspect
    @param height - int, height of camera aspect
    @param samples_per_pixel - int, number of paths traced for each pixel
    @param output_path - string, path to save resulting image as png, otherwise returns a raw pixel array by default
    """


    def status_callback(userData, device, source, sourceType, severity, code, message):
        print("anari", ctypes.cast(message, ctypes.c_char_p).value.decode()) #type: ignore

    CALLBACK = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_char_p, ctypes.c_int,
    ctypes.c_int, ctypes.c_int,
    ctypes.c_char_p)

    cb = CALLBACK(status_callback)

    device = anari.newDevice("barney", "default")
    if anari.has_cuda_capable_gpu():
        print("[pynari] CUDA GPU detected — full quality")
    else:
        print("[pynari] No CUDA GPU — running on CPU")

    renderer = device.newRenderer('default')
    renderer.setParameter('pixelSamples', anari.INT32, samples_per_pixel)
    renderer.commitParameters()


    world = build_random_scene(device) if randomize else build_scene(device)   
    # camera = device.newCamera('omnidirectional')
    # camera.setParameter('position',  anari.float3, (0.0, 0.0, 0.0))
    # camera.setParameter('up',        anari.float3, (0.0, 1.0, 0.0))
    # camera.setParameter('direction', anari.float3, (0.0, 0.0, -1.0))
    # camera.setParameter('layout',    anari.STRING, 'equirectangular')
    # camera.commitParameters()
    camera = device.newCamera('perspective')
    camera.setParameter('position',  anari.float3, (0.0, 0.0, 20.0))
    camera.setParameter('direction', anari.float3, (0.0, 0.0, -1.0))
    camera.setParameter('up',        anari.float3, (0.0, 1.0,  0.0))
    camera.setParameter('aspect',    anari.FLOAT32, width / height)
    camera.setParameter('fovy',      anari.FLOAT32, 60.0 * np.pi / 180)
    camera.commitParameters()

    frame = device.newFrame()
    frame.setParameter('size',          anari.uint2,     [width, height])
    frame.setParameter('channel.color', anari.DATA_TYPE, anari.UFIXED8_RGBA_SRGB)
    frame.setParameter('renderer',      anari.OBJECT,    renderer)
    frame.setParameter('camera',        anari.OBJECT,    camera)
    frame.setParameter('world',         anari.OBJECT,    world)
    frame.commitParameters()

    frame.render()
    #creating pixel array
    fb = frame.get('channel.color')
    pixels = np.array(fb)

    #converting pixel array to image if output path is provided
    if output_path is not None:
        Image.fromarray(pixels, mode="RGBA").convert("RGB").save(output_path)
        print(f"[pynari] Saved → {output_path}")

    return pixels