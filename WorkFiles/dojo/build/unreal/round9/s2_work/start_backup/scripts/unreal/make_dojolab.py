"""Create (or refresh) the DojoLab Unreal 5.8 project as a COPY of the Game Animation Sample (GASP). Plain Python, no
Unreal. Idempotent; the SOURCE project is only ever read.

- DojoLab.uproject: GASP's .uproject (same plugins, Blueprint-only) plus PythonScriptPlugin + EditorScriptingUtilities;
  the Epic sample hash is dropped (DojoLab is not the sample).
- Config/: every GASP config file. DefaultEngine.ini and DefaultGame.ini are GENERATED from GASP's:
    * RendererSettings = GASP's keys with DemoGame_1's render keys on top (DemoGame_1 is read-only: Lumen GI and
      reflections, virtual shadow maps, distance fields, ray tracing, Substrate, AllowStaticLighting False ...),
    * WindowsTargetSettings: DemoGame_1's RHI / shader-format lines (DX12, SM6),
    * GameMapsSettings: the dojo level is the editor-startup and game-default map, the game mode is GM_Dojo (a child of
      GASP's GM_Sandbox whose default pawn is SandboxCharacter_CMC, made by dj_gamemode.py),
    * ConsoleVariables: Interchange.FeatureFlags.Import.FBX=0 (legacy FBX importer: UCX hulls keyed to the node name),
    * DefaultGame.ini: ProjectName DojoLab and a new ProjectID.
  The other config files (collision channels are in DefaultEngine: Traversable / Mouse / Obstacle, GASP's cvars, input,
  gameplay tags, network prediction) are copied verbatim, missing only.
- Content/: copied MISSING files only (never overwrites, never deletes), so our own assets (/Game/Dojo, /Game/DojoKit) and
  any edit of a copied asset survive a refresh. NOT copied: DerivedDataCache, Intermediate, Saved, Binaries, Build.

Run: py -3 Scripts/dojo/unreal/make_dojolab.py   -> WorkFiles/dojo/build/unreal/make_dojolab.json
"""
import json
import shutil
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dj_common as C  # noqa: E402

SRC = C.SOURCE_DIR
DST = C.PROJECT_DIR
DEMO_INI = Path(r"C:\Users\Cody\Documents\Unreal Projects\DemoGame_1\Config\DefaultEngine.ini")   # read-only
WINDOWS_KEYS = ("DefaultGraphicsRHI", "-D3D12TargetedShaderFormats", "+D3D12TargetedShaderFormats",
                "-D3D11TargetedShaderFormats", "+D3D11TargetedShaderFormats")
GENERATED = {"DefaultEngine.ini", "DefaultGame.ini"}


def read_sections(path):
    """Unreal ini -> ordered [(section, [lines])]; keys may repeat (+/- prefixes)."""
    out, cur = [], None
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.rstrip()
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            cur = (s[1:-1], [])
            out.append(cur)
            continue
        if cur is None:
            if s:
                cur = ("", [])
                out.append(cur)
            else:
                continue
        cur[1].append(line)
    return out


def kv(line):
    s = line.strip()
    if not s or s.startswith(";") or "=" not in s:
        return None, None
    k, v = s.split("=", 1)
    return k.strip(), v.strip()


def section(secs, name):
    return next((lines for n, lines in secs if n == name), None)


