# Scoping Result — CPU Decode Throughput vs. the IonQ MegaQuOp Claim

Date: 2026-09-01
Status: **EXPLORATORY / NON-CONFIRMATORY. Not preregistered. Not an SF-D0 execution.**
Machine: Intel Core Ultra 9 285K (24 cores), WSL2 Ubuntu 24.04, `cudaq-qec` env
Data: SF-L2 frozen corpus, **development split only**; validation and sealed test never read.

## Question

Ye, Maksymov & Delfosse (arXiv:2608.25027) report real-time decoding of a
MegaQuOp trapped-ion workload — 408 logical qubits — on a single CPU, with
<0.3% overhead at p_CNOT = 1e-4 and <12% at 5e-4. That result is stated against
an **assumed 1–5 ms trapped-ion cycle time**. This note asks what that
assumption is worth, by measuring decode cost directly and sweeping the clock.

## Method

PyMatching 2.4.0 sparse blossom, single core (`OMP_NUM_THREADS=1`), rotated
planar surface code d=7 (192 detectors x 511 fault locations, T=7 rounds),
matcher built from the frozen SF-L2 `H_space` with LLR edge weights
`w_j = log((1-p_j)/p_j)`.

Built **without** `faults_matrix`, so `decode()` returns a length-511 physical
correction rather than a logical prediction. Syndrome consistency
`H . c = s` over GF(2) verified 256/256 at every noise cell.

Timing: `decode_batch` over ~2,000 development shots, median of 5 repetitions.

## Result 1 — decode cost is syndrome-weight dominated

| noise cell | mean syndrome weight | us/shot | us/round |
|---|---|---|---|
| p1e-4 | 0.08 | 0.085 | 0.0121 |
| p3e-4 | 0.28 | 0.086 | 0.0122 |
| p1e-3 | 0.99 | 0.153 | 0.0219 |
| p3e-3 | 2.73 | 0.340 | 0.0486 |
| p1e-2 | 8.73 | 1.183 | 0.1690 |

Cost scales ~14x across the range, tracking mean detection-event count. Any
single-number decode cost quoted without its error rate is not meaningful.

## Result 2 — a surface-code budget comparison, not a replication

Scaling worst-case per-logical-qubit cost (p=1e-2, 0.169 us/round) to 408
logical qubits, assuming independent per-qubit decoding:

| workers | tau = 1 ms | tau = 5 ms |
|---|---|---|
| 1 core | 6.89% | 1.38% |
| 12 cores (their configuration) | 0.575% | 0.115% |
| 24 cores | 0.287% | 0.057% |

The cited percentages fall inside this projected band, but the comparison is
not like-for-like: this note uses a phenomenological surface-code model, while
the cited work uses a circuit-level qLDPC workload and reports observed stretch.
The two error-rate parameters cannot be rank-ordered. The calculation does show
that the cycle-time assumption materially changes the available decode budget.

## Result 3 — where this projected budget comparison crosses saturation

At tau = 1 us, the superconducting surface-code regime, CPU decoding saturates:

| workers | logical qubits sustained at d=7, tau = 1 us |
|---|---|
| 1 core | 5.9 |
| 12 cores | 71 |
| 24 cores | 142 |

Under this linear projection, a 24-core desktop sustains ~142 logical qubits at
superconducting cycle times, against the 408-logical scale of the cited
workload. The calculation illustrates that a sufficiency claim at millisecond
cycles does not transfer unchanged to a 1000× faster clock.

## Result 4 — the GPU arm LOSES, decisively

NVIDIA `nv-qldpc-decoder` (cudaq-qec 0.7.0) on the RTX 5090, same d=7 substrate,
same development shots, `max_iterations=50`, `bp_method=0`, `proc_float=fp64`:

