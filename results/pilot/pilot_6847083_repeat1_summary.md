# Pilot summary: results/pilot/pilot_6847083_repeat1.jsonl

## All configurations
task      C  config                   n  medT s   p95T  xBASE   acc prefill/task cached% ans tok  T/cp
quality   4  BASE (seq, APC on)      20    8.70  10.70   1.00  0.80         7436    80.2     178  2.37
quality   4  L1+L2                   20    4.60   5.85   1.89  0.55         7417    80.3     171  1.00

## Preregistered quantities (pilot scale)

### quality, C=4
Rule 1/2  L1 speedup T_BASE/T_L1 = 1.89  (95% bootstrap LB 1.70); add-one gain 0.89
H2        critical-path bound on L1 speedup (median T_seq/cp) = 2.37
Rule 5    L1+L2                vs BASE: final answers agree 15/20; accuracy -25.0 pp (discordant: BASE-only 5, config-only 0)
H4        seq : round-1 prompt served from cache for agents 2-3: 100%
H4        par : round-1 prompt served from cache for agents 2-3: 87%
