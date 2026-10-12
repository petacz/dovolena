# Testování Hotel Lens v7

Vše spouštějte z kořene projektu. Testy používají **dočasnou SQLite databázi**, nikoli `data/hotels.sqlite`. Nepřepisují váš katalog, ruční ověření ani oblíbené. Soubory v `reports/` mohou obsahovat veřejné zdrojové URL a popisy hotelů.

## Instalace

```bash
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
```

Pouze pro Chromium testy na podporovaném Linuxu:

```bash
python -m playwright install --with-deps chromium
```

Instalace systémových knihoven může vyžadovat administrátorská práva. Na Windows/macOS stačí `python -m playwright install chromium`. Na ARM lze použít systémové Chromium a `CHROMIUM_PATH=/usr/bin/chromium`. Běh na fyzickém Pi zatím není ověřen.

## 1. Výchozí offline testy

```bash
python -m pytest
# totéž explicitně:
python -m pytest -m unit --junitxml=reports/unit-junit.xml
```

Výchozí `pytest.ini` **vylučuje `live` i `chromium`**. Neprovádí skutečné požadavky na EXIM a nepotřebuje instalovaný browser. Pokrývá parser, různá schémata dodavatelů, strukturovaná data v HTML, oddělení pokojů, neúplné popisy, zachování dřívějších dat a ručních ověření, bezpečnost URL, stránkování API včetně chyb, filtry, SQLite a Flask API. Uložené reálné vzorky jsou regresní vstupy, nikoli živá měření. `test_saved_catalog.py` znovu projde všech 190 archivovaných popisů a provede úplný offline databázový import. Manifest uchovává referenční názvy a upozornění; není to nezávislý ruční audit každého tvrzení.

## 2. Živé kontraktní testy EXIM

```bash
python -m pytest -m "live and not bulk and not prices" -v --junitxml=reports/live-contract-junit.xml
```

Čtyři katalogové testy (původní URL a archivovaný větší odkaz 8/6; cenové hledání 9/7 viz níže): původní menší vyhledávání bez browseru, všechny stránky většího hledání, tři detailní vzorky (začátek/střed/konec) a opravené pokojové formáty na třech konkrétních hotelech. Používají skutečné HTTP odpovědi. Test velkého hledání vyžaduje více než 20 výsledků, **nikoli přesně 190**: nabídka zdroje se mění.

## 3. Nákladný úplný import

```bash
python -m pytest -m "live and bulk" -s --junitxml=reports/live-bulk-junit.xml
```

Projde všechny stránky a potom **každou nalezenou detailní URL**, zapíše záznamy a fakta do izolované DB a ověří počty, chybová hlášení a `PRAGMA integrity_check`. Aktuálních 190 detailů znamená přibližně 200 HTTP požadavků; počítejte s několika až desítkami minut. Stahování je sériové, s prodlevou minimálně 0,6 s. Neprovádějte jej v krátké smyčce nebo po každé drobné úpravě UI.

Volitelně archivovat celé odpovědi mimo projekt:

```bash
EXIM_SAVE_HTML=/cesta/k/archivu python -m pytest -m "live and bulk" -s
```

`reports/<UTC timestamp>/live-import.json` rozlišuje:
- `ok`: uložené záznamy, **nikoli počet plně potvrzených hotelů**;
- `complete`: záznamy s nějakým popisem pokojů (mohou mít upozornění);
- `incomplete`: pouze metadata, EXIM neposkytl popis pokojů;
- `warnings`: konkrétní chybějící nebo neoddělitelné údaje;
- `errors`: chyby stažení/zpracování; ty způsobí neúspěch testu;
- `discovered`, `attempted`, `counts`, `integrity` a jednotlivé hotely.

Úspěch testu znamená technicky konzistentní import včetně pravdivě označené neúplnosti. **Neznamená**, že každý pokoj vyhovuje požadavkům, má známou plochu, že jsou všechny formulace ručně ověřené nebo že je dostupný pro zadané cestující.

