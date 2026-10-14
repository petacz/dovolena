/* Hotel Lens — front-end. Plain DOM + template strings, no build step.
 * Verdicts (✓ / ? / ✕) are computed from the same facts and the same selected criteria
 * as on the server; the server additionally orders hotels and rooms by them. */

const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const link = u => /^https?:\/\//.test(u || '') ? esc(u) : '#';
const val = (facts, k) => facts?.[k]?.value ?? null;
const status = v => v === true ? 'Ano' : v === false ? 'Ne' : v === null ? 'Neuvedeno' : String(v);
const cls = v => v === false ? 'no' : v === null ? 'unk' : '';
const ICON = {pass: '✓', unknown: '?', fail: '✕', none: '—'};
const FAMILY_PRESET = ['separate', 'twin', 'no_bunk', 'sand'];
const ROOM_KEYS = ['separate', 'doors', 'twin', 'no_bunk', 'area'];
const HOTEL_KEYS = ['sand', 'gentle', 'distance'];
const PAGE_SIZE = {cards: 24, table: 100};

let fields = [], items = [], current = null, editing = null, page = 1, onlySaved = false, requestId = 0, jobTimer, priceJobTimer;
let view = localStorage.getItem('hotel-lens-view') === 'table' ? 'table' : 'cards';
let saved;
try { saved = JSON.parse(localStorage.getItem('hotel-lens-saved') || '[]'); } catch { saved = []; }

function toast(t) {
  $('#toast').textContent = t;
  $('#toast').style.display = 'block';
  setTimeout(() => $('#toast').style.display = 'none', 5000);
}

