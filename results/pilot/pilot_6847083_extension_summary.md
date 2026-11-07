# Pilot summary: results/pilot/pilot_6847083_extension_seed0.jsonl

## All configurations
task      C  config                   n  medT s   p95T  xBASE   acc prefill/task cached% ans tok  T/cp
quality   1  BASE (seq, APC on)      64    7.13   9.26   1.00  0.64         7318    80.2     171  2.47
quality   1  L1 only                 64    3.80   5.26   1.88  0.69        36851     0.0     168  1.00
quality   1  L1+L2                   64    3.02   4.25   2.36  0.70         7294    80.2     170  1.00
quality  16  BASE (seq, APC on)      64   13.76  19.40   1.00  0.70         7297    80.2     170  2.38
quality  16  L1 only                 64   22.14  30.21   0.62  0.75        36921     0.0     171  1.00
quality  16  L1+L2                   64    8.42  16.24   1.63  0.70         7265    80.3     166  1.00
quality  16  L1+L2+L3a warm          64    8.55  11.86   1.61  0.72         7320    82.9     169  1.00
quality  16  L1+L2+L3 full           64    9.24  12.71   1.49  0.73         6704    86.4     185  1.00
quality  32  BASE (seq, APC on)      64   20.38  28.18   1.00  0.73         7284    80.2     165  2.19
quality  32  L1 only                 64   38.66  58.74   0.53  0.70        36860     0.0     167  1.00
quality  32  L1+L2                   64   14.33  25.37   1.42  0.72         7316    80.2     169  1.00
quality  32  L1+L2+L3 full           64   13.78  21.06   1.48  0.75         6710    86.4     185  1.00

## Preregistered quantities (pilot scale)

### quality, C=1
Rule 1/2  L1 speedup T_BASE/T_L1 = 2.36  (95% bootstrap LB 2.19); add-one gain 1.36
Rule 3    L2 leave-one-out loss = 0.77s = 25.5% of T(both)
H2        critical-path bound on L1 speedup (median T_seq/cp) = 2.47
Rule 5    L1+L2                vs BASE: final answers agree 55/64; accuracy +6.2 pp (discordant: BASE-only 1, config-only 5)
Rule 5    L1 only              vs BASE: final answers agree 54/64; accuracy +4.7 pp (discordant: BASE-only 2, config-only 5)
H4        seq : round-1 prompt served from cache for agents 2-3: 100%
H4        par : round-1 prompt served from cache for agents 2-3: 98%

### quality, C=16
Rule 1/2  L1 speedup T_BASE/T_L1 = 1.63  (95% bootstrap LB 1.45); add-one gain 0.63
Rule 3    L2 leave-one-out loss = 13.72s = 163.0% of T(both)
Rule 4    l3a: prefill tokens computed +1% vs L1+L2, median T +2%  (preregistered: <= -30% and <= -10% at C=16)
Rule 4    l3: prefill tokens computed -8% vs L1+L2, median T +10%  (preregistered: <= -30% and <= -10% at C=16)
H2        critical-path bound on L1 speedup (median T_seq/cp) = 2.38
Rule 5    L1+L2                vs BASE: final answers agree 56/64; accuracy +0.0 pp (discordant: BASE-only 3, config-only 3)
Rule 5    L1 only              vs BASE: final answers agree 55/64; accuracy +4.7 pp (discordant: BASE-only 1, config-only 4)
Rule 5    L1+L2+L3a warm       vs BASE: final answers agree 59/64; accuracy +1.6 pp (discordant: BASE-only 2, config-only 3)
Rule 5    L1+L2+L3 full        vs BASE: final answers agree 56/64; accuracy +3.1 pp (discordant: BASE-only 1, config-only 3)
H4        seq : round-1 prompt served from cache for agents 2-3: 100%
H4        par : round-1 prompt served from cache for agents 2-3: 89%
H4        l3a : round-1 prompt served from cache for agents 2-3: 100%

### quality, C=32
Rule 1/2  L1 speedup T_BASE/T_L1 = 1.42  (95% bootstrap LB 1.28); add-one gain 0.42
Rule 3    L2 leave-one-out loss = 24.33s = 169.8% of T(both)
Rule 4    l3: prefill tokens computed -8% vs L1+L2, median T -4%  (preregistered: <= -30% and <= -10% at C=16)
H2        critical-path bound on L1 speedup (median T_seq/cp) = 2.19
Rule 5    L1+L2                vs BASE: final answers agree 56/64; accuracy -1.6 pp (discordant: BASE-only 4, config-only 3)
Rule 5    L1 only              vs BASE: final answers agree 57/64; accuracy -3.1 pp (discordant: BASE-only 4, config-only 2)
Rule 5    L1+L2+L3 full        vs BASE: final answers agree 58/64; accuracy +1.6 pp (discordant: BASE-only 2, config-only 3)
H4        seq : round-1 prompt served from cache for agents 2-3: 100%
H4        par : round-1 prompt served from cache for agents 2-3: 91%
