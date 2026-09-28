"""Subdued, fine black cloth for the reference-driven BlackCloak rebuild.

Call from Blender with ``make_refined_textile(texture_directory)``. Only the
supplied directory receives texture files. UVs are in meters; the existing
cloak exporter bakes the 0.128 m texture repeat into portable mesh UVs.
"""

from pathlib import Path
import math

import bpy
import numpy as np


TILE_METERS = 0.128
TEXTURE_SIZE = 2048


def _save_image(directory, name, array, noncolor=False):
    """Write 8-bit PNG code values and reload before packing, like the exporter."""
    path = directory / (name + ".png")
    image = bpy.data.images.new(
        name + "_Generated", width=array.shape[1], height=array.shape[0],
        alpha=False, float_buffer=False,
    )
    image.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    pixels = np.ones((*array.shape[:2], 4), dtype=np.float32)
    if array.ndim == 2:
        pixels[:, :, :3] = array[:, :, None]
    else:
        pixels[:, :, :3] = array
    image.pixels.foreach_set(pixels.ravel())
    image.file_format = "PNG"
    image.filepath_raw = str(path)
    image.save()
    bpy.data.images.remove(image)
    image = bpy.data.images.load(str(path), check_existing=False)
    image.name = name
    image.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    image.pack()
    return image


def make_refined_textile(tex_dir):
    """Return the portable-compatible M_BlackCloak_WovenWool material.

    The reference reads as nearly uniform matte black cloth at garment scale.
    Fabric relief is exclusively microscopic: silhouette and drape must come
    from garment geometry, never a coarse procedural bump pattern.
    """
    directory = Path(tex_dir)
    directory.mkdir(parents=True, exist_ok=True)
    n = TEXTURE_SIZE
    tau = math.tau
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    u, v = x / n, y / n
    rng = np.random.default_rng(271849)

    # 128 yarns per 128 mm = 1 mm pitch. All frequencies are integer,
    # making the tile periodic without border seams. Crossings are softened
    # so normal filtering cannot produce a coarse, embossed checkerboard.
    phase_x = tau * (128 * u + 0.25 * np.sin(tau * 37 * v))
    phase_y = tau * (128 * v + 0.22 * np.sin(tau * 43 * u))
    warp = (0.5 + 0.5 * np.cos(phase_x)) ** 1.35
    weft = (0.5 + 0.5 * np.cos(phase_y)) ** 1.35
    crossing = np.cos(phase_x * 0.5) * np.cos(phase_y * 0.5)
    weave = warp * (0.53 + 0.12 * crossing) + weft * (0.47 - 0.12 * crossing)

    # Weak, smooth yarn-dye variation. Deliberately excluded from the height
    # field: this is color variation, not wrinkles or broad pebbled relief.
    dye = np.zeros((n, n), dtype=np.float32)
    for _ in range(12):
        fx, fy = int(rng.integers(1, 13)), int(rng.integers(1, 13))
        phase = float(rng.uniform(0, tau))
        dye += np.cos(tau * (fx * u + fy * v) + phase) / (1 + fx + fy)
    dye /= max(float(np.std(dye)), 0.01)
    dye = np.tanh(dye * 0.65)
    fibers = rng.normal(0, 1, (n, n)).astype(np.float32)
    grain = np.zeros((n,n),dtype=np.float32)
    for _ in range(22):
        fx,fy=int(rng.integers(60,225)),int(rng.integers(60,225))
        grain+=np.cos(tau*(fx*u+fy*v)+float(rng.uniform(0,tau)))
    grain/=max(float(np.std(grain)),.01)
    shade = np.clip(
        0.099 + dye * 0.003 + (weave - float(weave.mean())) * 0.008
        + fibers * 0.003 + grain*.010,
        0.081, 0.120,
    )
    # Neutral charcoal with only an almost imperceptible warm bias.
    rgb = np.stack([shade, shade * 0.997, shade * 0.988], axis=2)
    base = _save_image(directory, "T_BlackCloak_BaseColor", rgb)
    roughness = np.clip(0.927 + dye * 0.005 + (weave - 0.4) * 0.008, 0.915, 0.940)
    rough = _save_image(directory, "T_BlackCloak_Roughness", roughness, True)

    # Microscopic yarn relief produces a filterable cloth grain.
    # Its normal map contains the complete intended amplitude, allowing normal
    # strength 1 in Blender, glTF, and Unreal without differing scale settings.
    height = weave * 0.000028
    pixel_meters = TILE_METERS / n
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) / (2 * pixel_meters)
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) / (2 * pixel_meters)
    normals = np.stack([-dx, -dy, np.ones_like(dx)], axis=2)
    normals /= np.linalg.norm(normals, axis=2, keepdims=True)
    opengl = normals * 0.5 + 0.5
    normal = _save_image(directory, "T_BlackCloak_Normal_OpenGL", opengl, True)
    directx = opengl.copy()
    directx[:, :, 1] = 1 - directx[:, :, 1]
    _save_image(directory, "T_BlackCloak_Normal_DirectX", directx, True)

    # Reuse the exact export-facing name if the caller is rebuilding materials.
    mat = bpy.data.materials.get("M_BlackCloak_WovenWool")
    if mat is None:
        mat = bpy.data.materials.new("M_BlackCloak_WovenWool")
    mat.use_nodes = True
    mat.diffuse_color = (0.0132, 0.0131, 0.0129, 1)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (580, 80)
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    principled.name = "Principled BSDF"
    principled.location = (270, 80)
    principled.inputs["Specular IOR Level"].default_value = 0.08
    principled.inputs["Roughness"].default_value = 0.927
    principled.inputs["Sheen Weight"].default_value = 0.0
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    tc = nodes.new("ShaderNodeTexCoord")
    tc.name = "Texture Coordinate"
    tc.location = (-800, 120)
    scale = nodes.new("ShaderNodeVectorMath")
    scale.name = "Meter UV to 128 mm tile"
    scale.operation = "SCALE"
    scale.inputs[3].default_value = 1 / TILE_METERS
    scale.location = (-600, 120)
    links.new(tc.outputs["UV"], scale.inputs[0])
    for index, (image, socket) in enumerate([
        (base, "Base Color"), (rough, "Roughness"), (normal, "Normal"),
    ]):
        tex = nodes.new("ShaderNodeTexImage")
        tex.name = "Export_" + socket.replace(" ", "")
        tex.label = image.name
        tex.image = image
        tex.extension = "REPEAT"
        tex.interpolation = "Linear"
        tex.location = (-350, 240 - index * 300)
        links.new(scale.outputs[0], tex.inputs["Vector"])
        if socket == "Normal":
            nm = nodes.new("ShaderNodeNormalMap")
            nm.name = "Fine woven grain"
            nm.space = "TANGENT"
            nm.inputs["Strength"].default_value = 1.0
            nm.location = (-40, -330)
            links.new(tex.outputs["Color"], nm.inputs["Color"])
            links.new(nm.outputs["Normal"], principled.inputs["Normal"])
        else:
            links.new(tex.outputs["Color"], principled.inputs[socket])
    mat["uv_units"] = "Meters; repeat tile every 0.128 m"
    mat["reference_material_notes"] = "Matte black weave; irregular 1 mm yarn pitch; 28 um relief; fine color grain without broad bump or sheen."
    return mat
