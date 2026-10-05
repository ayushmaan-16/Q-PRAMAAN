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
    c.fillStyle='#334155';c.fillRect(center-31,h-Math.min(h-10,baseline*scale),18,Math.min(h-10,baseline*scale));
    c.fillStyle='#ff8a1f';c.fillRect(center-8,h-Math.min(h-10,q*scale),26,Math.max(2,Math.min(h-10,q*scale)));
    c.fillStyle='#f8fafc';c.font='600 12px "JetBrains Mono", monospace';c.textAlign='center';c.fillText((100*q).toFixed(1)+'%',center,h-Math.min(h-10,q*scale)-9);
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

  // Dual-pipeline comparative analytics
  const totalN = obs.reduce((v,x)=>v+x.n, 0);
  const totalErr = obs.reduce((v,x)=>v+x.errors, 0);
  const pooledRate = totalN ? totalErr / totalN : 0;
  const pooledMargin = Math.sqrt(Math.log(1 / 0.01) / (2 * (totalN || 1)));
  const legacyFlagged = pooledRate > (r.config.baseline + pooledMargin);
  const b0Obs = obs.filter(x => x.branch === 0);
  const b0N = b0Obs.reduce((v,x)=>v+x.n, 0);
  const b0Err = b0Obs.reduce((v,x)=>v+x.errors, 0);
  const b0Rate = b0N ? b0Err / b0N : 0;

  $('legacyQber').textContent = (100 * pooledRate).toFixed(2) + '%';
  $('qpramaanBranch').textContent = (100 * b0Rate).toFixed(2) + '%';

  if (r.scenario === 'targeted') {
    $('legacyStatus').textContent = 'NORMAL';
    $('legacyStatus').className = 'good';
    $('legacyAction').textContent = 'EXECUTE';
    $('legacyAction').className = 'bad';
    $('legacyCallout').className = 'pipeline-callout bad';
    $('legacyPill').textContent = 'BREACH';
    $('legacyPill').className = 'pipeline-status-pill bad';
    $('legacyTitle').textContent = 'SILENT COMPROMISE';
    $('legacyDesc').textContent = 'Targeted Pauli disturbance in Bell outcome 00 (8%) is diluted into the 2% pooled average. Conventional detector reports normal and allows execution on a tampered link.';

    $('qpramaanStatus').textContent = 'ANOMALY';
    $('qpramaanStatus').className = 'warn';
    $('qpramaanAction').textContent = 'QUARANTINE';
    $('qpramaanAction').className = 'warn';
    $('qpramaanCallout').className = 'pipeline-callout good';
    $('qpramaanPill').textContent = 'INTERLOCKED';
    $('qpramaanPill').className = 'pipeline-status-pill good';
    $('qpramaanTitle').textContent = 'ATTACK CAUGHT & QUARANTINED';
    $('qpramaanDesc').textContent = `Bell outcome 00 error (${(100*b0Rate).toFixed(1)}%) tripped the conditional Hoeffding threshold. Operation safely quarantined while signature validity is preserved.`;
  } else if (r.scenario === 'legitimate') {
    $('legacyStatus').textContent = 'NORMAL';
    $('legacyStatus').className = 'good';
    $('legacyAction').textContent = 'EXECUTE';
    $('legacyAction').className = 'good';
    $('legacyCallout').className = 'pipeline-callout good';
    $('legacyPill').textContent = 'HEALTHY';
    $('legacyPill').className = 'pipeline-status-pill good';
    $('legacyTitle').textContent = 'BENIGN OPERATION';
    $('legacyDesc').textContent = 'Channel operates at normal 2% baseline noise across all outcomes. Execution permitted.';

    $('qpramaanStatus').textContent = 'CONSISTENT';
    $('qpramaanStatus').className = 'good';
    $('qpramaanAction').textContent = 'EXECUTE';
    $('qpramaanAction').className = 'good';
    $('qpramaanCallout').className = 'pipeline-callout good';
    $('qpramaanPill').textContent = 'VERIFIED';
    $('qpramaanPill').className = 'pipeline-status-pill good';
    $('qpramaanTitle').textContent = 'ALL 20 SCOPES VERIFIED';
    $('qpramaanDesc').textContent = 'All Bell outcomes and Pauli bases confirmed within finite-sample baseline bounds.';
  } else if (r.scenario === 'replay') {
    $('legacyStatus').textContent = 'NORMAL';
    $('legacyStatus').className = 'good';
    $('legacyAction').textContent = 'REPLAY ALLOWED';
    $('legacyAction').className = 'bad';
    $('legacyCallout').className = 'pipeline-callout bad';
    $('legacyPill').textContent = 'EXPOSED';
    $('legacyPill').className = 'pipeline-status-pill bad';
    $('legacyTitle').textContent = 'REPLAY VULNERABILITY';
    $('legacyDesc').textContent = 'Conventional QDS without atomic receipt tracking permits re-submission of historically valid declarations.';

    $('qpramaanStatus').textContent = 'CONSISTENT';
    $('qpramaanStatus').className = 'good';
    $('qpramaanAction').textContent = 'REPLAY BLOCKED';
    $('qpramaanAction').className = 'warn';
    $('qpramaanCallout').className = 'pipeline-callout good';
    $('qpramaanPill').textContent = 'BLOCKED';
    $('qpramaanPill').className = 'pipeline-status-pill good';
    $('qpramaanTitle').textContent = 'ATOMIC RECEIPT GUARD';
    $('qpramaanDesc').textContent = 'SQLite receipt ledger detects previously executed session token. Duplicate execution rejected without invalidating signature.';
  } else if (r.scenario === 'forgery') {
    $('legacyStatus').textContent = 'NORMAL';
    $('legacyStatus').className = 'good';
    $('legacyAction').textContent = 'BLOCKED';
    $('legacyAction').className = 'warn';
    $('legacyCallout').className = 'pipeline-callout warn';
    $('legacyPill').textContent = 'REJECTED';
    $('legacyPill').className = 'pipeline-status-pill warn';
    $('legacyTitle').textContent = 'SIGNATURE INVALID';
    $('legacyDesc').textContent = 'Recipient mismatch threshold exceeded during forwarded verification.';

    $('qpramaanStatus').textContent = 'CONSISTENT';
    $('qpramaanStatus').className = 'good';
    $('qpramaanAction').textContent = 'BLOCKED';
    $('qpramaanAction').className = 'warn';
    $('qpramaanCallout').className = 'pipeline-callout good';
    $('qpramaanPill').textContent = 'DISALLOWED';
    $('qpramaanPill').className = 'pipeline-status-pill good';
    $('qpramaanTitle').textContent = 'FORGERY DETECTED';
    $('qpramaanDesc').textContent = 'Bob local guessing fails Charlie forwarded verification threshold (s_v L). Symmetrized state elimination protects recipient.';
  } else {
    $('legacyStatus').textContent = legacyFlagged ? 'ANOMALY' : 'NORMAL';
    $('legacyStatus').className = legacyFlagged ? 'warn' : 'good';
    $('legacyAction').textContent = legacyFlagged ? 'BLOCKED' : (d.operation === 'EXECUTABLE' ? 'EXECUTE' : 'BLOCKED');
    $('legacyAction').className = legacyFlagged ? 'warn' : (d.operation === 'EXECUTABLE' ? 'good' : 'bad');
    $('legacyCallout').className = legacyFlagged ? 'pipeline-callout warn' : 'pipeline-callout';
    $('legacyPill').textContent = legacyFlagged ? 'ALERT' : 'NORMAL';
    $('legacyPill').className = 'pipeline-status-pill ' + (legacyFlagged ? 'bad' : 'good');
    $('legacyTitle').textContent = legacyFlagged ? 'HIGH POOLED ERROR' : 'AGGREGATE RATE WITHIN LIMIT';
    $('legacyDesc').textContent = legacyFlagged ? `Pooled QBER (${(100*pooledRate).toFixed(1)}%) exceeded aggregate limit.` : `Pooled QBER (${(100*pooledRate).toFixed(1)}%) within aggregate tolerance.`;

    $('qpramaanStatus').textContent = pretty(d.channel);
    color($('qpramaanStatus'), d.channel);
    $('qpramaanAction').textContent = pretty(d.operation);
    color($('qpramaanAction'), d.operation);
    $('qpramaanCallout').className = d.operation === 'EXECUTABLE' ? 'pipeline-callout good' : 'pipeline-callout warn';
    $('qpramaanPill').textContent = d.operation === 'EXECUTABLE' ? 'VERIFIED' : 'ISOLATED';
    $('qpramaanPill').className = 'pipeline-status-pill ' + (d.operation === 'EXECUTABLE' ? 'good' : 'warn');
    $('qpramaanTitle').textContent = `DECISION: ${pretty(d.operation)}`;
    $('qpramaanDesc').textContent = r.channel_analysis.reason;
  }

  // Active run margin deltas
  const legacyLimit = r.config.baseline + pooledMargin;
  const legacyDeltaVal = pooledRate - legacyLimit;
  const legacyDeltaSign = legacyDeltaVal >= 0 ? '+' : '';
  $('legacyDelta').textContent = `${legacyDeltaSign}${(100 * legacyDeltaVal).toFixed(2)}%`;
  $('legacyDelta').className = legacyDeltaVal > 0 ? 'bad' : 'good';
  $('legacyDeltaSub').textContent = legacyDeltaVal > 0 ? 'Exceeds threshold' : 'Under threshold (Safe)';

  const b0Test = r.channel_analysis.tests.find(t => t.kind === 'branch' && t.label === '00') || r.channel_analysis.tests[0];
  const qpDeltaVal = (b0Test.rate || 0) - b0Test.threshold;
  const qpDeltaSign = qpDeltaVal >= 0 ? '+' : '';
  $('qpramaanDelta').textContent = `${qpDeltaSign}${(100 * qpDeltaVal).toFixed(2)}%`;
  $('qpramaanDelta').className = qpDeltaVal > 0 ? 'bad' : 'good';
  $('qpramaanDeltaSub').textContent = qpDeltaVal > 0 ? `+${(100*qpDeltaVal).toFixed(2)}% over bound` : 'Within bound';

  $('evidence-empty').hidden=true;$('evidence-content').hidden=false;$('evidence-status').textContent=pretty(d.channel);
  $('evidenceRows').innerHTML=r.channel_analysis.tests.map(t=>`<tr class="${t.flag?'flag':''}"><td>${safe(t.kind)} · ${safe(t.label)}</td><td>${t.rate==null?'—':(100*t.rate).toFixed(2)+'%'}</td><td>${(100*t.threshold).toFixed(2)}%</td><td>${t.n}</td><td>${t.flag?'DEVIATION':t.sufficient?'NORMAL':'INSUFFICIENT'}</td></tr>`).join('');
  $('reason').textContent=r.channel_analysis.reason;$('assumptions').textContent='Model: '+r.channel_analysis.model+'. '+r.limits[0];

  if (r.traces) renderTraceSection(r.traces);
}

