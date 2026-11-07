"""Validate and report the separate recorded 20-story C=1 three-seed check."""
from pathlib import Path
from collections import defaultdict
import sys,json,math,hashlib,statistics as st
sys.path.insert(0,str(Path.cwd()))
from pilot.debate import call_seed,parse_answer,majority,round2_released
p=Path(sys.argv[1]);g=defaultdict(list);seen=set();count=0
original=Path('results/pilot/pilot_6847083_initial.jsonl')
ids={r['id'] for r in map(json.loads,original.open()) if r['task']=='quality'}
for line in p.open():
 r=json.loads(line);count+=1;k=(r['seed'],r['mode']);unique=k+(r['id'],)
 assert unique not in seen;seen.add(unique)
 assert r['task']=='quality' and r['conc']==1 and r['apc']=='on' and r['mode'] in ['seq','par'] and len(r['calls'])==6
 assert r['problem_seed']==0 and r['model']=='llama-3.1-8b'
 R1={c['agent']:c for c in r['calls'] if c['rnd']==0}
 assert len(R1)==3 and len({c['messages_sha256'] for c in R1.values()})==1
 preds={}
 for c in r['calls']:
  assert c['kind']=='debate' and 0<=c['cached']<=c['prompt'] and c['prompt']>0 and c['out']>0
  assert 0<=c['submit']<=c['done']<=r['T']
  assert c['sampling']=={'temperature':.7,'top_p':.9,'max_tokens':512}
  assert c['request_seed']==call_seed(r['seed'],r['id'],c['agent'],c['rnd'])
  assert c['messages_sha256']==hashlib.sha256(json.dumps(c['messages'],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
  if c['rnd']==1:
   i=c['agent'];expected=[R1[i]['messages'][0],{'role':'assistant','content':R1[i]['response']},{'role':'user','content':round2_released('quality',[R1[j]['response'] for j in range(3) if j!=i])}]
   assert c['messages']==expected
   preds[i]=parse_answer('quality',c['response'])
 assert [preds[i] for i in range(3)]==r['preds'] and majority(r['preds'])==r['final']
 assert (r['final']==r['gold'])==r['correct']
 g[k].append(r)
complete={k:rs for k,rs in g.items() if len(rs)==20}
for k,rs in complete.items():assert {r['id'] for r in rs}==ids
out=['# QuALITY C=1 three-seed pilot — 2026-11-06','','Separate uniform runs on the same 20 distinct stories as the original pilot, with problem seed 0 and sampling seeds 0,1,2. Three agents, two rounds, one H100 80 GB, four CPUs, pinned vLLM 0.31.0, Llama-3.1-8B-Instruct bf16, temperature 0.7, top-p 0.9, maximum 512 output tokens. Both modes use APC on and reset the prefix cache before each configuration. Requests and responses were recorded. This is a fresh exploratory run; it does not replace earlier measurements or satisfy the registered 100-problem headline sample size.','',f'Validated {count} records. Complete groups: {sorted(complete)}. Incomplete groups: {[(k,len(v)) for k,v in g.items() if len(v)!=20] or "none"}. Request hashes/seeds/settings, history reconstruction, response parsing, votes, token counts and timings were checked. Only complete pairs enter the table.','','| Sampling seed | BASE median (s) | Parallel median (s) | BASE/parallel latency ratio | BASE correct | Parallel correct | Accuracy delta | BASE-only / parallel-only correct | Exact McNemar p |','|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
ms=[];acs=[];warnings=[]
for seed in [0,1,2]:
 if (seed,'seq') not in complete or (seed,'par') not in complete:continue
 A={r['id']:r for r in complete[seed,'seq']};B={r['id']:r for r in complete[seed,'par']}
 ma=st.median(r['T'] for r in A.values());mb=st.median(r['T'] for r in B.values())
 a=sum(r['correct'] for r in A.values());b=sum(r['correct'] for r in B.values())
 l=sum(A[i]['correct'] and not B[i]['correct'] for i in A);gain=sum(B[i]['correct'] and not A[i]['correct'] for i in A);n=l+gain
 pv=min(1.,2*sum(math.comb(n,i) for i in range(min(l,gain)+1))/2**n) if n else 1.
 out.append(f'| {seed} | {ma:.2f} | {mb:.2f} | {ma/mb:.2f}× | {a}/20 | {b}/20 | {5*(b-a):+.1f} pp | {l}/{gain} | {pv:.4f} |')
 ms.append((ma,mb));acs.append((a,b))
 if 5*(b-a)<-2 or (l>gain and pv<.05):warnings.append(f'**Pilot quality warning for seed {seed}:** parallel is {5*(b-a):+.1f} pp below BASE. Do not present it as a quality-preserving speedup.')
for warning in warnings:out+=['',warning]
if len(ms)==3:
 ma=st.mean(x[0] for x in ms);mb=st.mean(x[1] for x in ms)
 aa=5*st.mean(x[0] for x in acs);ab=5*st.mean(x[1] for x in acs)
 out+=['',f'Descriptive mean of the three per-seed medians: BASE **{ma:.2f} s**, parallel **{mb:.2f} s**, ratio **{ma/mb:.2f}×**. Mean accuracy over seeds: BASE **{aa:.2f}%**, parallel **{ab:.2f}%**, difference **{ab-aa:+.2f} pp**.']
out+=['','These are 20 unique problems repeated under three seeds, not 60 independent problems. Exact two-sided McNemar p-values are per seed, exploratory, and unadjusted; non-significance does not prove non-inferiority or cancel a numerical accuracy-loss warning. No pooled significance test is claimed. The small sample, approximate released-workflow prompts, same-seed variability and first-use compilation caveats remain. The separate 64-story load extension should be interpreted independently.','']
report=p.with_name(p.stem+'_report.md');report.write_text('\n'.join(out));print('Wrote',report,'records',count)
