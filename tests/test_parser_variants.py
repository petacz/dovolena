from pathlib import Path
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
