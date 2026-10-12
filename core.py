"""SQLite persistence, conservative EXIM parser and extensible field filtering."""
import os, re, json, sqlite3, unicodedata
from html import escape
from pathlib import Path
from datetime import datetime, timezone
from bs4 import BeautifulSoup
ROOT=Path(__file__).parent
DATA=Path(os.environ.get('DATA_DIR', ROOT/'data')); DATA.mkdir(parents=True,exist_ok=True)
DB=DATA/'hotels.sqlite'
FIELDS={
 'separate':('Oddělené místnosti','room','bool'),
 'doors':('Zavíratelné dveře','room','bool'),
 'twin':('2 samostatná lůžka pro děti','room','bool'),
 'no_bunk':('Bez palandy pro děti','room','bool'),
 'area':('Plocha od (m²)','room','number'),
 'sand':('Pouze písek (včetně vstupu)','hotel','bool'),
 'gentle':('Pozvolný vstup do moře','hotel','bool'),
 'distance':('Vzdálenost pláže (m)','hotel','number'),
}
def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def fold(t):return ''.join(c for c in unicodedata.normalize('NFD',str(t).lower()) if unicodedata.category(c)!='Mn')
class Connection(sqlite3.Connection):
 def __exit__(self,*args):
  try:return super().__exit__(*args)
  finally:self.close()
def connect():
 c=sqlite3.connect(DB,timeout=30,factory=Connection);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');c.create_function('fold',1,fold);return c
def init():
 with connect() as c:
  c.executescript('''
  PRAGMA journal_mode=WAL;
  CREATE TABLE IF NOT EXISTS hotels(id INTEGER PRIMARY KEY, url TEXT UNIQUE NOT NULL,name TEXT NOT NULL,location TEXT, image TEXT,sections TEXT NOT NULL DEFAULT '{}',updated TEXT);
  CREATE TABLE IF NOT EXISTS sources(id INTEGER PRIMARY KEY,hotel_id INTEGER REFERENCES hotels(id),url TEXT,label TEXT,content TEXT,fetched TEXT);
  CREATE TABLE IF NOT EXISTS rooms(id INTEGER PRIMARY KEY,hotel_id INTEGER REFERENCES hotels(id),name TEXT,description TEXT,origin TEXT,source_id INTEGER REFERENCES sources(id),active INTEGER DEFAULT 1,UNIQUE(hotel_id,name,origin));
  CREATE TABLE IF NOT EXISTS fields(key TEXT PRIMARY KEY,label TEXT,scope TEXT,type TEXT);
  CREATE TABLE IF NOT EXISTS facts(id INTEGER PRIMARY KEY,hotel_id INTEGER REFERENCES hotels(id),room_id INTEGER REFERENCES rooms(id),key TEXT REFERENCES fields(key),value TEXT,quote TEXT,source_id INTEGER REFERENCES sources(id),kind TEXT,created TEXT);
  CREATE INDEX IF NOT EXISTS facts_lookup ON facts(hotel_id,room_id,key,id);
  CREATE INDEX IF NOT EXISTS rooms_hotel ON rooms(hotel_id,active);
  CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY,status TEXT,progress TEXT,created TEXT,finished TEXT);
  ''')
  c.executescript("""
  CREATE TABLE IF NOT EXISTS price_searches(id INTEGER PRIMARY KEY,url TEXT NOT NULL,context TEXT NOT NULL,started TEXT,finished TEXT,status TEXT,report TEXT);
  CREATE TABLE IF NOT EXISTS price_hotels(search_id INTEGER REFERENCES price_searches(id),hotel_id INTEGER REFERENCES hotels(id),status TEXT,notes TEXT,PRIMARY KEY(search_id,hotel_id));
  CREATE TABLE IF NOT EXISTS room_offers(id INTEGER PRIMARY KEY,search_id INTEGER REFERENCES price_searches(id),hotel_id INTEGER REFERENCES hotels(id),room_id INTEGER REFERENCES rooms(id),fingerprint TEXT,provider TEXT,room_code TEXT,room_name TEXT,date_from TEXT,date_to TEXT,nights INTEGER,total REAL,currency TEXT,meal TEXT,airport TEXT,source_kind TEXT,source_url TEXT,fetched TEXT,over_budget INTEGER,data TEXT,request TEXT,UNIQUE(search_id,fingerprint));
  CREATE INDEX IF NOT EXISTS room_offers_hotel ON room_offers(search_id,hotel_id,room_id);
  """)
  columns={r[1] for r in c.execute('PRAGMA table_info(hotels)')}
  for field,definition in [('fetch_url','TEXT'),('import_status',"TEXT DEFAULT 'ok'"),('import_warnings',"TEXT DEFAULT '[]'")]:
   if field not in columns:c.execute(f'ALTER TABLE hotels ADD COLUMN {field} {definition}')
  for k,(l,s,t) in FIELDS.items():c.execute('INSERT OR IGNORE INTO fields VALUES(?,?,?,?)',(k,l,s,t))
