"""Opt-in live contracts. Run with -m 'live and not bulk' or -m 'live and bulk'."""
import os,json,time,hashlib,sqlite3
from pathlib import Path
import pytest
from conftest import ROOT
import core,importer
pytestmark=pytest.mark.live

def source_file(kind):
 override=os.getenv('EXIM_LIVE_URL' if kind=='large' else 'EXIM_LIVE_SMALL_URL')
 return override or (ROOT/'data'/('search_large_url.txt' if kind=='large' else 'search_url.txt')).read_text().strip()

@pytest.fixture(scope='module')
def catalog(report_dir):
 events=[];start=time.monotonic()
 links=importer.discover(source_file('large'),events.append,keep_context=True)
 result={'source':source_file('large'),'fetched':core.now(),'seconds':time.monotonic()-start,'unique_hotels':len(links),'progress':events,'urls':links}
 (report_dir/'live-discovery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 # Deliberately not ==190: live availability can change. Contract requires actual pagination.
 assert len(links)>20,'Large search no longer exercises pagination; refresh EXIM_LIVE_URL.'
 assert len(links)==len(set(links))
 return links

def test_live_small_api_without_browser(monkeypatch):
 monkeypatch.setattr(importer,'discover_browser',lambda *a,**k:pytest.fail('Browser was invoked'))
 links=importer.discover(source_file('small'))
 assert links,'Small live search returned no hotels; inspect source or update fixture URL.'
 assert all(x.startswith('https://www.eximtours.cz/') for x in links)

def test_live_large_all_pages(catalog):
 assert len(catalog)>20

def test_live_sample_detail_contract(catalog,report_dir):
 records=[]
 for u in [catalog[0],catalog[len(catalog)//2],catalog[-1]]:
  text=importer.fetch(u);p=core.parse_exim(text)
  assert p['name'] and p['rooms'] and p['beach']
  assert all(r['name'] and r['description'] for r in p['rooms'])
  records.append({'url':u,'name':p['name'],'rooms':len(p['rooms'])});time.sleep(.6)
 (report_dir/'live-samples.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))

@pytest.mark.bulk
def test_live_full_catalog_import(catalog,isolated_db,report_dir,monkeypatch):
 start=time.monotonic();records=[];original_fetch=importer.fetch
 cache=Path(os.environ['EXIM_SAVE_HTML']) if os.getenv('EXIM_SAVE_HTML') else None
 if cache:cache.mkdir(parents=True,exist_ok=True)
 def checked_fetch(url):
  text=original_fetch(url)
  if cache:(cache/(hashlib.sha256(url.encode()).hexdigest()+'.html')).write_text(text)
  return text
 monkeypatch.setattr(importer,'fetch',checked_fetch)
 result=importer.run(catalog,lambda message:print(message,flush=True))
 with core.connect() as c:
  counts={table:c.execute(f'SELECT count(*) FROM {table}').fetchone()[0] for table in ['hotels','rooms','sources']}
  result['integrity']=c.execute('PRAGMA integrity_check').fetchone()[0]
  for h in c.execute('SELECT id,name,url,sections FROM hotels'):
   rooms=c.execute('SELECT name,description FROM rooms WHERE hotel_id=?',(h['id'],)).fetchall()
   records.append({'name':h['name'],'url':h['url'],'rooms':len(rooms)})
  # Export test dataset, never overwrite the supplied/user database.
  with sqlite3.connect(report_dir/'live-catalog.sqlite',factory=core.Connection) as target:c.backup(target)
 result.update(counts=counts,seconds=time.monotonic()-start,source=source_file('large'),fetched=core.now(),hotels=records)
 (report_dir/'live-import.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 assert not result['errors'],json.dumps(result['errors'],ensure_ascii=False)
 assert result['ok']==len(catalog)==counts['hotels']
 assert result['complete']+result['incomplete']==result['ok']
 assert result['integrity']=='ok'
 assert all(h['rooms']>0 or any(w['url'].split('?')[0]==h['url'] for w in result['warnings']) for h in records)

def test_live_repaired_description_formats(catalog,report_dir):
 """Recheck the three specifically corrected edge cases without repeating all 190 downloads."""
 rows=[]
 for slug,expected in [('thalassa-superior',7),('atlantica-sungarden-beach',6),('apartmentos-estival-park',1)]:
  u=next(u for u in catalog if u.split('?')[0].endswith('/'+slug))
  p=core.parse_exim(importer.fetch(u));rows.append({'url':u,'name':p['name'],'rooms':len(p['rooms']),'warnings':p['warnings']})
  assert len(p['rooms'])==expected and not p['warnings']
  time.sleep(.6)
 (report_dir/'live-repaired-formats.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
