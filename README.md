# qldpc-decoder-bench

**Independent qLDPC decoding throughput study motivated by the MegaQuOp-scale
regime, on a single consumer GPU.**

This repository tests the broader throughput-scale observation motivating
[**arXiv:2608.25027**](https://arxiv.org/abs/2608.25027) — Min Ye, Andrii
Maksymov & Nicolas Delfosse, *"Real-time decoder for a MegaQuOp quantum computer
using a single CPU"* (IonQ, 2026) — using bivariate bicycle qLDPC codes and
NVIDIA's `nv-qldpc-decoder` on an RTX 5090. It is an independent corroborating
throughput study, not a replication of the paper's end-to-end experiment.

It also examines how the throughput interpretation changes with the assumed
**hardware cycle time**.

> **Status:** exploratory measurement. Single machine, no repetition across
> fresh processes, not preregistered. Decode cost only — no logical error rate,
> threshold, or accuracy claim is made.

---

## TL;DR

| | |
|---|---|
| Codes | Bivariate bicycle, incl. the gross code `[[144,12,12]]`, constructed and CSS-verified from scratch |
| Aggregate scale projected | **408 logical qubits / 9,792 physical** across 34 independent blocks |
| Projected serial aggregate | **101.25 µs/round**, from measured batch throughput for one block |
| Decoder budget fraction at τ = 1 ms | **10.125 %** |
| Decoder budget fraction at τ = 5 ms | **2.025 %** |
| Comparison boundary | Phenomenological `p` and budget fraction here; circuit-level `p_CNOT` and observed stretch in the cited work |
| Syndrome consistency | `H·c = s` over GF(2), **128/128 on every measured code** |

**The broader scalability observation is corroborated.** Measured per-block
batch throughput projects to a 408-logical-qubit serial aggregate inside 1 ms
and 5 ms syndrome-cycle budgets. This is not a measured 34-block decode, and
its phenomenological `p = 1e-3` cannot be ranked against the paper's
circuit-level `p_CNOT` operating points.

**And the assumption matters.** The paper's 1–5 ms budget comes from trapped-ion
cycle times. A superconducting surface-code cycle is ~1 µs. Sweeping the clock
is where the interesting structure lives.

---

## In plain language

**The problem.** Quantum computers make mistakes constantly — far too often to
be useful on their own. The fix is quantum error correction: you spread one
reliable "logical" qubit across many unreliable physical ones, then repeatedly
measure the system to ask *"has anything gone wrong?"* Those measurements
produce a stream of clues called a **syndrome**. They don't tell you what the
error was; a classical computer has to work that out. That program is the
**decoder**.

**The catch.** The decoder has to keep up. The quantum machine emits a fresh
round of syndrome data on a fixed clock, and if the decoder is slower than that
clock, unprocessed data piles up faster than it can be cleared. The lag grows
without bound and the machine effectively stalls. This is the *backlog problem*,
and it is why decoding speed is a real engineering constraint rather than a
detail.

Think of it as proofreading a book while it is being printed. If a page comes
off the press every second and you need two seconds a page, you fall behind
forever. **How fast the press runs matters as much as how fast you read.**

**Two ways to build the code.** *Surface codes* are the well-known approach:
simple, robust, and easy to decode with a fast algorithm called minimum-weight
matching. But they are expensive — in our measurements, about **97 physical
qubits for every logical one**. *qLDPC codes*, and specifically the CSS
bivariate-bicycle family used here, are far thriftier: about **24 physical
qubits per logical**, roughly a 4× saving. On hardware where every physical
qubit is precious, that difference is enormous.

**The price of thrift.** Standard graph-matching decoders are not directly
applicable to the unsplit Tanner-graph representation used here. Matching
expects each fault to touch at most two clues; in these codes each data fault
touches three. This motivates qLDPC-specific approaches such as belief
propagation, beam search, and related hypergraph-aware methods. This repository
benchmarks **belief propagation with OSD post-processing**, whose repetitive
arithmetic is well suited to a GPU.

**What the original paper showed.** An IonQ team
([arXiv:2608.25027](https://arxiv.org/abs/2608.25027)) demonstrated that a
single laptop CPU could decode a large quantum workload — 408 logical qubits —
in real time, with only a few percent overhead. A genuinely useful result.

The hardware context matters: trapped-ion syndrome-extraction cycles are
millisecond-scale, while superconducting cycles can be microsecond-scale. Going
back to the printing analogy, the two presses run at very different rates, so a
decoder that keeps up with one is not automatically fast enough for the other.

**What this repository does.** We rebuilt the qLDPC codes from scratch,
generated syndrome data, and measured single-block batch throughput on an
off-the-shelf RTX 5090. We then projected the measured per-block cost across 34
independent blocks, corresponding to 408 logical qubits.

The resulting serial aggregate consumes **10.125% of a 1 ms cycle budget and
2.025% of a 5 ms budget**. These are decode-time / cycle-time ratios, not the
paper's observed backlog-stretch metric, and the two noise parameters are not
directly comparable.

Along the way we found three practical things:

- **Feeding the GPU more work at once stops helping.** Performance peaks at 256
  problems per batch and gets meaningfully *worse* beyond that.
- **You run out of graphics memory before you run out of speed.** 32 GB caps how
  much of the problem can be handled as one piece — but the code blocks are
  independent, so they can simply be decoded separately.
- **The GPU is the wrong tool for surface codes.** On those, one CPU core beats
  the RTX 5090 by roughly 45×, because matching only inspects the handful of
  clues that actually fired, while belief propagation grinds through the entire
  problem every time regardless. A GPU is more interesting where standard graph
  matching is not directly applicable — which is the qLDPC case studied here.

**The honest summary.** These measurements support the feasibility of
large-scale qLDPC decoding on consumer hardware under millisecond-scale cycle
budgets. They do not establish end-to-end real-time operation. On faster
hardware the same arithmetic gets much tighter — and that is the regime where
the choice of decoder and processor starts to matter a great deal.

---

## Background: what the paper claims, and what rests on what

Ye, Maksymov & Delfosse demonstrate an end-to-end real-time decoding system for
fault-tolerant trapped-ion quantum computers, reporting:

- up to **408 logical qubits**, ~11,680 physical, over 1M operations;
- decoding overhead **< 0.3 %** at two-qubit gate error `1e-4`;
- decoding overhead **< 12 %** at `5e-4`;
- executed on a **2024 M4 Max MacBook Pro**, using 12 of 16 CPU cores.

The result is real and the engineering is substantial. But a time-budget ratio
depends on the syndrome-extraction cycle as well as decoder service time, so it
is not a property of the decoder alone. The cited work uses millisecond-scale
trapped-ion cycles; its 408-logical-qubit workload uses a 5 ms syndrome-
extraction cycle, while 1 ms applies to smaller 102-logical-qubit workloads.

This repository therefore measures **absolute decode cost in µs per syndrome
round**, and reports a **decoder budget fraction** across selected cycle times.
That ratio is not identical to the cited work's observed execution stretch.

---

## What is compared, and what is not

**Compared**

- qLDPC code family (bivariate bicycle) rather than surface codes
- Comparable logical-qubit count (408) in the projected serial aggregate
- Multi-round space-time syndrome decoding
- Decode-time / cycle-time ratio evaluated against 1 ms and 5 ms budgets
- Commodity, non-datacenter hardware

**Not reproduced**

- The Walking Cat Architecture execution stack, compiled workloads, logical
  operations, magic-state factories, or live backlog/stall behavior
- Sliding-window beam-search decoding and on-the-fly detector error modeling
- The exact code construction and workload used in the cited work
- **Phenomenological noise**, not circuit-level — no syndrome-extraction circuit
  is simulated, so these are not end-to-end logical error rates
- No trapped-ion hardware, no closed-loop control system, no real QPU
- Their decoder is CPU-based; this study measures a **GPU** BP+OSD decoder

---

## Theory: bivariate bicycle codes

Following Bravyi *et al.*, *Nature* **627**, 778 (2024). Over the group algebra
`F₂[x,y]/(xˡ − 1, yᵐ − 1)`:

```
x = S_l ⊗ I_m          y = I_l ⊗ S_m          (S = cyclic shift)
A = A₁ + A₂ + A₃       B = B₁ + B₂ + B₃       (monomials in x, y)
H_X = [A | B]          H_Z = [Bᵀ | Aᵀ]
```

giving `n = 2lm` data qubits and `lm` checks of each type. `src/bb_codes.py`
builds these and verifies, exactly over GF(2), that `H_X · H_Zᵀ = 0` and that
`k = n − rank(H_X) − rank(H_Z)` matches the published parameters.

| code | n | k | checks | row wt | col wt | `H_X·H_Zᵀ = 0` | k matches |
|---|---|---|---|---|---|---|---|
| `[[72,12,6]]` | 72 | 12 | 36 | 6 | 3 | ✅ | ✅ |
| `[[108,8,10]]` | 108 | 8 | 54 | 6 | 3 | ✅ | ✅ |
| `[[144,12,12]]` *(gross)* | 144 | 12 | 72 | 6 | 3 | ✅ | ✅ |
| `[[288,12,18]]` | 288 | 12 | 144 | 6 | 3 | ✅ | ✅ |

### Why this motivates a qLDPC-specific decoder

**Column weight is 3.** Minimum-weight perfect matching requires every fault to
touch at most **2** detectors, so that faults form edges in a graph. These codes
violate that condition in the unsplit representation used here. Standard graph-
matching decoders such as PyMatching and Fusion Blossom are therefore not
directly applicable without a transformation. qLDPC-specific alternatives
include BP-based, beam-search, and other hypergraph-aware decoders; this study
uses BP+OSD because it is available in CUDA-Q QEC and maps naturally to a GPU.

This is the structural reason a GPU is interesting here and was not interesting
for surface codes (see [Result 4](#result-4--surface-code-vs-qldpc-the-honest-trade)).

---

## Method: space-time syndrome substrate

`src/spacetime.py` builds a phenomenological multi-round detector model:

- **Detectors:** `checks × (T+1)` — `T` measurement-difference layers plus one
  terminal layer from ideal final readout.
- **Faults:** `n × T` data faults + `checks × T` measurement faults.

Column structure:

```
data fault (q,t)  →  detector rows (c,t) for every check c with H[c,q] = 1
meas fault (c,t)  →  detector rows (c,t) and (c,t+1)
```

Syndromes are sampled by drawing independent faults at rate `p` and computing
the exact syndrome over GF(2). Every decoded correction is verified to satisfy
`H·c = s` exactly before any timing is reported.

---

## Results

All figures: RTX 5090, `nv-qldpc-decoder` (CUDA-Q QEC 0.7.0), BP + OSD-0,
`max_iterations = 50`, `proc_float = fp64`, phenomenological `p = 1e-3`,
`T = d` rounds. Raw output in [`results/run_001.log`](results/run_001.log),
with provenance notes in [`results/README.md`](results/README.md).

### Single-block throughput

| code | detectors | faults | nnz | syndrome consistency | µs/shot | µs/round |
|---|---|---|---|---|---|---|
| `[[72,12,6]]` | 252 | 648 | 1,728 | 128/128 | 9.28 | 1.547 |
| `[[108,8,10]]` | 594 | 1,620 | 4,320 | 128/128 | 32.01 | 3.201 |
| `[[144,12,12]]` | 936 | 2,592 | 6,912 | 128/128 | 51.72 | 4.310 |
| `[[288,12,18]]` | 2,736 | 7,776 | 20,736 | 128/128 | 154.78 | 8.599 |

### Result 1 — batch size has a sweet spot, and it is not the largest

Gross code, single block:

| batch | µs/shot | µs/round |
|---|---|---|
| 64 | 66.15 | 5.512 |
| **256** | **35.73** | **2.978** |
| 1024 | 51.99 | 4.332 |
| 4096 | 55.84 | 4.653 |
| 8192 | 62.15 | 5.179 |

Throughput peaks at batch 256 and **degrades ~1.7× by batch 8192**. Bigger
batches are not uniformly better on this decoder — a practical tuning result for
anyone deploying it.

### Result 2 — projected serial aggregate at 408 logical qubits

34 independent gross-code blocks = **408 logical qubits, 9,792 physical**
(144 data + 144 ancilla per block):

```
projected serial cost       1,215.0 µs/shot   =   101.25 µs/round
decoder budget fraction at τ = 1 ms                    10.125 %
decoder budget fraction at τ = 5 ms                     2.025 %
τ_crit (budget fraction = 100%)                       101.25 µs/round
headroom at τ = 1 ms                                    9.88×
```

This is `34 ×` the measured batch-256 cost of one independent gross-code block.
It is a **projected serial aggregate throughput**, not a measured 34-block
decode and not a per-syndrome live latency measurement. Batch 256 measures
throughput across independent syndrome histories; the actual construction has
34-way block concurrency.

The 5 ms budget is the cleaner scale comparison because the cited paper's
408-logical workload uses a 5 ms syndrome-extraction cycle. Even then, this
study's 2.025% budget fraction is not the paper's stretch metric, and
phenomenological `p = 1e-3` is not directly comparable to circuit-level
`p_CNOT`. The result corroborates the broader throughput-scale observation
without claiming experimental replication.

### Result 3 — the block-diagonal monolith hits a hard memory ceiling

Decoding all blocks as one block-diagonal parity-check matrix:

| blocks | logical | detectors | faults | result |
|---|---|---|---|---|
| 17 | 204 | 15,912 | 44,064 | OK at batch 256 |
| 20 | 240 | 18,720 | 51,840 | OK at batch 256 |
| 24 | 288 | 22,464 | 62,208 | OK at batch 256 |
| 28 | 336 | 26,208 | 72,576 | OK at batch 256 |
| **34** | **408** | **31,824** | **88,128** | **`std::bad_alloc`, even at batch 16** |

32 GB of VRAM caps the monolithic approach at **~28 gross-code blocks**.

Per-logical-qubit cost also *degrades* under the monolithic model — 0.2394
µs/round/logical at 1 block, 0.4573 at 17 — so the decoder does not exploit
block-diagonal structure. Independent per-block decoding is both cheaper and
architecturally correct, since separate code blocks share no checks.

### Result 4 — surface code vs qLDPC, the honest trade

At `p = 1e-3`, per logical qubit:

| approach | decoder | µs/round/logical | physical/logical |
|---|---|---|---|
| rotated planar `d=7` | PyMatching MWPM, **1 CPU core** | **0.0219** | 97 |
| gross code `[[144,12,12]]` | nv-qldpc BP+OSD, **RTX 5090** | 0.248 | **24** |

Surface-code MWPM on a single CPU core is **~11× cheaper per logical qubit**.
The gross code is **~4× cheaper in physical qubits**. That is the qLDPC bargain
stated quantitatively: fewer physical qubits, materially harder decoding, and
standard graph matching is not directly applicable to this unsplit qLDPC
representation.

A companion measurement on rotated planar surface codes — including the finding
that this GPU decoder is ~45× *slower* than one CPU core on `d ≤ 7` surface
codes, because BP runs 50 fixed iterations regardless of syndrome sparsity while
sparse blossom costs `O(detection events)` — is in
[`results/surface_code_cpu_scoping_note.md`](results/surface_code_cpu_scoping_note.md).

---

## Reproducing

```bash
python src/bb_codes.py          # construct and verify the code family
python src/run_qldpc_bench.py   # single-block and block-scaling throughput; expected OOM is non-fatal
python src/run_scale2.py        # batch sweep, 408-logical point, memory ceiling
```

**Environment used**

| component | version |
|---|---|
| GPU | NVIDIA GeForce RTX 5090, 32,607 MiB, sm_120 |
| Driver / CUDA | 610.53 / 13.3 |
| CPU | Intel Core Ultra 9 285K, 24 cores |
| OS | WSL2, Ubuntu 24.04, kernel 6.18.33.2-microsoft-standard-WSL2 |
| Python | 3.11.10 |
| CUDA-Q | 0.15.1 |
| CUDA-Q QEC | 0.7.0 (`cudaq-qec-cu13`) |
| CuPy | 13.6.0 |
| NumPy / SciPy | 2.4.6 / 1.17.1 |
| PyMatching | 2.4.0 (surface-code comparison only) |

---

## Notes for anyone using `nv-qldpc-decoder`

Three parameter constraints cost real debugging time and are not obvious from
the parameter names:

- `proc_float` accepts **only** `"fp32"` or `"fp64"`. `"float64"` is rejected.
- `repeatable = True` requires `clip_value` to be **set and nonzero**;
  `clip_value = 0.0` reads as unset and the constructor refuses.
- `osd_method` and `osd_order` are **`int32`**, not strings.

`cudaq_qec.decoder_param_schema("nv-qldpc-decoder")` returns the full typed
schema — 23 parameters — and is far more reliable than reading field lists out
of compatibility shims.

**BP without OSD fails syndrome consistency on surface codes.** In the companion
measurement, BP alone returned syndrome-inconsistent corrections on 26/256 shots
at `p = 1e-3` and 182/256 at `p = 1e-2` — the classic degeneracy failure. OSD-0
repaired it completely. On the qLDPC codes here, BP+OSD-0 was
syndrome-consistent 128/128 throughout.

---

## Limitations

- **Phenomenological noise, not circuit-level.** No syndrome-extraction circuit
  is simulated. These are not end-to-end logical error rates.
- **Decode cost only.** No logical error rate, threshold, or accuracy claim.
- The 408-logical figure is `34 ×` measured single-block batch throughput,
  **not** a measured 34-block decode or live latency result — the monolith does
  not fit in 32 GB.
- GPU timings include host-device transfer and synchronization, not separated
  from compute time.
- One decoder, one parameter family. No sliding-window or relay-BP
  configuration was explored.
- Single machine, one retained full GPU execution, no fresh-process repetition,
  no preregistration. The README reports only values present in the committed
  raw log.
- The cited paper's exact code construction is not public; the bivariate bicycle
  family is a reasonable but not identical stand-in.

---

## References

1. M. Ye, A. Maksymov, N. Delfosse, *"Real-time decoder for a MegaQuOp quantum
   computer using a single CPU"*, [arXiv:2608.25027](https://arxiv.org/abs/2608.25027) (2026).
   — the work motivating the scale comparison.
2. S. Bravyi, A. W. Cross, J. M. Gambetta, D. Maslov, P. Rall, T. J. Yoder,
   *"High-threshold and low-overhead fault-tolerant quantum memory"*,
   [Nature **627**, 778–782 (2024)](https://www.nature.com/articles/s41586-024-07107-7).
   — the bivariate bicycle code family.
3. O. Higgott, C. Gidney, *"Sparse Blossom: correcting a million errors per core
   second with minimum-weight matching"*,
   [arXiv:2303.15933](https://arxiv.org/abs/2303.15933) (2023). — PyMatching.
4. NVIDIA, *CUDA-Q QEC* (`cudaqx`), v0.7.0.
   [github.com/NVIDIA/cudaqx](https://github.com/NVIDIA/cudaqx) — `nv-qldpc-decoder`.

## License

MIT — see [LICENSE](LICENSE).
