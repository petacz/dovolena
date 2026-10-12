# Hotel Lens — závazné produktové zadání

**Verze zadání: 1.4 · 8. 10. 2026 · implementace v7 (ceny) + zbývající požadavky v §11: prvotní výběr bez povinných dveří, pozvolný vstup zvýrazněný jako plus pro děti, preferovaný přímý HTTP/API přístup.**

Tento soubor zachycuje požadavky nezávisle na původním chatu. Slouží k vytvoření nové aplikace i k dalším úpravám. Nejde jen o popis současného kódu. Při rozporu se starší dokumentací má pro produktové chování přednost tento soubor. Novější výslovné rozhodnutí uživatele má přednost před ním; změnu pak zapište sem a do historie.

## 1. Účel a uživatel

Vytvořit soukromou webovou aplikaci pro **prvotní výběr rodinné dovolené**, která získá detaily hotelů a typů ubytování, uloží je do **SQLite** a umožní v nich hledat a kombinovat filtry. Výsledky si uživatel stejně ověří ručně u hotelu nebo prodejce. Nejde o rezervační systém ani o záruku vhodnosti.

Počátečních šest hotelů je **testovací sada, nikoli pevný limit**. Návrh musí umožnit přidávat větší množství hotelů i další vlastnosti a filtry.

Kontext původního hledání: 2 dospělí, děti 9 a 7 let, červenec–srpen 2027. Úplná původní URL je v `data/search_url.txt`, jednotlivé nabídky v `data/search_links.json`. Tyto termíny a počty nejsou omezením obecného katalogu.

## 2. Požadavky na ubytování — aktuální pravidla

### P-01: Děti spí odděleně od rodičů

Za vhodnou dispozici pro prvotní výběr považovat:
- dvě oddělené ložnice;
- ložnici a oddělený obývací pokoj, v němž spí děti;
- dva propojené hotelové pokoje tvořící společné ubytování.

**Dvě oddělené ložnice nebo místnosti stačí. Není nutné, aby zdroj výslovně uváděl dveře.** Nevyřazovat variantu ani ji nesnižovat na „k ověření“ pouze kvůli chybějící informaci o dveřích.

Při čtení zdroje platí: „dvě místnosti oddělené dveřmi“, „2 pokoje oddělené dveřmi“, „ložnice a obývací část oddělená dveřmi“ i anglické „two rooms separated by a door“ jsou výslovné potvrzení obojího — oddělení i dveří. Slovně zapsaná číslice se rovná číslici, skloňování („dveřmi“, „dveří“) se rovná 1. pádu. Dveře na balkon či terasu nejsou dělicí dveře a nesmí vytvořit `ano`. Explicitní „nejsou oddělené dveřmi“ je doložené `ne`, nikoli nejistota.
Výslovná zmínka o dveřích je užitečný doplňkový údaj. Lze nabídnout samostatný, ve výchozím stavu vypnutý přísnější filtr na dveře. Bez důkazu nepřepisovat samotný údaj o dveřích na „ano“ — mění se požadavek, nikoli zdrojová fakta.

Jeden velký pokoj se čtyřmi lůžky nevyhovuje. Samotný název „rodinný pokoj“ či „suite“ nedokazuje oddělené místnosti. Dvě explicitně oddělené místnosti s posuvnou stěnou vyhovují prvotnímu dispozičnímu filtru. Dva nezávislé pokoje bez potvrzeného propojení nepovažovat automaticky za vyhovující společné ubytování.

### P-02: Dvě samostatná lůžka pro děti, bez palandy

Uživatel požaduje dvě samostatná dětská lůžka a žádnou palandu. Dvě postele uvedené pro rodiče nejsou důkazem dvou dětských postelí. Chybějící zmínka o palandě není důkazem její nepřítomnosti.

Pravidlo pro prvotní hodnocení (upřesnění 11. 10. 2026): neshodu `✕` v poli „Bez palandy pro děti“ smí vytvořit jedině přímá zmínka o palandě v názvu nebo popisu téhož typu ubytování, a to bez ohledu na to, zda je palanda hlavní konfigurací lůžek nebo jen volitelnou přistýlkou pro další osobu. Není-li palanda uvedena, `✕` nikdy nevznikne — varianta zůstane `?`, případně `✓` z doložených samostatných dětských postelí. Uživatel počítá s tím, že zdroje absenci palandy formulací „palanda není“ nepíší; doklad „bez palandy“ proto nevzniká z mlčení. Obrátit zmínku na `✓` umí parser jen u formulací „bez paland“ / „no bunk beds“. Jiná negace (například „palanda není k dispozici“) zůstává mylně `✕` a smí ji opravit jedině ruční ověření s citací, nikoli domýšlení parseru.

