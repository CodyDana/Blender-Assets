import json
from collections import defaultdict
D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/blind/"
k = json.load(open(D + "_key_sealed.json", encoding="utf-8"))["ours_is"]
g = json.load(open(D + "guesses_before_reveal.json", encoding="utf-8"))["guesses"]
st = defaultdict(lambda: [0, 0]); rows = []
for key, (gs, conf, why) in g.items():
    ok = k[key] == gs; st[conf][0] += ok; st[conf][1] += 1
    v = key.split("|")[1]; st["view:" + v][0] += ok; st["view:" + v][1] += 1
    rows.append({"pair": key, "ours": k[key], "guess": gs, "correct": ok, "conf": conf, "tell": why})
    print(("OK " if ok else "XX ") + key, "ours=", k[key], "guess=", gs, conf)
print({a: b for a, b in st.items()})
print("unviewed:", [x for x in k if x not in g])
json.dump({"rows": rows, "stats": dict(st)}, open(D + "blind_scores.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