async function api(u, data) {
  const r = await fetch(u, data ? {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Hotel-Lens': '1'}, body: JSON.stringify(data)} : {});
  const j = await r.json();
  if (!r.ok) throw Error(j.error || 'Požadavek se nezdařil');
  return j;
}

function handle(fn) {
  return async (...args) => { try { await fn(...args); } catch (e) { toast(e.message); } };
}

function updateSaved() {
  $('#savedCount').textContent = saved.length;
  localStorage.setItem('hotel-lens-saved', JSON.stringify(saved));
}

/* ---------- filters ---------- */

function filterControl(f) {
  if (f.type === 'bool') {
    const hint = f.key === 'doors' ? ' (volitelné)' : f.key === 'gentle' ? ' (plus pro děti)' : '';
    return `<label class="filter"><input type="checkbox" data-key="${esc(f.key)}"><span>${esc(f.label)}${hint}</span></label>`;
  }
  const placeholder = f.type === 'number' ? 'Bez omezení' : 'Obsahuje text…';
  return `<label class="filter numeric">${esc(f.label)}${f.key === 'distance' ? ' · maximum' : ''}<input data-key="${esc(f.key)}" type="${f.type === 'number' ? 'number' : 'text'}" min="0" step="any" placeholder="${placeholder}"></label>`;
}

async function loadFields() {
  fields = await api('/api/fields');
  $('#roomFilters').innerHTML = fields.filter(f => ROOM_KEYS.includes(f.key)).map(filterControl).join('');
  $('#hotelFilters').innerHTML = fields.filter(f => HOTEL_KEYS.includes(f.key)).map(filterControl).join('');
  $('#customFilters').innerHTML = fields.filter(f => !ROOM_KEYS.includes(f.key) && !HOTEL_KEYS.includes(f.key)).map(filterControl).join('');
  $$('[data-key]').forEach(el => el.addEventListener('change', () => { page = 1; load(); }));
}

function filters() {
  return $$('[data-key]').flatMap(el => {
    const f = fields.find(f => f.key === el.dataset.key);
    if (f.type === 'bool') return el.checked ? [{key: f.key, value: true, op: 'eq'}] : [];
    if (!el.value) return [];
    return [{key: f.key, value: f.type === 'number' ? Number(el.value) : el.value, op: f.type === 'number' ? (f.key === 'distance' ? 'max' : 'min') : 'contains'}];
  });
}

function strict() { return !$('#showAll').checked; }

function params() {
  return new URLSearchParams({
    q: $('#search').value,
    filters: JSON.stringify(strict() ? filters() : []),
    rank: JSON.stringify(filters()),
    unknown: $('#unknown').checked ? '1' : '0',
    sort: $('#sort').value,
    page,
    size: PAGE_SIZE[view],
    ...(onlySaved ? {ids: saved.join(',')} : {}),
  });
}

/* ---------- verdicts (shared logic, also exercised by tests/test_assessment_scopes.py) ---------- */

// A failing condition wins over missing evidence. Never label uncertainty as failure.
// Conditions are evaluated at their own scope: a room requirement belongs to the variant,
// a hotel requirement (beach, distance) belongs to the hotel — never repeated per room.
function evaluate(h, r, scope) {
  const failed = [], missing = [], passed = [];
  for (const f of filters()) {
    const field = fields.find(x => x.key === f.key);
    if (field.scope !== scope) continue;
    const v = val(scope === 'hotel' ? h.facts : r && r.facts, f.key);
    const label = field.label;
    if (v === null) { missing.push(label); continue; }
    const ok = f.op === 'min' ? v >= f.value : f.op === 'max' ? v <= f.value : f.op === 'contains' ? String(v).toLocaleLowerCase().includes(String(f.value).toLocaleLowerCase()) : v === f.value;
    (ok ? passed : failed).push(label + (ok ? '' : ` (zdroj: ${status(v)})`));
  }
  const state = failed.length ? 'fail' : missing.length ? 'unknown' : passed.length ? 'pass' : 'none';
  return {state, failed, missing, passed, requested: failed.length + missing.length + passed.length};
}
function assessment(h, r) {
  const a = evaluate(h, r, 'room');
  a.label = a.state === 'fail' ? '✕ Nevyhovuje' : a.state === 'pass' ? '✓ Vyhovuje podle zdrojů' : a.state === 'unknown' ? '? K ověření' : '— Bez požadavků na pokoj';
  return a;
}
function hotelAssessment(h) {
  const a = evaluate(h, null, 'hotel');
  if (h.import_status === 'incomplete') {
    a.missing.push('Aktuální popis EXIM');
    if (a.state === 'pass' || a.state === 'none') a.state = 'unknown';
    a.requested++;
  }
  a.label = a.state === 'fail' ? '✕ Hotel nesplňuje' : a.state === 'pass' ? '✓ Hotel vyhovuje podle zdrojů' : a.state === 'unknown' ? '? Hotel k ověření' : '— Bez požadavků na hotel';
  return a;
}
function assessmentBlock(a, cls, note) {
  return `<div class="assessment ${a.state}${cls}"><strong>${esc(a.label)}</strong>`
    + (a.failed.length ? `<small>Nesplňuje: ${esc(a.failed.join(' · '))}</small>` : '')
    + (a.missing.length ? `<small>Nedoloženo: ${esc(a.missing.join(' · '))}</small>` : '')
    + (a.state === 'pass' && note ? `<small>${esc(note)}</small>` : '')
    + '</div>';
}
function assessmentHTML(h, r) {
  return assessmentBlock(assessment(h, r), '', 'Vyhovuje všem vybraným požadavkům na pokoj. Dostupnost a údaje o celém hotelu tím nejsou potvrzeny.');
}
function hotelAssessmentHTML(h) {
  const a = hotelAssessment(h);
  if (!a.requested) return '';
  return assessmentBlock(a, ' hotel', 'Společný údaj pro celý hotel, netýká se jednoho pokoje.');
}
function roomSummary(h,r){
  // One variant row in a card. ✓ rows are open with all details; ? and ✕ rows stay one line until clicked.
  const a = assessment(h, r), area = val(r.facts, 'area'), offer = r.offers?.[0];
  const reason = a.state === 'fail' ? `nesplňuje: ${a.failed.join(' · ')}` : a.state === 'unknown' ? `zdroj neuvádí: ${a.missing.join(' · ')}` : '';
  const meta = [r.origin, area === null ? 'plocha neuvedena' : `od ${area} m²`, r.origin === 'EXIM' ? '' : 'nepřiřazeno k nabídce EXIM'].filter(Boolean).join(' · ');
  return `<details class="variant-row ${a.state}" data-room-id="${r.id}"${a.state === 'pass' ? ' open' : ''}>
    <summary>
      <span class="assessment ${a.state}" title="${esc(a.label)}">${ICON[a.state]}</span>
      <span class="variant-main"><span class="variant-title">${esc(r.name)}</span><span class="variant-meta">${esc(meta)}</span>${reason ? `<small class="variant-note">${esc(reason)}</small>` : ''}</span>
      ${roomPriceSummary(h, r)}
    </summary>
    <div class="variant-body">
      <div class="fact-row">${factBoxes(r.facts, 'room')}</div>
      <p class="variant-desc">${esc(r.description)}</p>
      ${offer ? offerBrief(offer, r.offer_count) : ''}
    </div>
  </details>`;
}

/* ---------- cards ---------- */

function tag(v, yes, no, unk) {
  return `<span class="tag ${v === false ? 'no' : v === null ? 'unknown' : ''}">${v === true ? '✓' : v === false ? '×' : '?'} ${esc(v === true ? yes : v === false ? no : unk)}</span>`;
}

function gentleBonus(h) {
  if (val(h.facts, 'gentle') !== true) return '';
  return `<div class="gentle-bonus" title="${esc(h.facts.gentle.quote)}"><b>★ Plus pro děti · pozvolný vstup do moře</b><small>Uvedeno ve zdroji. Výhoda navíc, nikoli záruka bezpečnosti.</small></div>`;
}

function importWarning(h) {
  if (!h.import_warnings?.length) return '';
  const kept = h.import_status === 'incomplete' && h.rooms.length ? 'Ponechány dříve získané varianty; poslední stažení je nepotvrdilo.' : '';
  return `<div class="import-warning"><b>⚠ Neúplné údaje / k ověření</b><p>${h.import_warnings.map(esc).join('<br>')}</p>${kept}</div>`;
}

function hotelTags(h) {
  const distance = val(h.facts, 'distance');
  return `<div class="tags">${tag(val(h.facts, 'sand'), 'Písečná pláž', 'Oblázky / smíšená pláž', 'Povrch pláže k ověření')}${distance === null ? '' : `<span class="tag">pláž ${esc(distance)} m</span>`}</div>`;
}

function groupRooms(h) {
  const groups = {pass: [], none: [], unknown: [], fail: []};
  for (const r of h.rooms) groups[assessment(h, r).state].push(r);
  return groups;
}

function card(h) {
  const g = groupRooms(h), shown = [...g.pass, ...g.none, ...g.unknown];
  const counts = [g.pass.length ? `✓ ${g.pass.length}` : '', g.unknown.length ? `? ${g.unknown.length} k ověření` : '', g.fail.length ? `✕ ${g.fail.length} skryto` : '', g.none.length ? `${g.none.length} bez požadavku` : ''].filter(Boolean).join(' · ');
  const hidden = g.fail.length ? `<details class="rejected"><summary>Skryto ${g.fail.length} nevyhovujících variant — zobrazit</summary>${g.fail.map(r => roomSummary(h, r)).join('')}</details>` : '';
  const empty = !h.rooms.length ? '' : !shown.length ? '<p class="muted">Žádná varianta nesplňuje vybrané požadavky na pokoj.</p>' : '';
  return `<article class="card ${h.state || ''}">
    <div class="photo">
      ${h.image ? `<img src="${esc(h.image)}" alt="${esc(h.name)}" loading="lazy" onerror="this.style.display='none'">` : ''}
      <span class="origin">${esc((h.location || 'EXIM').split('/')[0].trim())} · ${esc(h.category || 'EXIM TOURS')}</span>
      <button aria-label="Uložit ${esc(h.name)}" class="heart ${saved.includes(h.id) ? 'selected' : ''}" data-save="${h.id}">${saved.includes(h.id) ? '♥' : '♡'}</button>
    </div>
    <div class="card-body">
      <div class="location">${esc(h.location)}</div>
      <h2>${esc(h.name)}</h2>
      ${hotelTags(h)}
      ${gentleBonus(h)}
      ${importWarning(h)}
      ${hotelAssessmentHTML(h)}
      ${hotelPriceStatus(h)}
      <div class="all-rooms">
        <div class="overline">VARIANTY (${h.rooms.length})${counts ? ' · ' + esc(counts) : ''}</div>
        ${shown.map(r => roomSummary(h, r)).join('')}${empty}${hidden}
      </div>
      ${unmappedSummary(h)}
      <div class="card-bottom"><span>${h.rooms.length} typů · ${new Date(h.updated).toLocaleDateString('cs-CZ')}</span><button data-detail="${h.id}">Prozkoumat hotel ↗</button></div>
    </div>
  </article>`;
}

function emptyState() {
  const q = $('#search').value.trim();
  if (onlySaved) return '<div class="empty"><span>♡</span><h2>Zatím tu není žádný hotel</h2><p>Uložte si hotely srdíčkem. Aktivní filtry a hledání platí i pro váš výběr.</p></div>';
  if (q) return `<div class="empty"><span>⌕</span><h2>Nic neodpovídá hledání „${esc(q)}“</h2><p>Hledá se bez ohledu na diakritiku v názvech, lokalitách a popisech. Zkuste kratší text.</p></div>`;
  const allow = strict() && !$('#unknown').checked ? '<button class="primary" id="allowUnknown">Zahrnout neověřené údaje</button>' : '';
  return `<div class="empty"><span>⌕</span><h2>Žádná potvrzená shoda</h2><p>Žádný pokoj nemá doložené všechny vybrané podmínky zároveň. To neznamená, že vhodné ubytování neexistuje — některé detaily ještě chybí.</p>${allow}</div>`;
}

function renderAssessmentSummary(data) {
  const s = data.summary || {}, hs = data.hotel_summary || {}, any = filters().length > 0;
  const hotelLine = hs.pass + hs.unknown + hs.fail ? `<span>Hotel: ✓ ${hs.pass} · ? ${hs.unknown} · ✕ ${hs.fail}</span>` : '';
  $('#assessmentSummary').innerHTML = `<strong>Celý výběr (${data.total} hotelů):</strong>`
    + `<span class="pass">✓ ${s.pass || 0} doložených variant</span>`
    + `<span class="unknown">? ${s.unknown || 0} ${any ? 'k ověření' : 'bez posouzení'}</span>`
    + `<span class="fail">✕ ${s.fail || 0} nevyhovujících (skryté)</span>`
    + (s.none ? `<span>— ${s.none} bez požadavku na pokoj</span>` : '')
    + hotelLine;
}

function bindCards() {
  $$('[data-save]').forEach(b => b.onclick = () => {
    const id = Number(b.dataset.save);
    saved = saved.includes(id) ? saved.filter(x => x !== id) : [...saved, id];
    updateSaved();
    render();
    if (onlySaved) load();
  });
  $$('[data-detail]').forEach(b => b.onclick = handle(() => detail(Number(b.dataset.detail))));
  if ($('#allowUnknown')) $('#allowUnknown').onclick = () => { $('#unknown').checked = true; page = 1; load(); };
}

/* ---------- overview table ---------- */

function cell(f, facts, active) {
  const v = val(facts, f.key), flt = active.get(f.key);
  if (v === null) return `<td class="mark unk${flt ? ' active' : ''}" title="${esc(f.label)}: neuvedeno">?</td>`;
  if (f.type === 'bool') return `<td class="mark ${v ? 'yes' : 'no'}${flt ? ' active' : ''}" title="${esc(f.label)}: ${status(v)}">${v ? '✓' : '✕'}</td>`;
  let ok = null;
  if (flt) ok = flt.op === 'min' ? v >= flt.value : flt.op === 'max' ? v <= flt.value : String(v).toLocaleLowerCase().includes(String(flt.value).toLocaleLowerCase());
  const unit = f.key === 'area' ? ' m²' : f.key === 'distance' ? ' m' : '';
  return `<td class="num ${ok === null ? '' : ok ? 'yes' : 'no'}${flt ? ' active' : ''}" title="${esc(f.label)}: ${esc(v)}${unit}">${esc(v)}${unit}</td>`;
}

function priceCell(r, h) {
  const o = r?.offers?.[0];
  if (o) return `<td class="price"><b>${esc(money(o))}</b><small>${shortDate(o.date_from)} · ${o.nights} nocí</small></td>`;
  if (!r && h.price_from) return `<td class="price"><b>${esc(money({total: h.price_from}))}</b><small>jiný typ</small></td>`;
  return '<td class="price muted">—</td>';
}

function overviewTable(list) {
  const hotelFields = fields.filter(f => f.scope === 'hotel'), roomFields = fields.filter(f => f.scope === 'room');
  const active = new Map(filters().map(f => [f.key, f]));
  const th = f => `<th class="${active.has(f.key) ? 'active' : ''}" title="${esc(f.label)}">${esc(f.label)}</th>`;
  const head = `<thead><tr><th class="hotel">Hotel</th>${hotelFields.map(th).join('')}<th class="variant">Varianta</th>${roomFields.map(th).join('')}<th>Cena od</th><th>Stav</th></tr></thead>`;
  const bodies = list.map(h => {
    const g = groupRooms(h), rooms = [...g.pass, ...g.none, ...g.unknown], ha = hotelAssessment(h);
    const hotelCells = hotelFields.map(f => cell(f, h.facts, active)).join('');
    const hotelCell = `<td class="hotel"><button class="heart-mini ${saved.includes(h.id) ? 'selected' : ''}" data-save="${h.id}" aria-label="Uložit">${saved.includes(h.id) ? '♥' : '♡'}</button><a href="#" data-detail="${h.id}">${esc(h.name)}</a><small>${esc(h.location)}${ha.requested ? ` · <span class="${ha.state}">${esc(ha.label)}</span>` : ''}</small></td>`;
    const verdict = (r, a) => { const s = a.state === 'fail' || ha.state === 'fail' ? 'fail' : a.state === 'unknown' || ha.state === 'unknown' ? 'unknown' : a.state === 'none' && ha.state === 'none' ? 'none' : 'pass'; return `<td class="mark state ${s}" title="${esc(a.label)}">${ICON[s]}</td>`; };
    if (!rooms.length) {
      const note = h.rooms.length ? `žádná vyhovující varianta · ✕ ${g.fail.length}` : 'bez popisu pokojů';
      return `<tbody>${`<tr>${hotelCell}${hotelCells}<td class="variant muted" colspan="${roomFields.length + 1}">${esc(note)}</td>${priceCell(null, h)}<td class="mark state ${h.rooms.length ? 'fail' : 'unknown'}">${h.rooms.length ? '✕' : '?'}</td></tr>`}</tbody>`;
    }
    const rows = rooms.map((r, i) => {
      const a = assessment(h, r), more = i === 0 && rooms.length > 1 ? `<button class="text expand" data-expand="${h.id}">+${rooms.length - 1} další</button>` : '';
      const hiddenNote = i === 0 && g.fail.length ? `<small class="muted">✕ ${g.fail.length} skryto</small>` : '';
      return `<tr class="${i ? 'extra' : ''}" data-hotel="${h.id}"${i ? ' hidden' : ''}>${i ? `<td class="hotel sub"></td>${hotelFields.map(() => '<td></td>').join('')}` : hotelCell + hotelCells}<td class="variant"><span class="assessment ${a.state}">${ICON[a.state]}</span> ${esc(r.name)}${more}${hiddenNote}</td>${roomFields.map(f => cell(f, r.facts, active)).join('')}${priceCell(r, h)}${verdict(r, a)}</tr>`;
    });
    return `<tbody>${rows.join('')}</tbody>`;
  });
  return head + bodies.join('');
}

function bindTable() {
  bindCards();
  $$('[data-detail]').forEach(b => b.onclick = handle(e => { e.preventDefault(); return detail(Number(b.dataset.detail)); }));
  $$('[data-expand]').forEach(b => b.onclick = () => {
    const rows = $$(`tr.extra[data-hotel="${b.dataset.expand}"]`), open = rows[0]?.hidden;
    rows.forEach(r => r.hidden = !open);
    b.textContent = open ? 'sbalit' : `+${rows.length} další`;
  });
}

/* ---------- loading & rendering ---------- */

function render() {
  const list = onlySaved ? items.filter(h => saved.includes(h.id)) : items;
  $('#cards').hidden = view !== 'cards';
  $('#tableWrap').hidden = view !== 'table';
  if (view === 'table') {
    $('#table').innerHTML = list.length ? overviewTable(list) : '';
    $('#cards').innerHTML = list.length ? '' : emptyState();
    $('#cards').hidden = list.length > 0;
    bindTable();
  } else {
    $('#cards').innerHTML = list.length ? list.map(card).join('') : emptyState();
    bindCards();
  }
}

function modeLabel() {
  const n = filters().length, sortText = {match: 'řazeno podle shody', price: 'řazeno podle ceny', name: 'řazeno podle názvu'}[$('#sort').value];
  if (!strict()) return `${n ? `${n} požadavků · ` : ''}všechny hotely · ${sortText} · nevyhovující varianty skryté`;
  return `${n} požadavků · ${$('#unknown').checked ? 'vyloučeny jen doložené rozpory' : 'jen doložené shody, chybějící údaj se skrývá'} · ${sortText}`;
}

async function load() {
  const rid = ++requestId;
  $('#unknown').disabled = !strict();
  try {
    const data = await api('/api/hotels?' + params());
    if (rid !== requestId) return;
    items = data.items;
    $('#totalHotels').textContent = data.catalog_total;
    $('#totalRooms').textContent = data.room_total;
    $('#resultCount').textContent = `${data.total} hotelů ${onlySaved ? 'v mém výběru' : 've výběru'}`;
    $('#modeLabel').textContent = modeLabel();
    renderAssessmentSummary(data);
    render();
    $('#pagination').innerHTML = data.pages > 1
      ? `<button class="secondary" id="prev" ${page === 1 ? 'disabled' : ''}>← Předchozí</button><span>${page} / ${data.pages}</span><button class="secondary" id="next" ${page === data.pages ? 'disabled' : ''}>Další →</button>`
      : '';
    if ($('#prev')) {
      $('#prev').onclick = () => { page--; load(); scrollToResults(); };
      $('#next').onclick = () => { page++; load(); scrollToResults(); };
    }
  } catch (e) {
    $('#cards').hidden = false;
    $('#cards').innerHTML = `<div class="empty"><h2>Data se nepodařilo načíst</h2><p>${esc(e.message)}</p><button class="primary" onclick="load()">Zkusit znovu</button></div>`;
  }
}

function scrollToResults() {
  $('.results').scrollIntoView?.({behavior: 'smooth', block: 'start'});
}

function setView(v) {
  view = v;
  localStorage.setItem('hotel-lens-view', v);
  $('#viewCards').classList.toggle('active', v === 'cards');
  $('#viewTable').classList.toggle('active', v === 'table');
  page = 1;
  load();
}

/* ---------- detail dialog ---------- */

function factBoxes(facts, scope) {
  return fields.filter(f => f.scope === scope).map(f => {
    const v = val(facts, f.key);
    return `<div class="fact">${esc(f.label)}<b class="${cls(v)}">${esc(status(v))}${facts?.[f.key]?.conflict ? ' · rozpor' : ''}</b></div>`;
  }).join('');
}

function sourceLink(id) {
  const s = current.sources.find(s => s.id === id);
  if (!s) return '';
  return `${s.url ? `<a href="${link(s.url)}" target="_blank" rel="noopener">${esc(s.label)} ↗</a>` : esc(s.label)} · ${new Date(s.fetched).toLocaleDateString('cs-CZ')}`;
}

function evidence(facts) {
  const out = Object.entries(facts).map(([k, f]) => `<div class="quote"><b>${esc(fields.find(x => x.key === k)?.label || k)}: ${esc(status(f.value))}</b>${f.kind === 'manual' ? ' · ruční ověření' : ''}<br>${esc(f.quote)}<br>${sourceLink(f.source_id)}`
    + (f.history.length > 1 ? `<details><summary>Historie (${f.history.length})</summary>${f.history.map(o => `<p>${esc(o.created.slice(0, 10))} · ${esc(o.kind)} · ${esc(o.value)}<br>${esc(o.quote)}<br>${sourceLink(o.source_id)}</p>`).join('')}</details>` : '')
    + '</div>').join('');
  return out || '<p class="muted">Strukturované údaje zatím nejsou doložené. Podívejte se na původní popis nebo přidejte ověření.</p>';
}

function roomSection(h, r) {
  return `<section class="room ${assessment(h, r).state}">
    <div class="room-head"><div><div class="eyebrow">${esc(r.origin)}</div><h4>${esc(r.name)}</h4>${assessmentHTML(h, r)}</div><button class="secondary" data-edit="${r.id}">Ověřit údaj</button></div>
    <p>${esc(r.description)}</p>
    ${roomPriceDetail(h, r)}
    <div class="fact-row">${factBoxes(r.facts, 'room')}</div>
    <details><summary>Citace a zdroje jednotlivých údajů</summary>${evidence(r.facts)}</details>
  </section>`;
}

async function detail(id) {
  current = await api('/api/hotels/' + id);
  const h = current, order = {pass: 0, none: 1, unknown: 2, fail: 3};
  const rooms = [...h.rooms].sort((a, b) => order[assessment(h, a).state] - order[assessment(h, b).state]);
  $('#detailContent').innerHTML = `
    <div class="detail-top">
      <div class="dialog-head">
        <div><div class="eyebrow">${esc(h.location)}</div><h2>${esc(h.name)}</h2><a href="${link(h.fetch_url || h.url)}" target="_blank" rel="noopener">Otevřít na EXIM ↗</a> <span class="muted">· načteno ${new Date(h.updated).toLocaleString('cs-CZ')}</span></div>
        <button class="icon" id="closeDetail">×</button>
      </div>
      <div class="detail-note">Dispozice není rezervace. Ověřte u prodejce dostupnost přesně tohoto typu pro vaše cestující a termín. Typy z jiných zdrojů nejsou automaticky propojené s EXIM.</div>
    </div>
    <div class="detail-body">
      <div class="dialog-head"><h3>Pláž &amp; vlastnosti hotelu</h3><button class="secondary" data-edit="hotel">Ověřit údaj</button></div>
      ${gentleBonus(h)}${importWarning(h)}
      <div class="fact-row">${factBoxes(h.facts, 'hotel')}</div>
      ${hotelAssessmentHTML(h)}
      <details><summary>Zdroje a důkazy k pláži</summary>${evidence(h.facts)}</details>
      <h3>Typy ubytování <span class="muted">(${h.rooms.length}) · vyhovující první, každý posuzovaný samostatně</span></h3>
      ${rooms.map(r => roomSection(h, r)).join('')}
      ${unmappedDetail(h)}
      <h3>Úplný popis z EXIM</h3>
      ${Object.entries(h.sections).map(([k, v]) => `<details><summary>${esc(k)}</summary><p>${esc(v)}</p></details>`).join('')}
      <h3>Archiv zdrojů <span class="muted">(${h.sources.length})</span></h3>
      ${h.sources.map(s => `<details><summary>${esc(s.label)} · ${new Date(s.fetched).toLocaleString('cs-CZ')}</summary>${s.url ? `<a href="${link(s.url)}" target="_blank" rel="noopener">${esc(s.url)} ↗</a>` : ''}<div class="source-text">${esc(s.content)}</div></details>`).join('')}
    </div>`;
  $('#closeDetail').onclick = () => $('#detail').close();
  $$('[data-edit]').forEach(b => b.onclick = () => openEdit(b.dataset.edit));
  if (!$('#detail').open) $('#detail').showModal();
}

function openEdit(target) {
  const room = target === 'hotel' ? null : current.rooms.find(r => r.id === Number(target));
  editing = {hotel_id: current.id, room_id: room?.id ?? null, facts: room?.facts ?? current.facts};
  $('#editTarget').textContent = room?.name || current.name;
  $('#editKey').innerHTML = fields.filter(f => f.scope === (room ? 'room' : 'hotel')).map(f => `<option value="${esc(f.key)}">${esc(f.label)}</option>`).join('');
  $('#editUrl').value = '';
  $('#editQuote').value = '';
  renderValue();
  $('#editDialog').showModal();
}

function renderValue() {
  const f = fields.find(f => f.key === $('#editKey').value), v = val(editing.facts, f.key);
  $('#valueInput').innerHTML = f.type === 'bool'
    ? '<select id="editValue"><option value="null">Neuvedeno / nelze potvrdit</option><option value="true">Ano</option><option value="false">Ne</option></select>'
    : `<input id="editValue" type="${f.type === 'number' ? 'number' : 'text'}" min="0" step="any" placeholder="Prázdné = neuvedeno">`;
  $('#editValue').value = f.type === 'bool' ? String(v) : v ?? '';
}

$('#editKey').onchange = renderValue;
$('#editForm').onsubmit = handle(async e => {
  e.preventDefault();
  const f = fields.find(f => f.key === $('#editKey').value), input = $('#editValue').value;
  const value = f.type === 'bool' ? JSON.parse(input) : input === '' ? null : f.type === 'number' ? Number(input) : input;
  await api('/api/facts', {hotel_id: editing.hotel_id, room_id: editing.room_id, key: f.key, value, url: $('#editUrl').value, quote: $('#editQuote').value});
  $('#editDialog').close();
  await detail(current.id);
  await load();
  toast('Ověření uloženo do databáze');
});

/* ---------- controls ---------- */

function reset() {
  $$('[data-key]').forEach(e => { e.checked = false; if (e.type !== 'checkbox') e.value = ''; });
  $('#search').value = '';
  $('#unknown').checked = false;
  page = 1;
  load();
}

function applyPreset() {
  $$('[data-key]').forEach(e => { e.checked = FAMILY_PRESET.includes(e.dataset.key); if (e.type !== 'checkbox') e.value = ''; });
}

$('#showAll').onchange = () => { page = 1; load(); };
$('#unknown').onchange = () => { page = 1; load(); };
$('#sort').onchange = () => { page = 1; load(); };
$('#reset').onclick = reset;
$('#family').onclick = () => { applyPreset(); page = 1; load(); };
$('#viewCards').onclick = () => setView('cards');
$('#viewTable').onclick = () => setView('table');
let searchTimer;
$('#search').oninput = () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => { page = 1; load(); }, 250); };
$('#catalog').onclick = () => { onlySaved = false; $('#catalog').classList.add('active'); $('#saved').classList.remove('active'); page = 1; load(); };
$('#saved').onclick = () => { onlySaved = true; $('#saved').classList.add('active'); $('#catalog').classList.remove('active'); page = 1; load(); };
$('#method').onclick = () => $('#methodDialog').showModal();
$('#openField').onclick = () => $('#fieldDialog').showModal();
$('#openImport').onclick = handle(async () => { $('#importDialog').showModal(); await jobs(); });
$$('.close').forEach(b => b.onclick = () => b.closest('dialog').close());
$$('dialog').forEach(d => d.addEventListener('click', e => {
  if (e.target !== d) return;
  const r = d.getBoundingClientRect();
  if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) d.close();
}));

