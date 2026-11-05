"""Postaví úvodní stránku (index.html), /jak-funguju/ a appku s projekty (projekty/index.html) přímo z monorepa.

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
import hashlib
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
HOME_TEMPLATE = HERE / "index.template.html"
HOW_TEMPLATE = HERE / "jak-funguju.template.html"
HOW_FILE = SITE / "jak-funguju" / "index.html"
ASSETS = SITE / "assets"
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


ARROW = '<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17 17 7M8 7h9v9"/></svg>'
CAT_MARKS = {"klienti": ("#", "var(--seal)"), "web": ("=", "#6A9BCC"), "hry": ("+", "var(--olive)"),
             "ai": ("*", "#8E7FBB"), "nastroje": ("-", "var(--clay)"), "server": (":", "var(--muted)")}


def card_html(i, p, cats):
    """Řádek v seznamu + detail. Detail je v HTML u každého projektu, ať ho vidí vyhledávače i prohlížeč bez JS."""
    d = datetime.fromtimestamp(p["updated"])
    chips = "".join(f"<li>{escape(t)}</li>" for t in p["stack"])
    lang = p["stack"][0] if p["stack"] else ""
    can_try = bool(p.get("url") and (p.get("demo") or p.get("featured")))
    ping = f'<span data-ping="{escape(p["url"])}"><span class="ping"></span></span>' if can_try else ""
    try_line = f'<p class="d__try" data-try="{p["slug"]}">{escape(p["try_cs"])}</p>' if p.get("try_cs") else ""
    note = f'<p class="d__note" data-note="{p["slug"]}">{escape(p["note_cs"])}</p>' if p.get("note_cs") else ""
    label = ('<span data-t="tryIt">Vyzkoušet naživo</span>' if can_try else '<span data-t="openIt">Otevřít</span>')
    go = (f'<a class="btn d__go" href="{escape(p["url"])}" target="_blank" rel="noopener">{label} '
          f'<span style="opacity:.7;font-weight:400">{escape(host(p["url"]))}</span> {ARROW}</a>') if p["url"] else ""
    return f"""
<article class="p" id="{p['slug']}" data-status="{p['status'] or ''}" data-cat="{p['cat']}" data-lines="{p['lines']}" data-date="{d:%Y-%m-%d}" data-name="{escape(p['name'].lower())}" data-can="{1 if can_try else 0}" style="--i:{min(i, 16)}">
  <h2 class="p__h"><button class="p__row" type="button" aria-expanded="false" aria-controls="m-{p['slug']}">
    <span class="p__star" aria-hidden="true">*</span><span class="p__name">{escape(p['name'])}</span><span class="p__dots" aria-hidden="true"></span><span class="p__right">{escape(lang)} · {d.year}</span>
    <span class="p__line" data-p="{p['slug']}">{escape(p['cs'])}</span>
  </button></h2>
  <div class="p__more" id="m-{p['slug']}"><div class="d">
    <span class="d__img"><img src="shots/{p['image']}" alt="" width="480" height="300" loading="lazy" decoding="async"></span>
    <div class="d__body">
      <div class="d__top"><span class="d__cat" data-cat-label="{p['cat']}">{escape(cats[p['cat']][0])}</span>{status_html(p)}{ping}</div>
      <p class="d__name">{escape(p['name'])}</p>
      <p class="d__desc" data-p="{p['slug']}">{escape(p['cs'])}</p>{try_line}{note}
      <ul class="chips">{chips}</ul>
      <p class="d__facts"><span>{cs_num(p['lines'])} <span data-t="factLinesWord">řádků</span></span><span>{d.month}/{d.year}</span></p>
      {go}
    </div>
  </div></div>
</article>"""


def featured_html(i, p):
    note = (f'\n    <span class="feature__note" data-note="{p["slug"]}">{escape(p["note_cs"])}</span>'
            if p.get("note_cs") else "")
    return f"""
