import os,time,requests,json
from urllib.parse import urlparse,urljoin,parse_qsl,urlencode
from bs4 import BeautifulSoup
from core import save_exim

def validate(url):
 p=urlparse(url)
 if p.scheme!='https' or p.hostname!='www.eximtours.cz' or p.port not in (None,443) or p.username:raise ValueError('Automatický import podporuje pouze HTTPS odkazy www.eximtours.cz.')
 if not p.path or p.path=='/':raise ValueError('Vložte detail hotelu nebo výsledky vyhledávání EXIM.')
 return url

def fetch(url):
 validate(url)
 for _ in range(4):
  r=requests.get(url,timeout=(10,45),allow_redirects=False,headers={'User-Agent':'HotelLens/1.0 (personal hotel research)'})
  if r.is_redirect:url=validate(urljoin(url,r.headers['Location']));continue
  r.raise_for_status()
  if len(r.content)>8_000_000:raise ValueError('Stránka překročila limit 8 MB.')
  r.encoding='utf-8';return r.text
 raise ValueError('Příliš mnoho přesměrování.')

def api_search_url(url,offset=None):
 validate(url)
 if urlparse(url).path.rstrip('/')!='/vysledky-vyhledavani':
  raise ValueError('Pro vyhledávací API vložte výsledkovou URL EXIM.')
 query=parse_qsl(urlparse(url).query,keep_blank_values=True)
 if offset is not None:
  query=[(k,v) for k,v in query if k.lower()!='pstg'];query.append(('pstg',str(offset)))
 if not any(k.lower()=='sc' for k,v in query):query.append(('sc','residential'))
 return 'https://www.eximtours.cz/api/searchapi/getsearchresult?'+urlencode(query)

def dedupe_details(urls):
 # One record per detail path, preserving first offer's provider/date context.
 result={}
 for u in urls:result.setdefault(u.split('?')[0],u)
 return list(result.values())

def parse_search_response(payload,keep_context=False):
 if not isinstance(payload,dict) or not isinstance(payload.get('tours'),list):
  raise ValueError('Nerozpoznaná struktura výsledků API EXIM (tours).')
 rows=payload['tours'];links=[]
 for row in rows:
  if not isinstance(row,dict) or not isinstance(row.get('detailUrl'),str) or not row['detailUrl']:
   raise ValueError('API nevrátilo detailUrl u každé nabídky; odmítám tichý částečný import.')
  full=validate(urljoin('https://www.eximtours.cz',row['detailUrl'])).split('#')[0]
  u=full.split('?')[0]
  if urlparse(u).path.startswith('/api/') or urlparse(u).path=='/vysledky-vyhledavani':
   raise ValueError('API vrátilo neplatný hotelový odkaz.')
  links.append(full if keep_context else u)
 total=payload.get('toursCount')
 if not rows and total!=0:raise ValueError('Prázdná nebo neúplná odpověď API.')
 return dedupe_details(links),len(rows),total

def discover_browser(url):
 """Legacy diagnostic helper, NEVER used by discover/run in v6."""
 if os.getenv('ALLOW_BROWSER_FALLBACK','1')=='0':
  raise ValueError('HTML neobsahuje odkazy; prohlížečový fallback je vypnutý.')
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  exe=os.environ.get('CHROMIUM_PATH')
  browser=p.chromium.launch(headless=True,executable_path=exe or None,args=['--no-sandbox','--disable-dev-shm-usage'])
  try:
   page=browser.new_page()
   page.route('**/*',lambda route:route.abort() if route.request.resource_type in ('image','media','font') else route.continue_())
   page.goto(url,wait_until='domcontentloaded',timeout=60000)
   page.wait_for_selector('a[href*="HID="]',timeout=60000)
   links=page.locator('a[href*="HID="]').evaluate_all('(els)=>els.map(e=>e.href.split("?")[0])')
   return list(dict.fromkeys(validate(u) for u in links))
  finally:browser.close()

class DiscoveryError(ValueError):
 """Refuse to silently import a partial or unstable paginated result."""

