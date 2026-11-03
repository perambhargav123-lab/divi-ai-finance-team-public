from playwright.sync_api import sync_playwright
S = "out/screens/edge_"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1280, "height": 900}); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    pg.goto("http://127.0.0.1:8000/"); pg.wait_for_selector("#h-router table", state="attached"); pg.wait_for_timeout(1000)
    pg.evaluate("document.body.classList.add('shot')")
    for sid, name in (("h-rules", "controls_alerts"), ("h-loan", "loan_covenant"), ("h-debate", "debate_scorecard"), ("h-rcpt", "receipts"), ("h-router", "router"), ("h-board", "challenge_link")):
        d = pg.locator(f"details:has(#{sid})"); d.locator("summary").click(); pg.wait_for_timeout(500); d.screenshot(path=S + name + ".png"); d.locator("summary").click()
    d = pg.locator("details:has(#h-rules)"); d.locator("summary").click(); pg.click("text=Add control"); pg.wait_for_selector("#rout .ok", timeout=60000); pg.wait_for_timeout(300)
    d.screenshot(path=S + "rule_added.png")
    pg.locator("#hood .hoodlist").screenshot(path=S + "hood_list.png") if False else None
    c = b.new_page(viewport={"width": 1280, "height": 1000}); c.on("pageerror", lambda e: errs.append(str(e)))
    c.goto("http://127.0.0.1:8000/challenge"); c.fill("#who", "Demo player"); c.click("text=Fake new vendor"); c.click("text=Run Divi on my books"); c.wait_for_selector("#res .claim")
    c.fill("#who", "Sneaky split"); c.click("text=Split under the radar"); c.click("text=Run Divi on my books"); c.wait_for_timeout(1500)
    c.screenshot(path=S + "challenge.png", full_page=True)
    print("errors", errs); b.close()
