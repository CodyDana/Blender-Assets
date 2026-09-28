"""One-off patch: trace.py dense spline bases -> sparse (idempotent check)."""
p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/trace.py"
s = open(p, encoding="utf-8").read()
assert "class _Basis" not in s, "already patched"
a = s.index("def _clamped_basis(")
b = s.index("@dataclass\nclass Curve:")
new = open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/pbt/pbt_sparse_block.txt", encoding="utf-8").read()
s = s[:a] + new + s[b:]


def rep(old, new_):
    global s
    assert s.count(old) == 1, old[:80]
    s = s.replace(old, new_)


rep("""        B = _periodic_basis(nc, s)
        D = _second_diff(nc, True)
        A = B.T @ B + smooth * (D.T @ D)
        c = np.linalg.solve(A, B.T @ q)
        pieces.append(c)""", """        B = _periodic_basis(nc, s)
        c = _solve_periodic(B, q, smooth)
        pieces.append(c)""")
rep("""            B = _clamped_basis(nspan, t)
            nc = B.shape[1]
            P0, P1 = seg[0], seg[-1]
            rhs = seg - np.outer(B[:, 0], P0) - np.outer(B[:, -1], P1)
            Bi = B[:, 1:-1]
            D = _second_diff(nc, False)
            Di = D[:, 1:-1]
            A = Bi.T @ Bi + smooth * (Di.T @ Di)
            rhs2 = Bi.T @ rhs - smooth * (Di.T @ (np.outer(D[:, 0], P0) + np.outer(D[:, -1], P1)))
            ci = np.linalg.solve(A, rhs2)
            c = np.vstack([P0, ci, P1])
            pieces.append(c)""", """            B = _clamped_basis(nspan, t)
            P0, P1 = seg[0], seg[-1]
            c = _solve_clamped(B, seg, P0, P1, smooth)
            pieces.append(c)""")
rep("""    B = _clamped_basis(nspan, t)
    nc = B.shape[1]
    rhs = pts - np.outer(B[:, 0], P0) - np.outer(B[:, -1], P1)
    Bi = B[:, 1:-1]
    D = _second_diff(nc, False)
    Di = D[:, 1:-1]
    A = Bi.T @ Bi + smooth * (Di.T @ Di)
    rhs2 = Bi.T @ rhs - smooth * (Di.T @ (np.outer(D[:, 0], P0) + np.outer(D[:, -1], P1)))
    ci = np.linalg.solve(A, rhs2)
    return np.vstack([P0, ci, P1])""", """    B = _clamped_basis(nspan, t)
    return _solve_clamped(B, pts, P0, P1, smooth)""")
rep("""    B = _periodic_basis(nc, np.arange(n) * (nc / n))
    D = _second_diff(nc, True)
    return np.linalg.solve(B.T @ B + smooth * (D.T @ D), B.T @ q)""", """    B = _periodic_basis(nc, np.arange(n) * (nc / n))
    return _solve_periodic(B, q, smooth)""")
rep("MAX_PIECE_PX = 40.0", "MAX_PIECE_PX = 2500.0")
old_c = s[s.index("    # BOUNDED PIECES."):s.index("    joints: list[int] = []")]
rep(old_c, """    # BOUNDED PIECES.  The basis is sparse (``_Basis``) but the normal equations are solved
    # dense, so a stretch longer than ``MAX_PIECE_PX`` between corners (none on this card)
    # is split at evenly spaced joints.  A joint pins the curve without carrying the
    # tangent across, so it can show as a kink (``joint_kink_deg`` in the stats): 40 px
    # joints did exactly that on the emblem's hooks, hence a limit above any real contour.
""")
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched")
