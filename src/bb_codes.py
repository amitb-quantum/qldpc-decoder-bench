"""Bivariate bicycle (BB) qLDPC codes — construction and exact GF(2) verification.

Following Bravyi et al., "High-threshold and low-overhead fault-tolerant quantum
memory" (Nature 627, 778, 2024). These are the codes the qLDPC literature means
by "gross code" and relatives, and the family a MegaQuOp trapped-ion machine
would plausibly use.

Construction. Over the group algebra F2[x,y]/(x^l - 1, y^m - 1):
    x = S_l (x) I_m        y = I_l (x) S_m        (S = cyclic shift)
    A = A1 + A2 + A3       B = B1 + B2 + B3       (monomials in x, y)
    H_X = [A | B]          H_Z = [B^T | A^T]
n = 2lm data qubits, l*m checks of each type.
"""
import numpy as np


def _shift(k):
    S = np.zeros((k, k), dtype=np.uint8)
    for i in range(k):
        S[i, (i + 1) % k] = 1
    return S


def _mono(l, m, ex, ey):
    """x^ex y^ey as an (lm x lm) permutation matrix."""
    X = np.linalg.matrix_power(_shift(l).astype(np.int64), ex) % 2
    Y = np.linalg.matrix_power(_shift(m).astype(np.int64), ey) % 2
    return np.kron(X, Y).astype(np.uint8)


def gf2_rank(M):
    A = M.copy().astype(np.uint8)
    rows, cols = A.shape
    r = 0
    for c in range(cols):
        piv = None
        for i in range(r, rows):
            if A[i, c]:
                piv = i
                break
        if piv is None:
            continue
        A[[r, piv]] = A[[piv, r]]
        sel = A[:, c].copy().astype(bool)
        sel[r] = False
        A[sel] ^= A[r]
        r += 1
        if r == rows:
            break
    return r


def bb_code(l, m, a_terms, b_terms):
    """a_terms/b_terms: three (ex, ey) monomial exponents each."""
    A = np.zeros((l * m, l * m), dtype=np.uint8)
    for ex, ey in a_terms:
        A ^= _mono(l, m, ex, ey)
    B = np.zeros((l * m, l * m), dtype=np.uint8)
    for ex, ey in b_terms:
        B ^= _mono(l, m, ex, ey)
    HX = np.hstack([A, B]).astype(np.uint8)
    HZ = np.hstack([B.T, A.T]).astype(np.uint8)
    n = 2 * l * m
    rx, rz = gf2_rank(HX), gf2_rank(HZ)
    k = n - rx - rz
    return dict(l=l, m=m, n=n, k=k, HX=HX, HZ=HZ, rank_X=rx, rank_Z=rz)


# Frozen catalogue from the published family.
CATALOGUE = {
    "[[72,12,6]]":   dict(l=6,  m=6,  a=[(3,0),(0,1),(0,2)], b=[(0,3),(1,0),(2,0)]),
    "[[108,8,10]]":  dict(l=9,  m=6,  a=[(3,0),(0,1),(0,2)], b=[(0,3),(1,0),(2,0)]),
    "[[144,12,12]]": dict(l=12, m=6,  a=[(3,0),(0,1),(0,2)], b=[(0,3),(1,0),(2,0)]),
    "[[288,12,18]]": dict(l=12, m=12, a=[(3,0),(0,2),(0,7)], b=[(0,3),(1,0),(2,0)]),
}

if __name__ == "__main__":
    print(f"{'code':>15} {'n':>5} {'k':>4} {'checks':>7} {'wt_r':>5} {'wt_c':>5} "
          f"{'CSS HX.HZ^T=0':>14} {'k matches':>10}")
    for name, p in CATALOGUE.items():
        c = bb_code(p["l"], p["m"], p["a"], p["b"])
        css = int(((c["HX"] @ c["HZ"].T) % 2).any()) == 0
        wr = c["HX"].sum(axis=1)
        wc = c["HX"].sum(axis=0)
        expect_k = int(name.split(",")[1])
        print(f"{name:>15} {c['n']:>5} {c['k']:>4} {c['HX'].shape[0]:>7} "
              f"{wr.min()}-{wr.max():<3} {wc.min()}-{wc.max():<3} "
              f"{str(css):>14} {str(c['k']==expect_k):>10}")
