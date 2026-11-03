const AG={capture:['Capture','#0284c7','Reads receipts'],reconciler:['Reconciler','#7c3aed','Matches the bank'],controller:['Controller','#059669','Posts and closes'],redteam:['Red Team','#dc2626','Hunts fraud'],treasurer:['Treasurer','#d97706','Finds the cash']};
var f=n=>Number(n).toLocaleString('en-AE',{maximumFractionDigits:0});const $=id=>document.getElementById(id);let chart,DATA;
$('roster').innerHTML=Object.entries(AG).map(([k,[n,c,d]])=>`<div class="agent" id="ag-${k}" style="color:${c}"><div class="av" style="background:${c}">${n[0]}</div><div><div style="color:var(--txt);font-weight:600">${n}</div><div class="st" id="st-${k}">${d}</div></div></div>`).join('');
function setMeter(m){if(!m||!m.overall)return;$('tot').textContent=m.overall.automated_pct+'%';$('totsub').textContent=`${m.overall.rule} by rules, ${m.overall.model} by Muse, ${m.overall.human} by you`;
 $('meters').innerHTML=Object.entries(m.stages).map(([k,s])=>`<div class="m">${k.replace('_',' ')}<b>${s.total>1?s.automated_pct+'%':'...'}</b><div class="bar"><i style="width:${s.total>1?s.automated_pct:0}%"></i></div></div>`).join('')}
function drawCash(series,weeks){const L=weeks.map((w,i)=>'W'+(i+1));if(chart)chart.destroy();
 const cfg=[['base','#2563eb',[]],['base_with_levers','#059669',[]],['downside','#dc2626',[5,4]],['downside_with_levers','#d97706',[5,4]]];
 chart=new Chart($('cash'),{type:'line',data:{labels:L,datasets:cfg.map(([k,c,d])=>({label:k.replaceAll('_',' '),data:series[k],borderColor:c,borderDash:d,tension:.3,pointRadius:series[k].map((v,i)=>k=='downside'&&v==Math.min(...series[k])?7:0),pointBackgroundColor:c}))},
 options:{maintainAspectRatio:false,animation:{duration:1200},plugins:{legend:{labels:{color:'#5b6b82',boxWidth:10,font:{size:10}}}},scales:{x:{ticks:{color:'#5b6b82'},grid:{color:'#e8edf3'}},y:{ticks:{color:'#5b6b82',callback:v=>f(v/1000)+'k'},grid:{color:'#e8edf3'}}}}})}
function bubble(e,inner){const d=document.createElement('div');d.className='ev';d.style.setProperty('--c',e.color);
 d.innerHTML=`<div class="av" style="background:${e.color}">${e.name[0]}</div><div class="bub"><span class="who">${e.name}</span><span class="k">${e.kind}</span><div>${e.text}</div>${inner||''}</div>`;return d}
let debateBox=null;
const fmt=n=>Math.round(n||0).toLocaleString('en-US');let thinkEl=null;
function liveStats(st,live){if(!st)return;$('pcalls').textContent=fmt(st.calls);$('ptok').textContent=fmt(st.tokens);$('powered').classList.add('on');if(live===false)$('pwho').innerHTML='Replaying a <b>recorded real run</b> of Muse Spark Open on Baseten'}
function render(e){if(window.cashTick)cashTick(e);if(e.data&&e.data.stats)liveStats(e.data.stats);
 if(e.kind=='powered'){liveStats(e.data.stats,e.data.live);if(e.data.live){$('powered').classList.add('live');$('pwho').innerHTML='<b>Live now</b>: Muse Spark Open on Baseten'}return}
 if(e.kind=='thinking'){const feed=$('feed');if(!thinkEl||thinkEl.dataset.agent!=e.agent){thinkEl=document.createElement('div');thinkEl.className='ev thinking';thinkEl.dataset.agent=e.agent;thinkEl.style.setProperty('--c',e.color);thinkEl.innerHTML=`<div class="av" style="background:${e.color}">${e.name[0]}</div><div class="bub"><span class="who">${e.name}</span><span class="k">thinking live</span><div class="tt"></div></div>`;feed.appendChild(thinkEl)}
  thinkEl.querySelector('.tt').textContent='…'+e.text.slice(-260);feed.scrollTop=feed.scrollHeight;return}
 if(thinkEl){thinkEl.remove();thinkEl=null}
const feed=$('feed');document.querySelectorAll('.agent').forEach(a=>a.classList.remove('act'));const a=$('ag-'+e.agent);if(a){a.classList.add('act');if(window._lastAg!=e.agent){window._lastAg=e.agent;a.scrollIntoView({block:'nearest',behavior:'smooth'})}}if($('st-'+e.agent))$('st-'+e.agent).textContent=e.text.slice(0,40)+'...';
 setMeter(e.meter);let el;
 if(e.kind=='doc')el=bubble(e,`<div class="doc"><img src="${e.data.image}" onclick="window.open(this.src)"><div class="kv">${Object.entries(e.data.fields).filter(([k,v])=>typeof v!='object').map(([k,v])=>`<span>${k.replaceAll('_',' ')}</span><b>${typeof v=='number'?f(v):v}</b>`).join('')}</div></div><div class="sub">Muse Spark vision | ${e.data.secs}s | ${e.data.accuracy}/8 fields match the source</div>`);
 else if(e.kind=='cashcheck'){const t=e.data.totals;el=bubble(e,`<div class="levers">${['recovered','protected','released'].map(k=>`<div class="lv t"><span>${k}</span><b>AED ${fmt(t[k])}</b></div>`).join('')}</div>`)}
 else if(e.kind=='think'){const it=e.data.items,row=i=>`<div class="lv t"><code>${i.bank_id}</code><span>${(i.category||'').replaceAll('_',' ')}</span><span class="lo">${i.reason||''}</span></div>`;
  el=bubble(e,`<div class="levers">${it.slice(0,3).map(row).join('')}</div>${it.length>3?`<details class="more"><summary>more (${it.length-3})</summary><div class="levers">${it.slice(3).map(row).join('')}</div></details>`:''}`)}
 else if(e.kind=='flag')el=bubble(e,`<div class="sub">${e.data.finding.explanation||''}</div><div>${e.data.finding.proof.map(p=>'<code>'+p+'</code>').join(' ')}</div>`);
 else if(e.kind=='debate_start'){debateBox=document.createElement('div');debateBox.className='debate';debateBox.innerHTML=`<div class="sub">⚖ ${e.text} | Red Team vs Controller</div>`;feed.appendChild(debateBox);feed.scrollTop=feed.scrollHeight;return}
 else if(e.kind=='debate'&&debateBox){const t=document.createElement('div');t.className='dt'+(e.agent=='controller'?' r':'');t.style.animation='in .35s';t.innerHTML=`<div class="b"><b style="color:${e.color}">${e.name}</b><br>${e.text}</div>`;debateBox.appendChild(t);feed.scrollTop=feed.scrollHeight;return}
 else if(e.kind=='approval'){el=bubble(e,`<div class="appr">${e.data.flag=='large_payment_to_new_vendor'?`<button class="btn" onclick="decide(this,'large_payment_to_new_vendor','block')">⛔ Block payment</button><button class="btn ghost" onclick="decide(this,'large_payment_to_new_vendor','release')">Release payment</button>`:`<button class="btn" onclick="decide(this,'${e.data.flag}','approve_escalation')">Approve escalation</button><button class="btn ghost" onclick="decide(this,'${e.data.flag}','reject')">Reject</button>`}</div>`);
  $('dec').innerHTML=($('dec').textContent.startsWith('Escal')?'':$('dec').innerHTML)+`<div id="d-${e.data.flag}">⏳ ${e.data.flag.replaceAll('_',' ')}</div>`}
 else if(e.kind=='fraud'){const x=e.data;el=document.createElement('div');el.className='fraud';el.style.animation='in .5s';
  el.innerHTML=`<div class="sub">🚨 RED TEAM CATCH</div><h3>Hidden sale</h3><div class="big">AED ${f(x.amount)}</div><div class="sub">received on ${x.bank_id}, never invoiced | output VAT at risk AED ${x.vat_at_risk}</div>
  <p>${x.how}</p><h2>Evidence chain</h2><ol class="chain">${x.chain.map(c=>`<li>${c.step}<br><code>${c.proof}</code></li>`).join('')}</ol>
  <h2>Draft query to the CFO</h2><pre>${x.query}</pre><div class="appr"><button class="btn" onclick="decide(this,'hidden_sale','send_query')">Approve query</button><button class="btn ghost" onclick="decide(this,'hidden_sale','dismiss')">Dismiss</button></div>`}
 else if(e.kind=='forecast'){const sr=e.data.series;drawCash(sr,e.data.weeks);const d=sr.downside,mi=Math.min(...d);$('low').innerHTML=`<span class="no">Downside low AED ${f(mi)} in week ${d.indexOf(mi)+1}</span>`;
  const lo=k=>{const v=Math.min(...sr[k]);return [v,sr[k].indexOf(v)+1]},[b0,bw]=lo('base'),[d0,dw]=lo('downside'),[d1]=lo('downside_with_levers');
  const tile=(l,v,c)=>`<div class="ft"><span>${l}</span><b class="${c||''}">${v}</b></div>`;
  el=bubble({...e,text:`13-week cash plan ready. Base case stays positive; the downside dips below zero in week ${dw}, and three levers cut the gap.`},
  `<div class="ftiles">${tile('Base case low, week '+bw,K(b0))}${tile('Downside low, week '+dw,K(d0),'bad')}${tile('Downside low with levers',K(d1),d1<0?'bad':'ok')}</div>
  <div class="levers">${e.data.levers.map(L=>`<div class="lv"><span class="ln">${L.rank}. ${L.name}</span><span class="la">${K(L.amount)}</span><span class="lo">${L.owner}</span><span class="lw">Weeks ${L.first_week} to ${L.last_week}</span></div>`).join('')}</div>
  <details class="more"><summary>more</summary>${e.data.levers.map(L=>`<p><b>${L.name}:</b> ${L.action}${L.note?' ('+L.note+')':''}</p>`).join('')}<p>${e.data.narrative.split('\n')[0]}</p></details>`)}
 else el=bubble(e);
 feed.appendChild(el);feed.scrollTop=feed.scrollHeight}
