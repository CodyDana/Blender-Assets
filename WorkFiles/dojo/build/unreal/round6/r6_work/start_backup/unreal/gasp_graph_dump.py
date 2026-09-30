"""Readable dump of one Blueprint graph from a T3D text export (dj_gasp_inspect.py writes them; UTF-16 is converted).

Each node: its class, the function / variable it calls or reads, and every pin with its default value (the numbers GASP's
traversal uses live in pin defaults) and what it links to. Plain Python.

Run: py -3 gasp_graph_dump.py <export.t3d> <GraphName> [--out file.txt]
"""
import codecs
import re
import sys
from pathlib import Path


def load(path):
    b = Path(path).read_bytes()
    t = b.decode("utf-16") if b[:2] == codecs.BOM_UTF16_LE else b.decode("utf-8", "replace")
    return t.replace(chr(13) + chr(10), chr(10))


def graph_block(text, name):
    m = re.search(r'Begin Object Class=/Script/Engine\.EdGraph Name="%s"' % re.escape(name), text)
    if not m:
        raise SystemExit(f"graph {name} not found")
    # the graph's body is the SECOND block with this name (the first declares it, the second fills it) when present
    starts = [x.start() for x in re.finditer(r'Begin Object Name="%s" ExportPath="[^"]*EdGraph' % re.escape(name), text)]
    start = starts[0] if starts else m.start()
    indent = text.rfind("\n", 0, start) + 1
    pad = text[indent:start]
    end = text.find("\n" + pad + "End Object", start)
    return text[start:end]


def nodes(block):
    out = []
    for m in re.finditer(r'Begin Object Name="(K2Node[^"]*|EdGraphNode[^"]*)" ExportPath="[^"]*"\n(.*?)\n\s*End Object', block, re.S):
        name, body = m.group(1), m.group(2)
        info = {"name": name, "fields": {}, "pins": []}
        for line in body.splitlines():
            l = line.strip()
            if l.startswith("CustomProperties Pin"):
                pn = re.search(r'PinName="([^"]*)"', l)
                fr = re.search(r'PinFriendlyName=[^,]*"([^"]*)"\)', l)
                dv = re.search(r'DefaultValue="([^"]*)"', l)
                dobj = re.search(r'DefaultObject="([^"]*)"', l)
                d = re.search(r'Direction="(EGPD_Output)"', l)
                lk = re.findall(r'(K2Node_[A-Za-z0-9_]+) ', (re.search(r'LinkedTo=\(([^)]*)\)', l) or [None, ""])[1] if re.search(r'LinkedTo=\(([^)]*)\)', l) else "")
                cat = re.search(r'PinType\.PinCategory="([^"]*)"', l)
                info["pins"].append({"pin": pn.group(1) if pn else "?", "friendly": fr.group(1) if fr else None,
                                     "out": bool(d), "default": dv.group(1) if dv else None,
                                     "obj": dobj.group(1) if dobj else None, "links": lk,
                                     "cat": cat.group(1) if cat else None})
            elif "=" in l and not l.startswith("CustomProperties"):
                k, v = l.split("=", 1)
                if k in ("FunctionReference", "VariableReference", "NodeComment", "StructType", "Enum", "TargetType",
                         "EventReference", "CustomFunctionName", "InputKey", "MacroGraphReference", "bIsPureFunc",
                         "NodePosX", "NodePosY", "ErrorMsg"):
                    info["fields"][k] = v[:300]
        out.append(info)
    return out


def main():
    src, gname = sys.argv[1], sys.argv[2]
    text = load(src)
    block = graph_block(text, gname)
    lines = [f"# graph {gname} from {Path(src).name}"]
    for n in nodes(block):
        f = n["fields"]
        ref = f.get("FunctionReference") or f.get("VariableReference") or f.get("MacroGraphReference") or ""
        mm = re.search(r'MemberName="([^"]*)"', ref)
        lines.append(f"\n[{n['name']}] {mm.group(1) if mm else ''} {('// ' + f['NodeComment']) if 'NodeComment' in f else ''}")
        for p in n["pins"]:
            if p["pin"] in ("execute", "then") and not p["links"]:
                continue
            dv = p["default"] if p["default"] not in (None, "") else (p["obj"] or "")
            lines.append(f"   {'->' if p['out'] else '<-'} {p['friendly'] or p['pin']}"
                         f"{' = ' + dv if dv else ''}{'  links ' + ','.join(p['links']) if p['links'] else ''}")
    txt = "\n".join(lines)
    if "--out" in sys.argv:
        Path(sys.argv[sys.argv.index("--out") + 1]).write_text(txt, encoding="utf-8")
    else:
        print(txt)


main()
