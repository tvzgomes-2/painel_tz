// ---------- load embedded data ----------
const TOPO = JSON.parse(document.getElementById('topo-data').textContent);
const STATS = JSON.parse(document.getElementById('data-stats').textContent);
const MUNI_COL = JSON.parse(document.getElementById('data-muni').textContent);

// zip columnar municipal data into id -> row object
const COLS = MUNI_COL.cols;
const MUNI = new Map();
for (const row of MUNI_COL.data) {
  const obj = {};
  for (let i = 0; i < COLS.length; i++) obj[COLS[i]] = row[i];
  obj.rec_prop_pc = (obj.rec_prop != null && obj.pop) ? obj.rec_prop / obj.pop : null;
  obj.tz_bin = (obj.tz_status === 'Ativa' || obj.tz_status === 'Encerrada') ? 'TZ' : 'Não TZ';
  MUNI.set(obj.id, obj);
}

// ---------- decode topojson ----------
const objName = Object.keys(TOPO.objects)[0];
const geometries = TOPO.objects[objName].geometries;
const scale = TOPO.transform.scale, translate = TOPO.transform.translate;

function decodeArc(arc) {
  let x = 0, y = 0;
  const pts = new Array(arc.length);
  for (let i = 0; i < arc.length; i++) {
    x += arc[i][0]; y += arc[i][1];
    pts[i] = [x * scale[0] + translate[0], y * scale[1] + translate[1]];
  }
  return pts;
}
const decodedArcs = TOPO.arcs.map(decodeArc);

function arcsToRing(arcIdx) {
  let coords = [];
  for (let i = 0; i < arcIdx.length; i++) {
    const idx = arcIdx[i];
    const reversed = idx < 0;
    const ai = reversed ? ~idx : idx;
    let seg = decodedArcs[ai];
    if (reversed) seg = seg.slice().reverse();
    if (i > 0) seg = seg.slice(1);
    coords = coords.concat(seg);
  }
  return coords;
}

// bounding box
let lonMin = Infinity, lonMax = -Infinity, latMin = Infinity, latMax = -Infinity;
const features = geometries.map(g => {
  let rings;
  if (g.type === 'Polygon') {
    rings = g.arcs.map(arcsToRing);
  } else if (g.type === 'MultiPolygon') {
    rings = [];
    for (const poly of g.arcs) for (const ring of poly) rings.push(arcsToRing(ring));
  } else {
    rings = [];
  }
  for (const ring of rings) for (const [lon, lat] of ring) {
    if (lon < lonMin) lonMin = lon; if (lon > lonMax) lonMax = lon;
    if (lat < latMin) latMin = lat; if (lat > latMax) latMax = lat;
  }
  return { id: g.properties.cod_ibge, rings };
});

const latMean = (latMin + latMax) / 2;
const cosLat = Math.cos(latMean * Math.PI / 180);
const W = 760, H = 800, PAD = 10;
const spanX = (lonMax - lonMin) * cosLat, spanY = (latMax - latMin);
const K = Math.min((W - 2 * PAD) / spanX, (H - 2 * PAD) / spanY);
const offX = PAD + ((W - 2 * PAD) - spanX * K) / 2;
const offY = PAD + ((H - 2 * PAD) - spanY * K) / 2;

function project([lon, lat]) {
  const x = offX + (lon - lonMin) * cosLat * K;
  const y = offY + (latMax - lat) * K;
  return [x, y];
}

function ringToPath(ring) {
  let d = '';
  for (let i = 0; i < ring.length; i++) {
    const [x, y] = project(ring[i]);
    d += (i === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1);
  }
  return d + 'Z';
}

// ---------- render map paths ----------
const svg = document.getElementById('mapSvg');
svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
const frag = document.createDocumentFragment();
const pathById = new Map();
for (const f of features) {
  const d = f.rings.map(ringToPath).join(' ');
  const el = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  el.setAttribute('d', d);
  el.dataset.id = f.id;
  frag.appendChild(el);
  pathById.set(f.id, el);
}
svg.appendChild(frag);

