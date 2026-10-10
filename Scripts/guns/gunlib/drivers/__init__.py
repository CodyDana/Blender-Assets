"""Gun-agnostic gate drivers (gunlib 0.2.0), promoted from the AR-01's Scripts/guns/rifle/rifle_*.py.

Each driver module has ``main(cfg, argv=None)``; ``cfg`` is the gun's ``gunlib.gunconf.GunConfig`` and ``argv`` the
arguments after Blender's ``--`` (or sys.argv[1:] for the plain-Python drivers). A gun calls them either through a
thin shim next to its build code (``rifle_b3.py`` = ``b3.main(CFG)``) or through the generic runner::

    blender -b X.blend --factory-startup --python Scripts/guns/gunlib/drivers/run.py -- --gun <cfg.py> --driver b3 [args]
    py -3 -B Scripts/guns/gunlib/drivers/run.py --gun <cfg.py> --driver b4 [args]

Blender drivers (need bpy): b3, b6a, measure, magfit_check, g5_lods, rig_verify, mag_fit.
Plain-Python drivers (numpy + PIL): b4, viewgates.
"""
BLENDER_DRIVERS = ("b3", "b6a", "measure", "magfit_check", "g5_lods", "rig_verify", "mag_fit", "ud")
PLAIN_DRIVERS = ("b4", "viewgates")
