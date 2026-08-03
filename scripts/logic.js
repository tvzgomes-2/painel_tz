// ---------- load embedded data ----------
const TOPO = JSON.parse(document.getElementById('topo-data').textContent);
const STATS = JSON.parse(document.getElementById('data-stats').textContent);
const MUNI_COL = JSON.parse(document.getElementById('data-muni').textContent);
const FONTES_RAW = JSON.parse(document.getElementById('data-fontes').textContent);
const NOTICIAS_RAW = JSON.parse(document.getElementById('data-noticias').textContent);
const CAMADAS_RAW = JSON.parse(document.getElementById('data-camadas').textContent);

// zip columnar municipal data into id -> row object
const COLS = MUNI_COL.cols;
const MUNI = new Map();
for (const row of MUNI_COL.data) {
  const obj = {};
  for (let i = 0; i < COLS.length; i++) obj[COLS[i]] = row[i];
  obj.rec_prop_pc = (obj.rec_prop != null && obj.pop) ? obj.rec_prop / obj.pop : null;
  obj.tz_bin = (obj.tz_status === 'Ativa' || obj.tz_status === 'Encerrada') ? 'TZ' : 'Não TZ';
  obj.tz_ano_num = obj.tz_ano != null ? parseInt(String(obj.tz_ano).slice(0, 4)) : null;
  obj.tz_fim_num = obj.tz_fim != null ? parseInt(String(obj.tz_fim).slice(0, 4)) : null;
  MUNI.set(obj.id, obj);
}

// ---------- fontes por município (Fase 8 — casos por fonte, ver ROADMAP §3/§8) ----------
// crosswalk gerado a partir de 03 - Dados/_data/casos por fonte (11 arquivos incorporados nesta
// rodada; ver Pendências.md/ROADMAP.md para a lista dos ainda não incorporados).
function normKey(nome, uf) {
  return (nome || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '') + '|' + (uf || '').toUpperCase();
}
// Painel cita só artigos/estudos acadêmicos (tipo "Estudo acadêmico") — a pedido do autor
// (27/07/2026), levantamentos de coleta própria (ex.: "Municípios com FFPT", planilha de
// levantamento) e reportagens de jornal/revista ficam de fora da citação pública, mesmo
// aparecendo no crosswalk bruto de casos_por_fonte.json.
const FONTES = new Map();
const FONTES_FLAT = [];
for (const k in FONTES_RAW) {
  const [nome, uf] = k.split('|');
  const academicas = FONTES_RAW[k].filter(f => f.tipo === 'Estudo acadêmico');
  if (academicas.length) FONTES.set(normKey(nome, uf), academicas);
  for (const f of academicas) FONTES_FLAT.push({ nome, uf, ...f });
}
function fontesFor(m) { return (m && FONTES.get(normKey(m.nome, m.uf))) || []; }
for (const r of STATS.tz_list) r.n_fontes = fontesFor(r).length;

// ---------- notícias por município (consolidação de referências, 27/07/2026) ----------
// Reportagens de imprensa mapeadas em 05 - Referências/Reportagens por município (cofre), separadas
// das "Fontes" acima por decisão do autor (27/07/2026): "Fontes" segue restrita a estudo acadêmico;
// notícias de jornal/revista/site aparecem numa seção própria, sem se misturar com a citação acadêmica.
const NOTICIAS = new Map();
for (const k in NOTICIAS_RAW) {
  const [nome, uf] = k.split('|');
  NOTICIAS.set(normKey(nome, uf), NOTICIAS_RAW[k]);
}
function noticiasFor(m) { return (m && NOTICIAS.get(normKey(m.nome, m.uf))) || []; }

// ---------- régua descritiva ampliada — camadas 2a/3/4 (além da universal) ----------
// Consolidação 29/07/2026: 24 temporal-dias + 4 espacial-periférica + 4 grupo social = 32
// municípios, a pedido do autor ("aplicação de uma régua descritiva... ampliando para além da
// universal"). Exclui de propósito a camada 2b/temporal-eventos (324 gratuidades eleitorais/
// pontuais — mesma decisão já tomada para o card "TZ parciais", ver comentário mais abaixo):
// fenômeno de origem judicial (STF), não adesão municipal voluntária — misturar inflaria o número
// e mudaria o sentido do que está sendo medido. Um município pode ter mais de uma camada ao mesmo
// tempo (ex.: Belo Horizonte tem 2a + 3 + 4).
const CAMADAS = new Map();
for (const k in CAMADAS_RAW) {
  const [nome, uf] = k.split('|');
  CAMADAS.set(normKey(nome, uf), CAMADAS_RAW[k]);
}
function camadasFor(m) { return (m && CAMADAS.get(normKey(m.nome, m.uf))) || []; }
const CAMADA_LABELS = { '2a': 'Temporal (dias)', '3': 'Espacial (periférica)', '4': 'Grupo social' };

// ---------- lista de municípios com TZ parcial (para a tabela "Municípios com Tarifa Zero") ----------
// Município com alguma camada (2a/3/4) que NÃO está no bucket universal (tz_bin!=='TZ') — evita
// duplicar quem a base principal já classifica como Ativa/Encerrada (ex.: Palmas, já contado na
// universal; São Caetano do Sul, ainda "Ativa" na base apesar da revogação — ver flag no card de
// detalhe). Ano de início é uma extração best-effort de um ano de 4 dígitos no texto de "detalhe"
// de camadas_tz.json — nem toda camada tem essa informação estruturada (ex.: passe estudantil de
// BH/Uberlândia e o programa de desempregados de Curitiba não têm data), fica "—" nesses casos.
function camadaAnoInicio(m) {
  let minYear = null;
  for (const c of camadasFor(m)) {
    const match = (c.detalhe || '').match(/(19[89]\d|20[0-2]\d)/);
    if (match) {
      const y = parseInt(match[1], 10);
      if (minYear == null || y < minYear) minYear = y;
    }
  }
  return minYear;
}
const PARCIAL_LIST = [];
for (const m of MUNI.values()) {
  if (m.tz_bin === 'TZ') continue;
  const camadas = camadasFor(m);
  if (!camadas.length) continue;
  PARCIAL_LIST.push(Object.assign({}, m, {
    tz_status: 'Parcial',
    tz_ano: camadaAnoInicio(m),
    n_fontes: fontesFor(m).length,
  }));
}

// ---------- agregados extras (censo22 modal, série motorização) ----------
// Pré-computados 26/07/2026 a partir de base_municipal_v3.csv (script avulso, fora do build
// regular) — mover para build_stats.py quando o pipeline completo rodar de novo. Metodologia:
// grupo TZ restrito a tz_ano_inicio<=ano de referência (mesma correção cronológica já aplicada
// nas Análises I/II do Cap 2 — ver Pendências.md, evita comparar "antes da TZ" com rótulo "TZ").
const MODAL_COMPARACAO = {
  n_tz: 73, n_ntz: 5426, ano_ref: 2022,
  modos: [
    { k: 'onibus', label: 'Ônibus', tz: 15.06, ntz: 9.41 },
    { k: 'automovel', label: 'Automóvel', tz: 35.19, ntz: 24.29 },
    { k: 'motocicleta', label: 'Motocicleta', tz: 13.55, ntz: 24.83 },
    { k: 'a_pe', label: 'A pé', tz: 22.76, ntz: 28.68 },
    { k: 'bicicleta', label: 'Bicicleta', tz: 8.31, ntz: 7.15 },
  ],
};

// ---------- decode topojson (two layers: municipios + ufs) ----------
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

function geomToRings(g) {
  if (g.type === 'Polygon') return g.arcs.map(arcsToRing);
  if (g.type === 'MultiPolygon') {
    const rings = [];
    for (const poly of g.arcs) for (const ring of poly) rings.push(arcsToRing(ring));
    return rings;
  }
  return [];
}

const muniGeoms = TOPO.objects.municipios_simpl.geometries;
const ufGeoms = TOPO.objects.ufs.geometries;