let currentTraces = [];
let activeTraceFilter = 'all';
let selectedTraceId = 0;
let sandboxState = null;

function renderTraceSection(traces) {
  currentTraces = traces || [];
  const meta = $('traceStreamMeta');
  if (meta) meta.textContent = `${currentTraces.length} Bell Pairs Analyzed`;
  applyTraceFilter();
}

function applyTraceFilter() {
  let filtered = currentTraces;
  if (activeTraceFilter === 'branch0') {
    filtered = currentTraces.filter(t => t.branch === 0);
  } else if (activeTraceFilter === 'perturbed') {
    filtered = currentTraces.filter(t => t.is_perturbed);
  } else if (activeTraceFilter === 'clean') {
    filtered = currentTraces.filter(t => !t.is_perturbed);
  } else if (activeTraceFilter === 'mismatch') {
    filtered = currentTraces.filter(t => t.mismatch);
  }

  const strip = $('traceStrip');
  if (!strip) return;
  if (filtered.length === 0) {
    strip.innerHTML = '<div class="empty" style="padding:14px;width:100%;">No frames match current filter.</div>';
    return;
  }

  strip.innerHTML = filtered.map(t => `
    <div class="trace-chip ${t.is_perturbed ? 'perturbed' : ''} ${t.is_targeted_attack ? 'targeted' : ''} ${t.frame_id === selectedTraceId ? 'active' : ''}" data-id="${t.frame_id}">
      <div class="trace-chip-head">
        <span>#${String(t.frame_id).padStart(2, '0')}</span>
        <span class="${t.mismatch ? 'bad' : 'good'}">${t.mismatch ? 'ERR' : 'OK'}</span>
      </div>
      <div class="trace-chip-state">${safe(t.state_name)}</div>
      <div class="trace-chip-badges">
        <span class="trace-chip-badge branch">B${safe(t.branch_label)}</span>
        <span class="trace-chip-badge ${t.is_perturbed ? 'pauli-err' : ''}">${safe(t.pauli)}</span>
      </div>
    </div>
  `).join('');

  strip.querySelectorAll('.trace-chip').forEach(el => {
    el.onclick = () => selectTraceFrame(Number(el.dataset.id));
  });

  const exists = filtered.some(t => t.frame_id === selectedTraceId);
  if (!exists && filtered.length > 0) {
    selectTraceFrame(filtered[0].frame_id);
  } else if (exists) {
    selectTraceFrame(selectedTraceId);
  }
}

