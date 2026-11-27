# Final results: results/final_NVIDIA-H100-80GB-HBM3 (78 of 80 configurations; quality seq/par apc=off C=4 pending)

78 configurations loaded.

## Preregistered decision rules

| Rule | Quantity | Value [95% CI] | Threshold | Verdict |
|---|---|---|---|---|
| 1 | gsm8k L1 speedup at C=1 | 2.32 [2.19, 2.48] | >= 1.5, lower bound > 1.2 | met |
| 1 | quality L1 speedup at C=1 | 2.24 [2.15, 2.37] | >= 1.5, lower bound > 1.2 | met |
| 2 | gsm8k L1 gain C=32 vs C=1 | 0.57 vs 1.32 (C=32 speedup 1.57 [1.50, 1.64]) | < half | met |
| 2 | quality L1 gain C=32 vs C=1 | 0.32 vs 1.24 (C=32 speedup 1.32 [1.29, 1.39]) | < half | met |
| 3 | QuALITY L2 loss C=16 vs C=1 | 14.33 [13.57, 15.13] s vs 0.94 [0.81, 1.08] s (141.2% of T) | >= 2x and >= 10% | met |
| 3 | GSM8K L2 loss at C=1 | -0.04 [-0.17, 0.19] s (-1.5% of T) | < 5% | met |
| 4 | QuALITY L3 at C=16: prefill cut, median T cut | 7.7%, 9.4% (T ratio 0.91 [0.88, 0.97]) | >= 30%, >= 10% | not met |
| 5 | gsm8k noise floor: BASE repeat vs BASE (seed 0) | 0.0 pp, 0/0 discordant, p=1.000 | reference | - |
| 5 | gsm8k par apc=on vs BASE, C=1 | 0.3 pp (86.0% vs 85.7%, n=300, 6/5, p=1.000) | not < -2.0 pp, not sig. lower | held |
| 5 | gsm8k l3a apc=on vs BASE, C=1 | -2.0 pp (83.7% vs 85.7%, n=300, 3/9, p=0.146) | not < -2.0 pp, not sig. lower | held |
| 5 | gsm8k l3 apc=on vs BASE, C=1 | -1.3 pp (84.3% vs 85.7%, n=300, 6/10, p=0.454) | not < -2.0 pp, not sig. lower | held |
| 5 | gsm8k par apc=off vs BASE, C=1 | -1.0 pp (84.7% vs 85.7%, n=300, 9/12, p=0.664) | not < -2.0 pp, not sig. lower | held |
| 5 | gsm8k seq apc=off vs BASE, C=1 | 0.3 pp (86.0% vs 85.7%, n=300, 5/4, p=1.000) | not < -2.0 pp, not sig. lower | held |
| 5 | quality noise floor: BASE repeat vs BASE (seed 0) | 0.0 pp, 0/0 discordant, p=1.000 | reference | - |
| 5 | quality par apc=on vs BASE, C=1 | 0.7 pp (75.0% vs 74.3%, n=300, 17/15, p=0.860) | not < -2.0 pp, not sig. lower | held |
| 5 | quality l3a apc=on vs BASE, C=1 | 2.0 pp (76.3% vs 74.3%, n=300, 21/15, p=0.405) | not < -2.0 pp, not sig. lower | held |
| 5 | quality l3 apc=on vs BASE, C=1 | 2.7 pp (77.0% vs 74.3%, n=300, 22/14, p=0.243) | not < -2.0 pp, not sig. lower | held |
| 5 | quality par apc=off vs BASE, C=1 | -1.3 pp (73.0% vs 74.3%, n=300, 18/22, p=0.636) | not < -2.0 pp, not sig. lower | held |
| 5 | quality seq apc=off vs BASE, C=1 | -0.7 pp (73.7% vs 74.3%, n=300, 15/17, p=0.860) | not < -2.0 pp, not sig. lower | held |

## H2: critical path and factorial at C=1

| Task | L1 speedup | Critical-path bound | Share of bound | Answer-length spread (tokens, median) |
|---|---:|---:|---:|---:|
| gsm8k | 2.32 | 2.38 | 98% | 68 |
| quality | 2.24 | 2.39 | 93% | 70 |

| Task | T seq/off | T par/off | T seq/on (BASE) | T par/on | Interaction (s) |
|---|---:|---:|---:|---:|---:|
| gsm8k | 6.58 | 2.77 | 6.50 | 2.81 | 0.12 |
| quality | 7.93 | 4.07 | 7.00 | 3.13 | -0.00 |

## All configurations