$('#fieldForm').onsubmit = handle(async e => {
  e.preventDefault();
  await api('/api/fields', Object.fromEntries(new FormData(e.target)));
  $('#fieldDialog').close();
  e.target.reset();
  await loadFields();
  await load();
  toast('Vlastnost přidána. Hodnoty vyplníte v detailu hotelu.');
});

/* ---------- import jobs ---------- */

async function startImport(urls) {
  $('#startImport').disabled = true;
  try {
    await api('/api/import', {urls});
    toast('Import spuštěn');
    await jobs();
  } finally {
    $('#startImport').disabled = false;
  }
}

$('#startImport').onclick = handle(() => startImport($('#urls').value.split(/\n/).map(x => x.trim()).filter(Boolean)));
$('#refreshAll').onclick = handle(async () => {
  if (!confirm('Znovu stáhnout detaily všech hotelů EXIM? Doplňkové zdroje a ruční ověření se zachovají.')) return;
  const all = (await api('/api/hotel-urls')).map(h => h.fetch_url || h.url);
  await startImport(all);
});

function jobMessage(j) {
  let msg = j.progress;
  try {
    const r = JSON.parse(msg);
    if (r.price_report) {
      const p = r.price_report;
      msg = `Ceny: ${p.hotels_with_prices}/${p.discovered} záznamů s cenou, ${p.priced_room_codes} cenových typů, ${p.offers} nabídek.\n${p.coverage}\nChyby: ${p.errors.length}; upozornění: ${p.warnings.length}`;
    } else {
      msg = `Uloženo: ${r.ok} záznamů · s popisem pokojů: ${r.complete ?? r.ok} · pouze metadata: ${r.incomplete ?? 0}.\n${(r.warnings || []).map(w => w.url.split('?')[0] + ': ' + w.messages.join(' ')).join('\n')}\n${r.errors.join('\n')}\n${(r.discovery || []).join('\n')}\n${r.note}`;
    }
  } catch {}
  return msg;
}

