"""Namaluje impresionistické SVG pro portfolio: hero obraz, key art, ilustrace sekcí.

    python tools/paint.py        ->  img/*.svg

Stejný princip jako v LID: všechno jsou krátké „tahy štětcem" (zakulacené
obdélníky v náhodném úhlu) + SVG filtr, který okraje rozvlní jako barvu na
plátně. Ilustrace sekcí jsou naivní perokresba přes namalovanou skvrnu, kreslená
dvakrát s jiným rozvlněním, ať čára vypadá jako od ruky. Náhoda má pevné
semínko, takže každé spuštění dá stejný výsledek.
"""
import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "img"

INK = "#141413"
PAPER = "#FAF9F5"
IVORY = "#F0EEE6"

CLAY = ["#D97757", "#CC785C", "#E08A68", "#C8664A"]
KRAFT = ["#D4A27F", "#DDB592", "#C9956F", "#E3BE9A"]
MANILLA = ["#EBDBBC", "#F2E6CC", "#E4D0AA", "#F4E6CC"]
OLIVE = ["#788C5D", "#8A9C6C", "#6A7D52", "#9AAA7C"]
SKY = ["#6A9BCC", "#8DB3D9", "#A9C5E0", "#7FA6CF"]
HEATHER = ["#CBCADB", "#BDBBD3", "#D6D0DE"]
SUN = ["#E8A15A", "#F0B46E", "#D98A45", "#F5C88A"]


def rough(fid, scale, freq=0.035, seed=7, octaves=2):
    return (
        f'<filter id="{fid}" x="-5%" y="-5%" width="110%" height="110%">'
        f'<feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="{octaves}" seed="{seed}" result="n"/>'
        f'<feDisplacementMap in="SourceGraphic" in2="n" scale="{scale}" xChannelSelector="R" yChannelSelector="G"/>'
        f"</filter>"
    )


def dab(x, y, length, angle, color, opacity=1.0):
    t = length * 0.42
    op = f' opacity="{opacity:.2f}"' if opacity < 0.995 else ""
    return (
        f'<rect x="{-length / 2:.1f}" y="{-t / 2:.1f}" width="{length:.1f}" height="{t:.1f}" rx="{t / 2:.1f}" '
        f'fill="{color}"{op} transform="translate({x:.1f} {y:.1f}) rotate({angle:.0f})"/>'
    )


def stroke(x1, y1, x2, y2, width, color, opacity=1.0):
    op = f' opacity="{opacity:.2f}"' if opacity < 0.995 else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
        f'stroke-width="{width:.1f}" stroke-linecap="round"{op}/>'
    )


def dabs(r, box, colors, n, length, angle, spread=50, warm=None, opacity=(0.75, 1.0)):
    """n tahů v obdélníku box=(x, y, w, h). warm=(barvy, cx, cy, poloměr) přidá teplé světlo od slunce."""
    x0, y0, w, h = box
    out = []
    for _ in range(n):
        x, y = x0 + r.random() * w, y0 + r.random() * h
        color = r.choice(colors)
        if warm and (x - warm[1]) ** 2 + (y - warm[2]) ** 2 < warm[3] ** 2 and r.random() < 0.35:
            color = r.choice(warm[0])
        out.append(dab(x, y, length[0] + r.random() * (length[1] - length[0]),
                       angle + (r.random() - 0.5) * spread, color,
                       opacity[0] + r.random() * (opacity[1] - opacity[0])))
    return out


def ellipse_dabs(r, cx, cy, rx, ry, colors, n, length, angle=0, spread=70, opacity=(0.8, 1.0)):
    """Tahy rozházené uvnitř elipsy (koruna stromu, záře, skvrna)."""
    out = []
    for _ in range(n):
        a, d = r.random() * math.tau, math.sqrt(r.random())
        out.append(dab(cx + math.cos(a) * rx * d, cy + math.sin(a) * ry * d,
                       length[0] + r.random() * (length[1] - length[0]),
                       angle + (r.random() - 0.5) * spread, r.choice(colors),
                       opacity[0] + r.random() * (opacity[1] - opacity[0])))
    return out


