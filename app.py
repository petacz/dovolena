import io,csv,json,os,threading,tempfile,sqlite3,secrets
from concurrent.futures import ThreadPoolExecutor
from flask import Flask,request,jsonify,render_template,send_file,Response
from core import *
from importer import run,validate
from seed import seed
seed()
app=Flask(__name__);app.config['MAX_CONTENT_LENGTH']=1024*1024
executor=ThreadPoolExecutor(max_workers=1)
with connect() as c:c.execute("UPDATE jobs SET status='error',progress='Import přerušen restartem. Spusťte jej znovu.' WHERE status IN ('running','queued')")
@app.before_request
def security():
 password=os.environ.get('APP_PASSWORD')
 if password:
  a=request.authorization
  if not a or not secrets.compare_digest(a.password or '',password):return Response('Přihlášení vyžadováno',401,{'WWW-Authenticate':'Basic realm="Hotel Lens"'})
 if request.method in ('POST','PUT','DELETE') and request.headers.get('X-Hotel-Lens')!='1':return jsonify(error='Chybí bezpečnostní hlavička.'),403
@app.errorhandler(ValueError)
def invalid(e):return jsonify(error=str(e)),400
@app.get('/')
def index():return render_template('index.html')
@app.get('/api/fields')
def fields():
 with connect() as c:return jsonify([dict(r) for r in c.execute('SELECT * FROM fields')])
@app.post('/api/fields')
def add_field():
 d=request.get_json();k=d.get('key','');t=d.get('type');s=d.get('scope');label=d.get('label','').strip()
 if not re.fullmatch('[a-z][a-z0-9_]{1,40}',k) or not label or t not in ['bool','number','text'] or s not in ['room','hotel']:raise ValueError('Neplatná definice pole.')
 with connect() as c:
  if c.execute('select 1 from fields where key=?',(k,)).fetchone():raise ValueError('Klíč už existuje.')
  c.execute('insert into fields values(?,?,?,?)',(k,label[:100],s,t))
 return jsonify(ok=True)
def query():
 filters=json.loads(request.args.get('filters','[]'))
 if not isinstance(filters,list) or len(filters)>30:raise ValueError('Neplatné filtry.')
 with connect() as c:valid={r['key']:dict(r) for r in c.execute('select * from fields')}
 for f in filters:
  if not isinstance(f,dict) or f.get('key') not in valid or f.get('op','eq') not in ['eq','min','max','contains'] or 'value' not in f:raise ValueError('Neplatný filtr.')
  t=valid[f['key']]['type']
  if t=='number' and (not isinstance(f['value'],(int,float)) or isinstance(f['value'],bool)):raise ValueError('Číselný filtr vyžaduje číslo.')
  if t=='bool' and not isinstance(f['value'],bool):raise ValueError('Filtr vyžaduje ano/ne.')
 result=search(request.args.get('q',''),filters,request.args.get('unknown')=='1')
 if 'ids' in request.args:
  ids={int(x) for x in request.args.get('ids','').split(',') if x}
  result=[h for h in result if h['id'] in ids]
 return result
