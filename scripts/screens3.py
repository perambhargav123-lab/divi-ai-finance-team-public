from playwright.sync_api import sync_playwright
S = "out/screens/"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1600, "height": 1100})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:8000/"); pg.wait_for_selector("#tr-rows table", state="attached"); pg.wait_for_timeout(800)
    def tab(t, name, full=False):
        pg.click(f'#nav2 button[data-t="{t}"]'); pg.wait_for_timeout(1500); pg.screenshot(path=S + name, full_page=full)
    tab("t5", "proof_layer_counter.png")
    tab("t6", "contract_overbilling_catch.png")
    tab("t7", "ai_cash_p10_p50_p90.png")
    pg.click('#nav2 button[data-t="t8"]'); pg.wait_for_timeout(500)
    for d in ("C1", "C2", "S3"): pg.click(f"button[onclick*=\"'{d}','approve_draft'\"]"); pg.wait_for_timeout(300)
    pg.click("button[onclick*=\"'S1','reject'\"]"); pg.wait_for_timeout(500); pg.screenshot(path=S + "collections_supplier_drafts.png", full_page=True)
    for f in ("large_payment_to_new_vendor", "weekend_journal_by_junior"):
        pg.evaluate(f"fetch('/api/decision',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{flag:'{f}',decision:'approve_escalation'}})}})")
    pg.wait_for_timeout(500); pg.click('#nav2 button[data-t="t9"]'); pg.evaluate("loadLearning()"); pg.wait_for_timeout(1500); pg.screenshot(path=S + "learning_loop.png")
    tab("t10", "uae_tax_panel.png", True)
    tab("t11", "board_flux.png")
    tab("t12", "fraud_benchmark_scoreboard.png", True)
    tab("t13", "ai_trace_viewer.png", True)
    print("errors", errs); b.close()
