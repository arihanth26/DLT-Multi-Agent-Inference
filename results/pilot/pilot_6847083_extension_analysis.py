"""Validate the load extension. From the repository root, pass its JSONL path as argv[1]."""
from pathlib import Path
from collections import defaultdict, Counter
import json, hashlib, math, statistics as st, random, re, sys
sys.path.insert(0, str(Path.cwd()))
from pilot.debate import call_seed, parse_answer, majority, round2_released, round2_shared_prefix, round2_agent_line
p=Path(sys.argv[1]); groups=defaultdict(list); seen=set(); total=0
for line in p.open():
 r=json.loads(line); total+=1
 key=(r['conc'],r['mode'],r['apc'],r['seed'])
 unique=key+(r['id'],); assert unique not in seen,unique;seen.add(unique)
 assert r['task']=='quality' and r['model']=='llama-3.1-8b' and r['problem_seed']==0
 assert len(r['calls'])=={'seq':6,'par':6,'l3a':7,'l3':8}[r['mode']]
 predictions={}; r1_text=None
 for c in r['calls']:
  assert 0<=c['cached']<=c['prompt'] and c['prompt']>0 and c['out']>0
  assert 0<=c['submit']<=c['done']<=r['T']
  assert r['apc']=='on' or c['cached']==0
  assert c['request_seed']==call_seed(r['seed'],r['id'],c['agent'],c['rnd'])
  assert c['sampling']=={'temperature':.7,'top_p':.9,'max_tokens':1 if c['kind']=='warm' else 512}
  assert hashlib.sha256(json.dumps(c['messages'],sort_keys=True,ensure_ascii=False).encode()).hexdigest()==c['messages_sha256']
  assert isinstance(c['response'],str)
  if c['kind']=='debate' and c['rnd']==0:
   assert len(c['messages'])==1 and c['messages'][0]['role']=='user'
   if r1_text is None:r1_text=c['messages'][0]['content']
   assert c['messages'][0]['content']==r1_text

  if c['kind']=='debate' and c['rnd']==1:predictions[c['agent']]=parse_answer('quality',c['response'])
  del c['messages']
 r1={c['agent']:c['response'] for c in r['calls'] if c['kind']=='debate' and c['rnd']==0}
 for c in r['calls']:
  if c['rnd']!=1:continue
  if r['mode']=='l3':
   shared=round2_shared_prefix('quality',r1_text,[r1[i] for i in range(3)])
   content=shared if c['kind']=='warm' else shared+round2_agent_line('quality',c['agent'])
   expected=[{'role':'user','content':content}]
  else:
   agent=c['agent']
   expected=[{'role':'user','content':r1_text},{'role':'assistant','content':r1[agent]},
    {'role':'user','content':round2_released('quality',[r1[j] for j in range(3) if j!=agent])}]
  assert hashlib.sha256(json.dumps(expected,sort_keys=True,ensure_ascii=False).encode()).hexdigest()==c['messages_sha256']
 assert [predictions[i] for i in range(3)]==r['preds']
 assert majority(r['preds'])==r['final'] and (r['final']==r['gold'])==r['correct']
 groups[key].append(r)
complete={k:v for k,v in groups.items() if len(v)==64}
assert complete,'No complete groups'
baseids={r['id'] for r in complete[(1,'seq','on',0)]}
for k,rs in complete.items():assert {r['id'] for r in rs}==baseids,k
required={(c,m,a,0) for c,configs in [(1,[('seq','on'),('par','on'),('par','off')]),(16,[('seq','on'),('par','on'),('l3a','on'),('l3','on'),('par','off')]),(32,[('seq','on'),('par','on'),('l3','on'),('par','off')])] for m,a in configs}
missing=required-set(complete)
med=lambda rs:st.median(r['T'] for r in rs)
acc=lambda rs:100*st.mean(r['correct'] for r in rs)
prefill=lambda rs:sum(c['prompt']-c['cached'] for r in rs for c in r['calls'])/len(rs)
def paired(a,b):
 """Return discordant correctness counts, exact McNemar p, and answer agreement."""
 A={r['id']:r for r in a}; B={r['id']:r for r in b}
 assert set(A)==set(B)
 losses=sum(A[i]['correct'] and not B[i]['correct'] for i in A)
 gains=sum(B[i]['correct'] and not A[i]['correct'] for i in A)
 n=losses+gains;pval=min(1.,2*sum(math.comb(n,i) for i in range(min(losses,gains)+1))/2**n) if n else 1.
 return losses,gains,pval,sum(A[i]['final']==B[i]['final'] for i in A)
