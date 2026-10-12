# Hotel Lens

## Novinky v7 — ceny pokojových typů

- Nové hledání pro **2 dospělé a děti 9/7 let**, léto 2027.
- Samostatné ceny konkrétních pokojových typů za celou rodinu, s termínem, stravou, odletem, dodavatelem a časem získání.
- Nejnižší **nalezená** cena a další získané nabídky v detailu; typy bez bezpečného přiřazení odděleně, nikoli přiřazené odhadem.
- Cenová aktualizace neodstraňuje obecné pokojové varianty ani ruční fakta.
- Návod a hranice: [CENY.md](CENY.md), nové výsledky: [CENY_REPORT.md](CENY_REPORT.md).
- Katalog s cenami otevřete `DATA_DIR=reports/prices-2027 python app.py`; původní databáze zůstává zachovaná.

## Předchozí novinky v6

- **Všechny stránky EXIM** přes JSON API, kontrola celkového počtu a opakovaných stránek; žádný tichý import pouze prvních 20 výsledků.
- Zachování parametrů konkrétní nabídky, rozšířený parser dodavatelských popisů a viditelně označené neúplné údaje.
- Samostatné offline, **živé EXIM** a **Chromium E2E** testy. Návod: [TESTOVANI.md](TESTOVANI.md), naměřené výsledky: [TEST_REPORT.md](TEST_REPORT.md).
- Kontrola uživatelova hledání přibližně 190 nabídek v oddělené databázi; váš původní katalog se nepřepisuje. Finální kontrolní katalog: `reports/final/hotels.sqlite` (190 záznamů, 929 pokojových záznamů; neúplnost je označená). Otevření: `DATA_DIR=reports/final python app.py`.

Pozvolný vstup zůstává bonusem pro děti, nikoli povinnou podmínkou. Technické detaily a limity importu: [API_IMPORT.md](API_IMPORT.md).

## Začněte zde

- **Chci aplikaci spustit:** tento README, sekce Docker níže.
- **Chci vědět, co přesně aplikace má dělat:** [POZADAVKY.md](POZADAVKY.md) — autoritativní zadání, nezávislé na chatu.
- **Chci aplikaci vytvořit znovu nebo předat AI/vývojáři:** [GENEROVANI_APLIKACE.md](GENEROVANI_APLIKACE.md) — připravené předávací zadání a postup.
- **Chci ověřit novou implementaci:** [AKCEPTACNI_SCENARE.md](AKCEPTACNI_SCENARE.md).
- **Chci pochopit předchozí změny:** [HISTORIE_ROZHODNUTI.md](HISTORIE_ROZHODNUTI.md).

Archiv obsahuje všechny tyto dokumenty, kód, SQLite databázi, zdrojové URL, snapshoty EXIM, uložené doplňkové zdroje, Docker konfiguraci a testy. Není potřeba původní konverzace. Dokumenty představují zadání pro generování nové implementace, nikoli automatický generátor; kvalitu nové aplikace je třeba ověřit scénáři a testy.

## Aktuální pravidla (logika v3, dokumentační vydání v4)

Předvolba **Naše rodina** vyžaduje oddělené ložnice nebo místnosti, dvě samostatné dětské postele, bez palandy a písečnou pláž včetně vstupu podle zdroje. **Výslovné potvrzení dveří není nutné.** Dveře, pozvolnost vstupu, plocha a vzdálenost zůstávají volitelné filtry.

Výchozí obrazovka ukazuje všechny varianty s ikonou a důvody: **✓ vyhovuje podle zdrojů / ✕ nevyhovuje / ? k ověření**. Podmínky se posuzují ve své rovině: ikona u varianty hodnotí jen požadavky na pokoj, údaj o pláži a vzdálenosti se vyhodnocuje jednou za celý hotel (řádek „Hotel …“ nad seznamem variant), aby vyhovující pokoj nevypadal jako nevyhovující kvůli pláži. Obojí se ve výsledku stále slučuje bytovou kombinací – hotel vyhoví jen tehdy, když platí jeho hotelové podmínky a zároveň existuje varianta splňující podmínky pokojové. Nepotvrzuje dostupnost zájezdu. Chybějící údaj se nezaměňuje za neshodu; známá neshoda má přednost před nejistotou.

