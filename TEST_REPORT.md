# Hotel Lens v6 — výsledky ověření

**Datum: 7. 10. 2026.** Testované hledání je archivované v `data/search_large_url.txt`: 2 dospělí, děti 8 a 6 let, léto 2027. Původní uživatelská databáze zůstala zachovaná: **6 hotelů / 43 aktivních variant**, SQLite integrita `ok`.

## Výsledek většího hledání

| Kontrola | Naměřeno |
|---|---:|
| Počet položek hlášený živým EXIM API | 190 |
| Stránek API / velikost první stránky | 10 / 20 |
| Offsety `pstg` | 0, 20, …, 180 |
| Nalezené odlišné detailní URL | 190 |
| Skutečně stažené detaily | 190 |
| Chyby stažení a uložení při živém bulk testu | 0 |
| Záznamy s popisem pokojů po konečné opravě | 189 |
| Pouze metadata, bez pokojového popisu | 1 |
| Pokojové záznamy ve finální kontrolní DB | 929 |
| Z toho nerozlišené popisy bez pokojových faktů | 2 |
| SQLite integrita finální DB | `ok` |
| Chromium: všech osm stránek kontrolního katalogu | 190 různých ID / 929 pokojových záznamů |

**190 URL není 190 prokazatelně různých fyzických hotelů.** EXIM vrací také různé dodavatelské cesty ke stejnému hotelu, například s `/hotely/` a bez něj. Neslučujeme je automaticky, aby se nesmíchaly varianty různých popisů.

### Zbývající nedostatky zdrojových dat

- **Asterias Beach:** konkrétní živá nabídka má prázdné hotelové popisy i v aplikačním JSON. Uložena pouze metadata, žádné vymyšlené pokoje ani potvrzená vhodnost.
- **MarSenses Ferrera Blanca Hotel** (cesta končící `marsenses-ferrera-blanca-hotel`): souvislý popis apartmánů/suit/studia nemá dostatečně jednoznačné hranice názvů a jednotlivých variant. Je uložen celý, označený jako nerozlišený a bez automatických pokojových faktů. Jiná dodavatelská cesta `…-family-hotel` má oddělené pokojové sekce.
- **Hotel Riu Costa del Sol:** obecný popis odkazuje na vybavení pokojů u konkrétních termínů, ale nevyjmenovává typy; navíc chybí použitelný podrobný plážový popis. Označeno k ručnímu ověření.

„Zpracováno“ neznamená, že jsou známá všechna lůžka, plocha či písek. Stav `ok` je technický stav parseru, nikoli doporučení hotelu. Cenová dostupnost, obsazenost a přiřazení pokoje ke konkrétní nabídce nebyly ověřovány.

## Automatické sady

| Sada | Poslední výsledek | Čas | Reálná síť |
|---|---:|---:|---|
| Výchozí offline unit/API/regrese, včetně opakování všech 190 uložených popisů | **48 prošlo** | 1,98 s | Ne |
| Chromium E2E, včetně všech 190 záznamů na 8 stránkách | **14 prošlo** | 30,02 s | Jen lokální aplikace |
| Živé kontraktní testy EXIM včetně opravených formátů | **4 prošly** | 26,14 s | Ano |
| Živý úplný import všech 190 detailů | **1 prošel** | 314,05 s | Ano |

Příkazy, markery, instalace a bezpečnost: **[TESTOVANI.md](TESTOVANI.md)**.

### Přesné rozlišení živého běhu a následné regrese

Úplný živý bulk test nejprve uložil 190 záznamů / 931 pokojových záznamů. Podrobná následná kontrola odhalila, že EXIM označil dvě sekce **„Pro handicapované“ kódem `ROOMS`**. Parser je mylně evidoval jako další nerozlišené pokojové záznamy. Opraveno: sekce jsou zachované v popisu, ale nepřidávají falešné varianty. Opraven byl také pokojový nadpis bez tučného písma u Estival Park Apartments.

Po těchto opravách:
1. znovu zpracováno **všech 190 původních úplných HTTP odpovědí** v oddělené DB — výsledných 929 záznamů, bez chyb;
2. znovu **živě staženy tři dotčené hotely** a ověřeny opravené výsledky v kontraktním testu;
3. přidány cílené offline regrese a opakování všech 190 archivovaných popisů;
4. Chromium prošel finální katalog na všech osmi stránkách.

Celých 190 detailů se po této malé opravě zbytečně nestahovalo podruhé. **Finální replay je výslovně offline**, nikoli vydávaný za další živé měření. Živé a replay reporty jsou uchované zvlášť.

## Opravené problémy

1. Import pouze první stránky (20 místo 190): úplné stránkování `pstg`, kontroly počtů, opakování a nestabilního výsledku.
2. Nebezpečný fallback, který by maskoval neúplnost: při chybě seznamu nyní bezpečné ukončení.
3. Ztracené parametry detailní nabídky: uchovává se dodavatel, termín a celé `detailUrl`; používá se také při obnovení katalogu.
4. Různé názvy hotelových/plážových sekcí, anglická jména pokojů a dodavatelské pokojové sekce: rozšířený parser aplikačního JSON a kompatibilního HTML.
5. Falešná varianta ze sekce přístupnosti a nadpis pokoje bez tučného písma: cílené opravy s regresními testy.
6. Chybějící popisy: explicitní neúplná metadata, upozornění v kartě, detailu a výsledku importu; dřívější pokoje se při neúplné aktualizaci nesmažou.
7. Pevné „ŘECKO“ na kartách: země se bere ze skutečné lokality. Text detailu již nepředpokládá pevný věk dětí.
8. Oddělené markery, dočasné DB, blokování náhodných HTTP požadavků v offline testech, browserové screenshoty a trace.

