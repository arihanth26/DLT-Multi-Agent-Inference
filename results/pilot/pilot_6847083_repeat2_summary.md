# Pilot summary: results/pilot/pilot_6847083_repeat2.jsonl

## All configurations
task      C  config                   n  medT s   p95T  xBASE   acc prefill/task cached% ans tok  T/cp
quality   4  BASE (seq, APC on)      20    8.52  10.05   1.00  0.65         7386    80.3     172  2.39
quality   4  L1+L2                   20    4.37   6.33   1.95  0.60         7444    80.2     175  1.00

## Preregistered quantities (pilot scale)

### quality, C=4
Rule 1/2  L1 speedup T_BASE/T_L1 = 1.95  (95% bootstrap LB 1.68); add-one gain 0.95
H2        critical-path bound on L1 speedup (median T_seq/cp) = 2.39
Rule 5    L1+L2                vs BASE: final answers agree 17/20; accuracy -5.0 pp (discordant: BASE-only 2, config-only 1)
H4        seq : round-1 prompt served from cache for agents 2-3: 100%
H4        par : round-1 prompt served from cache for agents 2-3: 94%
