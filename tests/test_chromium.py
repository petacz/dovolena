"""Local E2E: real Chromium + real Flask + disposable SQLite, external network blocked."""
import json,sqlite3
from pathlib import Path
import pytest
from playwright.sync_api import expect
from conftest import ROOT
pytestmark=pytest.mark.chromium

def test_default_all_variants_and_optional_filters(page):
 expect(page.locator('.card')).to_have_count(6)
 data=page.request.get(page.url+'api/hotels').json()
 expect(page.locator('.variant-row')).to_have_count(data['room_total'])
 expect(page.locator('#showAll')).to_be_checked()
 for key in ['separate','twin','no_bunk','sand']:expect(page.locator(f'[data-key="{key}"]')).to_be_checked()
 for key in ['doors','gentle']:expect(page.locator(f'[data-key="{key}"]')).not_to_be_checked()
 assert page.locator('.assessment.fail').count()>0
 assert page.locator('.assessment.unknown').count()>0
 assert page.locator('.gentle-bonus').count()>0

def test_beach_verdict_once_per_hotel_not_per_variant(page):
 # Pláž je údaj celého hotelu: musí se objevit jednou v kartě a ani jednou u varianty.
 for key in ['separate','twin','no_bunk','sand']:page.locator(f'[data-key="{key}"]').check()
 page.wait_for_function("()=>document.querySelectorAll('.card .assessment.hotel').length>0")
 for card in page.locator('.card').all():
  assert card.locator('.assessment.hotel').count()==1
  variants=card.locator('.variant-row').all_inner_texts()
  assert variants and all('Pouze písek' not in v for v in variants)
 text=page.locator('.assessment.hotel').first.inner_text()
 assert 'Pouze písek' in text or 'Nedoloženo' not in text
 assert 'Hotel:' in page.locator('#assessmentSummary').inner_text()


def test_search_empty_and_reset(page):
 page.locator('#search').fill('Ninos')
 expect(page.locator('.card')).to_have_count(1)
 expect(page.locator('.card h2')).to_contain_text('Ninos')
 page.locator('#search').fill('zz-not-a-real-hotel-2026')
 expect(page.locator('.card')).to_have_count(0)
 expect(page.locator('.empty')).to_be_visible()
 page.locator('#reset').click()
 expect(page.locator('.card')).to_have_count(6)
 expect(page.locator('[data-key="separate"]')).not_to_be_checked()
 page.locator('#family').click()
 expect(page.locator('[data-key="separate"]')).to_be_checked()
 expect(page.locator('[data-key="doors"]')).not_to_be_checked()

def test_saved_persists_after_reload(page):
 first=page.locator('.card').first;name=first.locator('h2').inner_text()
 first.locator('.heart').click();expect(page.locator('#savedCount')).to_have_text('1')
 page.locator('#saved').click();expect(page.locator('.card')).to_have_count(1)
 expect(page.locator('.card h2')).to_have_text(name)
 page.reload();expect(page.locator('#savedCount')).to_have_text('1')
 page.locator('#saved').click();expect(page.locator('.card')).to_have_count(1)
 page.locator('.heart').click();expect(page.locator('.card')).to_have_count(0)

def test_strict_filter_keeps_all_rooms_of_matching_hotels(page):
 with page.expect_response(lambda r:'/api/hotels?' in r.url) as response:page.locator('#showAll').uncheck()
 data=response.value.json()
 expect(page.locator('.card')).to_have_count(data['total'])
 expect(page.locator('.variant-row')).to_have_count(sum(len(h['rooms']) for h in data['items']))
 assert data['total']<6
 with page.expect_response(lambda r:'/api/hotels?' in r.url) as response:page.locator('#unknown').check()
 expect(page.locator('.card')).to_have_count(response.value.json()['total'])
 page.locator('#showAll').check();expect(page.locator('.card')).to_have_count(6)

def test_detail_manual_evidence_is_persisted(page):
 page.locator('[data-detail]').first.click();expect(page.locator('#detail')).to_be_visible()
 page.locator('#detail [data-edit="hotel"]').click()
 page.locator('#editKey').select_option('gentle');page.locator('#editValue').select_option('true')
 quote='Chromium regresní test: hotel potvrdil pozvolný vstup.'
 page.locator('#editQuote').fill(quote);page.locator('#editUrl').fill('https://example.com/evidence')
 with page.expect_response(lambda r:'/api/facts' in r.url and r.request.method=='POST') as response:
  page.locator('#editForm button[type=submit], #editForm button.primary').click()
 assert response.value.ok
 expect(page.locator('#editDialog')).not_to_be_visible()
 expect(page.locator('#detailContent')).to_contain_text(quote)
 page.locator('#closeDetail').click();page.reload();page.locator('[data-detail]').first.click()
 expect(page.locator('#detailContent')).to_contain_text(quote)
 expect(page.locator('#detail .gentle-bonus')).to_be_visible()