def bootstrap(a,b):
 """Resample matched problem IDs to describe a latency-ratio interval."""
 A={r['id']:r['T'] for r in a};B={r['id']:r['T'] for r in b};ids=sorted(A)
 rng=random.Random(0);v=[]
 for _ in range(4000):
  s=rng.choices(ids,k=len(ids));v.append(st.median(A[i] for i in s)/st.median(B[i] for i in s))
 v.sort();return v[99],v[3899]
labels={('seq','on'):'BASE',('par','on'):'L1+L2',('l3a','on'):'L1+L2+L3a',('l3','on'):'L1+L2+L3',('par','off'):'Parallel, APC off'}
lines=[]
def emit(s=''):
 """Append one line to the report."""
 lines.append(s)
emit('# QuALITY load extension — 2026-11-06');emit()
emit('Exploratory follow-up on 64 distinct validation stories with the same problem selection for all complete groups. One H100 80 GB, four allocated CPUs, Llama-3.1-8B-Instruct bf16, vLLM 0.31.0; temperature 0.7, top-p 0.9, maximum 512 output tokens; three agents and two rounds. Full messages, request seeds, sampling settings and responses were recorded. Each configuration starts with a reset prefix cache; APC on/off use separate server processes. The original 30/20-problem grid is preserved separately.')
emit();emit(f'Validated **{total} records**; **{len(complete)} complete 64-problem groups**. Partial groups: {[(k,len(v)) for k,v in groups.items() if len(v)!=64] or "none"}. Missing priority groups: {sorted(missing) or "none"}. Counts, problem IDs, request hashes/seeds/settings, round-2 message construction from recorded round-1 outputs, call counts, token counts, APC-off cache counts, response parsing and final votes were checked. Only complete groups enter comparisons below.')
emit();emit('This is not the preregistered evaluation: 64 problems rather than 100/300, an approximate released-workflow implementation, short closed-loop windows, and exploratory follow-up selected after the initial pilot. C=32 has only two waves of 32 problems, so startup/drain effects can be substantial. Task bootstraps do not capture within-run queue dependence and are descriptive at load. Recording adds client work; do not pool these timings with the uninstrumented original pilot. Raw Prometheus snapshots and server logs are retained, including first-use JIT warnings. Per-call finish reasons and rendered token IDs are not recorded; token-cap hits below are a proxy, not definitive truncation labels.')
emit();emit('## Main observations');emit()
if all((c,m,'on',0) in complete for c in [1,16,32] for m in ['seq','par']):
 ratios={c:med(complete[(c,'seq','on',0)])/med(complete[(c,'par','on',0)]) for c in [1,16,32]}
 emit(f'- The raw BASE/parallel latency ratio falls from **{ratios[1]:.2f}× at C=1** to **{ratios[16]:.2f}× at C=16** and **{ratios[32]:.2f}× at C=32**. The C=32 add-one gain is {100*(ratios[32]-1)/(ratios[1]-1):.0f}% of its C=1 value. This is descriptive pilot evidence for contention, not preregistered acceptance.')
if all((c,'par',a,0) in complete for c in [1,16,32] for a in ['on','off']):
 losses={c:med(complete[(c,'par','off',0)])-med(complete[(c,'par','on',0)]) for c in [1,16,32]}
 emit(f'- Disabling caching adds **{losses[1]:.2f} s at C=1**, **{losses[16]:.2f} s at C=16**, and **{losses[32]:.2f} s at C=32** to median parallel latency. Caching is a major contributor under load on these long prompts.')
