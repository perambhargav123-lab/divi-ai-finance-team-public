// Cash counter (header pill + chapter 4 card) and the auditor loop (chapter 6)
const KA=n=>'AED '+Math.round(n).toLocaleString('en-US');
const _anim=new WeakMap();
function countUp(el,to,ms=1400){const id={};_anim.set(el,id);const t0=performance.now();const step=t=>{if(_anim.get(el)!==id)return;const k=Math.min(1,(t-t0)/ms);el.textContent=KA(k>=1?to:to*(1-Math.pow(1-k,3)));if(k<1)requestAnimationFrame(step)};requestAnimationFrame(step)}
function setNow(el,v){_anim.set(el,{});el.textContent=KA(v)}
let CASH=null,_cashIO=null,_cashShown=false;
// Headline is always the sum of the rounded parts shown on screen, from one fetch.
async function cashLoad(){CASH=await (await fetch('/api/cash_counter?t='+Date.now(),{cache:'no-store'})).json();const t=CASH.totals;
 const parts=['recovered','protected','released'].map(k=>[k,Math.round(t[k])]);CASH.shown=parts.reduce((a,[,v])=>a+v,0);
 $('cashsplit').innerHTML=parts.map(([k,v])=>`<div><b>${KA(v)}</b><span>${k}</span></div>`).join('');
 if(_cashIO)_cashIO.disconnect();
 const go=()=>{_cashShown=true;if(_tick&&_tick.sum){setNow($('cashbig'),CASH.shown);setNow($('cashtop'),CASH.shown);return}countUp($('cashbig'),CASH.shown);countUp($('cashtop'),CASH.shown)};
 _cashIO=new IntersectionObserver(es=>{if(es.some(e=>e.isIntersecting)){go();_cashIO.disconnect()}});_cashIO.observe($('cashbig'))}
// Called when a close starts: clear the old figures so nothing stale shows during the run.
function cashReset(){_cashShown=false;if(_cashIO)_cashIO.disconnect();setNow($('cashbig'),0);setNow($('cashtop'),0);$('cashsplit').innerHTML='';const b=$('cashlines');if(b)b.style.display='none'}
function showCash(){const b=$('cashlines');if(!CASH)return;b.style.display=b.style.display=='none'?'block':'none';
 b.innerHTML=`<table><tr><th>What</th><th>Type</th><th class="n">AED</th><th>Source</th></tr>${CASH.lines.map(l=>`<tr><td>${l.label}</td><td>${l.kind}</td><td class="n">${A(l.amount)}</td><td><span class="cite" onclick="cite('${encodeURIComponent(l.ref)}')">${l.ref}</span></td></tr>`).join('')}</table><p class="hint">${CASH.note}</p>`}
const ST={adjusted:['Adjusted','tag red'],cleared:['Cleared','tag teal'],'control point':['Control point','tag amber']};
async function auditLoop(){const go=$('a6go');go.disabled=true;go.textContent='Auditing...';$('stamp').style.display='none';
 const R=await (await fetch('/api/auditor')).json();const box=$('a6q');box.innerHTML='';$('a6n').textContent='0';
 for(const [i,q] of R.queries.entries()){await new Promise(r=>setTimeout(r,i?900:200));const d=document.createElement('div');d.className='card aq';
  d.innerHTML=`<div class="hl"><span class="${ST[q.status][1]}">${ST[q.status][0]}</span><div style="flex:1"><div class="who" style="color:#7c3aed">Auditor · ${q.area}</div><h3>${q.ask}</h3>${q.policy?`<span class="tag teal" title="${q.policy.rule}">Policy ${q.policy.id}: ${q.policy.title}</span>`:''}
   <p class="qa"><b style="color:var(--teal)">Divi:</b> ${q.divi}</p>
   <details><summary class="hint" style="cursor:pointer">Re-performed in code</summary><pre>${q.reperform}</pre>${q.adjustment?`<p class="hint">Entry: ${q.adjustment}</p>`:''}<div>${q.cites.map(c=>`<span class="cite" onclick="cite('${encodeURIComponent(c)}')">${c}</span>`).join('')}</div></details></div>
   ${q.difference?`<div class="amt">${KA(q.difference)}</div>`:''}</div>`;
  box.appendChild(d);$('a6n').textContent=i+1}
 $('a6s').textContent=`${R.adjusted} adjusted · ${R.cleared} cleared · ${R.controls} control points`;
 const st=$('stamp');st.innerHTML=`✓ ${R.opinion}<small>${R.cert_id} · net profit ${KA(R.net_profit_before)} → ${KA(R.net_profit_after)}</small>`;st.style.display='block';
 go.disabled=false;go.textContent='Run the audit again';dlogLoad();
 const M=R.materiality;$('p6').innerHTML=`<h4>Materiality</h4><p>${M.basis}: ${A(M.overall)}. Performance ${A(M.performance)}. Clearly trivial ${A(M.trivial)}.</p>
  <h4>Sign-off letter (Muse)</h4><p>${R.letter}</p><h4>Independence</h4><p class="hint">${R.independence}</p>${R.models?`<p class="hint">Preparer: ${R.models.preparer} · Auditor: ${R.models.auditor}</p>`:""}<h4>Evidence fingerprint</h4><code>sha256 ${R.signature}</code>`}