async function jobs() {
  clearTimeout(jobTimer);
  const list = await api('/api/jobs');
  const label = {done: 'Dokončeno', partial: 'Dokončeno s upozorněními / chybami', error: 'Chyba', queued: 'Ve frontě', running: 'Probíhá'};
  $('#jobs').innerHTML = list.map(j => `<div><b>${esc(label[j.status])}</b> · ${new Date(j.created).toLocaleString('cs-CZ')}<p>${esc(jobMessage(j))}</p></div>`).join('')
    || '<span class="muted">Zatím žádný nový import. Testovací katalog je již načtený.</span>';
  if (list.some(j => ['queued', 'running'].includes(j.status))) jobTimer = setTimeout(() => jobs().catch(e => toast(e.message)), 1500);
  else load();
}

$('#export').onclick = () => { location.href = '/api/export.csv?' + params(); toast('Exportuji filtrované pokoje do CSV.'); };
$('#backup').onclick = () => location.href = '/api/backup';

/* ---------- prices (a dated observation, never a hotel-wide minimum copied onto every room) ---------- */

const money = o => new Intl.NumberFormat('cs-CZ', {style: 'currency', currency: o.currency || 'CZK', maximumFractionDigits: 0}).format(o.total);
const shortDate = s => new Date(s + 'T12:00:00').toLocaleDateString('cs-CZ');

