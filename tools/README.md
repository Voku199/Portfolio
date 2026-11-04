# Nástroje portfolia

| Skript | Co dělá |
|---|---|
| `paint.py` | namaluje obrazy a ilustrace do `img/` |
| `build_projects.py` | postaví `index.html`, `jak-funguju/` a appku `projekty/` ze šablon a monorepa + `sitemap.xml` a `llms.txt` |
| `shoot.py` | vyfotí screenshoty živých webů do `tools/shots/` (Playwright) |

## Projekty (`/projekty/`)

```bash
python tools/shoot.py            # jen když se změnily živé weby
python tools/build_projects.py   # vždycky před pushem, i po změně v assets/ (mění otisk ?v=)
python tools/shoot.py --og       # po buildu: náhled pro sdílení projekty/og.png + apple-touch-icon.png
python tools/build_projects.py --check   # suchý běh: co se najde, jaké technologie
python tools/build_projects.py --from-json   # bez monorepa: čísla z projects.json, texty a odkazy z projects_data.py
```

Build se zastaví, když v monorepu najde míň než 80 % projektů, protože by jinak ořezal archiv a smazal obrázky. Na počítači bez celého monorepa použij `--from-json`.

Build zároveň přegeneruje **SEO soubory**: `sitemap.xml` (s obrázky, `lastmod` hlavní stránky jen když se změnila),
`llms.txt` (přehled pro AI vyhledávače) a JSON-LD stránek (`Person` na úvodní stránce, ostatní se na něj napojují přes `@id`).

- **Ručně** v `projects_data.py`: který projekt se ukáže, název, kategorie, jedna věta CS + EN, odkaz, jestli je to bezpečné živé demo.
- **Samo**: technologie (z `requirements.txt`, `package.json`, `build.gradle` a podpisů v kódu), počet řádků, datum poslední změny, stav „Aktivní“ (změna za posledních 30 dní).
- **Obrázek**: `tools/shots/<slug>.png` → pole `shot` → namalovaná obálka.
- Nová složka v monorepu se na web **nedostane sama**, build ji jen vypíše jako „nezařazenou“. Soukromé složky, jejichž jména nemají být ani ve veřejném repu, patří do `tools/ignore.local.txt` (v `.gitignore`).
- `projekty/index.html` je generovaný, upravuj `projekty.template.html`, `assets/projekty.css` a `assets/projekty.js`.

## Úvodní stránka (`/`) a Jak funguju (`/jak-funguju/`)

Obě se generují, takže needituj `index.html` ani `jak-funguju/index.html`, ale `tools/index.template.html` a `tools/jak-funguju.template.html`. Česky se píše přímo v HTML, anglicky v bloku `<script id="i18n">` dole v šabloně (stejný klíč jako `data-t`). Karty k vyzkoušení určuje pole `featured` v `projects_data.py` (pořadí), věta `try_cs` a `try_en` říká, co tam návštěvník může udělat, a `note_cs` a `note_en` proč to případně nejde hned. Odkaz `projekty/#slug` na neexistující projekt build zastaví.

`o-mne/index.html` je jen přesměrování, aby staré odkazy dál fungovaly.

## Vzhled

| Soubor | Co v něm je |
|---|---|
| `assets/site.css` | barvy (světlý i tmavý režim jako tokeny na `:root`), typografie, sekce |
| `assets/site.js` | tmavý režim, jazyk, odkrývání, kroky na `/jak-funguju/` |
| `assets/ascii.js` | živý ASCII obraz: scéna, palety pro svítání a noc, postupné dokreslování (`stage` 0 až 7) |
| `assets/projekty.*` | appka s projekty |

Tmavý režim: uložená volba, jinak nastavení systému, jinak denní doba (od 20 do 6 tmavě).

## Doména vokudev.cz

Web běží na **Raspberry Pi** doma, stejně jako dema: DNS `vokudev.cz` (A + AAAA) míří na domácí IP,
Caddy servíruje složku `/home/voku/vokudev` (statické soubory, žádný server ani služba).
GitHub Pages (`voku199.github.io/Portfolio/`) běží dál jako zrcadlo, proto všechny odkazy na webu musí být relativní; `canonical` míří na vokudev.cz, takže Google bere jen tu.

**Nasazení nové verze** (z PC):

```bash
python tools/build_projects.py && python tools/shoot.py --og     # bez monorepa: --from-json, shoot jen když je Playwright
git commit -am "..." && git push
ssh rpi 'tar czf ~/backups/vokudev-$(date +%Y%m%d-%H%M).tar.gz -C ~ vokudev'
git archive HEAD | ssh rpi 'tar xf - -C ~/vokudev'
```

