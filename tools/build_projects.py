"""Postaví rozcestník (index.html) a archiv projektů (projekty/index.html) přímo z monorepa.

    python tools/build_projects.py                 # monorepo = složka nad PORTOFOLIO/
    python tools/build_projects.py --root X        # jiná složka s projekty
    python tools/build_projects.py --check         # jen vypíše, co by se stalo, nic nezapíše
    python tools/build_projects.py --from-json     # bez monorepa: čísla vezme z projekty/projects.json,
                                                   # texty, odkazy a výběr z projects_data.py a šablon

Když se v monorepu najde málo projektů (špatná složka, jiný počítač), build skončí chybou
dřív, než by archiv ořezal a smazal obrázky. Na takovém počítači použij --from-json.

Co je ručně a co samo:
    ručně   tools/projects_data.py  - který projekt se ukáže, název, jedna věta CS/EN, odkaz
    samo    technologie (requirements.txt, package.json, gradle, obsah souborů),
            počet řádků, datum poslední změny, obrázek

Obrázek projektu se hledá v tomhle pořadí:
    1. tools/shots/<slug>.png|jpg|webp   (screenshot: ručně nebo přes tools/shoot.py)
    2. pole "shot" v projects_data.py     (obrázek uvnitř projektu, např. og.png)
    3. namalovaná SVG obálka              (stejný štětec jako tools/paint.py)

Nová složka v monorepu, která není v projects_data.py ani v IGNORE, se na web
nedostane, build ji jen vypíše. Nic soukromého tak neuteče omylem.
"""
import argparse
import json
import math
import os
import random
import re
import sys
import unicodedata
from datetime import date, datetime
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent                       # PORTOFOLIO/Portfolio
OUT = SITE / "projekty"
SHOTS_IN = HERE / "shots"
SHOTS_OUT = OUT / "shots"
TEMPLATE = HERE / "projekty.template.html"
HOME_TEMPLATE = HERE / "rozcestnik.template.html"
ABOUT_FILE = SITE / "o-mne" / "index.html"
MIN_FOUND = 0.8                          # míň nalezených projektů = skoro jistě špatná složka
DEFAULT_ROOT = SITE.parent.parent        # .Projekty (monorepo)

sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8")
import paint                              # noqa: E402  (štětec pro obálky)
import projects_data as D                 # noqa: E402

# ─────────────────────────────────────────────────────────── scan

CODE_EXT = {".py": "Python", ".pyw": "Python", ".js": "JavaScript", ".mjs": "JavaScript", ".ts": "TypeScript",
            ".tsx": "TypeScript", ".jsx": "JavaScript", ".java": "Java", ".kt": "Kotlin", ".html": "HTML",
            ".css": "CSS", ".sh": "Shell", ".ps1": "PowerShell", ".cs": "C#"}
SKIP_DIRS = {"venv", ".venv", "env", "node_modules", ".git", "__pycache__", "site-packages", "Lib", "lib",
             "dist", "build", ".gradle", "graphify-out", ".idea", ".claude", ".pytest_cache", "out",
             "logs", "cache", ".cache", "e2e"}
MAX_FILE = 400_000

# requirements.txt -> název na webu (None = nezajímavé, neukazovat)
REQ = {
    "flask": "Flask", "flask-socketio": "Socket.IO", "flask_socketio": "Socket.IO", "fastapi": "FastAPI",
    "pygame": "Pygame", "pygame-ce": "Pygame", "discord.py": "discord.py", "py-cord": "discord.py",
    "nextcord": "nextcord", "anthropic": "Claude API", "mistralai": "Mistral", "google-genai": "Gemini",
    "google-generativeai": "Gemini", "openai": "OpenAI API", "ollama": "Ollama", "numpy": "NumPy",
    "scipy": "SciPy", "opencv-python": "OpenCV", "mediapipe": "MediaPipe", "playwright": "Playwright",
    "selenium": "Selenium", "beautifulsoup4": "BeautifulSoup", "apscheduler": "APScheduler",
    "stripe": "Stripe", "resend": "Resend", "pywebview": "pywebview", "pillow": None,
    "sqlalchemy": "SQLAlchemy", "spotipy": "Spotify API", "yt-dlp": "yt-dlp", "elevenlabs": "ElevenLabs",
    "edge-tts": "edge-tts", "speechrecognition": "SpeechRecognition", "torch": "PyTorch",
    "cryptography": None,"praat-parselmouth": "Praat", "textual": "Textual", "rich": "Rich",
    "pyinstaller": "PyInstaller", "pystray": "pystray", "paramiko": "Paramiko", "mcp": "MCP",
    "zhipuai": "GLM", "matplotlib": "Matplotlib", "numba": "Numba", "flet": "Flet", "pymysql": "MySQL",
    "mysql-connector-python": "MySQL", "riotwatcher": "Riot API", "pywin32": "WinAPI", "pydantic": None,
}
NPM = {"three": "three.js", "vite": "Vite", "react": "React", "electron": "Electron", "typescript": "TypeScript",
       "@playwright/test": "Playwright", "socket.io": "Socket.IO", "express": "Express"}
