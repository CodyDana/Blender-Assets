import json, glob, os
d = os.path.dirname(os.path.abspath(__file__))
for f in sorted(glob.glob(os.path.join(d, "*.json"))):
    r = json.load(open(f))
    h, s = r["pieces"]["hero"], r["pieces"].get("scripted", {})
    for n, v in h.items():
        line = f"{n:28s} tris {v['tris']:5d} qa {len(v['qa_hard_fails'])}"
        if n in s:
            dm = max(abs(a - b) for a, b in zip(v["local_bbox_min"] + v["local_bbox_max"],
                                                  s[n]["local_bbox_min"] + s[n]["local_bbox_max"]))
            line += f" bbox_delta {dm*100:.2f} cm"
        line += f"  {v['local_bbox_min']} {v['local_bbox_max']}"
        print(line)
        for q in v["qa_hard_fails"]:
            print("   ", q)