Přepínač **Zobrazit i nevyhovující** je výchozí zapnutý. Po vypnutí skutečné filtrování ponechá hotely s alespoň jednou vhodnou variantou; uvnitř hotelu stále ukazuje všechny typy. Textové hledání a oblíbené fungují v obou režimech. CSV obsahuje podkladové hodnoty, nikoli grafické ikonky.

Referenční výsledek v kompletní dodané databázi: **3 vyhovující varianty, 16 k ověření, 24 nevyhovujících**. Vyhovují dvě rodinné varianty Aldemaru a Comfortable Suite z oficiálního webu Kalogrie. Hotelový typ Kalogria není automaticky přiřazen k nabídce EXIM. Po aktualizaci dat se počty mohou změnit; nejsou pevnou podmínkou programu.

## Co je hotové

- Naplněná SQLite databáze **6 hotelů a 43 záznamů typů ubytování**: 36 variant z EXIM + 7 samostatných doplňkových variant. Nejde o 43 různých fyzických pokojů; varianty různých zdrojů nejsou automaticky ztotožněné.
- Textové hledání bez diakritiky v názvech, lokalitách a popisech.
- Kombinovatelné filtry: oddělené místnosti, dveře, dvě samostatné dětské postele, bez palandy, minimální plocha, písečná pláž včetně vstupu, pozvolný vstup a maximální vzdálenost pláže.
- Režimy **pouze doložené** a **zahrnout neověřené**; známá neshoda neprojde ani druhým režimem.
- Podmínky pokoje se musí sejít na **stejném typu ubytování**, nikoli na libovolné kombinaci pokojů hotelu.
- Podrobné popisy, citace, odkazy a archiv textů zdrojů s datem načtení.
- Ruční ověření s citací a historií, zachované i při opakovaném importu.
- Nové vlastní vlastnosti typu ano/ne, číslo nebo text přímo z rozhraní. Bez změny databázového schématu.
- Import detailních URL EXIM nebo všech stránek výsledků z vloženého vyhledávacího odkazu; kontrola úplnosti, průběh, upozornění a chyby importu.
- Oblíbené hotely uložené v prohlížeči, CSV filtrovaných pokojů a konzistentní záloha SQLite.
- Responzivní rozhraní pro počítač i telefon.

## Nejrychlejší spuštění: Docker

Nainstalujte Docker Engine s Compose pluginem, případně Docker Desktop na PC. Rozbalte archiv a v adresáři `hotel-lens` spusťte:

```bash
docker compose up -d --build
```

Otevřete **http://localhost:8000**.

Produkční Docker image už Chromium nepotřebuje: seznamy i detaily EXIM stahuje HTTP klient. Chromium se instaluje zvlášť pouze pro E2E testy podle TESTOVANI.md.

```bash
docker compose logs -f                # průběh spuštění
docker compose down                   # zastavení, data zůstanou
docker compose up -d --build          # nové sestavení / opětovné spuštění
```

**Nepoužívejte `docker compose down -v`, pokud nechcete smazat databázi.**

### Raspberry Pi 5 / přístup z domácí sítě

Použijte **64bitový Raspberry Pi OS nebo Ubuntu (arm64)**. Dockerfile používá vícearchitekturní Python image bez závislosti na x86 prohlížeči. Doporučení: 4 GB RAM nebo více, pro větší archiv SSD.

```bash
cp .env.example .env
```

V `.env` nastavte:

```dotenv
BIND_ADDRESS=0.0.0.0
APP_PASSWORD=sem-vlozte-vlastni-dlouhe-heslo
```

Poté `docker compose up -d --build`. Z jiného zařízení otevřete `http://IP-ADRESA-RASPBERRY:8000`. Pro HTTP Basic přihlášení můžete zadat libovolné uživatelské jméno, ověřuje se nastavené heslo.

Výchozí Compose zpřístupňuje port jen na lokálním počítači. Pro vzdálené použití preferujte VPN nebo HTTPS reverzní proxy. Samotné Basic přihlášení přes HTTP heslo nešifruje. **Aplikace není veřejná víceuživatelská služba**, nezpřístupňujte ji nechráněnou na internetu.

ARM64 konfigurace je připravená, ale **Docker build a skutečný Raspberry Pi nebyly v tomto prostředí otestované**. Web, databáze, parser a skutečný import byly otestované na Linuxu mimo Docker.

