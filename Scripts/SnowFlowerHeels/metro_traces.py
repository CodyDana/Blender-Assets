"""Hand traces of the Snow Flower heels reference (reference pixels, x right, y down, origin top-left of
References/SnowFlowerHeels/snowflowerheels_reference.png, 1254x1254). View A = front/left shoe (hero, larger),
view B = rear/right shoe. kind: outline (closed polygon), polyline (open), centerline (open, with width_px),
point (with d_px), points (several centres).
Traced by eye on 2-5x zooms with a labelled grid, then checked by overlay (metro_overlay.py). Typical accuracy 1-3 px
for edges and landmarks, 3-6 px for the dense counter ornament envelopes."""
T = {}


def add(view, name, kind, pts, **kw):
    T[view + "." + name] = dict(view=view, kind=kind, pts=[[float(p[0]), float(p[1])] for p in pts], **kw)


# ---------------- VIEW A : heel counter ornament ----------------
add("A", "crest_spike", "outline", [(118,8),(124,14),(135,35),(145,60),(152,85),(157,110),(160,135),(159,160),(155,178),(148,193),(138,196),(126,184),(113,160),(104,135),(100,110),(103,90),(106,65),(110,38),(113,18)],
    layer=4, material="silver", note="tall pointed leaf plate = top end of the front branch band; silver rim + dark recessed lens (crest_spike_inset); tip stands above the collar")
add("A", "crest_spike_inset", "outline", [(119,30),(128,50),(138,75),(146,105),(148,135),(145,160),(140,175),(133,160),(125,135),(119,105),(116,75),(116,50)], layer=4, material="recess_dark")
add("A", "front_branch_band", "centerline", [(140,196),(137,230),(136,270),(136,320),(134,370),(130,420),(124,470),(119,520),(118,560),(122,585),(114,603),(104,625),(100,660),(97,700),(96,750),(95,800),(95,850),(97,880)],
    width_px=[14,14,14,15,15,15,14,13,13,12,12,14,16,17,17,17,17,15], layer=3, material="silver",
    note="main S-curved silver band: rises from the top-lift up the back of the stiletto, follows the front edge of the counter (edge of the open side) and ends in the crest spike")
add("A", "rear_c_band", "centerline", [(95,268),(75,278),(55,295),(38,320),(27,350),(22,380),(22,410),(28,440),(40,470),(52,500),(62,530),(68,555)], width_px=7, layer=3, material="silver",
    note="C-shaped branch framing the leather medallion on the counter back; carries leaf spurs")
add("A", "rear_leaf_spur", "outline", [(10,371),(20,355),(30,345),(33,352),(26,368),(18,380)], layer=3, material="silver", note="leaf spur on the C-band; rearmost silhouette point (x=10, y~371)")
add("A", "sickle_plate_1", "centerline", [(80,125),(75,145),(78,170),(88,195),(100,220),(110,245),(117,270)], width_px=11, layer=3, material="silver", note="upper sickle lame below the crest spike, knob at top (77,125), point sweeps down-forward")
add("A", "sickle_plate_2", "centerline", [(62,190),(53,215),(48,245),(50,275),(58,300)], width_px=10, layer=3, material="silver", note="rear lame along the counter-back silhouette")
add("A", "medallion_leather", "outline", [(85,285),(100,300),(115,330),(122,370),(120,420),(110,455),(92,470),(70,462),(52,430),(45,390),(48,345),(60,305)], layer=2, material="leather_crackle",
    note="bulging oval of crackle-grain leather on the counter back, framed by the C-band (rear) and the front band")
add("A", "medallion_leaf", "outline", [(53,377),(55,355),(60,338),(65,333),(66,352),(61,370)], layer=3, material="silver")
add("A", "medallion_bud", "point", [(85,447)], d_px=16, layer=3, material="silver+pearl")
add("A", "counter_blossom", "point", [(72,575)], d_px=38, layer=5, material="pearl", note="five-petal blossom low on the counter back where the C-band meets the front band, over leaf plates")
add("A", "counter_low_leaves", "outline", [(40,480),(60,500),(85,530),(105,560),(110,590),(95,600),(75,598),(55,585),(45,560),(40,520)], layer=3, material="silver", note="cluster of pointed leaf plates around the counter blossom (envelope only)")
add("A", "heel_thorn_1", "outline", [(83,718),(90,708),(95,715),(90,730)], layer=4, material="silver", note="thorn on the stiletto band, points back")
add("A", "heel_diamond", "outline", [(88,797),(95,812),(94,840),(88,853),(83,835),(83,812)], layer=4, material="silver", note="elongated diamond boss on the stiletto band")
# ---------------- VIEW A : heel / stiletto ----------------
add("A", "stiletto_outline", "outline", [(73,600),(80,640),(83,680),(86,720),(87,760),(88,800),(86,840),(84,884),(84,905),(107,917),(139,908),(139,890),(140,850),(142,800),(144,760),(147,700),(150,660),(155,630),(163,610),(172,600)],
    layer=1, material="stiletto_black+silver_band", note="stiletto incl. top-lift; front edge = heel-breast curve into the sole")
