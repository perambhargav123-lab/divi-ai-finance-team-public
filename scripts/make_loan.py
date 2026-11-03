"""Generate a fictional ~100 page facility agreement (text + PDF). Fictional parties only."""
import random
from pathlib import Path
O = Path(__file__).resolve().parents[1] / "data" / "loan"; O.mkdir(parents=True, exist_ok=True)
R = random.Random(11)
TOPICS = ["Definitions and Interpretation", "The Facility", "Purpose", "Conditions of Utilisation", "Utilisation", "Repayment", "Prepayment and Cancellation",
          "Interest", "Interest Periods", "Changes to the Calculation of Interest", "Fees", "Tax Gross Up and Indemnities", "Increased Costs", "Other Indemnities",
          "Mitigation by the Lenders", "Costs and Expenses", "Representations", "Information Undertakings", "General Undertakings", "Security",
          "Guarantee", "Financial Covenants", "Events of Default", "Changes to the Lenders", "Role of the Agent", "Conduct of Business by the Finance Parties",
          "Sharing among the Finance Parties", "Payment Mechanics", "Set-Off", "Notices", "Calculations and Certificates", "Partial Invalidity",
          "Remedies and Waivers", "Amendments and Waivers", "Confidentiality", "Counterparts", "Governing Law", "Enforcement"]
FILL = ["The Borrower shall ensure that each Obligor complies with this Clause at all times during the Availability Period.",
        "Any reference in this Agreement to a Finance Party shall be construed so as to include its successors in title, permitted assigns and permitted transferees.",
        "Unless a contrary indication appears, a term used in any other Finance Document or in any notice given under or in connection with any Finance Document has the same meaning in that Finance Document or notice as in this Agreement.",
        "The Agent shall promptly notify the Borrower and the Lenders of the determination of a rate of interest under this Agreement.",
        "Each payment to be made by an Obligor under the Finance Documents shall be made in AED to such account in the United Arab Emirates as the Agent may specify.",
        "No failure to exercise, nor any delay in exercising, on the part of any Finance Party, any right or remedy under a Finance Document shall operate as a waiver.",
        "The Borrower shall supply to the Agent, in sufficient copies for all the Lenders, such information as the Agent may reasonably request.",
        "If any provision of a Finance Document is or becomes illegal, invalid or unenforceable in any respect, that shall not affect the remaining provisions.",
        "All amounts payable under the Finance Documents are exclusive of any value added tax which might be chargeable in connection with that supply.",
        "The Lender may disclose to any of its Affiliates any information relating to the Obligors that it considers appropriate."]
COV = {22: ["22.1 Financial definitions. In this Clause, Cash means unrestricted cash at bank in the name of the Borrower held with Emirates NBD or another Acceptable Bank; Debt Service means scheduled principal plus interest falling due in a Relevant Period; EBITDA has the meaning given in Schedule 9.",
            "22.2 Debt Service Cover. The Borrower shall ensure that the ratio of EBITDA to Debt Service for each Relevant Period ending on a Quarter Date is not less than 1.25:1.",
            "22.3 Minimum Liquidity. The Borrower shall ensure that Cash is not, at the close of business on the last Business Day of any week, less than AED 250,000 (two hundred and fifty thousand UAE Dirhams).",
            "22.4 Testing. The financial covenants in Clause 22.2 shall be tested on each Quarter Date and the covenant in Clause 22.3 shall be tested weekly by reference to the Borrower's cash forecast and bank statements delivered under Clause 18.4.",
            "22.5 Equity Cure. If a breach of Clause 22.3 occurs, the Borrower may within 10 Business Days procure a shareholder injection in cash sufficient to cure the shortfall, in which case no Event of Default shall occur."],
       18: ["18.4 Cash forecast. The Borrower shall deliver to the Agent, every Monday, a rolling 13 week cash flow forecast signed by its finance manager."],
       23: ["23.3 Financial covenants. Any requirement of Clause 22 (Financial Covenants) is not satisfied, subject to Clause 22.5 (Equity Cure)."]}
pages, page_of = [], {}
for ci, t in enumerate(TOPICS, 1):
    n_pages = R.randint(2, 3) if ci not in (1, 38) else 5
    for p in range(n_pages):
        paras = []
        if p == 0: paras.append(f"{ci}. {t.upper()}")
        special = COV.get(ci, []) if p == 1 else []
        k = 1
        for _ in range(R.randint(5, 7)):
            paras.append(f"{ci}.{k + 5 if special else k} " + " ".join(R.sample(FILL, 3))); k += 1
            if special and k == 3: paras.extend(special); special = []
        pages.append(paras)
while len(pages) < 100: pages.append([f"SCHEDULE {len(pages) - 95}. FORM OF COMPLIANCE CERTIFICATE (CONTINUED)"] + [" ".join(R.sample(FILL, 3)) for _ in range(11)])
head = "FACILITY AGREEMENT dated 1 September 2026 between FALCON TRADING LLC (Borrower) and GULF CREST BANK PJSC (Lender, fictional) for an AED 3,000,000 revolving working capital facility."
txt = []
for i, ps in enumerate(pages, 1):
    txt.append(f"[Page {i}]\n" + ("\n".join([head] + ps) if i == 1 else "\n".join(ps)))
(O / "facility_agreement.txt").write_text("\n\n".join(txt), encoding="utf-8")
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import textwrap
c = canvas.Canvas(str(O / "facility_agreement.pdf"), pagesize=A4)
for i, ps in enumerate(pages, 1):
    y = 800; c.setFont("Helvetica", 8)
    for para in ([head] if i == 1 else []) + ps:
        for line in textwrap.wrap(para, 120):
            if y > 50: c.drawString(40, y, line); y -= 10
        y -= 4
    c.drawString(280, 25, f"Page {i} of {len(pages)}  |  fictional demo document"); c.showPage()
c.save(); print(len(pages), "pages", len(" ".join(" ".join(p) for p in pages).split()), "words")