def fact(c,h,r,k,v,q,s,kind='auto'):
 if v is not None:c.execute('INSERT INTO facts(hotel_id,room_id,key,value,quote,source_id,kind,created) VALUES(?,?,?,?,?,?,?,?)',(h,r,k,json.dumps(v,ensure_ascii=False),q,s,kind,now()))
def area(text):
 m=re.search(r'(\d+(?:[,.]\d+)?)(?:\s*[/–-]\s*(\d+(?:[,.]\d+)?))?\s*(?:m[²2]|sq\.?\s*m|sqm)',text,re.I)
 return float(m[1].replace(',','.')) if m else None

def room_values(t):
 x=fold(t);v={'area':area(t)}
 if re.search(r'oddelene? loznic|oddelenou loznic|oddelena loznic|2 mistnost|2 pokoj|two separate|two bedrooms|two separate areas',x):v['separate']=True
 if re.search(r'(?:posuvn\w*|spojovac\w*) dver|sliding door|connecting door',x):v.update(separate=True,doors=True)
 if 'open plan' in x or 'jedna mistnost' in x:v.update(separate=False,doors=False)
 if 'paland' in x or 'bunk bed' in x:v['no_bunk']=bool(re.search(r'bez paland|no bunk beds?',x))
 if re.search(r'dve jednoluzkove.*(?:ve spolecne|pro deti)|(?:2|two) (?:single|normal) beds.*(?:children|kids)|double bed.*(?:2|two) (?:single|normal) beds',x):
  v['twin']=True
  if v.get('no_bunk') is not False:v['no_bunk']=True
 return v