// ---------- color scales ----------
const PALETTES = {
  pib_pc: ['#c6dbef', '#9ecae1', '#4292c6', '#2171b5', '#084594'],
  motorizacao: ['#e5d8ec', '#c2a5cf', '#9970ab', '#762a83', '#40004b'],
  ibeu: ['#d9f0d3', '#a6dba0', '#5aae61', '#1b7837', '#00441b'],
  idh: ['#fee8c8', '#fdbb84', '#fc8d59', '#e34a33', '#b30000'],
  cresc_pop: ['#2166ac', '#92c5de', '#f7f7f7', '#f4a582', '#b2182b'],
  rec_prop_pc: ['#deebf7', '#9ecae1', '#4292c6', '#2171b5', '#08306b'],
  taxa_obitos_transito: ['#ffffb2', '#fecc5c', '#fd8d3c', '#f03b20', '#bd0026'],
  pct_investimento_desp: ['#edf8e9', '#bae4b3', '#74c476', '#31a354', '#006d2c'],
  tarifa: ['#f2f0f7', '#cbc9e2', '#9e9ac8', '#756bb1', '#54278f'],
  subsidio_ntu_pct: ['#fff5eb', '#fdbe85', '#fd8d3c', '#e6550d', '#a63603'],
};
const FAIXA_COLORS = {
  'Inferior a 20 mil': '#c6dbef', 'Entre 20 e 100 mil': '#6baed6',
  'Entre 100 e 250 mil': '#3182bd', 'Entre 250 e 500 mil': '#08519c', 'Acima de 500 mil': '#08306b'
};
const REGIC_COLORS = { 1: '#54278f', 2: '#807dba', 3: '#9e9ac8', 4: '#bcbddc', 5: '#dadaeb' };
const REGIC_LABELS = { 1: 'Metrópole', 2: 'Capital Regional', 3: 'Centro Sub-Regional', 4: 'Centro de Zona', 5: 'Centro Local' };
const ARRANJO_COLORS = { 'Sede/co-sede do arranjo': '#08519c', 'Satélite do arranjo': '#6baed6', 'Fora de arranjo': '#3a3f4a' };
const MODELO_COLORS = {
  'Concessão': '#2171b5', 'Prestação direta': '#2e9e5b', 'Permissão': '#e2892c',
  'Autorização': '#c9b458', 'Não regulamentado': '#a63603', 'Misto (2+ modelos)': '#756bb1'
};
const TZ_COLORS_HEX = { 'Ativa': '#2e9e5b', 'Encerrada': '#e2892c', 'Não TZ': '#2b2f39' };

function classify(v, breaks) {
  if (v == null || isNaN(v)) return null;
  for (let i = 1; i < breaks.length; i++) {
    if (v <= breaks[i] || i === breaks.length - 1) return i - 1;
  }
  return breaks.length - 2;
}

const CATEGORICAL_AXES = new Set(['tz', 'faixa_pop', 'regic_nivel', 'tipo_arranjo', 'modelo_prestacao_simples']);

function colorFor(m, colorBy) {
  if (!m) return '#22262e';
  if (colorBy === 'tz') return TZ_COLORS_HEX[m.tz_status] || TZ_COLORS_HEX['Não TZ'];
  if (colorBy === 'faixa_pop') return FAIXA_COLORS[m.faixa_pop] || '#22262e';
  if (colorBy === 'regic_nivel') return REGIC_COLORS[m.regic_nivel] || '#22262e';
  if (colorBy === 'tipo_arranjo') return ARRANJO_COLORS[m.tipo_arranjo] || '#22262e';
  if (colorBy === 'modelo_prestacao_simples') return m.modelo_prestacao_simples ? (MODELO_COLORS[m.modelo_prestacao_simples] || '#22262e') : '#22262e';
  const v = colorBy === 'rec_prop_pc' ? m.rec_prop_pc : m[colorBy];
  const breaks = STATS.breaks[colorBy];
  const cls = classify(v, breaks);
  if (cls == null) return '#22262e';
  return PALETTES[colorBy][cls];
}

// ---------- filters state ----------
const state = { colorBy: 'tz', uf: '', faixa: '', regic: '', arranjo: '', modelo: '', tzFilter: '', selected: null };

function passesFilter(m) {
  if (!m) return false;
  if (state.uf && m.uf !== state.uf) return false;
  if (state.faixa && m.faixa_pop !== state.faixa) return false;
  if (state.regic && String(m.regic_nivel) !== state.regic) return false;
  if (state.arranjo && m.tipo_arranjo !== state.arranjo) return false;
  if (state.modelo && m.modelo_prestacao_simples !== state.modelo) return false;
  if (state.tzFilter && m.tz_bin !== state.tzFilter) return false;
  return true;
}