| Task | Mode | APC | C | Seed | n | median T (s) | p95 T (s) | prefill tok/task | cache hit | accuracy |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| gsm8k | l3 | on | 1 | 0 | 100 | 3.05 | 5.37 | 1201 | 0.70 | 0.89 |
| gsm8k | l3a | on | 1 | 0 | 100 | 2.61 | 5.02 | 1830 | 0.43 | 0.86 |
| gsm8k | par | off | 1 | 0 | 100 | 2.76 | 5.16 | 3105 | 0.00 | 0.86 |
| gsm8k | par | on | 1 | 0 | 100 | 2.63 | 4.22 | 1826 | 0.41 | 0.88 |
| gsm8k | seq | off | 1 | 0 | 100 | 5.98 | 11.24 | 3038 | 0.00 | 0.89 |
| gsm8k | seq | on | 1 | 0 | 100 | 6.39 | 10.97 | 1838 | 0.41 | 0.89 |
| gsm8k | seq (repeat) | on | 1 | 0 | 100 | 6.36 | 10.89 | 1838 | 0.41 | 0.89 |
| gsm8k | single | on | 1 | 0 | 100 | 1.23 | 2.31 | 96 | 0.24 | 0.84 |
| gsm8k | l3 | on | 1 | 1 | 100 | 3.10 | 6.21 | 1224 | 0.70 | 0.84 |
| gsm8k | l3a | on | 1 | 1 | 100 | 2.88 | 6.08 | 1814 | 0.43 | 0.84 |
| gsm8k | par | off | 1 | 1 | 100 | 2.80 | 5.17 | 3032 | 0.00 | 0.84 |
| gsm8k | par | on | 1 | 1 | 100 | 2.69 | 5.48 | 1798 | 0.41 | 0.88 |
| gsm8k | seq | off | 1 | 1 | 100 | 6.88 | 11.94 | 3080 | 0.00 | 0.85 |
| gsm8k | seq | on | 1 | 1 | 100 | 6.58 | 11.80 | 1824 | 0.41 | 0.86 |
| gsm8k | single | on | 1 | 1 | 100 | 1.27 | 2.79 | 96 | 0.24 | 0.82 |
| gsm8k | l3 | on | 1 | 2 | 100 | 2.97 | 5.37 | 1206 | 0.70 | 0.80 |
| gsm8k | l3a | on | 1 | 2 | 100 | 2.68 | 4.90 | 1832 | 0.43 | 0.81 |
| gsm8k | par | off | 1 | 2 | 100 | 2.75 | 4.37 | 3132 | 0.00 | 0.84 |
| gsm8k | par | on | 1 | 2 | 100 | 2.75 | 4.93 | 1827 | 0.41 | 0.82 |
| gsm8k | seq | off | 1 | 2 | 100 | 6.37 | 11.16 | 3096 | 0.00 | 0.84 |
| gsm8k | seq | on | 1 | 2 | 100 | 6.47 | 12.06 | 1803 | 0.41 | 0.82 |
| gsm8k | single | on | 1 | 2 | 100 | 1.23 | 2.41 | 96 | 0.24 | 0.78 |
| gsm8k | l3 | on | 4 | 0 | 300 | 3.40 | 6.58 | 1222 | 0.71 | 0.85 |
| gsm8k | l3a | on | 4 | 0 | 300 | 3.11 | 5.58 | 1867 | 0.43 | 0.85 |
| gsm8k | par | off | 4 | 0 | 300 | 3.29 | 6.44 | 3158 | 0.00 | 0.84 |
| gsm8k | par | on | 4 | 0 | 300 | 3.07 | 5.92 | 1851 | 0.41 | 0.85 |
| gsm8k | seq | off | 4 | 0 | 300 | 7.14 | 12.52 | 3105 | 0.00 | 0.86 |
| gsm8k | seq | on | 4 | 0 | 300 | 6.91 | 13.17 | 1836 | 0.41 | 0.87 |
| gsm8k | l3 | on | 16 | 0 | 300 | 4.34 | 8.07 | 1224 | 0.71 | 0.88 |
| gsm8k | l3a | on | 16 | 0 | 300 | 4.18 | 7.98 | 1877 | 0.43 | 0.85 |
| gsm8k | par | off | 16 | 0 | 300 | 4.91 | 9.36 | 3159 | 0.00 | 0.83 |
| gsm8k | par | on | 16 | 0 | 300 | 4.22 | 9.00 | 1840 | 0.41 | 0.87 |
| gsm8k | seq | off | 16 | 0 | 300 | 8.65 | 15.72 | 3159 | 0.00 | 0.86 |
| gsm8k | seq | on | 16 | 0 | 300 | 8.10 | 14.55 | 1844 | 0.41 | 0.88 |
| gsm8k | l3 | on | 32 | 0 | 300 | 6.47 | 10.54 | 1218 | 0.71 | 0.83 |
| gsm8k | l3a | on | 32 | 0 | 300 | 6.22 | 10.09 | 1860 | 0.43 | 0.85 |
| gsm8k | par | off | 32 | 0 | 300 | 6.85 | 11.90 | 3105 | 0.00 | 0.83 |
| gsm8k | par | on | 32 | 0 | 300 | 5.91 | 11.03 | 1839 | 0.41 | 0.87 |
| gsm8k | seq | off | 32 | 0 | 300 | 9.99 | 17.83 | 3123 | 0.00 | 0.87 |
| gsm8k | seq | on | 32 | 0 | 300 | 9.26 | 16.27 | 1860 | 0.41 | 0.85 |
| quality | l3 | on | 1 | 0 | 100 | 2.96 | 4.87 | 7764 | 0.86 | 0.80 |
| quality | l3a | on | 1 | 0 | 100 | 3.14 | 4.52 | 8436 | 0.83 | 0.79 |
| quality | par | off | 1 | 0 | 100 | 4.01 | 5.33 | 42405 | 0.00 | 0.77 |
| quality | par | on | 1 | 0 | 100 | 3.02 | 4.45 | 8376 | 0.80 | 0.73 |
| quality | seq | off | 1 | 0 | 100 | 8.04 | 10.40 | 42624 | 0.00 | 0.74 |
| quality | seq | on | 1 | 0 | 100 | 6.97 | 9.61 | 8353 | 0.80 | 0.74 |
| quality | seq (repeat) | on | 1 | 0 | 100 | 6.94 | 9.64 | 8353 | 0.80 | 0.74 |
| quality | single | on | 1 | 0 | 100 | 1.43 | 2.50 | 6670 | 0.00 | 0.72 |
| quality | l3 | on | 1 | 1 | 100 | 3.19 | 4.64 | 7764 | 0.86 | 0.77 |
| quality | l3a | on | 1 | 1 | 100 | 3.15 | 4.70 | 8424 | 0.83 | 0.75 |
| quality | par | off | 1 | 1 | 100 | 4.04 | 5.81 | 42532 | 0.00 | 0.75 |
| quality | par | on | 1 | 1 | 100 | 3.17 | 4.58 | 8465 | 0.80 | 0.78 |
| quality | seq | off | 1 | 1 | 100 | 7.80 | 11.70 | 42579 | 0.00 | 0.74 |
| quality | seq | on | 1 | 1 | 100 | 6.92 | 9.58 | 8344 | 0.80 | 0.71 |
| quality | single | on | 1 | 1 | 100 | 1.48 | 2.47 | 6670 | 0.00 | 0.69 |
| quality | l3 | on | 1 | 2 | 100 | 3.05 | 5.02 | 7776 | 0.86 | 0.74 |
| quality | l3a | on | 1 | 2 | 100 | 3.13 | 5.00 | 8407 | 0.83 | 0.75 |
| quality | par | off | 1 | 2 | 100 | 4.06 | 5.95 | 42531 | 0.00 | 0.67 |
| quality | par | on | 1 | 2 | 100 | 3.17 | 4.78 | 8304 | 0.80 | 0.74 |
| quality | seq | off | 1 | 2 | 100 | 7.81 | 10.86 | 42538 | 0.00 | 0.73 |
| quality | seq | on | 1 | 2 | 100 | 6.78 | 10.56 | 8334 | 0.80 | 0.78 |
| quality | single | on | 1 | 2 | 100 | 1.49 | 2.84 | 6670 | 0.00 | 0.73 |
| quality | l3 | on | 4 | 0 | 265 | 4.52 | 6.59 | 7761 | 0.86 | 0.79 |
| quality | l3a | on | 4 | 0 | 265 | 4.57 | 7.19 | 8294 | 0.82 | 0.76 |
| quality | par | on | 4 | 0 | 265 | 4.47 | 6.75 | 8325 | 0.80 | 0.75 |
| quality | seq | on | 4 | 0 | 265 | 9.11 | 12.66 | 8324 | 0.80 | 0.77 |
| quality | l3 | on | 16 | 0 | 265 | 9.20 | 14.42 | 7721 | 0.86 | 0.78 |
| quality | l3a | on | 16 | 0 | 265 | 9.89 | 13.86 | 8321 | 0.82 | 0.76 |
| quality | par | off | 16 | 0 | 265 | 24.48 | 34.71 | 42459 | 0.00 | 0.75 |
| quality | par | on | 16 | 0 | 265 | 10.15 | 14.04 | 8257 | 0.80 | 0.76 |
| quality | seq | off | 16 | 0 | 265 | 28.65 | 39.87 | 42309 | 0.00 | 0.78 |
| quality | seq | on | 16 | 0 | 265 | 15.23 | 21.44 | 8286 | 0.80 | 0.78 |
| quality | l3 | on | 32 | 0 | 265 | 15.80 | 25.32 | 7737 | 0.86 | 0.77 |
| quality | l3a | on | 32 | 0 | 265 | 16.69 | 25.04 | 8278 | 0.82 | 0.77 |
| quality | par | off | 32 | 0 | 265 | 46.46 | 65.50 | 42345 | 0.00 | 0.76 |
| quality | par | on | 32 | 0 | 265 | 17.47 | 24.13 | 8300 | 0.80 | 0.76 |
| quality | seq | off | 32 | 0 | 265 | 50.43 | 71.64 | 42384 | 0.00 | 0.74 |
| quality | seq | on | 32 | 0 | 265 | 23.12 | 33.82 | 8337 | 0.80 | 0.76 |
