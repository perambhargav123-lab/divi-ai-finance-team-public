(async function(){
 const f=n=>n==null?'Chapter 6':'AED '+Math.round(n).toLocaleString('en-US');
 const r=await (await fetch('/api/cycle')).json();
 const sub={p2p:'held',o2c:'to collect',treasury:'payment run',r2r:'profit before audit',audit:'then'};
 document.getElementById('cstrip').innerHTML=r.strip.map(s=>`<div class="cstep"><b>${s.name}</b><div class="cv">${f(s.value)}</div><span>${sub[s.id]}: ${s.line}</span></div>`).join('');
 const T=(h,rows)=>`<table class="cyt"><tr>${h.map(x=>`<th>${x}</th>`).join('')}</tr>${rows.map(r=>`<tr>${r.map(x=>`<td>${x}</td>`).join('')}</tr>`).join('')}</table>`;
 const pr=r.payment_run, c=r.collections, k=r.close;
 document.getElementById('cycd').innerHTML=
  '<b>Three-way match (invoice, purchase order, goods received)</b>'+T(['Bill','Vendor','PO','GRN','Result'],r.three_way.filter(x=>!x.match).map(x=>[x.invoice,x.vendor,x.po,x.grn,x.issues.join('; ')+' · hold '+f(x.held_with_vat)]))+
  `<div class="hint">${r.three_way.filter(x=>x.match).length} other bills match all three.</div>`+
  '<b>Vendor onboarding check</b>'+T(['Vendor','Flags'],r.vendors.filter(v=>!v.ok).map(v=>[v.vendor,v.flags.join('; ')]))+
  `<b>Payment run proposal, ${pr.window} (${pr.status})</b>`+T(['Bill','Vendor','Due','Amount','Action'],[...pr.pay.map(x=>[x.invoice,x.vendor,x.due,f(x.amount),'pay']),...pr.hold.map(x=>[x.invoice,x.vendor,x.due,f(x.amount),'hold: '+x.why]),...pr.defer.map(x=>[x.invoice,x.vendor,x.due,f(x.amount),'defer: '+x.why])])+
  `<div class="hint">Pay ${f(pr.pay_total)}, hold ${f(pr.hold_total)}, defer ${f(pr.defer_total)}. Lowest week ${r.runway.lowest_week}: ${f(r.runway.lowest_cash)}, ${f(r.runway.headroom)} above one payroll.</div>`+
  '<b>Collections, ranked (drafts, not sent)</b>'+T(['#','Customer','Overdue','English','العربية'],c.rows.map(x=>[x.rank,x.customer,f(x.overdue)+' · '+x.bucket_days+' days'+(x.disputed?'<br>chase '+f(x.chase)+', disputed '+f(x.disputed)+' set aside':''),x.draft_en,`<div class="ar">${x.draft_ar}</div>`]))+
  '<b>Close checklist</b>'+T(['Step','Done'],k.steps.map(s=>[s.step,s.done?'yes':'open']))+T(['Entry','Accrual or prepayment','AED'],k.accruals.map(a=>[a.entry,a.memo,f(a.amount)]));
})();
function hideStart(){document.getElementById('starthere').style.display='none';try{localStorage.setItem('divi_start_hidden','1')}catch(e){}}
try{if(localStorage.getItem('divi_start_hidden')=='1')document.getElementById('starthere').style.display='none'}catch(e){}
async function showSummary(){
 const [cc,au]=await Promise.all([fetch('/api/cash_counter').then(r=>r.json()),fetch('/api/auditor').then(r=>r.json())]);
 const t=id=>(document.getElementById(id)||{}).textContent||'';
 const box=document.getElementById('wjh');
 box.innerHTML=`<section class="ch" style="padding-top:8px;padding-bottom:0"><div class="card wjh" id="wjhcard"><div class="eyebrow">What just happened</div>
 <h3 style="margin:6px 0 0">Five agents closed October for Falcon Trading LLC. Here is what they found. Click any box to see the detail.</h3>
 <div class="grid4">
 <a href="#ch4"><b>AED ${Math.round(cc.total).toLocaleString('en-US')}</b><span>cash found: recovered, protected and brought in sooner</span></a>
 <a href="#ch4"><b>${t('k4a')} to ${t('k4b')}</b><span>chance of running out of cash in the next 13 weeks, after the actions</span></a>
 <a href="#ch3"><b>AED 50,000</b><span>payment to a new vendor held for your decision, plus a hidden AED 18,500 sale found</span></a>
 <a href="#ch6"><b>${au.adjusted} adjustments</b><span>the independent auditor's changes before it signs. Press Send to the auditor</span></a>
 </div></div></section>`;
 box.scrollIntoView({behavior:'smooth',block:'start'});
}
