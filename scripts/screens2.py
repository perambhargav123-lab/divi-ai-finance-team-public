from playwright.sync_api import sync_playwright
S = "out/screens/"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1600, "height": 1000})
    pg.on("console", lambda m: print("console", m.text)); pg.goto("http://127.0.0.1:8000/?replay=1&speed=1"); pg.wait_for_timeout(1000); pg.click("#run")
    pg.wait_for_selector(".doc img", timeout=30000); pg.wait_for_timeout(2500); pg.screenshot(path=S + "live_capture_receipts.png")
    pg.goto("http://127.0.0.1:8000/"); pg.wait_for_timeout(1500); pg.click("text=Talk to your CFO")
    pg.click("text=Can we survive week 6?"); pg.wait_for_selector(".a >> text=165", timeout=90000)
    pg.click("text=Draft AED 165k credit line request"); pg.wait_for_selector("text=Open lender proof pack", timeout=90000); pg.wait_for_timeout(800)
    pg.screenshot(path=S + "cfo_chat_credit_line.png")
    pg.click("text=Bring your own books"); pg.set_input_files("#bcsv", "data/sample_byob_bank.csv"); pg.click("#t4 button.btn")
    pg.wait_for_selector("text=Column mapping by Muse", timeout=90000); pg.wait_for_timeout(1500); pg.screenshot(path=S + "byob_upload.png")
    pg.click("text=Statements and proof"); pg.wait_for_timeout(800); pg.click("#bs a.p >> nth=2"); pg.wait_for_selector("#proof img", timeout=30000); pg.wait_for_timeout(1000)
    pg.screenshot(path=S + "proof_panel.png"); b.close()