## Lokálně bez Dockeru

Python 3.12+:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Na Windows aktivace prostředí: `.venv\Scripts\activate`. `requirements.txt` fixuje `soupsieve==2.10`, protože soupsieve 3.x odmítá selektory a znehodnotí parser EXIM i cenové API. Produkční prohlížení i import používá pouze HTTP/JSON, Chromium není potřeba. Pro Chromium testy viz TESTOVANI.md.

Pro běžný Linux server použijte místo vývojového Flask serveru:

```bash
gunicorn --bind 0.0.0.0:8000 --workers 1 --threads 4 --timeout 120 app:app
```

Zachovejte **jeden worker**: fronta importů je v procesu, průběh je v SQLite. Gunicorn se používá také v Dockeru. Import přerušený restartem se označí jako chyba a lze jej spustit znovu.

## Jak hledat vaši dovolenou

1. Klikněte na **Naše rodina**. Vybere oddělené místnosti, dvě samostatné dětské postele, bez palandy a písek včetně vstupu. Výslovné dveře nevyžaduje.
2. Volitelně zapněte **Pozvolný vstup do moře** a minimální plochu.
3. Ve výchozím přehledu zůstanou všechny varianty viditelné a označené. Vypněte **Zobrazit i nevyhovující**, chcete-li hotely skutečně skrývat. Nad kompletní dodanou databází aktuální rodinná kombinace ponechá **2 hotely se 3 vyhovujícími variantami**. Pokud navíc vyžádáte výslovné potvrzení dveří, tento přísnější výběr vrátí 0 doložených shod.
4. Zapněte **Zahrnout neověřené**. Uvidíte kandidáty, kteří nemají známou neshodu ve všech požadovaných polích daného typu.
5. V detailu porovnejte konkrétní pokoje a přečtěte citace. Neověřené položky potvrďte u prodejce nebo hotelu a zapište přes **Ověřit údaj**.

Původní vyhledávání je pro **2 dospělé a děti 9 a 7 let, červenec–srpen 2027**. URL je uložená v `data/search_url.txt`; původní nabídky v `data/search_links.json`. Katalog neověřuje živou kapacitu, cenu ani dostupnost konkrétního typu pokoje pro tuto rodinu a termín.

### Stručný výsledek prvního průzkumu

| Hotel | Relevantní údaje | Co dál ověřit / známá neshoda |
|---|---|---|
| Aldemar Olympian Village | EXIM: rodinné varianty 43 m², oddělená ložnice a dvě jednolůžkové postele ve společné místnosti; písečná pláž, pozvolný vstup | Vyhovuje prvotnímu filtru; ručně potvrdit dostupnost přesného typu a finální uspořádání |
| Kalogria Beach | EXIM: rodinný pokoj s oddělenou ložnicí, průchozí pokoj se samostatnými lůžky. Oficiální Comfortable Suite: 35–40 m², dvě ložnice, dvě jednotlivé postele; pláž v EXIM písečná | Comfortable Suite vyhovuje prvotnímu filtru; ověřit přiřazení k EXIM a dostupnost, případně pozvolnost vstupu |
| Roda Beach Resort & Spa | EXIM: více oddělených rodinných variant; písečná pláž s pozvolným vstupem. Oficiální web u rodinných typů popisuje dvě pohovky | Pohovky nejsou v tomto katalogu běžné samostatné dětské postele; různé zdroje/názvy nutno propojit až po potvrzení |
| Poseidon Beach | EXIM: rodinný pokoj 28 m² s pevnými přistýlkami; písečná pláž | Rozdělení na oddělené místnosti není doložené pro tento konkrétní pokoj. Obecný text jiného prodejce to nenahrazuje |
| Apollonia Beach Resort & Spa | EXIM: dvě místnosti s posuvnými dveřmi; oficiální Family Room 46–50 m² vedený zvlášť | EXIM výslovně zmiňuje oblázky při vstupu do moře — nevyhovuje přísnému písečnému filtru |
| Ninos Grand Beach | EXIM: i rodinné varianty s posuvnou stěnou; oficiální Family Bedroom potvrzuje dveře a dvě běžné postele | EXIM uvádí písečno-oblázkovou pláž, doporučuje boty do vody; nevyhovuje písečnému filtru |

