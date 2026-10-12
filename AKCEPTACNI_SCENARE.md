# Akceptační scénáře pro novou implementaci

Platí produktové zadání `POZADAVKY.md`, verze 1.1. Jde o kontrolní seznam, **nikoli tvrzení, že všechny tyto scénáře již byly automatizovaně otestované v dosavadní aplikaci**. Aktuální programové testy jsou v `tests/`; stav předchozího ověření popisuje README.

U scénářů dispozice předpokládej splnění ostatních vybraných podmínek, není-li řečeno jinak. Syntetické testy nikdy nevkládej do uživatelského katalogu jako skutečné hotely.

## A. Dispozice, lůžka a pláž

| ID | Vstup / akce | Očekávaný výsledek |
|---|---|---|
| A01 | Dvě oddělené ložnice, dveře neuvedeny | Dispozice vyhovuje; žádný problém pouze kvůli dveřím. |
| A02 | Ložnice + oddělený obývací pokoj se dvěma běžnými dětskými postelemi | Dispozice a dětská lůžka vyhovují. |
| A03 | Dva hotelové pokoje s vnitřním propojením tvořící jednu variantu | Dispozice vyhovuje. |
| A04 | Jeden open-plan pokoj se čtyřmi lůžky | Nevyhovuje požadavku oddělených místností. |
| A05 | Jen název „rodinný pokoj“, dispozice neuvedena | K ověření, ne automaticky ano ani ne. |
| A06 | Dvě místnosti oddělené posuvnou stěnou | Vyhovuje oddělení v prvotním výběru; výslovné dveře mohou zůstat neuvedeno. |
| A07 | Dvě oddělené ložnice bez informace o dveřích; uživatel zapne přísnější dveřní filtr | Nově k ověření; po vypnutí dveřního filtru tento důvod zmizí. |
| A08 | Dvě jednotlivé postele pouze pro rodiče, dětská lůžka nejsou popsána | Dvě dětská lůžka nejsou potvrzena. |
| A09 | Dětská palanda | Nevyhovuje; zobrazit důvod. |
| A10 | Jen chybějící zmínka o palandě | Neodvodit automaticky „bez palandy“. |
| A11 | Výslovně „bez palandy“ | Pole bez palandy = ano; prosté hledání slova palanda nesmí hodnotu obrátit. |
| A12 | Dvě samostatné dětské pohovky | Nevyhovuje současnému pravidlu běžných dětských postelí; zachovat přesný typ lůžek. |
| A13 | Jedna varianta má alternativně běžné postele nebo palandu | Nepotvrdit bezpodmínečně vhodnost celé varianty; uvést alternativu a potřebu ověření konfigurace. |
| A14 | Písečná pláž, ale při vstupu do vody jsou uvedené oblázky | Nesplňuje přísný písečný filtr, přestože obecný štítek říká písek. |
| A15 | Písečná pláž, pozvolnost neuvedena | Výchozí rodinný výběr neblokovat kvůli pozvolnosti; po zapnutí této podmínky k ověření. |
| A16 | Plocha 35–40 m² | Minimum 35 splněno, minimum 38 nikoli; originální rozsah dostupný v citaci. |
| A17 | Plocha neuvedena | Zobrazit neuvedeno, nikoli 0 m²; při aktivním plošném filtru zachovat nejistotu. |
| A18 | Popis ani název typu neobsahuje „palanda“ / „bunk bed“ | Varianta nikdy nedostane ✕ kvůli palandě. ✕ je výhradně tam, kde zdroj palandu u tohoto typu přímo uvádí (i jako volitelnou přistýlku). |

Scénáře A09–A11 a A18 kryjí automatické testy `test_bunk_*` a `test_no_*_bunk_*` nad 36 variantami archivovaných EXIM snapshotů a nad 929 variantami archivu 190 hotelů; na všech 965 variantách platí, že ✕ existuje jen u doložené zmínky.

## B. Kombinování a zobrazení

