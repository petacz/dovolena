"""Replay archived real descriptions: OFFLINE, not another live EXIM download."""
import json,sqlite3
from pathlib import Path
import pytest
import core,importer
from conftest import ROOT
pytestmark=pytest.mark.unit
FOLDER=ROOT/'tests/fixtures/catalog-190'

def test_all_190_saved_descriptions():
 manifest=json.loads((FOLDER/'manifest.json').read_text())
 assert len(manifest['records'])==190
 for record in manifest['records']:
  parsed=core.parse_exim((FOLDER/record['file']).read_text())
  assert parsed['name']==record['name'],record['url']
  assert [r['name'] for r in parsed['rooms']]==record['room_names'],record['url']
  assert parsed['warnings']==record['warnings'],record['url']
  for room in parsed['rooms']:
   # A proven bunk bed is only ever the one the supplier names in this variant's own text.
   if not any(m in core.fold(room['name']+': '+room['description']) for m in ('paland','bunk bed')):
    assert room['values'].get('no_bunk') is not False,record['url']+' / '+room['name']

def test_full_saved_catalog_database_replay(isolated_db,monkeypatch,report_dir):
 manifest=json.loads((FOLDER/'manifest.json').read_text());records=manifest['records']
 html={r['url']:(FOLDER/r['file']).read_text() for r in records}
 monkeypatch.setattr(importer,'fetch',lambda u:html[u]);monkeypatch.setattr(importer.time,'sleep',lambda _:None)
 result=importer.run(list(html));result['mode']='offline replay of archived live EXIM descriptions, NOT a new network run'
 with core.connect() as c:
  result['counts']={t:c.execute(f'select count(*) from {t}').fetchone()[0] for t in ['hotels','rooms','sources']}
  result['integrity']=c.execute('pragma integrity_check').fetchone()[0]
  with sqlite3.connect(report_dir/'replayed-catalog.sqlite',factory=core.Connection) as target:c.backup(target)
 (report_dir/'saved-catalog-replay.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 assert result['ok']==190 and result['complete']==189 and result['incomplete']==1
 assert result['counts']=={'hotels':190,'rooms':929,'sources':190}
 assert result['integrity']=='ok' and not result['errors']
 assert len(result['warnings'])==3
