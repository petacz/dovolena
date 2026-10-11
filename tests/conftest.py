"""Pytest-only safety: never point test imports at the user's database."""
import os,sys,tempfile,shutil,sqlite3,threading
from pathlib import Path
from datetime import datetime,timezone
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
_session_dir=tempfile.TemporaryDirectory(prefix='hotel-lens-pytest-')
os.environ['DATA_DIR']=_session_dir.name
os.environ.pop('APP_PASSWORD',None)
for name in ['search_links.json']+[f'exim-{i}.html' for i in range(6)]:
 shutil.copy2(ROOT/'data'/name,Path(_session_dir.name)/name)

def pytest_collection_modifyitems(items):
 for item in items:
  if not any(item.get_closest_marker(m) for m in ['live','chromium']):item.add_marker(pytest.mark.unit)

@pytest.fixture
def isolated_db(tmp_path,monkeypatch):
 import core
 path=tmp_path/'hotels.sqlite';monkeypatch.setattr(core,'DB',path);core.init()
 return path

@pytest.fixture(scope='session')
def report_dir():
 path=ROOT/'reports'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 path.mkdir(parents=True,exist_ok=True)
 return path

@pytest.fixture
def local_app(isolated_db):
 """Seed only bundled EXIM snapshots; no network, no dependence on mutable user DB."""
 import core
 from app import app
 import json
 for i,x in enumerate(json.loads((ROOT/'data/search_links.json').read_text())):
  core.save_exim(x['url'],(ROOT/'data'/f'exim-{i}.html').read_text(),x['name'].title())
 app.config.update(TESTING=True)
 return app

@pytest.fixture
def app_url(local_app):
 from werkzeug.serving import make_server
 server=make_server('127.0.0.1',0,local_app,threaded=True)
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 yield f'http://127.0.0.1:{server.server_port}'
 server.shutdown();thread.join(timeout=5);server.server_close()

@pytest.fixture(scope='session')
def chromium_browser():
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_PATH') or None,args=['--no-sandbox','--disable-dev-shm-usage'])
  yield browser
  browser.close()

@pytest.fixture
def page(chromium_browser,app_url,request,report_dir):
 context=chromium_browser.new_context(viewport={'width':1440,'height':1000})
 # Browser tests must not accidentally call EXIM or load third-party images.
 from urllib.parse import urlparse
 context.route('**/*',lambda r:r.continue_() if urlparse(r.request.url).netloc==urlparse(app_url).netloc else r.abort())
 context.tracing.start(screenshots=True,snapshots=True,sources=True)
 page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(app_url);page.locator('.variant-row').first.wait_for()
 yield page
 name=request.node.name.replace('/','_')
 try:
  page.screenshot(path=str(report_dir/f'{name}.png'),full_page=True)
  context.tracing.stop(path=str(report_dir/f'{name}-trace.zip'))
 finally:context.close()
 assert not errors,f'JavaScript errors: {errors}'

@pytest.fixture(autouse=True)
def no_accidental_http_in_offline_tests(request,monkeypatch):
 if request.node.get_closest_marker('live'):return
 import requests
 def refused(*args,**kwargs):
  pytest.fail('Real requests HTTP call in an offline/Chromium test. Use a mock or mark the test live.')
 monkeypatch.setattr(requests.sessions.Session,'request',refused)