<a class="feature" href="{escape(p['url'])}" target="_blank" rel="noopener" data-ping="{escape(p['url'])}">
  <span class="feature__art"><img src="projekty/shots/{p['image']}" alt="" width="960" height="600" loading="lazy" decoding="async"></span>
  <span class="feature__body">
    <span class="feature__top"><span class="ping"></span><span class="feature__host">{escape(host(p['url']))}</span></span>
    <span class="feature__name">{escape(p['name'])}</span>
    <span class="feature__line" data-try="{p['slug']}">{escape(p['try_cs'])}</span>{note}
    <span class="feature__go"><span data-t="tryIt">Vyzkoušet</span> {ARROW}</span>
  </span>
</a>"""


# ─────────────────────────────────────────────────────────── společné kusy stránek

FONTS = ("https://fonts.googleapis.com/css2?family=Geist:wght@300..600&family=Geist+Mono:wght@400;500"
         "&family=Newsreader:ital,opsz,wght@0,6..72,300..500;1,6..72,300..500&display=swap")
# Motiv se rozhoduje ještě před prvním vykreslením, ať stránka v noci neblikne:
# uložená volba > systém > denní doba (večer a v noci tmavě, protože kvůli tomu tmavý režim je).
THEME_SCRIPT = ("<script>(function(d){d.classList.add('js');var t;try{t=localStorage.getItem('theme')}catch(e){}"
                "if(t!=='light'&&t!=='dark'){var h=new Date().getHours();"
                "t=matchMedia('(prefers-color-scheme: dark)').matches||h>=20||h<6?'dark':'light'}"
                "d.dataset.theme=t})(document.documentElement)</script>")
SEAL = ('<svg class="seal" viewBox="0 0 34 34" aria-hidden="true"><rect width="34" height="34" rx="5"/>'
        '<g fill="#fff6f2"><rect x="15.5" y="5" width="3" height="23"/><rect x="7" y="13" width="3" height="15"/>'
        '<rect x="24" y="13" width="3" height="15"/><rect x="7" y="25" width="20" height="3"/></g></svg>')


def asset_version():
    """Krátký otisk assets/: změna souboru = nová adresa, takže se neservíruje starý z cache."""
    h = hashlib.sha1()
    for f in sorted(ASSETS.iterdir()):
        h.update(f.read_bytes())
    return h.hexdigest()[:8]


def head_html(base):
    return "\n".join([
        THEME_SCRIPT,
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        f'<link rel="stylesheet" href="{FONTS}">',
        f'<link rel="stylesheet" href="{base}assets/site.css?v={asset_version()}">',
    ])


def nav_html(base, current):
    links = [("jak-funguju/", "navHow", "Jak funguju", "how"), ("projekty/", "navProjects", "Projekty", "projects")]
    items = ""
    for href, key, label, name in links:
        here = ' aria-current="page"' if name == current else ""
        items += f'<a href="{base}{href}" data-t="{key}"{here}>{label}</a>'
    home = "../" if base else "./"
    return f"""<header class="nav">
  <div class="nav__inner wrap">
    <a class="nav__logo" href="{home}" aria-label="Voku">{SEAL}<span>Voku</span></a>
    <nav class="nav__links" aria-label="Menu" data-t-aria="navMenu">{items}</nav>
    <button class="theme" type="button" aria-pressed="false" aria-label="Zapnout tmavý režim"><span class="theme__sun" aria-hidden="true"><svg class="i" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/></svg></span><span class="theme__moon" aria-hidden="true"><svg class="i" viewBox="0 0 24 24"><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/></svg></span></button>
    <div class="lang-switch" role="group" aria-label="Language / Jazyk">
      <button type="button" class="active" data-lang="cs" aria-pressed="true" title="Česky">CS</button>
      <button type="button" data-lang="en" aria-pressed="false" title="English">EN</button>
    </div>
  </div>
