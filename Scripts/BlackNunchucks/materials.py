"""Procedural source materials for the black nunchucks bake.

Contract: ``grip, steel = create_materials()``.  Both are opaque Principled
materials with procedural Base Color, Roughness and Normal inputs, constant
Metallic values (0 for grip and 1 for steel), and
no image textures.  Their names are stable and existing names are rebuilt.

Texture Coordinate.Object is in metres.  Apply object scale before baking;
model cap cylinders along local Z to align the fine circumferential brushing.
The nodes are source shaders: bake them into the shared, non-overlapping UV
atlas for the export materials.  Nothing is written to disk by this module.
"""

import bpy


def _material(name, color, roughness, metallic):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1.0)
    mat.roughness = roughness
    mat.metallic = metallic
    nodes = mat.node_tree.nodes
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    output.name = 'Material Output'
    output.location = (1000, 100)
    shader = nodes.new('ShaderNodeBsdfPrincipled')
    shader.name = 'PBR Source'
    shader.label = 'Bake Base Color / Roughness / Metallic / Normal'
    shader.location = (690, 100)
    shader.inputs['Base Color'].default_value = (*color, 1.0)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['IOR'].default_value = 1.49
    mat.node_tree.links.new(shader.outputs['BSDF'], output.inputs['Surface'])
    coords = nodes.new('ShaderNodeTexCoord')
    coords.name = 'Metric Object Coordinates'
    coords.label = 'Object coordinates in metres; apply scale'
    coords.location = (-1100, 150)
    return mat, nodes, mat.node_tree.links, shader, coords


def _noise(nodes, links, vector, name, scale, detail, roughness, location):
    node = nodes.new('ShaderNodeTexNoise')
    node.name = name
    node.label = name
    node.location = location
    node.noise_dimensions = '3D'
    node.inputs['Scale'].default_value = scale
    node.inputs['Detail'].default_value = detail
    node.inputs['Roughness'].default_value = roughness
    links.new(vector, node.inputs['Vector'])
    return node


def _ramp(nodes, links, socket, name, stops, location):
    node = nodes.new('ShaderNodeValToRGB')
    node.name = name
    node.label = name
    node.location = location
    node.color_ramp.interpolation = 'EASE'
    ramp = node.color_ramp
    for element, (position, color) in zip(ramp.elements, (stops[0], stops[-1])):
        element.position = position
        element.color = color
    for position, color in stops[1:-1]:
        ramp.elements.new(position).color = color
    links.new(socket, node.inputs['Fac'])
    return node


def _gray(value):
    return (value, value, value, 1.0)


def _metric_scale(nodes, links, socket, value, name, location):
    node = nodes.new('ShaderNodeVectorMath')
    node.operation = 'MULTIPLY'
    node.name = name
    node.label = name
    node.location = location
    node.inputs[1].default_value = value
    links.new(socket, node.inputs[0])
    return node.outputs['Vector']


def _grip_material():
    mat, nodes, links, shader, coords = _material(
        'M_BlackNunchucks_Grip', (0.011, 0.013, 0.014), 0.365, 0.0)
    mat['surface_description'] = 'Black satin elastomer, fine wavy pebble grain'
    mat['texture_units'] = 'metres'
    mat['nominal_grain_mm'] = 1.25
    mat['nominal_relief_mm'] = 0.20

    # Shallow grain is longer around the circumference than along the grip,
    # giving the fine crinkled waves visible on molded elastomer.  This is a
    # stochastic surface, not a spiral, wrap or repeated geometric pattern.
    grain_vector = _metric_scale(
        nodes, links, coords.outputs['Object'], (0.70, 0.70, 1.55),
        'Gently elongated grip grain', (-870, 150))
    flow = _noise(nodes, links, grain_vector, 'Submillimetre grain flow',
                  1050.0, 2.0, 0.60, (-660, 390))
    flow.inputs['Distortion'].default_value = 0.68

    # Distort Voronoi cells in physical units before extracting their narrow
    # edges.  A 0.46 mm warp avoids a regular alligator-skin appearance.
    warp = _metric_scale(nodes, links, flow.outputs['Color'],
                         (0.00046, 0.00046, 0.00046),
                         '0.46 mm irregular grain warp', (-430, 610))
    add = nodes.new('ShaderNodeVectorMath')
    add.operation = 'ADD'
    add.name = 'Warped metric grain coordinates'
    add.location = (-205, 580)
    links.new(grain_vector, add.inputs[0])
    links.new(warp, add.inputs[1])
    cells = nodes.new('ShaderNodeTexVoronoi')
    cells.name = 'Fine wavy pebble furrows'
    cells.label = 'Fine 1 mm crinkled grain'
    cells.location = (10, 570)
    cells.voronoi_dimensions = '3D'
    cells.feature = 'DISTANCE_TO_EDGE'
    cells.inputs['Scale'].default_value = 1350.0
    cells.inputs['Randomness'].default_value = 1.0
    links.new(add.outputs['Vector'], cells.inputs['Vector'])
    relief = _ramp(nodes, links, cells.outputs['Distance'],
                   'Soft creases with rounded grain peaks',
                   [(0.005, _gray(0.04)), (0.075, _gray(0.55)),
                    (0.20, _gray(0.96))], (240, 600))

    # Warped fine ripples make the grip read as a molded, crinkled surface
    # rather than tiled polygonal leather.  The pebble relief only breaks up
    # the waves and supplies small irregular valleys.
    crinkle = nodes.new('ShaderNodeTexWave')
    crinkle.name = 'Fine irregular molded crinkles'
    crinkle.label = 'Warped 1.26 mm waves; no wrap seam'
    crinkle.location = (-450, 850)
    crinkle.wave_type = 'BANDS'
    crinkle.bands_direction = 'Z'
    crinkle.wave_profile = 'SIN'
    crinkle.inputs['Scale'].default_value = 248.0
    crinkle.inputs['Distortion'].default_value = 9.0
    crinkle.inputs['Detail'].default_value = 3.0
    crinkle.inputs['Detail Scale'].default_value = 1.5
    crinkle.inputs['Detail Roughness'].default_value = 0.65
    links.new(coords.outputs['Object'], crinkle.inputs['Vector'])
    grain_height = nodes.new('ShaderNodeMixRGB')
    grain_height.name = 'Crinkled grain with small pebble valleys'
    grain_height.blend_type = 'MIX'
    grain_height.location = (260, 850)
    grain_height.inputs[0].default_value = 0.20
    links.new(crinkle.outputs['Fac'], grain_height.inputs[1])
    links.new(relief.outputs['Color'], grain_height.inputs[2])

    body_color = _ramp(nodes, links, flow.outputs['Fac'],
                       'Black grain color, linear values',
                       [(0.20, (0.0065, 0.0075, 0.008, 1.0)),
                        (0.80, (0.016, 0.018, 0.019, 1.0))], (-180, 230))
    links.new(body_color.outputs['Color'], shader.inputs['Base Color'])
    body_roughness = _ramp(nodes, links, flow.outputs['Fac'],
                           'Satin peaks and soft grain valleys',
                           [(0.20, _gray(0.415)), (0.80, _gray(0.305))],
                           (-160, -20))
    links.new(body_roughness.outputs['Color'], shader.inputs['Roughness'])

    micro = _noise(nodes, links, coords.outputs['Object'],
                   'Fine rubber micrograin', 7200.0, 2.0, 0.65, (-630, -300))
    micro_bump = nodes.new('ShaderNodeBump')
    micro_bump.name = '7 micron micrograin'
    micro_bump.location = (-130, -320)
    micro_bump.inputs['Strength'].default_value = 0.18
    micro_bump.inputs['Distance'].default_value = 0.000007
    links.new(micro.outputs['Fac'], micro_bump.inputs['Height'])
    grain_bump = nodes.new('ShaderNodeBump')
    grain_bump.name = '200 micron rounded grip relief'
    grain_bump.label = 'Shallow wavy grain catches close-up highlights'
    grain_bump.location = (410, 320)
    grain_bump.inputs['Strength'].default_value = 0.75
    grain_bump.inputs['Distance'].default_value = 0.00020
    links.new(grain_height.outputs['Color'], grain_bump.inputs['Height'])
    links.new(micro_bump.outputs['Normal'], grain_bump.inputs['Normal'])
    links.new(grain_bump.outputs['Normal'], shader.inputs['Normal'])
    return mat


