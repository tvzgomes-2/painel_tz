// ---------- load embedded data ----------
const TOPO = JSON.parse(document.getElementById('topo-data').textContent);
const STATS = JSON.parse(document.getElementById('data-stats').textContent);
const MUNI_COL = JSON.parse(document.getElementById('data-muni').textContent);
const FONTES_RAW = JSON.parse(document.getElementById('data-fontes').textContent);
const NOTICIAS_RAW = JSON.parse(document.getElementById('data-noticias').textContent);
const CAMADAS_RAW = JSON.parse(document.getElementById('data-camadas').textContent);
// Fase 11 / Bloco 3 (26/08/2026). Os dois crosswalks abaixo são chaveados por
// código IBGE (string) — não por "Município|UF" como os antigos. Escolha
// deliberada: o código não sofre do problema de grafia que já obrigou uma chave
// duplicada em camadas_tz.json (caso "Embu" x "Embu das Artes").
const MODAL_RAW = JSON.parse(document.getElementById('data-modal').textContent);
const GRUPOS_RAW = JSON.parse(document.getElementById('data-grupos').textContent);
const LEGISLACAO_RAW = JSON.parse(document.getElementById('data-legislacao').textContent);

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

// ---------- 11.9: partição modal do município (Censo 2022) ----------
// Mesmos 5 baldes do gráfico nacional TZ × não-TZ, para as duas leituras ficarem
// na mesma gramática. `t` é a soma bruta dos percentuais do Censo antes da
// normalização (mediana 98,75%): abaixo de 95% o painel avisa em vez de fingir
// precisão que o dado não tem.
function modalFor(m) { return (m && MODAL_RAW[String(m.id)]) || null; }

// ---------- 11.10 / 11.11: grupos econômicos por município ----------
// Exposição mínima (decisão do autor, 26/08/2026): só o nome do grupo. O código
// GE-xxx aparece no rótulo apenas quando o nome é ambíguo — 20 nomes da base são
// homônimos (sobrenomes usados por grupos distintos: "Santos" são 7 grupos
// diferentes). Sem essa desambiguação, contar alcance por nome fundiria grupos
// separados e inflaria o alcance deles.
function gruposFor(m) { return (m && GRUPOS_RAW[String(m.id)]) || []; }

// ---------- 8.4: base legal da TZ no município (levantamento jul/2026) ----------
// 137 municípios verificados, 62 com norma localizada. O levantamento é anterior à
// ampliação do universo canônico (03/08/2026), então 33 dos 169 municípios TZ de
// hoje não estavam nele — o card diz isso em vez de deixar o silêncio sugerir que
// não há norma.
function legislacaoFor(m) { return (m && LEGISLACAO_RAW[String(m.id)]) || null; }

const CONF_LABEL = {
  'alta': 'confiabilidade alta — confirmado em fonte primária',
  'média': 'confiabilidade média — número não confirmado em fonte primária',
  'baixa': 'confiabilidade baixa — número não verificado',
};