| ID | Vstup / akce | Očekávaný výsledek |
|---|---|---|
| B01 | Varianta A má oddělené místnosti, B má dvě dětské postele, žádná nemá obojí doložené | Hotel neprojde jako doložená shoda součtu těchto dvou variant. |
| B02 | Jedna podmínka nevyhovuje a další údaj chybí | Celkový stav ✕, uvést neshodu i chybějící údaj. |
| B03 | Všechny vybrané podmínky jsou potvrzené | ✓; text upozorní, že to nepotvrzuje dostupnost. |
| B04 | Žádná známá neshoda, jeden vybraný údaj chybí | ? K ověření. |
| B05 | Nevybraná podmínka není splněná (např. dveře) | Nemění výsledek aktuálního hodnocení. |
| B06 | Zobrazit i nevyhovující zapnuto | Všechny varianty nalezených hotelů zůstávají viditelné s hodnocením. |
| B07 | Režim skutečného filtrování, zahrnutí neověřených vypnuto | Hotel zůstane jen při alespoň jedné kompletní shodě na jedné variantě. |
| B08 | Režim skutečného filtrování, zahrnutí neověřených zapnuto | Lze ponechat variantu s chybějícím důkazem, nikdy variantu se známou neshodou. |
| B09 | Hotel prošel filtrem díky jednomu pokoji | U hotelu jsou nadále všechny typy, každý s vlastním stavem. |
| B10 | Zapnutí/vypnutí filtru nebo změna minimální plochy | Ikony a důvody se přepočtou podle aktuálních požadavků. |
| B11 | Nové otevření aplikace / předvolba Naše rodina | Oddělené místnosti, dvě dětské postele, bez palandy, písek zapnuty; dveře a pozvolnost vypnuty; všechny varianty viditelné. |
| B12 | Žádné vybrané podmínky | Nepředstírat „vše ověřeno“; zřetelně označit bez posouzení. |
| B13 | Nula při přísném filtru | Vysvětlení chybějících potvrzených shod a možnost ukázat neověřené / všechny. |

## C. Data a provoz

- **C01:** Každý strukturovaný důležitý údaj má dohledatelný zdroj, citaci a datum; datum neupravovat při pouhém zobrazení.
- **C02:** Stejně znějící typy z EXIM a oficiálního webu se bez důkazu nepovažují za totožné. Viditelně označit nepotvrzené přiřazení a dostupnost.
- **C03:** Dvě neslučitelná tvrzení téhož pole a konkrétního typu vedou ke konfliktu/k ověření, nikoli k automatickému optimistickému výběru. Ruční rozhodnutí je zdůvodněné a dohledatelné.
- **C04:** Opakovaný import stejné hotelové URL nevytvoří duplicitu hotelu a nesmaže ruční ověření.
- **C05:** Chyba sítě nebo nerozpoznatelná struktura stránky zobrazí chybu a zachová poslední platná data.
- **C06:** Přidání sedmého a dalších hotelů nevyžaduje změnu kódu se seznamem šesti hotelů.
- **C07:** Přidání vlastní vlastnosti hotelu/pokoje umožní její ruční vyplnění a filtrování. Pole nesmí být mylně prezentované jako automaticky získávané.
- **C08:** Odkazy, názvy a citace se bezpečně zobrazují jako text; importovaný text nesmí spustit JavaScript.
- **C09:** Záloha SQLite za běhu je konzistentní a lze ji obnovit. Restart ani nové sestavení kontejneru nemaže data.
- **C10:** Export odpovídá zvolenému režimu a jasně uvádí rozsah. Nesmí nazývat všechny exportované řádky vyhovujícími, pokud jde o přehled všech variant.
- **C11:** Rozhraní funguje na telefonu i desktopu, bez vodorovného přetékání. Stav není rozlišený pouze barvou.
- **C12:** Rozsah automatického importu a případné neimportované stránky/URL jsou přiznané; nevydávat částečný import za celý katalog.
- **C13:** Návrh pro Raspberry Pi používá ARM64 kompatibilní závislosti; skutečný test na Pi uvést jen tehdy, byl-li proveden.

## D. Referenční data

Nad **nezměněnou kompletní dodanou SQLite databází** očekávej 6 hotelů a 43 variantních záznamů. Předvolba bez dveří má 3 vyhovující varianty, 16 k ověření a 24 nevyhovujících. Vyhovující jsou dvě rodinné varianty Aldemaru a oficiální Comfortable Suite Kalogrie.

Samostatné EXIM snapshoty a testy v `tests/` obsahují pouze 36 variant: s touto fixture prochází 1 hotel (Aldemar) se 2 variantami. Nevynucuj 3 shody na datech, která doplňkovou Kalogrii neobsahují.

Po novém stažení živých webů se počty mohou legitimně změnit. V takovém případě porovnej citace a změny dat, nikoli tvrdě zakódovaná čísla. Primární jsou syntetické rozhodovací scénáře A–C.

## Jak zaznamenat převzetí

Pro každý scénář uveď **splněno / nesplněno / neověřeno**, datum, prostředí a případný důkaz (název testu, screenshot, log). Seznam požadavků není náhradou za provedené testy. Neověřené Docker/ARM64 prostředí odděl od otestovaného lokálního webu.

## E. Pozvolný vstup jako bonus a HTTP/API získávání (v5)