# podpisy přímo v kódu: (přípony, regex, technologie)
SIGNS = [
    ({".py"}, re.compile(r"^\s*import sqlite3|^\s*from sqlite3", re.M), "SQLite"),
    ({".py"}, re.compile(r"^\s*(import|from) flask_socketio", re.M), "Socket.IO"),
    ({".py"}, re.compile(r"^\s*(import|from) anthropic", re.M), "Claude API"),
    ({".py"}, re.compile(r"^\s*import pygame", re.M), "Pygame"),
    ({".py"}, re.compile(r"""["'](ffmpeg|ffmpeg\.exe)["']"""), "ffmpeg"),
    ({".py"}, re.compile(r"^\s*(import|from) tkinter", re.M), "Tkinter"),
    ({".html", ".js", ".mjs"}, re.compile(r"""from\s+['"]three['"]|three(\.module)?(\.min)?\.js|/three@"""), "three.js"),
    ({".html", ".js", ".mjs"}, re.compile(r"immersive-vr|navigator\.xr"), "WebXR"),
    ({".html", ".js"}, re.compile(r"serviceWorker\.register"), "PWA"),
]
# obecné knihovny jdou na konec, ať se do 6 štítků vejde to podstatné
GENERIC = {"NumPy", "SciPy", "Matplotlib", "SQLite", "PWA", "Tkinter", "Rich", "BeautifulSoup", "PyInstaller",
           "pystray", "APScheduler", "Playwright", "OpenCV", "WinAPI", "Gradle"}


def norm_req(line):
    line = line.split("#", 1)[0].strip()
    if not line or line.startswith(("-", "git+", "http")):
        return None
    return re.split(r"[\s<>=!~;\[]", line, maxsplit=1)[0].lower()