def parse_exim(html):
 soup=BeautifulSoup(html,'html.parser');sections={};roomnodes=[];room_sections=[];info={};warnings=[]
 # Prefer structured data embedded in HTTP HTML; independent of rendered CSS/layout.
 element=soup.select_one('[data-component-name="abnbHotelDetail"] script[type="application/json"]')
 blocks=[]
 if element:
  try:
   state=json.loads(element.string or element.get_text());info=state.get('hotelDetailInfo') or {}
   blocks=info.get('description') or []
   if not blocks:
    blocks=(state.get('dataNew') or {}).get('hotel',{}).get('description',{}).get('detailDescriptions',[]) or []
  except (ValueError,TypeError,AttributeError):blocks=[]
 if not blocks:
  # Older static pages: heading/body UL pairs. Only read recognized description area.
  for ul in soup.select('ul'):
   li=ul.find_all('li',recursive=False)
   if len(li)==2:
    title=li[0].get_text(' ',strip=True)
    if len(title)<180 and not li[0].find(['ul','a']):blocks.append({'title':title,'text':str(li[1])})
 roomlabels={'pokoje','popis pokoje','popis pokoju','pokoje - popis','ubytovani'}
 headings={'informace o hotelu','obecny popis','poloha','vybaveni','popis hotelu','popis plaze','popis plaz','plaz','strava','stravovani','deti','web','oficialni kategorie','vzdalenost','sportovni nabidka','sportovni aktivity zdarma','sportovni aktivity za priplatek','zabava','wellness','internet','poznamka','zvlastnosti','pro handicapovane','bazen','sport/ volny cas','dalsi informace','sport a zabava'}
 def is_room_title(title):
  t=fold(title).strip(' :')
  return len(t)<230 and not t.startswith(('ostatni','pokud','vsechny','vybaveni','popis')) and bool(re.search(r'pokoj|room|apartm|apartment|studio|suit|bungal|mezon|maison|villa|^vila',t))
 beach_parts=[];location_parts=[]
 for block in blocks:
  if not isinstance(block,dict):continue
  label=str(block.get('title') or '').strip().rstrip(':').strip();key=fold(label);code=block.get('code')
  raw=block.get('text') or block.get('description') or ''
  node=BeautifulSoup(raw if '<' in raw else '<span>'+escape(raw)+'</span>', 'html.parser');text=node.get_text(' ',strip=True)
  if not label or not text:continue
  if code or key in headings|roomlabels or is_room_title(label):
   # Preserve repeated sections instead of overwriting earlier supplier text.
   sections[label]=(sections[label]+'\n'+text) if label in sections else text
  if (code=='ROOMS' and key not in headings) or key in roomlabels:roomnodes.append(node)
  elif is_room_title(label):room_sections.append({'name':label,'description':label+': '+text,'values':room_values(label+': '+text)})
  if code=='BEACH' or key in ['plaz','popis plaze','popis plaz']:beach_parts.append(text)
  if code in ['LOCATION','ABOUT_HOTEL'] or key in ['poloha','obecny popis','informace o hotelu']:location_parts.append(text)
 rooms=list(room_sections)
 for roomnode in roomnodes:
  text=roomnode.get_text(' ',strip=True);titles=[]
  for tag in roomnode.find_all(['strong','b']):
   if tag.find(['strong','b']):continue
   title=tag.get_text(' ',strip=True).strip(' :')
   if len(title)>3 and is_room_title(title) and title not in titles:titles.append(title)
  if not titles:
   first=roomnode.get_text('\n',strip=True).split('\n')[0].strip()
   if len(first)<120 and first.endswith(':') and is_room_title(first):titles=[first.rstrip(':').strip()]
  if not titles:
   # Never combine facts from several unseparated room descriptions.
   rooms.append({'name':'Nerozlišený popis pokojů – ověřit variantu','description':text,'values':{}})
   warnings.append('Typy pokojů nelze bezpečně oddělit; uložen původní popis bez automatických pokojových faktů.')
   continue
  pos=0
  for n,title in enumerate(titles):
   start=text.find(title,pos);end=text.find(titles[n+1],start+len(title)) if n+1<len(titles) else len(text)
   if start<0 or end<start:raise ValueError('Nerozpoznané hranice typů pokojů; import zastaven.')
   desc=text[start:end].split('Ostatní typy pokojů')[0].strip();pos=end
   # The variant's own title counts as its text: „Rodinný pokoj s palandou“ is an explicit mention.
   rooms.append({'name':title,'description':desc,'values':room_values(title+': '+desc)})
 if not beach_parts:
  for text in location_parts:
   beach_parts.extend(sentence for sentence in re.split(r'(?<=[.!?])\s+',text) if 'plaz' in fold(sentence) or 'vstup' in fold(sentence))
 beach=' '.join(beach_parts)
 if not rooms:
  if not info.get('identifier'):raise ValueError('Zdroj neobsahuje zpracovatelný popis pokojů. Starší data zůstala zachována.')
  warnings.append('EXIM pro tuto nabídku neposkytl popis pokojů. Uložena pouze metadata hotelu; vhodnost nelze posoudit.')
 if not beach:
  warnings.append('Ve zdroji chybí podrobný popis pláže; plážové vlastnosti zůstávají neuvedené.')
 if warnings:sections['Upozornění importu']=' '.join(warnings)
 vals={};b=fold(beach)
 if any(x in b for x in ['oblaz','kamen','skaly','skalnat']):vals['sand']=False
 elif 'pisec' in b or 'pisc' in b:vals['sand']=True
 if 'pozvoln' in b:vals['gentle']=False if re.search(r'ne(?:ni|jde o)\s+pozvoln|strmy vstup',b) else True
 elif re.search(r'strmy vstup|prudky vstup',b):vals['gentle']=False
 if 'primo u hotelu' in b:vals['distance']=0
 dist=next((v for k,v in sections.items() if fold(k)=='vzdalenost'),'');m=re.search(r'pláže:\s*(\d+)\s*m',dist)
 if m:vals['distance']=int(m[1])
 h1=soup.find('h1');name=info.get('name') or (h1.get_text(' ',strip=True) if h1 else '')
 image=soup.find('meta',property='og:image');image=image.get('content') if image else None
 if not image:image=next((im.get('src') for im in soup.select('img[src]') if 'img.eximtours.cz/hotels/' in im.get('src','')),None)
 if not name:raise ValueError('Chybí název hotelu.')
 location=' / '.join(d.get('name','') for d in info.get('destination',[]) if d.get('name'))
 return dict(name=name,sections=sections,rooms=rooms,values=vals,beach=beach,image=image,location=location,warnings=warnings)