def sky_bands(r, bands, width, top, height, per_band, length):
    band_h = height / len(bands)
    out = []
    for i, colors in enumerate(bands):
        y = top + i * band_h - band_h * 0.25
        out += dabs(r, (-30, y, width + 60, band_h * 1.5), colors, per_band, length, (r.random() - 0.5) * 8, spread=14)
    return out


def gradient(gid, bands):
    stops = "".join(f'<stop offset="{i / (len(bands) - 1):.2f}" stop-color="{b[0]}"/>' for i, b in enumerate(bands))
    return f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">{stops}</linearGradient>'


def svg(width, height, defs, body, extra=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}"{extra}>'
        f"<defs>{''.join(defs)}</defs>{''.join(body)}</svg>\n"
    )


# ---------- hero: jihočeský rybník za úsvitu ----------

def hero(width=960, height=1200, seed=21):
    r = random.Random(seed)
    horizon, sun_x, sun_y, sun_r = 690, 630, 610, 66
    bands = [
        ["#A9C5E0", "#B8CFE4", "#9DBBDA", "#C3D5E6"],
        ["#CBCADB", "#D6D0DE", "#E3D6D6", "#C9C8DC"],
        ["#EBDBBC", "#F2E1C4", "#EED3B5", "#F4E6CC"],
        ["#F0C08E", "#EBB384", "#F4CDA0", "#E8A878"],
    ]
    sea = ["#9DBBDA", "#A9C5E0", "#8DB3D9", "#BDBBD3", "#B3C4D9"]
    sea_light = ["#EBDBBC", "#F2E1C4", "#F0C08E"]
    trees = ["#4F5E3C", "#5E6E46", "#6A7D52", "#44523A", "#56653F"]
    defs = [
        rough("f", 11, freq=0.013),
        gradient("g", bands),
        f'<clipPath id="s"><circle cx="{sun_x}" cy="{sun_y}" r="{sun_r}"/></clipPath>',
    ]
    body = [f'<rect width="{width}" height="{horizon}" fill="url(#g)"/>',
            f'<rect y="{horizon}" width="{width}" height="{height - horizon}" fill="{sea[0]}"/>',
            '<g filter="url(#f)">']
    body += sky_bands(r, bands, width, 0, horizon, 150, (54, 110))

    # slunce a záře kolem
    body.append(f'<g clip-path="url(#s)"><rect x="{sun_x - sun_r}" y="{sun_y - sun_r}" '
                f'width="{2 * sun_r}" height="{2 * sun_r}" fill="#FBE3B0"/>')
    body += dabs(r, (sun_x - sun_r, sun_y - sun_r, 2 * sun_r, 2 * sun_r), ["#FBE3B0", "#FFF0CF", "#F8D9A8", "#F5C88A"], 80, (16, 30), 10)
    body.append("</g>")
    for _ in range(46):
        x, y = sun_x + (r.random() - 0.5) * 560, sun_y - 70 + r.random() * 120
        body.append(stroke(x - 32, y, x + 32, y, 9, r.choice(SUN + KRAFT[:2]), 0.3))

    # hráz s duby: koruny jako shluky tahů, strana ke slunci teplejší
    x = -30
    while x < width + 30:
        near_sun = abs(x - sun_x) < 140
        h = (26 + r.random() * 30) if near_sun else (60 + r.random() * 90)
        w = 50 + r.random() * 60
        cy = horizon - h / 2 + 6
        body += ellipse_dabs(r, x, cy, w / 2, h / 2, trees, int(w * h / 170), (14, 26), 90, 120)
        lit = KRAFT[:2] + ["#B9A06A"]
        body += ellipse_dabs(r, x + (w / 4 if x < sun_x else -w / 4), cy - h / 6, w / 4, h / 3, lit,
                             int(w * h / 900) + 2, (8, 16), 90, 120, (0.5, 0.8))
        x += w * (0.55 + r.random() * 0.3)
    for _ in range(140):  # hráz pod stromy
        x = r.random() * width
        body.append(stroke(x, horizon + 2 + r.random() * 6, x + 30 + r.random() * 40,
                           horizon + 2 + r.random() * 6, 6, r.choice(trees), 0.9))

    # voda: vodorovné tahy, nahoře odraz stromů, odraz slunce se směrem dolů rozpadá
    y = horizon + 12
    row = 0
    while y < height + 10:
        x = -20
        while x < width + 20:
            length = 40 + r.random() * 70
            if row < 4 and r.random() < 0.5:
                color = r.choice(trees)
            elif r.random() < 0.14:
                color = r.choice(sea_light)
            else:
                color = r.choice(sea)
            body.append(stroke(x, y + (r.random() - 0.5) * 3, x + length, y + (r.random() - 0.5) * 3,
                               7 + row * 0.16, color, 0.85 + r.random() * 0.15))
            x += length + 6 + r.random() * 10
        spread = 70 + row * 8
        for _ in range(max(2, 7 - row // 7)):
            cx = sun_x + (r.random() - 0.5) * spread
            length = 22 + r.random() * 46
            body.append(stroke(cx - length / 2, y, cx + length / 2, y, 7 + row * 0.16,
                               r.choice(SUN + CLAY[:1]), max(0.35, 1 - row * 0.02)))
        y += 9 + row * 0.4
        row += 1

    # rákosí v popředí, pár orobinců
    reeds = OLIVE + KRAFT[:2] + ["#5E6E46", "#B9A06A"]
    for x0, x1, top in ((-10, 300, 930), (760, 980, 1010)):
        for _ in range(int((x1 - x0) * 0.55)):
            x = x0 + r.random() * (x1 - x0)
            y_top = top + r.random() * 180
            lean = (r.random() - 0.4) * 50
            body.append(stroke(x, height + 10, x + lean, y_top, 3 + r.random() * 2.5, r.choice(reeds), 0.9))
        for _ in range(int((x1 - x0) / 45)):
            x, y_top = x0 + r.random() * (x1 - x0), top - 30 + r.random() * 120
            body.append(stroke(x, y_top + 70, x + 2, y_top - 6, 2.5, r.choice(OLIVE)))
            body.append(stroke(x + 1, y_top + 4, x + 1.5, y_top + 30, 9, "#7A5636"))
    body.append("</g>")
    return svg(width, height, defs, body, ' preserveAspectRatio="xMidYMid slice"')


# ---------- Sparks of Silt: Zaun za soumraku, krystal nad bahnem ----------

def sparks(width=800, height=600, seed=33):
    r = random.Random(seed)
    horizon, cx, cy = 400, 400, 225
    bands = [
        ["#2A2440", "#30294A", "#262038", "#352C52"],
        ["#3A3358", "#43395F", "#3A3D62", "#4A3F66"],
        ["#4F4A70", "#5B4E72", "#4B5878", "#665374"],
        ["#6E5F7E", "#8A6A78", "#5F7A88", "#9A7268"],
    ]
    towers = ["#221D33", "#2A2440", "#1E1A2C", "#2F2945"]
    under = ["#18141F", "#1D1826", "#201A2A"]
    lights = ["#F0B46E", "#E8A15A", "#F5C88A"]
    hextech = ["#7FD3E8", "#BDEBF5", "#4FB3D6", "#E6F8FC", "#3E8FC0"]
    silt = ["#5A4632", "#46372A", "#6B5440", "#3A2E24", "#7A5E44"]
    crystal = f"{cx},{cy - 92} {cx + 44},{cy - 28} {cx + 32},{cy + 56} {cx},{cy + 86} {cx - 32},{cy + 56} {cx - 44},{cy - 28}"
    defs = [rough("f", 8, freq=0.02), gradient("g", bands), f'<clipPath id="c"><polygon points="{crystal}"/></clipPath>']
    body = [f'<rect width="{width}" height="{height}" fill="url(#g)"/>', '<g filter="url(#f)">']
    body += sky_bands(r, bands, width, 0, horizon, 100, (36, 70))
    body += ellipse_dabs(r, 640, 330, 170, 110, ["#C46686", "#D97A9A", "#A85A7E"], 70, (20, 40), 0, 40, (0.2, 0.4))

    # horní město: věže ze svislých tahů, sem tam okno
    x = -10
    while x < width + 10:
        w, h = 22 + r.random() * 40, 50 + r.random() * 200
        if abs(x - cx) < 70:
            h *= 0.45
        base = r.choice(towers)
        body.append(f'<rect x="{x:.1f}" y="{horizon - h:.1f}" width="{w:.1f}" height="{h + 4:.1f}" fill="{base}"/>')
        if r.random() < 0.5:  # špička věže
            body.append(f'<path d="M{x + w * .2:.1f} {horizon - h:.1f} L{x + w / 2:.1f} {horizon - h - 18 - r.random() * 24:.1f} '
                        f'L{x + w * .8:.1f} {horizon - h:.1f}Z" fill="{base}"/>')
        for _ in range(int(w * h / 420)):
            px, py = x + 4 + r.random() * (w - 8), horizon - r.random() * h
            body.append(dab(px, py, 12 + r.random() * 14, 90 + (r.random() - 0.5) * 6, r.choice(towers)))
        for _ in range(int(h / 40)):
            if r.random() < 0.6:
                body.append(dab(x + 4 + r.random() * (w - 8), horizon - 8 - r.random() * (h - 16), 5, 0,
                                r.choice(lights), 0.85))
        x += w + 2 + r.random() * 10
    # dolní město (Zaun), blíž a tmavší
    x = -10
    while x < width + 10:
        w, h = 30 + r.random() * 50, 20 + r.random() * 70
        body.append(f'<rect x="{x:.1f}" y="{horizon + 30 - h:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{r.choice(under)}"/>')
        body += dabs(r, (x, horizon + 30 - h, w, h), under, int(w * h / 300), (12, 22), 90, 10)
        if r.random() < 0.5:
            body.append(dab(x + r.random() * w, horizon + 20 - r.random() * h * 0.7, 5, 0, r.choice(lights), 0.9))
        x += w + r.random() * 6

    # záře a hextech krystal
    for _ in range(60):
        a, d = r.random() * math.tau, 60 + r.random() * 120
        x, y = cx + math.cos(a) * d, cy + math.sin(a) * d * 0.8
        body.append(stroke(x, y, x + math.cos(a) * 26, y + math.sin(a) * 26, 7, r.choice(hextech), 0.22))
    body.append(f'<g clip-path="url(#c)"><rect x="{cx - 50}" y="{cy - 95}" width="100" height="185" fill="#4FB3D6"/>')
    body += dabs(r, (cx - 50, cy - 95, 100, 185), hextech, 110, (10, 22), 60, 80)
    body.append("</g>")

    # bahno: vodorovné tahy, pod krystalem jeho odraz
    y = horizon + 26
    row = 0
    while y < height + 10:
        x = -20
        while x < width + 20:
            length = 30 + r.random() * 60
            color = r.choice(silt)
            if abs(x - cx) < 70 - row * 2 and r.random() < 0.5:
                color = r.choice(hextech[:3])
            elif r.random() < 0.05:
                color = r.choice(CLAY)
            body.append(stroke(x, y + (r.random() - 0.5) * 3, x + length, y + (r.random() - 0.5) * 3,
                               8 + row * 0.2, color, 0.9))
            x += length + 4 + r.random() * 8
        y += 9 + row * 0.5
        row += 1
    body.append("</g>")
    return svg(width, height, defs, body, ' preserveAspectRatio="xMidYMid slice"')


# ---------- Respawn: plátno pod 3D phaser, modrý a červený tým ----------

def respawn(width=800, height=600, seed=44):
    r = random.Random(seed)
    blue = ["#6A9BCC", "#4C8FD6", "#8DB3D9", "#A9C5E0", "#3D7FC2"]
    red = ["#D97757", "#E0607A", "#CC785C", "#E89A8A", "#C8505E"]
    defs = [rough("f", 10, freq=0.016)]
    body = [f'<rect width="{width}" height="{height}" fill="#E8E4D6"/>', '<g filter="url(#f)">']
    body += dabs(r, (-30, -30, width + 60, height + 60), MANILLA + ["#E8E4D6", "#DCD6C4"], 340, (40, 90), -18, 20)
    for colors, (x0, y0), (x1, y1) in ((blue, (-80, 230), (640, -40)), (red, (160, 660), (880, 360))):
        for i in range(300):  # tahy podél šikmé „vlny"
            t = r.random()
            x = x0 + (x1 - x0) * t + (r.random() - 0.5) * 120
            y = y0 + (y1 - y0) * t + math.sin(t * math.pi) * 60 + (r.random() - 0.5) * 140
            ang = math.degrees(math.atan2(y1 - y0, x1 - x0)) + (r.random() - 0.5) * 30
            body.append(dab(x, y, 26 + r.random() * 50, ang, r.choice(colors), 0.55 + r.random() * 0.4))
    body.append("</g>")
    return svg(width, height, defs, body, ' preserveAspectRatio="xMidYMid slice"')


# ---------- ilustrace sekcí: naivní perokresba přes namalovanou skvrnu ----------

def blob_path(r, cx, cy, radius, wobble=0.12, points=72):
    phase = [r.random() * math.tau for _ in range(3)]
    pts = []
    for i in range(points):
        a = i / points * math.tau
        k = 1 + wobble * (math.sin(2 * a + phase[0]) * 0.6 + math.sin(3 * a + phase[1]) * 0.3
                          + math.sin(5 * a + phase[2]) * 0.15)
        pts.append(f"{cx + math.cos(a) * radius * k:.1f},{cy + math.sin(a) * radius * k * 0.92:.1f}")
    return "M" + "L".join(pts) + "Z"


# Perokresby (viewBox 400×400). Každá položka: (d, fill). fill=None -> jen čára.
DRAWINGS = {
    # rašící rostlinka v dlani
    "sprout": [
        ("M140 336 Q200 350 266 336 L262 382 L142 382 Z", PAPER),
        ("M98 236 Q104 306 200 312 Q292 306 306 242 Q262 262 200 262 Q140 262 98 236 Z", PAPER),
        ("M98 236 Q84 214 96 198 Q110 190 122 214", None),
        ("M232 254 q10 -15 22 -2 M256 250 q10 -15 22 -2 M280 246 q9 -13 20 -1", None),
        ("M150 306 L146 340 M252 304 L258 338", None),
        ("M156 252 Q200 230 248 252", None),
        ("M200 240 C197 205 204 172 200 128", None),
        ("M200 182 C170 177 146 156 138 124 C168 126 194 146 200 182 Z", PAPER),
        ("M200 182 Q170 154 140 126", None),
        ("M201 154 C226 144 250 118 262 90 C232 94 208 114 201 154 Z", PAPER),
        ("M201 154 Q232 120 260 92", None),
        ("M200 128 q-9 -15 0 -28 q9 13 0 28", PAPER),
    ],
    # dvě ruce si podávají jiskru
    "hands": [
        ("M10 262 L92 238 L104 290 L22 312 Z", PAPER),
        ("M92 238 C124 222 168 222 186 232 C198 240 194 254 180 256 L148 258 C166 264 166 282 150 286 L104 290 Z", PAPER),
        ("M128 236 C134 250 146 256 148 258", None),
        ("M150 268 L120 270 M150 278 L118 282", None),
        ("M390 232 L308 212 L296 264 L378 286 Z", PAPER),
        ("M308 212 C276 196 232 196 214 206 C202 214 206 228 220 230 L252 232 C234 238 234 256 250 260 L296 264 Z", PAPER),
        ("M272 210 C266 224 254 230 252 232", None),
        ("M250 242 L280 244 M250 252 L282 256", None),
        ("M200 150 C203 172 206 178 228 182 C206 186 203 192 200 214 C197 192 194 186 172 182 C194 178 197 172 200 150 Z", PAPER),
        ("M200 118 L200 132 M248 140 L238 150 M152 140 L162 150 M200 232 L200 244", None),
    ],
    # cesta nahoru na kopec s praporkem
    "path": [
        ("M20 330 L380 330", None),
        ("M30 330 C110 312 150 150 228 136 C300 124 338 250 380 312", PAPER),
        ("M84 328 C150 304 118 266 176 236 C226 210 188 182 226 148", "dash"),
        ("M228 138 L228 70", None),
        ("M228 72 L272 84 L228 100 Z", PAPER),
        ("M320 72 m-18 0 a18 18 0 1 0 36 0 a18 18 0 1 0 -36 0", PAPER),
        ("M320 40 L320 30 M344 50 L352 44 M296 50 L288 44", None),
        ("M60 350 l14 0 M110 356 l20 0 M260 352 l18 0 M320 358 l14 0", None),
    ],
    # hrnek se štětcem, tužkou a klíčem
    "tools": [
        ("M174 222 L148 108", None),
        ("M141 92 L156 88 L160 110 L148 113 Z", PAPER),
        ("M146 92 Q138 68 152 56 Q160 74 156 89", PAPER),
        ("M206 220 L214 96 L228 97 L222 221 Z", PAPER),
        ("M214 96 L221 74 L228 97 Z", PAPER),
        ("M240 222 L284 126", None),
        ("M284 126 C268 118 266 96 282 88 L288 102 L300 104 L306 92 C318 104 312 124 296 128 Z", PAPER),
        ("M138 220 L150 340 Q200 354 250 340 L262 220 Q200 236 138 220 Z", PAPER),
        ("M138 220 Q200 206 262 220", None),
        ("M168 280 q32 14 64 0", None),
    ],
    # papírová vlaštovka s klikatou stopou
    "plane": [
        ("M96 222 C46 250 40 318 98 320 C160 322 150 270 112 280 C72 290 44 330 22 366", "dash"),
        ("M96 222 L320 116 L232 290 L196 222 Z", PAPER),
        ("M196 222 L320 116", None),
        ("M196 222 L206 268 L232 250", PAPER),
        ("M300 70 l8 -14 M334 86 l14 -6 M320 60 l2 -16", None),
    ],
    # tři kostky na sobě
    "blocks": [
        ("M84 248 L196 244 L198 340 L86 344 Z", PAPER),
        ("M206 246 L314 250 L310 344 L202 340 Z", PAPER),
        ("M146 158 L250 148 L258 240 L154 250 Z", PAPER),
        ("M140 296 m-18 0 a18 18 0 1 0 36 0 a18 18 0 1 0 -36 0", None),
        ("M240 316 L258 280 L276 316 Z", None),
        ("M188 190 L218 190 M203 176 L203 206", None),
        ("M60 348 L340 348", None),
    ],
}


def drawing(name, blob_colors, seed):
    r = random.Random(seed)
    w = h = 400
    blob = blob_path(r, 200, 214, 150)
    defs = [
        rough("p", 7, freq=0.03, seed=seed % 97),
        rough("a", 2.6, freq=0.045, seed=3),
        rough("b", 3.2, freq=0.04, seed=11),
        f'<clipPath id="k"><path d="{blob}"/></clipPath>',
    ]
    body = ['<g filter="url(#p)">', f'<g clip-path="url(#k)"><rect width="{w}" height="{h}" fill="{blob_colors[0]}"/>']
    body += dabs(r, (40, 50, 320, 330), blob_colors, 210, (22, 38), -25, 40)
    body.append("</g>")
    for _ in range(26):  # pár tahů mimo skvrnu, ať okraj není jako vystřižený
        a = r.random() * math.tau
        d = 150 + r.random() * 26
        body.append(dab(200 + math.cos(a) * d, 214 + math.sin(a) * d * 0.92, 10 + r.random() * 16,
                        math.degrees(a) + 90 + (r.random() - 0.5) * 40, r.choice(blob_colors), 0.7))
    body.append("</g>")

    def ink(fid, width, opacity, dx=0.0, dy=0.0, fills=True):
        g = [f'<g filter="url(#{fid})" fill="none" stroke="{INK}" stroke-width="{width}" stroke-linecap="round" '
             f'stroke-linejoin="round" opacity="{opacity}" transform="translate({dx} {dy})">']
        for d, fill in DRAWINGS[name]:
            extra = ""
            if fill == "dash":
                extra = ' stroke-dasharray="2 12"'
            elif fill and fills:
                extra = f' fill="{fill}"'
            g.append(f'<path d="{d}"{extra}/>')
        g.append("</g>")
        return g

    body += ink("a", 3.4, 1)
    body += ink("b", 1.8, 0.4, 1.6, -1.2, fills=False)  # druhý, slabší tah – jako by se ruka vracela
    return svg(w, h, defs, body)


# ---------- drobnosti ----------

def brush():
    r = random.Random(5)
    body = ['<g filter="url(#f)">']
    for i, color in enumerate(("#C8664A", "#D97757", "#E08A68")):
        y = 7 + (i - 1) * 1.6
        body.append(f'<path d="M4 {y + 1:.1f} Q 80 {y - 2 + r.random() * 2:.1f} 160 {y:.1f} T 296 {y - 1:.1f}" '
                    f'fill="none" stroke="{color}" stroke-width="{6 - i * 1.2:.1f}" stroke-linecap="round" opacity=".9"/>')
    body.append("</g>")
    return svg(300, 14, [rough("f", 3, freq=0.08)], body, ' preserveAspectRatio="none"')


def favicon():
    r = random.Random(9)
    defs = [rough("f", 3, freq=0.06), f'<clipPath id="k"><path d="{blob_path(r, 32, 33, 21, 0.1)}"/></clipPath>']
    body = [f'<rect width="64" height="64" rx="14" fill="{IVORY}"/>',
            f'<g filter="url(#f)"><g clip-path="url(#k)"><rect width="64" height="64" fill="{CLAY[0]}"/>']
    body += dabs(r, (8, 8, 48, 50), CLAY, 40, (5, 10), -20, 40)
    body.append("</g></g>")
    body.append(f'<text x="32" y="43" font-family="\'Newsreader\',\'Iowan Old Style\',Georgia,serif" '
                f'font-size="30" fill="{INK}" text-anchor="middle">V</text>')
    return svg(64, 64, defs, body)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "hero.svg": hero(),
        "sparks.svg": sparks(),
        "respawn.svg": respawn(),
        "spot-sprout.svg": drawing("sprout", OLIVE, 101),
        "spot-hands.svg": drawing("hands", CLAY, 102),
        "spot-path.svg": drawing("path", KRAFT, 103),
        "spot-tools.svg": drawing("tools", SKY, 104),
        "spot-plane.svg": drawing("plane", CLAY, 105),
        "spot-blocks.svg": drawing("blocks", HEATHER + SKY[2:], 106),
        "brush.svg": brush(),
    }
    for name, text in files.items():
        (OUT / name).write_text(text, encoding="utf-8")
        print(f"{name:18} {len(text) / 1024:6.1f} kB")
    (OUT.parent / "favicon.svg").write_text(favicon(), encoding="utf-8")
    print("favicon.svg        (kořen)")


if __name__ == "__main__":
    main()
