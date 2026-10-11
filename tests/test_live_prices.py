"""Opt-in price contract: actual EXIM HTTP, no booking or basket creation."""
import json
from pathlib import Path
import pytest
import prices,importer
from conftest import ROOT
pytestmark=[pytest.mark.live,pytest.mark.prices]

def test_live_corrected_age_search():
 url=(ROOT/'data/search_prices_url.txt').read_text().strip()
 result=json.loads(importer.fetch(importer.api_search_url(url,0)))
 assert result['toursCount']>0
 for row in result['tours']:
  for room in row['tour']['rooms']:
   assert sorted(p['age'] for p in room['children'])==[7,9]

def test_live_room_options_family_total(report_dir):
 ctx=prices.context((ROOT/'data/search_prices_url.txt').read_text().strip())
 template=json.loads((ROOT/'tests/fixtures/prices/template.json').read_text())
 url='https://www.eximtours.cz/recko/kreta/stalis-malia-a-stalida/hotel-high-beach?'+template['tourFilterQuery']
 actual=prices.template_from_html(importer.fetch(url));request=prices.range_filter(actual,ctx)
 response=prices.request_options(request);records,codes=prices.extract_offers(response,ctx,actual,url)
 assert records and codes
 assert all(r['date_from']>=ctx['from'] and r['date_to']<=ctx['to'] for r in records)
 assert all(r['total']>0 and r['currency']=='CZK' for r in records)
 (report_dir/'live-room-prices.json').write_text(json.dumps({'context':ctx,'records':records,'codes':codes},ensure_ascii=False,indent=2))