if (16,'l3','on',0) in complete and (16,'par','on',0) in complete:
 a=complete[(16,'l3','on',0)];b=complete[(16,'par','on',0)]
 emit(f'- At the registered target load C=16, full L3 changes prefill estimates by **{100*(prefill(a)/prefill(b)-1):+.1f}%** and median latency by **{100*(med(a)/med(b)-1):+.1f}%** relative to L1+L2. The current pilot implementation does not meet the proposed 30% prefill / 10% latency reduction targets in this sample.')
emit('- Accuracy and request/response differences remain separate from timing gains. Preserve the earlier C=4 quality warnings; this new grid does not replace them. A missing numerical flag in a new group is not proof of non-inferiority.')
for seed in sorted({k[3] for k in complete}):
 emit();emit(f'## Sampling seed {seed}');emit()
 emit('| C | Configuration | n | Median T (s) | p95 (s) | BASE/config latency ratio | Accuracy | Computed prefill/task | Mean answer tokens |')
 emit('|---:|---|---:|---:|---:|---:|---:|---:|---:|')
 for k,rs in sorted(complete.items(),key=lambda kv:(kv[0][0],list(labels).index(kv[0][1:3]))):
  c,m,a,s=k
  if s!=seed:continue
  base=complete.get((c,'seq','on',seed));ratio=f'{med(base)/med(rs):.2f}×' if base else '—'
  ts=sorted(r['T'] for r in rs)
  emit(f'| {c} | {labels[m,a]} | {len(rs)} | {med(rs):.2f} | {ts[math.ceil(.95*len(ts))-1]:.2f} | {ratio} | {acc(rs):.2f}% | {prefill(rs):.0f} | {st.mean(t for r in rs for t in r["answer_tokens"]):.1f} |')
 for c in sorted({k[0] for k in complete if k[3]==seed}):
  G=lambda m,a='on':complete.get((c,m,a,seed))
  emit();emit(f'### C={c} paired comparisons');emit()
  if G('seq') and G('par'):
   lo,hi=bootstrap(G('seq'),G('par'));emit(f'Raw BASE-to-parallel latency ratio: **{med(G("seq"))/med(G("par")):.2f}×**, paired bootstrap 95% interval **[{lo:.2f}, {hi:.2f}]** (4,000 resamples).')
  if G('par') and G('par','off'):
   delta=med(G('par','off'))-med(G('par'));emit(f'Caching leave-one-out loss: **{delta:.2f} s**, **{100*delta/med(G("par")):.1f}%** of parallel+APC time.')
  for mode in ['l3a','l3']:
   if G(mode) and G('par'):
    emit(f'{labels[mode,"on"]} vs L1+L2: computed prefill **{100*(prefill(G(mode))/prefill(G("par"))-1):+.1f}%**, median latency **{100*(med(G(mode))/med(G("par"))-1):+.1f}%**.')
  if G('seq'):
   emit();emit('| Configuration vs BASE | Accuracy delta (pp) | BASE-only / config-only correct | Answer agreement | Exact McNemar p | Quality warning |')
   emit('|---|---:|---:|---:|---:|---|')
   for mode,apc in [('par','on'),('l3a','on'),('l3','on'),('par','off')]:
    if not G(mode,apc):continue
    l,g,pval,same=paired(G('seq'),G(mode,apc));d=acc(G(mode,apc))-acc(G('seq'));warn=d<-2 or (l>g and pval<.05)
    emit(f'| {labels[mode,apc]} | {d:+.2f} | {l}/{g} | {same}/64 | {pval:.4f} | {"YES — do not claim quality preservation" if warn else "No numerical flag in this sample; not proof of non-inferiority"} |')
  for mode in ['seq','par','l3a','l3']:
   if not G(mode):continue
   calls=[x for r in G(mode) for x in r['calls'] if x['kind']=='debate' and x['rnd']==0 and x['agent']>0]
   final=[x for r in G(mode) for x in r['calls'] if x['kind']=='debate' and x['rnd']==1]
   unboxed=sum(not re.search(r"\\boxed\{[^}]*\}",x["response"]) for x in final)
   emit(f'{mode}: round-1 agents 2–3 cached share **{100*sum(x["cached"] for x in calls)/sum(x["prompt"] for x in calls):.1f}%**; final-agent calls at the 512-token cap **{sum(x["out"]==512 for x in final)}/{len(final)}**; final responses without boxed answers **{unboxed}/{len(final)}**.')
 emit();emit('Exact McNemar p-values are two-sided, exploratory and unadjusted for multiple comparisons. Non-significance does not override the numerical >2 pp accuracy-loss guardrail. The same problems across seeds remain repeated measurements, not independent new problems.')