Dosavadní produktové pravidlo: dvě běžné samostatné postele vyhovují; společná rozkládací pohovka nevyhovuje a dvě samostatné pohovky se nepovažují za dvě běžné postele. Typ přistýlky evidovat v popisu. Případné budoucí zmírnění pravidla pro pohovky musí být výslovné, nikoli tichý odhad implementátora.

Stejné pravidlo platí i pro dispozici: „jedna prostornější místnost nebo dvě místnosti oddělené posuvnými dveřmi“ je alternativa, nikoli tvrzení, že oddělení je — výsledek je `?`, ne `✓`.

Pokud je popsané více možných konfigurací lůžek, neoznačit celou variantu bezpodmínečně jako vyhovující, když část konfigurací nevyhovuje. Zachovat podmínky a uvést důvod či potřebu ověření.

### P-03: Plocha a maximum dostupných detailů

Ukládat plochu pokoje, je-li dostupná, v m². Zachovat původní údaj i rozsah. U minimálního plošného filtru porovnávat s dolní hranicí rozsahu (35–40 m² splňuje minimum 35, nikoli 38). Neuvádět falešnou přesnost ani si jednotku domýšlet.

Zachovat co nejvíce dostupných informací: původní popisy, dispozici, lůžka, případnou kapacitu, balkon/terasu, bazén u pokoje, výhled, vybavení, stravování, dětské zázemí, pláž a vzdálenosti. V první verzi nemusí být každý textový detail převeden na samostatný filtr; má být dostupný v detailu a vyhledatelný.

### P-04: Pláž

Požadavek je **pouze písečná pláž**, v dosavadní implementaci včetně vstupu do vody. Písečno-oblázková pláž nebo výslovná zmínka o oblázcích/kamenech při vstupu nesplňuje přísný písečný filtr. Pouhý marketingový štítek nesmí přebít podrobný popis.

**Pozvolný vstup do moře je výslovně zvýrazněná výhoda pro děti.** Pokud je doložený, zobrazit výrazný štítek „★ Plus pro děti · pozvolný vstup do moře“ na kartě i v detailu hotelu. Nesmí přebít neshodu jiné podmínky, například oblázkovou pláž. Nepředstavuje záruku bezpečnosti. Je to volitelná vlastnost/filtr, **nikoli povinná součást výchozí rodinné předvolby**. Chybějící údaj o pozvolnosti nesmí ve výchozím stavu pokoj vyřadit.

Hodnocení je tvrzení podle zdroje, ne terénní ověření. Z textu „písečná pláž“ nelze slíbit absenci každého kamínku v celé lokalitě.

## 3. Zdroje, ukládání a důvěryhodnost

### P-05: Více zdrojů

Uživatel dovolil EXIM, oficiální weby hotelů i další veřejné cestovní portály. Používat konkrétní dohledatelné zdroje; u důležitých faktů ukládat URL, citaci nebo výňatek, datum získání a způsob zpracování (automatický / výzkum / ruční ověření).

Ukládat hotel a **jednotlivé typy ubytování samostatně**. Typy nazvané odlišně v EXIM a na webu hotelu automaticky neztotožňovat jen podle podobného názvu. Neprokázané přiřazení viditelně označit. Typ pokoje na webu hotelu neprokazuje, že jej nabízí konkrétní zájezd EXIM.

### P-06: Nejistota není nevyhovění

Každý důležitý údaj musí umět rozlišit **ano / ne / neuvedeno**; pro čísla a text odpovídající chybějící hodnotu. Neslučitelné důkazy pro tentýž konkrétní typ a pole označit jako rozpor / k ověření, nikoli potichu vybrat optimističtější hodnotu.

Ruční ověření musí vyžadovat vysvětlení nebo citaci. Uchovat historii a chránit ruční údaje při opětovném automatickém importu. Ověření může zastarat; zobrazit datum a netvrdit, že je trvale platné.

### P-07: Import

Importovat původních šest hotelů a umožnit další importy. Neúspěšné stažení či změna struktury webu nesmí smazat předchozí platná data. Změna pravidla parseru se nesmí vydávat za nutnost znovu stahovat: uložený popis typu ubytování stačí přepočítat (režim `--reparse`), zdroje ani ruční ověření se tím nemění. Deduplikovat hotelové URL, zobrazovat průběh a chyby. Respektovat podmínky webů, používat timeouty a omezenou frekvenci; neobcházet přihlášení, CAPTCHA ani blokace.

