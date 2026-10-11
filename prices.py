"""Read-only EXIM price research; offers are separate from the general room catalog."""
import copy,hashlib,json,math,os,re,time,unicodedata
from pathlib import Path
from urllib.parse import urlparse,parse_qsl,urlencode
from datetime import date,timedelta
import requests
from bs4 import BeautifulSoup
import core,importer
ENDPOINT='https://www.eximtours.cz/api/SearchOffer/GetOfferWithOptions'

def context(url):
 if not isinstance(url,str):raise ValueError('Vložte výsledkový odkaz EXIM.')
 importer.validate(url)
 if urlparse(url).path.rstrip('/')!='/vysledky-vyhledavani':raise ValueError('Ceny vyžadují odkaz na hledání EXIM.')
 q={k.lower():v for k,v in parse_qsl(urlparse(url).query)}
 if not {'dd','rd','nn','ac1','kc1','ka1'}<=set(q):raise ValueError('V odkazu chybí termín, počet nocí nebo cestující.')
 adults=int(q.get('ac1','0'));ages=[int(x) for x in q.get('ka1','').split('|') if x]
 if adults!=2 or int(q.get('kc1','0'))!=len(ages) or len(ages)!=2 or q.get('ac2'):raise ValueError('Tento cenový konektor podporuje 1 pokoj, 2 dospělé a 2 děti.')
 start=date.fromisoformat(q['dd']);end=date.fromisoformat(q['rd']);nights=[int(x) for x in q['nn'].split('|')]
 if start>end or not nights or min(nights)<1 or max(nights)>31 or any(x<0 or x>17 for x in ages):raise ValueError('Neplatné termíny nebo věk.')
 return {'adults':adults,'children':ages,'from':str(start),'to':str(end),'nights':nights,'budget':float(q.get('pt') or 0),'airport_ids':[int(x) for x in q.get('to','').split('|') if x],'transport':int(q.get('tt') or 1),'meal_filter':q.get('m'),'currency':'CZK'}

def provider_key(key):
 return '|'.join(str(key.get(k,'')) for k in ['dataSource','bedBankID','bedBank'])
def url_provider(url):
 q={k.upper():v for k,v in parse_qsl(urlparse(url).query)}
 return '|'.join(q.get(k,'') for k in ['DS','PID','DPR'])
def room_name_key(s):
 # Exact title only, not semantic/fuzzy matching, accents preserved.
 return re.sub(r'\s+',' ',unicodedata.normalize('NFC',s)).strip(' :').casefold()

def template_from_html(html):
 soup=BeautifulSoup(html,'html.parser');el=soup.select_one('[data-component-name="abnbHotelDetail"] script[type="application/json"]')
 if not el:raise ValueError('Chybí zdrojové parametry cenového API.')
 state=json.loads(el.string or el.get_text());template=(state.get('dataNew') or {}).get('offerFilter')
 if not isinstance(template,dict) or not template.get('hotelDataKey'):raise ValueError('Zdroj neposkytl podporovaný cenový filtr.')
 return template

def range_filter(template,ctx,room_code=''):
 result=copy.deepcopy(template)
 result['packageId']='';result['flight']={k:{'flightClass':'','flightCode':'','flightNumber':''} for k in ['inboundIdentifier','outboundIdentifier']}
 result['offerDate']={'dateFrom':ctx['from']+'T00:00:00','dateTo':str(date.fromisoformat(ctx['to'])-timedelta(days=min(ctx['nights'])))+'T00:00:00','mainFilterDates':[ctx['from']+'T00:00:00',ctx['to']+'T00:00:00']}
 result['numberNights']=ctx['nights'];result['transportOrigin']=ctx['airport_ids'];result['transportType']=ctx['transport']
 # Keep exact meal code from the source offer rather than mixing unrelated board plans.
 travellers=[{'id':i+1,'type':0,'age':30} for i in range(ctx['adults'])]
 travellers += [{'id':ctx['adults']+i+1,'type':1,'age':age} for i,age in enumerate(ctx['children'])]
 result['rooms']=[{'groupId':1,'travellers':travellers,'roomCode':room_code}]
 # Query is context/evidence, not an authority for dates/occupancy in the response.
 return result

def request_options(payload):
 r=requests.post(ENDPOINT,json=payload,timeout=(10,60),allow_redirects=False,headers={'User-Agent':'HotelLens/1.0 (personal hotel research)'})
 r.raise_for_status()
 if r.is_redirect:raise ValueError('Neočekávané přesměrování cenového API.')
 if len(r.content)>8_000_000:raise ValueError('Cenová odpověď přesahuje 8 MB.')
 return normalize_response(r.json())

