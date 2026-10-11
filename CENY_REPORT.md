# Hotel Lens v7 — nové hledání a ceny pokojů

**Živé měření 8. 10. 2026, dokončeno v 16:37 pražského času (14:37 UTC).**

Kontext: **2 dospělí, děti 9 a 7 let**, odlet Praha, 10–15 nocí, období 24. 7.–22. 8. 2027, původní filtry hledání a rozpočet 200 000 Kč. Přijímány jsou pobyty s návratem nejpozději 22. 8.; dražší alternativy jsou uložené, ale označené jako nad rozpočtem. Přesná URL: `data/search_prices_url.txt`.

## Výsledky

| Ukazatel | Skutečně naměřeno |
|---|---:|
| Výsledky nového hledání / stránky API | **190 / 10** |
| Záznamy, u kterých byly prověřeny ceny | **190** |
| Záznamy s alespoň jednou přijatou cenovou nabídkou | **190** |
| Uložené cenové nabídky | **544** |
| Rozdílné cenové typy: hotelová cesta + dodavatel + kód pokoje | **492** |
| Obecné pokojové varianty s přesně přiřazenou cenou | **178** |
| Cenové typy bez bezpečného přiřazení k obecnému popisu | **308** |
| Cenové nabídky bez přiřazení k obecnému pokoji | **339** |
| Nabídky nad rozpočtem 200 000 Kč | **61**, viditelně označené |
| Hotelové záznamy s upozorněním na část cenového průchodu | **20** |
| Nevyřešené chyby zpracování po cílených opravách | **0** |
| SQLite integrita | **ok** |

**Cena u každého hotelového záznamu neznamená cenu u každého obecně popsaného typu pokoje.** Neznámé ceny nejsou nahrazené hotelovým minimem. Nepřiřazené cenové typy jsou zobrazené zvlášť pod skutečným názvem a kódem EXIM, v kartě i detailu. Několik dodavatelských kódů může mít stejný úplný název, proto počet přiřazených cenových kódů není totožný s počtem obecných variant s cenou.

Počet 190 odpovídá výsledkovým položkám / odlišným detailním URL, nikoli potvrzenému počtu fyzicky různých hotelů. Dodavatelské katalogy se mohou překrývat.

### Příklady skutečně získaných cen

Celková cena zájezdu pro 2 dospělé a děti 9/7, nikoli cena za osobu:

| Hotel | Typ podle EXIM | Termín | Celkem |
|---|---|---|---:|
| High Beach | Mezonet | 7.–17. 8. 2027, 10 nocí | **175 960 Kč** |
| High Beach | Rodinný pokoj, 2 ložnice, Deluxe, Výhled bazén | 7.–17. 8. 2027, 10 nocí | **184 640 Kč** |
| Asterias Beach | Rodinný pokoj, Výhled zahrada | 9.–19. 8. 2027, 10 nocí | **185 180 Kč** |

U High Beach jde o dvě různé doložené ceny, nikoli o cenu hotelu rozkopírovanou na oba typy. U Asterias existuje cenová nabídka, přestože v dosavadním obecném katalogu chyběl pokojový popis; cena proto zůstává v samostatné cenové sekci. Tyto ceny nejsou doporučením vhodnosti pokojů ani potvrzením budoucí rezervace.

U **Estival Islantilla** je nejnižší v tomto průchodu získaná přijatá cena **200 200 Kč**, tedy již nad rozpočtem. Záznam je ponechaný a rozdíl je označený. Ostatních 189 výsledkových záznamů má alespoň jednu získanou cenu nejvýše 200 000 Kč.

## Katalog se nezúžil podle nabídky

Kontrolní databáze vycházela z předchozího katalogu 190 záznamů / 929 pokojových záznamů. Nové hledání obsahovalo dva jiné hotelové odkazy. Přibyly:

- Pavlo Napa Beach;
- AluaSun Continental Park.

Dva původní záznamy mimo nové hledání — Iberostar Waves Ciudad Blanca a Cavo Orient Beach Resort — zůstaly zachované, bez přimíchání starých cen do profilu 9/7.

Finální kontrolní katalog proto obsahuje **192 hotelových záznamů a 937 obecných pokojových záznamů**. Přímé porovnání řádků ověřilo, že všech původních **190 hotelových řádků, 929 pokojových řádků a 646 faktů** z kontrolního katalogu zůstalo beze změny. Přibyly nové záznamy, zdrojové archivy a samostatné ceny.

Původní uživatelská databáze `data/hotels.sqlite` má nadále **6 hotelů / 43 aktivních variant**; cenový experiment ji nenahradil.

