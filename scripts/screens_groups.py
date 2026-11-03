from playwright.sync_api import sync_playwright
S = "out/screens/grp_"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1280, "height": 900}); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    pg.goto("http://127.0.0.1:8000/"); pg.wait_for_timeout(7500); pg.evaluate("document.body.classList.add('shot')")
    pg.locator("#hood").screenshot(path=S + "hood_collapsed.png")
    g = pg.locator("details.grp:has(#g2)"); g.locator(":scope > summary").click(); pg.wait_for_timeout(400); g.screenshot(path=S + "controls_open.png")
    d = pg.locator("details.sub:has(#h-debate)"); d.locator("summary").click(); pg.wait_for_timeout(500); d.screenshot(path=S + "debate_corrected.png")
    pg.locator("#ch2").screenshot(path=S + "ch2_counter.png")
    pg.evaluate("document.querySelector('#ch2 details.proof').open=true"); pg.wait_for_timeout(400); pg.locator("#p2").screenshot(path=S + "ch2_rejected.png")
    c = b.new_page(viewport={"width": 1280, "height": 1100}); c.on("pageerror", lambda e: errs.append(str(e)))
    c.request.post("http://127.0.0.1:8000/api/challenge/forget")
    c.goto("http://127.0.0.1:8000/challenge"); c.fill("#who", "Sneaky split"); c.click("text=Split under the radar"); c.click("text=Run Divi on my books"); c.wait_for_selector("#learn")
    c.screenshot(path=S + "challenge_proposal.png", full_page=True)
    c.click("text=Approve and re-run my sneak"); c.wait_for_selector("text=Caught on re-run"); c.wait_for_timeout(500)
    c.screenshot(path=S + "challenge_learned.png", full_page=True)
    c.request.post("http://127.0.0.1:8000/api/challenge/forget")
    print("errors", errs); b.close()