Počet skutečně importovaných hotelů a rozsah importu musí být zřejmé. Pokud konektor načte jen první/vykreslenou stránku výsledků, musí to výslovně říct. Nepředstírat podporu univerzálního prohledávání webu.

## 4. Uživatelské rozhraní a rozhodování

### P-08: Ukázat všechny varianty s ikonami

Výchozí obrazovka zobrazuje **všechny evidované varianty pokoje u každého nalezeného hotelu**, nikoli jen jednu doporučenou. Každá varianta má stav, textový důvod a zdroj:
- **✓ Vyhovuje podle zdrojů** — všechny aktuálně vybrané podmínky jsou splněné;
- **✕ Nevyhovuje** — alespoň jedna vybraná podmínka má doloženou neshodu;
- **? K ověření** — není známá neshoda, ale alespoň jedna vybraná podmínka není doložená.

Doložená neshoda má přednost před chybějícími údaji. Uvést všechny relevantní důvody, nejen barevnou ikonu. Hodnotit **podle aktuální volby filtrů**, nikoli stále podle napevno uloženého skóre. Bez vybraných podmínek nepředstírat ověřenou vhodnost.

Hotelové podmínky (pláž) se uplatní na každou variantu tohoto hotelu. Pokojové podmínky se musí všechny sejít na **stejném typu pokoje**. Plochu jedné varianty nelze zkombinovat s lůžky jiné.

### P-09: Dva režimy výběru

Výchozí režim „Zobrazit i nevyhovující“ ponechá všechny vyhledané hotely i jejich pokoje a jen označí shodu. Aktivní textové hledání a výběr oblíbených platí i zde.

Volitelné skutečné filtrování ponechá hotel jen tehdy, když alespoň jedna jeho varianta splní všechny vybrané podmínky. Přepínač „Zahrnout neověřené“ může ponechat i kandidáty s chybějícími údaji, ne však variantu se známou neshodou. I u ponechaných hotelů zobrazovat všechny varianty s hodnocením.

Nulový výsledek vysvětlit: znamená absenci doložené shody ve zvoleném režimu, ne důkaz, že žádné vhodné ubytování neexistuje.

### P-10: Výchozí předvolba „Naše rodina“

Vybrané podmínky:
1. oddělené ložnice nebo místnosti;
2. dvě samostatná dětská lůžka;
3. bez palandy;
4. pouze písek včetně vstupu podle popisu zdroje.

**Nevybrané:** výslovné dveře, pozvolný vstup, minimální plocha, maximální vzdálenost pláže. Tyto položky jsou volitelné. Výchozí zobrazení ponechá všechny varianty.

### P-11: Rozšiřování a ovládání

České responzivní rozhraní, textové hledání a kombinování filtrů. Umožnit přidat vlastní vlastnost hotelu či pokoje (ano/ne, číslo, text) bez přestavby celé aplikace. Přidání pole samo o sobě neznamená, že je nový údaj automaticky dohledávaný.

Zachovat možnost ručního ověření, čtení citací, exportu dat a SQLite zálohy. Oblíbené, CSV a lokální fotografie jsou užitečné funkce dosavadní implementace, ne samostatně vyslovené původní požadavky uživatele.

## 5. Nasazení a technické hranice

### P-12: Provoz

**SQLite je výslovný požadavek. Docker je preferovaný způsob nasazení.** Preferovaná cílová platforma je Raspberry Pi 5 s 64bitovým OS; běžné PC je přijatelná alternativa. Data musí přežít restart a nové sestavení kontejneru. Návod musí pokrýt spuštění, síťový přístup, zálohu, obnovu a aktualizaci.

Flask, Python, čistý JavaScript, Playwright, Gunicorn, konkrétní CSS ani přesný vzhled nejsou uživatelem povinně určené technologie. Byly zvolené v dosavadní implementaci. Nová aplikace je může změnit, zachová-li chování, SQLite, použitelné nasazení a data. Bez výslovného souhlasu nezavádět placené API jako nutnou podmínku provozu.

### P-13: Co není slíbeno

Není požadována automatická rezervace, platby, garance ceny při rezervaci, spolehlivé potvrzení dostupnosti pro konkrétní termín ani veřejný víceuživatelský portál. Nezapisovat, že nasazení či test proběhl, pokud skutečně neproběhl. Nepovažovat čísla ze snapshotu za pevná pravidla programu.