add("A", "toplift", "outline", [(84,885),(84,905),(107,917),(139,908),(139,888),(107,894)], layer=1, material="toplift_black", note="top-lift block ~23 px tall; bottom corners give the camera elevation")
# ---------------- VIEW A : far (closed) side interior + collar ----------------
add("A", "far_panel_topline", "polyline", [(155,60),(157,38),(163,29),(171,26),(185,30),(220,45),(255,65),(275,80),(283,95),(283,140),(284,200),(292,260),(305,300),(330,380),(350,450),(358,500),(355,555),(362,590),(380,660),(402,727),(450,745),(520,775),(580,800),(620,815)],
    layer=0, material="leather_lining", note="top edge of the closed (far) side: high collar at the back, falls to the throat; stitched binding ~5 px inside the edge")
# ---------------- VIEW A : ankle strap + buckle ----------------
add("A", "strap_far_run", "outline", [(270,140),(300,146),(350,165),(400,185),(440,202),(462,215),(470,228),(430,229),(383,230),(330,205),(290,190)], layer=6, material="strap_leather", note="strap run coming from the far side over the front of the ankle")
add("A", "strap_near_run", "outline", [(262,212),(300,219),(350,226),(400,229),(450,228),(468,230),(472,255),(467,277),(450,275),(400,270),(350,265),(300,258),(262,252)], layer=7, material="strap_leather", note="strap run on the visible side, from the fold at the ankle front back to the buckle; edge stitching on both edges")
add("A", "strap_fold", "point", [(470,248)], d_px=45, layer=7, note="U-fold / loop end of the strap at the front of the ankle")
add("A", "buckle_blossom", "point", [(201,221)], d_px=51, layer=9, material="pearl", note="five-petal blossom, pearl petals, silver stamen boss")
add("A", "buckle_hex_frame", "outline", [(200,177),(222,192),(216,257),(200,265),(184,247),(186,186)], layer=8, material="silver", note="open pointed-hex frame (bar ~5 px) behind the blossom, long axis near-vertical")
add("A", "buckle_left_diamond", "outline", [(150,201),(170,186),(178,212),(164,236)], layer=8, material="silver", note="open diamond frame, dark centre, points back toward the counter")
add("A", "buckle_right_diamond", "outline", [(239,205),(259,234),(235,254),(226,227)], layer=8, material="silver", note="open diamond frame with a small silver pin inside (the buckle tongue)")
add("A", "strap_stud", "outline", [(290,240),(304,231),(326,249),(302,256)], layer=8, material="silver", note="pyramidal diamond stud on the strap, long axis along the strap")
# ---------------- VIEW A : insole ----------------
add("A", "insole_emblem", "outline", [(163,405),(220,446),(248,535),(168,450)], layer=0, material="insole_print_silver", note="elongated kite emblem with an inner kite, a centre spine and chevrons; blunt end toward the heel")
add("A", "insole_emblem_inner", "outline", [(182,428),(212,452),(232,512),(186,457)], layer=0, material="insole_print_silver")
add("A", "insole_branch_stem", "polyline", [(245,540),(258,560),(270,578),(282,595),(293,612),(303,630),(310,650),(313,670),(312,690),(308,710),(302,730),(297,750),(292,770),(290,790),(292,810)], layer=0, material="insole_print_silver", note="printed branch running from the emblem toward the toe")
add("A", "insole_blossom_1", "point", [(345,737)], d_px=48, layer=0, material="insole_print_pearl")
add("A", "insole_blossom_2", "point", [(300,812)], d_px=55, layer=0, material="insole_print_pearl")
add("A", "insole_buds", "points", [(237,545),(247,577),(282,570),(287,617),(318,640),(303,677),(323,698),(302,717),(283,727),(277,760),(373,790)], d_px=12, layer=0, material="insole_print_pearl", note="approximate bud centres along the printed branch")
# ---------------- VIEW A : vamp ----------------
add("A", "topline_piping", "centerline", [(205,745),(225,768),(245,790),(280,820),(330,850),(380,870),(430,880),(480,879),(530,875),(575,874),(612,878)], width_px=7, layer=3, material="silver", note="silver piping on the vamp topline of the open side, runs into the toe plate")
add("A", "vine_frame_upper", "centerline", [(268,1005),(280,1000),(310,975),(345,955),(380,940),(410,925),(440,915),(460,910),(490,902),(520,897),(548,892)], width_px=5, layer=3, material="silver", note="upper arc of the pointed-oval vine frame on the vamp side; merges into the toe plate's rear arm")
add("A", "vine_frame_back", "centerline", [(287,827),(300,850),(305,870),(307,900),(303,930),(297,960),(285,990),(268,1005)], width_px=5, layer=3, material="silver", note="branch dropping from the piping to the frame's rear corner")
add("A", "vine_frame_lower", "centerline", [(268,1005),(275,1010),(300,1030),(330,1040),(380,1050),(400,1052),(440,1040),(490,1013),(500,985)], width_px=5, layer=3, material="silver", note="lower arc of the frame, rises to the vamp blossom")
add("A", "vine_frame_corner", "point", [(268,1006)], d_px=14, layer=4, material="silver", note="pointed rear corner of the frame (V join with a small thorn plate)")
add("A", "vine_lower_run", "centerline", [(500,983),(520,1000),(545,1008),(585,1015),(620,1030),(645,1060),(655,1070),(685,1100),(700,1110)], width_px=5, layer=3, material="silver", note="vine from the vamp blossom along the lower vamp to the toe frame's near rail")
add("A", "vine_thorns", "points", [(372,910),(477,910),(652,1070)], d_px=10, layer=4, material="silver", note="small pointed diamond thorns on the vine")
add("A", "vamp_blossom", "point", [(475,955)], d_px=68, layer=5, material="pearl", note="largest blossom, on the vamp side inside the vine frame (NOT present in view B)")
add("A", "vamp_buds", "points", [(410,940),(532,933),(563,1000),(577,982),(513,1010),(590,1055),(633,1020)], d_px=16, layer=5, material="pearl+silver", note="closed buds on short silver stems")
# ---------------- VIEW A : toe ----------------
add("A", "toe_apex_spike", "outline", [(625,818),(632,830),(645,850),(655,870),(660,885),(645,885),(628,880),(610,878),(603,870),(610,850),(618,832)], layer=6, material="silver", note="upright pointed leaf plate at the throat, dark recessed lens, tip stands proud of the topline")
add("A", "toe_blossom", "point", [(672,913)], d_px=64, layer=7, material="pearl")
add("A", "toe_rear_arm", "outline", [(550,888),(585,890),(620,898),(640,908),(620,910),(585,900)], layer=6, material="silver", note="long pointed bar pointing back along the topline (left of the toe blossom)")
add("A", "toe_keystone", "outline", [(668,948),(687,940),(700,968),(705,978),(662,984)], layer=6, material="silver", note="pointed diamond plate under the blossom where the two rails of the toe frame meet")
add("A", "toe_frame_far_rail", "centerline", [(665,895),(690,915),(720,945),(755,980),(790,1020),(820,1060),(845,1100),(860,1140),(867,1165)], width_px=12, layer=6, material="silver", note="outer rail along the far/top edge of the toe to the tip; inward thorns near (805,1090) and (773,1027)")
add("A", "toe_frame_near_rail", "centerline", [(683,985),(689,1030),(692,1065),(702,1095),(715,1118),(760,1132),(833,1146),(860,1160),(867,1167)], width_px=8, layer=6, material="silver", note="inner rail framing the toe cap on the visible side and along the sole line")
add("A", "toe_cap", "outline", [(697,983),(690,1000),(689,1033),(692,1060),(700,1090),(713,1112),(740,1125),(790,1136),(833,1145),(850,1152),(840,1135),(827,1117),(810,1097),(800,1077),(790,1050),(770,1027),(743,1003),(715,988)], layer=5, material="toecap_gloss",
    note="glossy black (patent) toe cap inside the frame; strong specular triangle ~ (685-770, 1000-1075)")
add("A", "toe_tip", "point", [(869,1172)], d_px=4, note="silhouette extreme along the heel->toe direction; silver-capped")
for n, p in {"toplift_front_corner": (107.4,917.3), "toplift_left_corner": (83.6,905.6), "toplift_right_corner": (139.5,907.8)}.items():
    add("A", n, "point", [p])

# ---------------- VIEW B : landmarks (registration + cross-check) ----------------
for n, p in {"toe_tip": (1234,1027), "toplift_front_corner": (633.6,792.3), "toplift_left_corner": (611.1,783.3), "toplift_right_corner": (655.5,785.1),
             "crest_spike_tip": (686,37), "buckle_blossom": (750,230), "strap_stud": (835,249), "strap_fold": (1013,263), "toe_apex_spike_tip": (1062,743),
             "toe_blossom": (1095,832), "insole_emblem_top": (720,427), "insole_emblem_bottom": (792,523), "insole_blossom": (857,730), "vamp_frame_notch": (950,820),
             "vamp_bud": (938,893)}.items():
    add("B", n, "point", [p])