cashLoad();
// Live tick: during Run the close, the pill climbs as each chapter finds a cash line (30 Oct polish).
let _tick=null;
async function cashTickStart(){_tick={got:new Set(),sum:0,lines:CASH&&CASH.lines};if(_tick.lines)return;try{const c=await (await fetch('/api/cash_counter?t='+Date.now(),{cache:'no-store'})).json();_tick.lines=c.lines}catch(e){}}
function cashTick(e){if(!_tick||!_tick.lines||!e)return;const s=JSON.stringify(e);let add=0;
 for(const l of _tick.lines){if(_tick.got.has(l.ref))continue;const id=l.ref.split('#')[1];
  const hit=e.kind=='cashcheck'||e.kind=='done'||(l.ref.startsWith('treasury')?e.kind=='forecast':['flag','fraud','approval'].includes(e.kind)&&s.includes(id));
  if(hit){_tick.got.add(l.ref);add+=Math.round(l.amount)}}
 if(!add)return;const from=_tick.sum;_tick.sum+=add;
 for(const el of [$('cashtop'),$('cashbig')]){const id={};_anim.set(el,id);const t0=performance.now(),to=_tick.sum;
  const st=t=>{if(_anim.get(el)!==id)return;const k=Math.min(1,(t-t0)/900);el.textContent=KA(from+(to-from)*(1-Math.pow(1-k,3)));if(k<1)requestAnimationFrame(st)};requestAnimationFrame(st)}
 const p=$('cashtop');if(p&&p.parentNode){p.parentNode.classList.add('bump');setTimeout(()=>p.parentNode.classList.remove('bump'),700)}}
// Auditor Q5 follows the owner's decision on the Quickline payment (B108) without a rerun.
async function auditRefreshQ5(){if(window.cashLoad)cashLoad();if($('dlogt').dataset.on)dlogLoad();const box=$('a6q');if(!box||!box.children.length)return;const R=await (await fetch('/api/auditor?t='+Date.now(),{cache:'no-store'})).json();
 const i=R.queries.findIndex(q=>q.id=='Q5');const card=box.children[i];if(card){const qa=card.querySelector('.qa');if(qa){qa.innerHTML=`<b style="color:var(--teal)">Divi:</b> ${R.queries[i].divi}`;card.style.animation='in .5s'}}
 const st=$('stamp');if(st&&st.style.display!='none')st.innerHTML=`✓ ${R.opinion}<small>${R.cert_id} · net profit ${KA(R.net_profit_before)} → ${KA(R.net_profit_after)}</small>`}

async function dlogLoad(){const L=await (await fetch('/api/decision_log?t='+Date.now(),{cache:'no-store'})).json();const el=$('dlogt');el.dataset.on=1;el.className='';
 el.innerHTML=`<table><tr><th>Exception</th><th>Policy</th><th>Decided by</th><th>Decision</th><th>Next month</th><th>Evidence</th></tr>${L.rows.map(r=>`<tr><td>${r.label}<br><span class="hint">${r.items.join(', ')}</span></td><td><span class="tag teal" title="${r.policy?r.policy.rule:''}">${r.policy?r.policy.id+' '+r.policy.title:'-'}</span></td><td>${r.decided_by||'<span class="hint">waiting</span>'}${r.when?'<br><span class="hint">'+r.when+'</span>':''}</td><td>${r.decision}</td><td class="hint">${r.next_month}</td><td>${r.evidence.slice(0,2).map(c=>`<span class="cite" onclick="cite('${encodeURIComponent(c)}')">${c.split('#')[1]||c}</span>`).join('')}</td></tr>`).join('')}</table><p class="hint">${L.decided} decided, ${L.waiting} waiting for you. ${L.note}</p>`}

(async()=>{try{const P=await (await fetch('/api/policy')).json();$('polt').innerHTML=`<table><tr><th>ID</th><th>Policy</th><th>Rule</th><th>Auditor queries</th></tr>${P.policies.map(x=>`<tr><td><span class="tag teal">${x.id}</span></td><td><b>${x.title}</b></td><td>${x.rule}</td><td class="hint">${x.auditor.join(', ')}</td></tr>`).join('')}</table><p class="hint">${P.company} · version ${P.version}</p>`}catch(e){}})();
