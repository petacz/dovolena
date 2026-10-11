import copy,json
from pathlib import Path
import pytest
import core,prices
from conftest import ROOT
pytestmark=pytest.mark.unit
F=ROOT/'tests/fixtures/prices'
URL=(ROOT/'data/search_prices_url.txt').read_text().strip()
def sample():
 ctx=prices.context(URL);template=json.loads((F/'template.json').read_text());data=json.loads((F/'offer-options.json').read_text())
 url='https://www.eximtours.cz/recko/kreta/stalis-malia-a-stalida/hotel-high-beach?'+template['tourFilterQuery']
 return ctx,template,data,url

def seeded_prices():
 ctx,t,d,u=sample();hid=core.save_exim(u,(F/'hotel.html').read_text());records,codes=prices.extract_offers(d,ctx,t,u)
 with core.connect() as c:
  sid=c.execute('insert into price_searches(url,context,started,finished,status,report) values(?,?,?,?,?,?)',(URL,json.dumps(ctx),core.now(),core.now(),'done',json.dumps({'hotels_with_prices':1}))).lastrowid
  c.execute("insert into price_hotels values(?,?,'priced','')",(sid,hid))
 prices.save_offers(sid,hid,records,t)
 return hid,sid

def test_corrected_age_and_scope():
 c=prices.context(URL);assert c['children']==[9,7] and c['adults']==2 and c['nights']==[10,11,12,13,14,15]
 assert c['from']=='2027-07-24' and c['to']=='2027-08-22'

def test_missing_parameters_are_validation_error():
 with pytest.raises(ValueError):prices.context('https://www.eximtours.cz/vysledky-vyhledavani')

def test_range_clears_package_and_dates_use_latest_departure():
 ctx,t,d,u=sample();payload=prices.range_filter(t,ctx,'FR02')
 assert payload['offerDate']['dateTo']=='2027-08-12T00:00:00'
 assert payload['packageId']=='' and payload['flight']['outboundIdentifier']['flightCode']==''
 assert payload['rooms'][0]['roomCode']=='FR02'
 assert [x['age'] for x in payload['rooms'][0]['travellers'] if x['type']==1]==[9,7]
 assert t['packageId'] # input not mutated

def test_total_not_per_person_or_hotel_minimum():
 ctx,t,d,u=sample();r,codes=prices.extract_offers(d,ctx,t,u)
 assert next(x for x in r if x['room_code']=='MA01')['total']==175960
 assert next(x for x in r if x['room_code']=='FR02')['total']==184640
 assert all(x['total']!=56410 for x in r)
 assert codes==['MA01','FR02']

@pytest.mark.parametrize('mutation', ['age','hotel','provider','room','return_date','nights','airport','meal'])
def test_incompatible_response_never_assigned(mutation):
 ctx,t,d,u=sample();requested=''
 if mutation=='age':d['offer']['rooms'][0]['travellers'][-1]['age']=6
 if mutation=='hotel':d['offer']['hotelDataKey']['hotelId']=999
 if mutation=='provider':d['offer']['hotelDataKey']['bedBankID']='different'
 if mutation=='room':requested='FR02'
 if mutation=='return_date':d['offer']['dateTo']='2027-08-25T00:00:00'
 if mutation=='nights':d['offer']['nights']=7
 if mutation=='airport':d['offer']['outbound']['flightSegments'][0]['departureAirport']['id']=123
 if mutation=='meal':d['offer']['mealCode']='BB'
 with pytest.raises(ValueError):prices.extract_offers(d,ctx,t,u,requested)

def test_no_offer_means_unknown_not_sold_out():
 ctx,t,d,u=sample();d['offer']=None;assert prices.extract_offers(d,ctx,t,u)==([],[])

def test_price_match_exact_name_and_provider_only(isolated_db):
 hid,sid=seeded_prices()
 with core.connect() as c:
  rows=c.execute('select * from room_offers').fetchall();assert len(rows)==2 and all(r['room_id'] for r in rows)
  record=json.loads(rows[0]['data']);record['room_name']+=' podobný';assert prices.match_room(c,hid,record) is None
  record=json.loads(rows[0]['data']);record['provider']='256|different|other';assert prices.match_room(c,hid,record) is None

def test_no_price_copied_to_other_general_types(isolated_db):
 hid,sid=seeded_prices()
 with core.connect() as c:h=core.hotel_record(c,c.execute('select * from hotels where id=?',(hid,)).fetchone(),True)
 assert len(h['rooms'])==9 and sum(bool(r['offers']) for r in h['rooms'])==2
 assert all(not r['offers'] for r in h['rooms'] if r['name'].startswith('Dvoulůžkový'))

def test_price_storage_preserves_all_catalog_and_manual_facts(isolated_db):
 hid,sid=seeded_prices()
 with core.connect() as c:
  before=[tuple(r) for r in c.execute('select * from rooms')];facts=[tuple(r) for r in c.execute('select * from facts')]
 ctx,t,d,u=sample();r,_=prices.extract_offers(d,ctx,t,u);prices.save_offers(sid,hid,r,t)
 with core.connect() as c:
  assert before==[tuple(r) for r in c.execute('select * from rooms')]
  assert facts==[tuple(r) for r in c.execute('select * from facts')]
  assert c.execute('select count(*) from room_offers').fetchone()[0]==2

