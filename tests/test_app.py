import os,sys,tempfile,shutil,sqlite3,unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
TMP=tempfile.TemporaryDirectory();os.environ['DATA_DIR']=TMP.name
for name in ['search_links.json']+[f'exim-{i}.html' for i in range(6)]:shutil.copy2(ROOT/'data'/name,Path(TMP.name)/name)
import core
from app import app
from importer import validate
BASE=Path(TMP.name)/'base.sqlite'
with core.connect() as src,sqlite3.connect(BASE,factory=core.Connection) as dst:src.backup(dst)
H={'X-Hotel-Lens':'1'}
class Tests(unittest.TestCase):
 def setUp(self):
  core.DB=Path(TMP.name)/('test-'+self._testMethodName+'.sqlite');shutil.copy2(BASE,core.DB);self.client=app.test_client()
 def query(self,filters,unknown=False):return self.client.get('/api/hotels',query_string={'filters':json.dumps(filters),'unknown':int(unknown)}).json
 def test_search_api_url(self):
  from importer import api_search_url
  from urllib.parse import urlparse,parse_qs
  u=api_search_url('https://www.eximtours.cz/vysledky-vyhledavani?ac1=2&ka1=9%7C7')
  self.assertEqual(urlparse(u).path,'/api/searchapi/getsearchresult')
  self.assertEqual(parse_qs(urlparse(u).query),{'ac1':['2'],'ka1':['9|7'],'sc':['residential']})
 def test_search_api_no_browser(self):
  from unittest.mock import patch
  from importer import discover
  body=json.dumps({'tours':[{'detailUrl':'/recko/test/hotel?HID=1'},{'detailUrl':'/recko/test/hotel?HID=1&NN=7'}],'toursCount':2})
  with patch('importer.fetch',return_value=body) as fetch,patch('importer.discover_browser') as browser:
   result=discover('https://www.eximtours.cz/vysledky-vyhledavani?ac1=2')
   self.assertEqual(result,['https://www.eximtours.cz/recko/test/hotel']);self.assertEqual(fetch.call_count,1);browser.assert_not_called()
 def test_search_api_invalid_schema_fails_closed(self):
  from unittest.mock import patch
  from importer import discover,DiscoveryError
  with patch('importer.fetch',return_value='{}') as fetch,patch('importer.discover_browser') as browser:
   with self.assertRaises(DiscoveryError):discover('https://www.eximtours.cz/vysledky-vyhledavani')
   self.assertEqual(fetch.call_count,1);browser.assert_not_called()
 def test_search_api_403_no_bypass(self):
  from unittest.mock import patch
  import requests
  from importer import discover
  response=requests.Response();response.status_code=403
  with patch('importer.fetch',side_effect=requests.HTTPError(response=response)) as fetch,patch('importer.discover_browser') as browser:
   with self.assertRaises(ValueError):discover('https://www.eximtours.cz/vysledky-vyhledavani')
   self.assertEqual(fetch.call_count,1);browser.assert_not_called()
 def test_search_api_external_url_rejected(self):
  from importer import parse_search_response
  with self.assertRaises(ValueError):parse_search_response({'tours':[{'detailUrl':'https://example.com/hotel'}]})
 def test_search_api_empty_and_incomplete(self):
  from importer import parse_search_response
  self.assertEqual(parse_search_response({'tours':[],'toursCount':0}),([],0,0))
  with self.assertRaises(ValueError):parse_search_response({'tours':[],'toursCount':10})
  with self.assertRaises(ValueError):parse_search_response({'tours':[{}],'toursCount':1})
 def test_seed_and_rooms(self):
  d=self.client.get('/api/hotels').json;self.assertEqual(d['catalog_total'],6);self.assertEqual(d['room_total'],36)
 def test_search_accentless(self):self.assertEqual(self.client.get('/api/hotels?q=skafidia').json['total'],1)
 def test_sandy_excludes_pebbles_at_entry(self):
  names=[h['name'] for h in self.query([{'key':'sand','value':True}])['items']];self.assertEqual(len(names),4);self.assertFalse(any('Apollonia' in x for x in names));self.assertFalse(any('Ninos' in x for x in names))
 def test_initial_screen_without_doors(self):
  d=self.query([{'key':k,'value':True} for k in ['sand','separate','twin','no_bunk']])
  self.assertEqual(d['total'],1) # EXIM-only fixture; supplementary Kalogria is in delivered DB.
  self.assertIn('Aldemar',d['items'][0]['name'])
  self.assertEqual(len(d['items'][0]['matching_rooms']),2)
 def test_strict_family_zero(self):self.assertEqual(self.query([{'key':k,'value':True} for k in ['sand','separate','doors','twin','no_bunk']])['total'],0)
 def test_unknown_does_not_admit_known_false(self):self.assertEqual(self.query([{'key':'sand','value':True}],True)['total'],4)
 def test_area_lower_bound(self):self.assertEqual(core.area('27,50/29 m2'),27.5);self.assertEqual(core.area('35 – 40 sq.m.'),35)
 def test_no_inferred_bunk_absence(self):self.assertNotIn('no_bunk',core.room_values('Rodinný pokoj, 2 místnosti'))
 def test_no_bunk_negation(self):self.assertTrue(core.room_values('Pokoj bez palandy')['no_bunk'])
 def test_twin_beds_for_parents_not_children(self):self.assertNotIn('twin',core.room_values('Double room with 2 single beds'))
 def test_room_atomicity(self):
  with core.connect() as c:
   hid=c.execute('insert into hotels(url,name) values(?,?)',('https://example.com','Atomic test')).lastrowid
   for name,key in [('First','doors'),('Second','twin')]:
    rid=c.execute('insert into rooms(hotel_id,name,origin) values(?,?,?)',(hid,name,'test')).lastrowid;core.fact(c,hid,rid,key,True,'test',None)
  ids=[h['id'] for h in core.search(filters=[{'key':'doors','value':True},{'key':'twin','value':True}])];self.assertNotIn(hid,ids)
 def test_conflict_is_unknown(self):
  obs=[dict(key='doors',value='true',kind='auto',quote='A',source_id=1),dict(key='doors',value='false',kind='reviewed',quote='B',source_id=2)];v=core.effective(obs)['doors'];self.assertIsNone(v['value']);self.assertTrue(v['conflict'])
 def test_manual_survives_refresh(self):
  h=self.client.get('/api/hotels/6').json;rid=next(r['id'] for r in h['rooms'] if r['name']=='Rodinný pokoj, Výhled zahrada')
  r=self.client.post('/api/facts',json={'hotel_id':6,'room_id':rid,'key':'doors','value':True,'quote':'Hotel písemně potvrzuje dveře.','url':'https://example.com'},headers=H);self.assertEqual(r.status_code,200)
  core.save_exim(h['url'],(ROOT/'data/exim-5.html').read_text())
  h=self.client.get('/api/hotels/6').json;r=next(r for r in h['rooms'] if r['id']==rid);self.assertTrue(r['facts']['doors']['value']);self.assertEqual(len(h['rooms']),7)
 def test_failed_parser_preserves_data(self):
  with self.assertRaises(ValueError):core.save_exim('https://www.eximtours.cz/broken','<html>error</html>')
  self.assertEqual(self.client.get('/api/hotels').json['catalog_total'],6)
 def test_custom_field_and_filter(self):
  r=self.client.post('/api/fields',json={'key':'kitchenette','label':'Kuchyňka','type':'bool','scope':'room'},headers=H);self.assertEqual(r.status_code,200)
  rid=self.client.get('/api/hotels/6').json['rooms'][0]['id'];self.client.post('/api/facts',json={'hotel_id':6,'room_id':rid,'key':'kitchenette','value':True,'quote':'Doloženo testovacím zdrojem'},headers=H)
  self.assertEqual(self.query([{'key':'kitchenette','value':True}])['total'],1)
 def test_scope_validation(self):
  r=self.client.post('/api/facts',json={'hotel_id':6,'room_id':None,'key':'doors','value':True,'quote':'doloženo'},headers=H);self.assertEqual(r.status_code,400)
 def test_csrf(self):self.assertEqual(self.client.post('/api/fields',json={}).status_code,403)
 def test_url_validation(self):
  for u in ['http://127.0.0.1','https://www.eximtours.cz.evil.example/foo','file:///etc/passwd','https://user@www.eximtours.cz/foo']:
   with self.assertRaises(ValueError):validate(u)
 def test_csv_and_sqlite_export(self):
  self.assertIn('text/csv',self.client.get('/api/export.csv').content_type);self.assertTrue(self.client.get('/api/backup').data.startswith(b'SQLite format 3'))
if __name__=='__main__':unittest.main(verbosity=2)
