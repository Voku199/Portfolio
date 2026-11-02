"""Vyfotí screenshoty živých webů z projects_data.py do tools/shots/<slug>.png.

    python tools/shoot.py              # všechno, co má "url"
    python tools/shoot.py sandiff bakix  # jen tyhle (slugy)
    python tools/shoot.py --og         # náhled pro sdílení projekty/og.png + apple-touch-icon.png
                                       # (spouštěj PO build_projects.py, bere z něj čísla a obrázky)

Potřebuje Playwright:  pip install playwright && playwright install chromium
Pak znovu spusť build_projects.py, ten screenshoty ořízne a převede na webp.
Ruční screenshot (třeba hry nebo appky, co neběží na webu) stačí uložit
do tools/shots/<slug>.png a build ho vezme přednostně.
"""
import json
import sys

from build_projects import D, OUT, SHOTS_IN, SITE, slugify

FONTS = ("https://fonts.googleapis.com/css2?family=Geist+Mono:wght@400;500"
         "&family=Newsreader:ital,opsz,wght@0,6..72,300..500;1,6..72,300..500&display=swap")


def og():
    """1200×630 karta ve stylu webu: titulek vlevo, mozaika obrázků projektů vpravo."""
    from playwright.sync_api import sync_playwright

    data = json.loads((OUT / "projects.json").read_text(encoding="utf-8"))["projects"]
    lines = sum(p["lines"] for p in data)
    shots = sorted((p for p in data if p["image"].endswith(".webp")), key=lambda p: not p["url"])  # živé weby první
    pics = shots[:4] + [p for p in data if p["image"].endswith(".svg")][:2]
    tiles = "".join(f'<img src="{(OUT / "shots" / p["image"].rsplit("/", 1)[1]).as_uri()}">' for p in pics[:6])
    html = f"""<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="{FONTS}">
<style>
*{{margin:0;box-sizing:border-box}}
body{{width:1200px;height:630px;background:#F0EEE6;color:#141413;display:grid;grid-template-columns:560px 1fr;border:1px solid #141413}}
.l{{padding:56px 52px;display:flex;flex-direction:column;border-right:1px solid #141413}}
.k{{font:500 17px 'Geist Mono',monospace;letter-spacing:.08em;text-transform:uppercase;color:#5E5D59}}
.k b{{color:#B5512F;font-weight:500}}
h1{{font:400 82px/0.98 'Newsreader',serif;letter-spacing:-.03em;margin-top:28px}}
h1 em{{color:#B5512F}}
.f{{margin-top:auto;font:400 19px 'Geist Mono',monospace;color:#5E5D59;letter-spacing:.04em}}
.f b{{color:#141413;font-weight:500}}
.r{{display:grid;grid-template-columns:1fr 1fr;grid-auto-rows:1fr;gap:1px;background:#141413}}
.r img{{width:100%;height:100%;object-fit:cover;display:block}}
</style>
<div class="l"><p class="k"><b>{len(data)}</b> projektů · vokudev.cz</p>
<h1>Všechno, co jsem <em>kdy postavil</em>.</h1>
<p class="f"><b>Vojtěch „Voku“ Kurinec</b><br>{lines // 10000 * 10}k+ řádků · weby · hry · AI</p></div>
<div class="r">{tiles}</div>"""
    page_file = OUT / "_og.html"
    page_file.write_text(html, encoding="utf-8")
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 1200, "height": 630})
            pg.goto(page_file.as_uri(), wait_until="networkidle")
            pg.wait_for_timeout(600)
            pg.screenshot(path=str(OUT / "og.png"))
            page_file.write_text('<body style="margin:0;background:#F0EEE6"><img src="../favicon.svg" '
                                 'style="width:180px;height:180px;display:block">', encoding="utf-8")
            icon = b.new_page(viewport={"width": 180, "height": 180})
            icon.goto(page_file.as_uri(), wait_until="load")
            icon.screenshot(path=str(SITE / "apple-touch-icon.png"))
            b.close()
    finally:
        page_file.unlink()
    print("ok   projekty/og.png, apple-touch-icon.png")


def main(only):
    from playwright.sync_api import sync_playwright

    SHOTS_IN.mkdir(exist_ok=True)
    todo = [p for p in D.PROJECTS if p.get("url")]
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1,
                                locale="cs-CZ", reduced_motion="reduce")
        for p in todo:
            slug = p.get("slug") or slugify(p["name"])
            if only and slug not in only:
                continue
            try:
                page.goto(p["url"], wait_until="networkidle", timeout=25_000)
                page.wait_for_timeout(1200)          # doběhnou úvodní animace a fonty
                page.screenshot(path=str(SHOTS_IN / f"{slug}.png"))
                print("ok  ", slug, p["url"])
            except Exception as e:                   # web zrovna neběží -> zůstane starý screenshot / obálka
                print("FAIL", slug, p["url"], type(e).__name__)
        browser.close()


if __name__ == "__main__":
    if "--og" in sys.argv:
        og()
    else:
        main(set(sys.argv[1:]))
