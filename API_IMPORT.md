# EXIM bez prohlížeče — v7 (katalog a samostatné ceny)

## Ověřená cesta

Dne 7. 10. 2026 ověřeno HTTP rozhraní používané frontendem EXIM:

```text
GET https://www.eximtours.cz/api/searchapi/getsearchresult
```

Zachovává parametry vloženého hledání, doplňuje `sc=residential`, pokud chybí. Pole `tours` obsahuje `detailUrl`, `toursCount` udává počet výsledkových položek. Jde o **interní frontendové rozhraní**, nikoli garantované veřejné integrační API. Respektovat podmínky a limity poskytovatele.

## Všechny stránky, nikoli první dvacítka

Nový uživatelův odkaz vrátil při kontrole **190 položek, první odpověď pouze 20**. Kliknutí na stránku 2 v reálném Chromium potvrdilo parametr **`pstg=20`**. Je to offset položek, ne pořadové číslo stránky.

1. Začít `pstg=0`, i když vložená URL obsahuje jiný offset.
2. Přičítat počet skutečně přijatých řádků (`0,20,…,180` v tomto hledání).
3. Ověřit `toursCount`, stálý počet během průchodu, platné URL, neopakování stránek a přesný počet přijatých řádků.
4. Deduplikovat stejné cesty detailu; uchovat parametry **první** nabídky dané cesty.
5. Teprve po úplném získání seznamu začít ukládat detaily.

Chyba API **nespustí fallback na první stránku HTML/Chromium**. Takový fallback by maskoval neúplný výsledek. Starší diagnostická funkce `discover_browser()` není v produkční importní cestě volaná. `ALLOW_BROWSER_FALLBACK` produkční chování už neovlivňuje.

`MAX_IMPORT_HOTELS` má výchozí limit 500 výsledkových položek/odkazů; maximálně 100 stránek. Při překročení limitu se import odmítne, neusekne. HTTP 401/403/429 zastaví další stahování. Dokončené hotelové transakce zůstávají; neúspěšná aktualizace nesmaže starší pokoje ani ruční fakta.

## Parametry nabídky a identita hotelu

Odstranit query před stažením detailu byla chyba: například Louis Althea či Pernera poskytují jiný/žádný popis bez kontextu dodavatele. Detail se nově stahuje přes plné `detailUrl` včetně DS, PID, DPR a termínu; URL se archivuje ve zdroji a `hotels.fetch_url` a používá i při obnovení katalogu. Klíčem záznamu zůstává URL cesta bez query.

**Počet detailních URL není zaručený počet fyzicky odlišných hotelů.** EXIM může mít stejný hotel na cestách s `/hotely/` i bez něj nebo v různých dodavatelských katalozích. Tyto různé cesty záměrně automaticky neslučujeme: mohly by popisovat rozdílné varianty. V reportu se uvádějí záznamy / detailní URL, nikoli garantovaně unikátní fyzické hotely.

## Detailní parser

HTTP HTML obsahuje aplikační JSON `abnbHotelDetail → hotelDetailInfo.description` (případně `dataNew.hotel.description.detailDescriptions`). Parser preferuje kódy `ROOMS` a `BEACH`, toleruje varianty názvů sekcí a umí i jednotlivé dodavatelské pokojové sekce. Starší HTML UL popisy slouží jako kompatibilní parser formátu, nikoli jako náhrada stránkovaného seznamu.

- Česká i anglická jména pokojů, více samostatných pokojových sekcí.
- Pláž i v relevantních větách sekce Poloha / Obecný popis; chybějící vlastnosti zůstanou neuvedené.
- Nerozlišený pokojový popis se uloží **bez automatických pokojových faktů**, aby se nemíchaly dvě varianty. Je viditelně označený.
- Rozpoznaná hotelová metadata bez pokojových popisů: stav `incomplete`, prázdný seznam pokojů, viditelné upozornění. Existující pokoje při takové aktualizaci zůstanou zachované, ale novým stažením nepotvrzené.
- Neznámá stránka bez identifikace hotelu: chyba, ne falešný úspěch.

Stavy importu a příkazy jsou v **TESTOVANI.md**, aktuální měření v **TEST_REPORT.md**. Úplný výzkum oficiálních webů, dalších portálů, přiřazení konkrétního pokoje k nabídce a ověřování cen/dostupnosti nadále nejsou obecně automatizované.

## Nové upřesnění po dodání v6 — 8. 10. 2026

Uživatel požaduje bohatý katalog všech typů uvedených ve zdrojích, nezávislý na nabídce pro konkrétní termín a cestující, s odděleným původem jednotlivých informací. **V6 toto zatím plně neimplementuje.** Parametrizovaný detail může obsahovat jiný dodavatelský popis, ale sám o sobě neurčuje úplný hotelový katalog ani dostupnost pokojů. Zachování query není náhradou nezávislého obecného hotelového popisu. Podrobné nové požadavky: §11 POZADAVKY.md, plánované scénáře G v AKCEPTACNI_SCENARE.md.

## Rozšíření v7: cenová rozhraní

Nový samostatný konektor `prices.py` čte frontendové `POST /api/SearchOffer/GetOfferWithOptions`. Používá autentické filtry z aplikačního JSON hotelu; nevytváří rezervaci ani košík. Obecný import popisů v `importer.py` zůstává od cen oddělený. Detaily parametrů, interpretace dataTo a všech omezení: CENY.md.
