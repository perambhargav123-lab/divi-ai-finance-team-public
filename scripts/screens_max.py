from playwright.sync_api import sync_playwright
S = "out/screens/max_"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1280, "height": 900}); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    pg.goto("http://127.0.0.1:8000/"); pg.wait_for_selector("#score .sc"); pg.wait_for_selector("#h-roi .mini", state="attached"); pg.wait_for_timeout(1200)
    pg.evaluate("document.body.classList.add('shot')")
    pg.locator(".hero").screenshot(path=S + "hero_scoreboard.png")
    pg.click("#ch3 .knum.clk"); pg.wait_for_timeout(700); pg.screenshot(path=S + "click_to_source.png")
    pg.evaluate("document.getElementById('proof').style.display='none'")
    for sid, name in (("h-vision", "vision"), ("h-fx", "fx"), ("h-lc", "longctx_tools"), ("h-audit", "audit"), ("h-roi", "roi")):
        d = pg.locator(f"details:has(#{sid})"); d.locator("summary").click(); pg.wait_for_timeout(500); d.screenshot(path=S + name + ".png"); d.locator("summary").click()
    d = pg.locator("details:has(#bcsv)"); d.locator("summary").click(); pg.wait_for_timeout(300); d.screenshot(path=S + "byob_sample.png")
    pg.locator("#rail").screenshot(path=S + "rail_reset.png")
    print("errors", errs); b.close()
