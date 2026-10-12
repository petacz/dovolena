"""Refresh the whole catalog from one EXIM search URL, with a backup and a what-changed report.

  python tools/refresh_catalog.py --url-file data/search_prices_url.txt --data-dir reports/final
  python tools/refresh_catalog.py --archive tests/fixtures/catalog-190 --data-dir /tmp/rehearsal

Live mode hits eximtours.cz: all result pages via JSON API, then one HTTP detail per offer
(0,6 s between them). Offline mode replays archived HTML, so it rehearses the pipeline
without network and without touching the shipped database. Never called automatically.
"""
import argparse,json,os,shutil,sqlite3,sys,time
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]

def parse_args():
 p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
 p.add_argument('--url-file',default=str(ROOT/'data/search_prices_url.txt'),help='EXIM results URL, one search; the wide 2+2 search returns ~190 offers')
 p.add_argument('--data-dir',default=str(ROOT/'data'),help='catalog to update; use a copy for the first run')
 p.add_argument('--archive',help='offline rehearsal: replay saved HTML from a manifest.json folder instead of the network')
 p.add_argument('--limit',type=int,default=0,help='import only the first N details (useful for a live smoke test)')
 p.add_argument('--no-backup',action='store_true',help='skip the pre-refresh SQLite backup')
 p.add_argument('--out',help='report path; default <data-dir>/refresh-report.json')
 p.add_argument('--force-live',action='store_true',help='allow a live run even when the sandbox blocks eximtours.cz')
 return p.parse_args()

def snapshot(db):
 """State a refresh is allowed to change: hotels, active EXIM rooms and their automatic facts."""
 with sqlite3.connect(db) as c:
  c.row_factory=sqlite3.Row
  hotels={r['url']:r['name'] for r in c.execute('SELECT url,name FROM hotels')}
  fetch_urls={r['url']:r['fetch_url'] for r in c.execute('SELECT url,fetch_url FROM hotels')}
  rooms={}
  for r in c.execute("SELECT h.url h, r.name n, r.origin o, r.active a FROM rooms r JOIN hotels h ON h.id=r.hotel_id"):
   rooms[(r['h'],r['n'],r['o'])]=bool(r['a'])
  facts={}
  q="SELECT h.url h, r.name n, f.key k, f.value v FROM facts f JOIN hotels h ON h.id=f.hotel_id LEFT JOIN rooms r ON r.id=f.room_id WHERE f.kind='auto'"
  for r in c.execute(q):facts[(r['h'],r['n'],r['k'])]=r['v']
 return {'hotels':hotels,'fetch_urls':fetch_urls,'rooms':rooms,'facts':facts}

FAMILY=[('sand','hotel'),('separate','room'),('twin','room'),('no_bunk','room')]
def assess(hfacts,rfacts):
 """Same three states as the UI: a proven mismatch beats missing evidence, missing is never a failure."""
 failed=[];missing=[]
 for key,scope in FAMILY:
  v=(hfacts if scope=='hotel' else rfacts).get(key,{}).get('value')
  if v is None:missing.append(key)
  elif v is not True:failed.append(key)
 return 'fail' if failed else ('unknown' if missing else 'pass')

def assessment_counts():
 import core
 counts={'pass':0,'unknown':0,'fail':0,'no_rooms':0};hotels_pass=set()
 with core.connect() as c:
  for h in c.execute('SELECT * FROM hotels ORDER BY id'):
   record=core.hotel_record(c,h);states=[]
   for r in record['rooms']:states.append(assess(record['facts'],r['facts']))
   if not states:counts['no_rooms']+=1
   counts.update({s:counts[s]+states.count(s) for s in ('pass','unknown','fail')})
   if 'pass' in states:hotels_pass.add(record['name'])
 return counts,sorted(hotels_pass)

