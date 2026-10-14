# Historie produktových rozhodnutí

Všechna níže uvedená rozhodnutí vycházejí z této zakázky; aktuální stav je sjednocen v `POZADAVKY.md`. Toto není doslovný přepis chatu. Starší rozhodnutí se nesmí automaticky vracet jako výchozí pravidla.

## Původní požadavek

Webová aplikace získávající co nejvíce detailů šesti hotelů z odkazu EXIM; SQLite; hledání a filtry; možnost rozšířit na více hotelů a další vlastnosti. Děti mají spát odděleně, dvě samostatná lůžka bez palandy. Plocha ubytování, písečná pláž, případně pozvolný vstup.

## Upřesnění zdrojů a provozu

Uživatel povolil i další cestovní portály, nejen EXIM a oficiální weby. Preferuje Docker a pokud možno Raspberry Pi 5; běžné PC je přijatelné. Přípustné jsou dvě ložnice, ložnice + obývací pokoj i propojené pokoje; ne jeden velký pokoj se čtyřmi lůžky.

## v1: Konzervativní první implementace

Aplikace požadovala výslovné potvrzení dveří. Výchozí přísná kombinace proto měla 0 potvrzených shod. Tento požadavek již **není aktuálním výchozím pravidlem**. Samostatný přísnější filtr na dveře zůstal dostupný.

## v2: Zobrazit všechny varianty

Uživatel požádal o uvedení všech pokojových variant s ikonou vhodnosti. Výchozí režim byl změněn na zobrazování všech variant s hodnocením místo skrývání. Historický výsledek při povinných dveřích: 0 vyhovujících, 19 k ověření, 24 nevyhovujících. Tato čísla nejsou aktuální rodinná předvolba.

## v3: Prvotní filtrace, nikoli definitivní ověření dveří

Uživatel výslovně upřesnil: **dvě ložnice nebo místnosti stačí; nemusí být napsáno, že jsou dveře; stejně provede ruční ověření**. Povinné dveře byly odstraněny z výchozí i tlačítkové předvolby Naše rodina. Samotné zdrojové pole o dveřích se neměnilo.

Nový referenční výsledek nad kompletní databází: 3 vyhovující varianty, 16 k ověření, 24 nevyhovujících. Ostatní podmínky dětských postelí, palandy a pláže se nezměnily.

## Dokumentační vydání v4

Uživatel požaduje uchování zadání tak, aby podle něj bylo možné vytvořit novou aplikaci bez původního chatu. Doplněny soubory `POZADAVKY.md`, `GENEROVANI_APLIKACE.md` a `AKCEPTACNI_SCENARE.md`. Provozní README bylo sjednoceno s aktuálním pravidlem bez povinných dveří. Dokumentační vydání nemění aplikační logiku ani hotelová data.

## Jak zapisovat další změny

1. Uveď datum, důvod a zda jde o výslovný požadavek uživatele, technickou volbu nebo omezení.
2. Aktualizuj autoritativní `POZADAVKY.md` a podle potřeby předávací zadání.
3. Přidej nebo změň akceptační scénář a test.
4. Teprve potom uprav implementaci; zaznamenej skutečně provedené ověření.
5. Předchozí pravidlo ponech zde označené jako historické, ne jako současný návod.

## v5: Výhoda pro děti a lehčí získávání seznamu

Uživatel požádal vyzdvihnout pozvolný vstup jako plus pro děti a navrhl REST/XHR namísto plného prohlížeče. Doplněn výrazný bonus v kartách i detailech, bez přidání nové povinné podmínky. Ověřen a zapojen JSON endpoint EXIM pro vyhledávací výsledky. HTTP HTML zůstává pro detaily a jako první záloha seznamu; Chromium je až poslední záloha. Nezměnila se pravidla pokojů ani se nepřidal univerzální průzkumník hotelových webů.

## v6: Živé testy, Chromium a skutečné stránkování

Uživatel požádal o oddělené live EXIM testy, Chromium scénáře a kontrolu nového hledání přibližně 190 hotelů. Ověřený offset `pstg=20` vedl k náhradě jednostránkového fallbacku za fail-closed úplné stránkování. Rozšířeny dodavatelské popisy, zachována query nabídky, přidána transparentní neúplná metadata a ochrana starších pokojů. Automatické testy pracují mimo uživatelskou DB. Počet detailních URL se nesmí vydávat za počet fyzicky unikátních hotelů. Historický popis v5 výše už neplatí pro aktuální importní cestu.

## 8. 10. 2026: Obecný katalog není konkrétní nabídka