async function decide(b,flag,d){await fetch('/api/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({flag,decision:d})});
 const lbl={block:'Payment blocked',release:'Payment released'}[d]||d.replaceAll('_',' ')+' recorded';const htm=`<span class="${d=='reject'||d=='dismiss'||d=='release'?'no':'ok'}">✔ ${lbl}</span> <a class="p" onclick="undecide('${flag}')">change</a>`;if(flag=='large_payment_to_new_vendor')document.querySelectorAll('.appr').forEach(x=>{if(x.innerHTML.includes("'large_payment_to_new_vendor'"))x.innerHTML=htm});b.parentNode&&(b.parentNode.innerHTML=htm);const r=$('d-'+flag);if(r)r.innerHTML=`✅ ${flag.replaceAll('_',' ')}: ${d.replaceAll('_',' ')}`;if(/new_vendor|B108/.test(flag)&&window.auditRefreshQ5)auditRefreshQ5()}
$('run').onclick=()=>{location.hash='';document.getElementById('ch1').scrollIntoView();$('run').disabled=true;$('feed').innerHTML='';if(window.cashReset)cashReset();if(window.cashTickStart)cashTickStart();const p=new URLSearchParams(location.search);const es=new EventSource('/api/close/stream'+(p.get('replay')?'?replay=1&speed='+(p.get('speed')||1):''));
 window._t0=Date.now();if(p.get('replay'))$('pwho').innerHTML='Replaying a <b>recorded real run</b> of Muse Spark Open on Baseten';clearInterval(window._tmr);window._tmr=setInterval(()=>{const sec=Math.round((Date.now()-_t0)/1000);$('run').textContent=`Closing… ${Math.floor(sec/60)}:${String(sec%60).padStart(2,'0')}`},500);es.onmessage=m=>{const e=JSON.parse(m.data);render(e);if(e.kind=='done'){es.close();clearInterval(window._tmr);$('run').textContent='Run the close again';$('run').disabled=false;if(window.cashLoad)cashLoad();if(window.showSummary)setTimeout(showSummary,800)}}};
// statements tab
async function showProof(ids){let h='<h2>Proof <a class="p" onclick="proof.style.display=\'none\'">close</a></h2>';
 for(const id of ids.slice(0,5)){const e=DATA.entries[id];h+=`<p><b>${id}</b> ${e.memo}</p>`;for(const r of e.proof){const p=await (await fetch('/api/proof/'+encodeURIComponent(r))).json();
 h+=`<div><code>${r}</code>${p.text?'<br>'+p.text:''}${p.row&&!Array.isArray(p.row)?'<pre>'+JSON.stringify(p.row,null,1)+'</pre>':''}${p.image?`<img src="${p.image}">`:''}</div>`}}
 if(ids.length>5)h+=`<p class="sub">and ${ids.length-5} more entries</p>`;$('proof').innerHTML=h;$('proof').style.display='block'}
function rows(t,o){t.innerHTML=Object.entries(o).map(([k,v])=>`<tr><td>${k} ${v.name}</td><td class="n"><a class="p" data-k="${k}">${f(Math.abs(v.amount))}</a></td></tr>`).join('');t.querySelectorAll('a.p').forEach(a=>a.onclick=()=>showProof(o[a.dataset.k].proof))}
fetch('/api/data').then(r=>r.json()).then(d=>{DATA=d;rows($('pnl'),d.pnl);rows($('bs'),d.bs);$('np').innerHTML=`<b>Net profit AED ${f(d.net_profit)}</b> | VAT payable AED ${f(d.vat)}`;setMeter(d.meter);
 LEV=d.treasury.levers.map(l=>`<tr><td>${l.rank}. <b>${l.name}</b><br><span class="sub">${l.action}</span></td><td class="n">${f(l.amount)}</td><td>${l.owner}</td></tr>`).join('');
 $('ck').innerHTML=Object.entries(d.checklist).map(([k,v])=>`<tr><td>${k.replaceAll('_',' ')}</td><td class="${v?'ok':'no'}">${v?'done':'needs review'}</td></tr>`).join('')});
// CFO chat
function addMsg(c,h){const d=document.createElement('div');d.className=c;d.innerHTML=h;$('chat').appendChild(d);$('chat').scrollTop=1e9}
function ansHtml(r){return `${r.answer}${r.proof&&r.proof.length?'<div>'+r.proof.map(p=>'<code>'+p+'</code>').join(' ')+'</div>':''}${r.actions?r.actions.map(a=>`<div style="margin-top:6px"><button class="btn ghost" onclick="${a.js}">${a.label}</button></div>`).join(''):''}`}
async function askq(q){if(!q)return;$('qin').value='';addMsg('q',q);addMsg('a sub','thinking...');const r=await (await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({q})})).json();$('chat').lastChild.remove();addMsg('a',ansHtml(r))}
async function voiceq(){const fd=new FormData();fd.append('audio',$('aud').files[0]);addMsg('a sub','listening...');const r=await (await fetch('/api/voice',{method:'POST',body:fd})).json();$('chat').lastChild.remove();addMsg('q','🎤 '+r.question);addMsg('a',ansHtml(r))}
async function credit(){$('cl').innerHTML='<span class="sub">running downside and drafting...</span>';const r=await (await fetch('/api/credit_line',{method:'POST'})).json();
 $('cl').innerHTML=`<p class="hint">Letter drafted, not sent.</p><p><a class="btn ghost sm" href="${r.pdf}" target="_blank">Open lender proof pack (PDF)</a></p>`}
