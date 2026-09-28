| Setup | Status |
|---|---|
| Unreal Engine 5.8, Windows, DirectX 12 desktop renderer, deferred shading | **Built and tested** (every material compiles; colours, recolours and the look measured) |
| Substrate enabled (`r.Substrate=True`) | **Tested**: compiles; base colour identical to deferred, lit result within 2 % (default and recoloured, all recolourable parts) |
| Forward shading (`r.ForwardShading=True`, for example VR) | **Tested**: compiles; lit result within 0.2 % of deferred |
| Optional Cloth Sheen switched on, under Substrate or forward shading | Not tested |
| Mobile (Android / iOS, ES3.1) | **Not tested.** The fabric and paper materials already use full float precision; their detail maps are 16-bit, which some mobile texture formats reduce to 8-bit |
| Instanced meshes, foliage, PCG scattering | Supported (the masters are flagged for instanced static meshes) |
| Nanite | Not flagged or tested; enable Nanite on the meshes and let the engine add the usage flag if you need it |