def main():
 args=parse_args();target=Path(args.data_dir).resolve();target.mkdir(parents=True,exist_ok=True)
 os.environ['DATA_DIR']=str(target)
 db=target/'hotels.sqlite'
 before=snapshot(db) if db.exists() else {'hotels':{},'fetch_urls':{},'rooms':{},'facts':{}}
 if db.exists() and not args.no_backup:
  stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');backup=target/f'backup-before-refresh-{stamp}.sqlite'
  with sqlite3.connect(db) as src,sqlite3.connect(backup) as dst:src.backup(dst)
  print(f'Záloha: {backup}')
 sys.path.insert(0,str(ROOT))
 import importer
 if args.archive:
  folder=Path(args.archive);manifest=json.loads((folder/'manifest.json').read_text())
  html={r['url']:(folder/r['file']).read_text() for r in manifest['records']}
  urls=list(html);importer.fetch=lambda u:html[u];importer.time.sleep=lambda _:None
  if args.limit:urls=urls[:args.limit];result_note=f'ČÁSTEČNÝ BĚH: {len(urls)} z {len(html)} záznamů archivu.'
  mode=f'offline replay of {len(html)} archived descriptions from {folder} — NOT fresh network data'
 else:
  url=Path(args.url_file).read_text().strip()
  if not args.force_live and os.environ.get('ALLOW_EXIM_NETWORK','0')!='1':
   try:importer.fetch(importer.api_search_url(url))
   except Exception as e:
    print(f'EXIM není dosažitelný ({type(e).__name__}). Zkuste --archive pro nácvik, nebo na vlastním PC --force-live.')
    return 2
  if args.limit:
   urls=importer.discover(url,progress=lambda m:print('  '+m,flush=True),keep_context=True)
   result_note=f'ČÁSTEČNÝ BĚH: {len(urls[:args.limit])} z {len(urls)} nalezených detailů; katalog zůstane neúplný.'
  else:urls=[url]
  mode=f'live EXIM import from {url.split("?")[0]}'
 started=time.time()
 result=importer.run(urls,progress=lambda m:print('  '+m,flush=True))
 result['mode']=mode;result['duration_seconds']=round(time.time()-started,1)
 if 'result_note' in locals():result['partial']=result_note;print('  '+result_note)
 after=snapshot(db)
 result['before']={'hotels':len(before['hotels']),'rooms':sum(1 for v in before['rooms'].values() if v),'fetch_urls':sum(1 for v in before['fetch_urls'].values() if v)}
 result['after']={'hotels':len(after['hotels']),'rooms':sum(1 for v in after['rooms'].values() if v),'fetch_urls':sum(1 for v in after['fetch_urls'].values() if v)}
 result['changes']={
  'hotels_added':sorted(set(after['hotels'])-set(before['hotels'])),
  'hotels_removed':sorted(set(before['hotels'])-set(after['hotels'])),
  'rooms_added':sorted(f'{h} / {n}' for (h,n,o),v in after['rooms'].items() if v and (h,n,o) not in before['rooms']),
  'rooms_deactivated':sorted(f'{h} / {n}' for (h,n,o),v in before['rooms'].items() if (h,n,o) not in after['rooms'] or not after['rooms'].get((h,n,o),False)),
  'facts_changed':sorted(f'{h} / {n} / {k}: {before["facts"][(h,n,k)]} → {v}' for (h,n,k),v in after['facts'].items() if (h,n,k) in before['facts'] and before['facts'][(h,n,k)]!=v),
   'facts_added':sorted(f'{h} / {n} / {k} = {v}' for (h,n,k),v in after['facts'].items() if (h,n,k) not in before['facts'])[:40],
   'facts_lost':[f'{h} / {n} / {k}' for (h,n,k) in set(before['facts'])-set(after['facts'])][:40],
 }
 with sqlite3.connect(db) as c:
  result['integrity']=c.execute('PRAGMA integrity_check').fetchone()[0]
  result['manual_facts_kept']=c.execute("SELECT count(*) FROM facts WHERE kind='manual'").fetchone()[0]
  result['reviewed_facts_kept']=c.execute("SELECT count(*) FROM facts WHERE kind='reviewed'").fetchone()[0]
 counts,passing=assessment_counts()
 result['family_preset']=counts;result['family_preset_hotels']=passing
 report=Path(args.out) if args.out else target/'refresh-report.json'
 report.write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(f"\nRežim: {result['mode']}")
 print(f"Staženo {result['ok']}/{result['attempted']} detailů, {result['discovered']} nalezených URL, {result['complete']} s popisem pokojů, {result['incomplete']} jen metadata.")
 print(f"Chyby: {len(result['errors'])}, upozornění: {len(result['warnings'])}, trvalo {result['duration_seconds']} s.")
 print(f"Hotelů {result['before']['hotels']} → {result['after']['hotels']}, aktivních pokojových záznamů {result['before']['rooms']} → {result['after']['rooms']}, fetch_url {result['before']['fetch_urls']} → {result['after']['fetch_urls']}.")
 for key,label in [('hotels_added','přidáno hotelů'),('hotels_removed','zmizelo hotelů'),('rooms_added','přidáno typů'),('rooms_deactivated','deaktivováno typů'),('facts_added','doloženo nových faktů'),('facts_changed','změněných faktů'),('facts_lost','ztracených faktů')]:
  print(f"  {label.strip()}: {len(result['changes'][key])}")
  for line in result['changes'][key][:6]:print('     ',line)
 print(f"Rodinná předvolba (2+2, bez palandy, písek) nad těmito daty: ✓ {counts['pass']} variant, ? {counts['unknown']}, ✕ {counts['fail']}, {counts['no_rooms']} hotelů bez pokojů.")
 print(f"Celoživotně vyhovující hotely: {', '.join(passing) if passing else 'žádné'}")
 print(f"Integrita: {result['integrity']} · ruční ověření zachováno: {result['manual_facts_kept']} · ověřené zdroje: {result['reviewed_facts_kept']}")
 print(f"Report: {report}")
 if result['errors']:
  print('\nChyby:')
  for e in result['errors'][:10]:print('  ',e)
  return 1
 return 0

if __name__=='__main__':sys.exit(main())