async function byob(){const fd=new FormData();fd.append('bank',$('bcsv').files[0]);if($('ocash').value)fd.append('opening_cash',$('ocash').value);$('byobout').innerHTML='<span class="sub">Muse is mapping your columns...</span>';
 const r=await (await fetch('/api/byob',{method:'POST',body:fd})).json();if(r.error){$('byobout').innerHTML='<span class="no">'+r.error+'</span>';return}
 $('byobout').innerHTML=`<h2>Column mapping by Muse</h2><pre>${JSON.stringify(r.mapping,null,1)}</pre><h2>Close checks</h2><pre>${JSON.stringify(r.checks,null,1)}</pre><h2>Findings</h2><pre>${r.findings.join('\n')||'none'}</pre>`;
 new Chart($('bchart'),{type:'line',data:{labels:r.forecast.map((_,i)=>'W'+(i+1)),datasets:[{label:'projected cash',data:r.forecast,borderColor:'#0f766e',tension:.3}]},options:{maintainAspectRatio:false,plugins:{legend:{labels:{color:'#5b6b82'}}},scales:{x:{ticks:{color:'#5b6b82'}},y:{ticks:{color:'#5b6b82'}}}}})}
// ---- story chapters ----
let LEV='',I;
const A=n=>'AED '+Number(n).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
const K=n=>'AED '+(Math.abs(n)>=1000?Math.round(n/1000)+'k':Math.round(n));
const ACT={C1:'Lifts the chance AED 48,000 arrives on time to 80%',C2:'Lifts the chance the AED 52,000 plan is kept to 85%',C3:'Lifts the chance AED 40,000 arrives on its dates to 92%',S1:'Pay AED 60,430 thirty days later',S2:'Pay AED 8,791 thirty days later',S3:'Hold PI-0012 until credit note: the full AED 31,153 invoice waits 21 days. The credit note itself is AED 3,738'};
const P=x=>(x*100).toFixed(1)+'%';
const vb=c=>c.verified?'<span class="vb vy">verified</span>':'<span class="vb vn">rejected</span>';
const cites=c=>(c.cites||[]).map(r=>`<span class="cite" onclick="cite('${encodeURIComponent(r)}')">${r.split('/').pop()}</span>`).join('');
async function cite(r){const p=await (await fetch('/api/cite/'+r)).json();const b=$('proof');b.style.display='block';
 b.innerHTML=`<div class="row" style="justify-content:space-between"><b>Source</b><a class="p" onclick="proof.style.display='none'">Close</a></div><p><code>${decodeURIComponent(r)}</code></p><pre>${p.text||'not found'}</pre>`}
const claimRow=c=>`<div class="claim">${vb(c)}${c.claim}<div>${cites(c)}</div>${c.verified?'':`<div class="why">Why rejected: ${c.det_ok?c.muse_reason:c.det_reason}</div>`}</div>`;
const tbl=(head,rows)=>`<table><tr>${head.map(h=>`<th${h[0]=='>'?' class="n"':''}>${h.replace('>','')}</th>`).join('')}</tr>${rows.join('')}</table>`;
const hl=(tag,cls,title,text,amt,extra='')=>`<div class="card hl"><div class="head"><span class="tag ${cls}">${tag}</span>${amt?`<div class="amt">${amt}</div>`:''}</div><div><h3>${title}</h3><p>${text}</p>${extra}</div></div>`;
function showMore(id,btn){$(id).querySelectorAll('tr.more').forEach(r=>r.style.display='table-row');btn.remove()}
const topN=(rows,n,id)=>rows.map((r,i)=>i<n?r:r.replace('<tr','<tr class="more" style="display:none"'));