## 6. Testovací hotely a data

Počáteční sada: Ninos Grand Beach; Poseidon Beach (Laganas, Zakynthos); Apollonia Beach Resort & Spa; Roda Beach Resort & Spa; Kalogria Beach; Aldemar Olympian Village.

V archivu jsou hotelové URL, HTML snapshoty EXIM a databáze s doplňkovými texty, zdroji a ověřenými záznamy. Aktuální snapshot má 6 hotelů a 43 variantních záznamů. Typy různých zdrojů se mohou týkat stejného fyzického ubytování, ale bez jistého přiřazení jsou vedené samostatně.

Referenční výsledek výchozí předvolby nad **dodanou databází**, nikoli pravidlo pro živá data: 3 vyhovující varianty (2 Aldemar + Comfortable Suite Kalogria), 16 k ověření a 24 nevyhovujících. EXIM-only testovací fixture obsahuje jen 36 variant a 2 vyhovující varianty Aldemaru. Rozdíl není chyba: doplňková Kalogria je pouze v úplné databázi.

## 7. Současná omezení nejsou nové uživatelské požadavky

Dosavadní aplikace automaticky aktualizuje pouze EXIM; doplňkové weby byly zpracované při úvodním výzkumu. EXIM prochází přes všechny stránky JSON API a kontroluje úplnost. Ruční ověření umožňuje přidat zdroj/citaci. Importní dávka má výchozí ochranný limit 500 položek/URL. Parser je pravidlový a konzervativní. Velmi rozsáhlý katalog ani fyzický Raspberry Pi nebyly zátěžově/provozně ověřené.

Tyto limity otevřeně uvést, ale při nové implementaci je není nutné kopírovat. Cílem je rozšiřitelný katalog a kvalitní prvotní filtrace, ne zachování chyb či nedostatků původního parseru.

## 8. Co předat při vytvoření nové aplikace

1. Spustitelnou aplikaci se zdrojovým kódem, nikoli pouze obrázek nebo statickou maketu.
2. SQLite databázi nebo doloženou migraci/import původních dat bez ztráty ručních ověření a zdrojů.
3. Dockerfile, Compose a přesný návod včetně ARM64 omezení.
4. Testy rozhodovacích pravidel a přehled toho, co skutečně bylo otestováno.
5. Tuto aktualizovanou specifikaci, zadání pro dalšího vývojáře a akceptační scénáře.
6. Seznam nehotových funkcí a známých omezení; žádné vymyšlené údaje hotelů.

Další podklady: `GENEROVANI_APLIKACE.md` (předávací zadání), `AKCEPTACNI_SCENARE.md` (kontrola výsledku), `README.md` (provoz) a `HISTORIE_ROZHODNUTI.md` (proč se pravidla měnila).

## 9. Preferovaný způsob stahování (aktuální stav v6)

Při získávání dat preferovat vhodná API/JSON/XHR rozhraní nebo přímé HTTP stažení HTML; plný prohlížeč použít jen při skutečné potřebě dynamického vykreslení. API neznamená, že jsou dostupná všechna požadovaná fakta nebo že je povolen neomezený hromadný přístup. Neobcházet autorizaci, blokace a limity.

V implementaci v6 se EXIM stránkuje přes `/api/searchapi/getsearchresult` s offsetem `pstg`; při neúplném seznamu se import zastaví. Detaily používají plné nabídky včetně query a aplikační JSON v HTTP HTML. Produkční fallback na první stránku Chromium je odstraněn. Podrobnosti: `API_IMPORT.md`. Univerzální import dalších webů nadále není hotový.

## 10. Reprodukovatelné testy a neúplná data (v6)

Živé EXIM testy oddělit markerem `live`, drahý celý katalog markerem `bulk`, lokální Chromium E2E markerem `chromium`. Výchozí testy musí být offline. Všechny testy pracují s izolovanou DB. Archivovat nový hledací odkaz a report skutečných počtů, chyb i chybějících údajů. Prázdný popis není důkaz vhodnosti: uložit pouze označená metadata, nevymýšlet varianty a při aktualizaci nezničit dřívější pokoje. Příkazy: TESTOVANI.md.

## 11. Bohatý katalog a oddělený původ informací — nové zadání 8. 10. 2026

**Stav: požadované rozšíření, ve v6 zatím není plně implementované.** Tato pravidla mají přednost před staršími formulacemi, které spojují hotelový katalog s jednou konkrétní nabídkou.

