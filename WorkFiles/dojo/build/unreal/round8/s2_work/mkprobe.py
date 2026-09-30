"""Round 8 s2: write a -game probe cfg. usage: py -3 mkprobe.py <name> <shots.json-literal-file>
shots file: a python literal list of dicts {name,w,h,out,uds,cmds,read}"""
import ast, json, sys
from pathlib import Path
W = Path(__file__).parent
name = sys.argv[1]
shots = ast.literal_eval(Path(sys.argv[2]).read_text())
d = W / name
d.mkdir(exist_ok=True)
cfg = {"out_dir": d.as_posix(), "report": (d / "game_capture.json").as_posix(), "warm_s": 40, "warm_per_cam_s": 4,
       "settle_s": 14, "shot_timeout_s": 90, "hide_pawn": True, "warm_pass": False,
       "cvars": ["scalability 3", "r.ScreenPercentage 100", "r.HighResScreenshotDelay 8", "t.MaxFPS 60"]}
if len(sys.argv) > 3:
    cfg.update(json.loads(sys.argv[3]))
cfg["shots"] = shots
(d / "cfg.json").write_text(json.dumps(cfg, indent=1))
print((d / "cfg.json").as_posix())
