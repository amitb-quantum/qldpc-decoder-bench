# Benchmark provenance

`run_001.log` is the sole retained full GPU execution behind the values reported
in the project README. The README intentionally reports only values present in
this committed log; an earlier two-run range was removed because the second raw
output was not retained.

| field | value |
|---|---|
| execution date | 2026-09-01 |
| benchmark scripts | `src/bb_codes.py`, `src/run_qldpc_bench.py`, `src/run_scale2.py` |
| RNG seeds | `20260901` (`run_qldpc_bench.py`), `7` (`run_scale2.py`) |
| noise model | phenomenological data and measurement faults, `p = 1e-3` |
| GPU | NVIDIA GeForce RTX 5090, 32,607 MiB |
| CUDA-Q / CUDA-Q QEC | 0.15.1 / 0.7.0 |
| raw-log SHA-256 | `db0a258349bc474583999b99aa276b40cfcbbdbc4156974ae88b34f43ca583e0` |

The traceback in `run_001.log` records the observed 34-block monolithic
allocation failure. The current benchmark script reports that expected failure
without aborting, allowing the remaining reproduction commands to complete.

The 408-logical-qubit result is a projected serial aggregate:

```text
35.73 µs/shot/block × 34 blocks ÷ 12 rounds ≈ 101.25 µs/round
```

It is not a measured 34-block decode or a live-latency measurement.
