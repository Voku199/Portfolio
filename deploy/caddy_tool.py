#!/usr/bin/env python3
"""Pomocník pro skripty v deploy/. Sám na serveru nic nemění, zapisuje jen do zadané složky.

    caddy_tool.py split Caddyfile SLOZKA   rozdělí bloky do SLOZKA/<jmeno>.caddy
    caddy_tool.py compare stary.json novy.json
                                           porovná adresy ve výstupu `caddy adapt`, když nějaká zmizí, skončí chybou

Split bere jen obyčejné bloky adres. Na cokoli jiného (globální volby, snippety, import, http://)
skončí chybou, takže se nikdy nestane, že by část konfigurace tiše zmizela.
"""
import json
import pathlib
import re
import sys

HLAVNI_WEB = {"vokudev.cz", "www.vokudev.cz"}     # ty nahrazuje deploy/vokudev.caddy
ZKRATIT = (".bakix.cz", ".vokudev.cz")
ADRESA = re.compile(r"^[a-z0-9*][a-z0-9.*-]*$")


def bloky(text):
    """Vrátí seznam (adresy, řádky). Komentář nad blokem patří k bloku."""
    vysledek, komentare, aktualni, hloubka = [], [], None, 0
    for cislo, radek in enumerate(text.splitlines(), 1):
        s = radek.strip()
        je_komentar = s.startswith("#")
        if aktualni is None:
            if not s:
                continue
            if je_komentar:
                komentare.append(radek)
                continue
            if not s.endswith("{"):
                raise SystemExit(f"CHYBA, řádek {cislo}: čekal jsem hlavičku bloku, našel jsem: {s}")
            adresy = [a for a in re.split(r"[,\s]+", s[:-1]) if a]
            if not adresy or not all(ADRESA.match(a) for a in adresy):
                raise SystemExit(f"CHYBA, řádek {cislo}: tohle neumím bezpečně přesunout: {s}")
            aktualni = (adresy, komentare + [radek])
            komentare, hloubka = [], 1
            continue
        aktualni[1].append(radek)
        if not je_komentar:
            hloubka += s.count("{") - s.count("}")
        if hloubka == 0:
            vysledek.append(aktualni)
            aktualni = None
    if aktualni is not None or hloubka != 0:
        raise SystemExit("CHYBA: neuzavřený blok na konci souboru")
    if komentare:
        raise SystemExit("CHYBA: komentář na konci souboru bez bloku: " + komentare[0])
    return vysledek


def jmeno_souboru(prvni_adresa, obsazeno):
    jmeno = prvni_adresa
    for pripona in ZKRATIT:
        if jmeno.endswith(pripona):
            jmeno = jmeno[: -len(pripona)]
            break
    return prvni_adresa if jmeno in obsazeno else jmeno


def split(caddyfile, slozka):
    cil = pathlib.Path(slozka)
    cil.mkdir(parents=True, exist_ok=True)
    obsazeno = set()
    for adresy, radky in bloky(pathlib.Path(caddyfile).read_text(encoding="utf-8")):
        if set(adresy) <= HLAVNI_WEB:
            print(f"  {', '.join(adresy)}: nahradí vokudev.caddy")
            continue
        jmeno = jmeno_souboru(adresy[0], obsazeno)
        obsazeno.add(jmeno)
        (cil / f"{jmeno}.caddy").write_text("\n".join(radky) + "\n", encoding="utf-8")
        print(f"  {', '.join(adresy)} -> {jmeno}.caddy")


def adresy_z_adapt(cesta):
    data = json.loads(pathlib.Path(cesta).read_text(encoding="utf-8"))
    nalezeno = set()
    for server in data.get("apps", {}).get("http", {}).get("servers", {}).values():
        for routa in server.get("routes", []):
            for podminka in routa.get("match", []):
                nalezeno.update(podminka.get("host", []))
    return nalezeno


def compare(stary, novy):
    stare, nove = adresy_z_adapt(stary), adresy_z_adapt(novy)
    print(f"  adresy: {len(stare)} -> {len(nove)}")
    for a in sorted(nove - stare):
        print(f"  přibude: {a}")
    chybi = sorted(stare - nove)
    for a in chybi:
        print(f"  ZMIZÍ: {a}")
    if chybi:
        raise SystemExit("CHYBA: nová konfigurace by přišla o adresy")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "split":
        split(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 4 and sys.argv[1] == "compare":
        compare(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
