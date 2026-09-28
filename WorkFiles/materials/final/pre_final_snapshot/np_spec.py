"""Load material_spec.json and the generators' recolour_maps.json, and resolve everything the Unreal build needs.

Pure Python (no ``unreal`` import), so it can be checked with any interpreter::

    python np_spec.py            # prints the resolved plan and exits non-zero on any unresolved value

The spec is the source of truth for items, slots, masters, parameters and texture intents. The per-part numbers the
map generators computed (Colour, Detail Bias / Scale / Mean / Highlight Ratio / Moments, paper and ink constants) live in
``Exports/<Group>/Textures/Recolour/recolour_maps.json``; a generator value always wins over a number typed in the spec,
and ``diffs`` lists every place where the two disagree (so a stale spec number is visible, never silently used).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
SPEC_PATH = HERE / "material_spec.json"
WORK = PROJECT / "WorkFiles" / "materials"
ROOT = "/Game/NinjaPack"


def load_spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def png_rel(text: str) -> str:
    """'Exports/X/Textures/T.png (NEW: ...)' -> 'Exports/X/Textures/T.png'."""
    return text.split(" (")[0].strip()


def group_of(rel: str) -> str:
    """The Exports group folder a file belongs to: Exports/<Group>/..."""
    parts = Path(rel).parts
    if len(parts) < 2 or parts[0] != "Exports":
        raise ValueError(f"not under Exports/: {rel}")
    return parts[1]


def texture_asset(rel: str) -> str:
    return f"{ROOT}/Textures/{group_of(rel)}/{Path(rel).stem}"


def folders(spec: dict) -> dict:
    return dict(spec["unreal"]["folders"])


def master_params(spec: dict, master: str) -> dict:
    return {p["name"]: p for p in spec["masters"][master]["parameters"]}


def _is_placeholder(v) -> bool:
    return isinstance(v, str) and (v.startswith("GENERATOR") or v == "per instance")


def _norm_vector(v):
    v = [float(x) for x in v]
    if len(v) == 3:
        v.append(1.0)
    return v[:4]


def load_recolour(spec: dict) -> dict:
    """instance name -> {"params": {...}, "json": rel path, "sha256": ...} from every item's recolour_maps.json."""
    out = {}
    for group, rel in spec["build"]["recolour_maps"].items():
        path = PROJECT / rel
        data = json.loads(path.read_text(encoding="utf-8"))
        for part_name, part in data["parts"].items():
            inst = part.get("instance")
            if not inst:
                continue
            out[inst] = {"params": part["params"], "json": rel, "sha256": sha256(path), "part": part_name,
                         "group": group, "pass": bool(part.get("pass", data.get("pass", True)))}
    return out


def _resolve_params(spec: dict, slot: dict, recolour: dict, diffs: list) -> dict:
    master = slot["master"]
    mp = master_params(spec, master)
    raw = dict(slot.get("params") or {})
    gen = (recolour.get(slot["instance"]) or {}).get("params") or {}
    resolved = {}
    for name in sorted(set(raw) | set(gen)):
        if name not in mp:
            raise KeyError(f"{slot['instance']}: parameter {name!r} is not a parameter of {master}")
        ptype = mp[name]["type"]
        spec_v, gen_v = raw.get(name), gen.get(name)
        value = gen_v if gen_v is not None else spec_v
        if _is_placeholder(value):
            raise ValueError(f"{slot['instance']}: {name!r} is still a placeholder ({value!r})")
        if ptype == "vector":
            value = _norm_vector(value)
        elif ptype == "scalar":
            value = float(value)
        elif ptype == "static_switch":
            value = bool(value)
        if gen_v is not None and spec_v is not None and not _is_placeholder(spec_v):
            a = _norm_vector(spec_v) if ptype == "vector" else [float(spec_v)] if ptype == "scalar" else [bool(spec_v)]
            b = value if ptype == "vector" else [value]
            if ptype in ("vector", "scalar") and any(abs(x - y) > 1e-9 + 1e-6 * abs(y) for x, y in zip(a, b)):
                diffs.append({"instance": slot["instance"], "param": name, "spec": a, "generator": b,
                              "used": "generator"})
        resolved[name] = value
    return resolved


