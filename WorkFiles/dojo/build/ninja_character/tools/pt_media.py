"""Play-test media from a dj_ninja_playtest.py report: per frame sequence an MP4 (frame durations = the recorded GAME
time between frames, so the video plays at real game speed even though it was shot in slow motion) and a contact sheet;
a contact sheet of the stills.

    py -3 -B pt_media.py <suite dir> [report name=report_ninja.json] [--every N]
Needs ffmpeg (C:/Users/Cody/Documents/ffmpeg-8.0.1-full_build/bin/ffmpeg.exe) and Pillow.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

FFMPEG = "C:/Users/Cody/Documents/ffmpeg-8.0.1-full_build/bin/ffmpeg.exe"


def sheet(paths, labels, out, cols=4, tw=480):
    ims = []
    for p in paths:
        try:
            ims.append(Image.open(p).convert("RGB"))
        except Exception:  # noqa: BLE001
            ims.append(None)
    ok = [i for i in ims if i is not None]
    if not ok:
        return None
    th = int(tw * ok[0].height / ok[0].width)
    rows = (len(ims) + cols - 1) // cols
    S = Image.new("RGB", (cols * tw, rows * th), (16, 16, 16))
    d = ImageDraw.Draw(S)
    for i, (im, lab) in enumerate(zip(ims, labels)):
        x, y = (i % cols) * tw, (i // cols) * th
        if im is not None:
            S.paste(im.resize((tw, th)), (x, y))
        d.rectangle([x, y, x + min(tw, 8 + 7 * len(lab)), y + 16], fill=(0, 0, 0))
        d.text((x + 4, y + 2), lab, fill=(255, 230, 80))
    S.save(out)
    return out


def main():
    root = Path(sys.argv[1]).resolve()
    rep = json.loads((root / (sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "report_ninja.json"))
                     .read_text(encoding="utf-8"))
    out = {"videos": {}, "sheets": {}}
    for seq, frames in rep.get("sequences", {}).items():
        fr = [f for f in frames if (root / f["file"]).exists()]
        if len(fr) < 2:
            continue
        lst = root / "frames" / seq / "concat.txt"
        lines = []
        for a, b in zip(fr, fr[1:]):
            lines.append(f"file '{(root / a['file']).as_posix()}'")
            lines.append(f"duration {max(0.001, b['t'] - a['t']):.4f}")
        lines.append(f"file '{(root / fr[-1]['file']).as_posix()}'")
        lines.append("duration 0.1")
        lines.append(f"file '{(root / fr[-1]['file']).as_posix()}'")
        lst.write_text("\n".join(lines) + "\n", encoding="utf-8")
        mp4 = root / "video" / f"{seq}.mp4"
        mp4.parent.mkdir(exist_ok=True)
        r = subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf",
                            "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "20", str(mp4)], capture_output=True,
                           text=True)
        game_s = fr[-1]["t"] - fr[0]["t"]
        out["videos"][seq] = {"file": f"video/{seq}.mp4", "frames": len(fr), "game_s": round(game_s, 2),
                              "game_fps": round((len(fr) - 1) / game_s, 1) if game_s > 0 else None,
                              "ok": r.returncode == 0, "err": r.stderr[-300:]}
        n = len(fr)
        pick = [fr[min(n - 1, round(i * (n - 1) / 15))] for i in range(16)] if n > 16 else fr
        t0 = fr[0]["t"]
        s = sheet([root / f["file"] for f in pick], [f"{seq} t+{f['t'] - t0:.2f}s" for f in pick],
                  root / "video" / f"{seq}_sheet.jpg")
        out["sheets"][seq] = str(s)
    shots = sorted((root / "shots").glob("*.png")) if (root / "shots").exists() else []
    if shots:
        out["sheets"]["stills"] = str(sheet(shots, [p.stem for p in shots], root / "stills_sheet.jpg", cols=4))
    (root / "media.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
