const $=id=>document.getElementById(id);let report=null;let benchmark=null;
function safe(t){const d=document.createElement('div');d.textContent=String(t??'');return d.innerHTML;}
function tab(name){document.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x.id===name));document.querySelectorAll('.nav').forEach(x=>x.classList.toggle('active',x.dataset.tab===name));window.scrollTo({top:0,behavior:'smooth'});}
document.querySelectorAll('.nav').forEach(x=>x.onclick=()=>tab(x.dataset.tab));
const status=(text)=>{$('status').textContent=text};
const pretty=x=>String(x||'—').replaceAll('_',' ');
function color(el,value){el.className=['VALID','CONSISTENT','AUTHORIZED','EXECUTABLE','EXECUTED'].includes(value)?'good':/BLOCKED|INVALID|DENIED|REJECTED|ANOMALY/.test(value)?'bad':'warn';}
function drawChart(rates,baseline){
  const canvas=$('chart'),w=canvas.clientWidth,h=canvas.clientHeight,dpr=window.devicePixelRatio||1;
  canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
  const c=canvas.getContext('2d');c.scale(dpr,dpr);
  rates.forEach((q,i)=>{const center=(i+.5)*w/4,scale=(h-30)/.10;
    c.fillStyle='#617d88';c.fillRect(center-31,h-Math.min(h-10,baseline*scale),18,Math.min(h-10,baseline*scale));
    c.fillStyle='#46d5c8';c.fillRect(center-8,h-Math.min(h-10,q*scale),26,Math.max(2,Math.min(h-10,q*scale)));
    c.fillStyle='#e9f9f7';c.font='600 13px Arial';c.textAlign='center';c.fillText((100*q).toFixed(1)+'%',center,h-Math.min(h-10,q*scale)-9);
  });
}
function render(r){report=r;$('results').hidden=false;const d=r.decisions;
  for(const [field,val] of [['signature',d.signature],['channel',d.channel],['authorization',d.authorization],['operation',d.operation]]){const el=$(field);el.textContent=pretty(val);color(el,val)}
  $('signatureWhy').textContent=r.charlie.reason||'Verification was gated before private records were accessed.';
  $('channelWhy').textContent=r.channel_analysis.reason;$('authorizationWhy').textContent=r.authorization_reason;
  $('bob').textContent=pretty(r.bob.status)+(Number.isInteger(r.bob.mismatches)?` · ${r.bob.mismatches} mismatches`:'');
  $('charlie').textContent=pretty(r.charlie.status)+(Number.isInteger(r.charlie.mismatches)?` · ${r.charlie.mismatches} mismatches`:'');
  $('reportid').textContent='Report '+r.id.slice(0,12);$('execute').disabled=!['EXECUTABLE','EXECUTED'].includes(d.operation);
  const obs=r.observations;const b=[0,1,2,3].map(c=>{let a=obs.filter(x=>x.branch===c);return a.reduce((v,x)=>v+x.errors,0)/a.reduce((v,x)=>v+x.n,0)});
  const pooled=obs.reduce((v,x)=>v+x.errors,0)/obs.reduce((v,x)=>v+x.n,0);
  $('pooled').textContent=`Pooled error ${(100*pooled).toFixed(2)}%`;
  drawChart(b,r.config.baseline);
  $('chartNote').textContent=`Baseline reference: ${(100*r.config.baseline).toFixed(1)}% · Flagged scopes: ${r.channel_analysis.flagged_count} / ${r.channel_analysis.family_size}`;
  $('evidence-empty').hidden=true;$('evidence-content').hidden=false;$('evidence-status').textContent=pretty(d.channel);
  $('evidenceRows').innerHTML=r.channel_analysis.tests.map(t=>`<tr class="${t.flag?'flag':''}"><td>${safe(t.kind)} · ${safe(t.label)}</td><td>${t.rate==null?'—':(100*t.rate).toFixed(2)+'%'}</td><td>${(100*t.threshold).toFixed(2)}%</td><td>${t.n}</td><td>${t.flag?'DEVIATION':t.sufficient?'NORMAL':'INSUFFICIENT'}</td></tr>`).join('');
  $('reason').textContent=r.channel_analysis.reason;$('assumptions').textContent='Model: '+r.channel_analysis.model+'. '+r.limits[0];
}
async function run(){const button=$('run');button.disabled=true;status('Running simulation and evaluating statistical tests…');try{const body={scenario:$('scenario').value,seed:Number($('seed').value),per_branch:Number($('probeN').value),length:4096};const res=await fetch('/api/experiments',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await res.json();if(!res.ok)throw Error(data.error||'Experiment failed');render(data);status(`${data.title} · ${data.elapsed_ms} ms · Status: ${data.channel_analysis.status.replaceAll('_',' ')}`);}catch(e){status('Error: '+e.message)}finally{button.disabled=false}}
async function execute(){if(!report)return;const res=await fetch('/api/execute',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:report.id})});const out=await res.json();if(out.report)render(out.report);status(out.status==='EXECUTED'?'Release action executed once. Subsequent attempts will test replay blocking.':out.status==='REPLAY_BLOCKED'?'Replay blocked by atomic guard. Signature validity unchanged.':out.reason||'Operation blocked.');}
function download(){if(!report)return;const blob=new Blob([JSON.stringify(report,null,2)],{type:'application/json'}),link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download=`qpramaan-evidence-${report.id.slice(0,12)}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000)}
async function calculate(){const body={target:Number($('target').value),budget:Number($('budget').value),model:$('model').value};const res=await fetch('/api/planner',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const p=await res.json();if(!res.ok){$('planResult').textContent=p.error;return}const s=p.selected;$('planResult').innerHTML=s?`<div class="plan-metrics"><div><small>SIGNATURE LENGTH</small><strong>${s.length.toLocaleString()}</strong></div><div><small>BELL PAIRS</small><strong>${s.bell_pairs.toLocaleString()}</strong></div><div><small>CLASSICAL CORRECTION BITS</small><strong>${s.teleportation_classical_bits.toLocaleString()}</strong></div></div><p>Reference upper bounds: forgery ${s.forgery.toExponential(2)} · repudiation ${s.repudiation.toExponential(2)} · exchange abort ${s.exchange_abort_union.toExponential(2)}</p>`:`<div class="empty">${safe(p.reason||'The requested target exceeds this Bell-pair budget.')}</div>`;$('planResult').innerHTML+=`<div class="explainer"><h3>Assumptions behind these bounds</h3><p>${p.assumptions.map(safe).join(' · ')}</p><p>${safe(p.claim)}</p></div>`;}
function showBenchmark(b){if(!b.channel_results){$('benchContent').textContent='No completed benchmark yet.';return}benchmark=b;let rows=b.channel_results.map(x=>`<tr><td>${safe(x.scenario)}</td><td>${x.pooled.flagged.toLocaleString()} / ${x.trials.toLocaleString()}</td><td>${x.full.flagged.toLocaleString()} / ${x.trials.toLocaleString()}</td><td>${(100*x.full.wilson_95[0]).toFixed(1)}–${(100*x.full.wilson_95[1]).toFixed(1)}%</td></tr>`).join('');$('benchContent').className='';$('benchContent').innerHTML=`<div class="tablewrap"><table><thead><tr><th>Scenario</th><th>Pooled flags</th><th>Full detector flags</th><th>Full 95% interval</th></tr></thead><tbody>${rows}</tbody></table></div><div class="explainer"><h3>What was tested</h3><p>${safe(b.notes.join(' '))}</p><p>Seed ${b.seed}; ${b.per_branch.toLocaleString()} observations per Bell outcome; ${b.channel_results[0].trials.toLocaleString()} batches per scenario. Minimum corrected-state fidelity ${b.correctness.minimum_fidelity.toFixed(12)} across ${b.correctness.count} checks.</p></div>`;}
async function init(){try{const m=await(await fetch('/api/meta')).json();$('scenario').innerHTML=Object.entries(m.scenarios).map(([k,v])=>`<option value="${k}">${safe(v[0])}</option>`).join('');$('scenario').value='targeted';const b=await(await fetch('/api/benchmark')).json();showBenchmark(b);await calculate();await run();}catch(e){status('Server connection failed: '+e.message)}}
$('run').onclick=run;$('execute').onclick=execute;$('download').onclick=download;$('calculate').onclick=calculate;init();
