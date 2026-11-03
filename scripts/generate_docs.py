"""Fictional unstructured docs for judgment tests: contracts, messages, invoice lines, payment history, September comparison."""
import csv, json, random
from pathlib import Path
D = Path(__file__).resolve().parent.parent / "data"; C = D / "contracts"; C.mkdir(exist_ok=True)
R = random.Random(55)
inv = {r["invoice_no"]: r for r in csv.DictReader(open(D / "invoices.csv", encoding="utf-8"))}
contracts = {
 "palm_foods_supply.txt": """SUPPLY AGREEMENT (FICTIONAL)
Parties: Palm Foods Import (Supplier) and Falcon Trading LLC (Buyer), Dubai, UAE
Effective date: 1 January 2026. Term: 24 months.
1. Products: Basmati rice, 25 kg bags, sold by the kilogram.
2. Price: AED 11.00 per kg, fixed for the term, excluding VAT.
3. VAT: 5% UAE VAT charged on top of the price.
4. Payment terms: 45 days from invoice date.
5. Price changes require 60 days written notice and a signed amendment.
6. Overbilling: any amount invoiced above the contract price must be credited within 14 days.
7. Governing law: Laws of the Emirate of Dubai.""",
 "jebel_ali_packaging.txt": """PACKAGING SUPPLY TERMS (FICTIONAL)
Parties: Jebel Ali Packaging LLC (Supplier) and Falcon Trading LLC (Buyer)
Effective date: 1 March 2026.
1. Products: Printed cartons, size A and size B.
2. Price: Size A AED 4.20 per carton; Size B AED 6.10 per carton, excluding VAT.
3. Payment terms: net 45 days.
4. Early payment discount: 2% of the invoice value if paid within 10 days of invoice date (2/10 net 45).
5. Minimum order: 1,000 cartons per order.""",
 "zenith_electronics_distribution.txt": """DISTRIBUTION AGREEMENT (FICTIONAL)
Parties: Zenith Electronics FZCO (Supplier) and Falcon Trading LLC (Distributor)
Effective date: 15 April 2026.
1. Products: LED panels and Bluetooth speakers.
2. Price list: LED panel 60x60 AED 62.00 per unit; Bluetooth speaker X2 AED 140.00 per unit.
3. Payment terms: 60 days from invoice date.
4. Price escalation: from 1 December 2026 all list prices increase by 3% if the LME copper price stays above USD 9,000 per tonne for 30 days. Supplier will notify by 15 November 2026.
5. Returns: unsold stock older than 180 days may be returned at 85% of cost.""",
 "gulf_star_customer.txt": """CUSTOMER SUPPLY AGREEMENT (FICTIONAL)
Parties: Falcon Trading LLC (Seller) and Gulf Star Supermarkets (Customer)
Effective date: 1 July 2026.
1. Credit terms: 30 days from invoice date. Credit limit AED 150,000.
2. Volume rebate: 2% of net sales if quarterly net purchases exceed AED 120,000. Rebate settled as a credit note after quarter end.
3. Late payment: Seller may suspend deliveries when any invoice is more than 30 days overdue.
4. Delivery: title and risk pass on delivery to the Customer warehouse, evidenced by a signed delivery note.""",
 "oasis_hotels_customer.txt": """HOSPITALITY SUPPLY AGREEMENT (FICTIONAL)
Parties: Falcon Trading LLC (Seller) and Oasis Hotels FZE (Customer)
Effective date: 1 February 2026.
1. Credit terms: 45 days from invoice date.
2. Quality claims: the Customer must raise any quality claim within 7 days of delivery with photos. Undisputed amounts remain payable on time.
3. Disputes are escalated to the account managers, then to the finance directors within 14 days.
4. Delivery: title passes on signed delivery note.""",
}
for n, t in contracts.items(): (C / n).write_text(t + "\n", encoding="utf-8")
msgs = [
 ("M01", "email", "2026-10-28", "accounts@gulfstar.example", "Gulf Star Supermarkets", "Re: October statement", "Hi Falcon team, we have your statement. Our payment run is after the 15th of November, we will pay FT-S-0012 and FT-S-0080 after the 15th."),
 ("M02", "email", "2026-10-29", "finance@oasishotels.example", "Oasis Hotels FZE", "Damaged linen delivery FT-S-0066", "Dear Falcon, 20 cartons of linen on FT-S-0066 arrived water damaged (photos attached, delivered 6 Oct). We are withholding AED 12,000 of that invoice until a credit note is agreed. The rest will be paid on terms."),
 ("M03", "whatsapp", "2026-10-31", "+971-50-000-0101 (Warehouse, Rashid)", "Marina Hypermarket", "", "Loaded and delivered Marina Hypermarket order MH-2210 today 31 Oct 5pm, DN-5521 signed. Sales will raise the invoice on 3 Nov, value AED 42,000 before VAT."),
 ("M04", "email", "2026-10-30", "it@falcontrading.example", "Horizon Office Supplies", "ERP licence renewal", "FYI the annual ERP licence was paid on invoice PI-0001 from Horizon Office Supplies, AED 18,000 net. It covers 1 Nov 2026 to 31 Oct 2027."),
 ("M05", "whatsapp", "2026-10-27", "+971-55-000-0202 (Desert Rose, Omar)", "Desert Rose Trading", "", "Sent you AED 18,500 today for the urgent order DR-77 your driver delivered on 29 Oct. Please send the invoice, we need it for our VAT."),
 ("M06", "email", "2026-10-26", "ap@sharjahwholesale.example", "Sharjah Wholesale Co", "Overdue balance", "Cash is tight this month. We will clear the AED 40,000 overdue in two parts, AED 20,000 on 20 Nov and AED 20,000 on 10 Dec."),
 ("M07", "email", "2026-10-30", "sales@zenith.example", "Zenith Electronics FZCO", "Advance notice: price review", "Copper has stayed above USD 9,000 for most of October. Under clause 4 we expect to apply the 3% increase from 1 December 2026. Formal notice to follow by 15 November."),
 ("M08", "email", "2026-10-24", "accounts@alnoor.example", "Al Noor Retail LLC", "Remittance", "Payment for all September invoices sent today. Thank you as always."),
 ("M09", "whatsapp", "2026-10-29", "+971-52-000-0303 (Blue Creek, Sara)", "Blue Creek Catering", "", "Can you resend the invoice copy for last week? Will pay this Thursday."),
 ("M10", "email", "2026-10-22", "procurement@emirateshome.example", "Emirates Home Supplies", "Next quarter volumes", "We plan to increase orders by about 15% from December. Please confirm stock of ceramic dinner sets."),
 ("M11", "email", "2026-10-25", "billing@palmfoods.example", "Palm Foods Import", "October invoices", "Please find our October invoices. Note our new price list of AED 12.50 per kg applies from October."),
 ("M12", "email", "2026-10-21", "ops@saharafreight.example", "Sahara Freight Services", "Fuel surcharge", "Fuel surcharge stays at current rate for November."),
 ("M13", "whatsapp", "2026-10-30", "+971-56-000-0404 (Coastline, Ali)", "Coastline Plastics", "", "Our bank details are unchanged. Ignore any email asking you to change them."),
 ("M14", "email", "2026-10-31", "accounts@oasishotels.example", "Oasis Hotels FZE", "Payment plan", "For the older balance of AED 52,000 we propose AED 26,000 in mid November and the rest in mid December."),
 ("M15", "email", "2026-10-28", "finance@marina.example", "Marina Hypermarket", "Payment", "All October invoices are approved and scheduled on normal terms."),
]
with open(D / "messages.jsonl", "w", encoding="utf-8") as f:
    for m in msgs: f.write(json.dumps(dict(zip(["id", "channel", "date", "from", "party", "subject", "body"], m)), ensure_ascii=False) + "\n")
