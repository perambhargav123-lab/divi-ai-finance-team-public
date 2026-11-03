"""Generate fictional October 2026 data for Falcon Trading LLC (Dubai). Seeded, reproducible."""
import csv, json, random
from datetime import date, timedelta
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

R = random.Random(2026)
D = Path(__file__).resolve().parent.parent / "data"; D.mkdir(exist_ok=True)
(D / "docs").mkdir(exist_ok=True)
OCT = [date(2026, 10, d) for d in range(1, 32)]
def w(name, rows):
    with open(D / name, "w", newline="", encoding="utf-8") as f:
        c = csv.DictWriter(f, fieldnames=list(rows[0])); c.writeheader(); c.writerows(rows)

coa = [("1000","Cash at Bank Emirates NBD","Asset"),("1100","Accounts Receivable","Asset"),("1200","Inventory","Asset"),
 ("1300","VAT Input Recoverable","Asset"),("1500","Fixed Assets","Asset"),("2000","Accounts Payable","Liability"),
 ("2100","VAT Output Payable","Liability"),("2200","Accrued Expenses","Liability"),("3000","Share Capital","Equity"),
 ("3100","Retained Earnings","Equity"),("4000","Sales","Income"),("5000","Cost of Goods Sold","Expense"),
 ("6000","Rent","Expense"),("6100","Salaries","Expense"),("6200","Bank Charges","Expense"),("6300","Utilities DEWA","Expense")]
w("chart_of_accounts.csv", [dict(code=a,name=b,type=c) for a,b,c in coa])
otb = {"1000":420000,"1100":610000,"1200":385000,"1300":0,"1500":150000,"2000":-455000,"2100":0,"2200":-40000,
       "3000":-300000,"3100":-770000}
w("opening_trial_balance.csv", [dict(code=k,balance_aed=v) for k,v in otb.items()])

customers = ["Al Noor Retail LLC","Gulf Star Supermarkets","Emirates Home Supplies","Desert Rose Trading","Marina Hypermarket",
             "Sharjah Wholesale Co","Oasis Hotels FZE","Blue Creek Catering"]
vendors = ["Jebel Ali Packaging LLC","Al Futtaim Logistics Demo","Zenith Electronics FZCO","Palm Foods Import","Horizon Office Supplies",
           "Sahara Freight Services","Coastline Plastics"]
def trn(): return "100" + "".join(str(R.randint(0,9)) for _ in range(12))
TRN = {n: trn() for n in customers + vendors + ["Quickline General Trading"]}

inv, ledger, bank = [], [], []
def add(kind, no, party, d, net, terms, status="paid", flag=""):
    vat = round(net*0.05, 2); tot = round(net+vat, 2); due = d + timedelta(days=terms)
    inv.append(dict(type=kind,invoice_no=no,party=party,trn=TRN[party],date=d.isoformat(),due=due.isoformat(),
                    net=net,vat=vat,total=tot,currency="AED",status=status,flag=flag)); return tot, due
for i in range(1, 86):  # sales
    d = R.choice(OCT); net = round(R.uniform(2000, 38000), 2)
    st = "paid" if R.random() < 0.55 else "open"
    tot, due = add("sale", f"FT-S-{i:04d}", R.choice(customers), d, net, 30, st)
    if st == "paid":
        pd = min(d + timedelta(days=R.randint(1, 10)), date(2026,10,31))
        ledger.append(dict(ref=f"FT-S-{i:04d}", date=pd.isoformat(), amount=tot))
        bank.append(dict(date=pd.isoformat(), description=f"INWARD TT {inv[-1]['party'].upper()} REF FT-S-{i:04d}", amount=tot))
for i in range(1, 64):  # purchases
    d = R.choice(OCT); net = round(R.uniform(1500, 30000), 2); v = R.choice(vendors)
    st = "paid" if R.random() < 0.6 else "open"
    tot, due = add("purchase", f"PI-{i:04d}", v, d, net, 45, st)
    if st == "paid":
        pd = min(d + timedelta(days=R.randint(0, 12)), date(2026,10,31))
        ledger.append(dict(ref=f"PI-{i:04d}", date=pd.isoformat(), amount=-tot))
        bank.append(dict(date=pd.isoformat(), description=f"OUTWARD PAYMENT {v.upper()}", amount=-tot))
