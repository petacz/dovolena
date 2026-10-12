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
 assert second['changes']=={'hotels_added':[],'hotels_removed':[],'rooms_added':[],'rooms_deactivated':[],'facts_changed':[],'facts_lost':[]}
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