def discover_api(url,progress=lambda s:None,keep_context=False):
 max_hotels=int(os.getenv('MAX_IMPORT_HOTELS','500'))
 offset=0;expected=None;all_links=[];seen_pages=set()
 for page_number in range(1,101):
  payload=json.loads(fetch(api_search_url(url,offset)))
  links,count,total=parse_search_response(payload,keep_context)
  if not isinstance(total,int) or isinstance(total,bool) or total<0:
   raise DiscoveryError('API neuvedlo platný celkový počet nabídek; úplnost nelze ověřit.')
  if expected is None:
   expected=total
   if total>max_hotels:raise DiscoveryError(f'Výsledky mají {total} nabídek, bezpečnostní limit je {max_hotels}. Zužte hledání nebo nastavte MAX_IMPORT_HOTELS.')
  elif total!=expected:raise DiscoveryError('Počet výsledků se během stránkování změnil. Import zastaven; zkuste jej znovu.')
  fingerprint=tuple(sorted(u.split('?')[0] for u in links))
  if count and fingerprint in seen_pages:raise DiscoveryError('API opakuje stejnou stránku. Odmítám neúplný import.')
  seen_pages.add(fingerprint);all_links.extend(links);offset+=count
  progress(f'JSON API · strana {page_number}: načteno {offset}/{expected} nabídek, {len(set(u.split("?")[0] for u in all_links))} odlišných detailních URL.')
  if offset==expected:return dedupe_details(all_links)
  if offset>expected or count==0:raise DiscoveryError('Nesouhlasí počet položek API; úplnost nelze potvrdit.')
  time.sleep(.6)
 raise DiscoveryError('Dosažen limit 100 stránek bez dokončení; import zastaven.')

def discover(url,progress=lambda s:None,keep_context=False):
 validate(url)
 progress('Získávám všechny stránky přes JSON API EXIM (bez prohlížeče)…')
 try:
  return discover_api(url,progress,keep_context)
 except requests.HTTPError as e:
  if e.response is not None and e.response.status_code in (401,403,429):
   raise DiscoveryError('EXIM omezil přístup k API. Import zastaven; blokaci ani limit neobcházíme.') from e
  raise DiscoveryError('HTTP chyba při načítání API. Import zastaven, aby se neuložil neúplný seznam.') from e
 except DiscoveryError:raise
 except (requests.RequestException,ValueError) as e:
  # Completeness is more important than silently falling back to a single DOM page.
  raise DiscoveryError(f'Nelze spolehlivě načíst všechny výsledky EXIM: {e}') from e

def run(urls,progress=lambda s:None):
 all_urls=[];discovery_log=[]
 def report(message):
  discovery_log.append(message);progress(message)
 for u in urls:
  validate(u)
  if '/vysledky-vyhledavani' in u:
   all_urls.extend(discover(u,report,keep_context=True))
  else:all_urls.append(u)
 all_urls=dedupe_details(all_urls)
 if len(all_urls)>int(os.getenv('MAX_IMPORT_HOTELS','500')):raise ValueError('Překročen limit MAX_IMPORT_HOTELS. Rozdělte import.')
 if not all_urls:raise ValueError('Nenalezeny žádné hotely.')
 errors=[];warnings=[];ok=0;complete=0;incomplete=0
 for i,u in enumerate(all_urls):
  progress(f'{i+1}/{len(all_urls)} · {urlparse(u).path.rsplit("/",1)[-1]}')
  try:
   result=save_exim(u,fetch(u),return_status=True);ok+=1
   if result['status']=='incomplete':incomplete+=1
   else:complete+=1
   if result['warnings']:warnings.append({'url':u,'messages':result['warnings']})
  except requests.HTTPError as e:
   errors.append(f'{u}: {e}')
   if e.response is not None and e.response.status_code in (401,403,429):
    errors.append(f'Další stahování zastaveno kvůli omezení přístupu; zbývá {len(all_urls)-i-1} hotelů.');break
  except Exception as e:errors.append(f'{u}: {e}')
  time.sleep(.6)
 return {'ok':ok,'complete':complete,'incomplete':incomplete,'warnings':warnings,'errors':errors,'discovery':discovery_log,'discovered':len(all_urls),'attempted':i+1,'note':'Seznam: všechny stránky JSON API s kontrolou počtu a opakování. Detaily: HTTP HTML bez prohlížeče. Neúplné nebo nestabilní stránkování se zastaví s chybou.'}