`git archive` pošle jen to, co je v gitu, takže `tools/ignore.local.txt` se jmény soukromých složek na server nikdy neodejde.
Smazané soubory na RPi zůstanou, takže je případně smaž ručně.

**Caddy blok** je v `deploy/vokudev.caddy`: www → vokudev.cz, vlastní 404, schované `tools/`, `deploy/` a `*.sh`, cache
a bezpečnostní hlavičky. Po jeho změně na RPi:

```bash
bash ~/vokudev/deploy/caddy-vokudev.sh --nanecisto    # ukáže rozdíl a ověří konfiguraci, sudo netřeba
sudo bash ~/vokudev/deploy/caddy-vokudev.sh
```

Skript mění jen blok hlavního webu, subdomény jako `9b.vokudev.cz` nechá být. Předtím udělá zálohu a když některá adresa
zmizí, validace neprojde nebo selže reload, vrátí původní stav.

V `github-profile/data.py` přepsat `PORTFOLIO` na `https://vokudev.cz/` a znovu `python build.py`.

### Po spuštění (SEO)

1. **Google Search Console** → přidat doménu `vokudev.cz` (TXT záznam v DNS) → Sitemaps → `https://vokudev.cz/sitemap.xml`.
   Pak „Kontrola URL“ na `/` a `/projekty/` → Požádat o indexování.
2. **Bing Webmaster Tools** → Import z Search Console (jedním klikem). Bing krmí i ChatGPT search a Copilot.
3. Ověřit strukturovaná data: <https://search.google.com/test/rich-results> a <https://validator.schema.org/> pro obě stránky.
4. Náhled sdílení: <https://www.opengraph.xyz/> (Discord / Messenger si náhled cachují, změna se projeví až za čas).
5. Odkazy zvenku jsou pro nový web to nejdůležitější: dát `vokudev.cz` do GitHub profilu (pole Website + README), Instagramu, patičky webů pro klienty („web: vokudev.cz“) a do README veřejných repozitářů.
6. Za 2–4 týdny v Search Console zkontrolovat: obě stránky ve stavu „Indexováno“ a dotaz `Vojtěch Kurinec` / `Voku vývojář` v Přehledu výkonu.

### Projekty na subdoménách

DNS má wildcard `*.vokudev.cz` a Caddy si certifikát vyřídí sám. Jednou je potřeba rozdělit Caddyfile na soubory (bloky přesune beze změny, přidá `lol.vokudev.cz`):

```bash
bash ~/vokudev/deploy/caddy-rozdelit.sh --nanecisto
sudo bash ~/vokudev/deploy/caddy-rozdelit.sh
```

Pak má každý projekt vlastní `/etc/caddy/sites/<projekt>.caddy` podle `deploy/sites/lol.caddy`. Po přidání: `sudo caddy validate --config /etc/caddy/Caddyfile` a `sudo systemctl reload caddy`. Staré adresy `*.bakix.cz` zůstávají ve stejném bloku.

Když subdoména běží, změň v `projects_data.py` `url` a spusť build. SANDIFF má `lol.bakix.cz` natištěné na tričku, tak tu starou adresu nech žít. Canonical odkazy si SANDIFF bere z `SITE_URL` (výchozí `https://lol.bakix.cz`), takže když má hlavní adresa být `lol.vokudev.cz`, nastav to v jeho službě.

### Zálohy

`deploy/zalohy/`: každý den ve 3:30 restic zálohuje `/home/voku` (bez venv, node_modules, Ollamy a podobně) a konfiguraci serveru na eeebox, šifrovaně. SQLite kopíruje konzistentně přes backup API.

```bash
bash ~/vokudev/deploy/zalohy/zaloha.sh --nanecisto
sudo bash ~/vokudev/deploy/zalohy/instalace.sh        # 1. běh řekne, jaký klíč přidat na eeebox, 2. běh to dokončí
```

Heslo z `/etc/vokudev/restic-eeebox.env` si ulož mimo RPi. Kopii mimo dům přidáš dalším souborem `/etc/vokudev/restic-<cil>.env`. Zkouška obnovy:

```bash
sudo bash -c 'set -a; . /etc/vokudev/restic-eeebox.env; set +a; restic snapshots; restic restore latest --target /tmp/obnova --include /home/voku/sandiff'
```
