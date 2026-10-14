"""Řazení a hodnocení v /api/hotels: vyhovující varianty první, nevyhovující hotely poslední.

Běží offline nad testovacím katalogem (6 hotelů EXIM) – stejná data jako tests/test_app.py.
"""
import csv
import io
import json

import pytest

import core

pytestmark = pytest.mark.unit

FAMILY = [{'key': k, 'value': True, 'op': 'eq'} for k in ['separate', 'twin', 'no_bunk', 'sand']]
ORDER = list(core.ROOM_ORDER)  # pass, none, unknown, fail


@pytest.fixture
def client(local_app):
    return local_app.test_client()


def hotels(client, **params):
    for key in ('filters', 'rank'):
        if key in params and not isinstance(params[key], str):
            params[key] = json.dumps(params[key])
    response = client.get('/api/hotels', query_string=params)
    assert response.status_code == 200, response.json
    return response.json


def test_rank_orders_hotels_by_best_variant_without_hiding_any(client):
    data = hotels(client, rank=FAMILY, filters=[])
    assert data['total'] == data['catalog_total'] == 6, 'výchozí režim nic neskrývá'
    ranks = [h['rank'] for h in data['items']]
    assert ranks == sorted(ranks), 'hotely jsou seřazené podle nejlepší varianty'
    assert data['items'][0]['state'] == 'pass' and 'Aldemar' in data['items'][0]['name']
    assert data['items'][-1]['state'] == 'fail'
    assert sum(data['summary'].values()) == data['room_total']
    assert sum(data['hotel_summary'].values()) == data['total']
    assert data['summary']['pass'] == 2 and data['hotel_summary']['pass'] == 1


def test_rooms_inside_hotel_are_ordered_pass_before_unknown_before_fail(client):
    data = hotels(client, rank=FAMILY, filters=[])
    for h in data['items']:
        states = [r['state'] for r in h['rooms']]
        assert states == sorted(states, key=ORDER.index), h['name']
        assert h['counts'] == {s: states.count(s) for s in ORDER}
        if h['hotel_state'] == 'pass':
            assert h['state'] == min(states, key=ORDER.index), h['name']
        assert len(h['matching_rooms']) == len(h['rooms']), 'bez tvrdého filtru nic nevypadává'


def test_hotel_level_failure_pushes_hotel_to_the_end_even_with_good_rooms(client):
    data = hotels(client, rank=[{'key': 'sand', 'value': True, 'op': 'eq'}], filters=[])
    failing = [h for h in data['items'] if h['hotel_state'] == 'fail']
    assert failing and all(h['state'] == 'fail' for h in failing)
    assert all(h['rank'] == core.RANK['fail'] for h in failing)
    assert data['items'].index(failing[0]) >= len(data['items']) - len(failing)


def test_rank_defaults_to_filters_and_strict_filter_still_hides(client):
    strict = hotels(client, filters=FAMILY)
    assert strict['total'] == 1 and strict['items'][0]['state'] == 'pass'
    h = strict['items'][0]
    assert sorted(h['matching_rooms']) == sorted(r['id'] for r in h['rooms'] if r['state'] == 'pass')
    assert all(h['rank'] == 0 for h in strict['items'])
    relaxed = hotels(client, filters=FAMILY, unknown=1)
    assert relaxed['total'] > strict['total']
    assert [h['rank'] for h in relaxed['items']] == sorted(h['rank'] for h in relaxed['items'])


def test_no_criteria_means_state_none_and_alphabetical_order(client):
    data = hotels(client)
    assert {h['state'] for h in data['items']} == {'none'}
    assert data['summary'] == {'pass': 0, 'unknown': 0, 'fail': 0, 'none': data['room_total']}
    names = [h['name'].lower() for h in data['items']]
    assert names == sorted(names)


def test_sort_by_price_and_name(client):
    by_name = hotels(client, rank=FAMILY, sort='name')
    names = [h['name'].lower() for h in by_name['items']]
    assert names == sorted(names)
    by_price = hotels(client, rank=FAMILY, sort='price')
    prices = [h['price_from'] for h in by_price['items']]
    known = [p for p in prices if p is not None]
    assert known == sorted(known) and prices[len(known):] == [None] * (len(prices) - len(known))


def test_page_size_and_hotel_urls(client):
    data = hotels(client, size=2, page=2)
    assert data['size'] == 2 and data['pages'] == 3 and len(data['items']) == 2
    assert hotels(client, size=999)['size'] == 200
    urls = client.get('/api/hotel-urls').json
    assert len(urls) == 6 and {tuple(sorted(u)) for u in urls} == {('fetch_url', 'id', 'url')}


def test_list_payload_is_slim(client):
    h = hotels(client)['items'][0]
    assert 'sections' not in h and 'fetch_url' not in h
    assert 'category' in h and 'price_from' in h and 'counts' in h
    assert all('history' not in f for f in h['facts'].values())
    detail = client.get(f"/api/hotels/{h['id']}").json
    assert 'sections' in detail and all('history' in f for f in detail['facts'].values())


@pytest.mark.parametrize('params', [
    {'sort': 'bogus'}, {'page': 'x'}, {'size': 'many'}, {'filters': 'not json'}, {'filters': '{"a":1}'},
    {'filters': '[{"key":"nope","value":true}]'}, {'filters': '[{"key":"area","value":"abc","op":"min"}]'},
    {'filters': '[{"key":"sand","value":true,"op":"min"}]'}, {'rank': '[1]'}, {'ids': '1,x'},
])
def test_invalid_parameters_are_400_not_500(client, params):
    response = client.get('/api/hotels', query_string=params)
    assert response.status_code == 400 and 'error' in response.json


def test_csv_export_contains_verdict_columns(client):
    response = client.get('/api/export.csv', query_string={'rank': json.dumps(FAMILY)})
    rows = list(csv.DictReader(io.StringIO(response.data.decode('utf-8-sig'))))
    assert rows and {'Hodnocení pokoje', 'Hodnocení hotelu'} <= set(rows[0])
    assert {r['Hodnocení pokoje'] for r in rows} <= {'vyhovuje', 'k ověření', 'nevyhovuje', 'bez požadavků'}
    assert rows[0]['Hodnocení pokoje'] == 'vyhovuje' and 'Aldemar' in rows[0]['Hotel']
