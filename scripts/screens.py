import sys, time
from playwright.sync_api import sync_playwright
U = "http://127.0.0.1:8000/?replay=1&speed=1"; S = "out/screens/"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1)
    pg.goto(U); pg.wait_for_timeout(1500); pg.click("#run")
    pg.wait_for_selector(".debate .dt", timeout=90000); pg.wait_for_timeout(1500)
    pg.screenshot(path=S + "live_feed_midrun.png")
    pg.wait_for_selector(".fraud", timeout=90000); pg.wait_for_timeout(1200)
    pg.locator(".fraud").scroll_into_view_if_needed(); pg.wait_for_timeout(800)
    pg.screenshot(path=S + "fraud_moment.png"); pg.locator(".fraud").screenshot(path=S + "fraud_card.png")
    pg.wait_for_selector("text=Close complete", timeout=90000); pg.wait_for_timeout(1500)
    pg.screenshot(path=S + "live_close_done.png")
    b.close()