Tabulka shrnuje uložené zdroje, není zárukou stavu nebo doporučením k rezervaci. Kompletní odkazy, texty i datum získání jsou v detailu každého hotelu.

**Dotaz pro hotel/prodejce:** „Prosím potvrďte přesný kód a název ubytování pro dva dospělé a děti 9 a 7 let: jsou dvě spací místnosti oddělené plně zavíratelnými dveřmi? Mají děti dvě samostatná běžná lůžka, nikoli palandu či pohovku? Jaká je vnitřní plocha? Je pláž i vstup do vody písečný bez oblázků a je vstup pozvolný? Je tato konkrétní varianta dostupná v našem termínu?“

## Import a aktualizace

- Tlačítko **Importovat hotely**: jeden odkaz na řádek, standardně max. 500 (`MAX_IMPORT_HOTELS`).
- Detailní URL jsou nejspolehlivější. Parametry nabídky se u hotelového záznamu odstraní, duplicitní URL se sjednotí.
- Odkaz na vyhledávání načte **všechny stránky** přes JSON API (`pstg` offset) a ověří počet. Při chybě skončí bezpečně, bez fallbacku na neúplnou první stránku. Parametry detailních nabídek se zachovávají.
- **Obnovit celý katalog** aktualizuje EXIM, nikoli doplňkové weby.
- Automatické stahování běží postupně, s prodlevou 0,6 s a timeouty. Respektujte podmínky zdroje; bez obcházení blokací či přihlášení.
- Neúspěšná stránka nepřepíše poslední funkční záznam. Chyby se zobrazí v importní historii. Při přejmenování pokoje vzniká nový typ, starý se deaktivuje a jeho ruční poznámky zůstávají v databázi.
- Aktualizace není plánovaná automaticky. Spouští se na požádání.

### Celý katalog jedním příkazem (například všech ~190 hotelů)

`tools/refresh_catalog.py` nejdřív zálohuje, pak stáhne všechny stránky výsledků hledání přes JSON API, každou nabídku uloží a na konci napíše, co se oproti předchozímu stavu změnilo.

```bash
# 1) Nácvik offline proti archivovaným popisům: žádná síť, žádná rizika
python tools/refresh_catalog.py --archive tests/fixtures/catalog-190 --data-dir /tmp/nacvik

# 2) Ostrý běh do KOPIE katalogu — vaše stávající data zůstanou nedotčená
cp -r data /tmp/katalog-190
python tools/refresh_catalog.py --url-file data/search_prices_url.txt --data-dir /tmp/katalog-190
DATA_DIR=/tmp/katalog-190 python app.py

# 3) Spokojeni? až potom aktualizujte svůj běžný katalog
python tools/refresh_catalog.py --url-file data/search_prices_url.txt --data-dir data
```

**Změna parseru nevyžaduje stažení.** Texty popisů už v databázi jsou, proto `--reparse` přepočítá automatické fakty pokojů z uložených popisů bez jediné sítové žádosti:

```bash
python tools/refresh_catalog.py --reparse --data-dir data
```

Kolónka `ztracených faktů` v reportu není chyba: jsou to tvrzení, která nový parser už nedělá (například alternativní dispozice „jedna místnost nebo dvě“ se nyní hodnotí `?`, ne `✓`). Ruční ověření a ověřené doplňkové zdroje se nepřepočítávají ani nemažou.

- Vyhledávací URL určuje rozsah. `data/search_prices_url.txt` je současné široké hledání (2 dospělí, děti 9/7, léto 2027, ~190 nabídek); `data/search_large_url.txt` se liší jen věkem 8/6 a nechává se pro reprodukci historických testů v6.
- Před živým během skript ověří dostupnost API. Když zdroj neodpovídá, skončí s vysvětlením a do dat nesahne; `--force-live` přeskočí pouze tuto předkontrolu, ne kontrolu úplnosti.
- `--limit N` stáhne jen prvních N detailů — rozumné první oťukání živého zdroje. Report pak jasně řekne, že jde o částečný běh.
- Report `refresh-report.json` v cílovém adresáři obsahuje přidané a deaktivované typy, změněné fakty, integritu a počty rodinné předvolby ✓ / ? / ✕ nad aktuálními daty.
- Opakovaný běh nad nezměněným zdrojem hlásí nulu ve všech koloncích změn; import proto ničím nepřepiše, co source stále tvrdí stejně.
- Ruční ověření (`manual`) a ověřené doplňkové zdroje (`reviewed`) zůstávají, maže se pouze `auto`.

