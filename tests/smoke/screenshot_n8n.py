from playwright.sync_api import sync_playwright
import sys

OUT = r"D:/ANSER_dev/tests/evidence"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    ctx = browser.new_context(viewport={"width": 1500, "height": 950})
    pg = ctx.new_page()

    pg.goto("http://localhost:5678/signin", wait_until="networkidle")
    pg.wait_for_timeout(1500)

    # điền bằng nhiều cách để chắc ăn
    try:
        pg.get_by_label("Email").fill("admin@anser.local")
        pg.get_by_label("Password").fill("AnserTest123!")
    except Exception:
        boxes = pg.query_selector_all("input")
        boxes[0].click(); pg.keyboard.type("admin@anser.local")
        boxes[1].click(); pg.keyboard.type("AnserTest123!")
    pg.wait_for_timeout(500)
    pg.get_by_role("button", name="Sign in").click()
    pg.wait_for_timeout(4000)
    print("after login url:", pg.url)

    pg.goto("http://localhost:5678/home/executions", wait_until="networkidle")
    pg.wait_for_timeout(4000)
    pg.screenshot(path=f"{OUT}/n8n_executions.png")
    print("shot executions url:", pg.url)

    pg.goto("http://localhost:5678/home/workflows", wait_until="networkidle")
    pg.wait_for_timeout(3000)
    pg.screenshot(path=f"{OUT}/n8n_workflows.png")
    print("shot workflows url:", pg.url)

    browser.close()
print("done")
