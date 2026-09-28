"""READ-ONLY headless inventory of a .blend for game/marketplace readiness.
Usage: blender -b file.blend --factory-startup --python inventory.py -- out.json
Never saves the .blend. Writes only the JSON given after '--'.
"""
import bpy, bmesh, json, os, sys, math, time, traceback
from mathutils import Vector

t0 = time.time()
argv = sys.argv
out_path = argv[argv.index('--') + 1] if '--' in argv else None

MANNY_BONES = {'root','pelvis','spine_01','spine_02','spine_03','spine_04','spine_05','neck_01','neck_02','head',
               'clavicle_l','upperarm_l','lowerarm_l','hand_l','clavicle_r','upperarm_r','lowerarm_r','hand_r',
               'thigh_l','calf_l','foot_l','ball_l','thigh_r','calf_r','foot_r','ball_r'}
PROCEDURAL_TYPES = {'TEX_NOISE','TEX_VORONOI','TEX_WAVE','TEX_MUSGRAVE','TEX_MAGIC','TEX_CHECKER','TEX_BRICK','TEX_GRADIENT','TEX_WHITE_NOISE','TEX_GABOR','TEX_POINTDENSITY','TEX_SKY'}

def approx(a, b, eps=1e-4):
    return all(abs(x - y) < eps for x, y in zip(a, b))

def upstream_sources(socket, depth=0, seen=None):
    """Walk upstream from an input socket; collect coordinate sources feeding it."""
    if seen is None:
        seen = set()
    found = []
    if depth > 12 or not socket.is_linked:
        return found
    for link in socket.links:
        node = link.from_node
        key = (node.name, link.from_socket.name)
        if key in seen:
            continue
        seen.add(key)
        if node.type == 'TEX_COORD':
            found.append('TexCoord.' + link.from_socket.name)
        elif node.type == 'NEW_GEOMETRY':
            found.append('Geometry.' + link.from_socket.name)
        elif node.type == 'UVMAP':
            found.append('UVMap')
        elif node.type == 'ATTRIBUTE':
            found.append('Attribute:' + getattr(node, 'attribute_name', ''))
        else:
            for inp in node.inputs:
                found.extend(upstream_sources(inp, depth + 1, seen))
    return found

def material_info(mat):
    info = {'name': mat.name, 'use_nodes': bool(mat.use_nodes), 'image_textures': [], 'procedural_nodes': [],
            'projection_sources': [], 'classification': 'unknown', 'blend_method': getattr(mat, 'blend_method', None),
            'surface_render_method': getattr(mat, 'surface_render_method', None)}
    if not mat.use_nodes or not mat.node_tree:
        info['classification'] = 'flat_values'
        return info
    nt = mat.node_tree
    for node in nt.nodes:
        if node.type == 'TEX_IMAGE':
            img = node.image
            entry = {'node': node.name, 'image': img.name if img else None, 'projection': node.projection,
                     'vector_sources': upstream_sources(node.inputs['Vector']) if node.inputs['Vector'].is_linked else ['UV(default)']}
            if img:
                try:
                    abspath = bpy.path.abspath(img.filepath) if img.filepath else ''
                except Exception:
                    abspath = img.filepath
                entry.update({'packed': img.packed_file is not None, 'filepath': img.filepath,
                              'source_exists': bool(abspath) and os.path.exists(abspath),
                              'size': list(img.size), 'colorspace': img.colorspace_settings.name,
                              'source': img.source, 'has_data': img.has_data,
                              'pow2': all(s > 0 and (s & (s - 1)) == 0 for s in img.size)})
            info['image_textures'].append(entry)
        elif node.type in PROCEDURAL_TYPES:
            srcs = []
            if 'Vector' in node.inputs:
                srcs = upstream_sources(node.inputs['Vector']) if node.inputs['Vector'].is_linked else ['Generated(default)']
            info['procedural_nodes'].append({'node': node.name, 'type': node.type, 'vector_sources': srcs})
    # projection detection: image textures fed by Object/Generated/Position
    for it in info['image_textures']:
        for s in it['vector_sources']:
            if any(k in s for k in ('TexCoord.Object', 'TexCoord.Generated', 'Geometry.Position', 'TexCoord.Camera', 'TexCoord.Window', 'TexCoord.Reflection')):
                info['projection_sources'].append({'image': it['image'], 'source': s})
    has_img = bool(info['image_textures'])
    has_proc = bool(info['procedural_nodes'])
    if info['projection_sources']:
        info['classification'] = 'image_projection_object_space'
    elif has_img and not has_proc:
        info['classification'] = 'image_textures_uv'
    elif has_img and has_proc:
        info['classification'] = 'image_plus_procedural'
    elif has_proc:
        obj_space = any(any('Object' in s or 'Position' in s for s in p['vector_sources']) for p in info['procedural_nodes'])
        info['classification'] = 'procedural_object_space' if obj_space else 'procedural'
    else:
        info['classification'] = 'flat_values'
    # principled defaults
    bs = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bs:
        info['principled'] = {k: (round(float(bs.inputs[k].default_value), 3) if not bs.inputs[k].is_linked else 'linked')
                              for k in ('Metallic', 'Roughness', 'Alpha') if k in bs.inputs}
        info['principled']['Base Color'] = 'linked' if bs.inputs['Base Color'].is_linked else [round(v, 3) for v in bs.inputs['Base Color'].default_value[:3]]
        info['principled']['Normal_linked'] = bs.inputs['Normal'].is_linked
        emis = bs.inputs.get('Emission Strength')
        if emis:
            info['principled']['Emission Strength'] = 'linked' if emis.is_linked else round(float(emis.default_value), 3)
    return info

