"""Batch sweep on a single gross-code block, plus the memory ceiling for block-diagonal."""
import time
import numpy as np, scipy.sparse as sp
import cudaq_qec as qec
from bb_codes import bb_code, CATALOGUE
from spacetime import build_spacetime, sample, block_diag_repeat

RNG=np.random.default_rng(7); P=1e-3; T=12
p=CATALOGUE["[[144,12,12]]"]; c=bb_code(p["l"],p["m"],p["a"],p["b"])
H1=build_spacetime(c["HX"],T); nd1=c["n"]*T

def mk(H,nd,batch):
    F=H.shape[1]; pv=np.empty(F); pv[:nd]=P; pv[nd:]=P
    return qec.get_decoder("nv-qldpc-decoder",H,use_sparsity=True,
        error_rate_vec=pv.tolist(),max_iterations=50,n_threads=1,use_osd=True,
        osd_method=0,osd_order=0,bp_method=0,bp_batch_size=int(batch),
        iter_per_check=1,clip_value=10.0,scale_factor=1.0,proc_float="fp64",
        bp_seed=1,repeatable=True)

print("=== single gross-code block: batch sweep (independent-block decoding model) ===")
print(f"{'batch':>7} {'us/shot':>10} {'us/round':>10} {'blocks/s @12rnd':>16}")
best=None
S,_=sample(H1,P,P,nd1,8192,RNG)
for B in (64,256,1024,4096,8192):
    try:
        dec=mk(H1,nd1,B); Sb=S[:B]
        dec.decode_batch(Sb[:min(64,B)])
        ts=[]
        for _ in range(3):
            t0=time.perf_counter_ns(); dec.decode_batch(Sb); ts.append((time.perf_counter_ns()-t0)/1e9)
        t=float(np.median(ts)); us=t/B*1e6
        print(f"{B:>7} {us:>10.2f} {us/T:>10.3f} {1e6/us:>16.0f}")
        if best is None or us<best: best=us
    except Exception as e:
        print(f"{B:>7}  FAILED {type(e).__name__}: {str(e)[:40]}")

if best is None:
    raise RuntimeError("No batch size completed successfully; cannot project aggregate throughput.")

print(f"\nbest per-block: {best:.2f} us/shot  ({best/T:.3f} us/round)")
print("\n=== projected serial aggregate: 408 logical qubits in 34 independent blocks ===")
per_machine_shot = best*34
print(f"  projected serial cost : {per_machine_shot:9.1f} us/shot  "
      f"{per_machine_shot/T:8.2f} us/round")
print(f"  budget fraction, 1ms  : {per_machine_shot/T/1000*100:.3f}%")
print(f"  budget fraction, 5ms  : {per_machine_shot/T/5000*100:.3f}%")
print(f"  tau_crit (fraction=1) : {per_machine_shot/T:.2f} us/round")
print("  note                  : throughput projection, not measured live latency")

print("\n=== block-diagonal monolith: memory ceiling ===")
for blocks in (17,20,24,28,34):
    Hb=block_diag_repeat(H1,blocks); nd=nd1*blocks
    for B in (256,64,16):
        try:
            dec=mk(Hb,nd,B)
            S2,_=sample(Hb,P,P,nd,B,RNG)
            dec.decode_batch(S2)
            print(f"  blocks={blocks:>3} D={Hb.shape[0]:>6} F={Hb.shape[1]:>6}: OK at batch {B}")
            break
        except Exception as e:
            if B==16:
                print(f"  blocks={blocks:>3} D={Hb.shape[0]:>6} F={Hb.shape[1]:>6}: "
                      f"FAILED even at batch 16 — {type(e).__name__}")