def normalize_response(d):
 if isinstance(d,dict) and 'offer' not in d and all(d.get(k)==[] for k in ['availableDates','alternativeStays','roomOptions','mealOptions','flightOptions']) and isinstance(d.get('defaultSearchUrl'),str):
  # Verified EXIM empty result omits the optional offer member. Never follow the suggested broader search URL.
  d={**d,'offer':None}
 if not isinstance(d,dict) or 'offer' not in d or not isinstance(d.get('roomOptions'),list):raise ValueError('Nerozpoznané schéma cenové odpovědi.')
 return d

def validate_offer(offer,ctx,expected_provider):
 if provider_key(offer.get('hotelDataKey',{}))!=expected_provider:raise ValueError('Odpověď změnila dodavatele hotelu.')
 rooms=offer.get('rooms') or []
 if len(rooms)!=1:raise ValueError('Nabídka není pro jeden pokoj; cenu nelze přiřadit jednotlivému typu.')
 travellers=rooms[0].get('travellers') or []
 if sum(t.get('type')==0 for t in travellers)!=ctx['adults'] or sorted(t['age'] for t in travellers if t.get('type')==1)!=sorted(ctx['children']) or len(travellers)!=ctx['adults']+len(ctx['children']):raise ValueError('Věk/obsazenost odpovědi nesouhlasí s hledáním.')
 a=offer['dateFrom'][:10];b=offer['dateTo'][:10];n=int(offer['nights'])
 date.fromisoformat(a);date.fromisoformat(b)
 if not (ctx['from']<=a<b<=ctx['to']) or n not in ctx['nights']:raise ValueError('Nabídka je mimo zadaný interval nebo počet nocí.')
 if offer.get('transferType')!=ctx['transport']:raise ValueError('Odpověď změnila druh dopravy.')
 segments=(offer.get('outbound') or {}).get('flightSegments') or []
 airport=segments[0]['departureAirport'] if segments else {}
 if ctx['airport_ids'] and airport.get('id') not in ctx['airport_ids']:raise ValueError('Odpověď změnila letiště odletu.')
 return rooms[0],a,b,n,airport

def extract_offers(response,ctx,template,hotel_url,requested_code=''):
 offer=response.get('offer')
 if not offer:return [],[]
 pk=provider_key(template['hotelDataKey'])
 if (offer.get('hotelDataKey') or {}).get('hotelId')!=template['hotelDataKey'].get('hotelId'):raise ValueError('Odpověď změnila hotel.')
 room,a,b,n,airport=validate_offer(offer,ctx,pk)
 if requested_code and room.get('roomCode')!=requested_code:raise ValueError('EXIM nevrátil požadovaný kód pokoje; cenu nepřiřazuji jinému typu.')
 if template.get('mealCode') and offer.get('mealCode')!=template['mealCode']:raise ValueError('Odpověď změnila stravování.')
 variants=[(room,offer.get('priceOffer'), 'offer')]
 variants += [(r,r.get('price'),'room_option') for r in response['roomOptions'] if r.get('groupId')==room.get('groupId') and r.get('availableCount',1)!=0]
 records=[]
 for r,price,kind in variants:
  if not price or not r.get('roomCode') or not r.get('roomName'):continue
  amount=price.get('price');currency=(price.get('currencySettings') or {}).get('currency')
  if isinstance(amount,bool) or not isinstance(amount,(int,float)) or not math.isfinite(amount) or amount<=0 or currency!='CZK':continue
  query=dict(parse_qsl(offer.get('tourFilterQuery') or ''))
  if not query:continue
  query.update(RCS=r['roomCode'],AC1=str(ctx['adults']),KC1=str(len(ctx['children'])),KA1='|'.join(map(str,ctx['children'])),DD=a,RD=b,NN=str(n),DI=offer.get('mealCode',''))
  record={'provider':pk,'room_code':r['roomCode'],'room_name':r['roomName'],'date_from':a,'date_to':b,'nights':n,'total':amount,'currency':currency,'meal':offer.get('mealName',''),'meal_code':offer.get('mealCode',''),'airport':airport.get('name',''),'airport_id':airport.get('id'),'transport':ctx['transport'],'over_budget':bool(ctx['budget'] and amount>ctx['budget']),'source_kind':kind,'fetched':core.now(),'source_url':hotel_url.split('?')[0]+'?'+urlencode(query),'outbound':(offer.get('outbound') or {}).get('flightCode',''),'inbound':(offer.get('inbound') or {}).get('flightCode',''),'online':offer.get('isOnline'),'raw':{'price':price,'room':r,'context':{'hotelDataKey':offer['hotelDataKey'],'dateFrom':offer['dateFrom'],'dateTo':offer['dateTo'],'rooms':offer['rooms'],'meal':offer.get('mealName'),'priceInclude':offer.get('priceInclude'),'flightNote':offer.get('flightNote')}}}
  records.append(record)
 codes=list(dict.fromkeys([room['roomCode']]+[r['roomCode'] for r in response['roomOptions'] if r.get('roomCode') and r.get('groupId')==room.get('groupId')]))
 return records,codes