async function story(){
 const [ins,live,data]=await Promise.all([fetch('/api/insights').then(r=>r.json()),fetch('/api/live_events').then(r=>r.json()),fetch('/api/data').then(r=>r.json())]);I=ins;
 const p=I.proof,j=I.judgment;
 // chapter 2
 $('k2').textContent=`${p.verified}/${p.total}`;$('k2s').textContent=`${p.rejected} rejected and kept out of reports`;$('k2p').textContent=`${p.planted_caught}/${p.planted_total} planted false claims caught`;
 const ob=j.findings.find(c=>c.kind=='overbilling'),cut=j.adjustments.find(c=>c.verified&&c.kind=='accrued_revenue')||j.adjustments.find(c=>c.verified),rej=j.adjustments.find(c=>!c.verified);
 $('v2').innerHTML=hl('Overbilling','red','Palm Foods charged above the contract price',`Invoice ${ob.invoice} bills AED 12.50 per kg. The contract says AED 11.00.`,A(ob.amount*1.05),`<div style="margin-top:8px">${cites(ob)}</div>`)
  +hl('IFRS 15 cut-off','teal','Goods shipped 31 Oct, invoiced in November','Revenue belongs in October, so Divi accrues it.','AED 42,000',`<div style="margin-top:8px">${cites(cut)}</div>`)
  +hl('Rejected','amber','The verifier blocked a wrong amount','A prepayment claim said AED 18,000. The invoice says AED 18,000.12.','',`<div style="margin-top:8px">${cites(rej)}</div>`);
 $('k2c').innerHTML='<li>Code traces every number to its source</li><li>A second Muse call judges the evidence</li><li>Fails either check: rejected</li>';
 const all=[...j.findings,...j.signals,...j.adjustments,...I.flux.commentary];
 $('p2').innerHTML=`<h4>Rejected claims</h4>${p.rejected_items.map(r=>`<div class="claim"><span class="vb vn">rejected</span>${r.claim}<div class="why">Why: ${r.why}</div></div>`).join('')}
  <h4>Verifier self-test: planted false claims</h4>${p.planted.map(c=>`<div class="claim">${vb(c)}${c.claim} <span class="hint">Muse: ${c.muse_reason}</span></div>`).join('')}
  <h4>Contract terms Muse extracted</h4><div id="terms">${tbl(['Party','Term','Summary','Source'],topN(j.contract_terms.terms.map(t=>`<tr><td>${t.party}</td><td>${t.kind.replaceAll('_',' ')}</td><td>${t.summary}</td><td><span class="cite" onclick="cite('${encodeURIComponent(t.cite)}')">${t.cite.split('/').pop()}</span></td></tr>`),3))}<button class="btn ghost sm" onclick="showMore('terms',this)">Show all ${j.contract_terms.terms.length}</button></div>
  <h4>Customer signals from 15 emails and WhatsApp messages</h4>${j.signals.map(claimRow).join('')}
  <h4>All ${all.length} AI claims this close</h4>${all.map(claimRow).join('')}`;
 // chapter 3
 const fr=live.find(e=>e.kind=='fraud').data;const i0=live.findIndex(e=>e.kind=='debate_start');const deb=[];for(let i=i0+1;i<live.length&&live[i].kind=='debate';i++)deb.push(live[i]);
 const b=I.benchmark;
 $('k3c').innerHTML=fr.chain.slice(0,3).map(c=>`<div>${c.step}</div>`).join('');
 $('v3').innerHTML=`<div class="card"><div class="ctitle">⚖ The AED 50,000 debate: payment to a vendor created 2 days earlier</div>${deb.map(e=>`<div class="dt${e.agent=='controller'?' r':''}"><div class="b"><b style="color:${e.color}">${e.name}</b><br>${e.text}</div></div>`).join('')}
  <div class="appr" id="b108act"><button class="btn sm" onclick="decide(this,'large_payment_to_new_vendor','block')">⛔ Block payment</button><button class="btn ghost sm" onclick="decide(this,'large_payment_to_new_vendor','release')">Release payment</button></div></div>
  <div class="card"><div class="ctitle">Fraud benchmark: 20 planted anomalies in a copy of the books</div><div class="mini"><div><b>${b.detected}/${b.injected}</b><span>caught</span></div><div><b>${P(b.precision)}</b><span>precision</span></div><div><b>${b.false_positives.length}</b><span>false alarms</span></div></div></div>`;
 $('p3').innerHTML=`<h4>Hidden sale: evidence chain</h4><ol class="chain">${fr.chain.map(c=>`<li>${c.step}<br><code>${c.proof}</code></li>`).join('')}</ol>
  <h4>Draft query to the CFO (not sent)</h4><pre style="font:14px/1.6 Inter">${fr.query}</pre><div class="appr"><button class="btn sm" onclick="decide(this,'hidden_sale','send_query')">Approve query</button><button class="btn ghost sm" onclick="decide(this,'hidden_sale','dismiss')">Dismiss</button></div>
  <h4>All Red Team flags</h4>${tbl(['Rule','Items','Why it matters'],data.redteam.map(f=>`<tr><td>${f.rule.replaceAll('_',' ')}</td><td>${f.items.join(', ')}</td><td>${f.explanation||f.detail||''}</td></tr>`))}
  <h4>Benchmark: each anomaly</h4><div id="bm">${tbl(['Result','Type','Item'],topN(b.rows.sort((x,y)=>x.detected-y.detected).map(r=>`<tr><td>${r.detected?'<span class="vb vy">caught</span>':'<span class="vb vn">missed</span>'}</td><td>${r.kind}</td><td><code>${r.id}</code></td></tr>`),3))}<button class="btn ghost sm" onclick="showMore('bm',this)">Show all ${b.rows.length}</button></div>
  <p class="hint">The near-duplicate invoice changed by AED 1 was missed before; the near duplicate rule (same supplier, 7 days, AED 0.01 to 5 apart) now catches it.</p>`;
 // chapter 4
 const cb=I.cash.base,cw=I.cash.with_actions,L=cb.weeks.map((d,i)=>'W'+(i+1)),lev=data.treasury.levers.reduce((s,l)=>s+l.amount,0);
 const dsum=I.cash.drafts.reduce((t,d)=>t+d.impact.p50_delta,0);$('h4').textContent=`Six drafts add ${K(dsum)} to your tightest week and cut the risk of running out.`;$('h4s').textContent=`Measured on the median of 2,000 simulated futures in week 4, the low point. The wider 13-week cash release plan is ${K(lev)}, see proof.`;
 $('k4a').textContent=Math.round(cb.p_negative_any*100)+'%';$('k4b').textContent=P(cw.p_negative_any);$("k4s").textContent="in any of the next 13 weeks, before and after the six actions below";
 new Chart($('mcchart'),{type:'line',data:{labels:L,datasets:[
  {label:'P90',data:cb.p90,borderColor:'#bfdbfe',backgroundColor:'#dbeafe99',fill:'+2',pointRadius:0,borderWidth:1},
  {label:'Median (P50)',data:cb.p50,borderColor:'#0f2b4c',borderWidth:3,pointRadius:0,tension:.3},
  {label:'P10',data:cb.p10,borderColor:'#bfdbfe',pointRadius:0,borderWidth:1},
  {label:'Median after actions',data:cw.p50,borderColor:'#059669',borderWidth:2,borderDash:[5,4],pointRadius:0,tension:.3},
  {label:'zero',data:L.map(_=>0),borderColor:'#dc2626',borderWidth:1,pointRadius:0}]},
  options:{maintainAspectRatio:false,plugins:{legend:{position:'bottom',labels:{boxWidth:12,font:{family:'Inter',size:13},filter:i=>!['P10','zero'].includes(i.text)}}},scales:{x:{grid:{display:false}},y:{ticks:{callback:v=>(v/1000)+'k'},grid:{color:'#eef2f6'}}}}});
 $('drafts').innerHTML=I.cash.drafts.map(d=>`<div class="card dcard"><div class="agent">${d.agent}</div><div class="who">${d.party}</div><div class="subj">${d.subject||''}</div><div class="why">${ACT[d.id]||''}</div>
  <div class="impact">+${K(d.impact.p50_delta)}<small>to median cash in week ${d.impact.p50_low_week}, risk ${P(d.impact.p_neg_before)} → ${P(d.impact.p_neg_after)}</small></div>
  <details><summary>Read the draft</summary><pre>${d.body||''}</pre></details>
  <div class="acts"><button class="btn sm" onclick="decide2(this,'${d.id}','approve_draft')">Approve</button><button class="btn ghost sm" onclick="decide2(this,'${d.id}','reject')">Reject</button></div></div>`).join('');
 $('p4').innerHTML=`<h4>Payment behaviour per customer</h4>${tbl(['Customer','>Avg days late','>Spread','Signals Muse read','Proof'],Object.entries(I.cash.model).map(([c,m])=>`<tr><td>${c}</td><td class="n">${m.mean}</td><td class="n">${m.sd}</td><td>${m.signals.map(s=>s.kind.replaceAll('_',' ')+(s.pay_after?' after '+s.pay_after:'')).join(', ')||'-'}</td><td>${m.cites.map(r=>`<span class="cite" onclick="cite('${encodeURIComponent(r)}')">${r.startsWith('payment_history')?'history':r.split('#')[1]}</span>`).join('')}</td></tr>`))}
  <h4>Cash release plan (AED ${f(lev)})</h4><table>${LEV}</table>
  <p class="hint">Chance below zero in week 6: ${P(cb.p_negative_w6)}. The old single-line forecast said the low point was ${A(Math.min(...cb.deterministic))}; the median says ${A(Math.min(...cb.p50))}.</p>`;
 const tr=data.treasury;drawCash(Object.fromEntries(['base','base_with_levers','downside','downside_with_levers'].map(k=>[k,tr[k].closing])),tr.base.weeks);
 const dn=tr.downside.closing,mi=Math.min(...dn);$('low').innerHTML=`Downside low ${A(mi)} in week ${dn.indexOf(mi)+1}`;
 hood();loadLearning()}