## 4. Chromium: skutečné UI nad lokální testovací aplikací

```bash
python -m pytest -m chromium -v --junitxml=reports/chromium-junit.xml
```

Lokální Flask server na náhodném portu, skutečný Chromium, samostatná DB pro každý test. Vnější síť prohlížeče je blokovaná. Scénáře: výchozí filtry a všechny varianty, hledání, prázdné výsledky, oblíbené po reloadu, přísné/neověřené filtry, detail a trvalé ruční ověření, vlastní pole, CSV a SQLite download, mobil 390 px, katalog nad 24 hotely, viditelné neúplné údaje, validace importu a dokončení úloh bez/s upozorněním. Importní úloha je v těchto dvou UI scénářích simulovaná, **nejde o další živý EXIM test**.

Navíc se všech 190 archivovaných záznamů načte do lokální testovací aplikace a Chromium projde všech osm stránek: kontroluje 190 různých ID a všech 929 pokojových záznamů bez ztrát či duplikace při stránkování. To je offline E2E nad skutečnými archivovanými popisy, ne další stažení EXIM.

Automaticky se kontrolují JavaScriptové chyby. Screenshoty a Playwright trace jsou v `reports/<UTC timestamp>/`. Otevření trace:

```bash
python -m playwright show-trace reports/<timestamp>/<test>-trace.zip
```

Pro diagnostiku dřívějšího testu stačí screenshot; externí fotografie jsou v E2E záměrně blokované.

## Alternativní zdrojové URL

Součástí balíčku jsou `data/search_url.txt` a uživatelův nový odkaz `data/search_large_url.txt` (2 dospělí, děti 8/6, léto 2027).

```bash
EXIM_LIVE_URL='https://www.eximtours.cz/vysledky-vyhledavani?...' \
EXIM_LIVE_SMALL_URL='https://www.eximtours.cz/vysledky-vyhledavani?...' \
python -m pytest -m "live and not bulk"
```

CLI `-m` přepíše výchozí výběr. Samotné `-m live` zahrne **i drahý bulk test**. Pro všechny sady najednou lze použít `python -m pytest -m "unit or chromium or live"`, ale kvůli nákladům preferujte oddělené běhy.

Živé testy záměrně neskrývají síťové chyby jako `skip` či úspěch. HTTP 401/403/429 zastaví další stahování, nic se neobchází browserem. Změna počtu během stránkování nebo opakovaná stránka je chyba; po ověření stavu zdroje lze běh zopakovat. Bezplatnost přístupu neznamená licenci k veřejnému přebírání textů/fotek.

Naměřené výsledky této dodávky: **TEST_REPORT.md**. Docker build, fyzický Raspberry Pi, dlouhodobý provoz a správnost všech lidských interpretací nejsou pokryté touto sadou.

V dodávce je ponechán kompaktní výběr screenshotů a trace v `reports/final/`; nový běh generuje vlastní úplnou sadu.

## Cenové testy v7

`test_prices.py` testuje kontext, ceny za celou rodinu, odmítnutí nesprávné nabídky, přesné přiřazení, ochranu katalogu a export. Chromium má navíc cenové scénáře. `python -m pytest -m "live and prices"` provede dvě skutečné cenové kontraktní kontroly. Samotné `-m "live and not bulk"` nyní zahrne také tyto cenové testy; pro původní sadu použijte `-m "live and not bulk and not prices"`. Výsledky v6 v TEST_REPORT.md jsou historické; aktuální cenové měření je v CENY_REPORT.md.

## Nástroj `tools/refresh_catalog.py`

`tests/test_refresh_tool.py` ověřuje skript bez sítě: spustí ho jako podproces nad archivem `tests/fixtures/catalog-190` do dočasného adresáře, ověří, že druhý běh nad týmiž popisy nezmění nic (nula v kolonkách změn), že se záloha vytvoří až při existující databázi a že report vždy souhlasí počty rodinné předvolby s počtem variant. Když skript upravíte, hned vidíte, jestli jste rozbili idempotenci nebo zálohování.

