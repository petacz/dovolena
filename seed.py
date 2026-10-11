from core import *
import requests

def seed():
 with connect() as c:
  if c.execute('SELECT count(*) FROM hotels').fetchone()[0]:return
 links=json.loads((DATA/'search_links.json').read_text())
 for i,x in enumerate(links):save_exim(x['url'],(DATA/f'exim-{i}.html').read_text(),x['name'].title())
seed()
if __name__=='__main__':
 with connect() as c:
  for h in c.execute('select * from hotels'):
   d=hotel_record(c,h);print(d['name'],len(d['rooms']),[(r['name'],{k:v['value'] for k,v in r['facts'].items()}) for r in d['rooms']])