function offerLine(o) {
  return `<div class="offer-line"><strong>${esc(money(o))} <small>celý zájezd za rodinu</small></strong><span>${shortDate(o.date_from)} – ${shortDate(o.date_to)} · ${o.nights} nocí · ${esc(o.meal)} · ${esc(o.airport)}</span>${o.over_budget ? '<b class="over-budget">Nad rozpočtem hledání</b>' : ''}<small>EXIM · ${esc(o.provider)} · kód ${esc(o.room_code)} · získáno ${new Date(o.fetched).toLocaleString('cs-CZ')}</small><small>Orientační nabídka, nikoli potvrzení rezervace. ${o.source_kind === 'room_option' ? 'Cena alternativy v konkrétní kombinaci.' : ''}</small><span><a href="${link(o.source_url)}" target="_blank" rel="noopener">Ověřit na EXIM ↗</a> · <a href="/api/price-offers/${o.id}" target="_blank" rel="noopener">Zdrojová data</a></span></div>`;
}

function offerBrief(o, count) {
  return `<div class="offer-brief">${shortDate(o.date_from)} – ${shortDate(o.date_to)} · ${o.nights} nocí · ${esc(o.meal)} · ${esc(o.airport)}${o.over_budget ? ' · <b class="over-budget">nad rozpočtem</b>' : ''} · <a href="${link(o.source_url)}" target="_blank" rel="noopener">ověřit na EXIM ↗</a>${count > 1 ? ` · další nabídky (${count - 1}) v detailu` : ''}</div>`;
}