emit();emit('## First-round request/response audit');emit()
emit('Compare recorded message hashes, sampling settings and request seeds for the same problem/agent, excluding warm-up requests. Exact response matching is stricter than final-answer matching. Matching here concerns API messages/parameters; tokenized prompt identity was not directly logged.')
emit();emit('| Seed | C | Comparison | Identical recorded request tuples | Exact response matches | Parsed round-1 answer matches |');emit('|---:|---:|---|---:|---:|---:|')
for seed in sorted({k[3] for k in complete}):
 for c in [1,16,32]:
  for ma,mb in [('seq','par'),('par','l3a'),('par','l3')]:
   a=complete.get((c,ma,'on',seed));b=complete.get((c,mb,'on',seed))
   if not a or not b:continue
   A={(r['id'],x['agent']):x for r in a for x in r['calls'] if x['kind']=='debate' and x['rnd']==0}
   B={(r['id'],x['agent']):x for r in b for x in r['calls'] if x['kind']=='debate' and x['rnd']==0}
   assert set(A)==set(B)
   same=sum((A[i]['messages_sha256'],A[i]['request_seed'],A[i]['sampling'])==(B[i]['messages_sha256'],B[i]['request_seed'],B[i]['sampling']) for i in A)
   text=sum(A[i]['response']==B[i]['response'] for i in A)
   answer=sum(parse_answer('quality',A[i]['response'])==parse_answer('quality',B[i]['response']) for i in A)
   emit(f'| {seed} | {c} | {ma} vs {mb} | {same}/{len(A)} | {text}/{len(A)} | {answer}/{len(A)} |')
emit();emit('If identical recorded first-round request tuples yield different response text, divergence is already observable before any round-2 transcript rewrite. This does not identify the server-side cause; fixed seeds alone are insufficient evidence of identical answers. Later rounds can then legitimately have different inputs because their upstream answers differ. Every saved round-2 request was also checked against the expected construction of this harness using its own recorded upstream answers; this checks execution/history handling, not equivalence with the released Du et al. implementation. Full L3 intentionally changes round-2 messages and still requires its separate accuracy check.')
emit();emit('## Aggregate round-1 prefill check');emit()
emit('Normalize the sum of uncached round-1 tokens across all three agents (plus any round-1 warm-up) by one agent prompt length. This avoids assuming agent 1 is always the first prefiller under asynchronous dispatch. It is an API-token estimate, not a kernel execution trace.')
emit();emit('| Seed | C | Configuration | Mean uncached round-1 prompt copies, warm-up included | Call reporting largest round-1 prefill |');emit('|---:|---:|---|---:|---|')
for k,rs in sorted(complete.items(),key=lambda kv:(kv[0][3],kv[0][0],list(labels).index(kv[0][1:3]))):
 c,m,a,seed=k
 if a!='on':continue
 ratios=[];owners=Counter()
 for r in rs:
  calls=[x for x in r['calls'] if x['rnd']==0]
  debate=[x for x in calls if x['kind']=='debate']
  assert len({x['prompt'] for x in debate})==1
  ratios.append(sum(x['prompt']-x['cached'] for x in calls)/debate[0]['prompt'])
  largest=max(calls,key=lambda x:x['prompt']-x['cached'])
  owner='warm-up' if largest['kind']=='warm' else f'agent {largest["agent"]+1}'
  owners[owner]+=1
 assignment=', '.join(f'{who}: {n}' for who,n in sorted(owners.items()))
 emit(f'| {seed} | {c} | {labels[m,a]} | {st.mean(ratios):.3f} | {assignment} |')
