"""perf2: ratio signature B/A of key CPU / GPU stats between two CSV groups (same view): a uniform CPU slowdown shows
the game thread, render-thread work and worker tasks all scaled by a similar factor with the GPU unchanged.
usage: csv_ratio.py "A.csv,..." "B.csv,..." """
import sys
from csv_diff import group
KEYS = ["FrameTime", "GameThreadTime", "GPUTime", "RHIThreadTime", "Exclusive/RenderThread/RenderOther",
        "Exclusive/RenderThread/RenderLighting", "Exclusive/RenderThread/RDG", "Exclusive/RenderThread/RDG_CollectResources",
        "Exclusive/RenderThread/RenderShadows", "Exclusive/GameThread/UI", "Exclusive/GameThread/TickActors",
        "Exclusive/GameThread/Animation", "AnimationParallelEvaluation/TotalTaskTime", "Exclusive/AllWorkers/RenderLighting",
        "Exclusive/AllWorkers/Slate", "LightCount/All", "LightCount/Unbatched", "RHI/DrawCalls"]
a, b = group(sys.argv[1]), group(sys.argv[2])
for k in KEYS:
    x, y = a.get(k), b.get(k)
    if x is None or y is None:
        print(f"{k:50s} {x} {y}")
        continue
    print(f"{k:50s} {x:9.3f} {y:9.3f}  x{(y / x if x else float('nan')):5.2f}")
