"""Subtle lengthwise tool marks on the forged dark steel and polished bevel."""
for sf_mname,sf_scale,sf_depth,sf_contrast in [
    ('BlackenedSteel',(3900,3900,110),.000025,.16),
    ('BladeEdge',(7200,7200,95),.000012,.09),
]:
    sf_mat=materials[sf_mname];sf_nodes=sf_mat.node_tree.nodes;sf_links=sf_mat.node_tree.links
    sf_bs=sf_nodes.get('Principled BSDF')
    sf_coords=next(n for n in sf_nodes if n.type=='TEX_COORD')
    sf_stretch=sf_nodes.new('ShaderNodeVectorMath');sf_stretch.operation='MULTIPLY'
    sf_stretch.label='Lengthwise forged tool marks';sf_stretch.inputs[1].default_value=sf_scale
    sf_links.new(sf_coords.outputs['Object'],sf_stretch.inputs[0])
    sf_brush=sf_nodes.new('ShaderNodeTexNoise');sf_brush.inputs['Scale'].default_value=1
    sf_brush.inputs['Detail'].default_value=2;sf_brush.inputs['Roughness'].default_value=.64
    sf_links.new(sf_stretch.outputs['Vector'],sf_brush.inputs['Vector'])
    # Keep the blackened blade dark while introducing local linear wear variation.
    sf_ramp=sf_nodes.new('ShaderNodeValToRGB');sf_ramp.color_ramp.elements[0].position=.32
    sf_ramp.color_ramp.elements[1].position=.72
    sf_ramp.color_ramp.elements[0].color=(1-sf_contrast,)*3+(1,)
    sf_ramp.color_ramp.elements[1].color=(1+sf_contrast,)*3+(1,)
    sf_links.new(sf_brush.outputs['Fac'],sf_ramp.inputs[0])
    sf_color=sf_bs.inputs['Base Color'].links[0].from_socket
    sf_mix=sf_nodes.new('ShaderNodeMixRGB');sf_mix.blend_type='MULTIPLY';sf_mix.inputs[0].default_value=1
    sf_links.new(sf_color,sf_mix.inputs[1]);sf_links.new(sf_ramp.outputs['Color'],sf_mix.inputs[2])
    sf_links.new(sf_mix.outputs[0],sf_bs.inputs['Base Color'])
    sf_normal=sf_bs.inputs['Normal'].links[0].from_socket
    sf_bump=sf_nodes.new('ShaderNodeBump');sf_bump.inputs['Strength'].default_value=.23
    sf_bump.inputs['Distance'].default_value=sf_depth
    sf_links.new(sf_brush.outputs['Fac'],sf_bump.inputs['Height'])
    sf_links.new(sf_normal,sf_bump.inputs['Normal']);sf_links.new(sf_bump.outputs['Normal'],sf_bs.inputs['Normal'])