Uživatel opravil propojení pokojového katalogu s nabídkou a upřesnil, že chce co nejvíce informací, odděleně podle jejich původu; omezovat lze až následně filtry. Zapsáno do §11 zadání a scénářů G. Jde o nové požadované rozšíření, ne o již implementovanou vlastnost v6. Aktualizována dokumentace včetně omezení dosavadního reportu; kód a databáze zůstaly beze změny.

## V7: Nové hledání 9/7 a ceny podle typů

Uživatel potvrdil zachování období a 10–15 nocí a opravil věk dětí na 9/7. Přidán samostatný cenový konektor, oddělené cenové profily a zdrojové nabídky. Během ověření se ukázalo, že cenové API může nabídnout návrat mimo interval; proto se upravuje horní mez odletu a kontrolují skutečné vrácené termíny. Ceny se nepřiřazují podle podobnosti jmen a neomezují obecný katalog. Přesné výsledky nového běhu uvádí CENY_REPORT.md.

## 11. 10. 2026: Palanda — ✕ pouze z přímého uvedení (ověření, pojistky, oprava závislosti)

Uživatel upřesnil, že prodejci absenci palandy v popisu nevylučují, a požaduje, aby nevyhovujícím se stal pouze pokoj, u kterého je palanda uvedena. Ověřeno nad dodanými daty: z 43 variant zmiňuje palandu 5 a právě těch 5 má ✕; žádná neshoda bez zmínky; 32 variant je ?. Pravidlo P-02 ani referenční výsledek 3 vyhovující / 16 k ověření / 24 nevyhovujících se nemění, proto zůstává i výchozí přísný režim „pouze doložené“. Zda se má i ve skrývajícím režimu chovat „neuvedeno“ jako kandidát, řeší existující přepínač Zahrnout neověřené; uživatel pro tento výklad nic neměnil.

Technické volby, které pravidlo nemění:
1. Upřesnění P-02 a akceptační scénář A18; obranná větev pro „bez palandy“ zůstává, ač se v datech neuplatnila ani jednou.
2. Parser hodnotí i název typu jako součást jeho textu (`room_values(title+': '+description)`), aby „Rodinný pokoj s palandou“ v názvu nemohl uniknout posouzení. Na všech 1002 archivovaných variantách je změna bez dopadu na výsledky — naměřeno.
3. Popisky přepínačů rozlišují označení a skrytí: „Zobrazit i nevyhovující a nedoložené“ a stavový řádek říká, že bez „Zahrnout neověřené“ se skrývá i chybějící údaj.
4. `requirements.txt` fixuje `soupsieve==2.10`: soupsieve 3.0.1 odmítá každý CSS selektor, čímž rozbije `BeautifulSoup.select` a tím i EXIM parser a cenové API. Off-line sada 87 testů (29 v test_parser_variants.py) proběhla bez networku.

## 12. 10. 2026: Jednorázová obnova celého katalogu příkazem

Uživatel chce stáhnout a aktualizovat data u všech ~190 hotelů. Živý import z tohoto prostředí možný nebyl (povolené připojení jen pro GitHub, npm a PyPI; `www.eximtours.cz` i s vyřešenou adresou selže na TLS), proto byl přidán `tools/refresh_catalog.py`: záloha přes SQLite Backup API, živý běh jedním příkazem s předkontrolou dostupnosti, volitelný `--limit` a `--archive` nácvik nad archivy, report změn a počty rodinné předvolby. Jde o technickou pomůcku, ne o nové produktové pravidlo; chování kolektorů, filtrů ani hodnocení se nemění.

Nacvičeno offline nad 190 archivovanými popisy: 190/190 uloženo, 0 chyb, 3 upozornění, integrita `ok`, opakovaný běh hlásí 0 změněných faktů a 0 nových/zaniklých typů — skript tedy data sama od sebe nepřepisuje. Nad těmito archivovanými daty (pořízení 8. 10. 2026, nikoli živý stav) rodinná předvolba ukazuje 2 vyhovující varianty, 717 k ověření, 210 nevyhovujících a 1 hotel bez popisů pokojů; plně doloženou shodu má jen Aldemar Olympian Village. Nové `tests/test_refresh_tool.py` (3 testy) drží idempotenci, zálohování i formát reportu.

## 12. 10. 2026: Dveře mezi pokoji — oprava čitelnosti zdroje

Uživatel nahlásil, že ANNABELLE BEACH RESORT má u rodinného pokoje psáno „dvě místnosti oddělené dveřmi“, tedy obojí doložené, a přesto aplikace nic neoznámila. Byla to chyba parseru, ne chybějící údaj: vzor vyžadoval prázdné sloveso „2 místnost“/„2 pokoj“ (číslice) nebo přídavné jméno „posuvné/spojovací dveře“. Slovně zapsaná číslice a instrumentál „dveřmi“ ho neminuly, takže `separate` ani `doors` nevznikly.