function hotelPriceStatus(h) {
  if (!h.price_context) return '';
  const p = h.price_status || {};
  if (p.status === 'outside_search') return '<div class="price-hotel-note">Hotel není v aktuálním cenovém hledání; ceny se nedoplňují ze starších běhů.</div>';
  return p.notes ? `<div class="price-hotel-note">${esc(p.notes)}</div>` : '';
}

function roomPriceSummary(h, r) {
  if (!r.offers?.length) return `<span class="price-missing" title="Neznamená vyprodáno.">cena nezjištěna</span>`;
  const o = r.offers[0];
  return `<span class="room-price" title="Nejnižší ze získaných nabídek · ${esc(o.meal)} · ${esc(o.airport)}"><b>od ${esc(money(o))}</b><small>za rodinu · ${o.nights} nocí${o.over_budget ? ' · nad rozpočtem' : ''}</small></span>`;
}

function roomPriceDetail(h, r) {
  if (!r.offers?.length) return `<div class="price-missing">Cena nezjištěna${h.price_context ? ' pro toto hledání' : ''} <small>Neznamená vyprodáno.</small></div>`;
  return `<div class="room-price-detail"><h4>Ceny pro 2 dospělé a děti ${esc(h.price_context.context.children.join(' a '))} let</h4>${offerLine(r.offers[0])}${r.offers.length > 1 ? `<details><summary>Další získané nabídky (${r.offers.length - 1})</summary>${r.offers.slice(1).map(offerLine).join('')}</details>` : ''}</div>`;
}