def mesh_object_info(obj, depsgraph):
    me = obj.data
    d = {'name': obj.name, 'type': obj.type, 'collections': [c.name for c in obj.users_collection],
         'hide_viewport': obj.hide_viewport, 'hide_render': obj.hide_render, 'hide_get': obj.hide_get() if obj.name in bpy.context.view_layer.objects else None,
         'location': [round(v, 4) for v in obj.location], 'rotation_euler_deg': [round(math.degrees(v), 3) for v in obj.rotation_euler],
         'scale': [round(v, 5) for v in obj.scale],
         'scale_applied': approx(obj.scale, (1, 1, 1)), 'rotation_applied': approx(obj.rotation_euler, (0, 0, 0), 1e-5),
         'world_scale': [round(v, 5) for v in obj.matrix_world.to_scale()],
         'dimensions_m': [round(v, 4) for v in obj.dimensions],
         'parent': obj.parent.name if obj.parent else None, 'parent_type': obj.parent_type if obj.parent else None,
         'modifiers': [{'name': m.name, 'type': m.type, 'show_render': m.show_render, 'show_viewport': m.show_viewport,
                        **({'levels': m.levels, 'render_levels': m.render_levels} if m.type == 'SUBSURF' else {}),
                        **({'ratio': round(m.ratio, 3)} if m.type == 'DECIMATE' else {}),
                        **({'object': m.object.name if m.object else None} if m.type == 'ARMATURE' else {})} for m in obj.modifiers],
         'armature_modifier_target': next((m.object.name for m in obj.modifiers if m.type == 'ARMATURE' and m.object), None),
         'vertex_groups': len(obj.vertex_groups),
         'uv_layers': [uv.name for uv in me.uv_layers], 'uv_layer_count': len(me.uv_layers),
         'materials': [m.name if m else None for m in me.materials], 'material_slot_count': len(me.materials),
         'base_vertices': len(me.vertices), 'base_faces': len(me.polygons),
         'shape_keys': len(me.shape_keys.key_blocks) if me.shape_keys else 0,
         'color_attributes': [c.name for c in me.color_attributes],
         'custom_props': {k: str(obj[k])[:80] for k in obj.keys() if not k.startswith('_')},
         'is_collision_named': obj.name.upper().startswith(('UCX_', 'UBX_', 'USP_', 'UCP_')),
         }
    me.calc_loop_triangles()
    d['base_triangles'] = len(me.loop_triangles)
    # custom normals
    has_cn = getattr(me, 'has_custom_normals', None)
    if has_cn is None:
        has_cn = 'custom_normal' in me.attributes
    d['custom_normals'] = bool(has_cn)
    d['auto_smooth_or_smooth_by_angle_mod'] = any(m.type == 'NODES' and m.node_group and 'Smooth by Angle' in m.node_group.name for m in obj.modifiers)
    d['smooth_faces_fraction'] = round(sum(1 for p in me.polygons if p.use_smooth) / max(1, len(me.polygons)), 3)
    d['sharp_edges'] = 'sharp_edge' in me.attributes
    # non-manifold via bmesh on base mesh
    try:
        bm = bmesh.new(); bm.from_mesh(me)
        d['non_manifold_edges'] = sum(1 for e in bm.edges if not e.is_manifold)
        d['boundary_edges'] = sum(1 for e in bm.edges if e.is_boundary)
        d['loose_verts'] = sum(1 for v in bm.verts if not v.link_edges)
        d['ngons'] = sum(1 for f in bm.faces if len(f.verts) > 4)
        bm.free()
    except Exception as e:
        d['non_manifold_error'] = str(e)
    # evaluated (modifiers applied)
    try:
        ev = obj.evaluated_get(depsgraph)
        eme = ev.to_mesh()
        eme.calc_loop_triangles()
        d['eval_vertices'] = len(eme.vertices); d['eval_faces'] = len(eme.polygons); d['eval_triangles'] = len(eme.loop_triangles)
        d['eval_uv_layer_count'] = len(eme.uv_layers)
        ev.to_mesh_clear()
    except Exception as e:
        d['eval_error'] = str(e)
    # skinning quick stats
    if obj.vertex_groups and obj.parent and obj.parent.type == 'ARMATURE' or d['armature_modifier_target']:
        try:
            unweighted = sum(1 for v in me.vertices if not v.groups)
            maxinf = max((len(v.groups) for v in me.vertices), default=0)
            d['skin'] = {'unweighted_vertices': unweighted, 'max_influences': maxinf}
        except Exception as e:
            d['skin_error'] = str(e)
    return d