function render() {
  for (const [id, el] of pathById) {
    const m = MUNI.get(id);
    const pass = passesFilter(m);
    el.setAttribute('fill', pass ? colorFor(m, state.colorBy) : '#1a1d23');
    el.style.opacity = pass ? '1' : '.25';
  }
  renderLegend();
  renderBars();
}

function renderLegend() {
  const el = document.getElementById('legend');
  let html = '';
  if (state.colorBy === 'tz') {
    html = `<span><span class="sw" style="background:${TZ_COLORS_HEX.Ativa}"></span>Ativa</span>
            <span><span class="sw" style="background:${TZ_COLORS_HEX.Encerrada}"></span>Encerrada</span>
            <span><span class="sw" style="background:${TZ_COLORS_HEX['Não TZ']}"></span>Não TZ</span>`;
  } else if (state.colorBy === 'faixa_pop') {
    html = STATS.faixa_order.map(f => `<span><span class="sw" style="background:${FAIXA_COLORS[f]}"></span>${f}</span>`).join('');
  } else if (state.colorBy === 'regic_nivel') {
    html = STATS.regic_order.map(r => `<span><span class="sw" style="background:${REGIC_COLORS[r]}"></span>${r} · ${REGIC_LABELS[r]}</span>`).join('');
  } else if (state.colorBy === 'tipo_arranjo') {
    html = STATS.arranjo_order.map(a => `<span><span class="sw" style="background:${ARRANJO_COLORS[a]}"></span>${a}</span>`).join('');
  } else if (state.colorBy === 'modelo_prestacao_simples') {
    html = STATS.modelo_order.map(a => `<span><span class="sw" style="background:${MODELO_COLORS[a]}"></span>${a}</span>`).join('')
      + `<span><span class="sw" style="background:#22262e"></span>Sem dado (MUNIC 2020, ${5570 - STATS.totais.modelo_prestacao_n} municípios)</span>`;
  } else {
    const breaks = STATS.breaks[state.colorBy];
    const pal = PALETTES[state.colorBy];
    const n = state.colorBy === 'tarifa' ? STATS.totais.tarifa_n : state.colorBy === 'subsidio_ntu_pct' ? STATS.totais.subsidio_ntu_n : null;
    html = pal.map((c, i) => `<span><span class="sw" style="background:${c}"></span>${fmtNum(breaks[i])} – ${fmtNum(breaks[i + 1])}</span>`).join('');
    if (n != null) html += `<span style="color:#e2892c;">⚠ apenas ${n} municípios com dado — restante em cinza</span>`;
  }
  el.innerHTML = html;
}

function fmtNum(v) {
  if (v == null || isNaN(v)) return '—';
  if (Math.abs(v) >= 1000) return v.toLocaleString('pt-BR', { maximumFractionDigits: 0 });
  if (Math.abs(v) < 5) return v.toLocaleString('pt-BR', { maximumFractionDigits: 3 });
  return v.toLocaleString('pt-BR', { maximumFractionDigits: 1 });
}

// ---------- cards ----------
function renderCards() {
  const t = STATS.totais;
  const cards = [
    { n: t.municipios.toLocaleString('pt-BR'), l: 'Municípios (universo)' },
    { n: t.tz_ativa, l: 'TZ ativas (base-mestre)' },
    { n: t.tz_encerrada, l: 'TZ encerradas (distintas)' },
    { n: (100 * (t.tz_ativa + t.tz_encerrada) / t.municipios).toFixed(1) + '%', l: '% do universo com histórico de TZ' },
    { n: t.modelo_prestacao_n.toLocaleString('pt-BR'), l: 'Com modelo de prestação (MUNIC 2020)' },
    { n: t.tarifa_n, l: 'Com tarifa reconciliada' },
  ];
  document.getElementById('cards').innerHTML = cards.map(c => `<div class="card"><div class="n">${c.n}</div><div class="l">${c.l}</div></div>`).join('');
}