function hood(){const v=I.uae.vat,ct=I.uae.ct,ei=I.uae.einv,t=I.trace;
 $('hs1').textContent=`VAT ${K(v.boxes.at(-1).vat)} · CT ${K(ct.estimated_tax)} a year · e-invoicing ${ei.ready_pct}% ready`;
 $('h-uae').innerHTML=`<div class="mini"><div><b>${A(v.boxes.at(-1).vat)}</b><span>VAT payable, Form 201 box 14 ${v.ties_to_ledger?'✔ ties to ledger':''}</span></div><div><b>${A(ct.estimated_tax)}</b><span>estimated corporate tax a year at 9%</span></div><div><b>${ei.ready_pct}%</b><span>e-invoicing ready · ${ei.trn_invalid.length} invalid TRNs</span></div></div>
  <h4>Form 201 boxes</h4>${tbl(['Box','Description','>Amount','>VAT'],v.boxes.map(x=>`<tr><td><b>${x.box}</b></td><td>${x.label}<div class="hint">${x.proof||''}</div></td><td class="n">${x.amount!=null?A(x.amount):''}</td><td class="n">${A(x.vat)}</td></tr>`))}
  <h4>Corporate tax</h4>${tbl(['Item','>AED'],[['October net profit',ct.oct_net_profit],['Margin on verified cut-off revenue',ct.cutoff_margin],['Annualised taxable profit',ct.annualised_profit],['0% band',ct.threshold],['Estimated annual tax at 9%',ct.estimated_tax],['Monthly provision',ct.monthly_provision]].map(([a,b])=>`<tr><td>${a}</td><td class="n">${A(b)}</td></tr>`))}<p class="hint">${ct.note}</p>
  <h4>E-invoicing fields</h4>${tbl(['Field','Status','Coverage'],ei.fields.map(x=>`<tr><td>${x.field}</td><td class="${x.status=='ok'?'ok':'no'}">${x.status}</td><td>${x.coverage}</td></tr>`))}<p class="hint">${ei.note}</p>`;
 const fx=I.flux;$('hs2').textContent=`${fx.commentary.filter(c=>c.verified).length}/${fx.commentary.length} sentences verified`;
 $('h-flux').innerHTML=`<div class="grid"><div class="s5">${tbl(['Line','>Sep','>Oct','>%'],fx.table.map(r=>`<tr><td>${r.name}</td><td class="n">${f(Math.abs(r.sep))}</td><td class="n">${f(Math.abs(r.oct))}</td><td class="n">${r.pct==null?'':r.pct+'%'}</td></tr>`))}</div><div class="s7">${fx.commentary.map(claimRow).join('')}</div></div>`;
 $('hs4').textContent=`${A(t.cost_aed)} for ${t.close_calls} Muse calls vs ${A(t.accountant_cost_aed)} manual`;
 $('h-trace').innerHTML=`<div class="mini"><div><b>${A(t.cost_aed)}</b><span>AI cost of this close</span></div><div><b>${t.tokens.toLocaleString()}</b><span>tokens, ${t.latency_s}s model time</span></div><div><b>${A(t.accountant_cost_aed)}</b><span>manual close, ${t.accountant.hours} hours (assumption)</span></div></div>
  ${tbl(['Purpose','Model','>Tokens in','>Out','>Seconds','>AED'],t.calls.map(c=>`<tr><td>${c.purpose}</td><td>${c.model}</td><td class="n">${c.tokens_in}</td><td class="n">${c.tokens_out}</td><td class="n">${c.latency_s}</td><td class="n">${c.cost_aed.toFixed(4)}</td></tr>`))}<p class="hint">${t.price_note}. ${t.not_metered}</p>`}
let LC;
async function loadLearning(){const s=await (await fetch('/api/learning')).json();const m=s.months;
 $('hs3').textContent=`${m[0].automated_pct}% → ${m[1].automated_pct}% → ${m[2].automated_pct}% projected`;
 const d={labels:m.map(x=>x.month),datasets:[{data:m.map(x=>x.automated_pct),backgroundColor:['#cbd5e1','#0f766e','#86efac'],borderRadius:8}]};
 if(LC){LC.data=d;LC.update()}else LC=new Chart($('lchart'),{type:'bar',data:d,options:{maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{min:80,max:100},x:{grid:{display:false}}}}});
 $('l-tab').innerHTML=tbl(['Month','>Automated','>Human touches'],m.map(x=>`<tr><td>${x.month}</td><td class="n">${x.automated_pct}%</td><td class="n">${x.human} of ${x.total}</td></tr>`));
 $('l-rules').innerHTML=`<h4 style="margin-top:0">Learned from ${s.decisions} decisions</h4>`+(s.learned.map(r=>`<div class="claim"><span class="vb ${r.kind=='rule'?'vy':'vn'}">${r.kind}</span><b>${r.source}</b> <span class="hint">removes ${r.saves} human touch${r.saves==1?'':'es'} next month</span><div>${r.text}</div></div>`).join('')||'<p class="hint">Approve or reject the drafts in chapter 4 to teach Divi.</p>')}
async function decide2(b,flag,d){await fetch('/api/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({flag,decision:d})});
 const no=d=='reject'||d=='block';b.parentNode.innerHTML=`<span class="${no?'no':'ok'}">✔ ${d=='block'?'Blocked':no?'Rejected':'Approved'}. Not sent.</span>`;loadLearning()}
// rail highlight
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){document.querySelectorAll('.rail a').forEach(a=>a.classList.toggle('on',a.dataset.c==e.target.id))}}),{rootMargin:'-40% 0px -55% 0px'});
document.querySelectorAll('.ch').forEach(s=>io.observe(s));
story();

// ---- maximum build: scoreboard, click-to-source, reset, vision, FX, long context, tool calls, audit, ROI ----
document.addEventListener('click',e=>{const n=e.target.closest('.clk');if(!n)return;
 if(n.dataset.ref)cite(encodeURIComponent(n.dataset.ref));
 else if(n.dataset.open){const d=document.querySelector('#'+n.dataset.open+' details.proof');d.open=true;d.scrollIntoView({behavior:'smooth',block:'start'})}});
