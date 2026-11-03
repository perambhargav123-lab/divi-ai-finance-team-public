from playwright.sync_api import sync_playwright
S = "out/screens/extras_"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1280, "height": 900}); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    pg.goto("http://127.0.0.1:8000/"); pg.wait_for_selector("#h-sam img", state="attached"); pg.wait_for_selector("#h-cogs table", state="attached"); pg.wait_for_timeout(1500)
    pg.evaluate("document.body.classList.add('shot')")
    for sid, name in (("h-sam", "sam_pipeline"), ("h-taxweb", "uae_tax_web"), ("h-exp", "exports"), ("h-cogs", "je1040_cogs")):
        d = pg.locator(f"details:has(#{sid})"); d.locator("summary").click(); pg.wait_for_timeout(700); pg.locator(f"#{sid}").screenshot(path=S + name + ".png"); d.locator("summary").click()
    pg.click("text=शुद्ध लाभ कितना है?"); pg.wait_for_timeout(9000); pg.locator("#chat").screenshot(path=S + "chat_hindi.png")
    pg.locator("#hood").screenshot(path=S + "hood_list.png")
    print("errors", errs); b.close()