Oprava: `EXPLICIT_SEPARATION` bere i „dva/dvě/two/3“ plus „propojené/spojené“ a `DOOR_DIVIDES` hodnotí dveře jako dělicí prvek větu od věty, nikoli v celém popisu. Dveře na balkon nebo terasu proto `ano` nevyrobí a „nejsou oddělené dveřmi“ je doložené `ne`, nikoli nejistota. Žádné pravidlo se tím nemění — P-01 stále vyžaduje pro prvotní výběr jen oddělení, dveře zůstávají volitelný přísnější filtr.

Dopad na 965 archivovaných variant: `oddělené místnosti = ano` 102 → 161, `dveře = ano` 17 → 56, žádné dříve detekované tvrzení neztrateno, 0 změn v šesti dodaných snapshotech (referenční výsledek 3/16/24 ani testy `test_app.py` se nemění). Nové testy `test_doors_dividing_rooms_are_recorded`, `test_balcony_door_is_not_treated_as_a_room_divider`, `test_explicitly_undivided_rooms_are_a_mismatch_not_a_maybe`; scénáře A19–A21. V archivu není jediné „bez propojení“, proto nebyla přidaná žádné pravidlo pro vyvrácení propojení — dva nezávislé pokoje zůstávají k ověření podle P-01.

## 12. 10. 2026 (večer): Oprava se má promítnout do stažených dat bez stahování

Uživatel správně namítl, že data už stažená jsou: v `reports/final` i `reports/prices-2027` leží Annabelin popis „dvě místnosti oddělené dveřmi“ v `rooms.description`, chyběly jen odvozené fakty, protože je vytvořil starý parser. Oprava parseru se tedy bez dalšího zásahu do zdrojů nijak neprojeví — data jsou v pořádku, zastaralý je výklad.

Přidán režim `tools/refresh_catalog.py --reparse`, který přepočítá automatické fakty typů ubytování z textu uloženého v databázi. Bez sítě, bez nového stahování, s backupem a stejným reportem; doplňkové zdroje (`reviewed`) a ruční ověření (`manual`) se přepisovat nesmí, proto se maže a vkládá pouze `kind='auto'` nad pokoji s `origin='EXIM'`.

Zároveň zpřesnění, aby oprava nebyla jen přesnější: popis „jedna prostornější místnost nebo dvě místnosti oddělené posuvnými dveřmi“ je alternativa, ne tvrzení o oddělení. Původní parser u tří suit tvrdil `dveře = ano` i `oddělení = ano`; to bylo špatně a nové pravidlo je vrací na `?`. Je to zároveň jediný případ, kdy report hlásí `ztracené fakty` — záměrně, ne regresi.

Nad 965 archivovanými variantami: `oddělené místnosti = ano` 102 → 158, `zavíratelné dveře = ano` 17 → 53, 3 dříve mylná `ano` stažena zpět na `?`. Přepočtem `reports/prices-2027` (937 typů) přibylo 99 faktů v 73 typu ubytování, 0 změněných a 6 stažených (3 alternativní dispozice × 2 pole), integrita `ok`. Rodinná předvolba nad těmito daty zůstává 2 vyhovující varianty / 724 k ověření / 211 nevyhovujících, protože u Annabelle zdroj píše o dispozici, ale už ne o dětských postelích ani o povrchu pláže — proto `?`, nikoli `✓`.

## 12. 10. 2026 (v noci): Údaj o pláži patří hotelu, ne každé variantě

Uživatel správně upozornil na nepřehlednost: „Pouze písek (včetně vstupu)“ se objevovalo
v seznamu „Nedoloženo“ u každého typu ubytování zvlášť, takže vyhovující pokoj vypadal
jako „? K ověření“ kvůli pláži — a doložený štěrk dokonce přebarvoval všechny varianty
na „✕ Nevyhovuje“, i když o dispozici zdroj říkal „ano“.

Funkční význam se nemění: `core.search()` už předtím dělil požadavky podle rozsahu
(`hf` proti faktům hotelu, `rf` proti faktům konkrétního typu) a hotel zůstal ve výsledku
jen při splnění obou rovin. Šlo o prezentaci — `assessment()` v UI vyhodnocovala všechny
požadavky najednou, takže hotelový údaj tekl do hodnocení varianty.

Rozhodnutí: `evaluate(h,r,scope)` vyhodnotí jen požadavky dané roviny. Hodnocení varianty
dostává pouze pokojové podmínky, řádek `.assessment.hotel` nad seznamem variant podmínky
hotelové (včetně varování o neaktuálním importu, které se dříve opakovalo u každé varianty).
Bez požadavku v dané rovině se nic netvrdí: varianta hlásí „— Bez požadavků na pokoj“
a řádek hotelu se vůbec nevykreslí. Třída `hotel` je jen vizuální (levý proužek), barvy
podle stavu zůstávají. Souhrn nad výsledky nově uvádí zvlášť „Hotel: ✓/?/✕“, aby bylo jasné,
kolik variant se rozpadlo kvůli pláži a kolik kvůli dispozici.

