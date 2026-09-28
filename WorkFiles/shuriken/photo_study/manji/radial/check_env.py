import sys, numpy
print("PY", sys.version, "NUMPY", numpy.__version__)
try:
    import scipy; print("SCIPY", scipy.__version__)
except Exception as e: print("NO SCIPY", e)