- **E01:** Potvrzený pozvolný vstup má výrazné označení plus pro děti na kartě i v detailu. Filtr zůstává ve výchozí předvolbě vypnutý.
- **E02:** Chybějící údaj o vstupu je označen jako nedoložený, nikoli nevhodný; nemění shodu bez aktivace filtru.
- **E03:** Písečno-oblázková pláž s pozvolným vstupem získá bonus, ale stále nevyhoví povinnému písečnému filtru.
- **E04:** EXIM JSON API zachovává parametry původního vyhledávání a vrací detailní hotelové odkazy bez nutnosti Chromium.
- **E05:** Při neznámém schématu seznamu import bezpečně skončí; nesmí přejít na neúplnou první stránku HTML. Při 401/403/429 se zastaví další stahování, bez obcházení prohlížečem.
- **E06:** Částečná stránka není vydávána za celý katalog. Historie importu ukáže způsob získání seznamu a případný větší celkový počet nabídek.
- **E07:** Úspěšné EXIM API se neprezentuje jako hotové automatické dohledávání jiných webů.

## F. Velké hledání a testovatelnost (v6)

- **F01:** 190 výsledkových položek / 20 na stránku projít až do offsetu 180; nesplést `pstg` s číslem stránky.
- **F02:** Změna celkového počtu, opakování stránky či chyba uprostřed musí zneplatnit celý seznam, nikoli tiše vrátit část.
- **F03:** Detail se stahuje s query konkrétní nabídky; zdrojová URL se zachová i pro obnovení.
- **F04:** České, anglické a dodavatelské pokojové sekce se oddělí; nerozlišený text nedodává smíchané automatické pokojové hodnoty.
- **F05:** Rozpoznaný hotel bez popisu pokojů se zobrazí s upozorněním, bez vymyšlených variant; starší aktualizovaný katalog se nesmaže.
- **F06:** `pytest` nespustí síťové ani browserové testy. `-m live`, `-m bulk` a `-m chromium` mají doložené příkazy a samostatné reporty.
- **F07:** Chromium ověří filtry, všechny pokoje, editaci, exporty, více stránek, mobil a chyby; vnější síť je blokovaná.
- **F08:** Živý úplný import kontroluje počty, chyby, integritu a explicitní neúplnost. Nesmí zaměnit úspěch importu za potvrzenou dostupnost/vhodnost.

## G. Bohaté informace a zdrojově oddělený katalog — požadováno, dosud neověřeno

- **G01:** Obecný popis obsahuje pět typů, nabídka pro rodinu jen dva. Katalog zachová všech pět; pouze dva mají doložený vztah ke konkrétní nabídce.
- **G02:** Změna termínu nebo počtu osob nesmaže dříve evidované hotelové varianty ani fakta jiného zdroje.
- **G03:** EXIM uvádí 35 m², jiný zdroj 40 m². Obě citace a zdroje jsou viditelné; systém je nezamění za automaticky potvrzené rozpětí 35–40 m². Rozpor hodnotí až u doloženě stejného typu.
- **G04:** Text obsahuje kuchyňský kout, i když tento filtr neexistuje. Text se uchová a je přístupný; pozdější přidání filtru není podmínkou předchozího sběru.
- **G05:** Nabídka má prázdný popis, obecný hotelový zdroj má šest typů. Označí se nedostatek konkrétního zdroje, ale obecné typy zůstanou v katalogu.
- **G06:** Nový import jednoho zdroje nepřepíše tvrzení jiného zdroje; zdroj, datum, kontext a ruční historie zůstanou dohledatelné.
- **G07:** Filtr podle zdroje či vlastnosti mění pouze zobrazení. Po zrušení filtru jsou původní informace znovu dostupné.

Scénáře G nejsou pokryté výsledky testů verze v6. Jejich implementace a automatické testy teprve následují.

## H. Cenové nabídky (v7)

- **H01:** Hledání používá děti 9/7; odpověď s věkem 8/6 se nesmí přiřadit.
- **H02:** Mezonet a rodinný typ se dvěma ložnicemi mají různé doložené ceny; minimum hotelu se nekopíruje na ostatní typy.
- **H03:** Cena je celkem za rodinu, nikoli cena za osobu; obsahuje přesný termín a stravu.
- **H04:** Odpověď s jiným hotelem, dodavatelem, pokojovým kódem, obsazeností, stravou, letištěm nebo mimo interval/noci se odmítne.
- **H05:** Nepřiřazené cenové typy jsou samostatně; obecné pokoje bez ceny nezmizí.
- **H06:** Cenový import nezmění existující místnosti a fakta; opakované uložení téže nabídky ji nezdvojí.
- **H07:** Nový cenový profil nečerpá staré ceny jiného profilu. Ceny nad rozpočtem jsou označené, zdroj a čas dohledatelné.
- **H08:** Chromium ověří správné ceny jednotlivých typů, kontext věku, oddělené nepřiřazené typy a CSV export.
- **H09:** Živý cenový kontrakt a offline regrese jsou oddělené; dílčí pokrytí nesmí být prezentováno jako garantované minimum všech kombinací.