def scan(paths):
    """Projde složky projektu: řádky podle jazyka, datum poslední změny, technologie, testy."""
    lines, techs, newest, tests = {}, [], 0.0, False

    def add(t):
        if t and t not in techs:
            techs.append(t)

    for root in paths:
        for cur, dirs, files in os.walk(root):
            keep = []
            for d in dirs:
                if d in SKIP_DIRS or d.startswith("."):
                    continue
                if "vendor" in d.lower():
                    try:
                        if any(n.lower().startswith("three") for n in os.listdir(os.path.join(cur, d))):
                            add("three.js")
                    except OSError:
                        pass
                    continue
                if d in ("tests", "test"):
                    tests = True
                keep.append(d)
            dirs[:] = keep
            for f in files:
                p = os.path.join(cur, f)
                low = f.lower()
                if low.startswith("requirements") and low.endswith(".txt"):
                    with open(p, encoding="utf-8", errors="ignore") as fh:
                        for line in fh:
                            add(REQ.get(norm_req(line) or ""))
                    continue
                if low == "package.json":
                    try:
                        pkg = json.loads(Path(p).read_text(encoding="utf-8"))
                        for dep in {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}:
                            add(NPM.get(dep))
                    except (ValueError, OSError):
                        pass
                    continue
                if low.startswith("build.gradle"):
                    add("Gradle")
                    if "paper" in Path(p).read_text(encoding="utf-8", errors="ignore").lower():
                        add("Paper")
                    continue
                ext = os.path.splitext(low)[1]
                lang = CODE_EXT.get(ext)
                if not lang or low.endswith(".min.js"):
                    continue
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if st.st_size > MAX_FILE:
                    continue
                if low.startswith("test_") or low.endswith((".test.js", "_test.py")):
                    tests = True
                with open(p, encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
                n = sum(1 for line in text.splitlines() if line.strip())
                lines[lang] = lines.get(lang, 0) + n
                newest = max(newest, st.st_mtime)
                for exts, rx, tech in SIGNS:
                    if ext in exts and tech not in techs and rx.search(text):
                        add(tech)
    return {"lines": lines, "techs": techs, "updated": newest, "tests": tests}


def stack_of(p, s):
    """Jazyky (jen ty, co v projektu opravdu něco váží) + frameworky, max 6."""
    if p.get("stack"):
        return p["stack"]
    total = sum(s["lines"].values()) or 1
    langs = sorted((l for l, n in s["lines"].items() if n >= max(150, total * 0.08)), key=lambda l: -s["lines"][l])
    if len(langs) > 1:                    # HTML/CSS jen když jsou hlavní věc projektu
        langs = [l for l in langs if l not in ("HTML", "CSS")] or langs
    out = langs[:2]
    for t in sorted(s["techs"], key=lambda t: t in GENERIC):
        if t not in out and not (t == "TypeScript" and "TypeScript" in out):
            out.append(t)
    return out[:6]


# ─────────────────────────────────────────────────────────── obrázky

PALETTES = {
    "klienti": (paint.CLAY + paint.SUN, paint.MANILLA + paint.KRAFT),
    "web": (paint.SKY, paint.HEATHER + paint.MANILLA),
    "hry": (paint.OLIVE + paint.KRAFT, paint.MANILLA + paint.SUN),
    "ai": (paint.HEATHER + ["#9C8CC4", "#8E7FBB"], paint.SKY + paint.MANILLA),
    "nastroje": (paint.KRAFT + paint.CLAY, paint.MANILLA + paint.HEATHER),
    "server": (paint.OLIVE + ["#6FA39A", "#7FB0A7"], paint.SKY + paint.MANILLA),
}


def cover_svg(slug, cat, w=480, h=300):
    """Malá impresionistická obálka: pozadí z vodorovných tahů, jedna skvrna jako „motiv“ a stín pod ní."""
    r = random.Random(slug)
    main, ground = PALETTES.get(cat, PALETTES["web"])
    horizon = h * (0.55 + r.random() * 0.15)
    # pod tahy plná barva, ať mezerami neprosvítá papír a obraz nepůsobí jako konfety
    body = [f'<rect width="{w}" height="{horizon:.0f}" fill="{ground[1]}"/>',
            f'<rect y="{horizon:.0f}" width="{w}" height="{h - horizon + 1:.0f}" fill="{main[0]}"/>']
    body += paint.sky_bands(r, [ground[:3], ground[1:4], ground[2:5] or ground], w, -10, horizon + 10, 70, (30, 60))
    body += paint.dabs(r, (-20, horizon - 4, w + 40, h - horizon + 14), main + ground[:1], 150, (24, 50),
                       r.choice([-6, 0, 6]), spread=16)
    cx, cy = w * (0.22 + r.random() * 0.56), horizon - h * (0.12 + r.random() * 0.1)
    rad = h * (0.15 + r.random() * 0.08)
    body += paint.ellipse_dabs(r, cx, cy, rad * 1.2, rad, main, 110, (12, 26), angle=r.random() * 180)
    # odlesk motivu pod horizontem, jako slunce na rybníce v hero obrazu
    body += paint.dabs(r, (cx - rad * .8, horizon + 6, rad * 1.6, h - horizon - 12), ground[:3], 34, (16, 34), 0,
                       spread=8, opacity=(.55, .9))
    defs = [paint.rough("f", 7, freq=0.03, seed=r.randint(1, 99))]
    return paint.svg(w, h, defs, [f'<g filter="url(#f)">', *body, "</g>"],
                     ' preserveAspectRatio="xMidYMid slice" role="img"')


def raster(src, dst, top=True, size=(960, 600)):
    """Ořízne obrázek na 16:10 (screenshoty od horního okraje) a uloží jako webp."""
    from PIL import Image
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return
    im = Image.open(src).convert("RGB")
    tw, th = size
    scale = max(tw / im.width, th / im.height)
    im = im.resize((math.ceil(im.width * scale), math.ceil(im.height * scale)), Image.LANCZOS)
    x = (im.width - tw) // 2
    y = 0 if top else (im.height - th) // 2
    im.crop((x, y, x + tw, y + th)).save(dst, "WEBP", quality=80, method=6)


def image_for(p, root):
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        src = SHOTS_IN / f"{p['slug']}{ext}"
        if src.exists():
            return src, True
    if p.get("shot") and (root / p["shot"]).exists():
        return root / p["shot"], False
    return None, False


# ─────────────────────────────────────────────────────────── html

CS_MONTHS = ["leden", "únor", "březen", "duben", "květen", "červen", "červenec", "srpen", "září",
             "říjen", "listopad", "prosinec"]


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def cs_num(n):
    return f"{n:,}".replace(",", " ")


def host(url):
    return re.sub(r"^https?://", "", url or "").rstrip("/")


def status_html(p):
    if p["status"] == "live":
        return '<span class="status status--live" data-t="live">V provozu</span>'
    if p["status"] == "active":
        return '<span class="status status--wip" data-t="active">Aktivní</span>'
    return ""


def card_html(i, p, cats):
    img = f'<img src="shots/{p["image"]}" alt="" width="480" height="300" loading="lazy" decoding="async">'
    figure = (f'<a class="pc__img" href="{escape(p["url"])}" target="_blank" rel="noopener" tabindex="-1" aria-hidden="true">{img}</a>'
              if p["url"] else f'<div class="pc__img">{img}</div>')
    chips = "".join(f"<li>{escape(t)}</li>" for t in p["stack"])
    link = (f'<a class="link" href="{escape(p["url"])}" target="_blank" rel="noopener">{escape(host(p["url"]))}'
            f'<svg class="i" viewBox="0 0 24 24"><path d="M7 17 17 7M8 7h9v9"/></svg></a>' if p["url"] else "")
    d = datetime.fromtimestamp(p["updated"])
    return f"""
<article class="pc" id="{p['slug']}" data-slug="{p['slug']}" data-cat="{p['cat']}" data-lines="{p['lines']}" data-date="{d:%Y-%m-%d}" data-name="{escape(p['name'].lower())}" style="--i:{i % 6}">
  {figure}
  <div class="pc__body">
    <div class="pc__top"><span class="pc__cat" data-cat-label="{p['cat']}">{escape(cats[p['cat']][0])}</span>{status_html(p)}</div>
    <h3>{escape(p['name'])}</h3>
    <p data-p="{p['slug']}">{escape(p['cs'])}</p>
    <ul class="chips" aria-label="Technologie">{chips}</ul>
    <div class="pc__foot"><span class="pc__meta"><span data-lines="{p['lines']}">{cs_num(p['lines'])} řádků</span> · <time datetime="{d:%Y-%m}">{CS_MONTHS[d.month - 1]} {d.year}</time></span>{link}</div>
  </div>
</article>"""


def demo_html(p):
    return f"""
<a class="demo" href="{escape(p['url'])}" target="_blank" rel="noopener" data-ping="{escape(p['url'])}">
  <span class="demo__img"><img src="shots/{p['image']}" alt="" width="480" height="300" loading="lazy" decoding="async"></span>
  <span class="demo__body">
    <span class="demo__top"><span class="ping" data-t="pingWait">Zkouším spojení…</span><span class="demo__host">{escape(host(p['url']))}</span></span>
    <span class="demo__name">{escape(p['name'])}</span>
    <span class="demo__line" data-p="{p['slug']}">{escape(p['cs'])}</span>
    <span class="demo__go"><span data-t="tryIt">Vyzkoušet naživo</span> <svg class="i" viewBox="0 0 24 24"><path d="M7 17 17 7M8 7h9v9"/></svg></span>
  </span>
</a>"""


def featured_html(i, p):
    note = (f'\n    <span class="card__note" data-note="{p["slug"]}">{escape(p["note_cs"])}</span>'
            if p.get("note_cs") else "")
    return f"""
<a class="card" href="{escape(p['url'])}" target="_blank" rel="noopener" data-ping="{escape(p['url'])}" style="--i:{i % 2}">
  <span class="card__img"><img src="projekty/shots/{p['image']}" alt="" width="960" height="600" loading="lazy" decoding="async"></span>
  <span class="card__body">
    <span class="card__top"><span class="ping" data-t="pingWait">Zkouším spojení…</span><span class="card__host">{escape(host(p['url']))}</span></span>
    <span class="card__name">{escape(p['name'])}</span>
    <span class="card__try" data-try="{p['slug']}">{escape(p['try_cs'])}</span>{note}
    <span class="card__go"><span data-t="tryIt">Vyzkoušet</span> <svg class="i" viewBox="0 0 24 24"><path d="M7 17 17 7M8 7h9v9"/></svg></span>
  </span>
</a>"""


def news_html(p, cats):
    d = datetime.fromtimestamp(p["updated"])
    return f"""
      <li><a href="projekty/#{p['slug']}"><time datetime="{d:%Y-%m-%d}" data-day="{d:%Y-%m-%d}">{d.day}. {d.month}. {d.year}</time><span class="news__name">{escape(p['name'])}</span><span class="news__cat" data-cat-label="{p['cat']}">{escape(cats[p['cat']][0])}</span></a></li>"""


def build_home(items, cats, total):
    """Rozcestník: vybrané projekty k vyzkoušení (pole featured) a naposledy změněné projekty."""
    featured = sorted((p for p in items if p.get("featured")), key=lambda p: p["featured"])
    for p in featured:
        if not (p.get("url") and p.get("try_cs") and p.get("try_en")):
            raise SystemExit(f"{p['slug']}: projekt na rozcestníku potřebuje url, try_cs a try_en")
    if not featured:
        raise SystemExit("v projects_data.py není žádný projekt s polem featured")
    n = len(featured)
    word = "projekt k vyzkoušení" if n == 1 else "projekty k vyzkoušení" if n < 5 else "projektů k vyzkoušení"
    home, about, archive = f"{D.SITE_URL}/", f"{D.SITE_URL}/o-mne/", f"{D.SITE_URL}/projekty/"
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "@id": f"{home}#web", "url": home, "name": "Voku", "inLanguage": ["cs", "en"],
         "publisher": {"@id": f"{home}#voku"}},
        {"@type": "Person", "@id": f"{home}#voku", "name": "Vojtěch Kurinec", "alternateName": "Voku", "url": about},
        {"@type": "WebPage", "@id": f"{home}#page", "url": home, "inLanguage": "cs",
         "name": "Vojtěch \"Voku\" Kurinec | Projekty k vyzkoušení",
         "isPartOf": {"@id": f"{home}#web"}, "about": {"@id": f"{home}#voku"},
         "primaryImageOfPage": f"{home}og-image.png",
         "hasPart": [{"@type": "ProfilePage", "@id": f"{about}#page", "url": about},
                     {"@type": "CollectionPage", "@id": f"{archive}#page", "url": archive}],
         "mainEntity": {"@type": "ItemList", "numberOfItems": n, "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "url": p["url"], "name": p["name"]}
             for i, p in enumerate(featured)]}},
    ]}
    i18n = {"cats": cats,
            "try": {p["slug"]: [p["try_cs"], p["try_en"]] for p in featured},
            "note": {p["slug"]: [p["note_cs"], p["note_en"]] for p in featured if p.get("note_cs")}}
    page = HOME_TEMPLATE.read_text(encoding="utf-8")
    for key, val in {
        "SITE_URL": D.SITE_URL,
        "COUNT": str(len(items)),
        "LINES": round_k(total),
        "FEATURED_COUNT": str(n),
        "FEATURED_WORD_JS": json.dumps(word, ensure_ascii=False),
        "FEATURED_WORD": word,
        "FEATURED": "".join(featured_html(i, p) for i, p in enumerate(featured)),
        "NEWS": "".join(news_html(p, cats) for p in items[:D.NEWS_COUNT]),
        "I18N": json.dumps(i18n, ensure_ascii=False).replace("</", "<\\/"),
        "JSONLD": json.dumps(jsonld, ensure_ascii=False, indent=1),
    }.items():
        page = page.replace("{{" + key + "}}", val)
    write_if_changed(SITE / "index.html", page)
    return featured