@app.get('/api/hotels')
def hotels():
 items=query()
 with connect() as c:total=c.execute('SELECT count(*) FROM hotels').fetchone()[0];rooms=c.execute('SELECT count(*) FROM rooms WHERE active=1').fetchone()[0]
 page=max(1,int(request.args.get('page',1)));size=24
 return jsonify(items=items[(page-1)*size:page*size],total=len(items),catalog_total=total,room_total=rooms,page=page,pages=max(1,(len(items)+size-1)//size))
@app.get('/api/hotels/<int:hid>')
def hotel(hid):
 with connect() as c:
  h=c.execute('SELECT * FROM hotels WHERE id=?',(hid,)).fetchone()
  if not h:return jsonify(error='Hotel nenalezen'),404
  return jsonify(hotel_record(c,h,True))
@app.post('/api/facts')
def update_fact():
 d=request.get_json();hid=int(d['hotel_id']);rid=d.get('room_id');key=d.get('key');value=d.get('value');quote=d.get('quote','').strip();url=d.get('url','').strip()
 if len(quote)<5:raise ValueError('Uveďte citaci nebo důvod změny (min. 5 znaků).')
 if url and (urlparse(url).scheme not in ['http','https'] or not urlparse(url).netloc):raise ValueError('Neplatná URL zdroje.')
 with connect() as c:
  f=c.execute('SELECT * FROM fields WHERE key=?',(key,)).fetchone()
  if not f:raise ValueError('Neznámé pole.')
  if not c.execute('SELECT 1 FROM hotels WHERE id=?',(hid,)).fetchone():raise ValueError('Neznámý hotel.')
  if (f['scope']=='room')!=(rid is not None):raise ValueError('Nesprávný rozsah pole.')
  if rid is not None and not c.execute('SELECT 1 FROM rooms WHERE id=? AND hotel_id=? AND active=1',(rid,hid)).fetchone():raise ValueError('Pokoj nepatří tomuto hotelu.')
  if value is not None:
   if f['type']=='bool' and not isinstance(value,bool):raise ValueError('Vyžadováno ano/ne.')
   if f['type']=='number' and (not isinstance(value,(float,int)) or isinstance(value,bool) or value<0):raise ValueError('Vyžadováno nezáporné číslo.')
   if f['type']=='text' and not isinstance(value,str):raise ValueError('Vyžadován text.')
  sid=c.execute('INSERT INTO sources(hotel_id,url,label,content,fetched) VALUES(?,?,?,?,?)',(hid,url,'Ruční ověření',quote,now())).lastrowid
  c.execute('INSERT INTO facts(hotel_id,room_id,key,value,quote,source_id,kind,created) VALUES(?,?,?,?,?,?,?,?)',(hid,rid,key,json.dumps(value),quote,sid,'manual',now()))
 return jsonify(ok=True)
from urllib.parse import urlparse
@app.post('/api/import')
def import_urls():
 urls=request.get_json().get('urls',[])
 limit=int(os.getenv('MAX_IMPORT_HOTELS','500'))
 if not isinstance(urls,list) or not 1<=len(urls)<=limit:raise ValueError(f'Vložte 1 až {limit} odkazů.')
 for u in urls:validate(u)
 with connect() as c:
  if c.execute("SELECT 1 FROM jobs WHERE status IN ('running','queued')").fetchone():raise ValueError('Jiný import právě probíhá.')
  jid=c.execute('INSERT INTO jobs(status,progress,created) VALUES(?,?,?)',('queued','Čeká na spuštění',now())).lastrowid
 def progress(msg):
  with connect() as c:c.execute("UPDATE jobs SET status='running',progress=? WHERE id=?",(msg,jid))
 def worker():
  try:res=run(urls,progress);status='done' if not res['errors'] and not res.get('warnings') else 'partial';msg=json.dumps(res,ensure_ascii=False)
  except Exception as e:status='error';msg=str(e)
  with connect() as c:c.execute('UPDATE jobs SET status=?,progress=?,finished=? WHERE id=?',(status,msg,now(),jid))
 executor.submit(worker)
 return jsonify(id=jid),202
@app.get('/api/jobs')
def jobs():
 with connect() as c:return jsonify([dict(r) for r in c.execute('SELECT * FROM jobs ORDER BY id DESC LIMIT 10')])
@app.get('/api/export.csv')
def export_csv():
 items=query();s=io.StringIO();w=csv.writer(s)
 with connect() as c:keys=[r['key'] for r in c.execute('SELECT key FROM fields')]
 w.writerow(['Hotel','Lokalita','Pokoj','Původ','Zdroj']+keys)
 def safe(x):
  s=str(x)
  return "'"+s if s.startswith(('=','+','-','@','\t','\r')) else s
 for h in items:
  for r in h['rooms']:
   if r['id'] not in h['matching_rooms']:continue
   vals={**h['facts'],**r['facts']}
   w.writerow([safe(x) for x in [h['name'],h['location'],r['name'],r['origin'],h['url']]]+[('neuvedeno' if vals.get(k,{}).get('value') is None else vals[k]['value']) for k in keys])
 return Response('\ufeff'+s.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=hotely.csv'})
@app.get('/api/backup')
def backup():
 with tempfile.TemporaryDirectory() as td:
  path=Path(td)/'hotels.sqlite'
  with connect() as src,sqlite3.connect(path,factory=Connection) as dst:src.backup(dst)
  buf=io.BytesIO(path.read_bytes())
 return send_file(buf,as_attachment=True,download_name='hotels.sqlite',mimetype='application/vnd.sqlite3')
@app.get('/api/prices/context')
def price_context():
 from prices import latest_search
 with connect() as c:
  latest=latest_search(c)
  running=c.execute("SELECT id,started FROM price_searches WHERE status='running' ORDER BY id DESC LIMIT 1").fetchone()
 return jsonify(latest=latest,running=dict(running) if running else None,default_url=(ROOT/'data/search_prices_url.txt').read_text().strip())
@app.get('/api/price-offers/<int:oid>')
def price_offer_evidence(oid):
 with connect() as c:r=c.execute('SELECT * FROM room_offers WHERE id=?',(oid,)).fetchone()
 if not r:return jsonify(error='Nabídka nenalezena'),404
 d=dict(r);d['data']=json.loads(d['data']);d['request']=json.loads(d['request']);return jsonify(d)
@app.post('/api/prices/refresh')
def refresh_prices():
 from prices import context,run_prices
 url=(request.get_json() or {}).get('url','');context(url)
 with connect() as c:
  if c.execute("SELECT 1 FROM jobs WHERE status IN ('running','queued')").fetchone() or c.execute("SELECT 1 FROM price_searches WHERE status='running'").fetchone():raise ValueError('Jiný import nebo cenová aktualizace právě probíhá.')
  jid=c.execute('INSERT INTO jobs(status,progress,created) VALUES(?,?,?)',('queued','Ceny: čeká na spuštění',now())).lastrowid
 def progress(msg):
  with connect() as c:c.execute("UPDATE jobs SET status='running',progress=? WHERE id=?",(msg,jid))
 def worker():
  try:
   result=run_prices(url,progress);message=json.dumps({'price_report':result},ensure_ascii=False);status='partial' if result['errors'] or result['warnings'] else 'done'
  except Exception as e:message=str(e);status='error'
  with connect() as c:c.execute('UPDATE jobs SET status=?,progress=?,finished=? WHERE id=?',(status,message,now(),jid))
 executor.submit(worker);return jsonify(id=jid),202
@app.get('/api/prices.csv')
def price_export():
 from prices import latest_search
 stream=io.StringIO();writer=csv.writer(stream)
 writer.writerow(['Hotel','Pokoj ve zdroji','Přiřazený pokoj ID','Dodavatel','Od','Do','Nocí','Celkem za rodinu','Měna','Strava','Odlet','Nad rozpočtem','Získáno','Zdroj','Kontext'])
 def safe(v):
  value=str(v if v is not None else '')
  return "'"+value if value.startswith(('=','+','-','@','\t','\r')) else value
 with connect() as c:
  selected=latest_search(c)
  if selected:
   for r in c.execute('SELECT h.name,o.* FROM room_offers o JOIN hotels h ON h.id=o.hotel_id WHERE search_id=? ORDER BY h.name,o.room_name,o.total',(selected['id'],)):
    writer.writerow([safe(r[k]) for k in ['name','room_name','room_id','provider','date_from','date_to','nights','total','currency','meal','airport','over_budget','fetched','source_url']]+[safe(json.dumps(selected['context'],ensure_ascii=False))])
 return Response('\ufeff'+stream.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=ceny-pokoju.csv'})
@app.get('/api/health')
def health():
 with connect() as c:c.execute('SELECT 1')
 return jsonify(ok=True)
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT',8000)),threaded=True)