def save_exim(url,html,name=None,return_status=False):
 p=parse_exim(html);source_url=url;url=url.split('?')[0]
 with connect() as c:
  c.execute('INSERT INTO hotels(url,name) VALUES(?,?) ON CONFLICT(url) DO NOTHING',(url,name or p['name'] or url.rsplit('/',1)[-1]))
  h=c.execute('SELECT id FROM hotels WHERE url=?',(url,)).fetchone()[0]
  old=c.execute('SELECT image FROM hotels WHERE id=?',(h,)).fetchone()[0]
  status='incomplete' if not p['rooms'] else 'warning' if p['warnings'] else 'ok'
  c.execute('UPDATE hotels SET import_status=?,import_warnings=?,fetch_url=? WHERE id=?',(status,json.dumps(p['warnings'],ensure_ascii=False),source_url,h))
  if not p['rooms'] and c.execute('SELECT 1 FROM rooms WHERE hotel_id=? AND active=1',(h,)).fetchone():
   c.execute('INSERT INTO sources(hotel_id,url,label,content,fetched) VALUES(?,?,?,?,?)',(h,source_url,'EXIM TOURS – neúplná aktualizace',json.dumps(p['sections'],ensure_ascii=False),now()))
   return {'id':h,'status':status,'warnings':p['warnings']} if return_status else h
  if old and old.startswith('/static/'):p['image']=old
  parts=url.split('/')[3:]
  if parts and parts[0]=='hotely':parts=parts[1:]
  location=p.get('location') or ' / '.join(parts[:-1]).replace('-',' ').title()
  c.execute('UPDATE hotels SET name=?, location=?, image=?,sections=?,updated=? WHERE id=?',(name or p['name'],location,p['image'],json.dumps(p['sections'],ensure_ascii=False),now(),h))
  c.execute('UPDATE hotels SET fetch_url=? WHERE id=?',(source_url,h))
  s=c.execute('INSERT INTO sources(hotel_id,url,label,content,fetched) VALUES(?,?,?,?,?)',(h,source_url,'EXIM TOURS',json.dumps(p['sections'],ensure_ascii=False,indent=2),now())).lastrowid
  # Replace current automatic observations only; manual corrections and snapshots survive.
  c.execute("DELETE FROM facts WHERE hotel_id=? AND kind='auto'",(h,))
  c.execute("UPDATE rooms SET active=0 WHERE hotel_id=? AND origin='EXIM'",(h,))
  for k,v in p['values'].items():fact(c,h,None,k,v,p['beach'] if k!='distance' else p['sections'].get('Vzdálenost',p['beach']),s)
  for r in p['rooms']:
   c.execute("INSERT INTO rooms(hotel_id,name,description,origin,source_id) VALUES(?,?,?,'EXIM',?) ON CONFLICT(hotel_id,name,origin) DO UPDATE SET description=excluded.description,source_id=excluded.source_id,active=1",(h,r['name'],r['description'],s))
   rid=c.execute("SELECT id FROM rooms WHERE hotel_id=? AND name=? AND origin='EXIM'",(h,r['name'])).fetchone()[0]
   for k,v in r['values'].items():fact(c,h,rid,k,v,r['description'],s)
 return {'id':h,'status':status,'warnings':p['warnings']} if return_status else h