def test_custom_field_creation(page):
 page.locator('#openField').click()
 page.locator('[name=label]').fill('Dětský klub');page.locator('[name=key]').fill('kids_club')
 page.locator('[name=scope]').select_option('hotel');page.locator('#fieldForm button').click()
 expect(page.locator('[data-key=kids_club]')).to_be_visible()
 data=page.request.get(page.url+'api/fields').json()
 assert any(x['key']=='kids_club' and x['scope']=='hotel' for x in data)

def test_csv_and_consistent_sqlite_download(page,tmp_path):
 with page.expect_download() as dl:page.locator('#export').click()
 csv=tmp_path/'export.csv';dl.value.save_as(csv)
 assert csv.read_text(encoding='utf-8-sig').startswith('Hotel,Lokalita,Pokoj')
 with page.expect_download() as dl:page.locator('#backup').click()
 db=tmp_path/'backup.sqlite';dl.value.save_as(db)
 with sqlite3.connect(db) as c:
  assert c.execute('pragma integrity_check').fetchone()[0]=='ok'
  assert c.execute('select count(*) from hotels').fetchone()[0]==6

def test_mobile_no_horizontal_overflow(page):
 page.set_viewport_size({'width':390,'height':844})
 expect(page.locator('.card')).to_have_count(6)
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
 page.locator('[data-detail]').first.click()
 expect(page.locator('#detail')).to_be_visible()
 assert page.evaluate('document.querySelector("#detail").getBoundingClientRect().right <= innerWidth+1')

@pytest.fixture
def larger_catalog(local_app):
 import core
 html=(ROOT/'data/exim-0.html').read_text()
 for i in range(25):core.save_exim(f'https://www.eximtours.cz/recko/test/extra-{i}',html,name=f'Zzz test hotel {i:02}')

@pytest.mark.usefixtures('larger_catalog')
def test_catalog_pagination(page):
 expect(page.locator('.card')).to_have_count(24)
 expect(page.locator('#pagination')).to_contain_text('1 / 2')
 page.locator('#next').click();expect(page.locator('.card')).to_have_count(7)
 expect(page.locator('#pagination')).to_contain_text('2 / 2')
 page.locator('#prev').click();expect(page.locator('.card')).to_have_count(24)

@pytest.fixture
def incomplete_catalog(local_app):
 import core
 core.save_exim('https://www.eximtours.cz/kypr/test/incomplete',(ROOT/'tests/fixtures/asterias-beach-hotel.html').read_text())

@pytest.mark.usefixtures('incomplete_catalog')
def test_missing_source_data_visible_not_hidden_or_pass(page):
 expect(page.locator('.card')).to_have_count(7)
 card=page.locator('.card').filter(has=page.get_by_role('heading',name='Asterias Beach',exact=True))
 expect(card.locator('.import-warning')).to_contain_text('pouze metadata')
 expect(card.locator('.variant-row')).to_have_count(0)
 expect(card.locator('.origin')).to_contain_text('Kypr')
 card.locator('[data-detail]').click()
 expect(page.locator('#detail .import-warning')).to_be_visible()

def test_import_validation_and_dialog(page):
 page.locator('#openImport').click();expect(page.locator('#importDialog')).to_be_visible()
 page.locator('#urls').fill('https://example.com/not-exim')
 page.locator('#startImport').click()
 expect(page.locator('#toast')).to_contain_text('www.eximtours.cz')
 expect(page.locator('#startImport')).to_be_enabled()
 assert page.request.get(page.url+'api/jobs').json()==[]

