#!/bin/bash
# Nasadí blok hlavního webu z deploy/vokudev.caddy. Spouští se jednou a pak po každé změně bloku.
#   bash deploy/caddy-vokudev.sh --nanecisto    ukáže rozdíl a ověří konfiguraci, nic nemění, sudo netřeba
#   sudo bash deploy/caddy-vokudev.sh           nasadí
#
# Ostatních adres se nedotkne, ani subdomén typu 9b.vokudev.cz. Když některá adresa zmizí, konfigurace
# neprojde validací nebo selže reload, vrátí zálohu. Po rozdělení přes caddy-rozdelit.sh jen vymění
# soubor sites/vokudev.caddy.
set -euo pipefail

HERE="$(dirname "$(readlink -f "$0")")"
CF=/etc/caddy/Caddyfile
SITES=/etc/caddy/sites
NEW="$HERE/vokudev.caddy"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

adapt() { caddy adapt --config "$1" --adapter caddyfile 2>/dev/null; }

# vystup: kandidát konfigurace v $TMP/Caddyfile, importy vedou do $TMP/sites
kandidat() {
  if [ -d "$SITES" ]; then
    cp -r "$SITES" "$TMP/sites"
    grep -v '^#' "$NEW" > "$TMP/sites/vokudev.caddy"
    sed "s#$SITES/#$TMP/sites/#" "$CF" > "$TMP/Caddyfile"
  else
    { awk -f "$HERE/strip-vokudev.awk" "$CF" | cat -s; echo; grep -v '^#' "$NEW"; } > "$TMP/Caddyfile"
  fi
}

kontrola() {
  caddy validate --config "$TMP/Caddyfile" --adapter caddyfile >"$TMP/validate.log" 2>&1 || {
    tail -5 "$TMP/validate.log"
    echo "CHYBA: nová konfigurace neprošla validací"
    return 1
  }
  adapt "$CF" > "$TMP/old.json"
  adapt "$TMP/Caddyfile" > "$TMP/new.json"
  python3 "$HERE/caddy_tool.py" compare "$TMP/old.json" "$TMP/new.json"
}

kandidat

if [ "${1:-}" = "--nanecisto" ]; then
  if [ -d "$SITES" ]; then
    diff -u "$SITES/vokudev.caddy" "$TMP/sites/vokudev.caddy" || true
  else
    diff -u "$CF" "$TMP/Caddyfile" || true
  fi
  kontrola
  echo "OK nanečisto: konfigurace je platná, nic jsem nezměnil."
  exit 0
fi

[ "$EUID" -eq 0 ] || { echo "Spust pres sudo: sudo bash $0  (nebo zkus --nanecisto)"; exit 1; }
kontrola

STAMP="$(date +%Y%m%d-%H%M%S)"
if [ -d "$SITES" ]; then
  BAK="/etc/caddy/vokudev.caddy.bak-$STAMP"
  cp "$SITES/vokudev.caddy" "$BAK"
  CIL="$SITES/vokudev.caddy"
  install -m 644 "$TMP/sites/vokudev.caddy" "$CIL"
else
  BAK="$CF.bak-$STAMP"
  cp "$CF" "$BAK"
  CIL="$CF"
  install -m 644 "$TMP/Caddyfile" "$CIL"
fi

# Caddy musí projít /home/voku a číst web
setfacl -m u:caddy:--x /home/voku
setfacl -R -m u:caddy:rX /home/voku/vokudev

if systemctl reload caddy; then
  echo "OK: Caddy načten, záloha $BAK"
else
  cp "$BAK" "$CIL"
  systemctl reload caddy || true
  echo "CHYBA: reload selhal, vrácena záloha $BAK"
  exit 1
fi