**Automatický konektor je pouze pro EXIM.** Oficiální weby a jiní prodejci byli použiti při prvním výzkumu; jejich údaje jsou uložené odděleně. Aplikace neobsahuje univerzální crawler ani automatické AI dohledávání libovolných hotelů. Další zdroje lze zapisovat jako ruční ověření s URL a citací. `enrich.py` je pomocný jednorázový výzkumný skript, nikoli obecný importér; některé weby přímé HTTP požadavky blokují. Rozhodující je dodaná databáze včetně textů získaných při výzkumu.

## Význam údajů a omezení parseru

- **Ano/ne/neuvedeno** nejsou zaměnitelné. Absence slova „palanda“ neznamená, že tam palanda není.
- Dveře mezi pokoji se počítají jen tehdy, když v téže větě dělí místnosti, ložnici nebo pokoje; „dveře na balkon“ ne. Skloňování (dveřmi/dveří) a slovně zapsané číslice („dvě místnosti“) parser zvládá, explicitní „nejsou oddělené dveřmi“ vyhodnotí jako `ne`.
- Palanda je `✕` jedině tehdy, když ji zdroj u daného typu přímo uvádí — tedy i tehdy, pokud jde jen o volitelnou přistýlku pro další osobu. Název „… s palandou“ se počítá jako uvedení. Obrátit ji na `✓` umí formulace „bez palandy“ / „no bunk beds“; jiné negace parser nepozná a opravuje je ruční ověření.
- „Rodinný pokoj“ sám neprokazuje dvě místnosti. Oddělená ložnice neprokazuje dveře. Dvě postele pro rodiče neprokazují dvě dětská lůžka.
- Písek znamená, že popis pláže uvádí písek a nezmiňuje kameny/oblázky, včetně vstupu. Není to ověření terénu ani záruka každého metru pláže.
- U plochy 35–40 m² se filtr porovnává s dolní hranicí 35 m²; celý rozsah zůstává v citaci. Nejednoznačná jednotka `32m` zůstává bez číselného údaje.
- Parser je konzervativní, pravidlový, ne jazykový model. Složitější formulace, dědění údajů „viz výše“, negace a alternativy musí případně posoudit člověk. Citace zůstává dostupná pro kontrolu.
- Při rozporu několika strukturovaných tvrzení stejného typu/pole je výsledek neověřený. Rozpory v nepřiřazených pokojích různých zdrojů se automaticky nedetekují jako stejný pokoj.
- Ruční ověření má přednost před automatickým. Při změně zdrojové stránky jej znovu zkontrolujte — aplikace sama neposoudí jeho zastarání.
- Numerická vlastní pole mají v UI filtr „alespoň“, kromě vzdálenosti pláže, která má „nejvýše“. Textová pole filtrují podřetězec. Checkbox znamená vyžadovat `ano`; `ne` lze použít přes API.
- Vlastní pole jsou ihned filtrovatelná, ale jejich automatické plnění vyžaduje rozšíření `room_values()` / hotelového parseru.
- Oblíbené hotely jsou lokální pro prohlížeč; nejsou součástí SQLite zálohy.

## Data a zálohy

Mimo Docker: `data/hotels.sqlite`. V Dockeru: `/data/hotels.sqlite` ve svazku `hotel-data`. Při prvním startu se dodaná databáze bezpečně zkopíruje do svazku. Další buildy vaše data nepřepisují.

Tlačítko **▤** u vyhledávání stáhne konzistentní SQLite zálohu (SQLite Backup API), bez rizika neúplného kopírování aktivního WAL souboru. CSV zahrnuje aktuálně filtrované pokoje a všechna pole včetně vlastních; původní texty a historie jsou v SQLite.

Obnova Docker zálohy:

```bash
docker compose stop
# Zálohu z prohlížeče uložte jako ./backup.sqlite
docker compose run --rm --user root -v "$(pwd)/backup.sqlite:/restore.sqlite:ro" hotel-lens sh -c 'cp /restore.sqlite /data/hotels.sqlite && rm -f /data/hotels.sqlite-wal /data/hotels.sqlite-shm && chown lens:lens /data/hotels.sqlite'
docker compose up -d
```