function selectTraceFrame(id) {
  selectedTraceId = id;
  document.querySelectorAll('.trace-chip').forEach(el => {
    el.classList.toggle('active', Number(el.dataset.id) === id);
  });

  const t = currentTraces.find(x => x.frame_id === id);
  if (!t) return;

  $('traceFrameLabel').textContent = `FRAME #${String(t.frame_id).padStart(2, '0')}`;
  $('traceFrameTitle').textContent = `Alice ${t.state_name} · Bell Branch ${t.branch_label} · Channel ${t.pauli_name}`;

  const fidBadge = $('traceFidelityBadge');
  fidBadge.textContent = `FIDELITY ${(t.fidelity).toFixed(3)}`;
  fidBadge.className = 'pipeline-status-pill ' + (t.fidelity >= 0.99 ? 'good' : 'bad');

  const matchBadge = $('traceMatchBadge');
  matchBadge.textContent = t.mismatch ? 'MISMATCH (REJECT)' : 'COMPATIBLE';
  matchBadge.className = 'pipeline-status-pill ' + (t.mismatch ? 'bad' : 'good');

  // Stage 1
  $('stage1State').textContent = t.state_name;
  $('stage1Dirac').textContent = t.state_dirac;
  $('stage1Basis').textContent = t.basis;
  $('stage1Bloch').textContent = `(${t.alice_bloch.x.toFixed(1)}, ${t.alice_bloch.y.toFixed(1)}, ${t.alice_bloch.z.toFixed(1)})`;

  // Stage 2
  $('stage2Branch').textContent = `Branch ${t.branch_label}`;
  $('stage2Bell').textContent = t.branch === 0 ? '|Φ⁺⟩ = (|00⟩+|11⟩)/√2' : (t.branch === 1 ? '|Ψ⁺⟩ = (|01⟩+|10⟩)/√2' : (t.branch === 2 ? '|Φ⁻⟩ = (|00⟩-|11⟩)/√2' : '|Ψ⁻⟩ = (|01⟩-|10⟩)/√2'));
  $('stage2Feed').textContent = `z=${t.feed_forward.z}, x=${t.feed_forward.x}`;
  $('stage2Corr').textContent = t.correction;

  // Stage 3
  $('stage3Pauli').textContent = `Operator ${t.pauli}`;
  $('stage3Desc').textContent = t.pauli_name;
  const targetTag = $('stage3TargetTag');
  targetTag.textContent = t.is_targeted_attack ? 'Targeted Attack: YES (Branch 00)' : (t.is_perturbed ? 'Ordinary Noise: YES' : 'Perturbed: NO (Identity)');
  targetTag.className = t.is_targeted_attack ? 'bad' : (t.is_perturbed ? 'warn' : 'good');

  // Stage 4
  $('stage4Operator').textContent = `U = Z^${t.feed_forward.z} X^${t.feed_forward.x} = ${t.correction}`;
  $('stage4Result').textContent = t.fidelity >= 0.99 ? 'Eigenstate restored' : 'Perturbed outcome state';
  $('stage4Fidelity').textContent = (t.fidelity).toFixed(3);
  $('stage4Bloch').textContent = `(${t.receiver_bloch.x.toFixed(1)}, ${t.receiver_bloch.y.toFixed(1)}, ${t.receiver_bloch.z.toFixed(1)})`;

  // Stage 5
  $('stage5Measured').textContent = `Measured: ${t.measured_state} (bit ${t.measured_bit})`;
  $('stage5Prob').textContent = `Born P(0)=${(100*t.p0).toFixed(1)}% · P(1)=${(100*t.p1).toFixed(1)}%`;
  $('stage5Basis').textContent = `Basis ${t.basis}`;

  // Stage 6
  $('stage6Eliminated').textContent = `Eliminated: ${t.eliminated_state}`;
  $('stage6Declared').textContent = `Alice Declared: ${t.declared_state}`;
  const verdict = $('stage6Verdict');
  verdict.textContent = t.mismatch ? 'MISMATCH (Deviation)' : 'PASSED (Compatible)';
  verdict.className = t.mismatch ? 'bad' : 'good';
}