def engine_ini(report):
    gasp = read_sections(SRC / "Config" / "DefaultEngine.ini")
    demo = read_sections(DEMO_INI)
    demo_render = [(k, v) for k, v in (kv(l) for l in section(demo, "/Script/Engine.RendererSettings")) if k]
    demo_win = [(k, v) for k, v in (kv(l) for l in section(demo, "/Script/WindowsTargetPlatform.WindowsTargetSettings"))
                if k in WINDOWS_KEYS]
    m = C.LEVEL + "." + C.LEVEL.rsplit("/", 1)[1]
    gm = C.DOJO_GAME_MODE + "." + C.DOJO_GAME_MODE.rsplit("/", 1)[1] + "_C"
    out = ["; DojoLab: generated from GameAnimationSample/Config/DefaultEngine.ini by Scripts/dojo/unreal/make_dojolab.py.",
           "; Render settings on top from DemoGame_1/Config/DefaultEngine.ini (both sources are read-only).", ""]
    changed = {"render_overrides": {}, "render_added": [], "windows": demo_win}
    seen_sections = set()
    for name, lines in gasp:
        seen_sections.add(name)
        if name:
            out.append(f"[{name}]")
        if name == "/Script/Engine.RendererSettings":
            demo_keys = dict(demo_render)
            have = set()
            for l in lines:
                k, v = kv(l)
                if k in demo_keys:
                    if demo_keys[k] != v:
                        changed["render_overrides"][k] = [v, demo_keys[k]]
                    out.append(f"{k}={demo_keys[k]}")
                    have.add(k)
                else:
                    out.append(l)
            while out and not out[-1].strip():
                out.pop()
            for k, v in demo_render:
                if k not in have:
                    out.append(f"{k}={v}")
                    changed["render_added"].append(k)
            out.append("")
        elif name == "/Script/WindowsTargetPlatform.WindowsTargetSettings":
            first = True
            for l in lines:
                k, _v = kv(l)
                if k in WINDOWS_KEYS:
                    if first:
                        out += [f"{a}={b}" for a, b in demo_win]
                        first = False
                    continue
                out.append(l)
        elif name == "/Script/EngineSettings.GameMapsSettings":
            for l in lines:
                k, _v = kv(l)
                if k in ("EditorStartupMap", "GameDefaultMap", "GlobalDefaultGameMode"):
                    continue
                out.append(l)
            while out and not out[-1].strip():
                out.pop()
            out += [f"EditorStartupMap={m}", f"GameDefaultMap={m}", f"GlobalDefaultGameMode={gm}", ""]
        elif name == "ConsoleVariables":
            body = [l for l in lines if kv(l)[0] != "Interchange.FeatureFlags.Import.FBX"]
            while body and not body[-1].strip():
                body.pop()
            out += body
            out += ["; legacy FBX importer (UCX hulls keyed to the node name; measured on UE 5.8.2, export-pipeline notes)",
                    "Interchange.FeatureFlags.Import.FBX=0", ""]
        else:
            out += lines
    if "ConsoleVariables" not in seen_sections:
        out += ["[ConsoleVariables]", "Interchange.FeatureFlags.Import.FBX=0", ""]
    report["engine_ini_changes"] = changed
    return "\n".join(out) + "\n"


def game_ini():
    pid = uuid.uuid5(uuid.NAMESPACE_URL, "file:///DojoLab/Blender_Projects/dojo").hex.upper()
    lines = []
    for l in (SRC / "Config" / "DefaultGame.ini").read_text(encoding="utf-8-sig").splitlines():
        if l.strip().startswith("ProjectID="):
            lines += [f"ProjectID={pid}", "ProjectName=DojoLab",
                      "Description=Dojo courtyard arena lab (grey-box, then kits) on the Game Animation Sample"]
            continue
        if l.strip().startswith(("ProjectName=", "Description=")):
            continue
        lines.append(l)
    return "\n".join(lines) + "\n"


def uproject():
    src = json.loads(next(SRC.glob("*.uproject")).read_text(encoding="utf-8-sig"))
    src.pop("EpicSampleNameHash", None)
    src["Category"] = ""
    src["Description"] = "Dojo courtyard arena lab: grey-box and kits on a copy of the Game Animation Sample (GASP)."
    names = {p["Name"] for p in src.get("Plugins", [])}
    for extra in ("PythonScriptPlugin", "EditorScriptingUtilities"):
        if extra not in names:
            src.setdefault("Plugins", []).append({"Name": extra, "Enabled": True})
    return json.dumps(src, indent="\t") + "\n"


