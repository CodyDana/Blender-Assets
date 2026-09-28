"""Export and round-trip-check the saved Black Nunchucks Blender asset.

Run inside Blender 5.2, after the builder has saved the baked source::

    from export_validate import export_asset
    report = export_asset(project_root, project_root / 'Assets/BlackNunchucks.blend')

The source is never saved by this module. It is reopened at the end, including
after a failed export. Validation is performed in Blender, not in a game engine.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

import bmesh
import bpy
from mathutils import Matrix

_SCRIPTS = str(Path(__file__).resolve().parents[1])
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from pipeline.export_fbx import export_fbx
from pipeline.helpers import selection
from pipeline.qa_check import qa_check


ASSET = 'BlackNunchucks'
COLLECTION = 'BLACK_NUNCHUCKS'
RIG = 'Nunchucks_Rig'
LOD_LEVELS = (0, 1, 2)
DISTANCE_TOLERANCE = 1e-5  # metres: 0.01 mm
UV_TOLERANCE = 2e-5
WELD_DISTANCE = 1e-7      # inspect topology across interchange vertex splits


def _digest(path):
    sha = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            sha.update(chunk)
    return sha.hexdigest()


def _write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding='utf-8')


def _close_values(left, right, tolerance):
    return len(left) == len(right) and all(abs(a - b) <= tolerance for a, b in zip(left, right))


def _bounds(objects):
    coords = [obj.matrix_world @ vertex.co for obj in objects for vertex in obj.data.vertices]
    if not coords:
        raise ValueError('Cannot measure an empty asset')
    low = [min(point[axis] for point in coords) for axis in range(3)]
    high = [max(point[axis] for point in coords) for axis in range(3)]
    return {'min': low, 'max': high, 'dimensions': [b - a for a, b in zip(low, high)]}


def _topology(mesh):
    mesh.calc_loop_triangles()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        raw = {
            'loose_vertices': sum(not vertex.link_faces for vertex in bm.verts),
            'wire_edges': sum(not edge.link_faces for edge in bm.edges),
            'edges_with_over_two_faces': sum(len(edge.link_faces) > 2 for edge in bm.edges),
            'boundary_edges': sum(edge.is_boundary for edge in bm.edges),
            'zero_length_edges': sum(edge.calc_length() <= 1e-8 for edge in bm.edges),
            'degenerate_triangles': sum(tri.area <= 1e-12 for tri in mesh.loop_triangles),
        }
        # glTF legitimately splits vertices at UV seams and hard normals. Check
        # its geometric surface on a temporary welded BMesh, without editing it.
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=WELD_DISTANCE)
        raw.update({
            'welded_boundary_edges': sum(edge.is_boundary for edge in bm.edges),
            'welded_non_manifold_edges': sum(not edge.is_manifold for edge in bm.edges),
            'welded_vertices': len(bm.verts),
            'weld_tolerance_m': WELD_DISTANCE,
        })
        return raw
    finally:
        bm.free()


def _uv_statistics(mesh):
    """Corner-weighted moments survive vertex splits and triangle reordering."""
    records = []
    for layer in mesh.uv_layers:
        coordinates = [layer.data[loop].uv for tri in mesh.loop_triangles for loop in tri.loops]
        count = len(coordinates)
        if not count:
            raise ValueError(f'{mesh.name} has empty UV data')
        records.append({
            'name': layer.name,
            'triangle_corners': count,
            'min': [min(uv[axis] for uv in coordinates) for axis in range(2)],
            'max': [max(uv[axis] for uv in coordinates) for axis in range(2)],
            'mean': [sum(uv[axis] for uv in coordinates) / count for axis in range(2)],
            'second_moment': [sum(uv[axis] ** 2 for uv in coordinates) / count for axis in range(2)],
        })
    return records


def _weights(obj, rig):
    bones = set(rig.data.bones.keys())
    groups = {group.index: group.name for group in obj.vertex_groups}
    signatures = []
    unweighted = 0
    max_error = 0.0
    max_influences = 0
    for vertex in obj.data.vertices:
        weights = sorted((groups[group.group], float(group.weight)) for group in vertex.groups
                         if group.weight > 0 and groups.get(group.group) in bones)
        total = sum(weight for _, weight in weights)
        unweighted += not weights
        max_error = max(max_error, abs(total - 1.0))
        max_influences = max(max_influences, len(weights))
        signatures.append('|'.join(f'{bone}:{weight:.6f}' for bone, weight in weights))
    # Count by triangle corner, not by raw vertices: glTF may split vertices.
    counts = Counter(signatures[index] for tri in obj.data.loop_triangles for index in tri.vertices)
    return {
        'unweighted_vertices': unweighted,
        'max_influences': max_influences,
        'max_weight_sum_error': max_error,
        'triangle_corner_assignments': dict(sorted(counts.items())),
    }


def _mesh_record(obj, rig=None):
    mesh = obj.data
    mesh.calc_loop_triangles()
    materials = Counter()
    for tri in mesh.loop_triangles:
        slot = tri.material_index
        material = mesh.materials[slot] if slot < len(mesh.materials) else None
        materials[material.name if material else '<unassigned>'] += 1
    result = {
        'name': obj.name,
        'vertices': len(mesh.vertices),
        'triangles': len(mesh.loop_triangles),
        'uv_layers': _uv_statistics(mesh),
        'material_triangles': dict(sorted(materials.items())),
        'bounds_m': _bounds([obj]),
        'topology': _topology(mesh),
    }
    if rig:
        result['skin'] = _weights(obj, rig)
    return result


def _skeleton_record(rig):
    return {
        'name': rig.name,
        'bone_count': len(rig.data.bones),
        'bones': {
            bone.name: {
                'parent': bone.parent.name if bone.parent else None,
                'deform': bone.use_deform,
                'head_m': list(rig.matrix_world @ bone.head_local),
            }
            for bone in rig.data.bones
        },
    }


def _materials(objects):
    result = {}
    for obj in objects:
        for material in obj.data.materials:
            if material is None or material.name in result:
                continue
            images = {}
            if material.node_tree:
                for node in material.node_tree.nodes:
                    image = getattr(node, 'image', None)
                    if image:
                        filepath = Path(bpy.path.abspath(image.filepath)) if image.filepath else None
                        images[image.name] = {
                            'filepath': str(filepath) if filepath else None,
                            'size': list(image.size),
                            'colorspace': image.colorspace_settings.name,
                            'packed': bool(image.packed_file),
                            'sha256': _digest(filepath) if filepath and filepath.is_file() else None,
                        }
            result[material.name] = {'images': images}
    return result


def _source_objects():
    collection = bpy.data.collections.get(COLLECTION)
    if not collection:
        raise ValueError(f'Missing collection {COLLECTION}')
    rig = bpy.data.objects.get(RIG)
    if rig is None or rig.type != 'ARMATURE':
        raise ValueError(f'Missing armature {RIG}')
    lods = {level: [] for level in LOD_LEVELS}
    for obj in collection.all_objects:
        if obj.type != 'MESH' or obj.name.startswith(('UCX_', 'UBX_', 'USP_', 'UCP_')):
            continue
        if 'part_id' not in obj or 'lod_level' not in obj:
            raise ValueError(f'{obj.name} lacks part_id/lod_level metadata')
        level = int(obj['lod_level'])
        if level not in lods:
            raise ValueError(f'{obj.name} has unsupported LOD {level}')
        lods[level].append(obj)
    for level, objects in lods.items():
        objects.sort(key=lambda obj: str(obj['part_id']))
        parts = [str(obj['part_id']) for obj in objects]
        if not parts or len(parts) != len(set(parts)):
            raise ValueError(f'LOD{level} must have unique, nonempty part_id entries')
        for obj in objects:
            expected_name = f'SM_{ASSET}_{obj["part_id"]}_LOD{level}'
            if obj.name != expected_name:
                raise ValueError(f'Expected {expected_name}, found {obj.name}')
            if any(mod.type != 'ARMATURE' for mod in obj.modifiers):
                raise ValueError(f'{obj.name}: apply geometry modifiers before exporting')
            skin = [mod for mod in obj.modifiers if mod.type == 'ARMATURE' and mod.object == rig]
            if len(skin) != 1:
                raise ValueError(f'{obj.name}: expected one Armature modifier targeting {RIG}')
            if len(obj.data.uv_layers) < 2:
                raise ValueError(f'{obj.name}: UV0 and UV1 are required')
            if not obj.data.materials or any(mat is None for mat in obj.data.materials):
                raise ValueError(f'{obj.name}: missing material assignment')
    return rig, lods


def _static_copies(objects):
    """Detach geometry from the rig in memory; retain original export node names."""
    copies = []
    renamed = []
    for source in objects:
        name = source.name
        source.name = '__NUNCHUCKS_SOURCE_' + name
        renamed.append((source, name))
        obj = bpy.data.objects.new(name, source.data.copy())
        bpy.context.scene.collection.objects.link(obj)
        obj.data.transform(source.matrix_world)
        obj.matrix_world = Matrix.Identity(4)
        obj['part_id'] = source['part_id']
        obj['component'] = source.get('component', '')
        copies.append(obj)
    return copies, renamed


def _collision_hulls(objects):
    """Two convex handle proxies; geometry only, with no game-physics claim."""
    hulls = []
    records = []
    for side in ('L', 'R'):
        grip = next((obj for obj in objects if obj.get('part_id') == f'grip_{side}'), None)
        parts = [obj for obj in objects if obj.get('part_id') in (f'grip_{side}', f'cap_{side}')]
        if not grip or not parts:
            continue
        bm = bmesh.new()
        try:
            for obj in parts:
                for vertex in obj.data.vertices:
                    bm.verts.new(obj.matrix_world @ vertex.co)
            bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=WELD_DISTANCE)
            bmesh.ops.convex_hull(bm, input=list(bm.verts), use_existing_faces=False)
            unused = [vertex for vertex in bm.verts if not vertex.link_faces]
            if unused:
                bmesh.ops.delete(bm, geom=unused, context='VERTS')
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            bmesh.ops.triangulate(bm, faces=list(bm.faces))
            name = f'UCX_{grip.name}_00'
            mesh = bpy.data.meshes.new(name)
            bm.to_mesh(mesh)
            hull = bpy.data.objects.new(name, mesh)
            bpy.context.scene.collection.objects.link(hull)
            hull.parent = grip
            hull.hide_render = True
            hull.display_type = 'WIRE'
            hulls.append(hull)
            closed = bool(bm.faces) and all(edge.is_manifold for edge in bm.edges)
            records.append({'name': name, 'render_parent': grip.name,
                            'source_parts': [str(obj['part_id']) for obj in parts],
                            'vertices': len(bm.verts), 'triangles': len(bm.faces),
                            'closed': closed, 'volume_m3': abs(bm.calc_volume())})
            if not closed:
                raise ValueError(f'Convex proxy {name} is not closed')
        finally:
            bm.free()
    return hulls, records


def _remove_temporary(objects, renamed):
    for obj in objects:
        mesh = obj.data if obj.type == 'MESH' else None
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for obj, name in renamed:
        obj.name = name


def _fbx_record(path, objects, kind):
    # Each file is one LOD with multiple parts. Do not emit the shared helper's
    # multi-node screen-size sidecar, which is intended for an FBX LodGroup.
    result = export_fbx(str(path), objects, kind=kind, sidecar=False)
    return {'path': str(path), 'sha256': _digest(path), 'bytes': path.stat().st_size,
            'objects': result['objects'], 'settings': result['settings'],
            'warnings': result['warnings']}


def _glb_json(path):
    with Path(path).open('rb') as stream:
        magic, version, size = struct.unpack('<4sII', stream.read(12))
        if magic != b'glTF' or version != 2 or size != Path(path).stat().st_size:
            raise ValueError(f'Invalid GLB header: {path}')
        chunk_size, chunk_type = struct.unpack('<II', stream.read(8))
        if chunk_type != 0x4E4F534A:
            raise ValueError('GLB does not start with a JSON chunk')
        return json.loads(stream.read(chunk_size))


def _export_glb(path, objects, rig):
    settings = {
        'export_format': 'GLB', 'use_selection': True, 'export_yup': True,
        'export_texcoords': True, 'export_normals': True,
        'export_materials': 'EXPORT', 'export_skins': True,
        'export_animations': False, 'export_cameras': False, 'export_lights': False,
        'export_extras': True, 'export_apply': False,
        'export_rest_position_armature': True, 'export_def_bones': False,
    }
    # The source intentionally uses modifier-only rig attachment. glTF's
    # exporter expects a parent armature and otherwise falls back to a name
    # lookup. Give it an explicit parent for this export, then restore source
    # state in memory. The saved .blend is never changed.
    parent_state = [(obj, obj.parent, obj.parent_type, obj.parent_bone,
                     obj.matrix_parent_inverse.copy(), obj.matrix_world.copy()) for obj in objects]
    try:
        for obj, _parent, _type, _bone, _inverse, world in parent_state:
            obj.parent = rig
            obj.parent_type = 'OBJECT'
            obj.matrix_parent_inverse = rig.matrix_world.inverted()
            obj.matrix_world = world
        bpy.context.view_layer.update()
        with selection([rig] + objects, rig):
            result = bpy.ops.export_scene.gltf(filepath=str(path), **settings)
    finally:
        for obj, parent, parent_type, parent_bone, inverse, world in parent_state:
            obj.parent = parent
            obj.parent_type = parent_type
            obj.parent_bone = parent_bone
            obj.matrix_parent_inverse = inverse
            obj.matrix_world = world
        bpy.context.view_layer.update()
    if 'FINISHED' not in result:
        raise RuntimeError(f'GLB export failed: {result}')
    document = _glb_json(path)
    mesh_nodes = [node.get('name', '') for node in document.get('nodes', []) if 'mesh' in node]
    if len(mesh_nodes) != len(objects) or set(mesh_nodes) != {obj.name for obj in objects}:
        raise ValueError(f'Unexpected render geometry in GLB: {mesh_nodes}')
    images = document.get('images', [])
    embedded = bool(images) and all('bufferView' in image and 'uri' not in image for image in images)
    if not embedded:
        raise ValueError('Textured GLB must contain embedded image data')
    material_records = {}
    for material in document.get('materials', []):
        pbr = material.get('pbrMetallicRoughness', {})
        material_records[material.get('name', '<unnamed>')] = {
            'base_color_texture': 'baseColorTexture' in pbr,
            'metallic_roughness_texture': 'metallicRoughnessTexture' in pbr,
            'normal_texture': 'normalTexture' in material,
            'occlusion_texture': 'occlusionTexture' in material,
        }
    if not material_records or not all(item['base_color_texture'] for item in material_records.values()):
        raise ValueError('Each GLB material must retain its baked base-color texture')
    for obj in objects:
        for material in obj.data.materials:
            principled = next((node for node in material.node_tree.nodes
                               if node.type == 'BSDF_PRINCIPLED'), None)
            if principled is None:
                raise ValueError(f'{material.name}: expected a portable Principled material')
            exported = material_records.get(material.name)
            if exported is None:
                raise ValueError(f'{material.name}: material missing from GLB')
            if principled.inputs['Normal'].is_linked and not exported['normal_texture']:
                raise ValueError(f'{material.name}: connected normal map missing from GLB')
            if (principled.inputs['Roughness'].is_linked or principled.inputs['Metallic'].is_linked
                    ) and not exported['metallic_roughness_texture']:
                raise ValueError(f'{material.name}: connected roughness/metallic maps missing from GLB')
    return {'path': str(path), 'sha256': _digest(path), 'bytes': path.stat().st_size,
            'settings': settings, 'mesh_nodes': mesh_nodes, 'embedded_images': len(images),
            'all_images_embedded': embedded, 'materials': material_records}


def _part_from_name(name, level):
    for prefix in (f'SM_{ASSET}_', f'SK_{ASSET}_'):
        suffix = f'_LOD{level}'
        if name.startswith(prefix) and name.endswith(suffix):
            return name[len(prefix):-len(suffix)]
    raise ValueError(f'Unexpected round-trip render mesh {name}')


def _good_topology(record):
    values = record['topology']
    return all(values[key] == 0 for key in (
        'loose_vertices', 'wire_edges', 'edges_with_over_two_faces',
        'zero_length_edges', 'degenerate_triangles', 'welded_non_manifold_edges'))


def _compare_uvs(source, imported):
    if len(source) != len(imported):
        return False
    for left, right in zip(source, imported):
        if left['triangle_corners'] != right['triangle_corners']:
            return False
        for key in ('min', 'max', 'mean', 'second_moment'):
            if not _close_values(left[key], right[key], UV_TOLERANCE):
                return False
    return True


def _roundtrip(path, level, source, skeleton, skeletal, collision_expected=0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if path.suffix == '.fbx':
        bpy.ops.import_scene.fbx(filepath=str(path), use_anim=False)
    else:
        # Blender 5.2 otherwise creates an extra Icosphere mesh solely for its
        # bone display. It is not part of the GLB. Disable that creation rather
        # than hiding or filtering unrecognized imported render geometry.
        bpy.ops.import_scene.gltf(filepath=str(path), disable_bone_shape=True)
    bpy.context.view_layer.update()
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH'
              and not obj.name.startswith(('UCX_', 'UBX_', 'USP_', 'UCP_'))]
    colliders = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and obj.name.startswith('UCX_')]
    checks = {'rig_count_matches': len(rigs) == (1 if skeletal else 0),
              'collision_proxy_count_matches': len(colliders) == collision_expected}
    rig = rigs[0] if skeletal and len(rigs) == 1 else None
    imported = {}
    for obj in meshes:
        part = _part_from_name(obj.name, level)
        if part in imported:
            raise ValueError(f'Duplicate imported part_id {part}')
        imported[part] = _mesh_record(obj, rig)
    checks['part_set_matches'] = set(imported) == set(source['parts'])
    checks['triangle_count_matches'] = sum(item['triangles'] for item in imported.values()) == source['triangles']
    bounds = _bounds(meshes)
    checks['bounds_and_dimensions_match'] = all(
        _close_values(source['bounds_m'][key], bounds[key], DISTANCE_TOLERANCE)
        for key in ('min', 'max', 'dimensions'))
    per_part = {}
    for part, record in imported.items():
        expected = source['parts'].get(part)
        if expected is None:
            continue
        part_checks = {
            'triangles_match': record['triangles'] == expected['triangles'],
            'material_triangle_counts_match': record['material_triangles'] == expected['material_triangles'],
            'uv_layer_statistics_match': _compare_uvs(expected['uv_layers'], record['uv_layers']),
            'closed_surface_without_loose_or_degenerate_geometry': _good_topology(record),
            'bounds_match': all(_close_values(expected['bounds_m'][key], record['bounds_m'][key],
                                              DISTANCE_TOLERANCE) for key in ('min', 'max', 'dimensions')),
        }
        if skeletal:
            skin = record.get('skin', {})
            part_checks['skin_assignments_match'] = (
                skin.get('triangle_corner_assignments') == expected['skin']['triangle_corner_assignments'])
            part_checks['all_vertices_have_normalized_bone_weights'] = (
                skin.get('unweighted_vertices', 1) == 0 and skin.get('max_influences', 5) <= 4
                and skin.get('max_weight_sum_error', 1) < 1e-6)
        per_part[part] = part_checks
    checks['all_part_checks_pass'] = bool(per_part) and all(all(item.values()) for item in per_part.values())
    imported_skeleton = _skeleton_record(rig) if rig else None
    if skeletal:
        bones = imported_skeleton['bones'] if imported_skeleton else {}
        checks['bone_names_and_count_match'] = set(bones) == set(skeleton['bones'])
        checks['bone_hierarchy_matches'] = bool(bones) and all(
            name in bones and item['parent'] == bones[name]['parent'] for name, item in skeleton['bones'].items())
        checks['bone_rest_heads_match'] = bool(bones) and all(
            name in bones and _close_values(item['head_m'], bones[name]['head_m'], DISTANCE_TOLERANCE)
            for name, item in skeleton['bones'].items())
    collision_records = {obj.name: _topology(obj.data) for obj in colliders}
    checks['collision_proxies_closed'] = all(item['welded_non_manifold_edges'] == 0
                                            for item in collision_records.values())
    return {'passed': all(checks.values()), 'checks': checks, 'part_checks': per_part,
            'meshes': imported, 'bounds_m': bounds, 'skeleton': imported_skeleton,
            'collision_meshes': collision_records,
            'uv_comparison': 'Layer count, corner counts, bounds, first and second moments; not a pixel/render comparison.'}


def export_asset(root, source_path):
    """Export saved source to Exports/BlackNunchucks and return the JSON report.

    Preconditions: three tagged LODs; applied mesh geometry modifiers; UV0/UV1;
    baked material images; normalized bone weights; a rest rig named
    Nunchucks_Rig. Raises on a failed check and preserves the partial report.
    """
    root = Path(root).resolve()
    source_path = Path(source_path).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    output = root / 'Exports' / ASSET
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / 'asset_report.json'
    source_hash = _digest(source_path)
    report = {
        'asset': 'Black Nunchucks', 'status': 'running',
        'source_path': str(source_path), 'source_sha256': source_hash,
        'blender_version': bpy.app.version_string,
        'validation_environment': 'Blender FBX/glTF export and Blender reimport',
        'engine_verified': False, 'gameplay_tested': False,
        'lods': {}, 'roundtrips': {},
        'limits': [
            'Game-engine import, animation playback, collision response and gameplay have not been tested.',
            'Separate FBX files represent the LOD levels; import and assign LODs in the target engine.',
            'Convex handle proxies are geometry suggestions; no rigid-body or chain physics setup is supplied.',
            'UV1 is checked in Blender; target-engine lightmap validation remains pending.',
        ],
    }
    jobs = []
    try:
        bpy.ops.wm.open_mainfile(filepath=str(source_path))
        rig, lods = _source_objects()
        rig.data.pose_position = 'REST'
        bpy.context.view_layer.update()
        report['skeleton'] = _skeleton_record(rig)
        report['materials'] = _materials([obj for objects in lods.values() for obj in objects])
        if not report['materials'] or any(not entry['images'] for entry in report['materials'].values()):
            raise ValueError('All asset materials must have baked image textures')
        qa_results = {}
        for level, objects in lods.items():
            qa_results[str(level)] = qa_check(objects + [rig], require_uv1=True, require_ucx=False,
                                             check_names=True, uv0_tile_range=(0.0, 1.0))
            parts = {str(obj['part_id']): _mesh_record(obj, rig) for obj in objects}
            report['lods'][str(level)] = {'parts': parts,
                'triangles': sum(item['triangles'] for item in parts.values()),
                'bounds_m': _bounds(objects), 'exports': {}}
        report['source_qa_passed'] = all(value['passed'] for value in qa_results.values())
        _write_json(output / 'source_qa.json', qa_results)
        totals = [report['lods'][str(level)]['triangles'] for level in LOD_LEVELS]
        report['lod_triangle_counts_descending'] = all(a > b for a, b in zip(totals, totals[1:]))
        report['source_closed_geometry'] = all(_good_topology(item)
            for lod in report['lods'].values() for item in lod['parts'].values())
        _write_json(report_path, report)
        if not report['source_qa_passed']:
            failures = [f"LOD{level} {item['object']} {item['name']}: {item['detail']}"
                        for level, result in qa_results.items() for item in result['checks'] if not item['passed']]
            raise ValueError('Source QA failed: ' + '; '.join(failures[:12]))
        if not report['source_closed_geometry'] or not report['lod_triangle_counts_descending']:
            raise ValueError('Source must have closed clean geometry and decreasing total LOD triangles')
        for level, objects in lods.items():
            lod = report['lods'][str(level)]
            static_path = output / f'SM_{ASSET}_LOD{level}.fbx'
            copies, renamed = _static_copies(objects)
            hulls = []
            try:
                hulls, collision = _collision_hulls(copies)
                lod['collision'] = collision
                lod['exports']['static_fbx'] = _fbx_record(static_path, copies + hulls, 'static')
            finally:
                _remove_temporary(hulls + copies, renamed)
            jobs.append((static_path, level, False, len(hulls)))
            skeletal_path = output / f'SK_{ASSET}_LOD{level}.fbx'
            original_names = [(obj, obj.name) for obj in objects]
            try:
                for obj, name in original_names:
                    obj.name = name.replace('SM_', 'SK_', 1)
                lod['exports']['skeletal_fbx'] = _fbx_record(skeletal_path, [rig] + objects, 'skeletal')
            finally:
                for obj, name in original_names:
                    obj.name = name
            jobs.append((skeletal_path, level, True, 0))
            if level == 0:
                glb_path = output / f'SM_{ASSET}_LOD0.glb'
                lod['exports']['glb'] = _export_glb(glb_path, objects, rig)
                jobs.append((glb_path, level, True, 0))
            _write_json(report_path, report)
            print(f'BLACK_NUNCHUCKS_EXPORTED_LOD {level} {lod["triangles"]}', flush=True)
        for path, level, skeletal, collision_count in jobs:
            result = _roundtrip(path, level, report['lods'][str(level)], report['skeleton'],
                                skeletal, collision_count)
            report['roundtrips'][path.name] = result
            _write_json(report_path, report)
            if not result['passed']:
                failed = [key for key, value in result['checks'].items() if not value]
                raise ValueError(f'{path.name} round-trip checks failed: {failed}')
            print(f'BLACK_NUNCHUCKS_ROUNDTRIP_PASSED {path.name}', flush=True)
        report['source_unchanged'] = _digest(source_path) == source_hash
        if not report['source_unchanged']:
            raise ValueError('Source file hash changed during export')
        report['status'] = 'passed'
        report['files'] = {str(path.relative_to(output)): _digest(path)
                           for path in output.rglob('*') if path.is_file()
                           and path.suffix.lower() in {'.fbx', '.glb', '.png'}}
        return report
    except Exception as exc:
        report['status'] = 'failed'
        report['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        report['source_unchanged'] = source_path.is_file() and _digest(source_path) == source_hash
        _write_json(report_path, report)
        bpy.ops.wm.open_mainfile(filepath=str(source_path))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--source', type=Path)
    arguments = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    result = export_asset(arguments.root, arguments.source or arguments.root / 'Assets' / 'BlackNunchucks.blend')
    print('BLACK_NUNCHUCKS_EXPORT_VALIDATION_PASSED', result['source_sha256'], flush=True)