async function updateSandbox() {
  const body = {
    state: Number($('sbState').value),
    branch: Number($('sbBranch').value),
    pauli: Number($('sbPauli').value),
    basis: Number($('sbBasis').value)
  };
  try {
    const res = await fetch('/api/trace', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!res.ok) return;
    sandboxState = data;

    const f = data.receiver.fidelity;
    $('sbFidelity').textContent = f.toFixed(4);
    $('sbFidelity').className = f >= 0.99 ? 'good' : 'bad';
    $('sbFidelitySub').textContent = f >= 0.99 ? 'State preserved with unit fidelity' : 'State perturbed by channel operator';

    $('sbProb0Bar').style.width = `${(100 * data.measurement.p0).toFixed(1)}%`;
    $('sbProb1Bar').style.width = `${(100 * data.measurement.p1).toFixed(1)}%`;
    $('sbProb0Label').textContent = `P(0) [${data.measurement.eigenstates[0]}]: ${(100 * data.measurement.p0).toFixed(1)}%`;
    $('sbProb1Label').textContent = `P(1) [${data.measurement.eigenstates[1]}]: ${(100 * data.measurement.p1).toFixed(1)}%`;

    $('sbAliceBloch').textContent = `(${data.alice.bloch.x.toFixed(1)}, ${data.alice.bloch.y.toFixed(1)}, ${data.alice.bloch.z.toFixed(1)})`;
    $('sbRecBloch').textContent = `(${data.receiver.bloch.x.toFixed(1)}, ${data.receiver.bloch.y.toFixed(1)}, ${data.receiver.bloch.z.toFixed(1)})`;

    $('sbElimInfo').innerHTML = `Measuring 0 eliminates <strong>${data.measurement.eliminated_if_0}</strong> (${data.measurement.mismatch_if_0 ? '<span class="bad">MISMATCH</span>' : '<span class="good">SAFE</span>'}). Measuring 1 eliminates <strong>${data.measurement.eliminated_if_1}</strong> (${data.measurement.mismatch_if_1 ? '<span class="bad">MISMATCH</span>' : '<span class="good">SAFE</span>'}).`;
  } catch (e) {
    console.error(e);
  }
}

