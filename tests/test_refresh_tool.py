"""Offline rehearsal of tools/refresh_catalog.py: no network, isolated throwaway catalog."""
import json,subprocess,sys
import pytest
from conftest import ROOT
pytestmark=pytest.mark.unit

def run(tmp_path,*extra):
 cmd=[sys.executable,str(ROOT/'tools/refresh_catalog.py'),'--archive',str(ROOT/'tests/fixtures/catalog-190'),'--data-dir',str(tmp_path),*extra]
 result=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
 assert result.returncode==0,result.stdout[-2000:]+result.stderr[-2000:]
 return json.loads((tmp_path/'refresh-report.json').read_text())

def test_refresh_reports_only_real_changes(tmp_path):
 first=run(tmp_path,'--limit','6')
 assert first['integrity']=='ok' and not first['errors'] and first['after']['hotels']==6
 assert first['after']['rooms']>0 and first['mode'].startswith('offline replay')
 # Re-importing the same source text must not look like an update.
 second=run(tmp_path,'--limit','6')
 assert second['changes']=={'hotels_added':[],'hotels_removed':[],'rooms_added':[],'rooms_deactivated':[],'facts_added':[],'facts_changed':[],'facts_lost':[]}
 # A fresh catalog reports every fact as added; the point is that a repeat run adds nothing.
 assert first['changes']['facts_added'] and second['changes']['facts_added']==[]
 assert second['before']==second['after']

def test_refresh_backs_up_an_existing_catalog_only(tmp_path):
 run(tmp_path,'--limit','3')
 assert not list(tmp_path.glob('backup-before-refresh-*.sqlite'))
 run(tmp_path,'--limit','3')
 assert len(list(tmp_path.glob('backup-before-refresh-*.sqlite')))==1

def test_family_preset_counts_are_reported(tmp_path):
 report=run(tmp_path,'--limit','6')
 counts=report['family_preset']
 assert set(counts)=={'pass','unknown','fail','no_rooms'}
 assert counts['pass']+counts['unknown']+counts['fail']==report['after']['rooms']

def test_report_counts_survive_the_shortened_listing(tmp_path):
 # Krácení výčtu v reportu nesmí podstřelit hlášený počet — jinak by menší oprava tvrdila,
 # že neudělala nic, a uživatel by ji šel hledat znovu.
 kratky=tmp_path/'kraceny';plny=tmp_path/'plny';kratky.mkdir();plny.mkdir()
 capped=run(kratky,'--limit','6','--list-cap','2')
 full=run(plny,'--limit','6','--list-cap','0')
 assert capped['changes_list_cap']==2 and full['changes_list_cap'] is None
 assert len(capped['changes']['facts_added'])==2
 assert capped['changes_counts']['facts_added']>2
 assert full['changes_counts']['facts_added']==len(full['changes']['facts_added'])>2
 assert capped['changes_counts']['facts_added']==full['changes_counts']['facts_added']
 assert capped['changes_counts']['facts_lost']==len(capped['changes']['facts_lost'])

def test_failed_start_leaves_no_empty_catalog_behind(tmp_path):
 # Nepovedený start (tady nečitelný archiv) nesmí v cíli zanechat prázdnou databázi ani zálohu —
 # uživatel by pak hledal, kde se mu ztratila data. Živý běh má stejný exit přes předkontrolu EXIM.
 target=tmp_path/'novy-katalog'
 cmd=[sys.executable,str(ROOT/'tools/refresh_catalog.py'),'--archive',str(tmp_path/'zinventare'),
      '--data-dir',str(target)]
 result=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
 assert result.returncode==2,result.stdout[-500:]+result.stderr[-500:]
 assert 'nesáhli' in result.stdout
 assert not target.exists(), f'v cíli zůstalo: {sorted(p.name for p in target.iterdir())}'