function unmappedSummary(h) {
  const count = h.unmapped_offer_count ?? h.unmapped_offers?.length ?? 0;
  if (!count) return '';
  return `<details class="unmapped-price-note"><summary><b>Cenové typy EXIM bez přiřazení k popisu</b> · ${count} nabídek, přesné přiřazení není ověřené</summary>${(h.unmapped_offers || []).map(o => `<div class="price-only-summary"><strong>${esc(o.room_name)}</strong><span>Od ${esc(money(o))} za celou rodinu${o.over_budget ? ' · nad rozpočtem' : ''}</span><small>${shortDate(o.date_from)} – ${shortDate(o.date_to)} · ${o.nights} nocí · ${esc(o.meal)}</small></div>`).join('')}</details>`;
}

function unmappedDetail(h) {
  if (!h.unmapped_offers?.length) return '';
  const grouped = {};
  for (const o of h.unmapped_offers) (grouped[o.provider + '|' + o.room_code] ??= []).push(o);
  return `<section class="unmapped-prices"><h3>Další cenové typy podle EXIM</h3><p>Následující názvy a kódy pocházejí přímo z nabídek. Neztotožňujeme je odhadem s podobně nazvanými typy v katalogu a nepřenášíme na ně jejich hodnocení.</p>${Object.values(grouped).map(list => `<section class="price-only-room"><h4>${esc(list[0].room_name)}</h4>${offerLine(list[0])}${list.length > 1 ? `<details><summary>Další nabídky (${list.length - 1})</summary>${list.slice(1).map(offerLine).join('')}</details>` : ''}</section>`).join('')}</section>`;
}