## Co bylo nutné opravit během měření

1. **Věk dětí:** nový hledací odkaz a cenové dotazy používají 9/7. Odpovědi se kontrolují, nestačí pouze přepsat popisek v UI.
2. **Rozsah termínů:** cenový endpoint používá konec intervalu pro výběr odletu. Nevhodné návraty se odmítají. U 17 záznamů bez přijaté ceny byly následně jednotlivě dotázány délky 10–15 nocí; přibylo 37 platných nabídek.
3. **Prázdná cenová odpověď:** EXIM někdy vynechá celé pole `offer` a ponechá prázdné seznamy alternativ. Po doložení tohoto skutečného formátu byl parser opraven. Původních 11 chybových průchodů bylo znovu živě prověřeno, nikoli administrativně přeznačeno na úspěch.
4. **Automatické rozšiřování hledání zdrojem:** prázdná odpověď může navrhovat URL s koncem až v září. Aplikace tento odkaz automaticky nenásleduje a nezamění zářijovou cenu za letní zadání.
5. **Změna dodavatele v odpovědi:** taková odpověď se nepřiřadí původnímu pokoji. Platné jiné nabídky stejného záznamu zůstávají dostupné s vlastním časem a zdrojem.

Zbývajících 20 upozornění znamená například prázdnou odpověď pro konkrétní pokojový kód nebo odmítnutou změnu dodavatele v dílčím dotazu. Neznamená to, že všechny alternativy byly vyčerpávajícím způsobem oceněné. Přesto má každý ze 190 hledaných záznamů alespoň jednu přijatou nabídku.

První průchod, cílené opravy a doplňkové kontroly jsou rozlišené v JSON a konzolových reportech. Počítadlo HTTP odpovědí z prvního průchodu není počtem všech následných diagnostických a opravných požadavků.

## Testy a audit

- **71 offline testů**: parser cen, kontext a věk, celková cena, odmítnutí nesprávného termínu/hotelu/dodavatele/letiště/stravy/kódu, přesné přiřazení, ochrana katalogu a ručních faktů, historie profilů, export, prázdné odpovědi a doplňkové délky.
- **17 Chromium testů**: dosavadní aplikace plus ceny jednotlivých typů, rodinný kontext, nepřiřazené cenové typy a CSV.
- Závěrečný společný offline + Chromium běh: **88 prošlo**, 45,57 s.
- **2 živé cenové kontraktní testy prošly**, 3,60 s: nové hledání s věkem 9/7 a skutečné pokojové ceny EXIM.
- Navíc skutečný hromadný cenový průchod všech 190 výsledků a cílené živé opravy; nejde o přehrávání uložených cen.
- Samostatný audit **všech 544 uložených nabídek** ověřil věk 9/7, 2 dospělé, datum návratu, počet nocí, kladnou konečnou cenu CZK, zdrojový cenový údaj, parametry URL a vazby do katalogu.
- Zvláštní Chromium smoke test nad finální skutečnou databází ověřil 192/937 záznamů, dvě různé ceny High Beach, cenový kontext 9/7, mobilní šířku a absenci JavaScriptových chyb.

Starší report `TEST_REPORT.md` dokumentuje v6 a hledání 8/6. Není přepisován jako nové měření.

## Soubory

- **`reports/prices-2027/hotels.sqlite`** — finální samostatný katalog a ceny.
- **`reports/prices-2027/ceny-pokoju-9-a-7.csv`** — všech 544 nabídek v tabulce.
- `reports/prices-2027/price-report.json` — finální rozsah, počty a konkrétní upozornění.
- `reports/prices-2027/initial-price-report.json` — první úplný průchod před cílenými opravami.
- `reports/prices-2027/final-price-audit.json` — kontrola všech uložených cen.
- `reports/prices-2027/catalog-preservation.json` — porovnání původních řádků katalogu.
- `reports/prices-2027/*junit.xml` — automatické testy.
- `reports/prices-2027/prices-high-beach.png`, `prices-mobile.png` — skutečný cenový náhled.

Spuštění, aktualizace, limity a API: **[CENY.md](CENY.md)**.

## Co z výsledku nevyplývá

Není garantována cena pro každý obecně popsaný typ, absolutní minimum přes všechny kombinace, rezervovatelnost ani správnost každého tvrzení dodavatele. Ceny mohou okamžitě zastarat. Automatické dohledávání všech obecných pokojových popisů na oficiálních webech a dalších portálech není tímto cenovým rozšířením dokončené. Docker build a fyzický Raspberry Pi nadále nejsou provozně ověřené.