function renderLegislacaoDetail(m) {
  const L = legislacaoFor(m);
  const ehTZ = m.tz_bin === 'TZ';
  if (!L) {
    if (!ehTZ) return '';
    return `<div style="margin-top:10px;border-top:1px dashed var(--border);padding-top:8px;">
      <b style="font-size:12.5px;">Base legal</b>
      <p style="margin:5px 0 0;font-size:12px;color:var(--muted);line-height:1.5;">Não verificado. O levantamento legal cobriu 137 municípios (jul/2026), anterior à ampliação do universo desta pesquisa — este caso entrou depois e ainda não passou pela busca de norma.</p>
    </div>`;
  }
  const linhas = [];
  if (L.norma) {
    const conf = L.conf ? ` <span class="tag ${L.conf === 'alta' ? 'ativa' : 'parcial'}" title="${CONF_LABEL[L.conf] || ''}">${L.conf}</span>` : '';
    linhas.push(`<div style="font-size:12.5px;color:var(--text);margin-top:4px;"><b>${L.norma}</b>${conf}</div>`);
  } else {
    linhas.push('<div style="font-size:12px;color:var(--muted);margin-top:4px;">Norma não localizada em fonte pública — a gratuidade costuma ter sido implantada por via administrativa (licitação deserta, contrato de concessão) ou por decreto não divulgado.</div>');
  }
  const extra = [];
  if (L.mecanismo) extra.push(`<b>Mecanismo:</b> ${L.mecanismo}`);
  if (L.fundo) extra.push('<b>Fundo municipal</b> criado na própria lei');
  if (extra.length) linhas.push(`<div style="font-size:12px;color:var(--muted);margin-top:4px;">${extra.join(' · ')}</div>`);
  if (L.nota) linhas.push(`<div style="font-size:11.5px;color:var(--muted);margin-top:4px;line-height:1.5;"><i>${L.nota}</i></div>`);
  return `<div style="margin-top:10px;border-top:1px dashed var(--border);padding-top:8px;">
    <b style="font-size:12.5px;">Base legal</b>${linhas.join('')}
  </div>`;
}
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
  renderGrupos();
  renderRegiaoUf();
  renderDispersao();
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
  // 11.8: quantos municipios declararam ter sistema de onibus. Responde ao recorte,
  // como os demais cards. Nacionalmente da 1.727 — que e o mesmo numero que o
  // glossario cita, e sao 31% dos municipios: amostra parcial, nao painel nacional.
  // A ressalva viaja junto com o numero, no proprio rotulo do card.
  const comOnibus = rows.reduce((n, m) => n + (m.modelo_prestacao ? 1 : 0), 0);
  const cards = [
    { n: rows.length.toLocaleString('pt-BR'), l: `Municípios ${scopeLabel}` },
    { n: comOnibus.toLocaleString('pt-BR'), l: `Com sistema de ônibus declarado ${scopeLabel} (MUNIC 2020 — só 31% dos municípios responderam; ausência aqui não é prova de ausência)` },
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
  // 11.7: a camada da regua descritiva era uma lista no fim do card, depois de ~16
  // linhas de tabela. Sobe para tag ao lado do status de TZ; o detalhe (ressalvas,
  // pop. estimada, flags) continua embaixo, em renderCamadaDetail().
  const camadasTag = camadasFor(m).map(c =>
    `<span class="tag parcial" title="Camada ${c.camada} da régua descritiva${c.detalhe ? ' — ' + c.detalhe : ''}">${CAMADA_LABELS[c.camada] || c.camada}${c.flag ? ' ⚠' : ''}</span>`
  ).join(' ');
  const paragrafoTZ = `<p style="margin:8px 0 0;font-size:12.5px;line-height:1.55;color:var(--text);">${gerarParagrafoTZ(m)}</p>`;
  let extra = '';
  if (m.tz_bin === 'TZ') {
    extra = `<tr><td>Início TZ</td><td>${m.tz_ano ?? '—'}</td></tr>
             <tr><td>Fim TZ</td><td>${m.tz_fim ?? '—'}</td></tr>
             <tr><td>% orçamento (fonte)</td><td>${m.tz_pct_orc ?? '—'}</td></tr>
             <tr><td>Operador</td><td>${m.tz_operador ?? '—'}</td></tr>`;
  }
  el.innerHTML = `<div><b style="font-size:15px;">${m.nome} – ${m.uf}</b> ${tzTag}${camadasTag ? ' ' + camadasTag : ''}</div>
    ${paragrafoTZ}
    <table style="margin-top:8px;">
      <tr><td>Região</td><td>${m.regiao}</td></tr>
      <tr><td>Hierarquia urbana</td><td>${m.regic_label ?? '—'}</td></tr>
      <tr><td>Arranjo metropolitano</td><td>${m.tipo_arranjo ?? '—'}${m.arranjo_nome ? ' — ' + m.arranjo_nome : ''}</td></tr>
      <tr><td>Modelo de prestação</td><td>${m.modelo_prestacao ?? 'sem dado'}</td></tr>
      <tr><td>Faixa populacional</td><td>${m.faixa_pop}</td></tr>
      <tr><td>População (2022)</td><td>${fmtNum(m.pop)}</td></tr>
      <tr><td>PIB per capita (2021)</td><td>R$ ${fmtNum(m.pib_pc)}</td></tr>
      <tr><td>Motorização (veíc/hab)</td><td>${fmtNum(m.motorizacao)}</td></tr>
      <tr><td>IBEU</td><td>${fmtNum(m.ibeu)}</td></tr>
      <tr><td>IDH</td><td>${fmtNum(m.idh)}</td></tr>
      <tr><td>Receita própria per capita</td><td>R$ ${fmtNum(m.rec_prop_pc)}</td></tr>
      <tr><td>Óbitos no trânsito /100mil (2019)</td><td>${fmtNum(m.taxa_obitos_transito)}</td></tr>
      <tr><td>Tarifa</td><td>${m.tz_status === 'Ativa' ? 'Gratuito (TZ universal)' : (m.tarifa != null ? 'R$ ' + fmtNum(m.tarifa) + ' (' + m.tarifa_ano + ', ' + m.tarifa_fonte + ')' : 'sem dado')}</td></tr>
      <tr><td>% do custo subsidiado</td><td>${m.subsidio_ntu_pct != null ? fmtNum(m.subsidio_ntu_pct) + '% (' + m.subsidio_ntu_ano + ')' : 'sem dado'}</td></tr>
      <tr><td>Plano Diretor</td><td>${m.plano_diretor ?? '—'}</td></tr>
      <tr><td>PlanMob (2025)</td><td>${m.pdmu_2025 ?? '—'}</td></tr>
      ${extra}
    </table>
    ${renderLegislacaoDetail(m)}
    ${renderModalDetail(m)}
    ${renderGruposDetail(m)}
    ${renderCamadaDetail(m)}
    ${renderFontesDetail(m)}
    ${renderNoticiasDetail(m)}`;
}