def match_room(c,hid,record):
 candidates=c.execute("SELECT r.id,r.name,s.url FROM rooms r LEFT JOIN sources s ON s.id=r.source_id WHERE r.hotel_id=? AND r.active=1 AND r.origin='EXIM'",(hid,)).fetchall()
 matched=[r['id'] for r in candidates if room_name_key(r['name'])==room_name_key(record['room_name']) and url_provider(r['url'] or '')==record['provider']]
 return matched[0] if len(matched)==1 else None

def save_offers(search_id,hid,records,request_payload):
 with core.connect() as c:
  for r in records:
   rid=match_room(c,hid,r)
   key=hashlib.sha256(json.dumps([hid,r['provider'],r['room_code'],r['date_from'],r['date_to'],r['nights'],r['total'],r['meal_code'],r['outbound'],r['inbound']],ensure_ascii=False).encode()).hexdigest()
   # If both option and selected-offer evidence exist, prefer the full selected offer.
   previous=c.execute('SELECT id,source_kind FROM room_offers WHERE search_id=? AND fingerprint=?',(search_id,key)).fetchone()
   if previous and previous['source_kind']=='offer':continue
   c.execute('''INSERT INTO room_offers(search_id,hotel_id,room_id,fingerprint,provider,room_code,room_name,date_from,date_to,nights,total,currency,meal,airport,source_kind,source_url,fetched,over_budget,data,request)
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(search_id,fingerprint) DO UPDATE SET room_id=excluded.room_id,source_kind=excluded.source_kind,data=excluded.data,request=excluded.request,fetched=excluded.fetched''',
    (search_id,hid,rid,key,r['provider'],r['room_code'],r['room_name'],r['date_from'],r['date_to'],r['nights'],r['total'],r['currency'],r['meal'],r['airport'],r['source_kind'],r['source_url'],r['fetched'],int(r['over_budget']),json.dumps(r,ensure_ascii=False),json.dumps(request_payload,ensure_ascii=False)))

def latest_search(c):
 r=c.execute("SELECT * FROM price_searches WHERE status IN ('done','partial') ORDER BY id DESC LIMIT 1").fetchone()
 if not r:return None
 d=dict(r);d['context']=json.loads(d['context']);d['report']=json.loads(d['report'] or '{}');return d

def attach_prices(c,h,detail=False):
 search=latest_search(c);h['price_context']=None;h['unmapped_offers']=[]
 for r in h['rooms']:r['offers']=[]
 if not search:return
 h['price_context']={k:search[k] for k in ['id','context','finished','status']}
 check=c.execute('SELECT * FROM price_hotels WHERE search_id=? AND hotel_id=?',(search['id'],h['id'])).fetchone()
 h['price_status']=dict(check) if check else {'status':'outside_search','notes':'Hotel není v aktuálně dokončeném hledání. Žádné staré ceny zde nedoplňujeme.'}
 offers=[dict(r) for r in c.execute('SELECT id,room_id,provider,room_code,room_name,date_from,date_to,nights,total,currency,meal,airport,source_kind,source_url,fetched,over_budget FROM room_offers WHERE search_id=? AND hotel_id=? ORDER BY total,date_from',(search['id'],h['id']))]
 byid={r['id']:r for r in h['rooms']}
 for o in offers:
  if o['room_id'] in byid:byid[o['room_id']]['offers'].append(o)
  else:h['unmapped_offers'].append(o)
 # List API carries summary prices only; detail retains every recorded offer.
 if not detail:
  for r in h['rooms']:r['offer_count']=len(r['offers']);r['offers']=r['offers'][:1]
  h['unmapped_offer_count']=len(h['unmapped_offers'])
  types={}
  for o in h['unmapped_offers']:types.setdefault((o['provider'],o['room_code']),o)
  h['unmapped_offers']=list(types.values());h['unmapped_type_count']=len(types)

class PriceBlocked(RuntimeError):pass

