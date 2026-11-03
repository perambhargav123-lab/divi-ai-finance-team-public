from playwright.sync_api import sync_playwright
S = "out/screens/redesign_"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    pg.goto("http://127.0.0.1:8000/?replay=1&speed=4"); pg.wait_for_selector("#drafts .dcard"); pg.wait_for_timeout(1500)
    pg.click("#run"); pg.wait_for_selector("text=Run the close again", timeout=120000); pg.wait_for_timeout(1500)
    pg.screenshot(path=S + "full.png", full_page=True)
    pg.evaluate("document.body.classList.add('shot')")
    for c in ("ch1", "ch2", "ch3", "ch4", "ch5", "hood"):
        pg.locator("#" + c).screenshot(path=S + c + ".png")
    pg.click("#hood summary >> nth=0"); pg.wait_for_timeout(600); pg.locator("#hood").screenshot(path=S + "hood_open.png")
    print("errors", errs); b.close()