def effective(rows):
 grouped={}
 for r in rows:grouped.setdefault(r['key'],[]).append(dict(r))
 result={}
 for k,obs in grouped.items():
  manual=[o for o in obs if o['kind']=='manual']
  if manual:
   o=manual[-1];value=json.loads(o['value']);conflict=False
  else:
   o=obs[-1];values={x['value'] for x in obs};conflict=len(values)>1;value=None if conflict else json.loads(o['value'])
  result[k]={'value':value,'conflict':conflict,'quote':o['quote'],'source_id':o['source_id'],'kind':o['kind'],'history':obs}
 return result

def hotel_record(c,h,detail=False):
 h=dict(h);h['sections']=json.loads(h['sections']);h['import_warnings']=json.loads(h.get('import_warnings') or '[]');facts=c.execute('SELECT * FROM facts WHERE hotel_id=? ORDER BY id',(h['id'],)).fetchall()
 h['facts']=effective([f for f in facts if f['room_id'] is None]);h['rooms']=[]
 for r in c.execute('SELECT * FROM rooms WHERE hotel_id=? AND active=1 ORDER BY id',(h['id'],)):
  r=dict(r);r['facts']=effective([f for f in facts if f['room_id']==r['id']]);h['rooms'].append(r)
 from prices import attach_prices
 attach_prices(c,h,detail)
 if detail:h['sources']=[dict(s) for s in c.execute('SELECT * FROM sources WHERE hotel_id=? ORDER BY id DESC',(h['id'],))]
 return h

def match(facts,filters,unknown):
 for f in filters:
  v=facts.get(f['key'],{}).get('value')
  if v is None:
   if unknown:continue
   return False
  want=f['value'];op=f.get('op','eq')
  if op=='eq' and v!=want:return False
  if op=='min' and (not isinstance(v,(int,float)) or v<float(want)):return False
  if op=='max' and (not isinstance(v,(int,float)) or v>float(want)):return False
  if op=='contains' and fold(want) not in fold(v):return False
 return True

def search(q='',filters=None,unknown=False):
 filters=filters or []
 with connect() as c:
  fields={r['key']:r['scope'] for r in c.execute('SELECT * FROM fields')}
  hf=[f for f in filters if fields.get(f['key'])=='hotel'];rf=[f for f in filters if fields.get(f['key'])=='room']
  # SQL prefilter then evaluate extensible facts, always at the same room level.
  rows=c.execute('''SELECT * FROM hotels h WHERE ?='' OR fold(h.name||' '||h.location||' '||h.sections) LIKE ? OR EXISTS(SELECT 1 FROM rooms r WHERE r.hotel_id=h.id AND fold(r.name||' '||r.description) LIKE ?) ORDER BY h.name''',(q,'%'+fold(q)+'%','%'+fold(q)+'%')).fetchall()
  out=[]
  for row in rows:
   h=hotel_record(c,row)
   if h.get('import_status')=='incomplete' and filters and not unknown:continue
   if not match(h['facts'],hf,unknown):continue
   matches=[r for r in h['rooms'] if match(r['facts'],rf,unknown)]
   if rf and not matches and not (unknown and not h['rooms']):continue
   h['matching_rooms']=[r['id'] for r in matches];out.append(h)
 return out
init()