async function loadPriceContext() {
  const data = await api('/api/prices/context'), p = data.latest;
  $('#priceUrl').value = p?.url || data.default_url;
  $('#priceContext').textContent = p
    ? `Ceny · ${p.context.adults} dospělí + děti ${p.context.children.join('/')} · ${shortDate(p.context.from)}–${shortDate(p.context.to)} · ${p.report.hotels_with_prices} záznamů s cenou · kontrola ${new Date(p.finished).toLocaleString('cs-CZ')}`
    : 'Ceny zatím nejsou načtené. Výchozí hledání: 2 dospělí a děti 9/7 let.';
  $('#priceResult').textContent = p ? JSON.stringify(p.report, null, 2) : 'Žádné dokončené cenové hledání.';
}

async function watchPriceJobs() {
  clearTimeout(priceJobTimer);
  const j = (await api('/api/jobs'))[0];
  $('#priceProgress').textContent = j?.progress || '';
  if (j && ['queued', 'running'].includes(j.status)) priceJobTimer = setTimeout(() => watchPriceJobs().catch(e => toast(e.message)), 1500);
  else { await loadPriceContext(); await load(); }
}

$('#openPrices').onclick = handle(async () => { await loadPriceContext(); $('#priceDialog').showModal(); });
$('#startPrices').onclick = handle(async () => {
  if (!confirm('Projít všechny výsledky a ceny pokojů pro vložené hledání? Může trvat několik až desítky minut. Obecný katalog a ruční fakta se nemění.')) return;
  $('#startPrices').disabled = true;
  try {
    await api('/api/prices/refresh', {url: $('#priceUrl').value.trim()});
    await watchPriceJobs();
  } finally {
    $('#startPrices').disabled = false;
  }
});
$('#exportPrices').onclick = () => location.href = '/api/prices.csv';

/* ---------- start ---------- */

updateSaved();
$('#viewCards').classList.toggle('active', view === 'cards');
$('#viewTable').classList.toggle('active', view === 'table');
loadFields().then(() => { applyPreset(); return load(); }).catch(e => toast(e.message));
loadPriceContext().catch(e => toast(e.message));