Před obnovou si ponechte kopii stávajících dat. SQL databáze neobsahuje přihlašovací heslo (`APP_PASSWORD` je pouze v prostředí). Fotografie testovací sady jsou lokálně v `static/`; nově importované hotely mohou odkazovat na obrázky u poskytovatele. Texty a fotografie patří svým původním autorům, nejsou poskytovány s licencí pro veřejné přebírání či publikaci.

## Struktura projektu

```text
app.py          HTTP API, rozhraní, exporty, fronta importů
core.py         SQLite, parser EXIM, pravidla a filtry
importer.py     HTTP stahování, úplné stránkování JSON API
seed.py         Základní EXIM data ze snapshotů (fallback)
bootstrap.py    Prvotní naplnění Docker svazku dodanou databází
enrich.py       Pomocný jednorázový výzkum doplňkových zdrojů
static/         CSS, JavaScript a fotografie
templates/      HTML rozhraní
data/           SQLite, výchozí URL a HTML snapshoty EXIM
tests/          Izolované automatické testy
POZADAVKY.md    Aktuální autoritativní zadání
GENEROVANI_APLIKACE.md   Předávací zadání pro novou implementaci
AKCEPTACNI_SCENARE.md    Kontrolní scénáře
HISTORIE_ROZHODNUTI.md   Historie produktových změn
```

Tabulky: `hotels`, `rooms`, `sources`, `fields`, `facts`, `jobs`. SQLite má cizí klíče, indexy a WAL. Automatické aktuální hodnoty se obnovují; historie stránek je v `sources`, ruční historie ve `facts`.

### API

- `GET /api/hotels?q=...&filters=...&unknown=0&page=1`
- `GET /api/hotels/<id>` — úplný detail a archiv
- `GET /api/fields`, `POST /api/fields`
- `POST /api/facts` — ruční ověření
- `POST /api/import`, `GET /api/jobs`
- `GET /api/export.csv`, `GET /api/backup`, `GET /api/health`

Zápisové požadavky vyžadují `Content-Type: application/json` a `X-Hotel-Lens: 1`. Příklad filtru:

```json
[
  {"key":"sand","op":"eq","value":true},
  {"key":"separate","op":"eq","value":true},
  {"key":"area","op":"min","value":35}
]
```

Architektura umožňuje přidávat další hotely a vlastnosti, import není pevně omezený na šest hotelů. Seznam má stránkování po 24 položkách. Filtrování flexibilních faktů zatím běží v Pythonu nad kandidáty z SQLite; pro desetitisíce hotelů by bylo vhodné přesunout filtry do SQL, doplnit FTS, samostatnou frontu a migrační systém. Masivní katalog ani souběžní uživatelé nebyli zátěžově testováni.

## Ověření

```bash
python -m pip install -r requirements-dev.txt
python -m pytest                         # pouze offline
python -m pytest -m "live and not bulk" # živé API + vzorky
python -m pytest -m "live and bulk"     # drahý celý katalog
python -m pytest -m chromium             # lokální UI v Chromium
```

Chromium vyžaduje předchozí instalaci browseru. Bezpečnost databáze, závislosti, markery, reporty a přesný rozsah: **[TESTOVANI.md](TESTOVANI.md)**. Výsledky aktuálního ověření: **[TEST_REPORT.md](TEST_REPORT.md)**.

Neověřeno: sestavení Docker image, běh na fyzickém Raspberry Pi, dlouhodobý provoz a zátěž desítek tisíc hotelů. Automatické testy neprokazují dostupnost ani ruční správnost všech údajů.

## Nové upřesnění po dodání v6 — 8. 10. 2026

Uživatel požaduje bohatý katalog všech typů uvedených ve zdrojích, nezávislý na nabídce pro konkrétní termín a cestující, s odděleným původem jednotlivých informací. **V6 toto zatím plně neimplementuje.** Parametrizovaný detail může obsahovat jiný dodavatelský popis, ale sám o sobě neurčuje úplný hotelový katalog ani dostupnost pokojů. Zachování query není náhradou nezávislého obecného hotelového popisu. Podrobné nové požadavky: §11 POZADAVKY.md, plánované scénáře G v AKCEPTACNI_SCENARE.md.