</header>"""


def footer_html(base, total, count):
    home = "../" if base else "./"
    return f"""<footer class="footer">
  <div class="wrap wrap--ruled">
    <p class="footer__quote" data-t="footQuote">„Neboj se říct <span class="brush">svůj názor</span>.“</p>
    <div class="waves" data-waves aria-hidden="true"></div>
    <div class="footer__row">
      <small class="footer__nav"><a href="{home}">vokudev.cz</a><a href="{base}jak-funguju/" data-t="navHow">Jak funguju</a><a href="{base}projekty/" data-t="navProjects">Projekty</a><a href="https://github.com/Voku199" rel="me noopener">GitHub</a></small>
      <small>{count} · {round_k(total)} <span data-t="footLines">řádků kódu</span></small>
    </div>
  </div>
</footer>"""


def fill(template, values):
    """Dosadí {{KLÍČE}}. Nedosazený klíč je skoro jistě překlep, proto build skončí chybou."""
    page = template
    for key, val in values.items():
        page = page.replace("{{" + key + "}}", val)
    left = sorted(set(re.findall(r"\{\{[A-Z_0-9]+\}\}", page)))
    if left:
        raise SystemExit(f"v šabloně zůstalo nedosazené: {left}")
    return page


def person(home):
    return {"@type": "Person", "@id": f"{home}#voku", "name": "Vojtěch Kurinec", "alternateName": "Voku", "url": home,
            "image": f"{home}ja_seriozne.webp", "email": "vojta.kurinec@gmail.com", "jobTitle": "Vývojář",
            "address": {"@type": "PostalAddress", "addressRegion": "Jihočeský kraj", "addressCountry": "CZ"},
            "sameAs": ["https://github.com/Voku199", "https://instagram.com/voku199"],
            "knowsAbout": ["Python", "Flask", "JavaScript", "Java", "WebXR", "three.js", "Unity", "Blender",
                           "Raspberry Pi", "3D tisk", "AI"]}


def json_inner(data):
    """Obsah JSON objektu bez závorek, jde dosadit do i18n bloku v šabloně."""
    return json.dumps(data, ensure_ascii=False)[1:-1].replace("</", "<\\/")


def build_home(items, total):
    """Úvodní stránka: texty ručně v šabloně, čísla a projekty k vyzkoušení (pole featured) z buildu."""
    featured = sorted((p for p in items if p.get("featured")), key=lambda p: p["featured"])
    for p in featured:
        if not (p.get("url") and p.get("try_cs") and p.get("try_en")):
            raise SystemExit(f"{p['slug']}: projekt na úvodní stránce potřebuje url, try_cs a try_en")
    if not featured:
        raise SystemExit("v projects_data.py není žádný projekt s polem featured")
    n = len(featured)
    home, how, archive = f"{D.SITE_URL}/", f"{D.SITE_URL}/jak-funguju/", f"{D.SITE_URL}/projekty/"
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "@id": f"{home}#web", "url": home, "name": "Voku", "inLanguage": ["cs", "en"],
         "publisher": {"@id": f"{home}#voku"}},
        person(home),
        {"@type": "ProfilePage", "@id": f"{home}#page", "url": home, "inLanguage": "cs",
         "name": "Vojtěch \"Voku\" Kurinec | Mladý vývojář z jižních Čech",
         "isPartOf": {"@id": f"{home}#web"}, "mainEntity": {"@id": f"{home}#voku"},
         "primaryImageOfPage": f"{home}og-image.png",
         "hasPart": [{"@type": "WebPage", "@id": f"{how}#page", "url": how},
                     {"@type": "CollectionPage", "@id": f"{archive}#page", "url": archive}],
         "about": {"@type": "ItemList", "numberOfItems": n, "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "url": p["url"], "name": p["name"]}
             for i, p in enumerate(featured)]}},
    ]}
    extra = {"try": {p["slug"]: [p["try_cs"], p["try_en"]] for p in featured},
             "note": {p["slug"]: [p["note_cs"], p["note_en"]] for p in featured if p.get("note_cs")}}
    page = fill(HOME_TEMPLATE.read_text(encoding="utf-8"), {
        "HEAD": head_html(""), "NAV": nav_html("", "home"), "FOOTER": footer_html("", total, f"{len(items)} projektů"),
        "V": asset_version(), "SITE_URL": D.SITE_URL, "COUNT": str(len(items)), "LINES": round_k(total),
        "FEATURED": "".join(featured_html(i, p) for i, p in enumerate(featured)),
        "I18N_EXTRA": json_inner(extra),
        "JSONLD": json.dumps(jsonld, ensure_ascii=False, indent=1),
    })
    write_if_changed(SITE / "index.html", page)
    return featured


def build_how(items, total):
    """/jak-funguju/: texty ručně v šabloně, počty z buildu. Mrtvý odkaz na projekt zastaví build."""
    known = {p["slug"] for p in items}
    template = HOW_TEMPLATE.read_text(encoding="utf-8")
    for slug in re.findall(r"projekty/#([a-z0-9-]+)", template + HOME_TEMPLATE.read_text(encoding="utf-8")):
        if slug not in known:
            raise SystemExit(f"odkaz na neexistující projekt: {slug}")
    home, url = f"{D.SITE_URL}/", f"{D.SITE_URL}/jak-funguju/"
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": f"{url}#page", "url": url, "inLanguage": "cs",
         "name": "Jak funguju, když dostanu zakázku", "isPartOf": {"@id": f"{home}#web"},
         "about": {"@id": f"{home}#voku"}, "primaryImageOfPage": f"{home}og-image.png",
         "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
             {"@type": "ListItem", "position": 1, "name": "Voku", "item": home},
             {"@type": "ListItem", "position": 2, "name": "Jak funguju", "item": url}]}},
    ]}
    page = fill(template, {
        "HEAD": head_html("../"), "NAV": nav_html("../", "how"), "FOOTER": footer_html("../", total, f"{len(items)} projektů"),
        "V": asset_version(), "SITE_URL": D.SITE_URL, "COUNT": str(len(items)),
        "JSONLD": json.dumps(jsonld, ensure_ascii=False, indent=1),
    })
    HOW_FILE.parent.mkdir(exist_ok=True)
    write_if_changed(HOW_FILE, page)


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
    live = sum(1 for p in items if p["status"] == "live")

    print(f"{len(items)} projektů, {total} řádků, {langs} jazyků, {live} běží naostro, {sum(1 for p in items if p.get('demo'))} živá dema")
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
    can_try = sum(1 for p in items if p.get("url") and (p.get("demo") or p.get("featured")))
    filters = '<button type="button" class="on" data-f="all" aria-pressed="true"><span data-t="all">Vše</span> <i>{}</i></button>'.format(len(items))
    filters += f'<button type="button" data-f="try" aria-pressed="false"><span data-t="liveFilter">Jde vyzkoušet</span> <i>{can_try}</i></button>'
    filters += "".join(f'<button type="button" data-f="{k}" aria-pressed="false"><span data-cat-label="{k}">{escape(cs)}</span> <i>{counts[k]}</i></button>'
                       for k, (cs, _) in cats.items() if counts[k])
    # jeden znak = jeden projekt, barva a značka podle kategorie
    catbar = "".join(f'<span style="color:{CAT_MARKS[k][1]}">{CAT_MARKS[k][0] * counts[k]}</span>'
                     for k in cats if counts[k])

    i18n = {"cats": cats, "p": {p["slug"]: [p["cs"], p["en"]] for p in items},
            "try": {p["slug"]: [p["try_cs"], p["try_en"]] for p in items if p.get("try_cs")},
            "note": {p["slug"]: [p["note_cs"], p["note_en"]] for p in items if p.get("note_cs")}}
    today = date.today()
    home, how, page_url = f"{D.SITE_URL}/", f"{D.SITE_URL}/jak-funguju/", f"{D.SITE_URL}/projekty/"
    author = {"@id": f"{home}#voku"}
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "@id": f"{page_url}#page", "url": page_url,
         "name": "Projekty | Vojtěch \"Voku\" Kurinec", "inLanguage": "cs",
         "description": f"Všech {len(items)} projektů Vojtěcha Kurince: weby, hry, AI nástroje a servery.",
         "isPartOf": {"@id": f"{home}#web"}, "author": author, "dateModified": today.isoformat(),
         "primaryImageOfPage": f"{page_url}og.png",
         "breadcrumb": {"@id": f"{page_url}#breadcrumb"}, "mainEntity": {"@id": f"{page_url}#list"}},
        {"@type": "BreadcrumbList", "@id": f"{page_url}#breadcrumb", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Voku", "item": home},
            {"@type": "ListItem", "position": 2, "name": "Projekty", "item": page_url}]},
        {"@type": "ItemList", "@id": f"{page_url}#list", "numberOfItems": len(items), "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "item": {
                "@type": "CreativeWork", "@id": f"{page_url}#{p['slug']}", "name": p["name"],
                "description": p["cs"], "creator": author, "keywords": ", ".join(p["stack"]),
                "dateModified": datetime.fromtimestamp(p["updated"]).strftime("%Y-%m-%d"),
                "image": f"{page_url}shots/{p['image']}",
                **({"url": p["url"]} if p["url"] else {})}}
            for i, p in enumerate(items)]},
    ]}
    page = fill(TEMPLATE.read_text(encoding="utf-8"), {
        "HEAD": head_html("../"), "NAV": nav_html("../", "projects"), "FOOTER": footer_html("../", total, f"{len(items)} projektů"),
        "V": asset_version(), "SITE_URL": D.SITE_URL, "COUNT": str(len(items)), "LINES": round_k(total),
        "LANGS": str(langs), "LIVE": str(live), "UPDATED_CS": f"{today.day}. {today.month}. {today.year}",
        "FILTERS": filters, "CATBAR": catbar,
        "CARDS": "".join(card_html(i, p, cats) for i, p in enumerate(items)),
        "I18N_EXTRA": json_inner(i18n),
        "JSONLD": json.dumps(jsonld, ensure_ascii=False, indent=1),
    })
    write_if_changed(OUT / "index.html", page)

    public = [{"name": p["name"], "slug": p["slug"], "category": p["cat"], "cs": p["cs"], "en": p["en"],
               "url": p["url"], "demo": bool(p.get("demo")), "status": p["status"], "stack": p["stack"],
               "lines": p["lines"], "tests": p["tests"],
               "updated": datetime.fromtimestamp(p["updated"]).strftime("%Y-%m-%d"),
               "image": f"{D.SITE_URL}/projekty/shots/{p['image']}"} for p in items]
    (OUT / "projects.json").write_text(json.dumps({"generated": today.isoformat(), "projects": public},
                                                  ensure_ascii=False, indent=1), encoding="utf-8", newline="")

    # soubor se mění jen když se opravdu změní -> poctivé lastmod
    featured = build_home(items, total)
    build_how(items, total)
    home_mod = date.fromtimestamp((SITE / "index.html").stat().st_mtime).isoformat()
    how_mod = date.fromtimestamp(HOW_FILE.stat().st_mtime).isoformat()

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
    <loc>{how}</loc>
    <lastmod>{how_mod}</lastmod>
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
             f"- [Úvod]({home}): kdo jsem, co jsem dokázal, proč to dělám, jak pracuju, co mám rád a kontakt. "
             "Projekty, které si můžeš hned vyzkoušet: " + ", ".join(p["name"] for p in featured),
             f"- [Jak funguju]({how}): co přesně udělám, když dostanu zakázku, krok po kroku",
             f"- [Projekty]({page_url}): všechny projekty s popisem a technologiemi",
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
    print(f"  -> index.html, jak-funguju/index.html, projekty/index.html, projects.json, sitemap.xml, llms.txt, {len(used)} obrázků")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--from-json", action="store_true", help="bez monorepa, čísla z projekty/projects.json")
    a = ap.parse_args()
    build(a.root, a.check, a.from_json)
