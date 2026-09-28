# Black nunchucks reference landmarks

Source: `C:/Users/Cody/Downloads/nunchucks.png`; 1254 × 1254 pixels. Coordinates use the top-left image origin, x right, y down. Measurements are visual estimates, normally ±3 px; hidden hardware dimensions are not recoverable from this image.

## Handle geometry

Silhouette-fitted grip axes (fit over y = 350–1100, dark-object threshold):

- Left: `x = 506.261 - 0.213000*y`, leaning left by 12.02° from vertical.
- Right: `x = 728.927 + 0.223323*y`, leaning right by 12.59° from vertical.

| Landmark | Left (x,y) | Right (x,y) |
|---|---:|---:|
| Top cap plane center on fitted axis | (464.5,196) | (772.7,196) |
| Steel/black seam center | (444.1,292) | (794.1,292) |
| Body axis at start of rounded heel | (263.4,1140) | (983.5,1140) |
| Approximate bottom end-plane center | (258,1165) | (989,1165) |
| Approximate lowest visible silhouette point | (284,1192) | (960,1194) |

- Both handles are very long circular-section bodies, subtly wider toward the heel. Their image length from cap center to heel is about 992 px; about 1010 px including the outermost rounded silhouette.
- Brushed steel caps: bounding boxes approximately left `(391,181)–(519,305)`, right `(720,181)–(850,306)`; actual diameter perpendicular to axis about 110–112 px and axial length 99–102 px. Cap edges have a small bevel. Black/steel seam follows an oblique elliptical edge, not a horizontal cut in image coordinates.
- Steel/black seam left approximate edge points `(391,280)` and `(499,304)`; right `(739,304)` and `(847,280)`.
- Grip cross-section diameter perpendicular to the axis grows from approximately 113 px near the top to 136–139 px above the bottom, approximately 20% flare. The silhouettes are nearly straight and the taper is gentle.
- Bottom heels are rounded corners on a cylinder, approximately 25–32 px corner radius. They are not hemispheres. A narrow, dark inset/edge line is visible around the last few pixels of the heel. Contact shadows are pale and soft.

Measured horizontal dark silhouette extents (perpendicular diameters are about 0.977 times these horizontal widths):

| y | Left x extents | Right x extents |
|---:|---:|---:|
| 310 | 382–499 | 739–855 |
| 500 | 337–462 | 778–903 |
| 700 | 292–422 | 821–951 |
| 900 | 247–382 | 862–998 |
| 1100 | 203–341 | 903–1045 |
| 1140 | 195–333 | 912–1052 |

## Chain and attachments

There are **seven free oval chain links**, with one additional fixed attachment eye/loop emerging from each steel cap. Some of the end link and eye surfaces overlap. Do not count the rear bar of the central link as a separate eighth link.

Angles below are major-axis angles in screen coordinates, with horizontal = 0° and increasing angles clockwise; orientations are modulo 180°. The source has a near mirror-symmetric inverted-U chain.

| Link, from left to right | Approx. center (x,y) | Major axis | Approx. projected outer size | Presentation |
|---|---:|---:|---:|---|
| 1, above left cap | (477,157) | −73° | 76 × 50 px | Open oval face; bottom partly hidden by cap/eye |
| 2 | (513,117) | −47° | 80 × 28 px | Narrow, turned oval; bright front rod |
| 3 | (560,85) | −22° | 94 × 60 px | Broad open oval face |
| 4, center | (623,77) | 0° | 94 × 34 px | Nearly edge-on oval; front horizontal arch and rear bar visible |
| 5 | (686,85) | +22° | 94 × 60 px | Broad open oval face |
| 6 | (732,117) | +47° | 80 × 28 px | Narrow, turned oval; bright front rod |
| 7, above right cap | (764,157) | +73° | 76 × 50 px | Open oval face; bottom partly hidden by cap/eye |

- Chain tube diameter is approximately 14–17 px. All links should use rounded oval/racetrack centerlines, not flattened plates or interlocking circular toruses.
- Top of chain is around y=52; center link front surface around y=61–86. Arc extends approximately x=443–794 before entering caps.
- Small circumferential joining/weld rings can be seen on broad upper links and the rear bar of the central link, but these are subtle.
- Left fixed eye: emerges from cap approximately around `(477,182)`, with crown around `(481,151)` and projected side rails roughly x=468 and x=493. Right fixed eye: emerges around `(764,182)`, with crown near `(760,151)` and rails roughly x=747 and x=777. Eye bases and complete cross-section are occluded. The visible image does not establish a bearing, screw, swivel pin, or an exact internal anchoring structure.

## Appearance

- Grips are near-black, with dense fine wrinkled/pebbled grain, longitudinally coherent in places. No discrete wraps, grooves, logos, seams, or raised rings are visible along the grip body.
- Metal is satin/brushed silver-gray with long vertical/specular highlight bands and fine brushing. It is neither mirror chrome nor gray plastic.
- White studio background; broad soft illumination. The black bodies retain readable soft highlights, especially along the center and near the edges. A little top surface of each cap and the low heel curvature are visible, so a shallow camera elevation is plausible, but exact camera projection and hidden cross-sections are indeterminate.

Inspection crops (`chain_reference_inspection.png`, `cap_reference_inspection.png`, `bottom_reference_inspection.png`) are enlarged crops solely for reference analysis. The supplied reference file is unchanged.