def main():
    result = {'file': bpy.data.filepath, 'blender': bpy.app.version_string, 'errors': []}
    scene = bpy.context.scene
    us = scene.unit_settings
    result['scene'] = {'name': scene.name, 'unit_system': us.system, 'length_unit': us.length_unit, 'scale_length': us.scale_length,
                       'render_engine': scene.render.engine, 'frame_range': [scene.frame_start, scene.frame_end],
                       'view_transform': scene.view_settings.view_transform}
    result['collections'] = [{'name': c.name, 'objects': len(c.all_objects), 'hide_render': c.hide_render} for c in bpy.data.collections]
    result['object_type_counts'] = {}
    for o in bpy.data.objects:
        result['object_type_counts'][o.type] = result['object_type_counts'].get(o.type, 0) + 1
    result['object_names_by_type'] = {}
    for o in bpy.data.objects:
        result['object_names_by_type'].setdefault(o.type, []).append(o.name)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    result['meshes'] = []
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        try:
            result['meshes'].append(mesh_object_info(obj, depsgraph))
        except Exception as e:
            result['errors'].append({'object': obj.name, 'error': str(e), 'trace': traceback.format_exc()[-800:]})
    # curves / text objects that may need conversion
    result['non_mesh_geometry'] = [{'name': o.name, 'type': o.type, 'materials': [m.name for m in getattr(o.data, 'materials', []) if m]}
                                   for o in bpy.data.objects if o.type in ('CURVE', 'FONT', 'SURFACE', 'META', 'CURVES', 'POINTCLOUD')]
    result['armatures'] = []
    for obj in bpy.data.objects:
        if obj.type != 'ARMATURE':
            continue
        bones = obj.data.bones
        names = {b.name for b in bones}
        roots = [b.name for b in bones if b.parent is None]
        result['armatures'].append({'name': obj.name, 'data': obj.data.name, 'bone_count': len(bones),
                                    'deform_bones': sum(1 for b in bones if b.use_deform), 'root_bones': roots,
                                    'scale': [round(v, 5) for v in obj.scale], 'rotation_euler_deg': [round(math.degrees(v), 3) for v in obj.rotation_euler],
                                    'location': [round(v, 4) for v in obj.location],
                                    'manny_name_matches': sorted(names & MANNY_BONES), 'manny_name_match_count': len(names & MANNY_BONES),
                                    'sample_bones': sorted(names)[:40],
                                    'children_meshes': [c.name for c in obj.children if c.type == 'MESH'],
                                    'actions_in_file': [a.name for a in bpy.data.actions],
                                    'has_dots_in_names': sum(1 for n in names if '.' in n)})
    result['materials'] = []
    for mat in bpy.data.materials:
        if mat.users == 0:
            continue
        try:
            result['materials'].append(material_info(mat))
        except Exception as e:
            result['errors'].append({'material': mat.name, 'error': str(e)})
    result['images'] = []
    for img in bpy.data.images:
        try:
            abspath = bpy.path.abspath(img.filepath) if img.filepath else ''
        except Exception:
            abspath = img.filepath
        result['images'].append({'name': img.name, 'size': list(img.size), 'packed': img.packed_file is not None,
                                 'filepath': img.filepath, 'source_exists': bool(abspath) and os.path.exists(abspath),
                                 'colorspace': img.colorspace_settings.name, 'source': img.source, 'users': img.users,
                                 'pow2': all(s > 0 and (s & (s - 1)) == 0 for s in img.size) if all(img.size) else False})
    result['collision_objects'] = [m['name'] for m in result['meshes'] if m['is_collision_named']]
    result['totals'] = {'mesh_objects': len(result['meshes']),
                        'base_triangles': sum(m.get('base_triangles', 0) for m in result['meshes']),
                        'eval_triangles': sum(m.get('eval_triangles', 0) for m in result['meshes']),
                        'eval_triangles_render_visible': sum(m.get('eval_triangles', 0) for m in result['meshes'] if not m['hide_render']),
                        'meshes_without_uvs': [m['name'] for m in result['meshes'] if m['uv_layer_count'] == 0],
                        'meshes_unapplied_scale': [m['name'] for m in result['meshes'] if not m['scale_applied']],
                        'meshes_unapplied_rotation': [m['name'] for m in result['meshes'] if not m['rotation_applied']],
                        'meshes_non_manifold': {m['name']: m['non_manifold_edges'] for m in result['meshes'] if m.get('non_manifold_edges')},
                        'meshes_with_custom_normals': [m['name'] for m in result['meshes'] if m['custom_normals']],
                        'material_classes': {mi['name']: mi['classification'] for mi in result['materials']}}
    result['elapsed_s'] = round(time.time() - t0, 1)
    text = json.dumps(result, indent=1, default=str)
    if out_path:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(text)
    print('INVENTORY_JSON_BEGIN')
    print(json.dumps(result['totals'], indent=1, default=str))
    print('INVENTORY_JSON_END', out_path, result['elapsed_s'])

main()