// ---------- detail panel ----------
function renderDetail(m) {
  const el = document.getElementById('detail');
  if (!m) { el.innerHTML = '<div class="empty">Clique em um município no mapa ou na lista abaixo.</div>'; return; }
  const tzTag = m.tz_status === 'Ativa' ? '<span class="tag ativa">TZ ativa</span>'
    : m.tz_status === 'Encerrada' ? '<span class="tag encerrada">TZ encerrada</span>' : '';
  let extra = '';
  if (m.tz_bin === 'TZ') {
    extra = `<tr><td>Início TZ</td><td>${m.tz_ano ?? '—'}</td></tr>
             <tr><td>Fim TZ</td><td>${m.tz_fim ?? '—'}</td></tr>
             <tr><td>% orçamento (fonte)</td><td>${m.tz_pct_orc ?? '—'}</td></tr>
             <tr><td>Operador</td><td>${m.tz_operador ?? '—'}</td></tr>`;
  }
  el.innerHTML = `<div><b style="font-size:15px;">${m.nome} – ${m.uf}</b> ${tzTag}</div>
    <table style="margin-top:8px;">
      <tr><td>Região</td><td>${m.regiao}</td></tr>
      <tr><td>Hierarquia REGIC</td><td>${m.regic_label ?? '—'}</td></tr>
      <tr><td>Arranjo metropolitano</td><td>${m.tipo_arranjo ?? '—'}${m.arranjo_nome ? ' — ' + m.arranjo_nome : ''}</td></tr>
      <tr><td>Modelo de prestação (MUNIC 2020)</td><td>${m.modelo_prestacao ?? 'sem dado'}</td></tr>
      <tr><td>Faixa populacional</td><td>${m.faixa_pop}</td></tr>
      <tr><td>População (2022)</td><td>${fmtNum(m.pop)}</td></tr>
      <tr><td>PIB per capita (2021)</td><td>R$ ${fmtNum(m.pib_pc)}</td></tr>
      <tr><td>Motorização (veíc/hab)</td><td>${fmtNum(m.motorizacao)}</td></tr>
      <tr><td>IBEU</td><td>${fmtNum(m.ibeu)}</td></tr>
      <tr><td>IDH</td><td>${fmtNum(m.idh)}</td></tr>
      <tr><td>Receita própria per capita</td><td>R$ ${fmtNum(m.rec_prop_pc)}</td></tr>
      <tr><td>Óbitos no trânsito /100mil (2019)</td><td>${fmtNum(m.taxa_obitos_transito)}</td></tr>
      <tr><td>Tarifa reconciliada</td><td>${m.tarifa != null ? 'R$ ' + fmtNum(m.tarifa) + ' (' + m.tarifa_ano + ', ' + m.tarifa_fonte + ')' : 'sem dado'}</td></tr>
      <tr><td>% custo subsidiado (NTU)</td><td>${m.subsidio_ntu_pct != null ? fmtNum(m.subsidio_ntu_pct) + '% (' + m.subsidio_ntu_ano + ')' : 'sem dado'}</td></tr>
      <tr><td>Plano Diretor</td><td>${m.plano_diretor ?? '—'}</td></tr>
      <tr><td>PDMU (2025)</td><td>${m.pdmu_2025 ?? '—'}</td></tr>
      ${extra}
    </table>`;
}

// ---------- comparison bars (recomputed live from filtered subset) ----------
const BAR_METRICS = [
  { k: 'pib_pc', label: 'PIB per capita mediano (R$)', fmt: v => 'R$ ' + fmtNum(v) },
  { k: 'motorizacao', label: 'Motorização mediana (veíc/hab)', fmt: fmtNum },
  { k: 'ibeu', label: 'IBEU mediano', fmt: fmtNum },
  { k: 'idh', label: 'IDH mediano', fmt: fmtNum },
  { k: 'rec_prop_pc', label: 'Receita própria per capita mediana (R$)', fmt: v => 'R$ ' + fmtNum(v) },
  { k: 'taxa_obitos_transito', label: 'Óbitos no trânsito /100mil mediano (2019)', fmt: fmtNum },
];

function median(arr) {
  const a = arr.filter(v => v != null && !isNaN(v)).sort((x, y) => x - y);
  if (!a.length) return null;
  const mid = Math.floor(a.length / 2);
  return a.length % 2 ? a[mid] : (a[mid - 1] + a[mid]) / 2;
}