def put(path, text, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old == text:
        report[str(path.relative_to(DST))] = "unchanged"
        return
    path.write_text(text, encoding="utf-8")
    report[str(path.relative_to(DST))] = "created" if old is None else "updated"


def copy_missing(src_dir, dst_dir, report):
    n_new = n_kept = size = 0
    for f in src_dir.rglob("*"):
        if not f.is_file():
            continue
        t = dst_dir / f.relative_to(src_dir)
        if t.exists():
            n_kept += 1
            continue
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, t)
        n_new += 1
        size += f.stat().st_size
    report[str(dst_dir.relative_to(DST))] = {"copied": n_new, "kept_existing": n_kept, "copied_gb": round(size / 1e9, 3)}


def main():
    t0 = time.time()
    assert DST != SRC and "DojoLab" in str(DST) and "DemoGame" not in str(DST) and "GameAnimationSample" not in str(DST)
    rep = {"source": str(SRC), "project": str(C.UPROJECT), "files": {}, "copies": {}}
    DST.mkdir(parents=True, exist_ok=True)
    put(C.UPROJECT, uproject(), rep["files"])
    put(DST / "Config" / "DefaultEngine.ini", engine_ini(rep), rep["files"])
    put(DST / "Config" / "DefaultGame.ini", game_ini(), rep["files"])
    for f in (SRC / "Config").glob("*.ini"):
        if f.name in GENERATED:
            continue
        t = DST / "Config" / f.name
        if not t.exists():
            shutil.copy2(f, t)
            rep["files"][f"Config\\{f.name}"] = "copied"
        else:
            rep["files"][f"Config\\{f.name}"] = "kept"
    copy_missing(SRC / "Content", DST / "Content", rep["copies"])
    # checks: the render keys the task names, the RHI, and the source untouched (no file there newer than our start)
    ini = (DST / "Config" / "DefaultEngine.ini").read_text(encoding="utf-8")
    need = {"r.AllowStaticLighting=False", "r.Shadow.Virtual.Enable=1", "r.GenerateMeshDistanceFields=True",
            "r.DynamicGlobalIlluminationMethod=1", "r.ReflectionMethod=1", "r.RayTracing=True", "r.Substrate=True",
            "+D3D12TargetedShaderFormats=PCD3D_SM6", "DefaultGraphicsRHI=DefaultGraphicsRHI_DX12",
            "Interchange.FeatureFlags.Import.FBX=0", "Name=\"Traversable\"", "TraversalObjectPreset"}
    rep["ini_checks"] = {k: (k in ini) for k in sorted(need)}
    up = json.loads(C.UPROJECT.read_text(encoding="utf-8"))
    rep["plugins"] = [p["Name"] for p in up["Plugins"]]
    n_src = sum(1 for f in (SRC / "Content").rglob("*") if f.is_file())
    n_dst = sum(1 for f in (SRC / "Content").rglob("*") if f.is_file() and (DST / "Content" / f.relative_to(SRC / "Content")).exists())
    rep["content_files_source"], rep["content_files_present_in_copy"] = n_src, n_dst
    rep["not_copied_from_source"] = ["DerivedDataCache", "Intermediate", "Saved", "Binaries", "Build"]
    rep["source_written"] = sorted(str(f) for f in SRC.rglob("*.ini") if f.stat().st_mtime > t0)
    rep["passed"] = (all(rep["ini_checks"].values()) and n_src == n_dst and "PythonScriptPlugin" in rep["plugins"]
                     and "EditorScriptingUtilities" in rep["plugins"] and not rep["source_written"])
    rep["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "make_dojolab.json", rep)
    print(json.dumps({k: rep[k] for k in ("files", "copies", "ini_checks", "content_files_source",
                                          "content_files_present_in_copy", "passed", "sec")}, indent=1))


main()