@pytest.mark.parametrize('incomplete',[False,True])
def test_import_job_completion_ui(page,monkeypatch,incomplete):
 import app as web
 def fake_run(urls,progress):
  progress('1/1 · lokální simulace importu')
  return {'ok':1,'complete':0 if incomplete else 1,'incomplete':int(incomplete),'errors':[],
          'warnings':[{'url':urls[0],'messages':['Ve zdroji chybí popis pokojů.']}] if incomplete else [],
          'discovery':['Kontrola stránkování'],'note':'Lokální UI test, bez EXIM.'}
 monkeypatch.setattr(web,'run',fake_run)
 page.locator('#openImport').click();page.locator('#urls').fill('https://www.eximtours.cz/recko/test/hotel')
 page.locator('#startImport').click()
 expect(page.locator('#jobs')).to_contain_text('pouze metadata: '+str(int(incomplete)),timeout=10000)
 expect(page.locator('#jobs')).to_contain_text('Dokončeno s upozorněními' if incomplete else 'Dokončeno')
 if incomplete:expect(page.locator('#jobs')).to_contain_text('chybí popis pokojů')
 assert page.request.get(page.url+'api/jobs').json()[0]['status']==('partial' if incomplete else 'done')

@pytest.fixture
def actual_large_catalog(local_app):
 import core
 folder=ROOT/'tests/fixtures/catalog-190'
 with core.connect() as c:
  for table in ['facts','rooms','sources','hotels']:c.execute(f'DELETE FROM {table}')
 for record in json.loads((folder/'manifest.json').read_text())['records']:
  core.save_exim(record['url'],(folder/record['file']).read_text())

@pytest.mark.usefixtures('actual_large_catalog')
def test_real_190_catalog_all_eight_ui_pages(page,report_dir):
 expect(page.locator('#totalHotels')).to_have_text('190')
 expect(page.locator('#totalRooms')).to_have_text('929')
 ids=[];rooms=0
 for number in range(1,9):
  expect(page.locator('#pagination')).to_contain_text(f'{number} / 8')
  expect(page.locator('.card')).to_have_count(24 if number<8 else 22)
  ids.extend(page.locator('[data-detail]').evaluate_all('(els)=>els.map(e=>e.dataset.detail)'))
  rooms+=page.locator('.variant-row').count()
  if number<8:page.locator('#next').click()
 assert len(ids)==len(set(ids))==190 and rooms==929
 (report_dir/'chromium-large-catalog.json').write_text(json.dumps({'mode':'Chromium over archived live descriptions, offline','pages':8,'unique_records':len(set(ids)),'room_records':rooms},indent=2))
 page.locator('#search').fill('Asterias Beach')
 expect(page.locator('.card')).to_have_count(1)
 expect(page.locator('.import-warning')).to_contain_text('pouze metadata')
 expect(page.locator('.variant-row')).to_have_count(0)

@pytest.fixture
def priced_catalog(local_app):
 from test_prices import seeded_prices
 return seeded_prices()

@pytest.mark.usefixtures('priced_catalog')
def test_prices_correct_variant_family_context_and_evidence(page):
 page.locator('#search').fill('High Beach')
 expect(page.locator('.card')).to_have_count(1)
 expect(page.locator('#priceContext')).to_contain_text('9/7')
 expect(page.locator('.room-price')).to_have_count(2)
 expect(page.locator('.price-missing')).to_have_count(7)
 page.locator('[data-detail]').click()
 expect(page.locator('#detail .room-price-detail')).to_have_count(2)
 expect(page.locator('#detail')).to_contain_text('184')
 expect(page.locator('#detail')).to_contain_text('za rodinu')
 expect(page.locator('#detail a[href^="/api/price-offers/"]').first).to_be_visible()

@pytest.mark.usefixtures('priced_catalog')
def test_price_csv_download_and_context_dialog(page,tmp_path):
 page.locator('#openPrices').click()
 expect(page.locator('#priceDialog')).to_be_visible()
 assert 'ka1=9|7' in page.locator('#priceUrl').input_value()
 page.locator('#priceDialog .close').click()
 with page.expect_download() as dl:page.locator('#exportPrices').click()
 target=tmp_path/'prices.csv';dl.value.save_as(target)
 assert '184640' in target.read_text(encoding='utf-8-sig')

@pytest.fixture
def unmapped_price_catalog(priced_catalog):
 import core
 with core.connect() as c:c.execute('update room_offers set room_id=NULL')

@pytest.mark.usefixtures('unmapped_price_catalog')
def test_unmapped_price_types_are_separate_not_inferred(page):
 page.locator('#search').fill('High Beach');expect(page.locator('.card')).to_have_count(1)
 expect(page.locator('.room-price')).to_have_count(0)
 expect(page.locator('.unmapped-price-note')).to_be_visible()
 page.locator('[data-detail]').click()
 expect(page.locator('.price-only-room')).to_have_count(2)
 expect(page.locator('.unmapped-prices')).to_contain_text('Neztotožňujeme je odhadem')
