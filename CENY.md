# Ceny pokojových typů — v7

## Co je implementováno

Samostatná vrstva cenových nabídek EXIM pro **2 dospělé a děti 9 a 7 let**, hledání uložené v `data/search_prices_url.txt`. Původní `search_large_url.txt` s věkem 8/6 zůstává zachované pro reprodukci historických testů v6.

U cen se uchovává konkrétní dodavatel, kód a název pokoje, termín, noci, stravování, letiště, lety, celková cena za rodinu, měna, čas získání a zdrojová URL. **Jde o cenu zájezdu, nikoli pouze za ubytování nebo za osobu.** Cena je orientační údaj zdroje v čase kontroly, ne rezervace ani záruka dostupnosti.

V kartě pokoje se ukáže nejnižší ze získaných cen. Detail obsahuje jednotlivé získané nabídky a odkazy na EXIM i uložená zdrojová data. Nabídky bez bezpečného přiřazení k obecnému popisu jsou uvedené zvlášť pod názvem a kódem z EXIM. Typy bez ceny zůstanou viditelné jako **„Cena nezjištěna“**, nikoli „vyprodáno“.

## Oddělení katalogu a cen

Tabulky `price_searches`, `price_hotels` a `room_offers` jsou oddělené od `rooms` a `facts`. Cenová aktualizace **nepřepisuje ani nedeaktivuje existující obecné varianty a jejich fakta**, včetně ručních ověření. Pro hotel, který v katalogu dosud není, se založí dostupný popis z EXIM. U existujících hotelů se nově stažený popis archivuje jako další zdroj, nikoli jako náhrada jejich obecného katalogu.

Přiřazení ceny k existujícímu pokoji vyžaduje současně:
1. stejnou hotelovou URL cestu;
2. totožný celý název typu (jen normalizace mezer, koncové dvojtečky a velikosti písmen);
3. shodný datový zdroj, dodavatele a dodavatelský identifikátor hotelu z URL zdroje pokoje;
4. právě jeden takový pokoj v katalogu.

Není použitá podobnost názvů ani odhad podle slov „family/suite“. Jde o automatické přesné přiřazení v rámci téhož zdroje, ne o ruční potvrzení prodejcem. Pokud původní obecný popis nemá dodavatelský kontext, cena se automaticky nepřipojí; přesto je dostupná v samostatné cenové sekci.

Aktivní zobrazení používá pouze poslední dokončený cenový běh. Starší běhy zůstávají v SQLite jako historie; staré ceny jiného hledání se nepřimíchávají. Hotel mimo aktuální hledání má tento stav výslovně uvedený.

## Ověřené rozhraní a rozsah

Na skutečné stránce EXIM byl v Chromium pozorován čtecí požadavek:

```text
POST https://www.eximtours.cz/api/SearchOffer/GetOfferWithOptions
```

Výchozí `offerFilter` se získává z aplikačního JSON v HTTP detailu (`dataNew.offerFilter`). Obsahuje skutečné identifikátory dodavatele a hotelu; nevymýšlíme je. Požadavek nic nerezervuje, nevytváří košík a neposílá osobní údaje cestujících kromě počtu a věku dětí. Technický věk dospělých 30 let přebírá konvenci frontendového filtru, není to tvrzení o věku uživatele.

Odpověď obsahuje `offer` a `roomOptions`, tedy vybranou nabídku a alternativní pokojové typy s vlastními cenami. `availableDates` je pouze kalendářový přehled — jeho ceny se **nepřipisují jednotlivým typům**, protože chybí kompletní přiřazení kombinace.

Konektor:
- znovu projde všechny stránky hledání s opraveným věkem;
- načte cenové filtry hotelů;
- odstraní omezení na jeden původní balíček/let/pokoj a vyžádá nabídku v období;
- objevené pokojové kódy samostatně dotazuje ve stejném období a zachovává nalezené alternativy;
- přijme pouze odpověď se správným hotelem, dodavatelem, 2 dospělými, dětmi 9/7, dopravou, letištěm, stravou a počtem nocí;
- porovná přímo `price.price` / `priceOffer.price`, ne cenu za osobu ani součet potenciálně odlišného dílčího rozpisu alternativy;
- zastaví další stahování při HTTP 401/403/429, neobchází omezení.

### Termíny a úplnost