async function resetDemo(){await fetch('/api/reset',{method:'POST'});location.href=location.pathname+location.search}
async function score(){const s=await (await fetch('/api/scoreboard')).json();
 const t=(v,l,ref,open)=>`<div class="sc clk" ${ref?`data-ref="${ref}"`:`data-open="${open}"`}><b>${v}</b><span>${l}</span></div>`;
 $('score').innerHTML=t(s.hours_saved+' h','hours saved per close (est.)',null,'ch1')+t((s.automation*100).toFixed(1)+'%','handled without a human',null,'ch1')+
  t(s.fraud_caught,'planted anomalies caught',null,'ch3')+t(K(s.aed_found),'cash found for the tightest week',null,'ch4')+t(A(s.cost_per_close),'AI cost per close',null,'ch1')}
async function maxDepth(){let M;try{M=await (await fetch('/api/max')).json()}catch(e){return}
 const v=M.vision,fx=M.fx,lc=M.long_context,tc=M.tool_calls;
 $('hs6').textContent=`${v.crumpled.map(x=>x.matched+'/'+x.of).join(' and ')} fields on crumpled Arabic receipts · SAM 3.1 phone-photo cut-out`;
 $('h-vision').innerHTML=`<div class="grid">${v.crumpled.map(x=>`<div class="s4"><img class="vimg" src="/${x.file.replace('vision/','vision/')}"><div class="hint">${x.source}, crumpled and rotated: <b>${x.matched}/${x.of}</b> fields read correctly (${x.lang})</div></div>`).join('')}
  <div class="s4"><img class="vimg" src="/${v.grounding.file}"><div class="hint">Vision grounding: Muse returned a box for each field it read. Boxes are approximate.</div></div></div>`;
 $('hs7').textContent=`${fx.items.length} USD and EUR balances · net ${fx.net_gain_loss>=0?'gain':'loss'} ${A(Math.abs(fx.net_gain_loss))}`;
 $('h-fx').innerHTML=tbl(['Item','Currency','>Amount','>Booked rate','>31 Oct rate','>Gain or loss AED'],fx.items.map(x=>`<tr><td>${x.party}<div class="hint">${x.kind}, ${x.ref}</div></td><td>${x.currency}</td><td class="n">${f(x.amount_fc)}</td><td class="n">${x.booked_rate}</td><td class="n">${x.closing_rate}</td><td class="n ${x.gain_loss<0?'no':'ok'}">${A(x.gain_loss)}</td></tr>`))+
  `<h4>Revaluation entry ${fx.entry.je}</h4>${tbl(['Account','>Debit','>Credit'],fx.entry.lines.map(l=>`<tr><td>${l.account}</td><td class="n">${l.debit?A(l.debit):''}</td><td class="n">${l.credit?A(l.credit):''}</td></tr>`))}<p class="hint">${fx.entry.memo}. ${fx.rates.note}</p>`;
 $('hs8').textContent=`${lc.tokens_in.toLocaleString()} tokens in one review · ${lc.grounded}/${lc.findings.length} findings grounded · ${tc.length} native tool calls`;
 $('h-lc').innerHTML=`<p class="hint">The Controller read the whole month (invoices, bank, journals, vendors, aging) in one Muse call. Each cited row was then looked up in the source files.</p>
  <div id="lcf">${tbl(['Finding','>AED','Sources'],topN(lc.findings.map(x=>`<tr><td><b>${x.title}</b><div class="hint">${x.why}</div></td><td class="n">${x.amount_aed?f(x.amount_aed):''}</td><td>${x.refs_checked.map(r=>`<span class="cite" onclick="cite('${encodeURIComponent(r.ref)}')">${r.found?'✔':'✖'} ${r.ref.split('#')[1]}</span>`).join(' ')}</td></tr>`),3))}<button class="btn ghost sm" onclick="showMore('lcf',this)">Show all ${lc.findings.length}</button></div>
  <h4>Native tool calling (Responses API tools)</h4>${tbl(['Question','Tool Muse chose','Result'],tc.map(q=>`<tr><td>${q.question}</td><td>${q.calls.map(c=>`<code>${c.name}(${Object.values(c.arguments).join(', ')})</code>`).join('<br>')}</td><td>${q.calls.map(c=>c.result.aed!=null?A(c.result.aed)+(c.result.week?' in week '+c.result.week:''):(c.result.row?'invoice row found':'')).join('<br>')}</td></tr>`))}
  <h4>Calls in this layer</h4>${tbl(['Purpose','Mode','>Tokens in','>Out','>AED'],M.trace.map(c=>`<tr><td>${c.purpose}</td><td>${c.mode||''}</td><td class="n">${c.tokens_in.toLocaleString()}</td><td class="n">${c.tokens_out.toLocaleString()}</td><td class="n">${c.cost_aed.toFixed(4)}</td></tr>`))}`;
 const I2=await (await fetch('/api/insights')).json(),t=I2.trace,extra=M.trace.reduce((s,c)=>s+c.cost_aed,0),review=2*t.accountant.rate_aed,divi=t.cost_aed+review,man=t.accountant_cost_aed;
 const R0=n=>'AED '+f(n);$('hs10').textContent=`about ${R0(divi)} vs ${R0(man)} a close (estimate)`;
 $('h-roi').innerHTML=`<div class="mini"><div><b>${R0(man)}</b><span>manual close: ${t.accountant.hours} h at AED ${t.accountant.rate_aed} (assumption)</span></div><div><b>${R0(divi)}</b><span>Divi: ${A(t.cost_aed)} AI cost plus 2 h human review (assumption)</span></div><div><b>${R0((man-divi)*12)}</b><span>saved a year at 12 closes (estimate)</span></div></div>
  <p class="hint">Estimate only. AI cost is measured from the token trace; the depth layer above adds ${A(extra)} once. Hourly rate, manual hours and review time are assumptions, not measurements. Hosting is not included.</p>`;
 const au=await (await fetch('/api/audit')).json();$('hs9').textContent=`${au.events.length} agent actions · ${au.decisions.length} human decisions`;
 $('h-audit').innerHTML=`<div id="aud1">${tbl(['Time (IST)','Agent','Action','Detail'],topN(au.events.map(e=>`<tr><td class="n">${e.t!=null?new Date(e.t*1000).toLocaleTimeString('en-GB',{timeZone:'Asia/Kolkata'}):''}</td><td>${e.agent||''}</td><td>${(e.kind||'').replace('_',' ')}</td><td>${(e.text||'').slice(0,140)}</td></tr>`),3))}<button class="btn ghost sm" onclick="showMore('aud1',this)">Show all ${au.events.length}</button></div>
  <h4>Human decisions</h4>${au.decisions.length?tbl(['Time','Item','Decision'],au.decisions.map(d=>`<tr><td>${d.time||''}</td><td>${d.flag}</td><td>${d.decision.replaceAll('_',' ')}</td></tr>`)):'<p class="hint">No approvals yet. Approve or reject a draft or escalation and it appears here with its time.</p>'}`}
score();maxDepth();

