# Nástroje portfolia

| Skript | Co dělá |
|---|---|
| `paint.py` | namaluje obrazy a ilustrace do `img/` |
| `build_projects.py` | postaví archiv `projekty/` přímo z monorepa + upraví počty na hlavní stránce a `sitemap.xml` |
| `shoot.py` | vyfotí screenshoty živých webů do `tools/shots/` (Playwright) |

## Archiv projektů (`/projekty/`)

```bash
python tools/shoot.py            # jen když se změnily živé weby
python tools/build_projects.py   # vždycky před pushem
python tools/shoot.py --og       # po buildu: náhled pro sdílení projekty/og.png + apple-touch-icon.png
python tools/build_projects.py --check   # suchý běh: co se najde, jaké technologie
```

Build zároveň přegeneruje **SEO soubory**: `sitemap.xml` (s obrázky, `lastmod` hlavní stránky jen když se změnila),
`llms.txt` (přehled pro AI vyhledávače) a JSON-LD archivu (`CollectionPage` + `BreadcrumbList` + `ItemList`,
napojené přes `@id` na `Person` z hlavní stránky).

- **Ručně** v `projects_data.py`: který projekt se ukáže, název, kategorie, jedna věta CS + EN, odkaz, jestli je to bezpečné živé demo.
- **Samo**: technologie (z `requirements.txt`, `package.json`, `build.gradle` a podpisů v kódu), počet řádků, datum poslední změny, stav „Aktivní“ (změna za posledních 30 dní).
- **Obrázek**: `tools/shots/<slug>.png` → pole `shot` → namalovaná obálka.
- Nová složka v monorepu se na web **nedostane sama**, build ji jen vypíše jako „nezařazenou“. Soukromé složky, jejichž jména nemají být ani ve veřejném repu, patří do `tools/ignore.local.txt` (v `.gitignore`).
- `projekty/index.html` je generovaný, upravuj `projekty.template.html`.

## Doména vokudev.cz

Web běží na **Raspberry Pi** doma, stejně jako dema: DNS `vokudev.cz` (A + AAAA) míří na domácí IP,
Caddy servíruje složku `/home/voku/vokudev` (statické soubory, žádný server ani služba).
GitHub Pages (`voku199.github.io/Portfolio/`) běží dál jako zrcadlo; `canonical` míří na vokudev.cz, takže Google bere jen tu.

**Nasazení nové verze** (z PC, přes ssh-console):

```bash
python tools/build_projects.py && python tools/shoot.py --og
git commit -am "..." && git push
python C:/Users/vojta/.claude/skills/rpi-deploy/scripts/rpi.py upload . "~/vokudev" --exclude ignore.local.txt
```

`--exclude ignore.local.txt` je důležitý: ten soubor obsahuje jména soukromých složek a na server nepatří.

Upload si sám udělá zálohu do `~/backups/`. Smazané soubory na RPi zůstanou, takže je případně smaž ručně.

**Caddy blok** je v `deploy/vokudev.caddy`: www → vokudev.cz, vlastní 404, schované `tools/` a `deploy/`, cache
a bezpečnostní hlavičky. Po jeho změně na RPi spusť jednou `sudo bash ~/vokudev/deploy/caddy-vokudev.sh`.
Skript nahradí jen blok vokudev.cz, předtím udělá zálohu a když konfigurace neprojde, vrátí původní.

V `github-profile/data.py` přepsat `PORTFOLIO` na `https://vokudev.cz/` a znovu `python build.py`.

### Po spuštění (SEO)

1. **Google Search Console** → přidat doménu `vokudev.cz` (TXT záznam v DNS) → Sitemaps → `https://vokudev.cz/sitemap.xml`.
   Pak „Kontrola URL“ na `/` a `/projekty/` → Požádat o indexování.
2. **Bing Webmaster Tools** → Import z Search Console (jedním klikem). Bing krmí i ChatGPT search a Copilot.
3. Ověřit strukturovaná data: <https://search.google.com/test/rich-results> a <https://validator.schema.org/> pro obě stránky.
4. Náhled sdílení: <https://www.opengraph.xyz/> (Discord / Messenger si náhled cachují, změna se projeví až za čas).
5. Odkazy zvenku jsou pro nový web to nejdůležitější: dát `vokudev.cz` do GitHub profilu (pole Website + README), Instagramu, patičky webů pro klienty („web: vokudev.cz“) a do README veřejných repozitářů.
6. Za 2–4 týdny v Search Console zkontrolovat: obě stránky ve stavu „Indexováno“ a dotaz `Vojtěch Kurinec` / `Voku vývojář` v Přehledu výkonu.

### Dema na subdoménách (volitelné)

Dema teď běží na `*.bakix.cz`. Pokud mají mít adresu pod vokudev.cz, stačí na RPi do Caddyfile přidat další jméno ke stávajícímu bloku a v DNS vokudev.cz přidat A záznam na veřejnou IP domu (stejnou jako má `bakix.cz`):

```caddy
vr.bakix.cz, vr.vokudev.cz {
    encode zstd gzip
    reverse_proxy 127.0.0.1:9983 {
        header_up X-Forwarded-Proto https
        header_up Host {host}
    }
}
lol.bakix.cz, lol.vokudev.cz {
    encode zstd gzip
    reverse_proxy 127.0.0.1:9980
}
```

```bash
sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak-$(date +%Y%m%d-%H%M)
sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy
```

Pak v `projects_data.py` změnit `url` a znovu spustit build. SANDIFF má `lol.bakix.cz` natištěné na tričku, tak tu starou adresu nech žít.