def write_if_changed(path, text):
    """Soubor se mění jen když se opravdu změní obsah -> poctivé lastmod v sitemapě."""
    if not path.exists() or path.read_bytes().decode("utf-8") != text:
        path.write_text(text, encoding="utf-8", newline="")


def round_k(n):
    return f"{n // 10_000 * 10}k+" if n >= 10_000 else cs_num(n)


def from_json():
    """Položky z minulého buildu (projects.json) + aktuální ruční data z projects_data.py."""
    old = {p["slug"]: p for p in json.loads((OUT / "projects.json").read_text(encoding="utf-8"))["projects"]}
    now = datetime.now().timestamp()
    items = []
    for p in D.PROJECTS:
        slug = p.get("slug") or slugify(p["name"])
        o = old.get(slug)
        if not o:
            print(f"  {slug}: není v projects.json, přeskakuju (přidá ho až build z monorepa)")
            continue
        updated = datetime.strptime(o["updated"], "%Y-%m-%d").timestamp()
        status = p.get("status") or ("active" if now - updated < 30 * 86400 else None)
        items.append({**p, "slug": slug, "lines": o["lines"], "updated": updated, "stack": p.get("stack") or o["stack"],
                      "status": status, "url": p.get("url"), "tests": o["tests"], "image": o["image"].rsplit("/", 1)[1]})
    order = {slug: i for i, slug in enumerate(old)}      # stejné datum = pořadí z minula, žádný šum v diffu
    items.sort(key=lambda p: (-p["updated"], order[p["slug"]]))
    found = re.search(r'<b>(\d+)</b><span data-t="figLangs">', (OUT / "index.html").read_text(encoding="utf-8"))
    if not found:
        raise SystemExit("v projekty/index.html jsem nenašel počet jazyků")
    return items, sum(p["lines"] for p in items), int(found.group(1))