let lonMin = Infinity, lonMax = -Infinity, latMin = Infinity, latMax = -Infinity;
const features = muniGeoms.map(g => {
  const rings = geomToRings(g);
  let bLonMin = Infinity, bLonMax = -Infinity, bLatMin = Infinity, bLatMax = -Infinity;
  for (const ring of rings) for (const [lon, lat] of ring) {
    if (lon < bLonMin) bLonMin = lon; if (lon > bLonMax) bLonMax = lon;
    if (lat < bLatMin) bLatMin = lat; if (lat > bLatMax) bLatMax = lat;
  }
  if (bLonMin < lonMin) lonMin = bLonMin; if (bLonMax > lonMax) lonMax = bLonMax;
  if (bLatMin < latMin) latMin = bLatMin; if (bLatMax > latMax) latMax = bLatMax;
  return { id: g.properties.cod_ibge, rings, bbox: [bLonMin, bLatMin, bLonMax, bLatMax] };
});
const ufFeatures = ufGeoms.map(g => ({ uf2: g.properties.uf2, rings: geomToRings(g) }));

const latMean = (latMin + latMax) / 2;
const cosLat = Math.cos(latMean * Math.PI / 180);
const W = 760, H = 800, PAD = 10;
const spanX = (lonMax - lonMin) * cosLat, spanY = (latMax - latMin);
const K = Math.min((W - 2 * PAD) / spanX, (H - 2 * PAD) / spanY);
const offX = PAD + ((W - 2 * PAD) - spanX * K) / 2;
const offY = PAD + ((H - 2 * PAD) - spanY * K) / 2;

function project([lon, lat]) {
  return [offX + (lon - lonMin) * cosLat * K, offY + (latMax - lat) * K];
}
function projectBbox([bLonMin, bLatMin, bLonMax, bLatMax]) {
  const [x1, y1] = project([bLonMin, bLatMax]);
  const [x2, y2] = project([bLonMax, bLatMin]);
  return [x1, y1, x2 - x1, y2 - y1]; // x, y, w, h em coordenadas do svg
}

function ringToPath(ring) {
  let d = '';
  for (let i = 0; i < ring.length; i++) {
    const [x, y] = project(ring[i]);
    d += (i === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1);
  }
  return d + 'Z';
}

// ---------- render map paths (não-TZ primeiro, TZ depois — contorno fica por cima; UF por último) ----------
const svg = document.getElementById('mapSvg');
svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
const HOME_VB = [0, 0, W, H];
const pathById = new Map();
// Ordem de empilhamento no mapa (ajuste 29/07/2026, a pedido do autor): não-TZ (base) → ativa →
// parcial → encerrada (topo) → limites de UF. Cada camada em seu próprio grupo SVG, para que o
// contorno de quem está "por cima" apareça em municípios vizinhos de categorias diferentes.
const gNaoTz = document.createElementNS('http://www.w3.org/2000/svg', 'g');
const gAtiva = document.createElementNS('http://www.w3.org/2000/svg', 'g');
const gParcial = document.createElementNS('http://www.w3.org/2000/svg', 'g');
const gEncerrada = document.createElementNS('http://www.w3.org/2000/svg', 'g');
const gUf = document.createElementNS('http://www.w3.org/2000/svg', 'g');

for (const f of features) {
  const d = f.rings.map(ringToPath).join(' ');
  const el = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  el.setAttribute('d', d);
  el.dataset.id = f.id;
  el.classList.add('mun');
  const m = MUNI.get(f.id);
  if (m && m.tz_bin === 'TZ') {
    el.classList.add('tzpath');
    if (m.tz_status === 'Encerrada') { el.classList.add('enc'); gEncerrada.appendChild(el); }
    else { gAtiva.appendChild(el); }
  } else if (m && camadasFor(m).length) {
    // contorno tracejado para camada parcial (2a/3/4) — só quando o município não já tem
    // contorno sólido de TZ universal acima (evita duplo contorno e mantém a distinção visual).
    el.classList.add('tzparcial');
    gParcial.appendChild(el);
  } else {
    gNaoTz.appendChild(el);
  }
  pathById.set(f.id, el);
}
for (const uf of ufFeatures) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  el.setAttribute('d', uf.rings.map(ringToPath).join(' '));
  el.classList.add('ufline');
  gUf.appendChild(el);
}
svg.appendChild(gNaoTz);
svg.appendChild(gAtiva);
svg.appendChild(gParcial);
svg.appendChild(gEncerrada);
svg.appendChild(gUf);

// ---------- auto-encaixe (animação do viewBox) ----------
let vbAnim = null;
function setViewBox(vb) {
  svg.setAttribute('viewBox', vb.map(v => v.toFixed(1)).join(' '));
}
function animateViewBox(target, ms = 350) {
  if (vbAnim) cancelAnimationFrame(vbAnim);
  const from = svg.getAttribute('viewBox').split(' ').map(Number);
  const t0 = performance.now();
  function step(t) {
    const p = Math.min(1, (t - t0) / ms);
    const e = 1 - Math.pow(1 - p, 3); // ease-out cúbico
    setViewBox(from.map((v, i) => v + (target[i] - v) * e));
    if (p < 1) vbAnim = requestAnimationFrame(step);
  }
  vbAnim = requestAnimationFrame(step);
}
function bboxToViewBox(x, y, w, h, padFrac = 0.12) {
  const pad = Math.max(w, h) * padFrac;
  let vw = w + 2 * pad, vh = h + 2 * pad;
  const ar = W / H; // manter a proporção do canvas
  if (vw / vh > ar) vh = vw / ar; else vw = vh * ar;
  return [x + w / 2 - vw / 2, y + h / 2 - vh / 2, vw, vh];
}
function zoomToUF(uf) {
  let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
  for (const f of features) {
    const m = MUNI.get(f.id);
    if (!m || m.uf !== uf) continue;
    const [x, y, w, h] = projectBbox(f.bbox);
    if (x < x1) x1 = x; if (y < y1) y1 = y;
    if (x + w > x2) x2 = x + w; if (y + h > y2) y2 = y + h;
  }
  if (x1 === Infinity) return;
  animateViewBox(bboxToViewBox(x1, y1, x2 - x1, y2 - y1));
  document.getElementById('zoomHint').textContent = 'enquadrado: ' + uf;
}
function zoomToMuni(f) {
  const [x, y, w, h] = projectBbox(f.bbox);
  animateViewBox(bboxToViewBox(x, y, w, h, 1.6));
  const m = MUNI.get(f.id);
  document.getElementById('zoomHint').textContent = 'enquadrado: ' + (m ? m.nome + ' – ' + m.uf : '');
}
function resetZoom() {
  animateViewBox(HOME_VB);
  document.getElementById('zoomHint').textContent = '';
}
document.getElementById('resetZoom').addEventListener('click', resetZoom);

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
const ARRANJO_COLORS = { 'Sede/co-sede do arranjo': '#08519c', 'Satélite do arranjo': '#6baed6', 'Fora de arranjo': '#5c6470' };
const MODELO_COLORS = {
  'Concessão': '#2171b5', 'Prestação direta': '#2e9e5b', 'Permissão': '#e2892c',
  'Autorização': '#c9b458', 'Não regulamentado': '#a63603', 'Misto (2+ modelos)': '#756bb1'
};
// identidade visual da pesquisa: verde = TZ ativa (universal), rosa = encerrada/revogação, amarelo
// reservado à gradação de TZ parcial (corParcial, abaixo) — decisão de 29/07/2026 (autor já havia
// testado verde antes, ver CHANGELOG v0.4/Fase 9; volta agora para diferenciar visualmente da
// escala amarela do parcial. Nota: combina 3 das 4 cores da identidade num mesmo painel — exceção
// registrada no CHANGELOG, já que a regra de "não misturar duas das três" foi pensada para peças
// gráficas isoladas, não para um painel com várias camadas de informação simultâneas).
const TZ_COLORS_HEX = { 'Ativa': '#6FBE44', 'Encerrada': '#FF2D6B' };

