import json
from unittest.mock import patch
from urllib.parse import parse_qs,urlparse
import pytest
import importer
pytestmark=pytest.mark.unit
URL='https://www.eximtours.cz/vysledky-vyhledavani?ac1=2&pstg=80&sortby=Rating.TrustYou'
def payload(names,total):return json.dumps({'tours':[{'detailUrl':f'/recko/test/{name}?HID=1'} for name in names],'toursCount':total})
def test_all_pages_offset_and_preserved_parameters():
 with patch('importer.fetch',side_effect=[payload(['a','b'],5),payload(['c','d'],5),payload(['e'],5)]) as fetch,patch('importer.time.sleep'):
  links=importer.discover(URL)
 assert len(links)==5
 queries=[parse_qs(urlparse(call.args[0]).query) for call in fetch.call_args_list]
 assert [q['pstg'] for q in queries]==[['0'],['2'],['4']]
 assert all(q['sortby']==['Rating.TrustYou'] and q['ac1']==['2'] for q in queries)
def test_repeated_page_fails_not_silently_twenty():
 with patch('importer.fetch',return_value=payload(['a','b'],4)),patch('importer.time.sleep'):
  with pytest.raises(importer.DiscoveryError,match='opakuje'):importer.discover(URL)
def test_changed_total_is_error():
 with patch('importer.fetch',side_effect=[payload(['a','b'],4),payload(['c','d'],5)]),patch('importer.time.sleep'):
  with pytest.raises(importer.DiscoveryError,match='změnil'):importer.discover(URL)
def test_mid_pagination_failure_no_fallback():
 with patch('importer.fetch',side_effect=[payload(['a','b'],4),'{}']),patch('importer.time.sleep'),patch('importer.discover_browser') as browser:
  with pytest.raises(importer.DiscoveryError):importer.discover(URL)
  browser.assert_not_called()
def test_safety_limit(monkeypatch):
 monkeypatch.setenv('MAX_IMPORT_HOTELS','3')
 with patch('importer.fetch',return_value=payload(['a','b'],4)):
  with pytest.raises(importer.DiscoveryError,match='limit'):importer.discover(URL)
def test_same_hotel_in_different_offers_deduped():
 with patch('importer.fetch',side_effect=[payload(['a','b'],4),payload(['b','c'],4)]),patch('importer.time.sleep'):
  assert len(importer.discover(URL))==3

def test_context_preserved_but_same_hotel_offers_deduped():
 body=json.dumps({'tours':[{'detailUrl':'/recko/test/a?DS=256&DD=2027-08-01'}, {'detailUrl':'/recko/test/a?DS=8192&DD=2027-08-02'}],'toursCount':2})
 with patch('importer.fetch',return_value=body):
  assert importer.discover(URL,keep_context=True)==['https://www.eximtours.cz/recko/test/a?DS=256&DD=2027-08-01']

def test_import_stops_on_detail_rate_limit(isolated_db):
 import requests
 response=requests.Response();response.status_code=429
 urls=['https://www.eximtours.cz/recko/test/a','https://www.eximtours.cz/recko/test/b']
 with patch('importer.fetch',side_effect=requests.HTTPError(response=response)) as fetch:
  result=importer.run(urls)
 assert fetch.call_count==1
 assert result['attempted']==1 and result['discovered']==2 and result['ok']==0 and result['errors']