function renderModalDetail(m) {
  const d = modalFor(m);
  if (!d) return '';
  const segs = ['onibus', 'automovel', 'motocicleta', 'ativo', 'outros']
    .map(k => ({ k, v: d[k] || 0 }));
  const bar = segs.map(s => `<div class="seg" style="width:${s.v.toFixed(2)}%;background:${MODAL_STACK_COLORS[s.k]};" title="${MODAL_STACK_LABELS[s.k]}: ${s.v.toFixed(1)}%"></div>`).join('');
  const principal = segs.slice().sort((a, b) => b.v - a.v)[0];
  const ressalva = (d.t != null && d.t < 95)
    ? ` <span style="color:#e2892c;">⚠ o Censo só classifica ${d.t.toFixed(0)}% dos deslocamentos deste município; os percentuais foram normalizados para 100%.</span>`
    : '';
  return `<div style="margin-top:10px;border-top:1px dashed var(--border);padding-top:8px;">
    <b style="font-size:12.5px;">Partição modal (Censo 2022)</b>
    <div class="msbar" style="height:22px;margin-top:6px;">${bar}</div>
    <div class="mslegend" style="margin-top:6px;">${segs.map(s =>
      `<span><i style="background:${MODAL_STACK_COLORS[s.k]}"></i>${MODAL_STACK_LABELS[s.k]} ${s.v.toFixed(1)}%</span>`).join('')}</div>
    <p style="margin:6px 0 0;font-size:11.5px;color:var(--muted);line-height:1.5;">Modo principal de deslocamento para trabalho e estudo: <b>${MODAL_STACK_LABELS[principal.k]}</b> (${principal.v.toFixed(1)}%).${ressalva}</p>
  </div>`;
}

