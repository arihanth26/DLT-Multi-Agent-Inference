# Pilot summary: results/pilot/pilot_6850879.jsonl

## All configurations
task      C  config                   n  medT s   p95T  xBASE   acc prefill/task cached% ans tok  T/cp
gsm8k     1  BASE (seq, APC on)       2    6.55   7.13   1.00  1.00         1502    43.7     140  2.01
gsm8k     1  neither lever            2    7.23   7.42   0.91  1.00         2708     0.0     157  2.20
gsm8k     1  L1 only                  2    2.77   2.90   2.37  1.00         2666     0.0     172  1.00
gsm8k     1  L1+L2                    2    2.50   2.76   2.63  1.00         1504    43.7     143  1.00
gsm8k     1  L1+L2+L3a warm           2    2.62   2.77   2.50  1.00         1502    46.2     160  1.00
gsm8k     1  L1+L2+L3 full            2    2.93   2.96   2.23  1.00          950    73.4     181  1.00
gsm8k     1  single agent             2    1.13   1.36   5.79  1.00          110    12.7     178  1.00
quality   1  BASE (seq, APC on)       2    7.90   9.27   1.00  0.50         6284    78.9     195  2.44
quality   1  neither lever            2    7.98   9.22   0.99  1.00        29548     0.0     184  2.65
quality   1  L1 only                  2    3.44   3.74   2.30  0.50        29397     0.0     166  1.00
quality   1  L1+L2                    2    3.35   3.88   2.36  1.00         6230    79.0     190  1.00
quality   1  L1+L2+L3a warm           2    3.52   4.20   2.25  1.00         6290    81.7     190  1.00
quality   1  L1+L2+L3 full            2    3.91   4.76   2.02  1.00         5574    85.9     201  1.00
quality   1  single agent             2    1.63   1.78   4.86  0.50         4546     0.2     232  1.00
quality   4  BASE (seq, APC on)       2    7.11   7.35   1.00  1.00         6025    79.5     165  2.44
quality   4  L1 only                  2    6.98   7.39   1.02  1.00        29403     0.0     184  1.00
quality   4  L1+L2                    2    5.39   5.61   1.32  1.00         6022    79.5     178  1.00
quality   4  L1+L2+L3 full            2    4.36   5.55   1.63  1.00         5598    85.9     215  1.00

## Preregistered quantities (pilot scale)

### gsm8k, C=1
Rule 1/2  L1 speedup T_BASE/T_L1 = 2.63  (95% bootstrap LB nan); add-one gain 1.63
Rule 3    L2 leave-one-out loss = 0.27s = 10.8% of T(both)
          (APC on vs off under sequential dispatch: 0.68s)
Rule 4    l3a: prefill tokens computed -0% vs L1+L2, median T +5%  (preregistered: <= -30% and <= -10% at C=16)
Rule 4    l3: prefill tokens computed -37% vs L1+L2, median T +17%  (preregistered: <= -30% and <= -10% at C=16)
H2        critical-path bound on L1 speedup (median T_seq/cp) = 2.01
Rule 5    L1+L2                vs BASE: final answers agree 2/2; accuracy +0.0 pp (discordant: BASE-only 0, config-only 0)
Rule 5    L1 only              vs BASE: final answers agree 2/2; accuracy +0.0 pp (discordant: BASE-only 0, config-only 0)
Rule 5    L1+L2+L3a warm       vs BASE: final answers agree 2/2; accuracy +0.0 pp (discordant: BASE-only 0, config-only 0)
Rule 5    L1+L2+L3 full        vs BASE: final answers agree 2/2; accuracy +0.0 pp (discordant: BASE-only 0, config-only 0)
Rule 5    neither lever        vs BASE: final answers agree 2/2; accuracy +0.0 pp (discordant: BASE-only 0, config-only 0)
H4        seq : round-1 prompt served from cache for agents 2-3: 95%
H4        par : round-1 prompt served from cache for agents 2-3: 95%
H4        l3a : round-1 prompt served from cache for agents 2-3: 95%

### quality, C=1
Rule 1/2  L1 speedup T_BASE/T_L1 = 2.36  (95% bootstrap LB nan); add-one gain 1.36
Rule 3    L2 leave-one-out loss = 0.09s = 2.7% of T(both)
          (APC on vs off under sequential dispatch: 0.08s)
Rule 4    l3a: prefill tokens computed +1% vs L1+L2, median T +5%  (preregistered: <= -30% and <= -10% at C=16)
Rule 4    l3: prefill tokens computed -11% vs L1+L2, median T +17%  (preregistered: <= -30% and <= -10% at C=16)
H2        critical-path bound on L1 speedup (median T_seq/cp) = 2.44
Rule 5    L1+L2                vs BASE: final answers agree 1/2; accuracy +50.0 pp (discordant: BASE-only 0, config-only 1)
Rule 5    L1 only              vs BASE: final answers agree 2/2; accuracy +0.0 pp (discordant: BASE-only 0, config-only 0)
Rule 5    L1+L2+L3a warm       vs BASE: final answers agree 1/2; accuracy +50.0 pp (discordant: BASE-only 0, config-only 1)
Rule 5    L1+L2+L3 full        vs BASE: final answers agree 1/2; accuracy +50.0 pp (discordant: BASE-only 0, config-only 1)
Rule 5    neither lever        vs BASE: final answers agree 1/2; accuracy +50.0 pp (discordant: BASE-only 0, config-only 1)
H4        seq : round-1 prompt served from cache for agents 2-3: 100%
H4        par : round-1 prompt served from cache for agents 2-3: 100%
H4        l3a : round-1 prompt served from cache for agents 2-3: 100%

### quality, C=4
Rule 1/2  L1 speedup T_BASE/T_L1 = 1.32  (95% bootstrap LB nan); add-one gain 0.32
Rule 3    L2 leave-one-out loss = 1.59s = 29.4% of T(both)
Rule 4    l3: prefill tokens computed -7% vs L1+L2, median T -19%  (preregistered: <= -30% and <= -10% at C=16)
H2        critical-path bound on L1 speedup (median T_seq/cp) = 2.44
Rule 5    L1+L2                vs BASE: final answers agree 2/2; accuracy +0.0 pp (discordant: BASE-only 0, config-only 0)
Rule 5    L1 only              vs BASE: final answers agree 2/2; accuracy +0.0 pp (discordant: BASE-only 0, config-only 0)
Rule 5    L1+L2+L3 full        vs BASE: final answers agree 2/2; accuracy +0.0 pp (discordant: BASE-only 0, config-only 0)
H4        seq : round-1 prompt served from cache for agents 2-3: 100%
H4        par : round-1 prompt served from cache for agents 2-3: 100%