def test_new_search_does_not_leak_previous_prices(isolated_db):
 hid,sid=seeded_prices()
 with core.connect() as c:
  c.execute('insert into price_searches(url,context,status) values(?,?,?)',(URL,json.dumps(prices.context(URL)),'done'))
  h=core.hotel_record(c,c.execute('select * from hotels where id=?',(hid,)).fetchone())
 assert all(not r['offers'] for r in h['rooms']) and h['price_status']['status']=='outside_search'

def test_price_export_and_evidence(local_app):
 hid,sid=seeded_prices();client=local_app.test_client()
 csv=client.get('/api/prices.csv');assert csv.status_code==200 and '184640' in csv.get_data(as_text=True)
 with core.connect() as c:oid=c.execute('select id from room_offers limit 1').fetchone()[0]
 evidence=client.get('/api/price-offers/'+str(oid)).json
 assert evidence['request']['rooms'][0]['travellers'][-1]['age']==7
 assert evidence['data']['raw']['price']
 assert client.post('/api/prices/refresh',json={'url':URL}).status_code==403

def test_over_budget_is_labeled_not_hidden():
 ctx,t,d,u=sample();d['roomOptions'][1]['price']['price']=250000
 r,_=prices.extract_offers(d,ctx,t,u)
 assert next(x for x in r if x['room_code']=='FR02')['over_budget'] is True

def test_entire_price_refresh_keeps_existing_rooms_and_manual_facts(isolated_db,monkeypatch):
 hid,_=seeded_prices();ctx,t,d,u=sample()
 with core.connect() as c:
  source=c.execute('select id from sources where hotel_id=?',(hid,)).fetchone()[0]
  core.fact(c,hid,None,'gentle',True,'Ruční ověření, ponechat.',source,'manual')
  before_rooms=[tuple(r) for r in c.execute('select * from rooms')]
  before_facts=[tuple(r) for r in c.execute('select * from facts')]
 monkeypatch.setattr(prices.importer,'discover',lambda *a,**k:[u])
 monkeypatch.setattr(prices.importer,'fetch',lambda _: (F/'hotel.html').read_text())
 monkeypatch.setattr(prices,'template_from_html',lambda _:t)
 monkeypatch.setattr(prices.time,'sleep',lambda _:None)
 second=json.loads((F/'range-FR02.json').read_text())
 monkeypatch.setattr(prices,'request_options',lambda payload: second if payload['rooms'][0]['roomCode']=='FR02' else d)
 result=prices.run_prices(URL,lambda _:None)
 assert result['processed']==1 and result['offers']==2 and not result['errors']
 with core.connect() as c:
  assert before_rooms==[tuple(r) for r in c.execute('select * from rooms')]
  assert before_facts==[tuple(r) for r in c.execute('select * from facts')]

def test_price_refresh_stops_at_access_limit(isolated_db,monkeypatch):
 import requests
 hid,_=seeded_prices();ctx,t,d,u=sample()
 monkeypatch.setattr(prices.importer,'discover',lambda *a,**k:[u,u.replace('hotel-high-beach','second')])
 monkeypatch.setattr(prices.importer,'fetch',lambda _: (F/'hotel.html').read_text())
 monkeypatch.setattr(prices,'template_from_html',lambda _:t)
 monkeypatch.setattr(prices.time,'sleep',lambda _:None)
 response=requests.Response();response.status_code=429;calls=[]
 def blocked(payload):calls.append(payload);raise requests.HTTPError(response=response)
 monkeypatch.setattr(prices,'request_options',blocked)
 result=prices.run_prices(URL,lambda _:None)
 assert len(calls)==1 and result['errors'] and result['processed']==0
 with core.connect() as c:assert c.execute('select status from price_searches order by id desc limit 1').fetchone()[0]=='partial'

def test_real_empty_offer_schema_does_not_expand_dates():
 raw=json.loads((F/'empty-offer.json').read_text())
 assert 'offer' not in raw
 normalized=prices.normalize_response(raw)
 assert normalized['offer'] is None
 ctx,t,_,u=sample();assert prices.extract_offers(normalized,ctx,t,u)==([],[])
 # Suggested search goes outside the user's period. It must never be followed.
 assert '2027-09-22' in raw['defaultSearchUrl']
 with pytest.raises(ValueError):prices.normalize_response({'unknown':'schema'})

def test_missing_price_rechecks_stay_lengths(isolated_db,monkeypatch):
 hid,_=seeded_prices();ctx,t,d,u=sample()
 monkeypatch.setattr(prices.importer,'discover',lambda *a,**k:[u])
 monkeypatch.setattr(prices.importer,'fetch',lambda _: (F/'hotel.html').read_text())
 monkeypatch.setattr(prices,'template_from_html',lambda _:t)
 monkeypatch.setattr(prices.time,'sleep',lambda _:None)
 outside=copy.deepcopy(d);outside['offer']['dateTo']='2027-08-25T00:00:00'
 empty=prices.normalize_response(json.loads((F/'empty-offer.json').read_text()))
 def response(payload):
  if len(payload['numberNights'])>1:return outside
  return d if payload['numberNights']==[10] else empty
 monkeypatch.setattr(prices,'request_options',response)
 result=prices.run_prices(URL,lambda _:None)
 assert result['offers']==2 and result['additional_stay_checks']['hotels_checked']==1
 assert not result['additional_stay_checks']['errors']
