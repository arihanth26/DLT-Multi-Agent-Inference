# Pilot summary: results/pilot/pilot_6847083_initial.jsonl

## All configurations
task      C  config                   n  medT s   p95T  xBASE   acc prefill/task cached% ans tok  T/cp
gsm8k     1  BASE (seq, APC on)      30    5.40  11.61   1.00  0.90         1619    43.8     165  2.38
gsm8k     1  neither lever           30    6.15   9.46   0.88  0.97         2845     0.0     170  2.47
gsm8k     1  L1 only                 30    2.48   4.60   2.18  0.93         2863     0.0     172  1.00
gsm8k     1  L1+L2                   30    2.47   5.83   2.19  0.93         1638    43.7     173  1.00
gsm8k     1  L1+L2+L3a warm          30    2.45   5.85   2.21  0.90         1641    45.9     171  1.00
gsm8k     1  L1+L2+L3 full           30    3.10   5.79   1.74  0.90         1016    73.8     201  1.00
gsm8k     1  single agent            30    1.07   2.51   5.02  0.90           98    24.0     208  1.00
quality   1  BASE (seq, APC on)      20    7.03   8.97   1.00  0.65         7441    80.2     172  2.41
quality   1  neither lever           20    7.73   9.58   0.91  0.70        37620     0.0     176  2.55
quality   1  L1 only                 20    3.76   5.36   1.87  0.60        37518     0.0     168  1.00
quality   1  L1+L2                   20    2.92   3.75   2.41  0.70         7392    80.3     170  1.00
quality   1  L1+L2+L3a warm          20    3.10   3.87   2.27  0.65         7429    82.9     174  1.00
quality   1  L1+L2+L3 full           20    3.30   4.39   2.13  0.75         6819    86.4     188  1.00
quality   1  single agent            20    1.39   1.98   5.05  0.60         5902     0.3     207  1.00
quality   4  BASE (seq, APC on)      20    8.95   9.85   1.00  0.80         7454    80.2     172  2.40
quality   4  L1 only                 20    7.76  11.14   1.15  0.75        37551     0.0     174  1.00
quality   4  L1+L2                   20    4.58   8.43   1.95  0.70         7445    80.2     177  1.00
quality   4  L1+L2+L3 full           20    4.79   6.11   1.87  0.70         6822    86.4     192  1.00

## Preregistered quantities (pilot scale)

### gsm8k, C=1
Rule 1/2  L1 speedup T_BASE/T_L1 = 2.19  (95% bootstrap LB 1.95); add-one gain 1.19
Rule 3    L2 leave-one-out loss = 0.01s = 0.4% of T(both)
          (APC on vs off under sequential dispatch: 0.75s)
Rule 4    l3a: prefill tokens computed +0% vs L1+L2, median T -1%  (preregistered: <= -30% and <= -10% at C=16)
Rule 4    l3: prefill tokens computed -38% vs L1+L2, median T +26%  (preregistered: <= -30% and <= -10% at C=16)
H2        critical-path bound on L1 speedup (median T_seq/cp) = 2.38
Rule 5    L1+L2                vs BASE: final answers agree 29/30; accuracy +3.3 pp (discordant: BASE-only 0, config-only 1)
Rule 5    L1 only              vs BASE: final answers agree 28/30; accuracy +3.3 pp (discordant: BASE-only 0, config-only 1)
Rule 5    L1+L2+L3a warm       vs BASE: final answers agree 27/30; accuracy +0.0 pp (discordant: BASE-only 1, config-only 1)
Rule 5    L1+L2+L3 full        vs BASE: final answers agree 28/30; accuracy +0.0 pp (discordant: BASE-only 0, config-only 0)
Rule 5    neither lever        vs BASE: final answers agree 28/30; accuracy +6.7 pp (discordant: BASE-only 0, config-only 2)
H4        seq : round-1 prompt served from cache for agents 2-3: 94%
H4        par : round-1 prompt served from cache for agents 2-3: 94%
H4        l3a : round-1 prompt served from cache for agents 2-3: 94%

### quality, C=1
Rule 1/2  L1 speedup T_BASE/T_L1 = 2.41  (95% bootstrap LB 2.08); add-one gain 1.41
Rule 3    L2 leave-one-out loss = 0.84s = 28.9% of T(both)
          (APC on vs off under sequential dispatch: 0.70s)
Rule 4    l3a: prefill tokens computed +1% vs L1+L2, median T +6%  (preregistered: <= -30% and <= -10% at C=16)
Rule 4    l3: prefill tokens computed -8% vs L1+L2, median T +13%  (preregistered: <= -30% and <= -10% at C=16)
H2        critical-path bound on L1 speedup (median T_seq/cp) = 2.41
Rule 5    L1+L2                vs BASE: final answers agree 18/20; accuracy +5.0 pp (discordant: BASE-only 0, config-only 1)
Rule 5    L1 only              vs BASE: final answers agree 18/20; accuracy -5.0 pp (discordant: BASE-only 1, config-only 0)
Rule 5    L1+L2+L3a warm       vs BASE: final answers agree 17/20; accuracy +0.0 pp (discordant: BASE-only 1, config-only 1)
Rule 5    L1+L2+L3 full        vs BASE: final answers agree 15/20; accuracy +10.0 pp (discordant: BASE-only 0, config-only 2)
Rule 5    neither lever        vs BASE: final answers agree 18/20; accuracy +5.0 pp (discordant: BASE-only 0, config-only 1)
H4        seq : round-1 prompt served from cache for agents 2-3: 100%
H4        par : round-1 prompt served from cache for agents 2-3: 94%
H4        l3a : round-1 prompt served from cache for agents 2-3: 100%

### quality, C=4
Rule 1/2  L1 speedup T_BASE/T_L1 = 1.95  (95% bootstrap LB 1.62); add-one gain 0.95
Rule 3    L2 leave-one-out loss = 3.18s = 69.3% of T(both)
Rule 4    l3: prefill tokens computed -8% vs L1+L2, median T +4%  (preregistered: <= -30% and <= -10% at C=16)
H2        critical-path bound on L1 speedup (median T_seq/cp) = 2.40
Rule 5    L1+L2                vs BASE: final answers agree 15/20; accuracy -10.0 pp (discordant: BASE-only 3, config-only 1)
Rule 5    L1 only              vs BASE: final answers agree 18/20; accuracy -5.0 pp (discordant: BASE-only 1, config-only 0)
Rule 5    L1+L2+L3 full        vs BASE: final answers agree 18/20; accuracy -10.0 pp (discordant: BASE-only 2, config-only 0)
H4        seq : round-1 prompt served from cache for agents 2-3: 100%
H4        par : round-1 prompt served from cache for agents 2-3: 90%
