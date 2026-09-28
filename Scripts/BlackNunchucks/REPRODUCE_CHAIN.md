# Reproducing the chain correction

All scripts resolve the workspace from their own path (`parents[2]`). They assert the BlackNunchucks asset lock belongs to `codex` through `Scripts/pipeline/lock.py`. Run from the workspace root with Blender 5.2 available as `blender` and a Python 3.12 environment available as `python`. Keep the packaged workspace folder structure intact.

`resolve_chain.py` uses only Blender's bundled libraries and the saved solution. To apply the delivered correction without repeating optimization:

```powershell
blender --background --python Scripts/BlackNunchucks/resolve_chain.py
```

Inputs are `WorkFiles/BlackNunchucks/BlackNunchucks_procedural.blend` and `WorkFiles/BlackNunchucks/chain_solution.json`. The script writes only `BlackNunchucks_resolved.blend` and `chain_resolution_report.json` in that work folder. It preserves every changed mesh's vertex/edge/face counts, face indices, and both UV layers, updates chain rest bones, and carries the same correction across all three LODs. It does not bake or export the final asset.

To reproduce the optimization itself:

```powershell
python -m pip install -r Scripts/BlackNunchucks/requirements-resolve.txt
blender --background WorkFiles/BlackNunchucks/BlackNunchucks_procedural.blend --python Scripts/BlackNunchucks/extract_chain_centers.py
python Scripts/BlackNunchucks/optimize_chain.py
blender --background --python Scripts/BlackNunchucks/resolve_chain.py
```

The extraction writes `chain_centers.json`; optimization writes `chain_solution.json`. NumPy and SciPy are needed only for the external optimization step. Installed third-party package directories do not need to be distributed. The optional local `WorkFiles/BlackNunchucks/qa_deps` path is used if it exists; a normal Python environment with the listed requirements also works.

The optimizer adjusts chain centers, depth, roll, and oval width, plus eye roll/width. It reduces only the two end-link wire radii from 8.7 to 7.6 reference pixels; the five middle links remain at 8.7. A source reference pixel corresponds to 0.00030 m in this model. The pose is an interpretation of the single supplied image, not an exact reconstruction of hidden geometry.

For independent read-only geometric QA of any saved asset, run the following command for LOD values 0, 1, and 2 with a different output name for each:

```powershell
blender --background Assets/BlackNunchucks.blend --python Scripts/BlackNunchucks/qa_chain_intersections.py -- --all-pairs --lod 0 --out WorkFiles/BlackNunchucks/chain_final_allpairs_LOD0.json
```

QA checks all 36 unordered pairs among seven links and two eyes. It uses evaluated world-space triangles, zero-epsilon BVH overlap, and an independent separating-axis triangle intersection test. The report includes the checked `.blend` SHA-256, triangle intersection counts, and Gauss linking integrals for all eight intended connections. Eye loops close across their cap-embedded bases for the topological check. Weld rings and intentional cap embedding are excluded from these chain/eye tests. The reported tube clearance uses exact straight centerline segment distances minus tube radii; rendered tubes are polygonal approximations. QA never saves the loaded `.blend`.