// ---------- gradação da régua descritiva (v0.4.03, a pedido do autor) ----------
// Substitui o contorno tracejado (v0.4.02, achado ruim pelo autor) por preenchimento em variação
// de saturação do amarelo: quanto mais camadas parciais (2a/3/4) um município acumula, mais perto
// do amarelo pleno (universal) ele chega — nunca chega lá de fato, para não confundir com universal.
// É uma gradação por CONTAGEM de camadas (não por tipo — não há hierarquia documentada entre
// 2a/3/4 na régua), decisão de design registrada no CHANGELOG.
function hexToRgbArr(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
function mixHex(hexA, hexB, t) {
  const [ar, ag, ab] = hexToRgbArr(hexA), [br, bg, bb] = hexToRgbArr(hexB);
  const r = Math.round(ar + (br - ar) * t), g = Math.round(ag + (bg - ag) * t), b = Math.round(ab + (bb - ab) * t);
  return '#' + [r, g, b].map(v => v.toString(16).padStart(2, '0')).join('');
}
function corParcial(nCamadas) {
  // rampa invertida (ajuste 29/07/2026, a pedido do autor): amarelo mais forte em 1 camada,
  // decaindo conforme acumula camadas — 1→0.75, 2→0.5, 3+→0.25 (nunca 1.0 = universal, nunca 0 = não-TZ).
  const t = 1 - Math.min(nCamadas, 3) / 4;
  return mixHex(NEUTRALS.naoTz, '#F5E400', t);
}
// cores de texto pequeno (legenda da linha do tempo) — acompanham TZ_COLORS_HEX
function tzUi() {
  return { ativa: '#6FBE44', enc: '#f96d92', parcial: '#F5E400' };
}

// tons neutros por tema (fills aplicados via JS precisam acompanhar o tema)
const NEUTRALS = { naoTz: '#2b2f39', noData: '#22262e', filteredOut: '#1a1d23' };
function neutrals() { return NEUTRALS; }

function classify(v, breaks) {
  if (v == null || isNaN(v)) return null;
  for (let i = 1; i < breaks.length; i++) {
    if (v <= breaks[i] || i === breaks.length - 1) return i - 1;
  }
  return breaks.length - 2;
}

function colorFor(m, colorBy) {
  const nt = neutrals();
  if (!m) return nt.noData;
  if (colorBy === 'tz') {
    if (TZ_COLORS_HEX[m.tz_status]) return TZ_COLORS_HEX[m.tz_status];
    const camadas = camadasFor(m);
    if (camadas.length) return corParcial(camadas.length);
    return nt.naoTz;
  }
  if (colorBy === 'faixa_pop') return FAIXA_COLORS[m.faixa_pop] || nt.noData;
  if (colorBy === 'regic_nivel') return REGIC_COLORS[m.regic_nivel] || nt.noData;
  if (colorBy === 'tipo_arranjo') return ARRANJO_COLORS[m.tipo_arranjo] || nt.noData;
  if (colorBy === 'modelo_prestacao_simples') return m.modelo_prestacao_simples ? (MODELO_COLORS[m.modelo_prestacao_simples] || nt.noData) : nt.noData;
  const v = colorBy === 'rec_prop_pc' ? m.rec_prop_pc : m[colorBy];
  const breaks = STATS.breaks[colorBy];
  const cls = classify(v, breaks);
  if (cls == null) return nt.noData;
  return PALETTES[colorBy][cls];
}

// ---------- filters state ----------
const state = { colorBy: 'tz', uf: '', faixa: '', regic: '', arranjo: '', modelo: '', tzFilter: '', camada: '' };

function passesCamadaFilter(m) {
  if (!state.camada) return true;
  if (state.camada === '1') return m.tz_bin === 'TZ';
  return camadasFor(m).some(c => c.camada === state.camada);
}

function passesFilter(m) {
  if (!m) return false;
  if (state.uf && m.uf !== state.uf) return false;
  if (state.faixa && m.faixa_pop !== state.faixa) return false;
  if (state.regic && String(m.regic_nivel) !== state.regic) return false;
  if (state.arranjo && m.tipo_arranjo !== state.arranjo) return false;
  if (state.modelo && m.modelo_prestacao_simples !== state.modelo) return false;
  if (state.tzFilter && m.tz_bin !== state.tzFilter) return false;
  if (!passesCamadaFilter(m)) return false;
  return true;
}
// subconjunto que ignora o recorte TZ (para comparações TZ×Não-TZ, cards e linha do tempo)
function subsetNoTz() {
  const rows = [];
  for (const m of MUNI.values()) {
    if (state.uf && m.uf !== state.uf) continue;
    if (state.faixa && m.faixa_pop !== state.faixa) continue;
    if (state.regic && String(m.regic_nivel) !== state.regic) continue;
    if (state.arranjo && m.tipo_arranjo !== state.arranjo) continue;
    if (state.modelo && m.modelo_prestacao_simples !== state.modelo) continue;
    rows.push(m);
  }
  return rows;
}

function render() {
  const nt = neutrals();
  for (const [id, el] of pathById) {
    const m = MUNI.get(id);
    const pass = passesFilter(m);
    el.setAttribute('fill', pass ? colorFor(m, state.colorBy) : nt.filteredOut);
    el.style.opacity = pass ? '1' : '.25';
  }
  renderLegend();
  renderBars();
  renderCards();
  renderTimeline();
  renderPopScore();
}

function renderLegend() {
  const el = document.getElementById('legend');
  const nt = neutrals();
  let html = '';
  if (state.colorBy === 'tz') {
    html = `<span><span class="sw" style="background:${TZ_COLORS_HEX.Ativa}"></span>Ativa (universal)</span>
            <span><span class="sw" style="background:${corParcial(1)}"></span>Parcial · 1 camada</span>
            <span><span class="sw" style="background:${corParcial(2)}"></span>Parcial · 2 camadas</span>
            <span><span class="sw" style="background:${corParcial(3)}"></span>Parcial · 3 camadas</span>
            <span><span class="sw" style="background:${TZ_COLORS_HEX.Encerrada}"></span>Encerrada</span>
            <span><span class="sw" style="background:${nt.naoTz}"></span>Não TZ</span>`;
  } else if (state.colorBy === 'faixa_pop') {
    html = STATS.faixa_order.map(f => `<span><span class="sw" style="background:${FAIXA_COLORS[f]}"></span>${f}</span>`).join('');
  } else if (state.colorBy === 'regic_nivel') {
    html = STATS.regic_order.map(r => `<span><span class="sw" style="background:${REGIC_COLORS[r]}"></span>${r} · ${REGIC_LABELS[r]}</span>`).join('');
  } else if (state.colorBy === 'tipo_arranjo') {
    html = STATS.arranjo_order.map(a => `<span><span class="sw" style="background:${ARRANJO_COLORS[a]}"></span>${a}</span>`).join('');
  } else if (state.colorBy === 'modelo_prestacao_simples') {
    html = STATS.modelo_order.map(a => `<span><span class="sw" style="background:${MODELO_COLORS[a]}"></span>${a}</span>`).join('')
      + `<span><span class="sw" style="background:${nt.noData}"></span>Sem dado (MUNIC 2020, ${5570 - STATS.totais.modelo_prestacao_n} municípios)</span>`;
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
function fmtCompact(v) {
  if (v == null || isNaN(v)) return '—';
  if (v >= 1e6) return (v / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' mi';
  if (v >= 1e3) return (v / 1e3).toLocaleString('pt-BR', { maximumFractionDigits: 0 }) + ' mil';
  return v.toLocaleString('pt-BR');
}
function median(arr) {
  const a = arr.filter(v => v != null && !isNaN(v)).sort((x, y) => x - y);
  if (!a.length) return null;
  const mid = Math.floor(a.length / 2);
  return a.length % 2 ? a[mid] : (a[mid - 1] + a[mid]) / 2;
}

// ---------- grandes números dinâmicos (reagem ao recorte atual) ----------
// TZ parciais (camadas_tz.json, 29/07/2026): 24 temporal-dias + 4 espacial-periférico + 4 grupo
// social = 32 nacionalmente. Exclui de propósito as 324 "temporal-eventos" (gratuidade eleitoral/
// pontual, decisão do STF) — fenômeno qualitativamente diferente (não é adesão municipal
// voluntária), somar junto inflaria o número e misturaria categorias. Desde 29/07/2026 tem
// recorte por município (ver camadasFor()) — o card abaixo agora reage ao filtro atual, como os
// demais.
function countParciais(rows) {
  // mesma regra do contorno no mapa (tzparcial): só conta quem NÃO já está no bucket universal
  // (Ativa/Encerrada) — evita contar duas vezes um município que aparece nas duas camadas por
  // desatualização da base principal (ex.: São Caetano do Sul, ainda "Ativa" apesar da revogação
  // de 15/07/2026 — ver flag no card de detalhe do município).
  return rows.reduce((n, m) => n + (m.tz_bin !== 'TZ' && camadasFor(m).length ? 1 : 0), 0);
}

function renderCards() {
  const rows = subsetNoTz();
  const tzRows = rows.filter(m => m.tz_bin === 'TZ');
  const ativas = tzRows.filter(m => m.tz_status === 'Ativa');
  const popTZ = ativas.reduce((s, m) => s + (m.pop || 0), 0);
  const pibMed = median(rows.map(m => m.pib_pc));
  const hasFilter = state.uf || state.faixa || state.regic || state.modelo;
  const scopeLabel = hasFilter ? 'no recorte' : 'no Brasil';
  const smallN = tzRows.length > 0 && tzRows.length < 5;
  const warn = smallN ? '<span class="warn-n">⚠ amostra pequena</span>' : '';
  const cards = [
    { n: rows.length.toLocaleString('pt-BR'), l: `Municípios ${scopeLabel}` },
    { n: ativas.length.toLocaleString('pt-BR'), l: `TZ ativas (<b>universal</b>) ${scopeLabel}`, w: warn },
    { n: countParciais(rows).toLocaleString('pt-BR'), l: `TZ <b>parciais</b> ${scopeLabel} (dias, bairros ou grupo social — fora da universal; não conta as 324 gratuidades eleitorais/eventuais)` },
    { n: (rows.length ? (100 * tzRows.length / rows.length) : 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + '%', l: `% com histórico de TZ universal ${scopeLabel}`, w: warn },
    { n: fmtCompact(popTZ), l: `Pessoas vivendo com TZ universal ativa ${scopeLabel} (soma da população, Censo 2022)`, w: warn },
    { n: pibMed != null ? 'R$ ' + fmtNum(pibMed) : '—', l: `PIB per capita mediano ${scopeLabel} (2021)` },
  ];
  document.getElementById('cards').innerHTML = cards.map(c =>
    `<div class="card"><div class="n">${c.n}</div><div class="l">${c.l}${c.w || ''}</div></div>`).join('');
}

// ---------- score de população abrangida pela Tarifa Zero (v1, 29/07/2026) ----------
// Metodologia aprovada pelo autor (29/07/2026): "quando é universal soma todos, quando é
// parcial, soma a estimativa de população daquele grupo". v1 simplificada:
//   - camada universal (tz_bin==='TZ'): 100% da população residente (Censo 2022).
//   - camada 4/grupo social COM estimativa carregada em camadas_tz.json (pop_estimada) — hoje só
//     Belo Horizonte e Uberlândia, proxy "estudo_total" do Censo 2022 (deslocamento p/ estudo,
//     não a contagem real de beneficiários do passe estudantil).
//   - demais casos de TZ parcial (temporal-dias/2a, espacial-periférica/3, grupo social sem dado
//     direto — Curitiba/desempregados) ficam de fora da soma, marcados "sem estimativa": não há
//     recorte sub-municipal defensável na base atual (ver Pendências.md, 29/07/2026).
//   - gratuidades por lei federal (idoso/PcD) NÃO somadas nesta v1: a base não tem população
//     idosa/PcD por município (pendência aberta, mesma nota).
// Evita contar 2x: um município só entra em UM dos dois buckets (universal OU parcial-estimado),
// nunca nos dois — mesma regra de exclusividade já usada em countParciais()/tzparcial no mapa.
function popScore(rows) {
  let popUniversal = 0, popParcialEstimada = 0;
  const semEstimativa = [];
  for (const m of rows) {
    if (m.tz_bin === 'TZ') { popUniversal += (m.pop || 0); continue; }
    const camadas = camadasFor(m);
    if (!camadas.length) continue;
    const comEstimativa = camadas.find(c => c.pop_estimada != null);
    if (comEstimativa) popParcialEstimada += comEstimativa.pop_estimada;
    else semEstimativa.push(m.nome + '/' + m.uf);
  }
  return { popUniversal, popParcialEstimada, semEstimativa };
}

function renderPopScore() {
  const el = document.getElementById('popScore');
  if (!el) return;
  const rows = subsetNoTz();
  const totalPop = rows.reduce((s, m) => s + (m.pop || 0), 0);
  const { popUniversal, popParcialEstimada, semEstimativa } = popScore(rows);
  const popTotal = popUniversal + popParcialEstimada;
  const pct = totalPop ? (100 * popTotal / totalPop) : 0;
  const cards = [
    { n: fmtCompact(popUniversal), l: 'População com TZ <b>universal</b> (100% dos moradores do município, Censo 2022)' },
    { n: fmtCompact(popParcialEstimada), l: 'População estimada com TZ <b>parcial por grupo social</b> (proxy Censo 2022 "estudo_total" — hoje só BH e Uberlândia, passe estudantil)' },
    { n: fmtCompact(popTotal) + ` (${pct.toFixed(2)}%)`, l: 'Total com algum acesso à TZ, das duas anteriores — % da população do recorte' },
    { n: String(semEstimativa.length), l: 'Municípios com TZ parcial <b>sem estimativa</b> (temporal-dias, espacial ou grupo social sem dado direto) — não somados' },
  ];
  let html = '<div class="cards" style="margin:4px 0 0;">' + cards.map(c =>
    `<div class="card"><div class="n">${c.n}</div><div class="l">${c.l}</div></div>`).join('') + '</div>';
  html += `<p class="sub" style="margin-top:12px;">
    <b>Metodologia v1 (aprovada pelo autor, 29/07/2026):</b> universal = 100% da população residente; grupo social/estudantil = proxy "estudo_total" (Censo 2022, deslocamento p/ estudo) — superestima levemente, pois nem todo estudante necessariamente usa o benefício. Camadas temporal (2a), espacial (3) e grupo social sem dado municipal direto (Curitiba/desempregados) ficam <b>fora da soma</b> — sem estimativa sub-municipal defensável na base atual. Gratuidades por lei federal (idoso/PcD) também não somadas: sem população idosa/PcD por município na base — pendência registrada no cofre da tese.
    ${semEstimativa.length ? `<br><b>Sem estimativa (${semEstimativa.length}):</b> ${semEstimativa.join(', ')}.` : ''}
  </p>`;
  el.innerHTML = html;
}

// ---------- linha do tempo das adoções (reage ao recorte) ----------
// Listas de municípios por ano/tipo, para o tooltip de hover das barras (ver listener de
// mousemove em '#timeline' junto do tooltip do mapa, mais abaixo) — recalculadas a cada render.
let TIMELINE_MUNIS = { universal: {}, parcial: {}, revogacao: {} };
// Ajuste pós-uso do v0.4.03 (29/07/2026, a pedido do autor): inclui o início das TZ parciais (camadas 2a/3/4), não só
// da universal. Ano de início da parcial vem de camadaAnoInicio() — extração best-effort de um ano
// de 4 dígitos no texto livre de "detalhe" (camadas_tz.json); nem todo caso tem essa informação
// (ex.: passe estudantil de BH/Uberlândia, desempregados de Curitiba) — esses ficam de fora do
// gráfico, não estimados. Correção do mesmo dia: as duas séries de adoção (universal/verde,
// parcial/amarelo) primeiro foram desenhadas lado a lado com escala própria cada uma — o autor
// notou que isso distorcia a leitura (uma barra pequena de uma série podia parecer tão alta quanto
// uma grande da outra). Agora são **empilhadas** numa única barra por ano, com uma única escala
// vertical compartilhada — altura honesta em relação ao total, universal na base e parcial por cima.
function renderTimeline() {
  const allRows = subsetNoTz();
  const rows = allRows.filter(m => m.tz_bin === 'TZ');
  const rowsParcial = allRows.filter(m => m.tz_bin !== 'TZ' && camadasFor(m).length);
  const el = document.getElementById('timeline');
  const adopt = {}, adoptParcial = {}, revoke = {};
  const adoptMunis = {}, adoptParcialMunis = {}, revokeMunis = {};
  let yMin = Infinity, yMax = -Infinity;
  for (const m of rows) {
    if (m.tz_ano_num && m.tz_ano_num > 1980 && m.tz_ano_num <= 2026) {
      adopt[m.tz_ano_num] = (adopt[m.tz_ano_num] || 0) + 1;
      (adoptMunis[m.tz_ano_num] = adoptMunis[m.tz_ano_num] || []).push(m.nome + '/' + m.uf);
      if (m.tz_ano_num < yMin) yMin = m.tz_ano_num;
      if (m.tz_ano_num > yMax) yMax = m.tz_ano_num;
    }
    if (m.tz_status === 'Encerrada' && m.tz_fim_num && m.tz_fim_num > 1980 && m.tz_fim_num <= 2026) {
      revoke[m.tz_fim_num] = (revoke[m.tz_fim_num] || 0) + 1;
      (revokeMunis[m.tz_fim_num] = revokeMunis[m.tz_fim_num] || []).push(m.nome + '/' + m.uf);
      if (m.tz_fim_num < yMin) yMin = m.tz_fim_num;
      if (m.tz_fim_num > yMax) yMax = m.tz_fim_num;
    }
  }
  for (const m of rowsParcial) {
    const y = camadaAnoInicio(m);
    if (y && y > 1980 && y <= 2026) {
      adoptParcial[y] = (adoptParcial[y] || 0) + 1;
      (adoptParcialMunis[y] = adoptParcialMunis[y] || []).push(m.nome + '/' + m.uf);
      if (y < yMin) yMin = y;
      if (y > yMax) yMax = y;
    }
  }
  // guarda as listas para o tooltip de hover (ver listener de mousemove em '#timeline', mais abaixo)
  TIMELINE_MUNIS = { universal: adoptMunis, parcial: adoptParcialMunis, revogacao: revokeMunis };
  if (yMin === Infinity) { el.innerHTML = ''; el.removeAttribute('viewBox'); return; }
  const years = []; for (let y = yMin; y <= yMax; y++) years.push(y);
  // escala única, pelo total empilhado (universal + parcial) de cada ano — não pelo máximo de
  // cada série isoladamente, para a altura da barra refletir o volume real.
  const maxTotal = Math.max(1, ...years.map(y => (adopt[y] || 0) + (adoptParcial[y] || 0)));
  const maxR = Math.max(0, ...Object.values(revoke));
  const TW = 1200, TH = 230, padL = 34, padR = 10, padT = 18;
  const axisY = padT + 140; // adoções acima do eixo, revogações abaixo
  const revH = 40;
  const bw = (TW - padL - padR) / years.length;
  const css = getComputedStyle(document.body);
  const mutedC = css.getPropertyValue('--muted').trim() || '#9aa3b2';
  const borderC = css.getPropertyValue('--border').trim() || '#2a2f3a';
  let s = '';
  s += `<line x1="${padL}" y1="${axisY}" x2="${TW - padR}" y2="${axisY}" stroke="${borderC}" stroke-width="1"/>`;
  for (let i = 0; i < years.length; i++) {
    const y = years[i];
    const x = padL + i * bw;
    const a = adopt[y] || 0, ap = adoptParcial[y] || 0, r = revoke[y] || 0;
    const total = a + ap;
    const xBar = x + bw * 0.12;
    const wBar = bw * 0.76;
    if (total > 0) {
      const hA = (a / maxTotal) * 130;
      const hAP = (ap / maxTotal) * 130;
      if (a > 0) {
        s += `<rect x="${xBar.toFixed(1)}" y="${(axisY - hA).toFixed(1)}" width="${wBar.toFixed(1)}" height="${hA.toFixed(1)}" rx="1.5" fill="${TZ_COLORS_HEX.Ativa}" data-year="${y}" data-tipo="universal"/>`;
      }
      if (ap > 0) {
        s += `<rect x="${xBar.toFixed(1)}" y="${(axisY - hA - hAP).toFixed(1)}" width="${wBar.toFixed(1)}" height="${hAP.toFixed(1)}" rx="1.5" fill="#F5E400" data-year="${y}" data-tipo="parcial"/>`;
      }
      s += `<text x="${(xBar + wBar / 2).toFixed(1)}" y="${(axisY - hA - hAP - 4).toFixed(1)}" font-size="9.5" fill="${mutedC}" text-anchor="middle">${total}</text>`;
    }
    if (r > 0) {
      const h = maxR ? (r / maxR) * revH : 0;
      s += `<rect x="${xBar.toFixed(1)}" y="${axisY + 2}" width="${wBar.toFixed(1)}" height="${h.toFixed(1)}" rx="1.5" fill="${TZ_COLORS_HEX.Encerrada}" data-year="${y}" data-tipo="revogacao"/>`;
      s += `<text x="${(xBar + wBar / 2).toFixed(1)}" y="${(axisY + h + 13).toFixed(1)}" font-size="9.5" fill="${mutedC}" text-anchor="middle">${r}</text>`;
    }
    if (y % 5 === 0 || y === yMin || y === yMax) {
      s += `<text x="${(x + bw / 2).toFixed(1)}" y="${TH - 6}" font-size="10" fill="${mutedC}" text-anchor="middle">${y}</text>`;
    }
  }
  const ui = tzUi();
  s += `<text x="${padL}" y="${padT - 5}" font-size="10.5" font-weight="700" fill="${ui.ativa}">▮ adoções (universal)</text>`;
  s += `<text x="${padL + 165}" y="${padT - 5}" font-size="10.5" font-weight="700" fill="${ui.parcial}">▮ adoções (parcial, início aprox.)</text>`;
  s += `<text x="${padL + 430}" y="${padT - 5}" font-size="10.5" font-weight="700" fill="${ui.enc}">▮ revogações</text>`;
  el.setAttribute('viewBox', `0 0 ${TW} ${TH}`);
  el.innerHTML = s;
}

// ---------- parágrafo descritivo de TZ (gerado por template, não escrito à mão — cobre os ~531
// casos da pesquisa a partir dos campos já estruturados: situação, camada, datas, população, fonte) ----------
function gerarParagrafoTZ(m) {
  const nomeUf = `${m.nome} (${m.uf})`;
  if (m.tz_status === 'Ativa') {
    const desde = m.tz_ano ? `desde ${m.tz_ano}` : 'desde uma data ainda não determinada nesta pesquisa';
    const operador = m.tz_operador ? ` A operação é feita por ${m.tz_operador}.` : '';
    return `${nomeUf} tem <b>Tarifa Zero universal</b> ${desde}: todo o transporte coletivo municipal é gratuito para qualquer usuário, todos os dias.${operador} Isso corresponde aos ${fmtCompact(m.pop)} habitantes do município (Censo 2022), sujeitos aos gaps de estimativa já registrados no painel (ver Score de população).`;
  }
  if (m.tz_status === 'Encerrada') {
    const periodo = (m.tz_ano && m.tz_fim) ? `entre ${m.tz_ano} e ${m.tz_fim}`
      : (m.tz_ano ? `a partir de ${m.tz_ano}` : 'em um período não totalmente determinado nesta pesquisa');
    return `${nomeUf} teve <b>Tarifa Zero universal</b> ${periodo}, mas a política foi <b>encerrada</b> e não está mais em vigor hoje. Entra na pesquisa como caso de reversão/trajetória, não como TZ ativa — não contar entre os municípios com gratuidade vigente.`;
  }
  if (typeof m.tz_status === 'string' && m.tz_status.startsWith('Excluída')) {
    return `${nomeUf} tem um programa de gratuidade no transporte, mas foi <b>excluído do universo desta pesquisa por escopo</b>: ${m.tz_status.replace(/^Excluída\s*/, '').replace(/^\(|\)$/g, '')}. A pesquisa cobre apenas sistemas de ônibus municipais — este caso é mantido nos dados só como registro histórico, sem contar no total canônico.`;
  }
  const camadas = camadasFor(m);
  if (camadas.length) {
    const partes = camadas.map(c => {
      const label = (CAMADA_LABELS[c.camada] || c.camada).toLowerCase();
      const prov = c.flag ? ' (classificação provisória, a confirmar)' : '';
      return `${label}${c.detalhe ? ' — ' + c.detalhe : ''}${prov}`;
    });
    return `${nomeUf} não tem Tarifa Zero universal, mas oferece <b>gratuidade parcial</b> no transporte coletivo: ${partes.join('; ')}. Não conta no total de municípios com TZ universal desta pesquisa, mas soma-se ao universo ampliado de casos mapeados pela régua descritiva.`;
  }
  return `${nomeUf} não tem nenhuma política de Tarifa Zero (universal ou parcial) mapeada até agora nesta pesquisa. Isso não significa necessariamente que o município nunca teve ou não tenha um programa de gratuidade — varreduras anteriores já mediram subnotificação nas fontes usuais (ver Achados de TZ não mapeada, 31/07-03/08/2026) — apenas que não há registro no levantamento atual.`;
}

// ---------- detail panel ----------
function renderDetail(m) {
  const el = document.getElementById('detail');
  if (!m) { el.innerHTML = '<div class="empty">Clique em um município no mapa ou na lista abaixo.</div>'; return; }
  const tzTag = m.tz_status === 'Ativa' ? '<span class="tag ativa">TZ ativa</span>'
    : m.tz_status === 'Encerrada' ? '<span class="tag encerrada">TZ encerrada</span>' : '';
  const paragrafoTZ = `<p style="margin:8px 0 0;font-size:12.5px;line-height:1.55;color:var(--text);">${gerarParagrafoTZ(m)}</p>`;
  let extra = '';
  if (m.tz_bin === 'TZ') {
    extra = `<tr><td>Início TZ</td><td>${m.tz_ano ?? '—'}</td></tr>
             <tr><td>Fim TZ</td><td>${m.tz_fim ?? '—'}</td></tr>
             <tr><td>% orçamento (fonte)</td><td>${m.tz_pct_orc ?? '—'}</td></tr>
             <tr><td>Operador</td><td>${m.tz_operador ?? '—'}</td></tr>`;
  }
  el.innerHTML = `<div><b style="font-size:15px;">${m.nome} – ${m.uf}</b> ${tzTag}</div>
    ${paragrafoTZ}
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
      <tr><td>Tarifa</td><td>${m.tz_status === 'Ativa' ? 'Gratuito (TZ universal)' : (m.tarifa != null ? 'R$ ' + fmtNum(m.tarifa) + ' (' + m.tarifa_ano + ', ' + m.tarifa_fonte + ')' : 'sem dado')}</td></tr>
      <tr><td>% custo subsidiado (NTU)</td><td>${m.subsidio_ntu_pct != null ? fmtNum(m.subsidio_ntu_pct) + '% (' + m.subsidio_ntu_ano + ')' : 'sem dado'}</td></tr>
      <tr><td>Plano Diretor</td><td>${m.plano_diretor ?? '—'}</td></tr>
      <tr><td>PlanMob (2025)</td><td>${m.pdmu_2025 ?? '—'}</td></tr>
      ${extra}
    </table>
    ${renderCamadaDetail(m)}
    ${renderFontesDetail(m)}
    ${renderNoticiasDetail(m)}`;
}

function renderCamadaDetail(m) {
  const camadas = camadasFor(m);
  if (!camadas.length) return '';
  const items = camadas.map(c => `<li><b>${CAMADA_LABELS[c.camada] || c.camada}</b> — ${c.detalhe || ''}${c.pop_estimada != null ? ` — <i>pop. estimada: ${fmtCompact(c.pop_estimada)} (${c.pop_estimada_fonte || 'estimativa'})</i>` : ''}${c.flag ? ` <span style="color:#e2892c;">⚠ ${c.flag}</span>` : ''}</li>`).join('');
  return `<div style="margin-top:10px;border-top:1px dashed var(--border);padding-top:8px;">
    <b style="font-size:12.5px;">Camada da régua descritiva (${camadas.length})</b>
    <ul style="margin:6px 0 0;padding-left:18px;font-size:12px;color:var(--muted);line-height:1.5;">${items}</ul>
  </div>`;
}

function renderFontesDetail(m) {
  const fontes = fontesFor(m);
  if (!fontes.length) return '';
  const items = fontes.map(f => `<li><b>${f.fonte}</b>${f.ano ? ' (' + f.ano + ')' : ''} — ${f.descricao || ''}${f.link ? ' — <a href="' + f.link + '" target="_blank" rel="noopener">link</a>' : ''}</li>`).join('');
  return `<div style="margin-top:10px;border-top:1px dashed var(--border);padding-top:8px;">
    <b style="font-size:12.5px;">Fontes (${fontes.length})</b>
    <ul style="margin:6px 0 0;padding-left:18px;font-size:12px;color:var(--muted);line-height:1.5;">${items}</ul>
  </div>`;
}

function renderNoticiasDetail(m) {
  const noticias = noticiasFor(m);
  if (!noticias.length) return '';
  const items = noticias.map(n => `<li><b>${n.veiculo}</b>${n.data ? ' (' + n.data + ')' : ''} — ${n.tema || ''}${n.url ? ' — <a href="' + n.url + '" target="_blank" rel="noopener">link</a>' : ''}</li>`).join('');
  return `<div style="margin-top:10px;border-top:1px dashed var(--border);padding-top:8px;">
    <b style="font-size:12.5px;">Notícias (${noticias.length})</b>
    <ul style="margin:6px 0 0;padding-left:18px;font-size:12px;color:var(--muted);line-height:1.5;">${items}</ul>
  </div>`;
}

// ---------- comparison bars ----------
const BAR_METRICS = [
  { k: 'pib_pc', label: 'PIB per capita mediano (R$)', fmt: v => 'R$ ' + fmtNum(v) },
  { k: 'motorizacao', label: 'Motorização mediana (veíc/hab)', fmt: fmtNum },
  { k: 'ibeu', label: 'IBEU mediano', fmt: fmtNum },
  { k: 'idh', label: 'IDH mediano', fmt: fmtNum },
  { k: 'rec_prop_pc', label: 'Receita própria per capita mediana (R$)', fmt: v => 'R$ ' + fmtNum(v) },
  { k: 'taxa_obitos_transito', label: 'Óbitos no trânsito /100mil mediano (2019)', fmt: fmtNum },
];

function renderBars() {
  const rows = subsetNoTz();
  const rowsTZ = rows.filter(m => m.tz_bin === 'TZ');
  const rowsNao = rows.filter(m => m.tz_bin !== 'TZ');
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

// ---------- crosstabs (rótulo acima da própria barra; % dentro de cada categoria) ----------
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
      html += `<div class="xtitem">
        <div class="xtlab"><span>${d.labelFn(k)}</span><b>${pct}% (n=${row.n_tz})</b></div>
        <div class="xtrack"><div class="xtfill" style="width:${(100 * row.pct_tz / maxPct).toFixed(1)}%"></div></div>
      </div>`;
    }
    html += `</div>`;
  }
  el.innerHTML = html;
}

// ---------- partição modal (Censo 2022) — TZ × Não-TZ, barra única 100% empilhada ----------
// Paleta restrita à identidade: azul (Ônibus) + rosa (Ativo) são as únicas cores oficiais usadas
// aqui — não combinam entre si nem com amarelo/verde (regra da Identidade Visual da Pesquisa) — e
// destacam os dois modos citados explicitamente (uso de ônibus e modos ativos). Automóvel/moto/
// outros ficam em neutros para não competir visualmente com os dois modos de interesse.
const MODAL_STACK_COLORS = { onibus: '#1A54C7', automovel: '#5c6470', motocicleta: '#8a8f9c', ativo: '#FF2D6B', outros: '#33333d' };
const MODAL_STACK_LABELS = { onibus: 'Ônibus', automovel: 'Automóvel', motocicleta: 'Motocicleta', ativo: 'Ativo (a pé + bicicleta)', outros: 'Outros' };
function renderModalStack() {
  const el = document.getElementById('modalStack');
  if (!el) return;
  const d = MODAL_COMPARACAO;
  const val = (grupo, k) => (d.modos.find(m => m.k === k) || {})[grupo] || 0;
  const linha = (grupo, label, n) => {
    const onibus = val(grupo, 'onibus'), automovel = val(grupo, 'automovel'), motocicleta = val(grupo, 'motocicleta');
    const ativo = val(grupo, 'a_pe') + val(grupo, 'bicicleta');
    const outros = Math.max(0, 100 - (onibus + automovel + motocicleta + ativo));
    const segs = [
      { k: 'onibus', v: onibus }, { k: 'automovel', v: automovel }, { k: 'motocicleta', v: motocicleta },
      { k: 'ativo', v: ativo }, { k: 'outros', v: outros },
    ];
    const bar = segs.map(s => `<div class="seg" style="width:${s.v.toFixed(2)}%;background:${MODAL_STACK_COLORS[s.k]};" title="${MODAL_STACK_LABELS[s.k]}: ${s.v.toFixed(1)}%"></div>`).join('');
    return `<div class="msrow"><div class="mslab"><b>${label}</b><span>n=${n}</span></div><div class="msbar">${bar}</div></div>`;
  };
  let html = linha('tz', `TZ (adotantes até ${d.ano_ref})`, d.n_tz);
  html += linha('ntz', 'Não-TZ', d.n_ntz);
  html += `<div class="mslegend">${Object.keys(MODAL_STACK_LABELS).map(k =>
    `<span><i style="background:${MODAL_STACK_COLORS[k]}"></i>${MODAL_STACK_LABELS[k]}</span>`).join('')}</div>`;
  el.innerHTML = html;
}

// ---------- referências bibliográficas ABNT (estudos acadêmicos citados no repositório de fontes) ----------
// Citekeys conferidos em biblioteca.bib (05 - Referências/_zotero): santini2019, angelo2023,
// vermander2021, brinco2018 (fonte citada como "brinco 2017", ano do artigo na FEE; citekey do
// Zotero usa 2018, ano dos direitos autorais — mantido "2017" na citação curta por já estar em uso
// no crosswalk de casos_por_fonte.json). "Pereira 2023" (Thais Fernandes Pereira, XIII Seminário
// Discente de Ciência Política da USP) ainda não tem citekey BBT no .bib (entrada sem chave).
const REFERENCIAS_ABNT = [
  { chave: 'Santini 2019', ref: 'SANTINI, Daniel et al. <i>Passe livre</i>: as possibilidades da tarifa zero contra a distopia da uberização. São Paulo: Autonomia Literária: Fundação Rosa Luxemburgo, 2019.' },
  { chave: 'Pereira 2023', ref: 'PEREIRA, Thais Fernandes. As capacidades estatais das cidades brasileiras com tarifa zero no transporte público. In: SEMINÁRIO DISCENTE DA PÓS-GRADUAÇÃO EM CIÊNCIA POLÍTICA DA USP, 13., 2023, São Paulo. <i>Anais eletrônicos</i> [...]. São Paulo: USP, 2023.' },
  { chave: 'Angelo 2023', ref: 'ANGELO, Danielle Andrade. <i>Tarifa Zero</i>: formas de financiamento e experiências nacionais. 2023. Trabalho de Conclusão de Curso (Graduação em Planejamento Territorial) – Universidade Federal do ABC, São Bernardo do Campo, 2023.' },
  { chave: 'Vermander 2021', ref: 'VERMANDER, Marijke. <i>Exploring fare-free public transport in Brazil</i>: rationales and characteristics of Tarifa Zero policies in small Brazilian municipalities. 2021. Dissertação (Mestrado) – Vrije Universiteit Brussel, Bruxelas, 2021.' },
  { chave: 'brinco 2017', ref: 'BRINCO, Ricardo. Tarifação e gratuidade no transporte público urbano. <i>Indicadores Econômicos FEE</i>, Porto Alegre, v. 45, n. 2, p. 79-96, 2017.' },
];

// Referências levantadas na consolidação bibliográfica de 27/07/2026 (fontes: artigo ANPET/versão
// cega, PGT092 — bibliografia + anexo de artigos selecionados, Observatório de Tarifa Zero — 3
// documentos do autor). Conferidas contra biblioteca.bib (leitura completa via bibtexparser +
// similaridade de título, não só sobrenome+ano) — nenhuma das 8 abaixo tem citekey no Zotero.
// Ainda não vinculadas a um município específico no crosswalk de Fontes (por isso ficam separadas
// da lista acima, que é só sobre os estudos citados nesse crosswalk).
const REFERENCIAS_ADICIONAIS = [
  { chave: 'Landin 2022', ref: 'LANDIN, Lucas de Paula. <i>Tarifa Zero</i>: la financiación del transporte público gratuito en el Municipio de Vargem Grande Paulista. 2022. Dissertação (Mestrado) – Universidad de Chile, Santiago, 2022.' },
  { chave: 'Campos; Santini 2024', ref: 'CAMPOS, Marcos; SANTINI, Daniel. Os sentidos da gratuidade universal no Brasil. In: <i>Institucionalização simbólica nas interações socioestatais</i>. Rio de Janeiro: EdUERJ, 2024. (referência incompleta na fonte de origem — capítulo/organizador(es) do livro a conferir antes de citar).' },
  { chave: 'CEM [s.d.]', ref: 'CENTRO DE ESTUDOS DA METRÓPOLE (CEM). <i>Base cartográfica digital georreferenciada das sedes municipais brasileiras 2010</i>. São Paulo: CEM, [s.d.]. Disponível em: https://centrodametropole.fflch.usp.br/pt-br/file/17640/download?token=K0XXrRXh. Acesso em: 27 jul. 2026.' },
  { chave: 'Fearnley 2013', ref: 'FEARNLEY, N. Free fares policies: impact on public transport mode share and other transport policy goals. <i>[periódico não especificado na fonte de origem — a conferir antes de citar]</i>, 2013.' },
  { chave: 'IBGE 2020', ref: 'INSTITUTO BRASILEIRO DE GEOGRAFIA E ESTATÍSTICA (IBGE). <i>Munic 2020</i>: pesquisa de informações básicas municipais. Rio de Janeiro: IBGE, 2020.' },
  { chave: 'Silva 2017', ref: 'SILVA, M. de L. <i>A gestão Luiza Erundina (1989-1992)</i>: participação popular nas políticas de transporte. 2017. Tese (Doutorado) – Universidade de São Paulo, São Paulo, 2017.' },
  { chave: 'Studenmund; Connor 1982', ref: 'STUDENMUND, A.; CONNOR, D. The free-fare transit experiments. <i>Transportation Research Part A: General</i>, v. 16, n. 4, p. 261-269, 1982.' },
  { chave: 'Kębłowski 2024 ⚠', ref: 'KĘBŁOWSKI, Wojciech. <i>Fare-free public transport</i>: an international perspective. Berlim: Rosa-Luxemburg-Stiftung, 2024. <b>⚠ Possível duplicata/versão anterior de "keblowski2025a"</b> (já no Zotero, título 2025 diferente — "Fare-Free Public Transport: From Policy Fringes to an Established Practice") — a confirmar antes de tratar como obra distinta.' },
];

function renderReferenciasAbnt() {
  const el = document.getElementById('referenciasAbnt');
  if (!el) return;
  let html = '<ol class="refs">' + REFERENCIAS_ABNT.map(r => `<li>${r.ref}</li>`).join('') + '</ol>';
  html += '<p class="sub" style="margin-top:14px;">Referências adicionais levantadas na consolidação bibliográfica de 27/07/2026 (ANPET, PGT092, Observatório de Tarifa Zero) — confirmadas como ausentes do Zotero (<code>biblioteca.bib</code>), ainda não vinculadas a um município específico no crosswalk de Fontes.</p>';
  html += '<ol class="refs">' + REFERENCIAS_ADICIONAIS.map(r => `<li>${r.ref}</li>`).join('') + '</ol>';
  el.innerHTML = html;
}

// ---------- TZ table ----------
let tzSort = { k: 'pib_pc', dir: -1 };
const fontesExpandedIds = new Set();
function renderTZTable() {
  let rows = STATS.tz_list.concat(PARCIAL_LIST).filter(r => {
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
  const parts = [];
  for (const r of rows) {
    const nf = r.n_fontes || 0;
    const expanded = fontesExpandedIds.has(r.id);
    const tag = r.tz_status === 'Ativa' ? '<span class="tag ativa">Ativa</span>'
      : r.tz_status === 'Encerrada' ? '<span class="tag encerrada">Encerrada</span>'
      : '<span class="tag parcial">Parcial</span>';
    parts.push(`<tr data-id="${r.id}">
      <td>${r.nome}</td><td>${r.uf}</td>
      <td>${tag}</td>
      <td>${r.tz_ano ?? '—'}</td><td>${r.regic_label ?? '—'}</td><td>${r.tipo_arranjo ?? '—'}</td>
      <td>${fmtNum(r.pop)}</td><td>${fmtNum(r.pib_pc)}</td><td>${fmtNum(r.motorizacao)}</td>
      <td>${nf ? `<button type="button" class="fontes-toggle" data-id="${r.id}">${nf} ${expanded ? '▲' : '▼'}</button>` : '—'}</td>
    </tr>`);
    if (expanded && nf) {
      const list = fontesFor(r).map(f => `<li><b>${f.fonte}</b>${f.ano ? ' (' + f.ano + ')' : ''} — ${f.descricao || ''}${f.link ? ' — <a href="' + f.link + '" target="_blank" rel="noopener">link</a>' : ''}</li>`).join('');
      parts.push(`<tr class="fontes-row"><td colspan="10"><ul class="fontes-inline">${list}</ul></td></tr>`);
    }
  }
  tbody.innerHTML = parts.join('');
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
document.getElementById('ufFilter').addEventListener('change', e => {
  state.uf = e.target.value;
  render(); renderTZTable();
  if (state.uf) zoomToUF(state.uf); else resetZoom();
});
document.getElementById('faixaFilter').addEventListener('change', e => { state.faixa = e.target.value; render(); renderTZTable(); });
document.getElementById('regicFilter').addEventListener('change', e => { state.regic = e.target.value; render(); renderTZTable(); });
document.getElementById('modeloFilter').addEventListener('change', e => { state.modelo = e.target.value; render(); });
document.getElementById('tzFilter').addEventListener('change', e => { state.tzFilter = e.target.value; render(); });
document.getElementById('camadaFilter').addEventListener('change', e => { state.camada = e.target.value; render(); renderTZTable(); });

document.querySelectorAll('#tzTable th').forEach(th => {
  th.addEventListener('click', () => {
    const k = th.dataset.k;
    tzSort.dir = (tzSort.k === k) ? -tzSort.dir : -1;
    tzSort.k = k;
    renderTZTable();
  });
});

document.querySelector('#tzTable tbody').addEventListener('click', e => {
  const toggle = e.target.closest('.fontes-toggle');
  if (toggle) {
    const id = toggle.dataset.id;
    if (fontesExpandedIds.has(id)) fontesExpandedIds.delete(id); else fontesExpandedIds.add(id);
    renderTZTable();
    return;
  }
  const tr = e.target.closest('tr');
  if (!tr || !tr.dataset.id) return;
  const m = MUNI.get(tr.dataset.id);
  renderDetail(m);
});

// ---------- tooltip (completo nos TZ; suprimido fora do recorte ativo) ----------
const tooltip = document.getElementById('tooltip');
function showTooltip(e, inner) {
  tooltip.innerHTML = inner;
  const pad = 14;
  let tx = e.clientX + pad, ty = e.clientY + pad;
  tooltip.style.display = 'block';
  const r = tooltip.getBoundingClientRect();
  if (tx + r.width > window.innerWidth - 8) tx = e.clientX - r.width - pad;
  if (ty + r.height > window.innerHeight - 8) ty = e.clientY - r.height - pad;
  tooltip.style.left = tx + 'px';
  tooltip.style.top = ty + 'px';
}
svg.addEventListener('mousemove', e => {
  const path = e.target.closest('path.mun');
  if (!path) { tooltip.style.display = 'none'; return; }
  const m = MUNI.get(path.dataset.id);
  if (!m || !passesFilter(m)) { tooltip.style.display = 'none'; return; }
  let inner;
  if (m.tz_bin === 'TZ') {
    inner = `<b>${m.nome} – ${m.uf} ${m.tz_status === 'Ativa' ? '· TZ ativa' : '· TZ encerrada'}</b>
      <div class="tt-grid">
        <span>Início</span><span>${m.tz_ano ?? '—'}</span>
        ${m.tz_fim ? `<span>Fim</span><span>${m.tz_fim}</span>` : ''}
        <span>REGIC</span><span>${m.regic_label ?? '—'}</span>
        <span>Arranjo</span><span>${m.tipo_arranjo ?? '—'}</span>
        <span>População</span><span>${fmtNum(m.pop)}</span>
        <span>PIB pc</span><span>R$ ${fmtNum(m.pib_pc)}</span>
        <span>Motorização</span><span>${fmtNum(m.motorizacao)}</span>
        ${m.tz_operador ? `<span>Operador</span><span>${m.tz_operador}</span>` : ''}
      </div>`;
  } else {
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
    inner = `<b>${m.nome} – ${m.uf}</b>${metricLabel}`;
  }
  showTooltip(e, inner);
});
svg.addEventListener('mouseleave', () => tooltip.style.display = 'none');

// ---------- tooltip da linha do tempo (lista de municípios por barra, a pedido do autor) ----------
const TIMELINE_TIPO_LABEL = {
  universal: 'adoção(ões) de TZ universal',
  parcial: 'adoção(ões) de TZ parcial (início aproximado)',
  revogacao: 'revogação(ões) de TZ universal',
};
const timelineSvg = document.getElementById('timeline');
timelineSvg.addEventListener('mousemove', e => {
  const rect = e.target.closest('rect[data-year]');
  if (!rect) { tooltip.style.display = 'none'; return; }
  const y = rect.dataset.year, tipo = rect.dataset.tipo;
  const munis = (TIMELINE_MUNIS[tipo] && TIMELINE_MUNIS[tipo][y]) || [];
  const inner = `<b>${y} · ${munis.length} ${TIMELINE_TIPO_LABEL[tipo] || tipo}</b>
    <div style="max-height:180px;overflow-y:auto;margin-top:6px;max-width:260px;color:var(--muted);">${munis.join(', ') || '—'}</div>`;
  showTooltip(e, inner);
});
timelineSvg.addEventListener('mouseleave', () => tooltip.style.display = 'none');
svg.addEventListener('click', e => {
  const path = e.target.closest('path.mun');
  if (!path) return;
  const m = MUNI.get(path.dataset.id);
  if (!m || !passesFilter(m)) return;
  renderDetail(m);
});
svg.addEventListener('dblclick', e => {
  const path = e.target.closest('path.mun');
  if (!path) return;
  const f = features.find(ft => ft.id === path.dataset.id);
  if (f) zoomToMuni(f);
});

// ---------- init ----------
populateSelects();
renderCrosstabs();
renderModalStack();
renderReferenciasAbnt();
renderTZTable();
render(); // desenha mapa, legenda, barras, cards, linha do tempo e score de população