def build(root, check=False, use_json=False):
    root = Path(root)
    if use_json:
        items, total, langs = from_json()
        publish(items, total, langs, root, check, scanned=False)
        return
    listed = {d for p in D.PROJECTS for d in p["dirs"]}
    present = {e.name for e in root.iterdir() if e.is_dir()}
    local = HERE / "ignore.local.txt"
    private = set(local.read_text(encoding="utf-8").split()) if local.exists() else set()
    unknown = sorted(present - listed - set(D.IGNORE) - private - {".idea", ".claude", ".git"})
    missing = sorted(d for d in listed if d not in present)

    items, lang_total = [], {}
    now = datetime.now().timestamp()
    for p in D.PROJECTS:
        paths = [root / d for d in p["dirs"] if (root / d).is_dir()]
        if not paths:
            continue
        s = scan(paths)
        lines = sum(s["lines"].values())
        if not lines:
            continue
        for k, v in s["lines"].items():
            lang_total[k] = lang_total.get(k, 0) + v
        status = p.get("status") or ("active" if now - s["updated"] < 30 * 86400 else None)
        items.append({**p, "slug": p.get("slug") or slugify(p["name"]), "lines": lines, "updated": s["updated"],
                      "stack": stack_of(p, s), "status": status, "url": p.get("url"), "tests": s["tests"]})

    items.sort(key=lambda p: -p["updated"])
    total = sum(lang_total.values())
    langs = sum(1 for v in lang_total.values() if v > 1000)
    if unknown:
        print("  nezařazené složky (doplň do projects_data.py nebo IGNORE):", ", ".join(unknown))
    if missing:
        print("  v projects_data.py, ale v monorepu nejsou:", ", ".join(missing))
    if not check and len(items) < MIN_FOUND * len(D.PROJECTS):
        raise SystemExit(f"STOP: v {root} je jen {len(items)} z {len(D.PROJECTS)} projektů, build by ořezal archiv "
                         "a smazal obrázky. Nastav --root na monorepo, nebo použij --from-json.")
    publish(items, total, langs, root, check, scanned=True)


