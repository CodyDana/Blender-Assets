# t7 (exec'd by compose_t7.py): compare_tacks.png, compare_skirt.png, compare_ring.png. Every number on the sheets is
# read from the final build's files (measure_t7.json, ../measure.json), none typed in (judge r6 item 6).
_m7 = json.loads((HERE / "measure_t7.json").read_text(encoding="utf-8"))
_mb = json.loads((HERE.parent / "measure.json").read_text(encoding="utf-8"))["summary"]
_r0 = _m7["rows"]["head+X_row0_body_side"]
_tk = "%d tacks per row, %.1f mm, rows %.1f mm apart (%.2f d), x %.4f design scale" % (
    _r0["tacks"], _r0["visible_equator_diameter_mm_min_max"][0], _m7["head+X"]["row_spacing_axial_mm"],
    _m7["head+X"]["row_spacing_over_visible_d"], _mb["t6_design_scale"])
ours = flat(HERE / "drum_front_standing_photo.png")
band_p = flat(HERE / "closeup_tack_band_photo.png")
band_s = flat(HERE / "closeup_tack_band.png")
W = 2000
im = Image.new("RGB", (W, 1960), "white")
d = ImageDraw.Draw(im)
top = 40
im.paste(ref.resize((760, 760), Image.LANCZOS), (10, top))
im.paste(ours.resize((760, 760), Image.LANCZOS), (800, top))
d.text((10, 8), "REFERENCE (user photo)", fill="black", font=F)
d.text((800, 8), "OURS t7: " + _tk + "; +Y handle side (photo-studio light)", fill="black", font=FS)
y = top + 780
im.paste(ref.crop((300, 150, 700, 330)).resize((990, 446), Image.LANCZOS), (10, y + 30))
d.text((10, y), "reference tack band (crop)", fill="black", font=F)
im.paste(band_p.crop((0, 120, 1200, 660)).resize((990, 446), Image.LANCZOS), (1005, y + 30))
d.text((1005, y), "ours t7: tack band close-up (photo-studio light)", fill="black", font=F)
y2 = y + 500
im.paste(band_s.crop((0, 120, 1200, 660)).resize((990, 446), Image.LANCZOS), (1005, y2 + 30))
d.text((1005, y2), "ours t7: same close-up, review-studio light", fill="black", font=F)
im.paste(flat(T3 / "closeup_tack_band_photo.png").crop((0, 120, 1200, 660)).resize((990, 446), Image.LANCZOS),
         (10, y2 + 30))
_t6 = json.loads((T3 / "measure_t6.json").read_text(encoding="utf-8"))
d.text((10, y2), "before (t6): %d per row, %.1f mm, rows %.1f mm apart (photo-studio light)" % (
    _t6["rows"]["head+X_row0_body_side"]["tacks"], _t6["rows"]["head+X_row0_body_side"]["visible_equator_diameter_mm_min_max"][0],
    _t6["head+X"]["row_spacing_axial_mm"]), fill="black", font=F)
im = im.crop((0, 0, W, y2 + 30 + 446 + 10))
im.save(HERE / "compare_tacks.png")
print("saved compare_tacks.png", im.size)
# the skirt sheet: the photo's upper skirt vs ours from 18 deg above (closeup_skirt), photo-studio and review light
sk_p = flat(HERE / "closeup_skirt_photo.png")
sk_s = flat(HERE / "closeup_skirt.png")
sk_4 = flat(T3 / "closeup_skirt_photo.png")
_ft = _mb["flap_tabs"]
_up = _ft["1"] if "1" in _ft else _ft[1]
S2 = Image.new("RGB", (2000, 1500), "white")
d2 = ImageDraw.Draw(S2)
d2.text((10, 8), "reference: the upper skirt (crop of the user's photo)", fill="black", font=F)
S2.paste(ref.crop((110, 140, 910, 340)).resize((1980, 495), Image.LANCZOS), (10, 36))
d2.text((10, 545), "ours t7: traced from the photo, %d lobes, open V slits %s mm, rolled lip r %.0f mm (design; photo light)" % (
    _up["lobes"], _up["slit_width_at_lip_design_mm_min_max"], _up["rho_design_mm"]), fill="black", font=FS)
S2.paste(sk_p.crop((0, 60, 1200, 560)).resize((985, 410), Image.LANCZOS), (10, 575))
S2.paste(sk_s.crop((0, 60, 1200, 560)).resize((985, 410), Image.LANCZOS), (1005, 575))
d2.text((1005, 545), "ours t7, review-studio light", fill="black", font=F)
d2.text((10, 1000), "before (t6): the parametric skirt (photo-studio light)", fill="black", font=F)
S2.paste(sk_4.crop((0, 60, 1200, 560)).resize((985, 410), Image.LANCZOS), (10, 1030))
S2.paste(flat(HERE / "silhouette_ours_refcam_photo.png").crop((100, 350, 940, 560)).resize((985, 246), Image.LANCZOS),
         (1005, 1030))
d2.text((1005, 1000), "ours t7 from the photo's fitted camera (photo light), same crop as the top", fill="black", font=FS)
S2 = S2.crop((0, 0, 2000, 1450))
S2.save(HERE / "compare_skirt.png")
print("saved compare_skirt.png", S2.size)
# t7: the ring hardware: the photo crop (u 385-665, v 475-740) at 3x and ours from the same fitted camera at 3x
_hw = _m7["t7_ring_hardware"]["+Y"]
rc = flat(HERE / "ring_closeup_photo.png")
rr = ref.crop((385, 475, 665, 740)).resize(rc.size, Image.LANCZOS)
lay = flat(HERE / "ring_layout.png")
S3 = Image.new("RGB", (2 * rc.width + 30, rc.height + 60 + 40 + 560), "white")
d3 = ImageDraw.Draw(S3)
d3.text((10, 10), "reference: the ring handle (photo crop, 3x)", fill="black", font=F)
d3.text((rc.width + 30, 10), "ours t7: the same camera at 3x (photo-studio light), +Y handle", fill="black", font=F)
S3.paste(rr, (10, 50))
S3.paste(rc, (rc.width + 20, 50))
yy = rc.height + 70
d3.text((10, yy), "ours t7 in the stand (drum lying): the ring hangs in a vertical plane, resting on the washer rim; "
        "ring to washer %.2f mm, to plate %.2f mm, to barrel %.2f mm; intersecting pairs %s" % (
            _hw["ring_min_distance_mm"].get("washer", -1), _hw["ring_min_distance_mm"].get("plate", -1),
            _hw["ring_min_distance_mm"].get("barrel", -1), sum(_hw["ring_intersecting_triangle_pairs"].values())),
        fill="black", font=FS)
S3.paste(lay.resize((840, 560), Image.LANCZOS), (10, yy + 30))
tc = flat(HERE / "tack_closeup.png")
S3.paste(tc.resize((840, 560), Image.LANCZOS), (870, yy + 30))
d3.rectangle((875, yy + 35, 1690, yy + 62), fill="white")
d3.text((880, yy + 38), "tack macro (camera about 0.6 m): 16-sided domes, 2 rings, smooth normals (%d triangles each)" % (
    _mb["tack_tris_each"]), fill="black", font=FS)
S3.save(HERE / "compare_ring.png")
print("saved compare_ring.png", S3.size)
