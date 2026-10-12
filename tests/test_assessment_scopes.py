"""Logika hodnocení v UI: požadavek na pláž patří hotelu, ne každé variantě zvlášť.

Testuje static/app.js mimo prohlížeč přes node, aby pravidlo zůstalo i když se CSS nebo
texty změní. Bez node se přeskočí — DOM část kontroluje tests/test_chromium.py.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import ROOT

pytestmark = pytest.mark.skipif(shutil.which('node') is None, reason='Logika UI se kontroluje přes node')

APP = ROOT / 'static' / 'app.js'
START = '// A failing condition wins'
END = 'function roomSummary(h,r){'

FIELDS = [
 {'key': 'separate', 'label': 'Oddělené místnosti', 'scope': 'room'},
 {'key': 'doors', 'label': 'Zavíratelné dveře', 'scope': 'room'},
 {'key': 'twin', 'label': '2 samostatná lůžka pro děti', 'scope': 'room'},
 {'key': 'no_bunk', 'label': 'Bez palandy pro děti', 'scope': 'room'},
 {'key': 'sand', 'label': 'Pouze písek (včetně vstupu)', 'scope': 'hotel'},
]

HARNESS = """
const {readFileSync} = require('fs');
const {fields, data, requests} = JSON.parse(readFileSync(process.argv[3], 'utf8'));
const val = (facts, k) => facts?.[k]?.value ?? null;
const status = v => v === true ? 'Ano' : v === false ? 'Ne' : v === null ? 'Neuvedeno' : String(v);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const filters = () => requests;
const app = readFileSync(process.argv[2], 'utf8');
const from = app.indexOf(process.argv[4]), to = app.indexOf(process.argv[5]);
if (from < 0 || to < 0) throw new Error('V app.js chybí oddelovač hodnocení — uprav test, ne ho tiše vynechej.');
eval(app.slice(from, to));
const out = {};
for (const [name, h] of Object.entries(data)) {
  const hotel = hotelAssessment(h);
  out[name] = {
    rooms: h.rooms.map(r => {
      const a = assessment(h, r);
      return {state: a.state, label: a.label, missing: a.missing, failed: a.failed, passed: a.passed, html: assessmentHTML(h, r)};
    }),
    hotel: {state: hotel.state, label: hotel.label, missing: hotel.missing, failed: hotel.failed, requested: hotel.requested, html: hotelAssessmentHTML(h)},
  };
}
process.stdout.write(JSON.stringify(out));
"""


def evaluate(tmp_path: Path, data: dict, requests: list) -> dict:
    harness = tmp_path / 'harness.js'
    harness.write_text(HARNESS)
    payload = tmp_path / 'input.json'
    payload.write_text(json.dumps({'fields': FIELDS, 'data': data, 'requests': requests}))
    run = subprocess.run(['node', str(harness), str(APP), str(payload), START, END],
                        capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def hotel(sand=None, import_status='ok', rooms=None):
    facts = {} if sand is None else {'sand': {'value': sand}}
    return {'facts': facts, 'import_status': import_status,
            'rooms': rooms or [{'name': 'Rodinný pokoj', 'facts': {'separate': {'value': True}}}],
            'matching_rooms': [0]}


def test_hodnoceni_varianty_neobsahuje_pozadavky_na_hotel(tmp_path):
    out = evaluate(tmp_path, {'Annabelle': hotel(sand=False)}, [{'key': 'sand', 'op': 'eq', 'value': True}])
    room = out['Annabelle']['rooms'][0]
    assert room['state'] == 'none' and room['label'].startswith('—')
    assert room['missing'] == [] and room['failed'] == []
    assert 'Pouze písek' not in room['html'], 'údaj o pláži se nesmí opakovat u varianty'
    assert out['Annabelle']['hotel']['state'] == 'fail'
    assert out['Annabelle']['hotel']['failed'] == ['Pouze písek (včetně vstupu) (zdroj: Ne)']


def test_plaz_nezmeni_vyhovujici_pokoj_na_nevyhovujici(tmp_path):
    # Dispozice doložena, pláž proti podmínce: variota zůstává ✓, neshodu hlásí jen řádek hotelu.
    out = evaluate(tmp_path, {'A': hotel(sand=False)},
                   [{'key': 'separate', 'op': 'eq', 'value': True}, {'key': 'sand', 'op': 'eq', 'value': True}])
    assert out['A']['rooms'][0]['state'] == 'pass'
    assert out['A']['rooms'][0]['passed'] == ['Oddělené místnosti']
    assert out['A']['hotel']['state'] == 'fail'
    assert 'Hotel nesplňuje' in out['A']['hotel']['html']


def test_chybejici_udaj_zustava_na_hotelu(tmp_path):
    out = evaluate(tmp_path, {'A': hotel(sand=None)}, [{'key': 'separate', 'op': 'eq', 'value': True}])
    room = out['A']['rooms'][0]
    assert room['state'] == 'pass' and room['missing'] == []
    assert out['A']['hotel']['state'] == 'none' and out['A']['hotel']['requested'] == 0
    assert out['A']['hotel']['html'] == '', 'bez požadavku na hotel se věta nevykresluje'


def test_udaj_o_plazi_se_neopakuje_u_kazde_varianty(tmp_path):
    data = {'A': hotel(sand=None), 'B': hotel(sand=True)}
    out = evaluate(tmp_path, data, [{'key': 'sand', 'op': 'eq', 'value': True}])
    for name, expected in [('A', 'unknown'), ('B', 'pass')]:
        assert out[name]['hotel']['state'] == expected
        assert out[name]['hotel']['html'].count('Pouze písek') <= 1
        for room in out[name]['rooms']:
            assert 'Pouze písek' not in room['html']
    assert out['A']['hotel']['html'].count('Pouze písek') == 1, 'nejistota se musí objevit aspoň jednou, na úrovni hotelu'


def test_neuplny_import_hlasi_hotel_ne_varianty(tmp_path):
    out = evaluate(tmp_path, {'A': hotel(import_status='incomplete')}, [])
    assert out['A']['hotel']['missing'] == ['Aktuální popis EXIM']
    assert out['A']['hotel']['state'] == 'unknown'
    assert 'Aktuální popis EXIM' not in out['A']['rooms'][0]['html']
