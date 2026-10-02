| view | pawn | FrameTime mean / median / p95 (p95 min-max) | GameThread mean / median / p95 | RenderThread mean (busy) | GPU mean / median / p95 | python dt p95 | vs 16.7 |
|---|---|---|---|---|---|---|---|
| CAM_PlayerEyeSand | ninja (GM_DojoNinja) | 11.99 / 11.92 / **12.84** (12.68-12.92) | 4.86 / 4.84 / 5.34 | 11.97 (9.64) | 11.13 / 11.11 / 11.39 | 13.15 | met |
| CAM_PlayerEyeSand | GASP (GM_Dojo) | 11.15 / 11.14 / **11.85** (11.8-11.93) | 4.22 / 4.19 / 4.71 | 11.13 (7.93) | 10.5 / 10.47 / 10.77 | 12.07 | met |
| CAM_AK_CW_WestAisle | ninja (GM_DojoNinja) | 13.28 / 13.28 / **14.23** (14.04-14.48) | 5.21 / 5.18 / 5.75 | 13.26 (10.04) | 12.42 / 12.39 / 12.66 | 14.56 | met |
| CAM_AK_CW_WestAisle | GASP (GM_Dojo) | 11.39 / 11.37 / **12.36** (12.25-12.47) | 4.37 / 4.32 / 5.07 | 11.37 (7.23) | 10.75 / 10.72 / 11.0 | 12.79 | met |
| CAM_RiverRapids | ninja (GM_DojoNinja) | 13.49 / 13.47 / **14.5** (14.28-14.67) | 4.52 / 4.48 / 5.07 | 13.47 (6.95) | 12.71 / 12.7 / 13.12 | 14.93 | met |
| CAM_RiverRapids | GASP (GM_Dojo) | 13.21 / 13.2 / **14.34** (14.29-14.42) | 3.96 / 3.96 / 4.54 | 13.19 (6.09) | 12.48 / 12.48 / 12.84 | 14.78 | met |
| PAWN | ninja (GM_DojoNinja) | 10.76 / 10.76 / **11.72** (11.69-11.75) | 4.62 / 4.58 / 5.18 | 10.74 (7.68) | 10.06 / 10.03 / 10.32 | 12.04 | met |
| PAWN | GASP (GM_Dojo) | 9.49 / 9.49 / **10.28** (10.17-10.39) | 4.13 / 4.09 / 4.64 | 9.47 (6.63) | 8.86 / 8.83 / 9.09 | 10.5 | met |

| view | ninja - GASP: FrameTime mean | p95 | GameThread mean | GPU mean |
|---|---|---|---|---|
| CAM_PlayerEyeSand | +0.84 | +0.99 | +0.64 | +0.63 |
| CAM_AK_CW_WestAisle | +1.89 | +1.87 | +0.84 | +1.67 |
| CAM_RiverRapids | +0.28 | +0.16 | +0.56 | +0.23 |
| PAWN | +1.27 | +1.44 | +0.49 | +1.20 |
