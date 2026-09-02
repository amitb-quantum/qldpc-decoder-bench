"""QUARANTINED EXPLORATORY — qLDPC (bivariate bicycle) decode throughput on RTX 5090."""
import time
import numpy as np, scipy.sparse as sp
import cudaq_qec as qec
from bb_codes import bb_code, CATALOGUE
from spacetime import build_spacetime, sample, block_diag_repeat

RNG = np.random.default_rng(20260901)
P = 1e-3


def make_decoder(Hst, p_data, p_meas, n_data, batch, use_osd=True, max_iter=50):
    F = Hst.shape[1]
    pv = np.empty(F); pv[:n_data] = p_data; pv[n_data:] = p_meas
    kw = dict(use_sparsity=True, error_rate_vec=pv.tolist(), max_iterations=max_iter,
              n_threads=1, use_osd=use_osd, bp_method=0, bp_batch_size=int(batch),
              iter_per_check=1, clip_value=10.0, scale_factor=1.0,
              proc_float="fp64", bp_seed=1, repeatable=True)
    if use_osd:
        kw.update(osd_method=0, osd_order=0)
    return qec.get_decoder("nv-qldpc-decoder", Hst, **kw)


def corr(res):
    a = np.asarray(getattr(res, "result", res))
    return (a > 0.5).astype(np.uint8) if a.ndim == 2 else (a > 0.5).astype(np.uint8)[None, :]


def bench(label, Hst, n_data, T, shots, batch, use_osd=True):
    S, E = sample(Hst, P, P, n_data, shots, RNG)
    dec = make_decoder(Hst, P, P, n_data, batch, use_osd)
    dec.decode_batch(S[:min(batch, shots)])          # warm
    ts = []
    for _ in range(3):
        t0 = time.perf_counter_ns()
        dec.decode_batch(S)
        ts.append((time.perf_counter_ns() - t0) / 1e9)
    t = float(np.median(ts))
    C = corr(dec.decode_batch(S[:128]))
    prod = Hst @ C.T.astype(np.uint8)
    prod = np.asarray(prod.todense() if sp.issparse(prod) else prod, dtype=np.uint8)
    ok = int(((prod % 2).T == S[:128]).all(axis=1).sum())
    us_shot = t / shots * 1e6
    us_round = us_shot / T
    print(f"{label:<34} D={Hst.shape[0]:>6} F={Hst.shape[1]:>6} "
          f"nnz={Hst.nnz:>7}  conf {ok:>3}/128  "
          f"{us_shot:9.2f} us/shot  {us_round:8.3f} us/round")
    return us_round, ok


print("=" * 108)
print("qLDPC BIVARIATE BICYCLE — nv-qldpc-decoder on RTX 5090, phenomenological p=1e-3")
print("=" * 108)

print("\n--- single code block, T = d rounds ---")
res = {}
for name in ("[[72,12,6]]", "[[108,8,10]]", "[[144,12,12]]", "[[288,12,18]]"):
    p = CATALOGUE[name]
    c = bb_code(p["l"], p["m"], p["a"], p["b"])
    T = int(name.rstrip("]").split(",")[2])
    Hst = build_spacetime(c["HX"], T)
    ur, ok = bench(f"{name} T={T}", Hst, c["n"] * T, T, 1024, 512)
    res[name] = (ur, ok, c, T, Hst)

print("\n--- GPU scaling: gross code [[144,12,12]] repeated block-diagonally ---")
p = CATALOGUE["[[144,12,12]]"]; c = bb_code(p["l"], p["m"], p["a"], p["b"]); T = 12
H1 = build_spacetime(c["HX"], T)
n_data_1 = c["n"] * T
print(f"{'blocks':>7} {'logical':>8} {'physical':>9} {'D':>7} {'F':>7} "
      f"{'nnz':>8} {'us/shot':>10} {'us/round':>9} {'us/rnd/logical':>15}")
base = None
for blocks in (1, 2, 4, 8, 17, 34):
    try:
        Hb = block_diag_repeat(H1, blocks)
        nd = n_data_1 * blocks
        shots = 256 if blocks >= 17 else 512
        batch = shots
        S, _ = sample(Hb, P, P, nd, shots, RNG)
        dec = make_decoder(Hb, P, P, nd, batch)
        dec.decode_batch(S[:min(64, shots)])
        ts = []
        for _ in range(3):
            t0 = time.perf_counter_ns(); dec.decode_batch(S)
            ts.append((time.perf_counter_ns() - t0) / 1e9)
        t = float(np.median(ts))
        us = t / shots * 1e6; ur = us / T
        logical = 12 * blocks; physical = 288 * blocks
        if base is None: base = ur
        print(f"{blocks:>7} {logical:>8} {physical:>9} {Hb.shape[0]:>7} {Hb.shape[1]:>7} "
              f"{Hb.nnz:>8} {us:>10.2f} {ur:>9.3f} {ur/logical:>15.4f}")
    except (MemoryError, RuntimeError) as exc:
        logical = 12 * blocks; physical = 288 * blocks
        print(f"{blocks:>7} {logical:>8} {physical:>9} {'-':>7} {'-':>7} "
              f"{'-':>8} {'OOM':>10} {'-':>9} {'-':>15}  "
              f"({type(exc).__name__}: {str(exc)[:48]})")

print("\nExpected allocation failures are reported above and are non-fatal.")
print("Run src/run_scale2.py for the measured single-block batch sweep and")
print("the explicitly labeled 34-block serial aggregate projection.")
