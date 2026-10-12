from pathlib import Path
from conftest import ROOT
import pytest
import core
pytestmark=pytest.mark.unit
FIX=Path(__file__).parent/'fixtures'
@pytest.mark.parametrize('slug',['estival-islantilla','hotel-san-antonio','marsenses-ferrera-blanca-family-hotel','arion-green-riviera'])
def test_real_supplier_description_formats(slug):
 p=core.parse_exim((FIX/(slug+'.html')).read_text())
 assert p['name'] and p['rooms'] and p['beach']
 assert all(r['name'] and r['description'] for r in p['rooms'])
def test_english_room_titles_not_dropped():
 p=core.parse_exim((FIX/'hotel-san-antonio.html').read_text())
 assert len(p['rooms'])==6
 assert any('FamilyRoom' in r['name'] for r in p['rooms'])
def test_partner_rooms_are_individual_sections():
 p=core.parse_exim((FIX/'marsenses-ferrera-blanca-family-hotel.html').read_text())
 assert len(p['rooms'])==9
 assert p['values']['sand'] is True

def test_missing_description_is_explicit_not_fabricated(isolated_db):
 text=(FIX/'asterias-beach-hotel.html').read_text()
 p=core.parse_exim(text);assert p['rooms']==[] and p['warnings']
 result=core.save_exim('https://www.eximtours.cz/kypr/test/asterias',text,return_status=True)
 assert result['status']=='incomplete'
 with core.connect() as c:assert c.execute('select count(*) from rooms').fetchone()[0]==0

def test_incomplete_update_keeps_previous_rooms(isolated_db):
 url='https://www.eximtours.cz/kypr/test/asterias'
 core.save_exim(url,(FIX/'hotel-san-antonio.html').read_text())
 core.save_exim(url,(FIX/'asterias-beach-hotel.html').read_text())
 with core.connect() as c:
  assert c.execute('select count(*) from rooms where active=1').fetchone()[0]==6
  assert c.execute('select import_status from hotels').fetchone()[0]=='incomplete'

def test_undivided_text_does_not_mix_room_facts():
 p=core.parse_exim((FIX/'marsenses-ferrera-blanca-hotel.html').read_text())
 assert p['warnings']
 assert p['rooms'][-1]['values']=={}

def test_source_context_retained(isolated_db):
 u='https://www.eximtours.cz/kypr/test/hotel?DS=256&DD=2027-08-01'
 core.save_exim(u,(FIX/'hotel-san-antonio.html').read_text())
 with core.connect() as c:
  h=c.execute('select * from hotels').fetchone()
  assert h['url']==u.split('?')[0] and h['fetch_url']==u
  assert c.execute('select url from sources').fetchone()[0]==u

@pytest.mark.parametrize('slug,count',[('thalassa-superior',7),('atlantica-sungarden-beach',6)])
def test_accessibility_section_is_not_an_extra_room(slug,count):
 p=core.parse_exim((FIX/(slug+'.html')).read_text())
 assert len(p['rooms'])==count and not p['warnings']
 assert 'Pro handicapované' in p['sections']

def test_unbold_single_room_heading():
 p=core.parse_exim((FIX/'apartmentos-estival-park.html').read_text())
 assert p['rooms'][0]['name']=='Apartmá, 1 ložnice'
 assert not p['warnings']

# --- Palanda: neshoda pouze z přímého uvedení v textu daného typu ---
BUNK=('paland','bunk bed')
def mentions_bunk(text):return any(x in core.fold(text) for x in BUNK)
def rooms_of(path):return core.parse_exim(path.read_text())['rooms']

@pytest.mark.parametrize('slug',['estival-islantilla','hotel-san-antonio','marsenses-ferrera-blanca-family-hotel','arion-green-riviera','marsenses-ferrera-blanca-hotel','apartmentos-estival-park','thalassa-superior','atlantica-sungarden-beach'])
def test_silence_about_bunk_is_never_a_mismatch(slug):
 for r in rooms_of(FIX/(slug+'.html')):
  if not mentions_bunk(f"{r['name']}: {r['description']}"):
   assert r['values'].get('no_bunk') is not False,r['name']

@pytest.mark.parametrize('index',range(6))
def test_bunk_mismatch_needs_explicit_mention_in_snapshots(index):
 for r in rooms_of(ROOT/'data'/f'exim-{index}.html'):
  if r['values'].get('no_bunk') is False:
   assert mentions_bunk(f"{r['name']}: {r['description']}"),r['name']

def test_bunk_reference_counts_over_archived_exim():
 # Archivovaná HTML jsou neměnná, proto zde fixujeme i referenční počty.
 rooms=[r for i in range(6) for r in rooms_of(ROOT/'data'/f'exim-{i}.html')]
 flagged=[r for r in rooms if r['values'].get('no_bunk') is False]
 assert len(rooms)==36 and len(flagged)==5
 assert all(mentions_bunk(f"{r['name']}: {r['description']}") for r in flagged)

def test_bunk_wording_is_literal_not_optimistic():
 assert core.room_values('Rodinný pokoj s palandou')['no_bunk'] is False
 assert core.room_values('Family room, bunk bed available for the 4th person')['no_bunk'] is False
 assert core.room_values('Rodinný pokoj, dvě jednolůžkové postele pro děti')['no_bunk'] is True
 assert core.room_values('Rodinný pokoj bez palandy')['no_bunk'] is True
 # Zdroje absenci palandy dle uživatele nepíší; jiná negace se nedokládá a řeší ji ruční ověření.
 assert core.room_values('Palanda není k dispozici')['no_bunk'] is False
 assert 'no_bunk' not in core.room_values('Rodinný pokoj, 2 místnosti')

# --- Dveře mezi pokoji: záleží na skloňování i na tom, co dveře dělí ---
def test_doors_dividing_rooms_are_recorded():
 # Nahlášeno uživatelem: EXIM píše „dvě místnosti oddělené dveřmi“ a parser to přehlédl.
 v=core.room_values('Rodinný pokoj: dvě místnosti oddělené dveřmi, pokoje umístěné v bungalovech')
 assert v['separate'] is True and v['doors'] is True
 assert core.room_values('Family room: two rooms separated by a door')['doors'] is True
 assert core.room_values('Rodinný pokoj, propojený: dva propojené pokoje')['separate'] is True
 assert core.room_values('Ložnice oddělena posuvnými dveřmi')['doors'] is True

def test_balcony_door_is_not_treated_as_a_room_divider():
 assert 'doors' not in core.room_values('Suita: jedna prostorná místnost, dveře na balkon, terasa')
 assert 'doors' not in core.room_values('Pokoj s výhledem: dveře, okno, vysoušeč vlasů')

def test_explicitly_undivided_rooms_are_a_mismatch_not_a_maybe():
 assert core.room_values('Mezonet: v přízemí ložnice, v patře druhá ložnice, nejsou oddělené dveřmi')['doors'] is False