// ---- edge: owner controls, alerts, covenant check, debate scorecard, receipts, router ----
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function edgeLoad(){let E;try{E=await (await fetch('/api/edge')).json()}catch(e){return}
 renderRules(E);
 const L=E.loan,liq=L.covenants.find(c=>c.metric=='min_weekly_cash_aed'),bt=liq&&liq.tests.find(t=>t.scenario=='base');
 $('hs12').textContent=liq?`${liq.name} clause ${liq.clause}, page ${liq.page}: ${bt.ok?'met':'breach in week '+bt.breach_weeks.join(' and ')} on the base forecast`:'';
 $('h-loan').innerHTML=`<p class="hint">Muse read all ${L.pages} pages (${L.words.toLocaleString()} words) of a fictional facility agreement in one call, listed every covenant with its page and clause, and Divi tested each against the 13-week forecast. Quotes were checked against the cited page. <a class="p" href="/loan/facility_agreement.pdf" target="_blank">Open the PDF</a></p>`+
  L.covenants.map(c=>`<div class="claim"><span class="vb ${c.grounded?'vy':'vn'}">${c.grounded?'quote found on page '+c.page:'quote not found'}</span><b>${esc(c.name)}</b>, clause ${esc(c.clause)}, <span class="cite" onclick="cite('${encodeURIComponent('loan#'+c.page)}')">page ${c.page}</span><div class="hint">"${esc(c.quote)}"</div>
   ${tbl(['Scenario','>Lowest cash','>Headroom','Result'],c.tests.map(t=>t.ok==null?`<tr><td colspan="4">${t.scenario}. ${t.note}</td></tr>`:`<tr><td><span class="cite" onclick="cite('${encodeURIComponent(t.ref)}')">${t.scenario}</span></td><td class="n">${A(t.lowest)} (week ${t.week})</td><td class="n ${t.headroom<0?'no':'ok'}">${A(t.headroom)}</td><td>${t.ok?'<span class="ok">Met</span>':'<span class="no">Breach, weeks '+(t.breach_weeks.length>4?t.breach_weeks[0]+' to '+t.breach_weeks.at(-1):t.breach_weeks.join(', '))+'</span>'}</td></tr>`))}
   ${c.cure?`<div class="hint">Cure right: ${esc(typeof c.cure=='object'?(c.cure.clause+', '+(c.cure.description||'')):c.cure)}</div>`:''}</div>`).join('')+
  (bt&&!bt.ok?`<div class="claim"><b>What Divi recommends</b><div>The base forecast dips ${A(-bt.headroom)} under the AED 250,000 minimum in week ${bt.week}. Running the cash levers in chapter 4 keeps every week above it, so no covenant breach and no equity cure is needed.</div></div>`:'');
 const D2=E.debate||[];$('hs13').textContent=`${D2.length} rounds · Red Team won ${D2.filter(d=>d.winner=='redteam').length}, Controller won ${D2.filter(d=>d.winner=='controller').length}`;
 $('h-debate').innerHTML=tbl(['Flag','Red Team','Controller','Winner and evidence'],D2.map(d=>`<tr><td><b>${esc(d.flag).replaceAll('_',' ')}</b></td><td>${esc(d.redteam)}<div class="hint">score ${d.score_redteam}/10</div></td><td>${esc(d.controller)}<div class="hint">score ${d.score_controller}/10</div></td><td><b class="${d.winner=='redteam'?'no':'ok'}">${d.winner=='redteam'?'Red Team':'Controller'}</b> <span class="cite" onclick="cite('${encodeURIComponent(d.winning_evidence)}')">${d.grounded?'✔':'✖'} ${esc(String(d.winning_evidence).split('#')[1]||d.winning_evidence)}</span><div class="hint">${esc(d.why)}</div>${(d.date_checks||[]).map(c=>`<div class="why"><span class="vb vn">Verifier corrected</span> model wrote <s>${esc(c.original)}</s> ${esc(c.errors.join('; '))}</div>`).join('')}</td></tr>`))+((D2.some(d=>(d.date_checks||[]).length))?'<p class="hint">Every date in debate text is checked: the Verifier computes the weekday from the cited row and corrects the model when it is wrong.</p>':'');
 const R=E.receipts||[];$('hs14').textContent=`${R.length} card spends with no receipt · WhatsApp drafts, not sent`;
 $('h-rcpt').innerHTML=`<p class="hint">Card spends booked to General Expenses with no receipt on file. Copy a message into WhatsApp yourself; Divi sends nothing.</p>`+R.map((r,i)=>`<div class="claim"><b>${A(r.amount)}</b> ${esc(r.payee)} on ${r.date} <span class="cite" onclick="cite('${encodeURIComponent(r.ref)}')">${r.bank_id}</span><div id="wa${i}">${esc(r.whatsapp)}</div><button class="btn ghost sm" onclick="navigator.clipboard.writeText($('wa${i}').textContent);this.textContent='Copied'">Copy text</button></div>`).join('');
 const Rt=E.router;$('hs15').textContent=`${Rt.steps.length} steps · ${Rt.total_tokens.toLocaleString()} tokens · ${A(Rt.total_aed)} recorded`;
 $('h-router').innerHTML=`<p class="hint">Which model handled each step and why. Maths stays in plain code so the numbers are exact and free.</p>`+tbl(['Step','Model','Why this model','>Calls','>Tokens','>AED'],Rt.steps.map(s=>`<tr><td>${esc(s.step).replaceAll('_',' ')}</td><td style="white-space:nowrap"><code>${s.model}</code></td><td>${s.why}</td><td class="n">${s.calls}</td><td class="n">${(s.tokens_in+s.tokens_out).toLocaleString()}</td><td class="n">${s.cost_aed.toFixed(4)}</td></tr>`));
 const B=E.leaderboard||[];$('h-board').innerHTML=B.length?tbl(['Player','>Rows','>AED','Result'],B.slice(0,5).map(b=>`<tr><td>${esc(b.name)}</td><td class="n">${b.rows}</td><td class="n">${A(b.amount)}</td><td>${b.won?'<span class="no">Slipped past</span>':'<span class="ok">Caught</span>'}</td></tr>`)):''}
function renderRules(E){const rs=E.rules||[],al=E.alerts||[];
 $('hs11').textContent=`${rs.length} owner rule${rs.length==1?'':'s'} · ${al.length} alerts waiting`;
 $('h-rules').innerHTML=`<p class="hint">Type a control in plain English. Muse turns it into a rule (data, not code), Divi checks it against known fields, runs it now and on every close.</p>
  <div class="row"><input type="text" id="rin" placeholder="flag any payment over AED 20k to a vendor added this month"><button class="btn" onclick="addRule()">Add control</button></div><div id="rout"></div>
  ${rs.map(r=>`<div class="claim"><span class="vb vy">${r.compiled_by=='Muse Spark'?'compiled by Muse':'fallback parser'}</span><b>${esc(r.plain||r.text)}</b><pre class="rule">${esc(JSON.stringify({source:r.source,conditions:r.conditions,severity:r.severity},null,1))}</pre></div>`).join('')}
  <h4>Control alerts</h4><div class="grid">${al.slice(0,6).map(a=>`<div class="card s6 alert"><div class="ctitle">${esc(a.title)}</div><div>${esc(a.text)}</div><div class="hint"><span class="cite" onclick="cite('${encodeURIComponent(a.ref)}')">${esc(a.ref.split('#')[1]||a.ref)}</span></div><div class="row"><button class="btn sm" onclick="decide2(this,'${esc(a.id)}','approve')">Approve</button><button class="btn ghost sm" onclick="decide2(this,'${esc(a.id)}','block')">Block</button></div></div>`).join('')}</div>`}
