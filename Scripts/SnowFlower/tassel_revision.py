"""Reference-directed Snow Flower cord, charm and tassel geometry.

Exec this file in build_snow_flower.py's globals before component assembly.
All dimensions are metres.  Hanging direction is local +Z.
"""

_sf_group = '06_Tassel'

def _sf_braided_cord(name, path, outer=.00175, turns=29):
    """A covered core and three twisted strands; each shell is capped."""
    path = [Vector(p) for p in path]
    tube(name + '_Core', path, outer * .68, 'Silk', _sf_group, 8)
    for strand in range(3):
        strand_points = []
        for j, p in enumerate(path):
            tangent = (path[min(j + 1, len(path) - 1)] - path[max(0, j - 1)]).normalized()
            across = tangent.cross(Vector((0, 1, 0))).normalized()
            depth = tangent.cross(across).normalized()
            angle = math.tau * (turns * j / (len(path) - 1) + strand / 3)
            strand_points.append(p + outer * .58 * (across * math.cos(angle) + depth * math.sin(angle)))
        tube(name + '_Braid', strand_points, outer * .39, 'Silk', _sf_group, 5)


# The reference ties the cord to the pommel's side, then lets it fall in a
# nearly straight, slightly outward diagonal. Avoid unsupported large beads.
_sf_cord = bezier([(-.018, 0, -.151), (-.030, 0, -.152),
                   (-.040, .001, -.077), (-.050, .001, -.038)], 244)
_sf_braided_cord('SF_Tassel_Cord', _sf_cord, .0017, 42)

# Three close wrapped knots at the pommel attachment, with an underpassing
# diagonal return so they read as tied rope rather than a string of spheres.
for _sf_k in range(3):
    _sf_z = -.136 + _sf_k * .0062
    _sf_x = -.0285 - _sf_k * .0016
    _sf_path = []
    for _sf_j in range(65):
        _sf_t = _sf_j / 64
        _sf_a = math.tau * 2.15 * _sf_t
        _sf_path.append((_sf_x + .0026 * math.cos(_sf_a),
                         .0026 * math.sin(_sf_a),
                         _sf_z - .002 + .004 * _sf_t))
    tube('SF_Tassel_AttachmentKnots', _sf_path, .00105, 'Silk', _sf_group, 6)
    tube('SF_Tassel_KnotCrossing',
         [(_sf_x-.002, -.0027, _sf_z-.0021),
          (_sf_x, -.0032, _sf_z),
          (_sf_x+.002, -.0027, _sf_z+.0021)], .0007, 'Silk', _sf_group, 6)

# Slim eyelets connect the hanging blossom at both ends.
for _sf_cx, _sf_cz in [(-.0505, -.037), (-.057, -.0115)]:
    tube('SF_Tassel_CharmEyelets',
         [(_sf_cx + .0015 * math.cos(math.tau*j/28), 0,
           _sf_cz + .00235 * math.sin(math.tau*j/28)) for j in range(28)],
         .00043, 'Silver', _sf_group, 6, True)

# A fine pointed backing gives the pendant the layered, sharply cut outline
# seen in the sheet; the front and rear flowers supply the scalloped petals.
_sf_charm = Vector((-.054, 0, -.024))
for _sf_k in range(5):
    _sf_a = .18 + math.tau*_sf_k/5
    _sf_r = Vector((math.cos(_sf_a), 0, math.sin(_sf_a)))
    _sf_tan = Vector((-math.sin(_sf_a), 0, math.cos(_sf_a)))
    _sf_outline = [_sf_charm + _sf_r*.0035 - _sf_tan*.0018,
                   _sf_charm + _sf_r*.0088 - _sf_tan*.0033,
                   _sf_charm + _sf_r*.0137,
                   _sf_charm + _sf_r*.0088 + _sf_tan*.0033,
                   _sf_charm + _sf_r*.0035 + _sf_tan*.0018]
    _sf_vs = [p+Vector((0,y,0)) for y in (-.00065,.00065) for p in _sf_outline]
    _sf_fs = [tuple(reversed(range(5))), tuple(range(5,10))]
    _sf_fs += [(j,(j+1)%5,(j+1)%5+5,j+5) for j in range(5)]
    add('SF_Tassel_CharmBacking','Silver',_sf_group,_sf_vs,_sf_fs)
for _sf_side in (-1,1):
    flower('SF_Tassel_FlowerCharm',(-.054,_sf_side*.00095,-.024),
           .0114,(0,_sf_side,0),.18,_sf_group,True)

_sf_braided_cord('SF_Tassel_LowerCord',
                 bezier([(-.057,0,-.0115),(-.059,0,-.0075),
                         (-.062,0,-.004),(-.063,0,.0005)],48), .0013, 8)

# Oval black bead, gathered dark cap and three close silver binding rings.
ellipsoid('SF_Tassel_Bead',(-.063,0,.0058),(.0056,0,0),(0,.0048,0),
          (-.0015,0,.0080),'Recess',_sf_group,24,12)
ellipsoid('SF_Tassel_GatheredCap',(-.065,0,.016),(.0065,0,0),(0,.0058,0),
          (-.0005,0,.0041),'Recess',_sf_group,24,10)
for _sf_z in (.0126,.0156,.0186):
    _sf_x = -.064 - (_sf_z-.0126)*.17
    tube('SF_Tassel_SilverCap',
         [(_sf_x+.00625*math.cos(math.tau*j/48),
           .00575*math.sin(math.tau*j/48),_sf_z) for j in range(48)],
         .00032,'Silver',_sf_group,6,True)