def resolve(spec: dict | None = None) -> dict:
    """Everything the build needs, flattened. Raises on any unresolved or inconsistent entry."""
    spec = spec or load_spec()
    recolour = load_recolour(spec)
    diffs, slots, textures, instances = [], [], {}, {}
    kinds = spec["texture_import"]

    def add_texture(rel, kind, used_by, extra=None):
        if kind not in kinds:
            raise KeyError(f"{rel}: unknown texture kind {kind!r}")
        asset = texture_asset(rel)
        entry = textures.setdefault(asset, {"asset": asset, "png": rel, "kind": kind, "used_by": [], "extra": {}})
        if entry["kind"] != kind:
            raise ValueError(f"{rel} requested as {kind} and {entry['kind']}")
        entry["used_by"].append(used_by)
        if extra:
            entry["extra"].update(extra)
        return asset

    for item in spec["items"]:
        for slot in item["slots"]:
            s = {"item": item["item"], "mesh": item["mesh"], "fbx": item["fbx"], "sidecar": item["sidecar"],
                 "index": slot["index"], "slot_name": slot["slot_name"], "part": slot["part"],
                 "instance": slot["instance"], "master": slot["master"], "recolourable": slot["recolourable"],
                 "textures": {}, "unwired_textures": {}}
            mp = master_params(spec, slot["master"])
            for pname, text in slot["textures"].items():
                if pname not in mp or mp[pname]["type"] != "texture":
                    raise KeyError(f"{slot['instance']}: {pname!r} is not a texture parameter of {slot['master']}")
                rel = png_rel(text)
                if not (PROJECT / rel).is_file():
                    raise FileNotFoundError(rel)
                s["textures"][pname] = add_texture(rel, slot["texture_kinds"][pname], f"{slot['instance']}:{pname}")
            for key, text in (slot.get("unwired_textures") or {}).items():
                rel = png_rel(text)
                s["unwired_textures"][key] = add_texture(rel, slot["unwired_texture_kinds"][key], f"{slot['instance']}:unwired {key}")
            ots = slot.get("orm_texture_settings")
            if ots:
                orm = s["textures"]["ORM Map"]
                n_asset = s["textures"]["Normal Map"]
                if Path(n_asset).name != ots["composite_texture"]:
                    raise ValueError(f"{slot['instance']}: composite texture {ots['composite_texture']} != {n_asset}")
                textures[orm]["extra"]["composite"] = {"composite_texture": n_asset,
                                                       "composite_texture_mode": ots["composite_texture_mode"],
                                                       "composite_power": float(ots["composite_power"])}
            s["params"] = _resolve_params(spec, slot, recolour, diffs)
            s["recolour_source"] = {k: v for k, v in (recolour.get(slot["instance"]) or {}).items() if k != "params"}
            s["instance_path"] = f"{spec['unreal']['folders']['instances']}/{slot['instance']}"
            s["master_path"] = spec["masters"][slot["master"]]["path"]
            slots.append(s)
            instances[slot["instance"]] = {"name": slot["instance"], "path": s["instance_path"],
                                           "parent": s["master_path"], "params": s["params"],
                                           "textures": s["textures"], "slot": f"{item['mesh']}/{slot['index']}"}
            for preset in slot.get("presets") or []:
                ptex = {}
                pparams = {}
                for k, v in preset["params"].items():
                    if k in mp and mp[k]["type"] == "texture":
                        rel = png_rel(v)
                        ptex[k] = add_texture(rel, "BC", f"{preset['instance']}:{k}")
                    else:
                        pparams[k] = bool(v) if mp[k]["type"] == "static_switch" else v
                parent = instances[preset["parent"]]["path"]
                instances[preset["instance"]] = {"name": preset["instance"],
                                                 "path": f"{spec['unreal']['folders']['presets']}/{preset['instance']}",
                                                 "parent": parent, "params": pparams, "textures": ptex,
                                                 "slot": None, "preset_of": preset["parent"],
                                                 "optional": bool(preset.get("optional"))}

    # which slot supplies each master's default textures
    master_defaults = {}
    for master, ref in spec["build"]["master_default_textures"].items():
        if master == "note":
            continue
        item_name, idx = ref.split("/")
        slot = next(x for x in slots if x["item"] == item_name and x["index"] == int(idx))
        if slot["master"] != master:
            raise ValueError(f"master default {ref} is not a {master} slot")
        master_defaults[master] = {"slot": ref, "textures": dict(slot["textures"]), "params": dict(slot["params"])}

    meshes = {}
    for s in slots:
        m = meshes.setdefault(s["mesh"], {"mesh": s["mesh"], "item": s["item"], "fbx": s["fbx"], "sidecar": s["sidecar"],
                                          "asset": f"{spec['unreal']['folders']['meshes']}/{s['mesh']}", "slots": []})
        m["slots"].append({"index": s["index"], "slot_name": s["slot_name"], "instance": s["instance"],
                           "instance_path": s["instance_path"]})
    for rel in (spec["build"].get("not_imported") or {}):
        if not (PROJECT / rel).is_file():
            raise FileNotFoundError(rel)
    return {"spec": spec, "slots": slots, "textures": textures, "instances": instances, "meshes": meshes,
            "master_defaults": master_defaults, "recolour": recolour, "diffs": diffs}


def export_pngs_accounted(plan: dict) -> dict:
    """Every PNG in the four export texture folders (and Recolour/) must be imported or listed in build.not_imported."""
    imported = {t["png"] for t in plan["textures"].values()}
    skipped = set(plan["spec"]["build"].get("not_imported") or {})
    groups = sorted({group_of(t["png"]) for t in plan["textures"].values()})
    found, unaccounted = [], []
    for g in groups:
        for sub in ("Textures", "Textures/Recolour"):
            for p in sorted((PROJECT / "Exports" / g / sub).glob("*.png")):
                rel = p.relative_to(PROJECT).as_posix()
                found.append(rel)
                if rel not in imported and rel not in skipped:
                    unaccounted.append(rel)
    return {"pngs_found": len(found), "imported": len(imported), "skipped": sorted(skipped),
            "unaccounted": unaccounted, "passed": not unaccounted}


if __name__ == "__main__":
    import sys
    plan = resolve()
    print(json.dumps({"slots": len(plan["slots"]), "textures": len(plan["textures"]),
                      "instances": sorted(plan["instances"]), "meshes": sorted(plan["meshes"]),
                      "diffs": plan["diffs"], "accounted": export_pngs_accounted(plan)}, indent=1))
    for s in plan["slots"]:
        print(s["instance"], json.dumps(s["params"])[:300])
    sys.exit(0 if export_pngs_accounted(plan)["passed"] else 1)
