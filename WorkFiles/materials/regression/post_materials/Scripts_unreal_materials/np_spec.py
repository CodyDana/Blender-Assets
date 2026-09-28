"""Load material_spec.json and the Recolour JSON files, and resolve everything the Unreal build needs.

Pure Python (no ``unreal`` import), so it can be checked with any interpreter::

    python np_spec.py            # prints the resolved plan and exits non-zero on any unresolved value or broken chain

The spec is the source of truth for items, slots, masters, parameters and texture intents. The per-part numbers the
map generators computed (Colour, Detail Bias / Scale / Mean / Highlight Ratio / Moments, paper and ink constants) live in
``Exports/<Group>/Textures/Recolour/recolour_maps.json``; version 2 (final pass) adds ``recolour_constants.json`` beside
it (maps/derive_constants.py: covered-texel constants, Lightest Colour, the mip compensation, the paper colour limit),
whose params override the generator's. A derived value always wins over a number typed in the spec, and ``diffs`` lists
every place where the two disagree (a stale spec number is visible, never silently used).

Instance chain (v2): every slot gets MI_<Item>_<Part>_Base (MaterialInstances/Base: every texture and value) and the
buyer-facing MI_<Item>_<Part> (on the mesh) whose parent is the Base and which overrides only its colour parameter(s)
(build.instance_chain.leaf_overrides). Presets hang off the Base.
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
DEFAULT_TEX_DIR = "Scripts/unreal/materials/default_textures/"


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
    if rel.startswith(DEFAULT_TEX_DIR):
        return f"{ROOT}/Textures/Default/{Path(rel).stem}"
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
    """instance name -> {"params": {...}, "json": rel path, "sha256": ...} from every item's recolour_maps.json, with
    recolour_constants.json (v2) merged over it."""
    out = {}
    for group, rel in spec["build"]["recolour_maps"].items():
        path = PROJECT / rel
        data = json.loads(path.read_text(encoding="utf-8"))
        for part_name, part in data["parts"].items():
            inst = part.get("instance")
            if not inst:
                continue
            out[inst] = {"params": dict(part["params"]), "json": rel, "sha256": sha256(path), "part": part_name,
                         "group": group, "pass": bool(part.get("pass", data.get("pass", True)))}
    for group, rel in (spec["build"].get("recolour_constants") or {}).items():
        path = PROJECT / rel
        data = json.loads(path.read_text(encoding="utf-8"))
        if not data.get("pass"):
            raise ValueError(f"{rel}: the derive_constants gates did not pass")
        for part in data["parts"].values():
            inst = part["instance"]
            if inst not in out:
                raise KeyError(f"{rel}: {inst} has no recolour_maps.json entry")
            out[inst]["params"].update(part["params"])
            out[inst]["constants_json"] = rel
            out[inst]["constants_sha256"] = sha256(path)
    return out


def maps_check(spec: dict) -> dict:
    """The sha256 chain maps -> recolour_maps.json -> recolour_constants.json is intact (nothing edited by hand, nothing
    regenerated without re-deriving). Pure Python: run_build.sh runs it before any Unreal step."""
    problems, checked = [], []
    for group, rel in spec["build"]["recolour_maps"].items():
        doc = json.loads((PROJECT / rel).read_text(encoding="utf-8"))
        for m in doc.get("maps", {}).values():
            f = PROJECT / m["file"]
            checked.append(m["file"])
            if not f.is_file():
                problems.append(f"{m['file']} missing")
            elif sha256(f) != m["sha256"]:
                problems.append(f"{m['file']} sha256 differs from {rel}")
        crel = (spec["build"].get("recolour_constants") or {}).get(group)
        if crel:
            c = json.loads((PROJECT / crel).read_text(encoding="utf-8"))
            checked.append(crel)
            if c["source"]["sha256"] != sha256(PROJECT / rel):
                problems.append(f"{crel} was derived from a different {rel}: re-run maps/derive_constants.py")
            for part in c["parts"].values():
                dm = part.get("detail_map")
                if dm and sha256(PROJECT / dm) != part["detail_map_sha256"]:
                    problems.append(f"{crel}: {dm} changed since the constants were derived")
            gen = c["generator"]
            for key, fpath in (("script_sha256", gen["script"]), ("twin_sha256", gen["twin"])):
                if sha256(PROJECT / fpath) != gen[key]:
                    problems.append(f"{crel}: {fpath} changed since the constants were derived (re-run it)")
    for rel in (spec["build"].get("default_textures") or {}):
        if not (PROJECT / rel).is_file():
            problems.append(f"{rel} missing (run default_textures/make_default_textures.py)")
    return {"checked": checked, "problems": problems, "passed": not problems}


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
    chain = spec["build"]["instance_chain"]

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
            base_name = slot["instance"] + chain["base_suffix"]
            s["base_instance"] = base_name
            s["base_path"] = f"{chain['base_folder']}/{base_name}"
            slots.append(s)
            instances[base_name] = {"name": base_name, "path": s["base_path"], "role": "base",
                                    "parent": s["master_path"], "params": s["params"], "textures": s["textures"],
                                    "effective_params": s["params"], "effective_textures": s["textures"],
                                    "slot": None, "base_of": slot["instance"]}
            leaf_keys = chain["leaf_overrides"][slot["master"]]
            missing = [k for k in leaf_keys if k not in s["params"]]
            if missing:
                raise KeyError(f"{slot['instance']}: leaf override(s) {missing} have no value")
            instances[slot["instance"]] = {"name": slot["instance"], "path": s["instance_path"], "role": "leaf",
                                           "parent": s["base_path"],
                                           "params": {k: s["params"][k] for k in leaf_keys}, "textures": {},
                                           "effective_params": s["params"], "effective_textures": s["textures"],
                                           "slot": f"{item['mesh']}/{slot['index']}"}
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
                instances[preset["instance"]] = {"name": preset["instance"], "role": "preset",
                                                 "path": f"{spec['unreal']['folders']['presets']}/{preset['instance']}",
                                                 "parent": parent, "params": pparams, "textures": ptex,
                                                 "effective_params": {**s["params"], **pparams},
                                                 "effective_textures": {**s["textures"], **ptex},
                                                 "slot": None, "preset_of": preset["parent"],
                                                 "optional": bool(preset.get("optional"))}

    # the masters' neutral defaults (v2): tiny textures in /Game/NinjaPack/Textures/Default, flat parameter values
    master_defaults = {}
    for master, md in spec["build"]["master_defaults"].items():
        if master == "note":
            continue
        mp = master_params(spec, master)
        texs = {}
        for pname, rel in md["textures"].items():
            if pname not in mp or mp[pname]["type"] != "texture":
                raise KeyError(f"{master}: default texture for unknown texture parameter {pname!r}")
            if not (PROJECT / rel).is_file():
                raise FileNotFoundError(rel)
            texs[pname] = add_texture(rel, spec["build"]["default_textures"][rel], f"{master}:default {pname}")
        missing = sorted(n for n, e in mp.items() if e["type"] == "texture" and n not in texs)
        if missing:
            raise KeyError(f"{master}: no default texture for {missing}")
        master_defaults[master] = {"textures": texs, "params": dict(md["params"])}

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
    groups = sorted({group_of(t["png"]) for t in plan["textures"].values() if t["png"].startswith("Exports/")})
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
    mc = maps_check(plan["spec"])
    acc = export_pngs_accounted(plan)
    print(json.dumps({"slots": len(plan["slots"]), "textures": len(plan["textures"]),
                      "instances": sorted(plan["instances"]), "meshes": sorted(plan["meshes"]),
                      "diffs": plan["diffs"], "accounted": acc, "maps_check": mc}, indent=1))
    for s in plan["slots"]:
        print(s["instance"], json.dumps(s["params"])[:300])
    sys.exit(0 if acc["passed"] and mc["passed"] else 1)