# invoice lines for contracted suppliers (PI-0012 is overbilled at 12.50/kg)
lines = []
for no, r in inv.items():
    net = float(r["net"])
    if r["party"] == "Palm Foods Import":
        price = 12.50 if no == "PI-0012" else 11.00; item = "Basmati rice per kg"
    elif r["party"] == "Jebel Ali Packaging LLC": price, item = 4.20, "Printed carton size A"
    elif r["party"] == "Zenith Electronics FZCO": price, item = 62.00, "LED panel 60x60"
    else: continue
    lines.append(dict(invoice_no=no, party=r["party"], item=item, qty=round(net / price, 2), unit_price=price, net=net))
w = csv.DictWriter(open(D / "invoice_lines.csv", "w", newline="", encoding="utf-8"), fieldnames=list(lines[0])); w.writeheader(); w.writerows(lines)
# payment history: days late on the last 12 invoices per customer
beh = {"Al Noor Retail LLC": (2, 3), "Gulf Star Supermarkets": (22, 8), "Emirates Home Supplies": (0, 2), "Desert Rose Trading": (9, 6),
       "Marina Hypermarket": (3, 2), "Sharjah Wholesale Co": (18, 12), "Oasis Hotels FZE": (30, 15), "Blue Creek Catering": (6, 4)}
hist = []
for c, (mu, sd) in beh.items():
    for k in range(12):
        hist.append(dict(customer=c, invoice=f"H-{c[:3].upper()}-{k+1:02d}", month=f"2025-{(k % 12) + 1:02d}" if k < 2 else f"2026-{k - 1:02d}",
                         days_late=max(-3, round(R.gauss(mu, sd))), amount=round(R.uniform(5000, 35000), 2)))
w = csv.DictWriter(open(D / "payment_history.csv", "w", newline="", encoding="utf-8"), fieldnames=list(hist[0])); w.writeheader(); w.writerows(hist)
sep = dict(pnl={"4000": -1512300.0, "5000": 1071000.0, "6000": 35000.0, "6100": 121400.0, "6200": 310.0, "6300": 3420.0, "6400": 2000.0, "6500": 1500.0, "6700": 22800.0},
           drivers={"units_sold": 61200, "avg_price_aed": 24.71, "headcount": 22, "active_customers": 8, "promo_days": 0},
           drivers_oct={"units_sold": 64900, "avg_price_aed": 25.49, "headcount": 23, "active_customers": 8, "promo_days": 3,
                        "note": "one warehouse hire on 1 Oct; card spend includes trade show stand AED 21,000"})
json.dump(sep, open(D / "sept_2026.json", "w"), indent=2)
print("ok", len(msgs), len(lines), len(hist))
