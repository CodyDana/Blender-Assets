"""G10 finish: copy the review frames of the final -game runs into runs/G10/finish/frames/ and draw the contact sheet.
Plain Python 3 + Pillow, outside Unreal:

    py -3 make_finish_sheet.py [<ClaudeGuns work root>]

Work dirs (tags) read: G10f_grip, G10f_g9, G10f_views, G10f_reload, G10f_freelook, G10f_pt3 (run_guns.ps1 -Mode game -ReadOnly).
"""
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W = Path(sys.argv[1] if len(sys.argv) > 1 else "C:/Users/Cody/AppData/Local/Temp/ClaudeGuns")
HERE = Path(__file__).resolve().parent
FR = HERE / "frames"
FR.mkdir(exist_ok=True)

BEST = {"02_left_hand_right_side_idle.png", "07b_both_hands_right_side_wide_shoulder_aim.png", "03_shoulder_aim_burst.png",
        "tactical_3p_06_t086_front_left.png", "tactical_fp_08_t115_player.png", "fl02_gun_hip_freelook_yaw90.png"}  # copied to frames/

SECTIONS = [
    ("Idle grip (3P, hip hold unchanged): left hand wraps the handguard, right hand on the pistol grip, index on the trigger", [
        ("G10f_grip", "02_left_hand_right_side_idle.png", "left hand, idle (right side)"),
        ("G10f_grip", "07b_left_hand_right_side_shoulder_aim.png", "left hand, shoulder aim"),
        ("G10f_grip", "03_right_hand_right_side_idle.png", "right hand, idle"),
        ("G10f_grip", "03_right_hand_left_front_below_idle.png", "right hand from below-front, idle"),
    ]),
    ("Firing", [
        ("G10f_grip", "05c_left_hand_right_side_burst_noflash.png", "auto burst, left hand (flash hidden)"),
        ("G10f_grip", "05c_right_hand_right_side_burst_noflash.png", "auto burst, right hand (flash hidden)"),
        ("G10f_g9", "03_shoulder_aim_burst.png", "burst in shoulder aim (player camera)"),
        ("G10f_views", "04_v_burst.png", "burst in first person (V)"),
    ]),
    ("Shoulder aim (hold RMB) and ADS (tap RMB)", [
        ("G10f_g9", "02_shoulder_aim_held.png", "shoulder aim held (player camera)"),
        ("G10f_grip", "07b_both_hands_right_side_wide_shoulder_aim.png", "shoulder aim, both hands"),
        ("G10f_pt3", "frame_ads_sight_picture.png", "ADS (3P mode): sight picture on the 25 m card"),
        ("G10f_views", "05_v_tap_ads.png", "ADS from first person"),
    ]),
    ("Third-person reload: tactical (old magazine out and dropped, new one from the belly pouch, seated) and empty (charge)", [
        ("G10f_reload", "tactical_3p_02_t020_front_left.png", "0.20 s hand on the magazine"),
        ("G10f_reload", "tactical_3p_04_t060_front_left.png", "0.60 s old magazine in the hand"),
        ("G10f_reload", "tactical_3p_06_t086_front_left.png", "0.86 s dropped, hand in the pouch"),
        ("G10f_reload", "tactical_3p_06_t086_pouch_front.png", "0.86 s pouch from the front"),
        ("G10f_reload", "tactical_3p_09_t125_front_left.png", "1.25 s new magazine in the hand"),
        ("G10f_reload", "tactical_3p_10_t145_front_left.png", "1.45 s riding it in"),
        ("G10f_reload", "tactical_3p_13_t200_front_left.png", "2.00 s seated, back on the handguard"),
        ("G10f_reload", "empty_3p_08_t245_right_close.png", "empty: 2.45 s hand on the charging handle"),
    ]),
    ("First-person reload (V, player's view)", [
        ("G10f_reload", "tactical_fp_01_t012_player.png", "0.12 s reach"),
        ("G10f_reload", "tactical_fp_03_t050_player.png", "0.50 s old magazine out"),
        ("G10f_reload", "tactical_fp_08_t115_player.png", "1.15 s new magazine"),
        ("G10f_reload", "tactical_fp_09_t130_player.png", "1.30 s riding it in"),
        ("G10f_reload", "tactical_fp_10_t145_player.png", "1.45 s seating"),
        ("G10f_reload", "tactical_fp_12_t190_player.png", "1.90 s back to the hold"),
        ("G10f_views", "02_v_idle.png", "V idle (after)"),
        ("G10f_views", "06_v_look_down.png", "V looking down (FP legs, pouch)"),
    ]),
    ("Free look (hold Left Alt + mouse): the camera turns, the body / gun / shots stay on the aim", [
        ("G10f_freelook", "fl01_gun_hip_base.png", "base view (aim)"),
        ("G10f_freelook", "fl02_gun_hip_freelook_yaw90.png", "Alt + 90 deg right"),
        ("G10f_freelook", "fl05_gun_run_freelook_120.png", "running W, camera +120 deg"),
        ("G10f_freelook", "fl06_gun_sprint_freelook_-90.png", "sprinting, camera -90 deg"),
        ("G10f_freelook", "fl03_gun_hip_freelook_yaw90_up30.png", "+90 deg, up 30 deg"),
        ("G10f_freelook", "fl08_fp_freelook_yaw90.png", "first person, +90 deg"),
        ("G10f_freelook", "fl13_wall_freelook_yaw90.png", "back to a wall: camera stops at it"),
        ("G10f_freelook", "fl04_gun_hip_released.png", "released: back on the aim"),
    ]),
]

COLS, TW = 4, 640
TH = TW * 9 // 16
LAB, HEAD = 30, 44


def font(n):
    for f in ("arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(f, n)
        except OSError:
            continue
    return ImageFont.load_default()


fl, fh, ft = font(19), font(24), font(30)
h = 60
for _, items in SECTIONS:
    h += HEAD + ((len(items) + COLS - 1) // COLS) * (TH + LAB)
sheet = Image.new("RGB", (COLS * TW, h), (24, 24, 24))
d = ImageDraw.Draw(sheet)
d.text((12, 14), "G10 finish (2026-10-11): BP_GunCharacter (card-shop pawn) on L_GunRange, final binaries, fresh -game runs", fill=(255, 255, 255), font=ft)
y = 60
for title, items in SECTIONS:
    d.rectangle([0, y, COLS * TW, y + HEAD - 4], fill=(52, 60, 74))
    d.text((12, y + 8), title, fill=(255, 255, 255), font=fh)
    y += HEAD
    for i, (tag, name, label) in enumerate(items):
        src = W / tag / "shots" / name
        dst = FR / f"{tag.replace('G10f_', '')}__{name}"
        if name in BEST:
            shutil.copy2(src, dst)
        x, yy = (i % COLS) * TW, y + (i // COLS) * (TH + LAB)
        t = Image.open(src).convert("RGB")
        t.thumbnail((TW - 4, TH - 4))
        sheet.paste(t, (x + (TW - t.width) // 2, yy + LAB))
        d.text((x + 8, yy + 5), label, fill=(235, 235, 235), font=fl)
    y += ((len(items) + COLS - 1) // COLS) * (TH + LAB)
out = HERE / "contact_sheet_G10_finish.png"
sheet.save(out)
print(out, sheet.size)