def run_prices(url,progress=print):
 ctx=context(url);start=core.now();errors=[];warnings=[];calls=0;processed=0;search_id=None;blocked=False
 # Complete discovery first: a failed second page must not publish a partial catalog.
 links=importer.discover(url,progress,keep_context=True)
 with core.connect() as c:
  search_id=c.execute('INSERT INTO price_searches(url,context,started,status) VALUES(?,?,?,?)',(url,json.dumps(ctx),start,'running')).lastrowid
 try:
  for i,u in enumerate(links):
   progress(f'Ceny {i+1}/{len(links)} · {urlparse(u).path.rsplit("/",1)[-1]}')
   notes=[];hid=None
   try:
    with core.connect() as c:
     existing=c.execute('SELECT id FROM hotels WHERE url=?',(u.split('?')[0],)).fetchone()
     if existing:
      hid=existing['id'];c.execute("INSERT INTO price_hotels VALUES(?,?,'running','')",(search_id,hid))
    calls+=1;html=importer.fetch(u);template=template_from_html(html)
    # Price refresh NEVER reimports/retires existing catalog rooms or touches their facts.
    hid=existing['id'] if existing else core.save_exim(u,html)
    with core.connect() as c:
     c.execute('INSERT OR REPLACE INTO price_hotels(search_id,hotel_id,status,notes) VALUES(?,?,?,?)',(search_id,hid,'running',''))
     c.execute('INSERT INTO sources(hotel_id,url,label,content,fetched) VALUES(?,?,?,?,?)',(hid,u,'EXIM · cenový kontext 2 dospělí + děti '+ '/'.join(map(str,ctx['children'])),json.dumps(core.parse_exim(html)['sections'],ensure_ascii=False),core.now()))
    pending=[''];seen=set();max_calls=int(os.getenv('MAX_PRICE_REQUESTS_PER_HOTEL','16'))
    while pending and len(seen)<max_calls:
     code=pending.pop(0)
     if code in seen:continue
     seen.add(code);payload=range_filter(template,ctx,code)
     time.sleep(.6);calls+=1;response=request_options(payload)
     try:records,codes=extract_offers(response,ctx,template,u,code)
     except (ValueError,KeyError,TypeError) as e:notes.append(str(e));continue
     save_offers(search_id,hid,records,payload)
     if not response.get('offer'):notes.append('Pro požadovaný kontext/typ nebyla vrácena nabídka. Není to důkaz vyprodání.')
     if not code and response.get('offer'):seen.add(response['offer']['rooms'][0]['roomCode'])
     pending.extend(x for x in codes if x not in seen and x not in pending)
    if pending:notes.append('Dosažen ochranný limit cenových dotazů; průchod pokojovými kódy je částečný.')
    with core.connect() as c:
     n=c.execute('SELECT count(*) FROM room_offers WHERE search_id=? AND hotel_id=?',(search_id,hid)).fetchone()[0]
     status='warning' if notes else 'priced' if n else 'no_price'
     c.execute('UPDATE price_hotels SET status=?,notes=? WHERE search_id=? AND hotel_id=?',(status,' '.join(dict.fromkeys(notes)),search_id,hid))
    processed+=1
    if notes:warnings.append({'url':u.split('?')[0],'messages':list(dict.fromkeys(notes))})
   except Exception as e:
    errors.append({'url':u.split('?')[0],'error':str(e)})
    if hid:
     with core.connect() as c:c.execute('UPDATE price_hotels SET status=?,notes=? WHERE search_id=? AND hotel_id=?',('error',str(e),search_id,hid))
    if isinstance(e,requests.HTTPError) and e.response is not None and e.response.status_code in (401,403,429):
     raise PriceBlocked('EXIM omezil přístup; další dotazy zastaveny bez obcházení.') from e
   time.sleep(.6)
 except PriceBlocked as e:blocked=True;errors.append({'error':str(e)})
 except BaseException:
  with core.connect() as c:c.execute("UPDATE price_searches SET status='error',finished=? WHERE id=?",(core.now(),search_id))
  raise
 with core.connect() as c:
  stats=dict(c.execute('''SELECT count(*) offers,count(distinct hotel_id) hotels_with_prices,count(distinct CASE WHEN room_id IS NOT NULL THEN room_id END) mapped_rooms,sum(room_id IS NULL) unmapped_offers FROM room_offers WHERE search_id=?''',(search_id,)).fetchone())
  stats['priced_room_codes']=c.execute('SELECT count(*) FROM (SELECT DISTINCT hotel_id,provider,room_code FROM room_offers WHERE search_id=?)',(search_id,)).fetchone()[0]
  stats['integrity']=c.execute('PRAGMA integrity_check').fetchone()[0]
  report={'search_id':search_id,'started':start,'finished':core.now(),'context':ctx,'discovered':len(links),'processed':processed,'http_calls_details_and_prices':calls,'errors':errors,'warnings':warnings,**stats,'coverage':'Nejnižší ze získaných nabídek v intervalu, ne garantované minimum všech kombinací. Kódy objevené v roomOptions; ne všechny obecné typy musejí mít cenu. Platí jen daný dodavatel a stravování z výsledku hledání.'}
  c.execute('UPDATE price_searches SET status=?,finished=?,report=? WHERE id=?',('partial' if errors or warnings else 'done',report['finished'],json.dumps(report,ensure_ascii=False),search_id))
 return report if blocked else repair_missing_prices(search_id,progress)