Pro tento běh je období konzervativně použité jako **celý pobyt od 24. 7. do 22. 8. 2027 včetně návratu**, 10–15 nocí. Cenový endpoint chápe `offerDate.dateTo` jako horní hranici výběru odletu. Proto se tato hranice upravuje o minimální počet nocí a **každý vrácený termín se navíc kontroluje**. Návrh s návratem po 22. 8. se neprezentuje jako splňující zadaný interval, i když jej zdroj vrátí.

Zobrazená cena je **nejnižší z nalezených nabídek**, ne garantované absolutní minimum každého pokoje přes všechny odlety, stravy, délky a dodavatele. `roomOptions` nemusí obsahovat pokoj, který je dostupný jen v jiném termínu, a vyhledání hotelů také není kompletní inventář všech pokojů. Nedoloženou úplnost aplikace neslibuje. Stravování je zachované z výchozí nabídky odpovídající vyhledávání; konektor neprohledává všechny stravovací varianty.

Levnější základní nabídka může mít dražší alternativy. Ty se nezahazují; cena přes původních 200 000 Kč je označena **„Nad rozpočtem hledání“**. V seznamu hotelů se zachovávají původní filtry hledání.

U hotelů, kde nebyla získána žádná cena kvůli návratu mimo interval, konektor provede doplňkové dotazy pro jednotlivé délky pobytu 10–15 nocí s odpovídajícím posledním odletem. Ani tím se nedokazuje vyprodání, pokud nabídka chybí.

Ověřená prázdná odpověď EXIM někdy vynechává celé pole `offer` a vrací prázdné seznamy alternativ. Tento tvar je podporovaný jako „nabídka nezjištěna“, nikoli chyba parseru. Navrženou `defaultSearchUrl`, která může rozšířit termín o další měsíc, konektor **automaticky nenásleduje**.

Limit objevených cenových dotazů na hotel je standardně 16 (`MAX_PRICE_REQUESTS_PER_HOTEL`). Při jeho dosažení se průchod označí jako částečný. Neznámé schéma, změna nabídky během dotazování či nevyhovující vrácený kontext se uvedou v reportu, nikoli jako cena jiného pokoje.

## Spuštění a aktualizace

Běžná aplikace: tlačítko **Ceny pokojů → Aktualizovat cenové nabídky**. Vložená výsledková URL určuje kontext. Příkazový řádek po instalaci `requirements.txt`:

```bash
# DATA_DIR musí ukazovat na zamýšlený katalog; před změnami udělejte SQLite zálohu.
DATA_DIR=reports/prices-2027 python prices.py \
  --url-file data/search_prices_url.txt \
  --report reports/prices-2027/price-report.json
```

CLI záměrně běží synchronně. Doplňková kontrola jednotlivých délek může přidat až šest cenových dotazů na hotel. Hromadné ověření může trvat desítky minut; nespouštějte několik aktualizací proti stejné DB současně. Vnější chyby neskrýváme. Násilně přerušený CLI běh se nemá vydávat za dokončený a nesmí se použít jako aktuální cenový profil.

Otevření přiloženého odděleného katalogu s cenami:

```bash
DATA_DIR=reports/prices-2027 python app.py
```

Původní `data/hotels.sqlite` zůstává zachovaná. Pro vlastní existující Docker svazek lze ceny načíst tlačítkem v aplikaci; nová image sama nepřepisuje vaše data. Kopírování testovací DB do existujícího svazku by přepsalo jeho obsah — nedělejte je bez zálohy.

## Export a audit

- `GET /api/prices/context` — poslední dokončený profil a report.
- `POST /api/prices/refresh` — nový běh, vyžaduje `X-Hotel-Lens: 1`.
- `GET /api/price-offers/<id>` — uložená cena, kontext, původní data a požadavek.
- `GET /api/prices.csv` — všechny nalezené ceny posledního profilu, nikoli jen minima.
- SQLite záloha obsahuje i historii cen; původní CSV pokojových vlastností zůstává samostatné.

## Testy

```bash
python -m pytest                         # offline parser cen, kontext, přiřazení, ochrana katalogu
python -m pytest -m chromium             # včetně cen v UI, oddělených typů a CSV
python -m pytest -m "live and prices"   # živé hledání 9/7 a skutečná cenová odpověď
```

Dosavadní live/bulk testy z v6 nadále zkoušejí import popisů, nikoli úplnost cen. Výsledky nové cenové kontroly jsou v `CENY_REPORT.md`. Žádné z těchto měření není příslib dostupnosti při pozdější rezervaci.
