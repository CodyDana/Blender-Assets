# Gun line queue (gun chat)

Order agreed with the user (2026-10-04 to 2026-10-09). One gun at a time; each starts when the previous finishes.

1. **Assault Rifle AR-01**: DONE 2026-10-09 (merged to main). Report: `WorkFiles/guns/rifle/RIFLE_REPORT.md`.
2. **Compact SMG SM-01** (`SMG01`): DONE 2026-10-13, merged to main (09dd0a27). Unreal 34/34, pack colours verified.
   Close-up realism NOT passed (user: accept now, fix in the joint pass, item 4). Report: `WorkFiles/guns/smg/SMG_REPORT.md`.
3. **Shooting prototype**: G0-G7 + G10 DONE (2026-10-11: card-shop pawn, grip, reloads with hands 3P + FP, Alt free look,
   shoulder camera, fire + reload sounds). Lives on DemoGame_1 branch `guns` in `Documents/Unreal Projects/DemoGame_1_Guns`.
   Open: holster + magazine-drop sounds (Kenney CC0 packs awaiting the user's download OK; impact-sound code built, uncommitted);
   later steps G9 tuning with the user, G11 network test, docs. Ask the user to close that editor before commandlets run.
4. **Joint close-up realism pass, SMG-01 + AR-01** (user 2026-10-13: accept the SMG now, then ONE push on both guns before
   the carbine, with a NEW method, since two paint rounds per gun did not converge). Judges' reasons to beat: one charcoal for
   steel and polymer alike (separate finishes: phosphate/anodised steel vs polymer, wood less orange/saturated on the AR-01),
   SMG stock head reads as a draped sheet (leave the trace where the real pattern demands), ball charging knob, rail teeth
   read as fins, AR-01 steel too clean/even and first-person dust cover. MARKINGS (user 2026-10-13): generic marks only:
   selector letters/icons (S/1/F or safe/semi/auto pictograms) and rail numbers; never a real maker or model name. Plus the
   AR-01's open Unreal gates U5/U10 (micro bevel strips -> fix in the generators) and U8 (lightmap UV). Target = both realism
   judges pass the close views (first person 35 cm, ADS, hero 3/4, 3x crops).
5. **Carbine CB-01** (`CB01`, M4-style sheet): defines the shared black-rifle parts with the long rifle.
6. **Sniper SR-01** (`SR01`): bipod rigged to fold/unfold; never copy the Asiimov look of `References/AWP.webp`.
   STARTED 2026-10-12 in a SEPARATE chat (user's request, Agent SDK runner on the user's API credit): branch
   `claude/sniper-sr01`, worktree `.claude/worktrees/sniper-sr01`, lock SR01 held there. This chat does not take SR01 or
   edit `WorkFiles/guns/sniper/` / `Scripts/guns/sniper/`; that chat treats gunlib, smg, rifle and this file as read-only
   and writes gunlib needs as proposals in `WorkFiles/guns/sniper/SR01_BUILD_PLAN.md`. Plan (user): that chat does the
   initial work and pushes; this chat then pulls it in as the starting point.
7. **Long rifle LR-01** (`LR01`, M16-style sheet): reuses the carbine's parts.

Not queued yet: Heavy Pistol HP-01 (sheet in `References/Guns/Pistol/`), pump shotgun, DMR, second SMG, LMG,
crossbow, attachments kit (prompts in `GUN_REFERENCE_PROMPTS.md`).