def repair_missing_prices(search_id,progress=print):
 """For hotels without a valid price, check individual stay lengths; do not broaden dates."""
 with core.connect() as c:
  search=dict(c.execute('SELECT * FROM price_searches WHERE id=?',(search_id,)).fetchone())
  report=json.loads(search['report']);ctx=json.loads(search['context'])
  if any('omezil přístup' in e.get('error','') for e in report.get('errors',[])):return report
  targets=c.execute("""SELECT h.id,h.url FROM price_hotels p JOIN hotels h ON h.id=p.hotel_id
    WHERE p.search_id=? AND p.notes LIKE '%mimo zadaný interval%'
    AND NOT EXISTS(SELECT 1 FROM room_offers o WHERE o.search_id=p.search_id AND o.hotel_id=p.hotel_id)""",(search_id,)).fetchall()
  if targets:c.execute("UPDATE price_searches SET status='running' WHERE id=?",(search_id,))
 correction={'hotels_checked':0,'offers_added':0,'requests':0,'errors':[],'notes':[]}
 for target in targets:
  hid=target['id'];progress('Doplňková kontrola délek pobytu · '+target['url'].rsplit('/',1)[-1])
  try:
   with core.connect() as c:
    source=c.execute("SELECT url FROM sources WHERE hotel_id=? AND label LIKE 'EXIM · cenový kontext%' ORDER BY id DESC LIMIT 1",(hid,)).fetchone()
   if not source:continue
   correction['requests']+=1;template=template_from_html(importer.fetch(source['url']))
   for n in ctx['nights']:
    single={**ctx,'nights':[n]};payload=range_filter(template,single)
    time.sleep(.6);correction['requests']+=1;response=request_options(payload)
    try:records,_=extract_offers(response,ctx,template,source['url'])
    except (ValueError,KeyError,TypeError) as e:
     correction['notes'].append({'url':target['url'],'nights':n,'message':str(e)});continue
    save_offers(search_id,hid,records,payload)
   correction['hotels_checked']+=1
   with core.connect() as c:
    n=c.execute('SELECT count(*) FROM room_offers WHERE search_id=? AND hotel_id=?',(search_id,hid)).fetchone()[0]
    if n:
     correction['offers_added']+=n
     c.execute("UPDATE price_hotels SET status='priced',notes='Doplněno kontrolou jednotlivých délek pobytu; minimum ze získaných nabídek.' WHERE search_id=? AND hotel_id=?",(search_id,hid))
     report['warnings']=[w for w in report['warnings'] if w.get('url')!=target['url']]
  except Exception as e:
   correction['errors'].append({'url':target['url'],'error':str(e)})
   if isinstance(e,requests.HTTPError) and e.response is not None and e.response.status_code in (401,403,429):
    correction['errors'].append({'error':'EXIM omezil přístup; další doplňkové dotazy zastaveny.'});break
 with core.connect() as c:
  stats=dict(c.execute('SELECT count(*) offers,count(distinct hotel_id) hotels_with_prices,count(distinct CASE WHEN room_id IS NOT NULL THEN room_id END) mapped_rooms,sum(room_id IS NULL) unmapped_offers FROM room_offers WHERE search_id=?',(search_id,)).fetchone())
  stats['priced_room_codes']=c.execute('SELECT count(*) FROM (SELECT DISTINCT hotel_id,provider,room_code FROM room_offers WHERE search_id=?)',(search_id,)).fetchone()[0]
  report.update(stats);report['additional_stay_checks']=correction;report['finished']=core.now()
  c.execute('UPDATE price_searches SET status=?,finished=?,report=? WHERE id=?',('partial' if report['errors'] or report['warnings'] or correction['errors'] else 'done',report['finished'],json.dumps(report,ensure_ascii=False),search_id))
 return report

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--url-file',default=str(core.ROOT/'data/search_prices_url.txt'));parser.add_argument('--report',default=str(core.DATA/'price-report.json'));args=parser.parse_args()
 result=run_prices(Path(args.url_file).read_text().strip())
 Path(args.report).write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