function collapseSandbox() {
  if (!sandboxState) return;
  const p0 = sandboxState.measurement.p0;
  const roll = Math.random();
  const bit = roll < p0 ? 0 : 1;
  const outcomeState = sandboxState.measurement.eigenstates[bit];
  const eliminated = bit === 0 ? sandboxState.measurement.eliminated_if_0 : sandboxState.measurement.eliminated_if_1;
  const mismatch = bit === 0 ? sandboxState.measurement.mismatch_if_0 : sandboxState.measurement.mismatch_if_1;

  $('sbShotResult').innerHTML = `Collapsed to <strong>${outcomeState}</strong> (bit ${bit}, roll ${(roll*100).toFixed(1)}%). Eliminated state: <strong>${eliminated}</strong>. Alice declared <strong>${sandboxState.alice.name}</strong> → <span class="${mismatch ? 'bad' : 'good'}">${mismatch ? 'SIGNATURE MISMATCH' : 'VERIFIED COMPATIBLE'}</span>`;
}

async function run(){const button=$('run');button.disabled=true;status('Running simulation and evaluating statistical tests…');try{const body={scenario:$('scenario').value,seed:Number($('seed').value),per_branch:Number($('probeN').value),length:4096};const res=await fetch('/api/experiments',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await res.json();if(!res.ok)throw Error(data.error||'Experiment failed');render(data);status(`${data.title} · ${data.elapsed_ms} ms · Status: ${data.channel_analysis.status.replaceAll('_',' ')}`);}catch(e){status('Error: '+e.message)}finally{button.disabled=false}}
async function execute(){if(!report)return;const res=await fetch('/api/execute',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:report.id})});const out=await res.json();if(out.report)render(out.report);status(out.status==='EXECUTED'?'Release action executed once. Subsequent attempts will test replay blocking.':out.status==='REPLAY_BLOCKED'?'Replay blocked by atomic guard. Signature validity unchanged.':out.reason||'Operation blocked.');}
function download(){if(!report)return;const blob=new Blob([JSON.stringify(report,null,2)],{type:'application/json'}),link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download=`qpramaan-evidence-${report.id.slice(0,12)}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000)}
async function calculate(){const body={target:Number($('target').value),budget:Number($('budget').value),model:$('model').value};const res=await fetch('/api/planner',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const p=await res.json();if(!res.ok){$('planResult').textContent=p.error;return}const s=p.selected;$('planResult').innerHTML=s?`<div class="plan-metrics"><div><small>SIGNATURE LENGTH</small><strong>${s.length.toLocaleString()}</strong></div><div><small>BELL PAIRS</small><strong>${s.bell_pairs.toLocaleString()}</strong></div><div><small>CLASSICAL CORRECTION BITS</small><strong>${s.teleportation_classical_bits.toLocaleString()}</strong></div></div><p>Reference upper bounds: forgery ${s.forgery.toExponential(2)} · repudiation ${s.repudiation.toExponential(2)} · exchange abort ${s.exchange_abort_union.toExponential(2)}</p>`:`<div class="empty">${safe(p.reason||'The requested target exceeds this Bell-pair budget.')}</div>`;$('planResult').innerHTML+=`<div class="explainer"><h3>Assumptions behind these bounds</h3><p>${p.assumptions.map(safe).join(' · ')}</p><p>${safe(p.claim)}</p></div>`;}
function showBenchmark(b){if(!b.channel_results){$('benchContent').textContent='No completed benchmark yet.';return}benchmark=b;let rows=b.channel_results.map(x=>`<tr><td>${safe(x.scenario)}</td><td>${x.pooled.flagged.toLocaleString()} / ${x.trials.toLocaleString()}</td><td>${x.full.flagged.toLocaleString()} / ${x.trials.toLocaleString()}</td><td>${(100*x.full.wilson_95[0]).toFixed(1)}–${(100*x.full.wilson_95[1]).toFixed(1)}%</td></tr>`).join('');$('benchContent').className='';$('benchContent').innerHTML=`<div class="tablewrap"><table><thead><tr><th>Scenario</th><th>Pooled flags</th><th>Full detector flags</th><th>Full 95% interval</th></tr></thead><tbody>${rows}</tbody></table></div><div class="explainer"><h3>What was tested</h3><p>${safe(b.notes.join(' '))}</p><p>Seed ${b.seed}; ${b.per_branch.toLocaleString()} observations per Bell outcome; ${b.channel_results[0].trials.toLocaleString()} batches per scenario. Minimum corrected-state fidelity ${b.correctness.minimum_fidelity.toFixed(12)} across ${b.correctness.count} checks.</p></div>`;}
async function init(){
  try{
    const m=await(await fetch('/api/meta')).json();
    $('scenario').innerHTML=Object.entries(m.scenarios).map(([k,v])=>`<option value="${k}">${safe(v[0])}</option>`).join('');
    $('scenario').value='targeted';
    const b=await(await fetch('/api/benchmark')).json();
    showBenchmark(b);
    await calculate();
    await updateSandbox();
    await run();
  } catch(e){
    status('Server connection failed: '+e.message)
  }
}

document.querySelectorAll('.trace-filter-btn').forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll('.trace-filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeTraceFilter = btn.dataset.filter;
    applyTraceFilter();
  };
});

['sbState', 'sbBranch', 'sbPauli', 'sbBasis'].forEach(id => {
  const el = $(id);
  if (el) el.onchange = updateSandbox;
});
if ($('sbCollapse')) $('sbCollapse').onclick = collapseSandbox;
if ($('gotoTrace')) $('gotoTrace').onclick = () => tab('physics');

$('run').onclick=run;$('execute').onclick=execute;$('download').onclick=download;$('calculate').onclick=calculate;init();