emit();emit('The observed parallel round-1 estimate is already about one prompt copy, not three. Warming the prefix raises the agents-2/3 cached share but does not reduce aggregate round-1 prefill below that one-copy requirement. Under parallel dispatch the first/largest prefill is not always attributed to agent 1, so agents-2/3 cache share alone cannot establish duplicate prefill. This weakens the round-1 premise for L3 on this stack; it does not establish the internal mechanism or behavior of other vLLM versions.')
emit();emit('## Server-side diagnostic counters');emit()
emit('Before/after Prometheus deltas cover the measured configuration plus its three short setup warm-up requests. Means are per server request, not a wall-clock decomposition of debate time. Local-compute tokens are the server-reported source counter; API prefill estimates above are prompt minus cached tokens and may omit internal recomputation when preemption occurs.')
emit();emit('| Seed | C | Configuration | Completed server requests | Mean queue (ms) | Mean prefill (ms) | Mean decode (s) | Preemptions | Server local-compute tokens/debate, setup included |');emit('|---:|---:|---|---:|---:|---:|---:|---:|---:|')
def metric(file,name,source=None):
 """Read a Prometheus counter, optionally filtered by token source."""
 value=0.
 for line in file.read_text().splitlines():
  if line.startswith(name+'{') or line.startswith(name+' '):
   if source is None or f'source="{source}"' in line:
    value+=float(line.rsplit(None,1)[1])
 return value
for k,rs in sorted(complete.items(),key=lambda kv:(kv[0][3],kv[0][0],list(labels).index(kv[0][1:3]))):
 c,m,a,seed=k;key=f'{m}_{a}_C{c}_seed{seed}'
 before=p.with_name(p.stem+'_'+key+'_before.prom');after=p.with_name(p.stem+'_'+key+'_after.prom')
 if not before.exists() or not after.exists():continue
 diff=lambda name,source=None:metric(after,name,source)-metric(before,name,source)
 count=diff('vllm:request_queue_time_seconds_count')
 if count<=0:continue
 queue=1000*diff('vllm:request_queue_time_seconds_sum')/count
 pre=1000*diff('vllm:request_prefill_time_seconds_sum')/count
 decode=diff('vllm:request_decode_time_seconds_sum')/count
 preempt=diff('vllm:num_preemptions_total')
 computed=diff('vllm:prompt_tokens_by_source_total','local_compute')/len(rs)
 emit(f'| {seed} | {c} | {labels[m,a]} | {count:.0f} | {queue:.2f} | {pre:.2f} | {decode:.3f} | {preempt:.0f} | {computed:.0f} |')
 expected=sum(len(r['calls']) for r in rs)+3
 if abs(count-expected)>.01:emit(f'Counter caveat for {key}: expected {expected} completed requests including warm-ups, observed {count:.0f}.')
emit();emit('## Scope');emit()
emit('No thresholds were changed. BASE remains sequential with prefix caching on; APC off is an ablation. L3a warms round 1 only in this harness; full L3 warms both rounds and changes round-2 inputs. Prefill estimates include warm-up requests and use prompt minus cached tokens. The released workflow, full sample sizes, formal multi-seed aggregation, and a 300-story sampling policy still need completion before preregistered claims. Metrics snapshots include the three short pre-measurement warm-up requests; do not interpret their aggregate counters as exact per-debate timing decomposition.')
out=p.with_name(p.stem+'_report.md');out.write_text('\n'.join(lines)+'\n')
print(f'Wrote {out}: {total} records, {len(complete)} complete groups, missing {sorted(missing)}')