def publish(items, total, langs, root, check, scanned):
    cats = {k: (cs, en) for k, cs, en in D.CATEGORIES}
    demos = [p for p in items if p.get("demo")]
    live = sum(1 for p in items if p["status"] == "live")

    print(f"{len(items)} projektů, {total} řádků, {langs} jazyků, {live} běží naostro, {len(demos)} živá dema")
    if check:
        for p in items:
            print(f"  {p['slug']:<24} {p['cat']:<9} {p['lines']:>7}  {', '.join(p['stack'])}")
        return

    # obrázky (při --from-json zůstávají, jak jsou)
    used = {p["image"] for p in items} if not scanned else set()
    if scanned:
        SHOTS_OUT.mkdir(parents=True, exist_ok=True)
        for p in items:
            src, is_shot = image_for(p, root)
            if src:
                p["image"] = f"{p['slug']}.webp"
                raster(src, SHOTS_OUT / p["image"], top=is_shot)
            else:
                p["image"] = f"{p['slug']}.svg"
                (SHOTS_OUT / p["image"]).write_text(cover_svg(p["slug"], p["cat"]), encoding="utf-8", newline="")
            used.add(p["image"])
        for old in SHOTS_OUT.iterdir():      # obrázky smazaných projektů pryč
            if old.name not in used:
                old.unlink()

    counts = {k: sum(1 for p in items if p["cat"] == k) for k in cats}
    filters = '<button type="button" class="on" data-f="all" aria-pressed="true"><span data-t="all">Vše</span> <i>{}</i></button>'.format(len(items))
    filters += "".join(f'<button type="button" data-f="{k}" aria-pressed="false"><span data-cat-label="{k}">{escape(cs)}</span> <i>{counts[k]}</i></button>'
                       for k, (cs, _) in cats.items() if counts[k])

    i18n = {"cats": cats, "p": {p["slug"]: [p["cs"], p["en"]] for p in items}}
    today = date.today()
    home, about, page_url = f"{D.SITE_URL}/", f"{D.SITE_URL}/o-mne/", f"{D.SITE_URL}/projekty/"
    person = {"@id": f"{home}#voku"}
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "@id": f"{page_url}#page", "url": page_url,
         "name": "Archiv projektů | Vojtěch \"Voku\" Kurinec", "inLanguage": "cs",
         "description": f"Všech {len(items)} projektů Vojtěcha Kurince: weby, hry, AI nástroje a servery.",
         "isPartOf": {"@id": f"{home}#web"}, "author": person, "dateModified": today.isoformat(),
         "primaryImageOfPage": f"{page_url}og.png",
         "breadcrumb": {"@id": f"{page_url}#breadcrumb"}, "mainEntity": {"@id": f"{page_url}#list"}},
        {"@type": "BreadcrumbList", "@id": f"{page_url}#breadcrumb", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Voku", "item": home},
            {"@type": "ListItem", "position": 2, "name": "Archiv projektů", "item": page_url}]},
        {"@type": "ItemList", "@id": f"{page_url}#list", "numberOfItems": len(items), "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "item": {
                "@type": "CreativeWork", "@id": f"{page_url}#{p['slug']}", "name": p["name"],
                "description": p["cs"], "creator": person, "keywords": ", ".join(p["stack"]),
                "dateModified": datetime.fromtimestamp(p["updated"]).strftime("%Y-%m-%d"),
                "image": f"{page_url}shots/{p['image']}",
                **({"url": p["url"]} if p["url"] else {})}}
            for i, p in enumerate(items)]},
    ]}
    page = TEMPLATE.read_text(encoding="utf-8")
    for key, val in {
        "SITE_URL": D.SITE_URL,
        "COUNT": str(len(items)),
        "LINES": round_k(total),
        "LANGS": str(langs),
        "LIVE": str(live),
        "UPDATED_ISO": today.isoformat(),
        "UPDATED_CS": f"{today.day}. {today.month}. {today.year}",
        "FILTERS": filters,
        "DEMOS": "".join(demo_html(p) for p in demos),
        "CARDS": "".join(card_html(i, p, cats) for i, p in enumerate(items)),
        "I18N": json.dumps(i18n, ensure_ascii=False).replace("</", "<\\/"),
        "JSONLD": json.dumps(jsonld, ensure_ascii=False, indent=1),
    }.items():
        page = page.replace("{{" + key + "}}", val)
    (OUT / "index.html").write_text(page, encoding="utf-8", newline="")

    public = [{"name": p["name"], "slug": p["slug"], "category": p["cat"], "cs": p["cs"], "en": p["en"],
               "url": p["url"], "demo": bool(p.get("demo")), "status": p["status"], "stack": p["stack"],
               "lines": p["lines"], "tests": p["tests"],
               "updated": datetime.fromtimestamp(p["updated"]).strftime("%Y-%m-%d"),
               "image": f"{D.SITE_URL}/projekty/shots/{p['image']}"} for p in items]
    (OUT / "projects.json").write_text(json.dumps({"generated": today.isoformat(), "projects": public},
                                                  ensure_ascii=False, indent=1), encoding="utf-8", newline="")

    # čísla na stránce O mně a rozcestník (soubor se mění jen když se opravdu změní -> poctivé lastmod)
    old = ABOUT_FILE.read_bytes().decode("utf-8")
    html = re.sub(r'(data-auto="projects">)[^<]*', rf"\g<1>{len(items) // 10 * 10}+", old)
    html = re.sub(r'(data-auto="projects-n">)[^<]*', rf"\g<1>{len(items)}", html)
    write_if_changed(ABOUT_FILE, html)
    about_mod = date.fromtimestamp(ABOUT_FILE.stat().st_mtime).isoformat()
    featured = build_home(items, cats, total)
    home_mod = date.fromtimestamp((SITE / "index.html").stat().st_mtime).isoformat()

    # sitemap: Google bere jen loc + lastmod (changefreq/priority ignoruje), obrázky pomáhají Google Images
    shots = [p for p in items if p["image"].endswith(".webp")]
    images = "".join(f"\n    <image:image><image:loc>{page_url}shots/{p['image']}</image:loc></image:image>" for p in shots)
    (SITE / "sitemap.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>{home}</loc>
    <lastmod>{home_mod}</lastmod>
    <image:image><image:loc>{home}og-image.png</image:loc></image:image>
  </url>
  <url>
    <loc>{about}</loc>
    <lastmod>{about_mod}</lastmod>
    <image:image><image:loc>{home}og-image.png</image:loc></image:image>
  </url>
  <url>
    <loc>{page_url}</loc>
    <lastmod>{today.isoformat()}</lastmod>
    <image:image><image:loc>{page_url}og.png</image:loc></image:image>{images}
  </url>
</urlset>
""", encoding="utf-8", newline="")

    # llms.txt: stručný přehled pro AI vyhledávače (ChatGPT, Perplexity, AI Overviews)
    lines = [f"# Vojtěch \"Voku\" Kurinec", "",
             f"> Mladý vývojář z jižních Čech (Jihočeský kraj, CZ). Weby a rezervační systémy pro laser game arény, "
             f"vlastní hry, AI nástroje a servery na Raspberry Pi. {len(items)} projektů, {round_k(total)} řádků kódu.", "",
             f"- [Rozcestník]({home}): projekty, které si můžeš hned vyzkoušet: "
             + ", ".join(p["name"] for p in featured),
             f"- [O mně]({about}): kdo jsem, na čem dělám, zakázky, technologie, kontakt",
             f"- [Archiv projektů]({page_url}): všechny projekty s popisem a technologiemi",
             f"- [Projekty jako JSON]({page_url}projects.json): strojově čitelná data", "",
             "## Kontakt", "", "- E-mail: vojta.kurinec@gmail.com", "- GitHub: https://github.com/Voku199", ""]
    for k, (cs, _) in cats.items():
        group = [p for p in items if p["cat"] == k]
        if not group:
            continue
        lines += [f"## {cs}", ""]
        lines += [f"- [{p['name']}]({p['url'] or page_url + '#' + p['slug']}): {p['cs']} ({', '.join(p['stack'])})"
                  for p in group]
        lines.append("")
    (SITE / "llms.txt").write_text("\n".join(lines), encoding="utf-8", newline="")
    print(f"  -> index.html, projekty/index.html, projects.json, sitemap.xml, llms.txt, {len(used)} obrázků")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--from-json", action="store_true", help="bez monorepa, čísla z projekty/projects.json")
    a = ap.parse_args()
    build(a.root, a.check, a.from_json)