function renderBars() {
  // subset by uf/faixa/regic/arranjo/modelo (ignore tzFilter so we always compare TZ vs Não-TZ)
  const rowsTZ = [], rowsNao = [];
  for (const m of MUNI.values()) {
    if (state.uf && m.uf !== state.uf) continue;
    if (state.faixa && m.faixa_pop !== state.faixa) continue;
    if (state.regic && String(m.regic_nivel) !== state.regic) continue;
    if (state.arranjo && m.tipo_arranjo !== state.arranjo) continue;
    if (state.modelo && m.modelo_prestacao_simples !== state.modelo) continue;
    (m.tz_bin === 'TZ' ? rowsTZ : rowsNao).push(m);
  }
  const el = document.getElementById('bars');
  if (!rowsTZ.length) {
    el.innerHTML = '<div class="empty">Nenhum município TZ neste recorte.</div>';
    return;
  }
  let html = `<div class="barrow"><div class="lab"><span>n</span><b>Não TZ: ${rowsNao.length} · TZ: ${rowsTZ.length}</b></div></div>`;
  for (const met of BAR_METRICS) {
    const vNao = median(rowsNao.map(m => met.k === 'rec_prop_pc' ? m.rec_prop_pc : m[met.k]));
    const vTZ = median(rowsTZ.map(m => met.k === 'rec_prop_pc' ? m.rec_prop_pc : m[met.k]));
    const max = Math.max(vNao || 0, vTZ || 0, 1e-9);
    html += `<div class="barrow">
      <div class="lab"><span>${met.label}</span></div>
      <div class="lab"><span>Não TZ</span><b>${met.fmt(vNao)}</b></div>
      <div class="bartrack"><div class="barfill a" style="width:${(100 * (vNao || 0) / max).toFixed(1)}%"></div></div>
      <div class="lab" style="margin-top:4px;"><span>TZ</span><b>${met.fmt(vTZ)}</b></div>
      <div class="bartrack"><div class="barfill b" style="width:${(100 * (vTZ || 0) / max).toFixed(1)}%"></div></div>
    </div>`;
  }
  el.innerHTML = html;
}

// ---------- crosstabs panel (% TZ por eixo, nacional, sem filtro) ----------
function renderCrosstabs() {
  const el = document.getElementById('crosstabs');
  const defs = [
    { key: 'regic_nivel', title: 'Hierarquia urbana (REGIC)', order: STATS.regic_order, labelFn: k => `${k} · ${REGIC_LABELS[k]}` },
    { key: 'tipo_arranjo', title: 'Sede × satélite de arranjo', order: STATS.arranjo_order, labelFn: k => k },
    { key: 'modelo_prestacao_simples', title: 'Modelo de prestação (MUNIC 2020, n=' + STATS.totais.modelo_prestacao_n + ')', order: STATS.modelo_order, labelFn: k => k },
    { key: 'faixa_pop', title: 'Faixa populacional', order: STATS.faixa_order, labelFn: k => k },
  ];
  let html = '';
  for (const d of defs) {
    const ct = STATS.crosstabs[d.key];
    const maxPct = Math.max(...d.order.map(k => (ct[String(k)]?.pct_tz || 0)), 0.001);
    html += `<div class="xt"><h4>${d.title}</h4>`;
    for (const k of d.order) {
      const row = ct[String(k)];
      if (!row) continue;
      const pct = (row.pct_tz * 100).toFixed(1);
      html += `<div class="xtrow">
        <div class="xtrack"><div class="xtfill" style="width:${(100 * row.pct_tz / maxPct).toFixed(1)}%"></div></div>
        <span>${d.labelFn(k)}</span><b style="color:var(--text)">${pct}% (n=${row.n_tz})</b>
      </div>`;
    }
    html += `</div>`;
  }
  el.innerHTML = html;
}

// ---------- TZ table ----------
let tzSort = { k: 'pib_pc', dir: -1 };
function renderTZTable() {
  let rows = STATS.tz_list.filter(r => {
    if (state.uf && r.uf !== state.uf) return false;
    if (state.faixa && r.faixa_pop !== state.faixa) return false;
    if (state.regic && String(r.regic_nivel) !== state.regic) return false;
    if (state.arranjo && r.tipo_arranjo !== state.arranjo) return false;
    return true;
  });
  rows = rows.slice().sort((a, b) => {
    const av = a[tzSort.k], bv = b[tzSort.k];
    if (av == null) return 1; if (bv == null) return -1;
    return av > bv ? tzSort.dir : av < bv ? -tzSort.dir : 0;
  });
  const tbody = document.querySelector('#tzTable tbody');
  tbody.innerHTML = rows.map(r => `<tr data-id="${r.id}">
      <td>${r.nome}</td><td>${r.uf}</td>
      <td>${r.tz_status === 'Ativa' ? '<span class="tag ativa">Ativa</span>' : '<span class="tag encerrada">Encerrada</span>'}</td>
      <td>${r.tz_ano ?? '—'}</td><td>${r.regic_label ?? '—'}</td><td>${r.tipo_arranjo ?? '—'}</td>
      <td>${fmtNum(r.pop)}</td><td>${fmtNum(r.pib_pc)}</td><td>${fmtNum(r.motorizacao)}</td>
    </tr>`).join('');
}

