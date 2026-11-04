#!/bin/bash
# Rozdělí /etc/caddy/Caddyfile na soubory v /etc/caddy/sites/, jeden na projekt. Spouští se jednou,
# až když běží nový blok webu z caddy-vokudev.sh.
#   bash deploy/caddy-rozdelit.sh --nanecisto   ukáže, co vznikne, a ověří to, nic nemění, sudo netřeba
#   sudo bash deploy/caddy-rozdelit.sh          provede
#
# Bloky přesouvá beze změny. Přepíše je jen to, co je v deploy/sites/ (lol.caddy přidává lol.vokudev.cz)
# a deploy/vokudev.caddy. Když některá adresa zmizí nebo reload selže, vrátí původní stav.
set -euo pipefail

HERE="$(dirname "$(readlink -f "$0")")"
CF=/etc/caddy/Caddyfile
SITES=/etc/caddy/sites
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

[ ! -e "$SITES" ] || { echo "$SITES už existuje, Caddyfile je rozdělený. Nic nedělám."; exit 1; }

adapt() { caddy adapt --config "$1" --adapter caddyfile 2>/dev/null; }

python3 "$HERE/caddy_tool.py" split "$CF" "$TMP/sites"
grep -v '^#' "$HERE/vokudev.caddy" > "$TMP/sites/vokudev.caddy"
for f in "$HERE"/sites/*.caddy; do
  cp "$f" "$TMP/sites/"
  echo "  $(basename "$f"): z deploy/sites/"
done

# kandidát s importem do dočasné složky, ať jde ověřit ještě před zásahem do /etc/caddy
sed "s#$SITES/#$TMP/sites/#" "$HERE/Caddyfile.main" > "$TMP/Caddyfile"
caddy validate --config "$TMP/Caddyfile" --adapter caddyfile >"$TMP/validate.log" 2>&1 || {
  tail -5 "$TMP/validate.log"
  echo "CHYBA: nová konfigurace neprošla validací, nic jsem nezměnil."
  exit 1
}
adapt "$CF" > "$TMP/old.json"
adapt "$TMP/Caddyfile" > "$TMP/new.json"
python3 "$HERE/caddy_tool.py" compare "$TMP/old.json" "$TMP/new.json"

if [ "${1:-}" = "--nanecisto" ]; then
  echo "OK nanečisto: konfigurace je platná, nic jsem nezměnil."
  exit 0
fi

[ "$EUID" -eq 0 ] || { echo "Spust pres sudo: sudo bash $0  (nebo zkus --nanecisto)"; exit 1; }

BAK="$CF.bak-$(date +%Y%m%d-%H%M%S)"
cp "$CF" "$BAK"
install -d -m 755 "$SITES"
install -m 644 "$TMP"/sites/*.caddy "$SITES/"
install -m 644 "$HERE/Caddyfile.main" "$CF"

vrat() {
  cp "$BAK" "$CF"
  rm -rf "$SITES"
  systemctl reload caddy || true
  echo "CHYBA: $1, vrácen původní Caddyfile ze zálohy $BAK"
  exit 1
}
caddy validate --config "$CF" --adapter caddyfile >"$TMP/validate.log" 2>&1 || { tail -5 "$TMP/validate.log"; vrat "validace selhala"; }
systemctl reload caddy || vrat "reload selhal"
echo "OK: rozděleno do $SITES, záloha $BAK"