def _steel_material():
    mat, nodes, links, shader, coords = _material(
        'M_BlackNunchucks_Steel', (0.59, 0.61, 0.63), 0.255, 1.0)
    mat['surface_description'] = 'Clean stainless steel with fine machining bands'
    mat['texture_units'] = 'metres'
    mat['brush_axis'] = 'local Z; fine circumferential bands on cylinders'
    mat['nominal_relief_mm'] = 0.005
    # The final bake need not rely on an anisotropy extension: low-amplitude
    # roughness bands and the normal bake carry the brushed surface appearance.
    if 'Anisotropic IOR Level' in shader.inputs:
        shader.inputs['Anisotropic IOR Level'].default_value = 0.15

    brush_vector = _metric_scale(
        nodes, links, coords.outputs['Object'], (50.0, 50.0, 4800.0),
        'Fine circumferential machining coordinates', (-860, 300))
    brush = _noise(nodes, links, brush_vector, 'Clean soft machining bands',
                   1.0, 2.0, 0.58, (-600, 320))
    finish = _ramp(nodes, links, brush.outputs['Fac'],
                   'Polished brushed steel roughness',
                   [(0.15, _gray(0.225)), (0.85, _gray(0.29))], (-290, 300))
    links.new(finish.outputs['Color'], shader.inputs['Roughness'])

    color = _ramp(nodes, links, brush.outputs['Fac'],
                  'Subtle neutral stainless variation',
                  [(0.15, (0.565, 0.585, 0.605, 1.0)),
                   (0.85, (0.62, 0.64, 0.66, 1.0))], (-290, 30))
    links.new(color.outputs['Color'], shader.inputs['Base Color'])

    fine_vector = _metric_scale(
        nodes, links, coords.outputs['Object'], (90.0, 90.0, 16500.0),
        'Microscopic polished brushing', (-860, -180))
    fine = _noise(nodes, links, fine_vector, 'Fine steel polish grain',
                  1.0, 1.4, 0.54, (-600, -180))
    fine_bump = nodes.new('ShaderNodeBump')
    fine_bump.name = '2 micron polish relief'
    fine_bump.location = (-285, -240)
    fine_bump.inputs['Strength'].default_value = 0.17
    fine_bump.inputs['Distance'].default_value = 0.000002
    links.new(fine.outputs['Fac'], fine_bump.inputs['Height'])
    brush_bump = nodes.new('ShaderNodeBump')
    brush_bump.name = '5 micron machining relief'
    brush_bump.location = (300, -100)
    brush_bump.inputs['Strength'].default_value = 0.24
    brush_bump.inputs['Distance'].default_value = 0.000005
    links.new(brush.outputs['Fac'], brush_bump.inputs['Height'])
    links.new(fine_bump.outputs['Normal'], brush_bump.inputs['Normal'])
    links.new(brush_bump.outputs['Normal'], shader.inputs['Normal'])
    return mat


def create_materials():
    """Return ``(grip, steel)`` source materials; safe to call repeatedly."""
    return _grip_material(), _steel_material()