# anomalies
dup = inv[90].copy(); dup.update(invoice_no=dup["invoice_no"]+"-A", flag="ANOMALY duplicate vendor invoice (same vendor, amount, date)"); inv.append(dup)
tot,_ = add("purchase","QGT-001","Quickline General Trading",date(2026,10,18),47619.05,0,"paid","ANOMALY round 50,000 payment to vendor created 16 Oct")
ledger.append(dict(ref="QGT-001",date="2026-10-18",amount=-tot)); bank.append(dict(date="2026-10-18",description="OUTWARD PAYMENT QUICKLINE GENERAL TRADING",amount=-tot))
paid_p = next(l for l in ledger if l["amount"] < 0)
bank.append(dict(date="2026-10-22", description=bank[[b["amount"] for b in bank].index(paid_p["amount"])]["description"]+" DUPLICATE", amount=paid_p["amount"]))
bank.append(dict(date="2026-10-27", description="INWARD TT DESERT ROSE TRADING NO REF", amount=18500.00))  # hidden sale
for d in [date(2026,10,1), date(2026,10,15), date(2026,10,31)]:
    bank.append(dict(date=d.isoformat(), description="BANK CHARGE TT FEES", amount=-R.choice([52.5,105.0,26.25])))
bank += [dict(date="2026-10-01",description="DIRECT DEBIT EJARI RENT OFFICE JLT",amount=-35000.0),
         dict(date="2026-10-28",description="WPS SALARY TRANSFER OCT",amount=-128400.0),
         dict(date="2026-10-12",description="DEWA DIRECT DEBIT",amount=-3180.4)]
ledger += [dict(ref="RENT-10",date="2026-10-01",amount=-35000.0),dict(ref="SAL-10",date="2026-10-28",amount=-128400.0),
           dict(ref="DEWA-10",date="2026-10-12",amount=-3180.4)]
# timing differences: cheques in ledger not yet cleared
for k,(amt,dd) in enumerate([(-12600.0,"2026-10-30"),(-8450.0,"2026-10-31"),(22300.0,"2026-10-31")]):
    ledger.append(dict(ref=f"CHQ-{k+1}",date=dd,amount=amt))
while len(bank) < 200:  # small card and POS lines with ledger entries
    d = R.choice(OCT); a = -round(R.uniform(40, 900), 2); ref = f"EXP-{len(bank):03d}"
    bank.append(dict(date=d.isoformat(), description=f"CARD PURCHASE {R.choice(['ENOC','ADNOC','CARREFOUR','DU TELECOM','NOON BUSINESS'])}", amount=a))
    ledger.append(dict(ref=ref, date=d.isoformat(), amount=a))
bank.sort(key=lambda b: b["date"])
for i,b in enumerate(bank,1): b["bank_id"] = f"B{i:03d}"
w("invoices.csv", inv); w("bank_statement.csv", [dict(bank_id=b["bank_id"],date=b["date"],description=b["description"],amount=b["amount"]) for b in bank])
w("ledger_cash.csv", ledger)
w("journals.csv", [dict(je="JE-1041",date="2026-10-24",weekday="Saturday",posted_by="intern.k (junior)",
                        debit="6000",credit="2200",amount=9750.0,memo="accrual adj",flag="ANOMALY weekend journal by junior, no approver"),
                   dict(je="JE-1040",date="2026-10-23",weekday="Friday",posted_by="fc.ahmed",debit="5000",credit="1200",amount=1190000.0,memo="COGS Oct, 72% margin method",flag="")])
# AR aging with overdue set (legacy September invoices)
ar = [dict(customer=c, current=round(R.uniform(20000,60000),2), d31_60=0, d61_90=0, d90_plus=0) for c in customers]
overdue = [("Gulf Star Supermarkets",0,48000,0),("Oasis Hotels FZE",0,0,52000),("Sharjah Wholesale Co",40000,0,0)]
for c,a,b,x in overdue:
    r = next(r for r in ar if r["customer"]==c); r.update(d31_60=a, d61_90=b, d90_plus=x)
w("ar_aging.csv", ar)
w("ap_aging.csv", [dict(vendor=v, current=round(R.uniform(15000,70000),2), early_pay_terms="2/10 net 45" if v in vendors[:3] else "net 45") for v in vendors])
stock = [dict(sku=f"SKU-{i:03d}", item=n, qty=q, unit_cost=u, last_sale_days=ls) for i,(n,q,u,ls) in enumerate([
    ("Stainless cookware set",420,185.0,12),("LED panel 60x60",900,62.0,8),("Bluetooth speaker X2",310,140.0,148),
    ("Insulated food box",1200,23.5,5),("Office chair ergo",95,390.0,210),("Ceramic dinner set",260,110.0,40)],1)]