| config | cell | syndrome consistency `H.c=s` | B=64 | B=512 | B=4096 (us/round) |
|---|---|---|---|---|---|
| BP only | p1e-3 | **230/256** | 18.50 | 3.19 | 2.34 |
| BP only | p1e-2 | **74/256** | 19.51 | 7.50 | 5.82 |
| BP + OSD-0 | p1e-3 | 256/256 | 19.53 | 3.99 | 2.87 |
| BP + OSD-0 | p1e-2 | 256/256 | 20.64 | 9.71 | 7.55 |

Head to head at p=1e-2, best GPU configuration against one CPU core:

    CPU  PyMatching sparse blossom : 0.169 us/round
    GPU  nv-qldpc BP+OSD, B=4096   : 7.550 us/round      ~45x SLOWER

At tau = 1 us the GPU arm sustains ~0.13 logical qubits at d=7, against 5.9 for
a single CPU core and 142 for 24 cores.

**This is not a statement that GPU decoding is bad.** It is a statement that a
GPU belief-propagation decoder is the wrong tool for a small, matchable code.
MWPM sparse blossom costs O(detection events) — about 9 per shot at p=1e-2 —
while BP performs 50 fixed iterations over the whole 192x511 matrix regardless
of how sparse the syndrome is. The GPU never reaches a scale where its
parallelism amortizes. `nv-qldpc-decoder` targets large qLDPC codes, where
standard graph matching is not directly applicable to the unsplit weight-3
representation; d<=7 rotated planar is close to the worst case for it.

## Result 5 — BP without OSD fails syndrome consistency

BP alone returns syndrome-inconsistent corrections on **26/256** shots at
p=1e-3 and **182/256** at p=1e-2. This is the surface-code degeneracy hazard,
observed rather than predicted. OSD-0 repairs it completely (256/256 at both).

Consequence for SF-D0: the v6 frozen Arm B configuration specified
`use_osd = False`, which **would have failed the Section 7 syndrome-consistency gate at
every noise cell**. That value was chosen because `osd_method`'s domain could
not be established by static string inspection. It can be established: see
below.

## Result 6 — decoder configuration domains, resolved

`cudaq_qec.decoder_param_schema("nv-qldpc-decoder")` returns a typed schema of
**23** parameters — more than the 21 in `_compat.py`'s field tuple, and far more
than static string scanning recovered. It also yields types, and runtime
validation yields domains:

- `proc_float` accepts **only** `"fp32"` or `"fp64"`. The v6 frozen value
  `"float64"` is **invalid** and would have aborted every Arm B configuration.
- `repeatable = True` requires `clip_value` to be **set and nonzero**.
  Determinism and LLR clipping are coupled; `clip_value = 0.0` reads as unset.
- `osd_method` and `osd_order` are `int32`, not strings. `osd_method = 0`,
  `osd_order = 0` construct and decode successfully.
- The schema additionally exposes `gamma_ensemble_size` and `repeatable`, which
  appear in neither `_compat.py` nor the compiled-string scan.

A schema-driven configuration preflight is strictly superior to static string
inspection and should replace it.

## Limitations

- Rotated planar surface code, not the qLDPC family of the cited work. Their
  code carries ~29 physical qubits per logical against ~97 here, so
  per-logical-qubit decode cost is not directly transferable.
- Phenomenological noise, not circuit-level.
- The 408x scaling is linear and assumes independent per-logical-qubit
  decoding. Real lattice surgery couples logical qubits and would cost more.
- `decode_batch` internal thread usage was not instrumented.
- Single machine, no repetition across fresh processes, no preregistration.
  **No adjudicable claim is made.**
- GPU timings include host-device transfer and synchronization but were not
  separated into transfer versus compute, so the GPU deficit is not attributed
  between launch overhead, transfer, and BP iteration cost.
- Only one GPU decoder was tested, in one parameter configuration family. A
  tuned or sliding-window configuration was not explored.

## Relationship to SF-D0

This note is exploratory and deliberately quarantined outside the repository.
It is not an SF-D0 execution and does not satisfy any SF-D0 endpoint. It does
mean SF-D0's frozen constants can no longer be described as chosen without
timing knowledge; if SF-D0 is later frozen, that must be disclosed or the
constants re-derived.
