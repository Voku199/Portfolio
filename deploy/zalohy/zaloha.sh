#!/bin/bash
# Denní záloha dat z RPi přes restic. Instaluje ji instalace.sh jako /usr/local/sbin/vokudev-zaloha.
#   bash zaloha.sh --nanecisto    zkusí kopie SQLite a vypíše, co by šlo do zálohy, sudo netřeba
#   sudo vokudev-zaloha           zazálohuje do všech cílů v /etc/vokudev/restic-*.env
#
# Každý soubor restic-*.env je jeden cíl (RESTIC_REPOSITORY + RESTIC_PASSWORD), takže kopii mimo dům
# přidáš dalším souborem.
set -euo pipefail

ZDROJE=(/home/voku /etc/caddy /etc/systemd/system /etc/vokudev /var/lib/vokudev)
VYNECHAT=(venv .venv node_modules __pycache__ .cache .npm .ollama .local /home/voku/backups)
NAJDI_DB=(-name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3')

existujici() { for z in "${ZDROJE[@]}"; do [ -e "$z" ] && echo "$z"; done; return 0; }

# Živá SQLite se nesmí kopírovat jen tak, proto konzistentní kopie přes backup API
kopie_sqlite() {
  local cil="$1" prune=() v
  for v in "${VYNECHAT[@]}"; do
    case "$v" in /*) prune+=(-path "$v" -o) ;; *) prune+=(-name "$v" -o) ;; esac
  done
  unset 'prune[${#prune[@]}-1]'
  existujici | while read -r zdroj; do
    find "$zdroj" -xdev \( "${prune[@]}" \) -prune -o -type f \( "${NAJDI_DB[@]}" \) -size +0 -print 2>/dev/null
  done | python3 -c '
import pathlib, sqlite3, sys
cil = pathlib.Path(sys.argv[1])
ok = bad = 0
for radek in sys.stdin:
    db = radek.rstrip("\n")
    kam = cil / db.lstrip("/")
    kam.parent.mkdir(parents=True, exist_ok=True)
    try:
        src = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=20)
        dst = sqlite3.connect(kam)
        with dst:
            src.backup(dst)
        src.close(); dst.close()
        ok += 1
    except sqlite3.Error as e:
        kam.unlink(missing_ok=True)
        print(f"  SQLite nešla zkopírovat: {db}: {e}", file=sys.stderr)
        bad += 1
print(f"  SQLite: {ok} zkopírováno, {bad} selhalo")
sys.exit(1 if bad else 0)
' "$cil"
}

DB="$(mktemp -d /var/tmp/zaloha-db.XXXXXX)"
trap 'rm -rf "$DB"' EXIT
chmod 700 "$DB"

if [ "${1:-}" = "--nanecisto" ]; then
  kopie_sqlite "$DB" || echo "  (bez sudo některé databáze nejdou číst, to je tady v pořádku)"
  echo "Zdroje:"; existujici | sed 's/^/  /'
  echo "Vynechat:"; printf '  %s\n' "${VYNECHAT[@]}"
  du -sh "$DB" | sed 's/^/Kopie databází: /'
  echo "OK nanečisto: nic se nezálohovalo."
  exit 0
fi

[ "$EUID" -eq 0 ] || { echo "Spust pres sudo: sudo $0  (nebo zkus --nanecisto)"; exit 1; }

chyba=0
kopie_sqlite "$DB" || chyba=1

vynechat=()
for v in "${VYNECHAT[@]}"; do vynechat+=(--exclude "$v"); done
mapfile -t zdroje < <(existujici)

shopt -s nullglob
cile=(/etc/vokudev/restic-*.env)
[ "${#cile[@]}" -gt 0 ] || { echo "CHYBA: v /etc/vokudev/ není žádný restic-*.env"; exit 1; }
for env in "${cile[@]}"; do
  echo "== $(basename "$env")"
  (
    set -a; . "$env"; set +a
    restic backup --one-file-system --tag denni "${vynechat[@]}" "${zdroje[@]}" "$DB"
    restic forget --tag denni --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
  ) || { echo "CHYBA: záloha do $(basename "$env") selhala"; chyba=1; }
done
exit "$chyba"
