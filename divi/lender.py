"""Credit line request and lender proof pack (PDF) built from the close and the 13-week forecast."""
import json
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from divi import llm, voice

O = Path(__file__).resolve().parents[1] / "out"; CACHE = O / "cache" / "credit_letter.txt"

def letter(amount, t, c):
    mock = CACHE.read_text() if CACHE.exists() else f"Request for a revolving working capital facility of AED {amount:,}."
    txt = llm.complete("Draft a short, plain, professional letter (under 200 words) from the CFO of Falcon Trading LLC, a Dubai trading company, "
                       f"to its relationship manager at the bank requesting a revolving working capital facility of AED {amount:,}. Facts: October 2026 "
                       f"net profit AED {c['net_profit']:,.0f}; cash 31 Oct AED {c['trial_balance']['1000']['amount']:,.0f}; downside 13-week forecast "
                       f"low AED {t['downside']['lowest_cash']:,.0f} in week {t['downside']['lowest_week']} driven by slower customer payments; cash "
                       f"release plan of AED 240,000 underway (overdue collections, slow stock, early-pay discounts). Mention the attached proof pack where "
                       "every number links to its source document. No placeholders except [Bank name] and [RM name].", mock_response=mock)
    if not llm.is_mock(): CACHE.parent.mkdir(parents=True, exist_ok=True); CACHE.write_text(txt)
    return txt

def _tbl(rows, widths=None):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("ALIGN", (1, 1), (-1, -1), "RIGHT")]))
    return t

def pack():
    c = json.load(open(O / "close_oct2026.json")); t = json.load(open(O / "treasury_13w.json")); rt = json.load(open(O / "redteam_oct2026.json"))
    amount = voice.credit_need(t); txt = letter(amount, t, c)
    S = getSampleStyleSheet(); el = [Paragraph("Falcon Trading LLC: lender proof pack", S["Title"]),
          Paragraph(f"October 2026 close | facility requested AED {amount:,} | fictional company, demo only", S["Normal"]), Spacer(1, 10),
          Paragraph("Credit line request", S["Heading2"])] + [Paragraph(p.replace("\n", "<br/>"), S["Normal"]) for p in txt.split("\n\n")]
    f = lambda x: f"{abs(x):,.0f}"
    el += [PageBreak(), Paragraph("Profit and loss, October 2026 (AED)", S["Heading2"]),
           _tbl([["Account", "AED", "Proof entries"]] + [[f"{k} {v['name']}", f(v["amount"]), f"{len(v['proof'])} entries"] for k, v in c["pnl"].items()]
                + [["Net profit", f"{c['net_profit']:,.0f}", ""]]),
           Paragraph("Balance sheet, 31 October 2026 (AED)", S["Heading2"]),
           _tbl([["Account", "AED", "Proof entries"]] + [[f"{k} {v['name']}", f(v["amount"]), f"{len(v['proof'])} entries"] for k, v in c["balance_sheet"].items()]),
           PageBreak(), Paragraph("13-week cash forecast (closing cash, AED)", S["Heading2"]),
           _tbl([["Week", "Starts", "Base", "Downside", "Base + release", "Downside + release"]] +
                [[str(i + 1), w, f"{t['base']['closing'][i]:,.0f}", f"{t['downside']['closing'][i]:,.0f}", f"{t['base_with_levers']['closing'][i]:,.0f}",
                  f"{t['downside_with_levers']['closing'][i]:,.0f}"] for i, w in enumerate(t["base"]["weeks"])]),
           Paragraph("Cash release levers", S["Heading2"]),
           _tbl([["#", "Lever", "AED", "Owner", "Weeks"]] + [[str(L["rank"]), L["name"], f"{L['amount']:,.0f}", L["owner"], f"{L['first_week']}-{L['last_week']}"] for L in t["levers"]]),
           PageBreak(), Paragraph("Evidence index", S["Heading2"]),
           Paragraph("Every statement line traces to journal entries; every entry traces to a source document, bank line or rule.", S["Normal"]),
           _tbl([["Entry", "Memo", "Proof"]] + [[e["id"], e["memo"][:45], ", ".join(e["proof"])[:70]] for e in c["entries"] if not e["memo"].startswith(("sale ", "purchase ", "cash ", "opening"))]
                + [["...", f"{len(c['entries'])} entries in total, full index in close_oct2026.json", ""]], [50, 200, 270]),
           Paragraph("Open review items (Red Team)", S["Heading2"]),
           _tbl([["Rule", "Items", "Severity"]] + [[x["rule"], ", ".join(x["items"]), x["severity"]] for x in rt])]
    p = O / "lender_proof_pack.pdf"; SimpleDocTemplate(str(p), pagesize=A4, title="Falcon Trading lender proof pack").build(el)
    return dict(amount=amount, letter=txt, pdf="/out/lender_proof_pack.pdf")
