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
d.text((800, 8), "OURS t6: wider barrel (wood shortened, scaled x 1.133), 79 tacks per row, camera 15 deg above (photo-studio light)",
       fill="black", font=F)
y = top + 780
im.paste(ref.crop((300, 150, 700, 330)).resize((990, 446), Image.LANCZOS), (10, y + 30))
d.text((10, y), "reference tack band (crop)", fill="black", font=F)
im.paste(band_p.crop((0, 120, 1200, 660)).resize((990, 446), Image.LANCZOS), (1005, y + 30))
d.text((1005, y), "ours t6: tack band close-up (photo-studio light)", fill="black", font=F)
y2 = y + 500
im.paste(band_s.crop((0, 120, 1200, 660)).resize((990, 446), Image.LANCZOS), (1005, y2 + 30))
d.text((1005, y2), "ours t6: same close-up, review-studio light", fill="black", font=F)
im.paste(flat(T3 / "closeup_tack_band_photo.png").crop((0, 120, 1200, 660)).resize((990, 446), Image.LANCZOS),
         (10, y2 + 30))
d.text((10, y2), "before (t5): 76 per row, the narrower barrel (photo-studio light)",
       fill="black", font=F)
im = im.crop((0, 0, W, y2 + 30 + 446 + 10))
im.save(HERE / "compare_tacks.png")
print("saved compare_tacks.png", im.size)
# t5: the skirt sheet: the photo's upper skirt vs ours from 18 deg above (closeup_skirt), photo-studio and review light
sk_p = flat(HERE / "closeup_skirt_photo.png")
sk_s = flat(HERE / "closeup_skirt.png")
sk_4 = flat(T3 / "closeup_skirt_photo.png")
S2 = Image.new("RGB", (2000, 1500), "white")
d2 = ImageDraw.Draw(S2)
d2.text((10, 8), "reference: the upper skirt (crop of the user's photo)", fill="black", font=F)
S2.paste(ref.crop((110, 140, 910, 340)).resize((1980, 495), Image.LANCZOS), (10, 36))
d2.text((10, 545), "ours t6: narrow / wide lobes, lapped slits, pockets, ears (photo light)",
        fill="black", font=F)
S2.paste(sk_p.crop((0, 60, 1200, 560)).resize((985, 410), Image.LANCZOS), (10, 575))
S2.paste(sk_s.crop((0, 60, 1200, 560)).resize((985, 410), Image.LANCZOS), (1005, 575))
d2.text((1005, 545), "ours t6, review-studio light", fill="black", font=F)
d2.text((10, 1000), "before (t5): even scalloped lobes, cut V slits, a bead lip all round (photo-studio light)", fill="black", font=F)
S2.paste(sk_4.crop((0, 60, 1200, 560)).resize((985, 410), Image.LANCZOS), (10, 1030))
S2 = S2.crop((0, 0, 2000, 1450))
S2.save(HERE / "compare_skirt.png")
print("saved compare_skirt.png", S2.size)