## Přiložené důkazy a data

- `reports/unit-junit.xml`, `chromium-junit.xml`, `live-contract-junit.xml`, `live-bulk-junit.xml` — výsledky jednotlivých sad.
- `reports/20261007T210111Z/live-discovery.json` — živé stránky, počty a plné detailní URL.
- `reports/20261007T210111Z/live-import.json` a `live-catalog.sqlite` — původní skutečný bulk běh, ještě před závěrečnou korekcí 931 → 929.
- `reports/20261007T210903Z/live-repaired-formats.json` — opětovná živá kontrola tří opravených případů.
- `reports/final/final-replay.json` — konečný replay úplných HTTP odpovědí.
- **`reports/final/hotels.sqlite` — finální samostatný kontrolní katalog: 190 záznamů / 929 pokojových záznamů.**
- `reports/final/chromium-large-catalog.json`, screenshoty a `test_real_190_catalog_all_eight_ui_pages-trace.zip` — browserové důkazy.
- `tests/fixtures/catalog-190/` — zkrácené autentické strukturované popisy a manifest pro offline regresi. Referenční očekávání byla vytvořena z naměřeného výsledku, nejsou nezávislým ručním auditem všech faktů.

### Otevření kontrolního katalogu bez změny původních dat

Z kořene projektu po instalaci běhových závislostí:

```bash
DATA_DIR=reports/final python app.py
```

PowerShell:

```powershell
$env:DATA_DIR="reports/final"
python app.py
```

Poté `http://localhost:8000`. Pro návrat k původnímu katalogu proměnnou `DATA_DIR` odstraňte. Běžné spuštění a Docker nadále používají původní data; kontrolní katalog se automaticky neslučuje s ručním výzkumem.

## Neověřeno / negarantováno

Docker build a fyzický Raspberry Pi, dlouhodobá stabilita interního EXIM API, zátěž desítek tisíc hotelů, aktuální rezervační dostupnost a ruční správnost všech interpretací. Obecné automatické vyhledávání oficiálních hotelových webů a dalších cestovních portálů není touto změnou implementováno. Změní-li EXIM obsah nebo schéma, živé testy mohou oprávněně selhat.

## Upřesnění rozsahu výsledků po připomínce uživatele

Výsledky výše nadále popisují naměřenou implementaci v6. Nedokazují úplnost obecného katalogu pokojů hotelu: šlo o stažení konkrétních detailních URL v daném kontextu. U Asterias nebyla doložena absence obecného hotelového popisu, pouze prázdný popis v testované nabídce. Nové požadavky §11 POZADAVKY.md a scénáře G nejsou těmito testy potvrzené. Aplikace nebyla v rámci tohoto dokumentačního upřesnění změněna ani znovu testována.

## 11. 10. 2026: Ověření pravidla „palanda jen z přímého uvedení“

Rozsah: pravidlo P-02 se neměnilo, ověřoval se jeho současný výklad a doplnily se pojistky. Python 3.11, `beautifulsoup4==4.14.3`, `soupsieve==2.10`, offline (`-m "not live and not chromium"`).

| Kontrola | Naměřeno |
|---|---:|
| Off-line testová sada | **87 passed / 0 failed**, 24 deselected (live, bulk, chromium, prices) |
| Testy palandy v `tests/test_parser_variants.py` | 29 collectionů, z toho 17 nových |
| Archivy EXIM: varianty celkem | 36 (snapshots) + 929 (katalog 190) = **965** |
| Varianty s `✕` pro `no_bunk` | **5** (z toho 5 × přímá zmínka o palandě) |
| `✕` bez zmínky o palandě v názvu či popisu daného typu | **0** |
| Varianty bez zmínky → `?` (žádný fakt) | 32 z 43 v dodané DB |
| Dopad započtení názvu typu do `room_values` | **0 ze 1002** archivovaných variant změnilo výsledek |
| Živý API test nad dodanou DB, filtr samotný `no_bunk` | přísný režim 4 hotely / 6 variant; se „Zahrnout neověřené“ 6 hotelů / 38 variant, vyřazeno právě 5 pokojů s uvedenou palandou |

Oprava závislosti: s `soupsieve==3.0.1` selže i selektor `span`, tedy všechny `BeautifulSoup.select` volání. Import EXIM i cenové API by končily `SelectorSyntaxError`; requirements proto fixují `soupsieve==2.10`.

**Neověřeno v tomto prostředí:** sestavení Docker image, live testy proti eximtours.cz (sem nedovoleno), Chromium E2E (chyběl binární prohlížeč), fyzické Raspberry Pi. Testovací běh dočasně vytvořil `reports/<timestamp>/`; výsledek replay je regenerovatelný `python -m pytest`.
