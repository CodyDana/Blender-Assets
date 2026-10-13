# Gun line queue (gun chat)

Order agreed with the user (2026-10-04 to 2026-10-09). One gun at a time; each starts when the previous finishes.

1. **Assault Rifle AR-01**: DONE 2026-10-09 (merged to main). Report: `WorkFiles/guns/rifle/RIFLE_REPORT.md`.
2. **Compact SMG SM-01** (`SMG01`): BUILDING (2026-10-12: W1-W3 done, W4 review fixes running, then W4b close-up, W5 Unreal,
   W6 finish). Includes a dedicated **close-up realism pass**
   (user 2026-10-09) before the Unreal stage: first person at 35 cm, ADS, hero 3/4 and 3x close-up crops; polymer
   and steel finish, micro-texture, wear and edge logic; target = the two realism judges pass the close views.
3. **Shooting prototype**: G0-G7 + G10 DONE (2026-10-11: card-shop pawn, grip, reloads with hands 3P + FP, Alt free look,
   shoulder camera, fire + reload sounds). Lives on DemoGame_1 branch `guns` in `Documents/Unreal Projects/DemoGame_1_Guns`.
   Open: holster + magazine-drop sounds (Kenney CC0 packs awaiting the user's download OK; impact-sound code built, uncommitted);
   later steps G9 tuning with the user, G11 network test, docs. Ask the user to close that editor before commandlets run.
4. **AR-01 close-up realism pass** (user 2026-10-09), after the SMG: steel too clean/even, wood too orange and
   saturated, first-person dust cover; plus the open Unreal gates U5/U10 (micro bevel strips -> fix in the generators)
   and U8 (lightmap UV). Same target as the SMG pass.
5. **Carbine CB-01** (`CB01`, M4-style sheet): defines the shared black-rifle parts with the long rifle.
6. **Sniper SR-01** (`SR01`): bipod rigged to fold/unfold; never copy the Asiimov look of `References/AWP.webp`.
7. **Long rifle LR-01** (`LR01`, M16-style sheet): reuses the carbine's parts.

Not queued yet: Heavy Pistol HP-01 (sheet in `References/Guns/Pistol/`), pump shotgun, DMR, second SMG, LMG,
crossbow, attachments kit (prompts in `GUN_REFERENCE_PROMPTS.md`).
