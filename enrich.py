"""One-time, reviewed supplemental sources; never automatically map hotel room names to EXIM."""
from core import *
import requests
SOURCES=[
(0,'https://www.ninosgrandbeachresort.com/accommodation/','Oficiální web hotelu','Family Bedroom with sea view or Swim Up','The two bedrooms are connected with a sliding door. 2 – 4 people. 1 double bed & 2 normal beds',{'separate':True,'doors':True,'twin':True,'no_bunk':True}),
(2,'https://apollonia.gr/useful-information/','Oficiální web hotelu','Family Room (2 separated sleeping rooms with sliding door)','46-50sqm in total, garden or land view, max. occupancy 2 adults and 2 children',{'area':46,'separate':True,'doors':True}),
(2,'https://apollonia.gr/accommodation/open-plan-family-room/','Oficiální web hotelu','Open Plan Family Room','26-30sqm in total; Main building: double bed or twin bed and up to two folding beds',{'area':26,'separate':False,'doors':False}),
(4,'https://kalogriahotel.gr/en/room/comfortable-suite/','Oficiální web hotelu','Comfortable Suite','Comfortable suite of 35 – 40 sq.m. constituted of two separate bedrooms. Double bed; 2 single beds',{'area':35,'separate':True,'twin':True,'no_bunk':True}),
(5,'https://aldemarolympianvillage.reserve-online.net/property/OLYMPIANV/AGV4','Rezervační web hotelu','Family Apartment Garden View','These Family Rooms with two separate areas; one bedroom with a double bed or two twin beds, a lounge area with additional beds; Space 43 sq.m',{'area':43,'separate':True}),
(5,'https://aldemarolympianvillage.reserve-online.net/property/OLYMPIANV/FRPGV','Rezervační web hotelu','Main Building Family Room (open plan)','a bedroom with two twin beds, two extra single beds; Space 47 sq.m.',{'area':47,'separate':False,'doors':False,'twin':True,'no_bunk':True}),
(1,'https://www.sunway.ie/sun-holidays/zakynthos/laganas/poseidon-beach-hotel/','Sunway · obecný popis, bez přiřazení pokoje',None,None,{}),
(3,'https://en.planetofhotels.com/greece/karousades/roda-beach-resort-spa','Planet of Hotels · doplňkový zdroj, ověřit typ pokoje',None,None,{})]
def run():
 links=json.loads((DATA/'search_links.json').read_text())
 for idx,url,label,name,quote,values in SOURCES:
  try:
   r=requests.get(url,timeout=30);r.raise_for_status();soup=BeautifulSoup(r.content,'html.parser')
   for x in soup(['script','style','nav','footer','header']):x.decompose()
   text=soup.get_text(' ',strip=True)
   with connect() as c:
    h=c.execute('SELECT id FROM hotels WHERE url=?',(links[idx]['url'].split('?')[0],)).fetchone()[0]
    if c.execute('SELECT 1 FROM sources WHERE url=?',(url,)).fetchone():continue
    sid=c.execute('INSERT INTO sources(hotel_id,url,label,content,fetched) VALUES(?,?,?,?,?)',(h,url,label,text,now())).lastrowid
    if name:
     rid=c.execute('INSERT INTO rooms(hotel_id,name,description,origin,source_id) VALUES(?,?,?,?,?)',(h,name,quote+' · Samostatný typ z jiného zdroje. Shoda s označením EXIM a dostupnost nejsou ověřeny.',label,sid)).lastrowid
     for k,v in values.items():fact(c,h,rid,k,v,quote,sid,'reviewed')
   print('OK',url,len(text))
  except Exception as e:print('ERROR',url,str(e))
if __name__=='__main__':run()
