"""Phenomenological space-time syndrome substrate for a CSS qLDPC code.

Detectors: (checks x (T+1)) — T measurement-difference layers plus a terminal
layer from ideal final readout.
Faults:    (n x T) data faults + (checks x T) measurement faults.

Column structure:
  data fault (q,t)   -> detector rows (c,t) for every check c with H[c,q]=1
  meas fault (c,t)   -> detector rows (c,t) and (c,t+1)
"""
import numpy as np
import scipy.sparse as sp


def build_spacetime(H, T):
    H = sp.csr_matrix(H.astype(np.uint8))
    mc, n = H.shape
    D = mc * (T + 1)
    F = n * T + mc * T
    rows, cols = [], []

    Hc = H.tocoo()
    for t in range(T):                      # data faults
        for r, c in zip(Hc.row, Hc.col):
            rows.append(t * mc + r)
            cols.append(t * n + c)
    off = n * T
    for t in range(T):                      # measurement faults
        for c in range(mc):
            rows.append(t * mc + c);       cols.append(off + t * mc + c)
            rows.append((t + 1) * mc + c); cols.append(off + t * mc + c)

    data = np.ones(len(rows), dtype=np.uint8)
    Hst = sp.coo_matrix((data, (rows, cols)), shape=(D, F)).tocsr()
    Hst.data %= 2
    Hst.eliminate_zeros()
    return Hst


def sample(Hst, p_data, p_meas, n_data_faults, shots, rng):
    """Sample fault vectors and their exact syndromes. Returns (S, E)."""
    F = Hst.shape[1]
    p = np.empty(F, dtype=np.float64)
    p[:n_data_faults] = p_data
    p[n_data_faults:] = p_meas
    E = (rng.random((shots, F)) < p).astype(np.uint8)
    S = (E @ Hst.T.astype(np.uint8)) % 2
    return np.asarray(S.todense() if sp.issparse(S) else S, dtype=np.uint8), E


def block_diag_repeat(Hst, blocks):
    return sp.block_diag([Hst] * blocks, format="csr")