async function addRule(){const t=$('rin').value||$('rin').placeholder;$('rout').innerHTML='<p class="hint">Muse is writing the rule...</p>';
 const r=await (await fetch('/api/rules',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})})).json();
 if(r.error){$('rout').innerHTML=`<p class="no">${r.error}</p>`;return}
 const E=await (await fetch('/api/edge')).json();renderRules(E);
 $('rout').innerHTML=`<p class="ok">Rule added. ${r.hits.length} match${r.hits.length==1?'':'es'} in October: ${r.hits.map(h=>`<span class="cite" onclick="cite('${encodeURIComponent(h.ref)}')">${h.id} ${A(h.amount)}</span>`).join(' ')||'none'}</p>`}
edgeLoad();
fetch('/api/edge').then(r=>r.json()).then(E=>{const g=E.cogs;if(!g)return;$('hs17').textContent=`under-booked ${A(g.gap)} vs the stock count`;
 $('h-cogs').innerHTML=`<p class="hint">${g.note} JE-1040 booked ${(g.booked_ratio*100).toFixed(1)}% of sales as cost. Divi rebuilt it from the stock roll-forward and the 31 Oct stock count.</p>
 ${tbl(['Stock roll-forward','>AED'],[['Opening stock',g.opening_stock],['Add October purchases',g.purchases],['Less counted stock at 31 Oct',-g.counted_stock],['Cost of sales from the count',g.cogs_from_count],['Booked in JE-1040',g.booked],['Under-booked',g.gap]].map(r=>`<tr><td>${r[0]}</td><td class="n">${A(r[1])}</td></tr>`))}
 <p class="hint">Gross margin falls from ${(g.gross_margin_booked*100).toFixed(1)}% to ${(g.gross_margin_count*100).toFixed(1)}%. Sources: ${g.proof.map(p=>`<span class="cite" onclick="cite('${encodeURIComponent(p)}')">${p}</span>`).join(' ')}</p>
 <div class="claim"><b>Proposed adjustment</b>: Debit ${g.proposal.debit}, Credit ${g.proposal.credit}, ${A(g.proposal.amount)}. Not posted.<div class="acts"><button class="btn sm" onclick="decide2(this,'cogs_true_up_JE-1040','approve_draft')">Approve</button><button class="btn ghost sm" onclick="decide2(this,'cogs_true_up_JE-1040','reject')">Reject</button></div></div>`});
fetch('/api/extras').then(r=>r.json()).then(X=>{const s=X.sam,t=X.tax,e=X.exports;
 if(s&&!s.error)$('h-sam').innerHTML=`<h4>Phone photo to ledger: SAM 3.1 cut-out, then Muse reads</h4><div class="grid">
  <div class="s4"><img class="vimg" src="/media/sam/photo_with_sam_box.png"><div class="hint">1. SAM 3.1 finds the "${s.concept}" on a cluttered desk photo and returns its box and mask.</div></div>
  <div class="s4"><img class="vimg" src="/media/sam/receipt_cutout.png" style="max-height:260px;object-fit:contain"><div class="hint">2. Divi crops to the box, so Muse only sees the receipt.</div></div>
  <div class="s4"><img class="vimg" src="/media/sam/receipt_fields_boxed.png"><div class="hint">3. Muse reads <b>${s.matched}/${s.of}</b> fields correctly and boxes where each was printed (boxes approximate).</div></div></div><p class="hint">${s.note}</p>`;
 if(t&&!t.error){$('h-taxweb').innerHTML=`<h4>Live check of UAE tax rules (Muse web search)</h4><p class="hint">The Treasurer searched official sources and compared them with the rates Divi uses. ${t.searches.length} searches and page opens.</p>`+
  tbl(['Rule','>Divi uses','>Official source says','Result'],t.checks.map(c=>`<tr><td>${c.rule}</td><td class="n">${f(c.divi_uses)}</td><td class="n">${c.web_says==null?'not found':f(c.web_says)}</td><td>${c.agrees?'<span class="ok">Agrees</span>':'<span class="no">Check</span>'}</td></tr>`))+
  `<div class="hint">${t.sources.map(x=>`<div><a class="p" href="${x.url}" target="_blank" rel="noopener">${x.url.replace(/^https?:\/\//,'').split('/')[0]}</a> ${esc(x.supports||'')}</div>`).join('')}</div>`}
 if(e&&!e.error){$('hs16').textContent=`${e.journals} journals ready as CSV`;$('h-exp').innerHTML=`<p class="hint">${e.note} Files only; nothing is uploaded.</p><div class="row">${e.files.map(x=>`<a class="btn ghost sm" href="/media/${x}" download>${x.split('/')[1]}</a>`).join('')}</div>`}});
function toggleMode(force){const on=force!=null?force:!document.body.classList.contains('owner');document.body.classList.toggle('owner',on);
 localStorage.setItem('divi_mode',on?'owner':'accountant');$('modebtn').textContent=on?'🧮 Accountant mode':'👤 Owner mode'}
toggleMode(localStorage.getItem('divi_mode')=='owner');
// group summaries: one line and a key number per group
function groupSum(){const t=id=>($(id)&&$(id).textContent)||'';
 const set=(g,v)=>{if(v)$(g).textContent=v};
 set('g1',[t('hs15').split(' · ').slice(-1)[0],'covenant '+(t('hs12').includes('breach')?'breach found on page 57':'checked'),'SAM 3.1, Muse Image, web search'].filter(Boolean).join(' · '));
 set('g2',[t('hs11').split(' · ')[1],t('hs13').split(' · ')[0]&&'debate '+t('hs13').split(' · ')[1],'Beat the Controller'].filter(Boolean).join(' · '));
 set('g3',t('hs1')+' · rates checked live');
 set('g4',[t('hs17'),t('hs16')].filter(Boolean).join(' · '));
 set('g5',t('hs10'))}
[1500,3500,7000].forEach(ms=>setTimeout(groupSum,ms));
// Keep the side menu flush under the top bar, whatever its height.
(()=>{const f=()=>{const h=document.querySelector('.top');if(h)document.documentElement.style.setProperty('--toph',h.offsetHeight+'px')};f();addEventListener('resize',f)})();

async function voice4(){const b=$('v4');b.disabled=true;try{const au=new Audio('/audio/q_week4.mp3');au.play().catch(()=>{});addMsg('a sub','listening...');
 const r=await (await fetch('/api/voice_week4')).json();await new Promise(x=>setTimeout(x,1600));$('chat').lastChild.remove();addMsg('q','🎤 '+(r.transcript||r.question));addMsg('a',ansHtml(r))}finally{b.disabled=false}}

async function undecide(flag){await fetch('/api/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({flag,decision:'pending'})});
 document.querySelectorAll('.appr').forEach(x=>{if(x.innerHTML.includes("undecide('"+flag+"')"))x.innerHTML=`<button class="btn sm" onclick="decide(this,'large_payment_to_new_vendor','block')">⛔ Block payment</button><button class="btn ghost sm" onclick="decide(this,'large_payment_to_new_vendor','release')">Release payment</button>`});if(window.auditRefreshQ5)auditRefreshQ5()}