for _sf_k in range(12):
    _sf_a = math.tau*_sf_k/12
    tube('SF_Tassel_CapEngraving',
         [(-.0645+.0063*math.cos(_sf_a+.20*t),
           .0058*math.sin(_sf_a+.20*t),.013+.005*t)
          for t in (0,.25,.5,.75,1)],.00014,'Silver',_sf_group,4)

def _sf_bundle_shape(t, angle, radial=1):
    # The bottom is a filled, softly flared oval, not a sparse wire fringe.
    r = .00555 + .0088 * (1-math.exp(-2.8*t))/(1-math.exp(-2.8))
    x = -.065 - .027*t - .0030*math.sin(math.pi*t) + radial*r*math.cos(angle)
    y = radial*r*.72*math.sin(angle)
    # End approximately perpendicular to the curved hanging direction.
    z = .0188 + .103*t + .0033*math.cos(angle)*t**7
    return Vector((x,y,z))

# Closed finely fluted core preserves silk mass between visible filaments and
# also preserves the reference silhouette when strands are reduced in LODs.
_sf_vs=[];_sf_fs=[];_sf_sides=144;_sf_rows=19
for _sf_j in range(_sf_rows):
    _sf_u=_sf_j/(_sf_rows-1)
    for _sf_k in range(_sf_sides):
        _sf_a=math.tau*_sf_k/_sf_sides
        # Stop the solid interior several millimetres above individual tips;
        # soften its edge with short clustered variations under the fibres.
        _sf_core_u=_sf_u*(.947+.008*math.sin(_sf_a*11)+.006*math.sin(_sf_a*23))
        _sf_core_r=(.936+.022*math.cos(_sf_a*72))*(1-.13*_sf_u**12)
        _sf_vs.append(_sf_bundle_shape(_sf_core_u,_sf_a,_sf_core_r))
for _sf_j in range(_sf_rows-1):
    for _sf_k in range(_sf_sides):
        _sf_kn=(_sf_k+1)%_sf_sides
        _sf_fs.append((_sf_j*_sf_sides+_sf_k,(_sf_j+1)*_sf_sides+_sf_k,
                       (_sf_j+1)*_sf_sides+_sf_kn,_sf_j*_sf_sides+_sf_kn))
_sf_fs.extend([tuple(reversed(range(_sf_sides))),
               tuple((_sf_rows-1)*_sf_sides+k for k in range(_sf_sides))])
add('SF_Tassel_FilledSilkBundle','Silk',_sf_group,_sf_vs,_sf_fs)

# The independently capped outer strands give the smooth black silk its fine
# longitudinal highlight. 180 components, 19 rings, five vertices per ring.
# They are intentionally confined to the outside so they survive export UVs.
for _sf_i in range(180):
    _sf_a=math.tau*(_sf_i+.25)/180
    _sf_points=[]
    _sf_phase=rng.random()*math.tau
    _sf_extension=rng.uniform(-.0011,.0022)+.0006*math.sin(_sf_a*17)
    for _sf_j in range(19):
        _sf_u=_sf_j/18
        _sf_radial=1.008+.012*math.sin(_sf_a*13)+.014*math.sin(_sf_u*5+_sf_phase)*_sf_u**2
        _sf_p=_sf_bundle_shape(_sf_u,_sf_a+.009*math.sin(_sf_u*5+_sf_phase),_sf_radial)
        _sf_p.z+=_sf_extension*_sf_u**6
        _sf_points.append(_sf_p)
    tube('SF_Tassel_Strands',_sf_points,
         lambda t:(.00024+.00009*t)*(1-.40*t**10),'Silk',_sf_group,5)

# Scattered fine loose fibres break the machine-straight outline without
# making the bundle look frayed or pushing it below the guard.
for _sf_i in range(32):
    _sf_a=math.tau*(_sf_i+.33)/32
    _sf_phase=rng.random()*math.tau
    _sf_points=[]
    _sf_extension=rng.uniform(-.0014,.0015)
    for _sf_j in range(19):
        _sf_u=_sf_j/18
        _sf_loosen=.024*math.sin(math.pi*_sf_u)+.055*_sf_u**4
        _sf_p=_sf_bundle_shape(_sf_u,_sf_a+.015*math.sin(_sf_phase+_sf_u*6),1.012+_sf_loosen)
        _sf_p.x+=.00023*math.sin(_sf_phase+_sf_u*8)*_sf_u**2
        _sf_p.z+=_sf_extension*_sf_u**5
        _sf_points.append(_sf_p)
    tube('SF_Tassel_LooseFibers',_sf_points,lambda t:.00015*(1-.53*t**7),'Silk',_sf_group,5)

# Data for deterministic LOD selection in the consolidated export mesh.
SF_TASSEL_STRAND_METADATA={
    'name':'SF_Tassel_Strands','components':180,'vertices_per_component':95,
    'rings_per_component':19,'vertices_per_ring':5,
    'component_min_z_range':(.0184,.0192),
    'component_max_z_range':(.1168,.1278),
    'component_x_range':(-.1085,-.058),
    'filled_core':'SF_Tassel_FilledSilkBundle',
    'loose_fiber_component':'SF_Tassel_LooseFibers',
    'loose_fiber_components':32,
    'note':'Retain the filled core; reduce only strand components. No radius inflation required.'
}