function renderGruposDetail(m) {
  const gs = gruposFor(m);
  if (!gs.length) {
    // ausencia aqui nao e prova de ausencia: o levantamento cobre 796 municipios,
    // nao os 5.570 — dizer isso e mais honesto que omitir a secao.
    return `<div style="margin-top:10px;border-top:1px dashed var(--border);padding-top:8px;">
      <b style="font-size:12.5px;">Grupos econômicos do transporte</b>
      <p style="margin:5px 0 0;font-size:12px;color:var(--muted);line-height:1.5;">Nenhum grupo mapeado neste município. O levantamento cobre 796 municípios — ausência aqui significa que não há registro, não que não haja operador.</p>
    </div>`;
  }
  const items = gs.map(g => `<li>${g[0]}</li>`).join('');
  return `<div style="margin-top:10px;border-top:1px dashed var(--border);padding-top:8px;">
    <b style="font-size:12.5px;">Grupos econômicos do transporte (${gs.length})</b>
    <ul class="grupos">${items}</ul>
  </div>`;
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
  // 11.2: o campo `ano` do crosswalk e o ano de ADOCAO da TZ naquele municipio,
  // nao o ano de publicacao — exibi-lo entre parenteses colado na citacao curta
  // ("Santini 2019 (2015)") lia-se como se fosse a data da obra. O ano de
  // publicacao ja esta na propria citacao; o de adocao ja aparece na linha
  // "Inicio TZ" da tabela acima e na coluna Inicio da lista de municipios.
  const items = fontes.map(f => `<li><b>${f.fonte}</b> — ${f.descricao || ''}${f.link ? ' — <a href="' + f.link + '" target="_blank" rel="noopener">link</a>' : ''}</li>`).join('');
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

// ---------- 3.3: TZ por região e por UF (pendente desde v0.3) ----------
// Proporção de municípios com histórico de TZ universal DENTRO de cada categoria.
// Mesma leitura do painel "% por eixo", em dois recortes territoriais que faltavam.
// O n de cada barra vai junto: uma UF com 2 municípios TZ em 20 dá 10%, e sem o n
// isso se lê como se fosse comparável a São Paulo.
function renderRegiaoUf() {
  const el = document.getElementById('regiaoUf');
  if (!el) return;
  const rows = subsetNoTz();

  const agrupa = (chave) => {
    const mapa = new Map();
    for (const m of rows) {
      const k = m[chave];
      if (k == null || k === '') continue;
      let g = mapa.get(k);
      if (!g) { g = { tot: 0, tz: 0 }; mapa.set(k, g); }
      g.tot++;
      if (m.tz_bin === 'TZ') g.tz++;
    }
    return [...mapa.entries()]
      .map(([k, g]) => ({ k, ...g, pct: 100 * g.tz / g.tot }))
      .sort((a, b) => b.pct - a.pct || b.tz - a.tz);
  };

  const bloco = (titulo, lista) => {
    if (!lista.length) return '';
    const max = Math.max(...lista.map(x => x.pct)) || 1;
    const bars = lista.map(x => `<div class="gerow" title="${x.k}: ${x.tz} de ${x.tot} municípios com TZ">
      <div class="gelab">${x.k}</div>
      <div class="getrack"><div class="gefill" style="width:${(100 * x.pct / max).toFixed(1)}%;background:var(--amarelo);"></div></div>
      <div class="geval">${x.pct.toFixed(1)}% <span style="opacity:.65;">(${x.tz}/${x.tot})</span></div>
    </div>`).join('');
    return `<div><h3 style="font-size:12.5px;margin:0 0 6px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;">${titulo}</h3><div class="gebars">${bars}</div></div>`;
  };

  const porUf = agrupa('uf');
  el.innerHTML = `<div class="ruGrid">
    ${bloco('Por região', agrupa('regiao'))}
    ${bloco(`Por UF (${porUf.length})`, porUf)}
  </div>`;
}

// ---------- 3.4: dispersão PIB per capita × motorização (pendente desde v0.3) ----------
// O painel de medianas comprime cada grupo num ponto só; a dispersão mostra a
// sobreposição real entre TZ e não-TZ — que é grande, e é justamente o que uma
// comparação de medianas esconde. Eixo X em escala log: PIB per capita é muito
// assimétrico e, em escala linear, 95% dos municípios viram uma mancha à esquerda.
function renderDispersao() {
  const svg = document.getElementById('dispersao');
  if (!svg) return;
  const rows = subsetNoTz().filter(m => m.pib_pc > 0 && m.motorizacao > 0);
  const W = 760, H = 380, ML = 56, MR = 14, MT = 14, MB = 40;
  const xs = rows.map(m => Math.log10(m.pib_pc)), ys = rows.map(m => m.motorizacao);
  if (!rows.length) { svg.innerHTML = ''; return; }
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMax = Math.min(Math.max(...ys), 2.0);   // corta a cauda extrema de motorização
  const px = v => ML + (Math.log10(v) - xMin) / (xMax - xMin || 1) * (W - ML - MR);
  const py = v => H - MB - Math.min(v, yMax) / (yMax || 1) * (H - MT - MB);

  const naoTz = [], tz = [];
  for (const m of rows) (m.tz_bin === 'TZ' ? tz : naoTz).push(m);
  const ponto = (m, cor, r, op) =>
    `<circle cx="${px(m.pib_pc).toFixed(1)}" cy="${py(m.motorizacao).toFixed(1)}" r="${r}" fill="${cor}" opacity="${op}"><title>${m.nome} – ${m.uf}\nPIB pc: R$ ${Math.round(m.pib_pc).toLocaleString('pt-BR')}\nMotorização: ${m.motorizacao.toFixed(3)}</title></circle>`;

  const ticksX = [1000, 5000, 10000, 25000, 50000, 100000, 250000].filter(v => Math.log10(v) >= xMin && Math.log10(v) <= xMax);
  const eixoX = ticksX.map(v => `<line x1="${px(v)}" y1="${MT}" x2="${px(v)}" y2="${H - MB}" stroke="var(--border)" stroke-width="1" opacity=".5"/>
    <text x="${px(v)}" y="${H - MB + 15}" fill="var(--muted)" font-size="10" text-anchor="middle">${v >= 1000 ? (v / 1000) + 'k' : v}</text>`).join('');
  const nTicksY = 4;
  const eixoY = Array.from({ length: nTicksY + 1 }, (_, i) => {
    const v = yMax * i / nTicksY;
    return `<line x1="${ML}" y1="${py(v)}" x2="${W - MR}" y2="${py(v)}" stroke="var(--border)" stroke-width="1" opacity=".5"/>
      <text x="${ML - 8}" y="${py(v) + 3}" fill="var(--muted)" font-size="10" text-anchor="end">${v.toFixed(2)}</text>`;
  }).join('');

  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.innerHTML = eixoX + eixoY +
    naoTz.map(m => ponto(m, 'var(--muted)', 1.6, .28)).join('') +
    tz.map(m => ponto(m, m.tz_status === 'Encerrada' ? 'var(--rosa)' : 'var(--amarelo)', 3.1, .95)).join('') +
    `<text x="${ML + (W - ML - MR) / 2}" y="${H - 4}" fill="var(--muted)" font-size="11" text-anchor="middle">PIB per capita (R$, escala log)</text>
     <text x="14" y="${MT + (H - MT - MB) / 2}" fill="var(--muted)" font-size="11" text-anchor="middle" transform="rotate(-90 14 ${MT + (H - MT - MB) / 2})">Motorização (veíc/hab)</text>`;

  const leg = document.getElementById('dispersaoLegenda');
  if (leg) leg.innerHTML = `<span><i style="background:var(--amarelo)"></i>TZ ativa (${tz.filter(m => m.tz_status === 'Ativa').length})</span>
    <span><i style="background:var(--rosa)"></i>TZ encerrada (${tz.filter(m => m.tz_status === 'Encerrada').length})</span>
    <span><i style="background:var(--muted)"></i>Não-TZ (${naoTz.length.toLocaleString('pt-BR')})</span>`;
}

// ---------- 11.10: concentração dos grupos econômicos (26/08/2026) ----------
// Conta alcance por ID de grupo, não por nome (ver nota em gruposFor): 20 nomes da
// base são homônimos. Responde ao recorte atual, como os demais painéis — com o
// filtro nacional, os 12 maiores são todos de ID único, então o topo do gráfico não
// muda por causa disso; a correção pega a cauda.
const GE_TOP_N = 15;

function renderGrupos() {
  const el = document.getElementById('grupos');
  if (!el) return;
  const rows = subsetNoTz();
  const alcance = new Map();   // id -> { rot, munis, tz }
  for (const m of rows) {
    for (const [rot, id] of gruposFor(m)) {
      let g = alcance.get(id);
      if (!g) { g = { rot, munis: 0, tz: 0 }; alcance.set(id, g); }
      g.munis++;
      if (m.tz_bin === 'TZ') g.tz++;
    }
  }
  const comGrupo = rows.reduce((n, m) => n + (gruposFor(m).length ? 1 : 0), 0);
  if (!alcance.size) {
    el.innerHTML = '<p class="sub">Nenhum grupo econômico mapeado no recorte atual.</p>';
    return;
  }
  const lista = [...alcance.values()].sort((a, b) => b.munis - a.munis || a.rot.localeCompare(b.rot));
  const top = lista.slice(0, GE_TOP_N);
  const max = top[0].munis;
  const bars = top.map(g => {
    const tzTxt = g.tz ? ` · ${g.tz} com TZ` : '';
    return `<div class="gerow" title="${g.rot}: ${g.munis} município(s)${tzTxt}">
      <div class="gelab">${g.rot}</div>
      <div class="getrack"><div class="gefill" style="width:${(100 * g.munis / max).toFixed(1)}%;"></div></div>
      <div class="geval">${g.munis}${tzTxt ? ` (${g.tz} TZ)` : ''}</div>
    </div>`;
  }).join('');
  const resto = lista.length - top.length;
  const plural = (n, s, p) => `${n.toLocaleString('pt-BR')} ${n === 1 ? s : p}`;
  el.innerHTML = `<p class="sub" style="margin-bottom:4px;">${plural(alcance.size, 'grupo mapeado', 'grupos mapeados')} no recorte, atuando em ${plural(comGrupo, 'município', 'municípios')}. Barras = número de municípios onde o grupo aparece; entre parênteses, quantos desses têm Tarifa Zero.</p>
    <div class="gebars">${bars}</div>
    ${resto > 0 ? `<p class="sub" style="margin-top:8px;">Mostrando os ${GE_TOP_N} de maior alcance — outros ${resto.toLocaleString('pt-BR')} grupos do recorte não aparecem no gráfico.</p>` : ''}`;
}

// ---------- referências bibliográficas ABNT ----------
// Uma lista só (decisão do autor, 26/08/2026 — item 11.3): cobre TODAS as citações
// curtas que aparecem na coluna "Fontes" da tabela e no card do município, e nada
// além delas. A lista anterior tinha 5 entradas para 15 citações em uso (regressão
// da rodada v0.5, item 11.14) e uma segunda lista de "referências adicionais"
// que expunha notas internas de trabalho ao leitor ("a conferir antes de citar",
// "possível duplicata") e fontes de dado que não são bibliografia de TZ (CEM,
// IBGE/MUNIC). Essas notas saíram do painel e viraram pendência no ROADMAP (11.13).
//
// Citekeys conferidos em biblioteca.bib (05 - Referências/_zotero) onde existem:
// santini2019, angelo2023, vermander2021, brinco2018 (citação curta mantida como
// "brinco 2017", ano do artigo na FEE, por já estar em uso no crosswalk).
const REFERENCIAS_ABNT = [
  { chave: 'Angelo 2023', ref: 'ANGELO, Danielle Andrade. <i>Tarifa Zero</i>: formas de financiamento e experiências nacionais. 2023. Trabalho de Conclusão de Curso (Graduação em Planejamento Territorial) – Universidade Federal do ABC, São Bernardo do Campo, 2023.' },
  { chave: 'brinco 2017', ref: 'BRINCO, Ricardo. Tarifação e gratuidade no transporte público urbano. <i>Indicadores Econômicos FEE</i>, Porto Alegre, v. 45, n. 2, p. 79-96, 2017.' },
  { chave: 'Campos et al. 2023', ref: 'CAMPOS, Júlia Pereira <i>et al.</i> Avaliação da qualidade do transporte público de Mariana (MG) com a implantação da política tarifa zero: uma comparação entre a perspectiva do usuário e a técnica. In: CONGRESSO DE PESQUISA E ENSINO EM TRANSPORTES, 37., 2023, Santos. <i>Anais</i>. Santos: ANPET, 2023.' },
  { chave: 'Costa & Sampaio 2024', ref: 'COSTA, Matheus Gregorini; SAMPAIO, Joelson Oliveira Ubida. Análise da viabilidade financeira da implementação da política de tarifa zero no transporte público urbano por ônibus em grandes municípios brasileiros. <i>Revista Delos</i>, v. 17, n. 61, p. e2597, 8 nov. 2024.' },
  { chave: 'Gomes et al. 2023', ref: 'GOMES, Thiago Von Zeidler; BAIARDI, Yara Cristina Labronici; ZIONI, Silvana. Caminhos para uma nova gestão e financiamento do Transporte Público Coletivo: experiências de Tarifa Zero na macrometrópole paulista. <i>Journal of Sustainable Urban Mobility</i>, v. 3, n. 1, p. 96-110, mar. 2023.' },
  { chave: 'Gonçalves & Santini 2023', ref: 'GONÇALVES, Cristiane Costa; SANTINI, Daniel. Tarifa Zero, segregação e desigualdade social: um estudo de caso sobre a experiência de Mariana (MG). <i>Journal of Sustainable Urban Mobility</i>, v. 3, n. 1, p. 111-121, 20 mar. 2023.' },
  { chave: 'Landin 2022', ref: 'LANDIN, Lucas de Paula. <i>Tarifa Zero</i>: la financiación del transporte público gratuito en el Municipio de Vargem Grande Paulista. 2022. Dissertação (Mestrado) – Universidad de Chile, Santiago, 2022.' },
  { chave: 'Lima & Kraus Junior 2021', ref: 'LIMA, Lucas Franco; KRAUS JUNIOR, Werner. Experiências de transporte público por passe livre. In: CONGRESSO DE PESQUISA E ENSINO EM TRANSPORTES, 35., 2021. <i>Anais</i>. [<i>S. l.</i>]: ANPET, 2021.' },
  { chave: 'Lopes & Muniz 2021', ref: 'LOPES, Neiva Aparecida Pereira; MUNIZ, R. M. Transporte público gratuito ou tarifa zero em Monte Carmelo/MG? <i>Revista de Gestão Pública</i>, 2021.' },
  { chave: 'Pereira 2023', ref: 'PEREIRA, Thais Fernandes. As capacidades estatais das cidades brasileiras com tarifa zero no transporte público. In: SEMINÁRIO DISCENTE DA PÓS-GRADUAÇÃO EM CIÊNCIA POLÍTICA DA USP, 13., 2023, São Paulo. <i>Anais eletrônicos</i> [...]. São Paulo: USP, 2023.' },
  { chave: 'Pereira 2024', ref: 'PEREIRA, Thais Fernandes. <i>A política de isenção de tarifa no transporte público</i>: uma análise política dos casos brasileiros. 2024. Dissertação (Mestrado) – Universidade de São Paulo, São Paulo, 2024.' },
  { chave: 'Santini 2019', ref: 'SANTINI, Daniel <i>et al.</i> <i>Passe livre</i>: as possibilidades da tarifa zero contra a distopia da uberização. São Paulo: Autonomia Literária: Fundação Rosa Luxemburgo, 2019.' },
  { chave: 'Santini 2023', ref: 'SANTINI, Daniel. <i>Tarifa Zero e desigualdade social</i>: um estudo de caso sobre a experiência de Mariana (MG). 2023. Dissertação (Mestrado) – Universidade de São Paulo, São Paulo, 2023.' },
  { chave: 'Santini et al. 2024', ref: 'SANTINI, Daniel <i>et al.</i> A experiência de Tarifa Zero no transporte público de São Caetano do Sul. In: CONGRESSO DE PESQUISA E ENSINO EM TRANSPORTES, 38., 2024, Florianópolis. <i>Anais</i>. Florianópolis: ANPET, 2024.' },
  { chave: 'Vermander 2021', ref: 'VERMANDER, Marijke. <i>Exploring fare-free public transport in Brazil</i>: rationales and characteristics of Tarifa Zero policies in small Brazilian municipalities. 2021. Dissertação (Mestrado) – Vrije Universiteit Brussel, Bruxelas, 2021.' },
];

// Confere, em tempo de carga, que toda citação exibida tem referência completa —
// a regressão de v0.5 (15 citações, 5 referências) passou justamente por não
// haver essa checagem. Falha barulhenta no console em vez de silenciosa na tela.
function auditarReferencias() {
  const comRef = new Set(REFERENCIAS_ABNT.map(r => r.chave));
  const citadas = new Set(FONTES_FLAT.filter(f => f.tipo === 'Estudo acadêmico').map(f => f.fonte));
  const semRef = [...citadas].filter(c => !comRef.has(c));
  const semUso = [...comRef].filter(c => !citadas.has(c));
  if (semRef.length) console.error('[painel] citações sem referência ABNT:', semRef);
  if (semUso.length) console.warn('[painel] referências ABNT sem citação correspondente:', semUso);
  return { semRef, semUso };
}

function renderReferenciasAbnt() {
  const el = document.getElementById('referenciasAbnt');
  if (!el) return;
  const { semRef } = auditarReferencias();
  let html = '<ol class="refs">' + REFERENCIAS_ABNT.map(r => `<li>${r.ref}</li>`).join('') + '</ol>';
  if (semRef.length) {
    html += `<p class="sub" style="color:var(--rosa);margin-top:10px;">⚠ ${semRef.length} citação(ões) sem referência completa nesta lista: ${semRef.join(', ')}. Pendência de bibliografia — ver ROADMAP.</p>`;
  }
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
      const list = fontesFor(r).map(f => `<li><b>${f.fonte}</b> — ${f.descricao || ''}${f.link ? ' — <a href="' + f.link + '" target="_blank" rel="noopener">link</a>' : ''}</li>`).join('');
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
  render(); renderTZTable(); atualizaBotaoLimpar();
  if (state.uf) zoomToUF(state.uf); else resetZoom();
});
document.getElementById('faixaFilter').addEventListener('change', e => { state.faixa = e.target.value; render(); renderTZTable(); atualizaBotaoLimpar(); });
document.getElementById('regicFilter').addEventListener('change', e => { state.regic = e.target.value; render(); renderTZTable(); atualizaBotaoLimpar(); });
document.getElementById('modeloFilter').addEventListener('change', e => { state.modelo = e.target.value; render(); atualizaBotaoLimpar(); });
document.getElementById('tzFilter').addEventListener('change', e => { state.tzFilter = e.target.value; render(); atualizaBotaoLimpar(); });
document.getElementById('camadaFilter').addEventListener('change', e => { state.camada = e.target.value; render(); renderTZTable(); atualizaBotaoLimpar(); });

