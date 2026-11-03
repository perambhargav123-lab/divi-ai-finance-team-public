"""Learning loop: each Approve or Reject becomes a rule or vendor note that removes a human touch next month.
September is a simulated earlier close; October is this close's real meter; November is projected from the learned rules."""
import json
from pathlib import Path
O = Path(__file__).resolve().parents[1] / "out"
# decision target -> (rule on approve, note on reject, stage, human touches it removes next month)
BOOK = {
 "large_payment_to_new_vendor": ("Payments over AED 10,000 to vendors created in the last 30 days are blocked until a PO and a phone callback are logged.",
                                 "Large payments to new vendors with a PO on file are allowed; keep flag only without PO.", "red_team", 2),
 "weekend_journal_by_junior": ("Journals by intern or junior users on weekends route to the Financial Controller before posting.",
                               "intern.k weekend journals are allowed when the FC approves within 24 hours.", "red_team", 1),
 "duplicate_vendor_invoice": ("Vendor invoices with the same party, amount and date, or a -A suffix, are auto-held and a credit note is requested.", "", "red_team", 1),
 "duplicate_bank_payment": ("A second bank payment with the same description and amount within 7 days is auto-recalled from the bank.", "", "red_team", 1),
 "C1": ("Gulf Star: chase on day 31 with the delivery suspension clause; their payment run is after the 15th.", "Gulf Star: softer tone, phone call before email.", "treasurer", 1),
 "C2": ("Oasis Hotels: always split disputed and undisputed amounts; escalate disputes to finance directors at day 14.", "Oasis: account manager handles disputes first.", "treasurer", 1),
 "C3": ("Sharjah Wholesale: accept two-part plans up to AED 50,000 without manager sign-off.", "Sharjah: plans need manager sign-off.", "treasurer", 1),
 "S1": ("Zenith: ask for 30 extra days when a week's net cash P50 is under AED 50,000.", "Zenith: never ask for extensions, relationship sensitive.", "treasurer", 0),
 "S2": ("Sahara Freight: extensions allowed on invoices under AED 10,000.", "", "treasurer", 0),
 "S3": ("Palm Foods: any basmati price above AED 11.00 per kg is auto-disputed under contract clause 6.", "", "capture", 1),
}
SEP = dict(month="Sep 2026 (simulated)", rule=548, model=12, human=56, total=616)

def state():
    meter = json.load(open(O / "automation_meter.json"))["overall"]
    dec = json.load(open(O / "decisions.json")) if (O / "decisions.json").exists() else []
    learned, seen = [], set()
    for d in dec:
        k = d["flag"]
        if k not in BOOK or k in seen: continue
        seen.add(k); rule, note, stage, saves = BOOK[k]; ok = d["decision"].startswith("approve")
        txt = rule if ok else note
        if txt: learned.append(dict(source=k, decision=d["decision"], kind="rule" if ok else "vendor note", stage=stage, text=txt, saves=saves if ok else 0))
    saved = sum(r["saves"] for r in learned); hn = max(meter["human"] - saved, 0)
    pct = lambda h, t: round(100 * (t - h) / t, 1)
    months = [dict(month=SEP["month"], human=SEP["human"], total=SEP["total"], automated_pct=pct(SEP["human"], SEP["total"])),
              dict(month="Oct 2026 (this close)", human=meter["human"], total=meter["total"], automated_pct=meter["automated_pct"]),
              dict(month="Nov 2026 (projected)", human=hn, total=meter["total"], automated_pct=pct(hn, meter["total"]))]
    return dict(months=months, learned=learned, decisions=len(dec))