w("inventory.csv", stock)
slow = sum(s["qty"]*s["unit_cost"] for s in stock if s["last_sale_days"]>120)
levers = {"overdue_receivables_collect": 140000.0, "early_pay_discounts_annualised": 19550.0,
          "slow_stock_release_at_cost_value": slow, "note": "Treasurer targets about AED 240,000 total"}
levers["total"] = round(sum(v for v in levers.values() if isinstance(v,float)),2)
json.dump(levers, open(D/"levers_expected.json","w"), indent=2)

# documents: 15 images (PNG), some Arabic or bilingual
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FA = "/usr/share/fonts/truetype/sand-box/google/Noto Sans Arabic/NotoSansArabic-VariableFont_wdth,wght.ttf"
from PIL import features
RAQM = features.check("raqm")
def ar_txt(s):  # raqm shapes and orders RTL itself; only fall back to reshaper+bidi without it
    return s if RAQM else get_display(arabic_reshaper.reshape(s))
truth = []
picks = [r for r in inv if r["type"]=="purchase"][:12] + [r for r in inv if r["type"]=="sale"][:3]
for k, r in enumerate(picks):
    lang = "ar" if k % 5 == 0 else "bilingual" if k % 3 == 0 else "en"
    im = Image.new("RGB",(800,1000),"white"); g = ImageDraw.Draw(im)
    f = ImageFont.truetype(F, 22); fa = ImageFont.truetype(FA, 26); big = ImageFont.truetype(F, 30)
    y = 40
    def line(en, ar=None):
        global y
        if lang != "ar" and en: g.text((40,y), en, font=f, fill="black")
        if lang != "en" and ar: g.text((760,y + (30 if lang=="bilingual" else 0)), ar_txt(ar), font=fa, fill="black", anchor="ra", **({"direction": "rtl", "language": "ar"} if RAQM else {}))
        y += 70 if lang=="bilingual" else 45
    title = "TAX INVOICE" if k % 4 else "RECEIPT"
    g.text((40,y), title, font=big, fill="navy"); y += 60
    line(f"Seller: {r['party'] if r['type']=='purchase' else 'Falcon Trading LLC'}", "البائع: " + (r['party'] if r['type']=='purchase' else 'فالكون للتجارة ش.ذ.م.م'))
    line(f"TRN: {r['trn']}", f"الرقم الضريبي: {r['trn']}")
    line(f"Invoice No: {r['invoice_no']}", f"رقم الفاتورة: {r['invoice_no']}")
    line(f"Date: {r['date']}", f"التاريخ: {r['date']}")
    line(f"Net amount: AED {r['net']:,.2f}", f"المبلغ الصافي: {r['net']:,.2f} درهم")
    line(f"VAT 5%: AED {r['vat']:,.2f}", f"ضريبة القيمة المضافة ٥٪: {r['vat']:,.2f} درهم")
    line(f"Total: AED {r['total']:,.2f}", f"الإجمالي: {r['total']:,.2f} درهم")
    g.text((40,940),"FICTIONAL DOCUMENT FOR DEMO", font=ImageFont.truetype(F,14), fill="gray")
    p = D/"docs"/f"doc_{k+1:02d}_{lang}.png"; im.save(p)
    truth.append(dict(file=p.name, lang=lang, vendor=r["party"] if r["type"]=="purchase" else "Falcon Trading LLC",
                      invoice_no=r["invoice_no"], date=r["date"], net=r["net"], vat=r["vat"], total=r["total"], currency="AED", trn=r["trn"]))
json.dump(truth, open(D/"docs"/"ground_truth.json","w"), indent=2, ensure_ascii=False)
print(len(inv), "invoices,", len(bank), "bank lines, levers", levers["total"])

# vendor master (Red Team) and October budget (Controller variance)
vm = [dict(vendor=v, created="2024-0%d-15" % (i % 9 + 1), bank_iban_changed="no", trn=TRN[v]) for i, v in enumerate(vendors)]
vm.append(dict(vendor="Quickline General Trading", created="2026-10-16", bank_iban_changed="no", trn=TRN["Quickline General Trading"]))
w("vendor_master.csv", vm)
json.dump({"4000": 1600000, "5000": 1150000, "6000": 45000, "6100": 128000, "6200": 300, "6300": 3000}, open(D/"budget_oct.json","w"), indent=2)