// ---------- controls wiring ----------
function populateSelects() {
  const uf = document.getElementById('ufFilter');
  for (const u of STATS.uf_list) {
    const opt = document.createElement('option');
    opt.value = u.uf; opt.textContent = `${u.uf_nome} (${u.uf})`;
    uf.appendChild(opt);
  }
  const faixa = document.getElementById('faixaFilter');
  for (const f of STATS.faixa_order) {
    const opt = document.createElement('option');
    opt.value = f; opt.textContent = f;
    faixa.appendChild(opt);
  }
}

document.getElementById('colorBy').addEventListener('change', e => { state.colorBy = e.target.value; render(); });
document.getElementById('ufFilter').addEventListener('change', e => { state.uf = e.target.value; render(); renderTZTable(); });
document.getElementById('faixaFilter').addEventListener('change', e => { state.faixa = e.target.value; render(); renderTZTable(); });
document.getElementById('regicFilter').addEventListener('change', e => { state.regic = e.target.value; render(); renderTZTable(); });
document.getElementById('arranjoFilter').addEventListener('change', e => { state.arranjo = e.target.value; render(); renderTZTable(); });
document.getElementById('modeloFilter').addEventListener('change', e => { state.modelo = e.target.value; render(); });
document.getElementById('tzFilter').addEventListener('change', e => { state.tzFilter = e.target.value; render(); });

document.querySelectorAll('#tzTable th').forEach(th => {
  th.addEventListener('click', () => {
    const k = th.dataset.k;
    tzSort.dir = (tzSort.k === k) ? -tzSort.dir : -1;
    tzSort.k = k;
    renderTZTable();
  });
});

document.querySelector('#tzTable tbody').addEventListener('click', e => {
  const tr = e.target.closest('tr');
  if (!tr) return;
  const m = MUNI.get(tr.dataset.id);
  renderDetail(m);
});

const tooltip = document.getElementById('tooltip');
svg.addEventListener('mousemove', e => {
  const path = e.target.closest('path');
  if (!path) { tooltip.style.display = 'none'; return; }
  const m = MUNI.get(path.dataset.id);
  if (!m) { tooltip.style.display = 'none'; return; }
  const metricLabel = {
    tz: m.tz_status, faixa_pop: m.faixa_pop,
    regic_nivel: m.regic_label, tipo_arranjo: m.tipo_arranjo,
    modelo_prestacao_simples: m.modelo_prestacao ?? 'sem dado',
    pib_pc: 'R$ ' + fmtNum(m.pib_pc), motorizacao: fmtNum(m.motorizacao), ibeu: fmtNum(m.ibeu), idh: fmtNum(m.idh),
    cresc_pop: fmtNum(m.cresc_pop), rec_prop_pc: 'R$ ' + fmtNum(m.rec_prop_pc),
    taxa_obitos_transito: fmtNum(m.taxa_obitos_transito) + ' /100mil',
    pct_investimento_desp: fmtNum(m.pct_investimento_desp) + '%',
    tarifa: m.tarifa != null ? 'R$ ' + fmtNum(m.tarifa) : 'sem dado',
    subsidio_ntu_pct: m.subsidio_ntu_pct != null ? fmtNum(m.subsidio_ntu_pct) + '%' : 'sem dado',
  }[state.colorBy];
  tooltip.innerHTML = `<b>${m.nome} – ${m.uf}</b>${metricLabel}`;
  tooltip.style.left = (e.clientX + 14) + 'px';
  tooltip.style.top = (e.clientY + 14) + 'px';
  tooltip.style.display = 'block';
});
svg.addEventListener('mouseleave', () => tooltip.style.display = 'none');
svg.addEventListener('click', e => {
  const path = e.target.closest('path');
  if (!path) return;
  const m = MUNI.get(path.dataset.id);
  renderDetail(m);
});

// ---------- init ----------
populateSelects();
renderCards();
render();
renderCrosstabs();
renderTZTable();