- Sbírat a uchovávat co nejvíce dostupných relevantních informací, nejen hodnoty aktuálních filtrů. Nepoužitelná či chybějící struktura neznamená zahodit původní text. Uchovat dispozice, lůžka a jejich alternativy, plochu, kapacitu, vybavení, pláž, stravování i dětské zázemí, pokud je zdroj skutečně uvádí.
- **Hotelový katalog** obsahuje všechny typy uvedené v obecných hotelových popisech a dalších dohledaných zdrojích. Není omezen výsledky hledání pro určitý termín, počet osob nebo věk dětí. Označovat jej jako „všechny typy uvedené ve zdrojích“, nikoli garantovaný inventář hotelu.
- **Nabídka zájezdu** je samostatný kontext: termín, osoby/věk dětí, dodavatel, nabízený pokoj, případně cena a dostupnost, pouze jsou-li skutečně získané. Nedostupnost či nepřítomnost varianty v nabídce nesmí odstranit variantu z hotelového katalogu. Nevyžaduje to automatické ověřování cen ani rezervovatelnosti.
- U každého tvrzení evidovat zdrojový web a dodavatele, URL, původní název pokoje, citaci, čas získání, rozsah platnosti (hotel / konkrétní typ / nabídka), kontext hledání, pokud se uplatňuje, a způsob získání (automaticky / ručně). Neznámý kontext zůstane neznámý; neodhadovat jej z pouhé přítomnosti query v URL.
- Původ informací zobrazovat odděleně: přehled podle zdrojů a citace u jednotlivých hodnot, nejen jeden společný štítek EXIM. U rozdílných údajů ponechat obě tvrzení s jejich zdroji a označit případný rozpor.
- Stejně či podobně nazvané pokoje z různých zdrojů automaticky neslučovat. Propojení na společný typ vyžaduje doložené přiřazení; nepřiřazené varianty zůstanou samostatné. Nesmí se složit vyhovující varianta z vlastností různých pokojů.
- Filtry mění zobrazení, nikoli rozsah sběru nebo uložená data. Navrhnout také filtrování podle původu, ověření a dostupnosti údajů. Původní popisy zůstanou přístupné, i když je parser nepřevede na strukturované vlastnosti.
- Při nové nabídce neodstraňovat předchozí varianty ani fakta jiného zdroje. Aktualizace a případné zneplatnění tvrzení se musí vztahovat ke konkrétnímu zdroji a rozsahu; archiv a ruční historie zůstanou zachované.
- Prázdný popis konkrétní nabídky znamená jen „tento zdroj neposkytl popis“. Není důkazem chybějícího obecného popisu hotelu. Obecný popis hledat nezávisle a evidovat výsledek pokusu. Případ Asterias z reportu v6 zatím není takto došetřený.

Současná v6 sice uchovává zdrojové texty, citace a část historie, ale automatický sběr více zdrojů ani úplné oddělení hotelového katalogu, dodavatelských popisů a nabídek zatím nemá. Při obnově nyní nahrazuje automatická fakta a aktivní EXIM varianty na úrovni záznamu hotelu; to je potřeba upravit před tvrzením, že nové zadání splňuje.

## 12. Ceny jednotlivých typů — 8. 10. 2026

Uživatel požádal znovu spustit hledání s opraveným věkem dětí **9 a 7 let** a přidat ceny jednotlivých typů. Potvrdil zachování období 24. 7.–22. 8. 2027 a 10–15 nocí; nejnižší nalezená cena musí mít konkrétní termín a možnost prohlédnout další nabídky. Cena se vztahuje k celé rodině 2+2, nikoli automaticky k osobě.

Nesmí se rozkopírovat hotelové minimum na všechny pokoje ani cenu z jiného věku/termínu přiřadit aktuálnímu profilu. Nepropojené cenové typy zobrazovat samostatně. Chybějící cena neznamená vyprodáno. Uchovat zdroj, dodavatele, kód, termín, noci, stravu, dopravu, měnu a čas získání. Ceny jsou časově omezená pozorování, nikoli potvrzená rezervace.

V7 implementuje oddělené cenové tabulky a aktualizaci, která existující katalog a fakta nemění. Tím se plní cenová část oddělení nabídky a katalogu; automatický univerzální sběr všech obecných pokojových popisů z více webů z §11 nadále hotový není. Podrobný skutečný rozsah a omezení: CENY.md. Historické měření v6 s věkem 8/6 zůstává označené jako historické.