// ---------- 11.5: busca de município (cobre os 5.570, não só os TZ) ----------
// Antes, chegar num município só era possível clicando no mapa ou na tabela de TZ —
// os 5.401 não-TZ ficavam acessíveis apenas pelo mapa, o que num município pequeno
// significa acertar alguns pixels. O datalist é preenchido sob demanda (no máximo
// 40 sugestões por digitação) em vez de despejar 5.570 <option> no DOM de uma vez.
const MUNI_BUSCA = [...MUNI.values()].map(m => ({ m, rot: `${m.nome} – ${m.uf}` }));
const MUNI_POR_ROTULO = new Map(MUNI_BUSCA.map(x => [x.rot, x.m]));

function normBusca(s) {
  return (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
}

const inputBusca = document.getElementById('muniSearch');
const listaBusca = document.getElementById('muniList');

function atualizaSugestoes() {
  const q = normBusca(inputBusca.value);
  if (q.length < 2) { listaBusca.innerHTML = ''; return; }
  const hits = [];
  for (const x of MUNI_BUSCA) {
    if (normBusca(x.rot).includes(q)) { hits.push(x.rot); if (hits.length >= 40) break; }
  }
  listaBusca.innerHTML = hits.map(r => `<option value="${r}"></option>`).join('');
}

function selecionaMunicipioBuscado() {
  const m = MUNI_POR_ROTULO.get(inputBusca.value.trim());
  if (!m) return false;
  renderDetail(m);
  const f = features.find(ft => ft.id === String(m.id));
  if (f) zoomToMuni(f);
  atualizaBotaoLimpar();
  return true;
}

if (inputBusca) {
  inputBusca.addEventListener('input', () => { atualizaSugestoes(); selecionaMunicipioBuscado(); });
  inputBusca.addEventListener('change', selecionaMunicipioBuscado);
  inputBusca.addEventListener('keydown', e => { if (e.key === 'Enter') selecionaMunicipioBuscado(); });
}

// ---------- 11.4: limpar tudo ----------
// O `↺ Brasil` que já existia reseta só o enquadramento do mapa; os filtros
// continuavam aplicados, o que deixava o painel num estado que parecia "inteiro"
// mas não era. Este zera filtros + busca + seleção + enquadramento de uma vez.
const btnLimpar = document.getElementById('clearAll');

function algumFiltroAtivo() {
  return !!(state.uf || state.faixa || state.regic || state.arranjo || state.modelo ||
            state.tzFilter || state.camada || (inputBusca && inputBusca.value.trim()));
}

function atualizaBotaoLimpar() {
  if (btnLimpar) btnLimpar.disabled = !algumFiltroAtivo();
}

function limparTudo() {
  state.uf = ''; state.faixa = ''; state.regic = ''; state.arranjo = '';
  state.modelo = ''; state.tzFilter = ''; state.camada = '';
  for (const id of ['ufFilter', 'faixaFilter', 'regicFilter', 'modeloFilter', 'tzFilter', 'camadaFilter']) {
    const el = document.getElementById(id);
    if (el) el.value = '';
  }
  if (inputBusca) { inputBusca.value = ''; listaBusca.innerHTML = ''; }
  renderDetail(null);
  resetZoom();
  render(); renderTZTable();
  atualizaBotaoLimpar();
}

if (btnLimpar) btnLimpar.addEventListener('click', limparTudo);

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
atualizaBotaoLimpar();
renderCrosstabs();
renderModalStack();
renderReferenciasAbnt();
renderTZTable();
render(); // desenha mapa, legenda, barras, cards, linha do tempo e score de população