Stejná úprava platí i v detailu hotelu, kde řádek visí pod faktovými poli hotelu.
Testovatelnost: logiku UI lze kontrolovat bez prohlížeče — `tests/test_assessment_scopes.py`
načte `static/app.js`, přes node vyhodnotí oddělený blok a hlídá, že se pláž u varianty
neobjeví nikdy a nejistota aspoň jednou na úrovni hotelu. DOM část zůstává v
`tests/test_chromium.py`.

## 12. 10. 2026: report nesmí krácení výčtu tvářit jako menší změnu

Ověření čísel pro tento text odhalilo chybu v reportu: `facts_added` a `facts_lost` se do
souboru i na konzoli ukládaly zkrácené na 40 položek a tisk hlásil jejich délku. Přepočet
`reports/prices-2027` tedy dvakrát vykázal „40 doložených, 0 ztracených“ fakty, zatímco
skutečně šlo o **99 doložených a 6 ztracených**. Číslo, které uživatel uvidí, tak bylo
ukazatelem na horní mez výčtu, ne na rozsah změny — a u opakovaného běhu by to mohlo
vysílit „0“ tam, kde změna je.

Oprava: plné počty jdou do nového klíče `changes_counts`, `changes` zůstává výčtem (a proto
se jmenuje jako výčet, ne jako součet). Velikost výčtu je přepínač `--list-cap`, výchozí 40,
`0` = vyjmenovat vše; report pak nese `changes_list_cap: null`. Konzore u zkráceného výčtu
řekne „(ve výčtu prvních 40, zbytek jen spočítán)“, aby zkratka nebyla tichá. Test
`test_report_counts_survive_the_shortened_listing` drží, že zkrácený i plný výčet hlásí
táž čísla a že počet nikdy nedosedne na délku výčtu.

Drobnost, která vyšla najevo u přepočtu: `reports/final` i `reports/prices-2027` obsahují
9 dvojic téhož hotelu pod odlišným URL (190 řádků = 181 různých hotelů, v databázi s cenami
192 řádků) — EXIM uvádí týž hotel pod dvěma letovisky, a protože deduplikace běží podle URL,
nesloučil je. `--reparse` oba záznamy přepočítá zvlášť a shodně; jejich sloučení je
samostatné rozhodnutí, zatím nedělané.

## 14. 10. 2026: vyhovující první, nevyhovující jen spočítané, tabulka vedle karet

Zadavatel po prohlídce 192hotelové databáze upřesnil, že „zobrazit všechny varianty“ nemá
znamenat 937 stejně vážených řádků v abecedním pořadí: vyhovující varianta má být první a
její podrobnosti vidět hned, nevyhovující se nemá vypisovat vůbec a hotely chce porovnat
v tabulce se značkou ✓/✕ za každou vlastnost podle aktuálních filtrů.

Rozhodnutí: verdikt se nově počítá i na serveru (`core.state/assess`) ze stejných faktů a
stejných kritérií jako v prohlížeči, protože podle něj musí být seřazené celé stránkování,
ne jen jedna stránka. `/api/hotels` proto rozlišuje `filters` (tvrdý filtr, beze změny
chování) a `rank` (jen hodnocení a pořadí; výchozí režim posílá `filters=[]` a `rank` =
vybrané podmínky). Pořadí hotelů: doložená shoda → k ověření → doložená neshoda, uvnitř
stupně více ✓ variant a název; uvnitř hotelu ✓ → bez požadavku → ? → ✕, pak cena. ✕ varianty
zůstávají v DOM (sbalené v „Skryto N nevyhovujících“), v CSV (nový sloupec s verdiktem) i
v počtech, takže platí P-08 „nic se neztratí“ a zároveň se netisknou. Seznamové JSON už
nenese úplné popisy a historii faktů (–40 % objemu); má je detail.

Vedlejší opravy při tom: hledání padalo u hotelu s prázdnou lokalitou (`NULL` v SQL
konkatenaci), špatně typované filtry vracely 500 místo 400, hromadné obnovení katalogu
stahovalo všechny stránky výpisu kvůli adresám (nově `/api/hotel-urls`), a `pytest` bez
nainstalovaného Playwrightu padal při sběru testů místo přeskočení Chromium sady.
Rozhodnuto nebylo: přepočet (`--reparse`) uložených databází opraveným parserem — mění
73 variant a čeká na výslovné schválení.
