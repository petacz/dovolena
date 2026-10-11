"""One-off correction of the initial price probe's previously unsupported empty-result schema.
Never required for a new run with the corrected prices.py. Requires a specific existing search ID.
"""
import sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import core,prices

def repair(search_id):
 with core.connect() as c:
  search=dict(c.execute('SELECT * FROM price_searches WHERE id=?',(search_id,)).fetchone());report=json.loads(search['report']);ctx=json.loads(search['context'])
  targets=c.execute("SELECT p.hotel_id,h.url FROM price_hotels p JOIN hotels h ON h.id=p.hotel_id WHERE search_id=? AND p.status='error' AND p.notes='Nerozpoznané schéma cenové odpovědi.'",(search_id,)).fetchall()
  c.execute("UPDATE price_searches SET status='running' WHERE id=?",(search_id,))
 corrected=[]
 for target in targets:
  hid=target['hotel_id'];print('Oprava prázdné odpovědi · '+target['url'],flush=True)
  notes=[]
  try:
   with core.connect() as c:
    sample=c.execute('SELECT request FROM room_offers WHERE search_id=? AND hotel_id=? ORDER BY id LIMIT 1',(search_id,hid)).fetchone()
   if not sample:continue
   template=json.loads(sample['request']);pending=[''];seen=set()
   while pending and len(seen)<16:
    code=pending.pop(0)
    if code in seen:continue
    seen.add(code);payload=prices.range_filter(template,ctx,code);time.sleep(.6);data=prices.request_options(payload)
    try:records,codes=prices.extract_offers(data,ctx,template,target['url'],code)
    except (ValueError,KeyError,TypeError) as e:notes.append(f'Kód {code or "výchozí"}: {e}');continue
    prices.save_offers(search_id,hid,records,payload)
    if not data.get('offer'):notes.append(f'Kód {code or "výchozí"}: zdroj při samostatném dotazu nevrátil nabídku. Dříve získané alternativy jsou opatřené vlastním časem.')
    if not code and data.get('offer'):seen.add(data['offer']['rooms'][0]['roomCode'])
    pending.extend(x for x in codes if x not in seen and x not in pending)
   if pending:notes.append('Dosažen limit dotazů; průchod je částečný.')
   with core.connect() as c:c.execute('UPDATE price_hotels SET status=?,notes=? WHERE search_id=? AND hotel_id=?',('warning' if notes else 'priced',' '.join(notes),search_id,hid))
   corrected.append(target['url'])
  except Exception as e:
   print('Neopraveno:',e,flush=True)
   if isinstance(e,prices.requests.HTTPError) and e.response is not None and e.response.status_code in (401,403,429):raise
 with core.connect() as c:
  report['errors']=[e for e in report['errors'] if e.get('url') not in corrected]
  report['warnings']=[{'url':r['url'],'messages':[r['notes']]} for r in c.execute("SELECT h.url,p.notes FROM price_hotels p JOIN hotels h ON h.id=p.hotel_id WHERE search_id=? AND p.status='warning'",(search_id,))]
  report['initial_processed']=report['processed'];report['processed']=c.execute("SELECT count(*) FROM price_hotels WHERE search_id=? AND status NOT IN ('error','running')",(search_id,)).fetchone()[0]
  report['empty_schema_correction']={'corrected_hotels':len(corrected),'urls':corrected,'method':'actual live requests after normalizing a verified empty-result shape, not inferred prices'}
  c.execute('UPDATE price_searches SET report=? WHERE id=?',(json.dumps(report,ensure_ascii=False),search_id))
 return prices.repair_missing_prices(search_id)

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('search_id',type=int);args=p.parse_args()
 result=repair(args.search_id);(core.DATA/'price-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps(result,ensure_ascii=False,indent=2))
