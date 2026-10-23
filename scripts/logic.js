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
// 23/10/2026: o bloco data-grupos deixou de ser embutido no Painel Brasil (a análise
// de grupos vai para a Rede de empresas). Sem isto, os nomes dos grupos por município
// continuariam publicados no código-fonte da página, só que invisíveis.
const GRUPOS_RAW = JSON.parse(document.getElementById('data-grupos')?.textContent || '{}');
const LEGISLACAO_RAW = JSON.parse(document.getElementById('data-legislacao').textContent);
const ARRANJO_RAW = JSON.parse(document.getElementById('data-arranjo').textContent);
const CURVA_PORTE = JSON.parse(document.getElementById('data-curva').textContent);
const FICHAS = JSON.parse(document.getElementById('data-fichas').textContent);
const REMUN = JSON.parse(document.getElementById('data-remun').textContent);
const CUSTEIO = JSON.parse(document.getElementById('data-custeio').textContent);
// Matriz origem-destino de trabalho do Censo 2022 (v0.8), mesma chave de código IBGE.
// Vem SUPRIMIDA: top-5 destinos (e top-5 origens) por município e no mínimo 5 registros
// amostrados por célula — 57,6% dos 120 mil pares do microdado se apoiam em UMA pessoa
// amostrada, e essas células não são publicáveis nem por custódia (o microdado é de
// acesso controlado) nem por ruído (CV da ordem de 100%). Ver build_od.py e METADADOS.md.
// Formato: { cod: { s:[[cod_destino, pessoas, rel]], st: total_que_sai, sd: n_destinos,
//                   e:[[cod_origem, pessoas, rel]], et: total_que_entra, eo: n_origens } }
// rel: 0 = fora do arranjo · 1 = mesmo arranjo · 2 = polo do próprio arranjo.
// O percentual NÃO vem no arquivo — é pessoas/total, calculado aqui, para não haver
// duas versões do mesmo número.
const OD_RAW = JSON.parse(document.getElementById('data-od').textContent);

// zip columnar municipal data into id -> row object
const COLS = MUNI_COL.cols;
const MUNI = new Map();
for (const row of MUNI_COL.data) {
  const obj = {};
  for (let i = 0; i < COLS.length; i++) obj[COLS[i]] = row[i];
  obj.rec_prop_pc = (obj.rec_prop != null && obj.pop) ? obj.rec_prop / obj.pop : null;
  obj.tz_bin = (obj.tz_status === 'Ativa' || obj.tz_status === 'Encerrada') ? 'TZ' : 'Não TZ';
  obj.tz_ano_num = obj.tz_ano != null ? parseInt(String(obj.tz_ano).slice(0, 4)) : null;
  if (Number.isNaN(obj.tz_ano_num)) obj.tz_ano_num = null;
  // tz_ano_txt: o que se pode escrever numa frase. Ano de 4 dígitos quando a
  // base traz um; null quando o campo é uma anotação de pendência ("a apurar",
  // "[A CONFIRMAR]", "não apurado") em vez de uma data.
  obj.tz_ano_txt = obj.tz_ano_num ? String(obj.tz_ano_num) : null;
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
// A camada 2 da régua descritiva (2a grupo social, 2b espaço, 2c dias, 2d eventos, 2e
// finalidade), gerada por build_camadas.py da planilha canônica da régua. Um município
// pode acumular mais de um subtipo ao mesmo tempo (Belo Horizonte e Brasília), e por isso
// a soma por subtipo passa do número de municípios — é regra da régua, não erro de conta.
// Fica FORA de propósito a gratuidade eleitoral: desde 2024 ela é obrigação do poder
// público por decisão do STF, integra o PISO da régua e não forma camada nem distingue
// casos; contá-la inflaria o número e mudaria o sentido do que está sendo medido.
// Leia-se esta contagem como PISO, e não estimativa: a busca dos arranjos parciais não foi
// exaustiva — sobretudo no 2e, com quatro casos registrados — e encontra mais facilmente os
// programas das cidades grandes. Comparar 174 universais com 43 parciais como se fossem
// medidas do mesmo tipo é erro de leitura.
// 23/10/2026 — a chave passou de "Município|UF" para código IBGE, como nos demais
// crosswalks. O motivo está no build_camadas.py: a planilha da régua grafa "Embu das
// Artes" e a base do painel grafa "Embu" (3515004), e normKey() só reconcilia acento
// e caixa, não nomes diferentes — a camada 2c do município ficou invisível de v0.11
// até aqui. Com o código, ou casa ou o build falha; não há como sumir em silêncio.
function camadasFor(m) { return (m && CAMADAS_RAW[String(m.id)]) || []; }

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
// 173 municípios verificados, 108 com norma localizada e 64 com busca feita sem resultado
// (flag `buscada`). Campos decompostos em tipo/numero/ano/data por build_legislacao_padrao.py.
// O levantamento de origem é anterior à
// ampliação do universo canônico (03/08/2026), então 33 dos 169 municípios TZ de
// hoje não estavam nele — o card diz isso em vez de deixar o silêncio sugerir que
// não há norma.
function legislacaoFor(m) { return (m && LEGISLACAO_RAW[String(m.id)]) || null; }

// ---------- 12.4: o arranjo contratual (Cap. 5.6 da tese) ----------
// O painel mostrava `tz_operador` — o NOME de quem opera — e nada sobre o contrato.
// A tese usa um capítulo inteiro para mostrar que a diferença decisiva não é quem
// opera, e sim o que foi contratado: uma prefeitura com frota própria e uma
// concessionária que recebeu a gratuidade por termo aditivo apareciam aqui como a
// mesma coisa. Fica FORA, por decisão do autor de 23/10/2026, tudo que é régua
// ANALÍTICA (destinatário em quatro categorias, contrapartida, posição no plano):
// isto é a descrição contratual da Parte 2, não a leitura crítica do Capítulo 7.
function arranjoFor(m) { return (m && ARRANJO_RAW[String(m.id)]) || null; }
const PROVA_ROT = { alta: ['#8FBF6A', 'prova alta'], media: ['#D9CE12', 'prova média'], baixa: ['#E2892C', 'prova baixa'] };
function odFor(m) { return (m && OD_RAW[String(m.id)]) || null; }

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
      <p style="margin:5px 0 0;font-size:12px;color:var(--muted);line-height:1.5;">Não verificado. O levantamento legal cobre 173 municípios (consolidação de 18/09/2026) — este caso entrou no universo depois e ainda não passou pela busca de norma.</p>
    </div>`;
  }
  const linhas = [];
  if (L.norma) {
    // Exibicao padronizada (18/09/2026): sempre "Tipo no NUMERO/ANO", venha a origem
    // como vier. A data completa e a grafia de citacao ficam no tooltip; o link, quando
    // existe, abre o texto da norma. Os campos vem decompostos de build_legislacao_padrao.py.
    let titulo = L.norma_ext || L.norma;
    if (L.conf_nota) titulo += ` — ${L.conf_nota}`;
    const conf = L.conf
      ? ` <span class="tag ${L.conf === 'alta' ? 'ativa' : 'parcial'}" title="${CONF_LABEL[L.conf] || ''}">${L.conf}</span>`
      : '';
    // o azul de link da paleta (#1A54C7) nao tem contraste suficiente sobre o fundo
    // escuro do painel: a norma fica na cor do texto e o link se anuncia pelo sublinhado.
    const rotulo = L.link
      ? `<a href="${L.link}" target="_blank" rel="noopener" title="${titulo}"
           style="color:var(--text);text-decoration:underline;text-decoration-color:var(--amarelo);text-underline-offset:3px;">${L.norma}</a>`
      : `<span title="${titulo}">${L.norma}</span>`;
    linhas.push(`<div style="font-size:12.5px;color:var(--text);margin-top:4px;"><b>${rotulo}</b>${conf}</div>`);
    if (L.extra) linhas.push(`<div style="font-size:11.5px;color:var(--muted);margin-top:2px;">Também citada: ${L.extra}</div>`);
  } else if (L.buscada) {
    linhas.push('<div style="font-size:12px;color:var(--muted);margin-top:4px;">Norma procurada e <b>não localizada</b> em fonte pública — a gratuidade costuma ter sido implantada por via administrativa (licitação deserta, contrato de concessão) ou por decreto não divulgado. A ausência aqui é resultado de busca, não lacuna de levantamento.</div>');
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
// Numeração vigente da régua (renumerada no cofre em 13/09/2026, propagada em 20/09).
// ATENÇÃO ao ler versões antigas do painel: até a v0.10 estes mesmos códigos tinham
// outro sentido — '2a' era temporal-dias, que hoje é '2c'. Os rótulos abaixo seguem
// `Regras de classificacao das reguas` do cofre.
const CAMADA_LABELS = {
  '2a': 'Grupo social',
  '2b': 'Espacial (periférica)',
  '2c': 'Temporal (dias)',
  '2d': 'Temporal (eventos)',
  '2e': 'Finalidade (estudo, saúde)',
};

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
// Grupo das linhas de desejo (v0.8). Criado por último para ficar acima de todas as
// camadas de município e dos limites de UF — linha de fluxo por baixo do preenchimento
// desaparece nos municípios grandes.
const gFluxo = document.createElementNS('http://www.w3.org/2000/svg', 'g');
gFluxo.setAttribute('pointer-events', 'none');

// Centroide por município, sob demanda. Usa o centro do bbox, não o centroide de área:
// na escala nacional a diferença é de poucos pixels, e o bbox já está calculado. Em
// município de forma muito irregular o ponto pode cair fora do polígono — é limitação
// aceita de propósito, porque a linha serve para indicar direção e intensidade, não
// para localizar um endereço.
const centroideCache = new Map();
function centroideDe(cod) {
  if (centroideCache.has(cod)) return centroideCache.get(cod);
  const f = features.find(ft => ft.id === String(cod));
  const p = f ? project([(f.bbox[0] + f.bbox[2]) / 2, (f.bbox[1] + f.bbox[3]) / 2]) : null;
  centroideCache.set(cod, p);
  return p;
}

svg.appendChild(gNaoTz);
svg.appendChild(gAtiva);
svg.appendChild(gParcial);
svg.appendChild(gEncerrada);
svg.appendChild(gUf);
svg.appendChild(gFluxo);

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
  cadunico_cobertura: ['#edf8b1', '#c7e9b4', '#7fcdbb', '#2c7fb8', '#253494'],
  trab_fora: ['#fde0dd', '#fa9fb5', '#f768a1', '#c51b8a', '#7a0177'],
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
  renderRegua();
  renderArranjoPanel();
  renderRemunPanel();
  // renderGrupos() saiu do ciclo em 23/10/2026: a análise de grupos econômicos passa
  // para a página Rede de empresas (decisão do autor). A lista de grupos no card do
  // município (renderGruposDetail) continua.
  renderCrosstabs();
  renderModalStack();
  renderRecorte();
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
    html = `<span><span class="sw" style="background:${TZ_COLORS_HEX.Ativa}"></span>TZ universal</span>
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
    { n: ativas.length.toLocaleString('pt-BR'), l: `TZ <b>universal</b> em vigor ${scopeLabel}`, w: warn },
    { n: countParciais(rows).toLocaleString('pt-BR'), l: `TZ <b>parciais</b> ${scopeLabel} (dias, bairros ou grupo social — fora da universal; não conta as 324 gratuidades eleitorais/eventuais)` },
    { n: (rows.length ? (100 * tzRows.length / rows.length) : 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + '%', l: `dos ${rows.length.toLocaleString('pt-BR')} municípios ${scopeLabel === 'no Brasil' ? 'do Brasil' : 'do recorte'} têm ou tiveram TZ universal (${tzRows.length.toLocaleString('pt-BR')})`, w: warn },
    { n: fmtCompact(popTZ), l: `Pessoas vivendo com TZ universal ${scopeLabel} (soma da população, Censo 2022)`, w: warn },
  ];
  document.getElementById('cards').innerHTML = cards.map(c =>
    `<div class="card"><div class="n">${c.n}</div><div class="l">${c.l}${c.w || ''}</div></div>`).join('');
  // Como os números se relacionam (24/10/2026, parecer externo): os 187 da base verificada e
  // os 44 parciais da régua não são o mesmo universo — e o leitor precisava cruzar abas para saber.
  const conta = st => rows.filter(m => m.tz_status === st).length;
  const nUni = conta('Ativa'), nPar = conta('Parcial (ativa)'), nEnc = conta('Encerrada');
  const nReg = rows.filter(m => /Regulamentada/.test(m.tz_status || '')).length, nPis = rows.filter(m => /Pista/.test(m.tz_status || '')).length;
  const n44 = countParciais(rows), nExtra = Math.max(0, n44 - nPar);
  const rel = document.getElementById('relUniversos');
  const pl = (n, um, varios) => `${n.toLocaleString('pt-BR')} ${n === 1 ? um : varios}`;
  const partes = [[nUni, 'universal', 'universais'], [nPar, 'parcial', 'parciais'], [nEnc, 'encerrada', 'encerradas']].filter(([n]) => n).map(([n, a, b]) => pl(n, a, b));
  const lista = partes.length > 1 ? partes.slice(0, -1).join(', ') + ' e ' + partes.at(-1) : (partes[0] || 'nenhuma');
  const base = nUni + nPar + nEnc;
  let txt = `<b>Como os números se relacionam${hasFilter ? ' no recorte' : ''}.</b> A base verificada da pesquisa — cada política conferida na norma, no contrato ou na prova de operação — tem <b>${pl(base, 'política', 'políticas')}</b>${base ? ': ' + lista : ''}. `;
  if (!n44) txt += 'Não há casos parciais da régua neste recorte.';
  else if (!nPar) txt += `${n44 === 1 ? 'O <b>caso parcial</b> da régua vem' : `Os <b>${n44} casos parciais</b> da régua vêm`} da busca exploratória da camada 2, que não é exaustiva e não entra na base verificada.`;
  else if (!nExtra) txt += `Os <b>${n44} casos parciais</b> da régua são os ${nPar} da base verificada.`;
  else txt += `Os <b>${n44} casos parciais</b> da régua são ${nPar === 1 ? 'esse' : `esses ${nPar}`} e mais <b>${pl(nExtra, 'município achado', 'municípios achados')}</b> na busca exploratória da camada 2, que não é exaustiva e não entra na base verificada.`;
  const fora = [nReg && pl(nReg, 'política regulamentada e não implantada', 'políticas regulamentadas e não implantadas'), nPis && pl(nPis, 'pista a verificar', 'pistas a verificar')].filter(Boolean);
  if (fora.length) txt += ` Ficam fora das duas contagens ${fora.join(' e ')}.`;
  if (rel) rel.innerHTML = txt;
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
    const desde = m.tz_ano_txt ? `desde ${m.tz_ano_txt}` : 'desde uma data ainda não determinada nesta pesquisa';
    const operador = m.tz_operador ? ` A operação é feita por ${m.tz_operador}.` : '';
    // 23/10/2026 — até aqui esta frase dizia "gratuito para qualquer usuário, todos os
    // dias" para TODA a camada 1, inclusive para os 9 casos de residência (1c). Em São
    // Caetano do Sul, que desde 15/07/2026 cobra R$ 5,00 do não residente, o painel
    // afirmava o contrário do que a tese documenta. A régua classifica os quatro
    // subtipos pelo PORTÃO DE ACESSO, e é o portão que a prosa precisa dizer.
    const PORTAO = {
      '1a': 'todo o transporte coletivo municipal é gratuito para qualquer usuário, todos os dias: <b>não há portão de acesso</b>',
      '1b': 'a gratuidade exige um <b>cadastro prévio</b>, mas aberto a qualquer usuário — é um portão de procedimento, que não decide quem pode viajar, e por isso o caso segue universal',
      '1c': 'a gratuidade é <b>de quem mora no município</b>; quem vem de fora paga. Pela régua, a residência delimita o território da universalidade e não focaliza por renda nem por grupo social, e por isso o caso continua na camada universal (Kębłowski, 2020) — num tecido urbano contínuo, porém, esse portão separa vizinhos que usam o mesmo sistema',
      '1d': 'a norma <b>declara um prazo de vigência</b>; enquanto o termo não chega, o desenho é universal',
    };
    const comoE = PORTAO[m.tz_regua_sub]
      || 'o desenho é universal pela régua desta pesquisa, e o subtipo (o portão de acesso, se houver) ainda não foi apurado';
    return `${nomeUf} tem <b>Tarifa Zero universal</b> ${desde}: ${comoE}.${operador} Isso corresponde aos ${fmtCompact(m.pop)} habitantes do município (Censo 2022), sujeitos aos gaps de estimativa já registrados no painel (ver Score de população).`;
  }
  if (m.tz_status === 'Encerrada') {
    const periodo = (m.tz_ano_txt && m.tz_fim) ? `entre ${m.tz_ano_txt} e ${m.tz_fim}`
      : (m.tz_ano_txt ? `a partir de ${m.tz_ano_txt}` : 'em um período não totalmente determinado nesta pesquisa');
    return `${nomeUf} teve <b>Tarifa Zero universal</b> ${periodo}, mas a política foi <b>encerrada</b> e não está mais em vigor hoje. Entra na pesquisa como caso de reversão/trajetória, não como TZ ativa — não contar entre os municípios com gratuidade vigente.`;
  }
  // Status criados na base-mestre em out/2026. Sem tratamento próprio os dois caíam
  // no texto genérico de fechamento ("nenhuma política mapeada"), que é falso
  // justamente aqui: num caso há lei aprovada, no outro há pista aberta.
  if (m.tz_status === 'Parcial (ativa)') {
    const cs = camadasFor(m).map(c => (CAMADA_LABELS[c.camada] || c.camada).toLowerCase());
    const quais = cs.length ? ` — ${cs.join('; ')}` : '';
    return `${nomeUf} tem <b>gratuidade ativa, mas parcial</b>${quais}: há portão de acesso (de dia, de lugar, de grupo ou de finalidade), então o caso não entra na contagem de Tarifa Zero <i>universal</i> desta pesquisa. Entra na régua descritiva, que é onde os desenhos parciais são comparados.`;
  }
  if (m.tz_status === 'Regulamentada — não implantada') {
    return `${nomeUf} <b>tem norma de gratuidade aprovada, mas a operação gratuita ainda não começou</b>. Não entra na contagem de municípios com Tarifa Zero — entra quando houver início de operação comprovado. É um caso a acompanhar, não um caso de ausência de política.`;
  }
  if (m.tz_status === 'Pista (a verificar)') {
    return `${nomeUf} é uma <b>pista em aberto</b>: há indício de gratuidade em alguma fonte, mas sem prova de operação que sustente a entrada no universo da pesquisa. Não conta como Tarifa Zero e também não é uma negativa — volta ao escopo se aparecer prova de operação.`;
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
  // Não reconstruir o card quando o município já é o que está na tela. A busca
  // chama isto a cada tecla e a cada blur do campo, e reescrever o innerHTML
  // destrói elementos interativos no meio de um clique do usuário (foi assim que
  // o botão "ver no mapa" ficava inerte — ver a nota em trocaDirecaoFluxo).
  if (m && munSelecionado && String(munSelecionado.id) === String(m.id)) return;
  munSelecionado = m || null;
  if (!m) {
    el.innerHTML = '<div class="empty">Clique em um município no mapa ou na lista abaixo.</div>';
    desenharFluxos(null);
    return;
  }
  const TAG_STATUS = {
    'Ativa': ['ativa', 'TZ ativa'],
    'Encerrada': ['encerrada', 'TZ encerrada'],
    'Regulamentada — não implantada': ['aguardando', 'Lei aprovada, sem operação'],
    'Pista (a verificar)': ['pista', 'Pista a verificar'],
    'Parcial (ativa)': ['parcial', 'Gratuidade parcial'],
  };
  const tagSpec = TAG_STATUS[m.tz_status]
    || (typeof m.tz_status === 'string' && m.tz_status.startsWith('Excluída') ? ['fora', 'Fora de escopo'] : null);
  const tzTag = tagSpec ? `<span class="tag ${tagSpec[0]}">${tagSpec[1]}</span>` : '';
  // 11.7: a camada da regua descritiva era uma lista no fim do card, depois de ~16
  // linhas de tabela. Sobe para tag ao lado do status de TZ; o detalhe (ressalvas,
  // pop. estimada, flags) continua embaixo, em renderCamadaDetail().
  const camadasTag = camadasFor(m).map(c =>
    `<span class="tag parcial" title="Camada ${c.camada} da régua descritiva${c.detalhe ? ' — ' + c.detalhe : ''}">${CAMADA_LABELS[c.camada] || c.camada}${c.flag ? ' ⚠' : ''}</span>`
  ).join(' ');
  // 23/10/2026 (item 12.2): o card mostrava a camada só dos casos parciais — quem é
  // universal não via subtipo nenhum, embora a régua da tese separe 1a a 1d. Entra a
  // tag do subtipo e, com ela, a FORÇA DA PROVA: 31 políticas da camada 1 têm o subtipo
  // classificado pela hipótese de um pedido de acesso à informação ainda sem resposta,
  // e a tese marca essa classificação como provisória. Exibi-las iguais às demais era
  // afirmar mais do que a pesquisa sustenta.
  const subInfo = (m.tz_bin === 'TZ' && m.tz_regua_sub && REGUA_IDX[m.tz_regua_sub] != null)
    ? REGUA[REGUA_IDX[m.tz_regua_sub]] : null;
  const subTag = subInfo
    ? `<span class="tag parcial" style="background:${subInfo.cor};color:rgba(0,0,0,.78);" title="Subtipo ${subInfo.k} da régua descritiva — ${subInfo.desc}">${subInfo.k} ${subInfo.rot}${m.tz_prov ? ' ◇' : ''}</span>`
    : '';
  const avisoProvisorio = m.tz_prov
    ? `<p style="margin:6px 0 0;font-size:11.5px;line-height:1.5;color:var(--muted);">◇ <b>Classificação provisória.</b> O subtipo deste caso é a <b>hipótese</b> que um pedido de acesso à informação ainda sem resposta testa — a resposta pode trocá-lo. São 31 casos assim na camada 1, e a contagem pode mudar à medida que os pedidos forem respondidos.${m.tz_prov_txt ? ` <span style="color:var(--muted);">Hipótese registrada na base: ${String(m.tz_prov_txt).slice(0, 220)}</span>` : ''}</p>`
    : '';
  const incoerente = m.tz_status === 'Ativa' && m.tz_fim != null;
  const avisoIncoerencia = incoerente
    ? `<p style="margin:6px 0 0;font-size:11.5px;line-height:1.5;color:#e2892c;">⚠ A base-mestre traz este caso como <b>Ativa</b> e ao mesmo tempo com data de <b>fim</b> preenchida (${m.tz_fim}). O painel exibe os dois campos como estão, sem escolher um — conflito a resolver na fonte.</p>`
    : '';
  const paragrafoTZ = `<p style="margin:8px 0 0;font-size:12.5px;line-height:1.55;color:var(--text);">${gerarParagrafoTZ(m)}</p>${avisoIncoerencia}${avisoProvisorio}`;
  let extra = '';
  if (m.tz_bin === 'TZ') {
    extra = `<tr><td>Início TZ</td><td>${m.tz_ano ?? '—'}${(m.tz_ano != null && m.tz_ano_txt == null) ? ' <span style="color:var(--muted);font-size:11px;">(anotação da base, não um ano)</span>' : ''}</td></tr>
             <tr><td>Fim TZ</td><td>${m.tz_fim ?? '—'}</td></tr>
             <tr><td>% orçamento (fonte)</td><td>${m.tz_pct_orc ?? '—'}</td></tr>
             <tr><td>Operador</td><td>${m.tz_operador ?? '—'}</td></tr>`;
  }
  el.innerHTML = `<div><b style="font-size:15px;">${m.nome} – ${m.uf}</b> ${tzTag}${subTag ? ' ' + subTag : ''}${camadasTag ? ' ' + camadasTag : ''}</div>
    ${paragrafoTZ}
    ${fichaFor(m) ? '<button class="btn-ficha" type="button">Abrir a ficha da tese →</button>' : ''}
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
      <tr><td>Cobertura do CadÚnico (ago/2025)</td><td>${m.cadunico_cobertura != null ? fmtNum(m.cadunico_cobertura) + '% (' + fmtNum(m.cadunico_pes) + ' pessoas)' : 'sem dado'}</td></tr>
      <tr><td>Cobertura do CadÚnico (set/2022)</td><td>${m.cadunico_cobertura_2022 != null ? fmtNum(m.cadunico_cobertura_2022) + '%' : 'sem dado'}</td></tr>
      <tr><td>Cadastro atualizado (ago/2025)</td><td>${m.cadunico_taxa_atualizacao != null ? fmtNum(m.cadunico_taxa_atualizacao) + '% das famílias' : 'sem dado'}</td></tr>
      <tr><td>Receita própria per capita</td><td>R$ ${fmtNum(m.rec_prop_pc)}</td></tr>
      <tr><td>Óbitos no trânsito /100mil (2019)</td><td>${fmtNum(m.taxa_obitos_transito)}</td></tr>
      <tr><td>Tarifa</td><td>${m.tz_status === 'Ativa' ? 'Gratuito (TZ universal)' : (m.tarifa != null ? 'R$ ' + fmtNum(m.tarifa) + ' (' + m.tarifa_ano + ', ' + m.tarifa_fonte + ')' : 'sem dado')}</td></tr>
      <tr><td>% do custo subsidiado</td><td>${m.subsidio_ntu_pct != null ? fmtNum(m.subsidio_ntu_pct) + '% (' + m.subsidio_ntu_ano + ')' : 'sem dado'}</td></tr>
      <tr><td>Plano Diretor</td><td>${m.plano_diretor ?? '—'}</td></tr>
      <tr><td>PlanMob (2025)</td><td>${m.pdmu_2025 ?? '—'}</td></tr>
      ${extra}
    </table>
    ${renderLegislacaoDetail(m)}
    ${renderODDetail(m)}
    ${renderModalDetail(m)}
    ${renderArranjoDetail(m)}
    ${renderCamadaDetail(m)}
    ${renderFontesDetail(m)}
    ${renderNoticiasDetail(m)}
    <p class="ponte-rede"><a href="rede-ge.html#mun-${m.id}-${encodeURIComponent(m.nome + '/' + m.uf)}">Que grupos econômicos têm endereço em ${m.nome}? Ver na Rede de empresas →</a><br><span>Endereço no cadastro não comprova que o grupo opera o sistema do município.</span></p>`;
  desenharFluxos(m);
}


// ---------- origem-destino de trabalho (v0.8) ----------
// Duas listas por município: para onde vão os que saem e de onde vêm os que entram.
// A direção de ENTRADA é a que carrega o argumento da tese: num município com TZ, quem
// chega de fora paga a tarifa intermunicipal para acessar o sistema gratuito; num polo
// sem TZ, o volume que entra é a mão de obra dos satélites que a gratuidade municipal
// dos vizinhos não alcança.
let munSelecionado = null;
let fluxoDir = 's';                         // 's' = saídas · 'e' = entradas
const OD_REL_TAG = {
  2: '<span title="destino é o polo do próprio arranjo populacional" style="color:var(--amarelo);">◆</span>',
  1: '<span title="mesmo arranjo populacional" style="color:var(--muted);">◇</span>',
  0: ''
};
const OD_COR = { s: '#FF2D6B', e: '#1A54C7' };

function odLista(d, chave, total, nDistintos, m) {
  const lst = d[chave];
  if (!lst || !lst.length) return '';
  const coberto = lst.reduce((a, x) => a + x[1], 0);
  const itens = lst.map(x => {
    const outro = MUNI.get(String(x[0]));
    const rot = outro ? `${outro.nome} – ${outro.uf}` : `município ${x[0]}`;
    const pct = total > 0 ? (x[1] / total * 100) : null;
    const tz = outro && outro.tz_status === 'Ativa'
      ? ' <span class="tag ativa" style="font-size:9px;padding:0 3px;">TZ</span>' : '';
    return `<li>${rot}${tz} ${OD_REL_TAG[x[2]] || ''} — <b>${fmtNum(x[1])}</b>${pct != null ? ` (${pct.toFixed(1)}%)` : ''}</li>`;
  }).join('');
  const dir = chave === 's' ? 'saem' : 'entram';
  const verbo = chave === 's' ? 'trabalham fora' : 'vêm de fora trabalhar aqui';
  return `<div style="margin-top:6px;">
    <div style="display:flex;align-items:baseline;gap:6px;">
      <b style="font-size:11.5px;color:${OD_COR[chave]};">${chave === 's' ? 'Para onde vão' : 'De onde vêm'}</b>
      <button class="odbtn" data-dir="${chave}" style="font-size:10px;padding:1px 5px;cursor:pointer;background:transparent;border:1px solid var(--border);border-radius:3px;color:var(--muted);">ver no mapa</button>
    </div>
    <ul style="margin:4px 0 0;padding-left:16px;font-size:11.5px;color:var(--muted);line-height:1.55;">${itens}</ul>
    <p style="margin:3px 0 0;font-size:10.5px;color:var(--muted);">${fmtNum(total)} pessoas ${verbo}, distribuídas por ${nDistintos} municípios; os ${lst.length} acima respondem por ${(coberto / total * 100).toFixed(0)}% desse fluxo.</p>
  </div>`;
}

function renderODDetail(m) {
  const d = odFor(m);
  const fora = m && m.trab_fora != null ? m.trab_fora : null;
  if (!d && fora == null) return '';
  const cabeca = fora != null
    ? `<p style="margin:5px 0 0;font-size:12px;color:var(--text);line-height:1.5;"><b>${fmtNum(fora)}%</b> dos ocupados de ${m.nome} trabalham em outro município — a parcela da mão de obra que uma gratuidade municipal, por definição, não atende inteira.</p>`
    : '';
  if (!d) {
    return `<div style="margin-top:10px;border-top:1px dashed var(--border);padding-top:8px;">
      <b style="font-size:12.5px;">Deslocamento para trabalho (Censo 2022)</b>${cabeca}
      <p style="margin:5px 0 0;font-size:11.5px;color:var(--muted);line-height:1.5;">Nenhum fluxo deste município foi amostrado o suficiente para ser publicado (mínimo de 5 registros por par origem-destino). São 403 municípios nessa situação — ausência aqui é ausência de medição, não de deslocamento.</p>
    </div>`;
  }
  return `<div style="margin-top:10px;border-top:1px dashed var(--border);padding-top:8px;">
    <b style="font-size:12.5px;">Deslocamento para trabalho (Censo 2022)</b>${cabeca}
    ${odLista(d, 's', d.st, d.sd, m)}
    ${odLista(d, 'e', d.et, d.eo, m)}
    <p style="margin:6px 0 0;font-size:10.5px;color:var(--muted);line-height:1.45;">◆ polo do próprio arranjo · ◇ mesmo arranjo. Matriz origem-destino dos microdados da amostra do Censo 2022, suprimida a células com pelo menos 5 registros amostrados — as demais têm coeficiente de variação da ordem de 100% e não são publicáveis. Ver METADADOS.md.</p>
  </div>`;
}

// ---------- linhas de desejo no mapa ----------
function desenharFluxos(m) {
  gFluxo.innerHTML = '';
  if (!m) return;
  const d = odFor(m);
  if (!d) return;
  const lst = d[fluxoDir];
  if (!lst || !lst.length) return;
  const origem = centroideDe(m.id);
  if (!origem) return;
  const maior = Math.max(...lst.map(x => x[1]));
  const cor = OD_COR[fluxoDir];
  for (const [outroCod, peso] of lst) {
    const p = centroideDe(outroCod);
    if (!p) continue;
    // A largura vai pela RAIZ do fluxo, não pelo fluxo: São Paulo recebe 871 mil e
    // Sorocaba 41 mil, e em escala linear a segunda linha seria invisível.
    const w = 1.1 + 4.2 * Math.sqrt(peso / maior);
    const [a, b] = fluxoDir === 's' ? [origem, p] : [p, origem];
    // curva de Bézier com desvio perpendicular de 18% da corda — arco em vez de reta
    // para que ida e volta entre o mesmo par não se sobreponham
    const dx = b[0] - a[0], dy = b[1] - a[1];
    const cx = (a[0] + b[0]) / 2 - dy * 0.18, cy = (a[1] + b[1]) / 2 + dx * 0.18;
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', `M${a[0].toFixed(1)},${a[1].toFixed(1)}Q${cx.toFixed(1)},${cy.toFixed(1)} ${b[0].toFixed(1)},${b[1].toFixed(1)}`);
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', cor);
    path.setAttribute('stroke-width', w.toFixed(2));
    path.setAttribute('stroke-opacity', '0.85');
    path.setAttribute('stroke-linecap', 'round');
    // a linha vive no mesmo espaço de coordenadas dos polígonos, então acompanha o
    // zoom do viewBox; sem isto, a espessura cresce junto e a linha vira uma mancha
    path.setAttribute('vector-effect', 'non-scaling-stroke');
    gFluxo.appendChild(path);
    gFluxo.appendChild(ponto(b, cor, w / 1.4 + 2.5));
  }
  // ancoragem do município selecionado, em branco com contorno, para o olho achar a origem
  gFluxo.appendChild(ponto(origem, cor, 9, '#fff'));
}

// Marcador de ponto desenhado como TRAÇO de comprimento zero com ponta redonda, e não
// como <circle>. Motivo: o `r` de um circle está em unidades do usuário e cresce com o
// zoom do viewBox, enquanto `stroke-width` com vector-effect="non-scaling-stroke" fica
// em pixels de tela. Com circle, ao enquadrar a bacia de deslocamento de um município
// os marcadores viravam manchas que engoliam o mapa e escondiam quatro dos cinco
// destinos — o primeiro desenho tinha exatamente esse defeito.
function ponto([x, y], cor, px, preenchimento) {
  const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  const s = `${x.toFixed(1)},${y.toFixed(1)}`;
  p.setAttribute('d', `M${s}L${s}`);
  p.setAttribute('stroke-linecap', 'round');
  p.setAttribute('vector-effect', 'non-scaling-stroke');
  p.setAttribute('stroke', preenchimento || cor);
  p.setAttribute('stroke-width', px.toFixed(2));
  if (preenchimento) {
    // dois traços sobrepostos: o de baixo, mais grosso, faz o contorno colorido
    const fora = p.cloneNode();
    fora.setAttribute('stroke', cor);
    fora.setAttribute('stroke-width', (px + 3).toFixed(2));
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.appendChild(fora); g.appendChild(p);
    return g;
  }
  return p;
}

// Troca a direção desenhada sem re-renderizar o card todo.
//
// ⚠️ Escuta 'pointerdown', não só 'click', e isso é correção de bug, não estilo.
// Depois de escolher o município pela busca, o campo #muniSearch continua com o
// foco. O primeiro clique real em qualquer lugar tira o foco dele, o que dispara
// 'change', que chama selecionaMunicipioBuscado() -> renderDetail(), que
// reescreve o innerHTML de #detail. Resultado: entre o mousedown e o click o
// botão deixa de existir, o evento 'click' não chega a ele e
// e.target.closest('.odbtn') não encontra nada — o botão simplesmente não
// respondia ao primeiro clique. Um .click() programático funcionava (não há
// blur), e foi o que quase deixou o bug passar no teste. 'pointerdown' acontece
// antes do blur. O 'click' fica também, para teclado (Enter no botão focado).
function trocaDirecaoFluxo(e) {
  const b = e.target.closest('.odbtn');
  if (!b) return;
  fluxoDir = b.dataset.dir;
  desenharFluxos(munSelecionado);
  enquadrarFluxos(munSelecionado);
}

// Enquadra o mapa na bacia de deslocamento do município: origem + destinos.
// Sem isto o recurso quase não serve. Na escala do Brasil os destinos de Sorocaba
// ficam todos a menos de 100 km, e os arcos saem com poucos pixels de comprimento —
// as linhas existem no SVG e são invisíveis na prática. O enquadramento acontece só
// no clique explícito em "ver no mapa", não a cada seleção: mexer no zoom sem o
// usuário pedir é desorientador, e a seleção também vem do mapa e da tabela.
function enquadrarFluxos(m) {
  if (!m) return;
  const d = odFor(m);
  const lst = d && d[fluxoDir];
  if (!lst || !lst.length) return;
  const pts = [centroideDe(m.id), ...lst.map(x => centroideDe(x[0]))].filter(Boolean);
  if (pts.length < 2) return;
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  const x1 = Math.min(...xs), x2 = Math.max(...xs);
  const y1 = Math.min(...ys), y2 = Math.max(...ys);
  // padFrac generoso: o arco de Bézier se afasta da corda, e sem folga a curva
  // mais externa é cortada pela borda do enquadramento
  animateViewBox(bboxToViewBox(x1, y1, x2 - x1, y2 - y1, 0.35));
  document.getElementById('zoomHint').textContent =
    (fluxoDir === 's' ? 'destinos de ' : 'origens de ') + m.nome + ' – ' + m.uf;
}
document.addEventListener('pointerdown', trocaDirecaoFluxo);
document.addEventListener('click', trocaDirecaoFluxo);

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

// 23/10/2026 — decisão do autor: a lista de grupos econômicos sai do card do
// município, junto com o painel de concentração; toda a análise de grupos passa para a
// página Rede de empresas. A função fica aqui, fora do card, para ser reaproveitada lá.
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

function renderArranjoDetail(m) {
  const a = arranjoFor(m);
  if (!a) {
    if (m.tz_bin !== 'TZ' && m.tz_status !== 'Parcial (ativa)') return '';
    return `<div style="margin-top:10px;border-top:1px dashed var(--border);padding-top:8px;">
      <b style="font-size:12.5px;">O arranjo do contrato</b>
      <p style="margin:5px 0 0;font-size:12px;color:var(--muted);line-height:1.5;">Arranjo não apurado para este caso. Não apurado não é zero: significa que o contrato, o edital ou o termo de referência não foi localizado, não que não exista.</p>
    </div>`;
  }
  const linha = (rot, v, extra) => v
    ? `<tr><td>${rot}</td><td>${v}${extra || ''}</td></tr>` : '';
  const pv = a.prova && PROVA_ROT[a.prova];
  const selo = pv
    ? ` <span title="${a.prova_txt || ''}" style="display:inline-block;margin-left:6px;padding:1px 6px;border-radius:9px;font-size:10px;font-weight:700;background:${pv[0]};color:rgba(0,0,0,.78);">${pv[1]}</span>`
    : '';
  return `<div style="margin-top:10px;border-top:1px dashed var(--border);padding-top:8px;">
    <b style="font-size:12.5px;">O arranjo do contrato</b>
    <p style="margin:4px 0 6px;font-size:11.5px;color:var(--muted);line-height:1.5;">O que foi contratado, e por qual instrumento a gratuidade entrou. Levantamento documental da pesquisa (14/10/2026).</p>
    <table style="margin:0;">
      ${linha('Arranjo', a.a, selo)}
      ${linha('Quem presta', a.esf === 'público' ? 'operação municipal' : a.esf === 'privado' ? 'empresa privada' : a.esf === 'variável' ? 'depende do contrato' : a.esf)}
      ${linha('Locação', a.loc)}
      ${linha('Via jurídica', a.via)}
      ${linha('O que a norma faz', a.norma)}
      ${(() => { const r = remunFor(m) || {}; const km = (r.km || [])[0], hab = (r.hab || [])[0];
        return linha('Quem recebe', r.dest ? DEST_ROT[r.dest].split(' — ')[0].split(' (')[0] : null)
          + linha('Como é pago', r.comp || a.rem, r.comp && r.comp_prova ? ` <span style="color:var(--muted);font-size:11px;">(prova ${r.comp_prova === 'alta' ? 'alta' : 'média'})</span>` : '')
          + linha('Risco de demanda', riscoDaFormula(r.comp))
          + linha('Preço do km', km ? `${fmtR(km.v)} <span style="color:var(--muted);font-size:11px;">(maio/2026, ${km.fonte})</span>` : null)
          + linha('Custo por habitante', hab ? `${fmtR(hab.v, 0)} por ano <span style="color:var(--muted);font-size:11px;">(contrato de ${hab.ano})</span>` : null); })()}
      ${(() => { const at = custeioFor(m)[0]; if (!at) return '';
        return linha('Ato lido', at.ato ? `${at.ato}${at.instr ? ` <span style="color:var(--muted);font-size:11px;">(${at.instr})</span>` : ''}` : at.instr)
          + linha('Custeio no ato', LEIT_ROT[at.leit] || at.leit)
          + linha('Fontes nomeadas', at.fontes)
          + linha('Condição no ato', at.cond); })()}
    </table>
    ${a.via === 'concessão/permissão preexistente' ? `<p style="margin:6px 0 0;font-size:11.5px;color:var(--muted);line-height:1.5;">A gratuidade <b>entrou sobre um contrato que já existia</b>, com o operador que já estava lá — em geral por termo aditivo. É a forma de entrada que a tese acompanha com atenção, e são 22 casos assim na base.</p>` : ''}
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
// Ordem do Gráfico 15 da tese (Seção 5.5): primeiro riqueza, motorização e uso do
// ônibus, que são a leitura que a tese faz; depois os demais indicadores do painel.
const BAR_METRICS = [
  { k: 'pib_pc', label: 'PIB per capita mediano (R$)', fmt: v => 'R$ ' + fmtNum(v) },
  { k: 'motorizacao', label: 'Motorização mediana (veíc/hab)', fmt: fmtNum },
  { k: 'onibus', label: 'Uso do ônibus no deslocamento a trabalho ou estudo (%, Censo 2022)', fmt: v => fmtNum(v) + '%' },
  { k: 'ibeu', label: 'IBEU mediano', fmt: fmtNum },
  { k: 'idh', label: 'IDH mediano', fmt: fmtNum },
  { k: 'rec_prop_pc', label: 'Receita própria per capita mediana (R$)', fmt: v => 'R$ ' + fmtNum(v) },
  { k: 'taxa_obitos_transito', label: 'Óbitos no trânsito /100mil mediano (2019)', fmt: fmtNum },
  { k: 'cadunico_cobertura', label: 'Cobertura do CadÚnico mediana (%, ago/2025)', fmt: v => fmtNum(v) + '%' },
];

// ---------- 23/10/2026: a comparação passa a fazer o que a tese faz ----------
// Dois ajustes de método, ambos da Seção 5.5 (Gráfico 15):
// (1) OS GRUPOS. "TZ" aqui é a camada 1 (universal ativa, 174) e "Não-TZ" são os
//     municípios sem política nenhuma. Parciais, encerradas, pistas e regulamentadas
//     ficam fora dos dois lados — antes entravam no "TZ" ou no "Não-TZ" conforme o
//     campo, e a comparação misturava desenhos que a régua separa.
// (2) O PORTE. A comparação bruta é confundida pelo tamanho: a Tarifa Zero está em
//     municípios pequenos e médios, e o "resto do país" vai das menores cidades às
//     metrópoles. Com o controle ligado, a mediana Não-TZ é PONDERADA para ter a mesma
//     distribuição de porte dos municípios com TZ (padronização direta, nas seis faixas
//     que a tese usa). É assim que a tese chega ao achado que o bruto esconde: acima de
//     100 mil habitantes a vantagem de riqueza some e o uso do ônibus se inverte.
const FAIXAS_TESE = [
  ['<10', 'até 10 mil', 0, 1e4], ['10-20', '10 a 20 mil', 1e4, 2e4], ['20-50', '20 a 50 mil', 2e4, 5e4],
  ['50-100', '50 a 100 mil', 5e4, 1e5], ['100-500', '100 a 500 mil', 1e5, 5e5], ['>500', 'mais de 500 mil', 5e5, Infinity],
];
function faixaTese(pop) {
  for (const f of FAIXAS_TESE) if (pop >= f[2] && pop < f[3]) return f[0];
  return null;
}
function valorMetrica(m, k) {
  if (k === 'onibus') { const md = modalFor(m); return md ? md.onibus : null; }
  return m[k];
}
function medianaPonderada(pares) {   // pares: [valor, peso]
  const v = pares.filter(p => p[0] != null && !Number.isNaN(p[0]) && p[1] > 0).sort((a, b) => a[0] - b[0]);
  const tot = v.reduce((a, p) => a + p[1], 0);
  if (!tot) return null;
  let ac = 0;
  for (const [x, w] of v) { ac += w; if (ac >= tot / 2) return x; }
  return v[v.length - 1][0];
}
function gruposComparacao() {
  const rows = subsetNoTz();
  return {
    tz: rows.filter(m => m.tz_status === 'Ativa'),
    nao: rows.filter(m => m.tz_status === 'Não TZ'),
  };
}
function controlePorteLigado() {
  const c = document.getElementById('porteCtrl');
  return !c || c.checked;
}

function renderBars() {
  const { tz: rowsTZ, nao: rowsNao } = gruposComparacao();
  const el = document.getElementById('bars');
  if (!el) return;
  if (!rowsTZ.length) {
    el.innerHTML = '<div class="empty">Nenhum município com Tarifa Zero universal neste recorte.</div>';
    return;
  }
  const porte = controlePorteLigado();
  // peso de cada município Não-TZ: (fração de TZ na faixa) / (fração de Não-TZ na faixa)
  const nTZf = {}, nNaof = {};
  for (const m of rowsTZ) { const f = faixaTese(m.pop); nTZf[f] = (nTZf[f] || 0) + 1; }
  for (const m of rowsNao) { const f = faixaTese(m.pop); nNaof[f] = (nNaof[f] || 0) + 1; }
  const peso = m => {
    if (!porte) return 1;
    const f = faixaTese(m.pop);
    return (nTZf[f] && nNaof[f]) ? (nTZf[f] / rowsTZ.length) / (nNaof[f] / rowsNao.length) : 0;
  };
  // municípios Não-TZ que efetivamente entram na comparação controlada
  const nNaoUsados = porte ? rowsNao.filter(m => peso(m) > 0).length : rowsNao.length;
  const rotNao = porte ? 'Não-TZ, mesmo porte' : 'Não-TZ';

  let html = `<p class="sub" style="margin:0 0 8px;grid-column:1/-1;">Municípios comparados: <b>TZ universal ${rowsTZ.length.toLocaleString('pt-BR')}</b> · <b>${rotNao} ${nNaoUsados.toLocaleString('pt-BR')}</b></p>`;
  for (const met of BAR_METRICS) {
    const vTZ = median(rowsTZ.map(m => valorMetrica(m, met.k)));
    const vNao = porte
      ? medianaPonderada(rowsNao.map(m => [valorMetrica(m, met.k), peso(m)]))
      : median(rowsNao.map(m => valorMetrica(m, met.k)));
    const max = Math.max(vNao || 0, vTZ || 0, 1e-9);
    html += `<div class="barrow">
      <div class="lab"><span>${met.label}</span></div>
      <div class="lab"><span>${rotNao}</span><b>${met.fmt(vNao)}</b></div>
      <div class="bartrack"><div class="barfill a" style="width:${(100 * (vNao || 0) / max).toFixed(1)}%"></div></div>
      <div class="lab" style="margin-top:4px;"><span>TZ universal</span><b>${met.fmt(vTZ)}</b></div>
      <div class="bartrack"><div class="barfill b" style="width:${(100 * (vTZ || 0) / max).toFixed(1)}%"></div></div>
    </div>`;
  }
  el.innerHTML = html;
  renderPorteTabela(rowsTZ, rowsNao);
}

// A leitura por faixa é onde a tese tira o achado: até 100 mil habitantes, os
// municípios com TZ usam mais o ônibus que os de mesmo porte; acima disso, menos.
function renderPorteTabela(rowsTZ, rowsNao) {
  const el = document.getElementById('porteTabela');
  if (!el) return;
  const mets = [BAR_METRICS[0], BAR_METRICS[2]];
  let linhas = '';
  for (const [k, rot] of FAIXAS_TESE) {
    const a = rowsTZ.filter(m => faixaTese(m.pop) === k);
    const b = rowsNao.filter(m => faixaTese(m.pop) === k);
    if (!a.length && !b.length) continue;
    const cel = met => {
      const va = a.length ? median(a.map(m => valorMetrica(m, met.k))) : null;
      const vb = b.length ? median(b.map(m => valorMetrica(m, met.k))) : null;
      const inv = (va != null && vb != null && met.k === 'onibus' && va < vb) ? ' class="inv"' : '';
      return `<td${inv}>${va != null ? met.fmt(va) : '—'}</td><td>${vb != null ? met.fmt(vb) : '—'}</td>`;
    };
    const pouco = a.length > 0 && a.length < 5;   // mediana de 1 a 4 casos: mostrar, mas avisar
    linhas += `<tr${pouco ? ' class="pouco" title="Menos de 5 municípios com TZ nesta faixa: a mediana é frágil"' : ''}><td>${rot}${pouco ? ' <span class="aviso-n">⚠ n pequeno</span>' : ''}</td><td class="n">${a.length}</td><td class="n">${b.length}</td>${mets.map(cel).join('')}</tr>`;
  }
  el.innerHTML = `<table class="portetab">
    <thead><tr><th rowspan="2">Faixa de população</th><th colspan="2">Municípios</th><th colspan="2">PIB per capita (mediana)</th><th colspan="2">Uso do ônibus (mediana)</th></tr>
    <tr><th>TZ</th><th>Não-TZ</th><th>TZ</th><th>Não-TZ</th><th>TZ</th><th>Não-TZ</th></tr></thead>
    <tbody>${linhas}</tbody></table>
    <p class="sub" style="margin-top:7px;">⚠ marca faixas com menos de 5 municípios com TZ: a mediana existe, mas um só caso a move. Em destaque, as faixas em que os municípios com Tarifa Zero usam <b>menos</b> o ônibus que os de mesmo porte. A tese lê assim: até 100 mil habitantes, a camada universal usa mais o ônibus; acima disso, a relação se inverte. O dado do Censo 2022 não separa causa e efeito — parte dessas políticas já operava na data do Censo e pode ter aumentado o uso.</p>`;
}

// ---------- crosstabs (rótulo acima da própria barra; % dentro de cada categoria) ----------
function renderCrosstabs() {
  const el = document.getElementById('crosstabs');
  if (!el) return;
  // 23/10/2026: antes era um agregado nacional fixo (STATS), o único bloco desta
  // área que não respondia ao recorte — quem filtrava MG via metade da comparação
  // mudar e metade não. Agora é calculado do recorte, com a mesma definição de TZ da
  // comparação de medianas: camada 1 ativa.
  const rows = subsetNoTz();
  const defs = [
    { key: 'regic_nivel', title: 'Hierarquia urbana (REGIC)', order: STATS.regic_order, labelFn: k => `${k} · ${REGIC_LABELS[k]}` },
    { key: 'tipo_arranjo', title: 'Sede × satélite de arranjo', order: STATS.arranjo_order, labelFn: k => k },
    { key: 'modelo_prestacao_simples', title: 'Modelo de prestação (MUNIC 2020 — só 31% responderam)', order: STATS.modelo_order, labelFn: k => k },
    { key: 'faixa_pop', title: 'Faixa populacional', order: STATS.faixa_order, labelFn: k => k },
  ];
  let html = '';
  for (const d of defs) {
    const ct = {};
    for (const m of rows) {
      const k = m[d.key];
      if (k == null || k === '') continue;
      const c = ct[String(k)] || (ct[String(k)] = { n: 0, tz: 0 });
      c.n++; if (m.tz_status === 'Ativa') c.tz++;
    }
    const itens = d.order.map(k => [k, ct[String(k)]]).filter(x => x[1] && x[1].n);
    if (!itens.length) continue;
    const maxPct = Math.max(...itens.map(([, c]) => c.tz / c.n), 0.001);
    html += `<div class="xt"><h4>${d.title}</h4>`;
    for (const [k, c] of itens) {
      const pct = c.tz / c.n;
      html += `<div class="xtitem">
        <div class="xtlab"><span>${d.labelFn(k)}</span><b>${(pct * 100).toFixed(1).replace('.', ',')}% <span style="font-weight:400;color:var(--muted);">(${c.tz} de ${fmtNum(c.n)})</span></b></div>
        <div class="xtrack"><div class="xtfill" style="width:${(100 * pct / maxPct).toFixed(1)}%"></div></div>
      </div>`;
    }
    html += `</div>`;
  }
  el.innerHTML = html || '<div class="empty">Sem municípios neste recorte.</div>';
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
  // 23/10/2026: passa a ser calculada do recorte (antes, agregado nacional fixo).
  // Mantém o critério de antes, que é o da Análise I da tese: o grupo TZ só conta
  // políticas iniciadas até 2022, porque o dado é do Censo 2022 — a gratuidade
  // adotada depois não pode ter mudado o deslocamento medido ali.
  const rows = subsetNoTz();
  const tz = rows.filter(m => m.tz_status === 'Ativa' && m.tz_ano_txt != null && Number(m.tz_ano_txt) <= 2022);
  const nao = rows.filter(m => m.tz_status === 'Não TZ');
  const mediaModos = grupo => {
    const acc = { onibus: 0, automovel: 0, motocicleta: 0, ativo: 0, outros: 0 }; let n = 0;
    for (const m of grupo) { const md = modalFor(m); if (!md) continue; n++; for (const k in acc) acc[k] += (md[k] || 0); }
    if (n) for (const k in acc) acc[k] /= n;
    return { acc, n };
  };
  const linha = (label, g) => {
    const { acc, n } = mediaModos(g);
    if (!n) return `<div class="msrow"><div class="mslab"><b>${label}</b><span>sem municípios no recorte</span></div></div>`;
    const tot = Object.values(acc).reduce((a, b) => a + b, 0) || 1;
    const bar = Object.keys(MODAL_STACK_LABELS).map(k => { const v = 100 * acc[k] / tot;
      return `<div class="seg" style="width:${v.toFixed(2)}%;background:${MODAL_STACK_COLORS[k]};" title="${MODAL_STACK_LABELS[k]}: ${v.toFixed(1)}%"></div>`; }).join('');
    return `<div class="msrow"><div class="mslab"><b>${label}</b><span>n=${n}</span></div><div class="msbar">${bar}</div></div>`;
  };
  el.innerHTML = linha('TZ universal (adotada até 2022)', tz) + linha('Não-TZ', nao)
    + `<div class="mslegend">${Object.keys(MODAL_STACK_LABELS).map(k =>
      `<span><i style="background:${MODAL_STACK_COLORS[k]}"></i>${MODAL_STACK_LABELS[k]}</span>`).join('')}</div>`;
}

// ---------- régua descritiva, no cabeçalho (22/10/2026) ----------
// A régua é uma ESCALA ORDENADA, não um conjunto de rótulos: vai da ausência de
// portão (1a) até os desenhos em que o portão condiciona quem ou quando se viaja
// (2a-2e), com as encerradas como camada própria (3). Desenhar os casos sobre ela
// é mais informativo que qualquer cartão: mostra onde o Brasil está na régua, e
// que a imensa maioria dos casos é 1a — o que é o achado, não um detalhe.
// Critério e rótulos: `Regras de classificacao das reguas` (cofre), A.1.4, 18/09/2026.
const REGUA = [
  { k: '1a', grupo: 1, rot: 'Ausência',     desc: 'nenhum portão de acesso',                       cor: '#F5E400' },
  { k: '1b', grupo: 1, rot: 'Procedimento', desc: 'exige uma ação (cadastro), mas qualquer um pode cumprir', cor: '#D9CE12' },
  { k: '1c', grupo: 1, rot: 'Residência',   desc: 'restrito a quem mora no município — não tira a universalidade (Kębłowski, 2020)', cor: '#BDB623' },
  { k: '1d', grupo: 1, rot: 'Prazo',        desc: 'a norma declara quando termina, mas o termo ainda não chegou', cor: '#A19E33' },
  { k: '2a', grupo: 2, rot: 'Grupo social', desc: 'portão de identidade que não é residência (renda, vínculo)', cor: '#E2892C' },
  { k: '2b', grupo: 2, rot: 'Espaço',       desc: 'gratuidade só em certas linhas ou regiões',      cor: '#D96F3B' },
  { k: '2c', grupo: 2, rot: 'Dias',         desc: 'gratuidade só em certos dias (domingos, feriados)', cor: '#D05549' },
  { k: '2d', grupo: 2, rot: 'Eventos',      desc: 'gratuidade pontual decidida pelo município',     cor: '#C73B58' },
  { k: '2e', grupo: 2, rot: 'Finalidade',   desc: 'gratuidade só para chegar a um serviço (escola, saúde)', cor: '#BE2166' },
];
const REGUA_IDX = Object.fromEntries(REGUA.map((r, i) => [r.k, i]));

// 12.9 — a adoção por porte com o denominador da tese. Bloco ESTÁTICO de propósito:
// o índice de indício de sistema é de um artigo inédito, e só as contagens agregadas
// vêm para o painel (ver build_curva_porte.py). Desenhado uma vez, na carga.
function renderCurvaPorte() {
  const el = document.getElementById('curvaPorte');
  if (!el || !CURVA_PORTE) return;
  const fx = CURVA_PORTE.faixas;
  const pct = (a, b) => b ? a / b : 0;
  const max = Math.max(...fx.map(f => Math.max(pct(f.tz, f.n), pct(f.tz_sist, f.n_sist))), 0.001);
  const fmtP = v => (100 * v).toFixed(1).replace('.', ',') + '%';
  const barra = (v, cor, txt) => `<div class="cvbar"><div class="cvtrack"><div class="cvfill" style="width:${(100 * v / max).toFixed(1)}%;background:${cor};"></div></div><div class="cvn">${txt}</div></div>`;
  const pico = fx.reduce((a, f) => pct(f.tz_sist, f.n_sist) > pct(a.tz_sist, a.n_sist) ? f : a, fx[0]);
  el.innerHTML = `
    <div class="rgchips" style="margin:0 0 10px;">
      <span class="rgchip"><i style="background:#6b7280"></i>entre todos os municípios da faixa</span>
      <span class="rgchip"><i style="background:var(--amarelo)"></i>entre os que têm indício de sistema de ônibus</span>
    </div>
    ${fx.map(f => `<div class="cvlin"><div class="cvrot">${f.rot}</div><div class="cvbars">
      ${barra(pct(f.tz, f.n), '#6b7280', `<b>${fmtP(pct(f.tz, f.n))}</b> · ${f.tz} de ${fmtNum(f.n)}`)}
      ${barra(pct(f.tz_sist, f.n_sist), 'var(--amarelo)', `<b>${fmtP(pct(f.tz_sist, f.n_sist))}</b> · ${f.tz_sist} de ${fmtNum(f.n_sist)}${f === pico ? ' ← pico' : ''}`)}
    </div></div>`).join('')}
    <p class="sub" style="margin-top:4px;">No total, a camada universal está em <b>${fmtP(pct(CURVA_PORTE.total.tz, CURVA_PORTE.total.n))}</b> de todos os municípios (${CURVA_PORTE.total.tz}) e em <b>${fmtP(pct(CURVA_PORTE.total.tz_sist, CURVA_PORTE.total.n_sist))}</b> dos ${fmtNum(CURVA_PORTE.total.n_sist)} com indício de sistema (${CURVA_PORTE.total.tz_sist}). O padrão é compatível com a hipótese da tese — a gratuidade universal rareia onde o sistema é maior e mais atrativo — e também com a explicação rival do custo e da complexidade, que crescem com o porte. Separar as duas é trabalho do teste, não deste gráfico.</p>`;
}

// ---------- remuneração e custo (Seções 7.2 a 7.4; pedido do autor, 23/10/2026) ----------
// Entra a remuneração: quem recebe o recurso, por qual fórmula, quem carrega o risco de
// demanda e quanto se paga (preço do km e custo por habitante). Fica FORA a contrapartida e a
// posição no plano analítico, suspensas até a defesa (12.6) — por isso nenhum texto aqui
// usa "gestão do comum", "garantia de receita sem controle" ou "Bolsa-Empresário".
function remunFor(m) { return (m && REMUN[String(m.id)]) || null; }
const DEST_ROT = {
  publica: 'Operação pública — a prefeitura opera, sem operador a remunerar',
  oferta: 'Operador privado pago pela oferta (km, veículo, valor fixo, custo)',
  demanda: 'Operador privado pago pela demanda (por passageiro)',
  usuario: 'Recurso entregue ao usuário (vale, crédito)',
  privado_nd: 'Operador privado, remuneração não apurada',
};
const DEST_COR = { publica: '#4F7FD4', oferta: '#C9A33B', demanda: '#D05549', usuario: '#8a8f3a', privado_nd: '#6b7280' };
// A regra de risco é a da Seção 7.2: preço fixado põe o risco de demanda na prefeitura e o
// de custo no operador; pagar o custo apurado põe os dois na prefeitura; pagar por
// passageiro põe a demanda no operador.
function riscoDaFormula(comp) {
  if (!comp) return null;
  if (/passageiro/.test(comp)) return 'demanda com o operador';
  if (/custo do serviço/.test(comp)) return 'os dois riscos com a prefeitura';
  return 'demanda com a prefeitura';
}
function grupoFormula(comp) {
  if (!comp) return 'não lida';
  if (comp.includes('+')) return 'combinação de parcelas';
  return ({ 'por km': 'só o quilômetro rodado', 'valor global fixo': 'valor global fixo',
            'fixo por veículo': 'parcela fixa por veículo', 'custo do serviço': 'custo apurado do serviço',
            'por passageiro': 'por passageiro' })[comp] || comp;
}
const fmtR = (v, d = 2) => 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d });

function stripPlot(pts, opts) {
  // pts: [{v, cor, tit}]; escala linear entre opts.min e opts.max
  if (!pts.length) return '<p class="sub">Nenhum contrato com valor lido neste recorte.</p>';
  const x = v => (100 * (Math.min(Math.max(v, opts.min), opts.max) - opts.min) / (opts.max - opts.min));
  const ord = [...pts].sort((a, b) => a.v - b.v);
  const med = ord.length % 2 ? ord[(ord.length - 1) / 2].v : (ord[ord.length / 2 - 1].v + ord[ord.length / 2].v) / 2;
  const nivel = {};   // empilha pontos muito próximos para não se esconderem
  const dots = ord.map(p => { const b = Math.round(x(p.v) / 1.6); nivel[b] = (nivel[b] || 0) + 1;
    const dy = [0, -12, 12, -24, 24][(nivel[b] - 1) % 5];
    return `<div class="pt" style="left:${x(p.v).toFixed(2)}%;top:${39 + dy}px;background:${p.cor};" title="${p.tit}"></div>`; }).join('');
  const faixas = (opts.faixas || []).map(f => `<div class="faixa" style="left:${x(f.a)}%;width:${x(f.b) - x(f.a)}%;${f.tom ? 'background:' + f.tom + ';' : ''}" title="${f.rot}"></div>`).join('');
  const ref = opts.ref ? `<div class="ref" style="left:${x(opts.ref.v)}%;" title="${opts.ref.rot}"></div>` : '';
  const ticks = opts.ticks.map(t => `<div class="tick" style="left:${x(t)}%;">${(opts.fmtTick || opts.fmt)(t)}</div>`).join('');
  return `<div class="strip">${faixas}<div class="eixo"></div>${ref}${dots}<div class="med" style="left:${x(med)}%;"><span>${opts.fmt(med)}</span></div>${ticks}</div>
    <p class="sub" style="margin-top:14px;">${ord.length} ${ord.length === 1 ? 'contrato' : 'contratos'} · mediana <b>${opts.fmt(med)}</b> · de ${opts.fmt(ord[0].v)} a ${opts.fmt(ord[ord.length - 1].v)}</p>`;
}

// ---------- custeio (Seção 7.5): de onde vem o dinheiro e quanto custa reverter ----------
function custeioFor(m) { return (m && CUSTEIO[String(m.id)]) || []; }
// Quadro 28 da tese. Não há coluna por política no pacote, e por isso este bloco é FIXO,
// com as contagens da tese, e diz isso; o bloco ao lado, do que o ato escreve, responde ao recorte.
const ESCALA_COMPROMISSO = [
  { n: 0, rot: 'Receita própria vinculada em lei e arrecadada', rev: 'revogar a lei e desfazer o vínculo' },
  { n: 15, rot: 'Fundo criado em lei, sem receita própria comprovada', rev: 'a estrutura resiste; o recurso, não' },
  { n: 53, rot: 'Dotação identificada (lei, LOA ou contrato)', rev: 'renovada a cada ano; desfeita sem ato específico' },
  { n: 52, rot: 'Orçamento geral, sem dotação identificada', rev: 'nenhum ato próprio a desfazer' },
];
const LEIT_ORDEM = ['fontes específicas além do orçamento', 'dotação com classificação orçamentária', 'fonte genérica (dotações próprias)', 'sem cláusula de custeio'];
const LEIT_ROT = {
  'fontes específicas além do orçamento': 'nomeia fontes além do orçamento',
  'dotação com classificação orçamentária': 'classifica a despesa (função, subfunção, elemento)',
  'fonte genérica (dotações próprias)': 'só diz que correrá por dotações próprias',
  'sem cláusula de custeio': 'não tem cláusula de custeio',
};
const LEIT_COR = { 'fontes específicas além do orçamento': '#4F7FD4', 'dotação com classificação orçamentária': '#6B8FC9', 'fonte genérica (dotações próprias)': '#C9A33B', 'sem cláusula de custeio': '#D05549' };

function renderCusteioBloco(rows) {
  const max = Math.max(...ESCALA_COMPROMISSO.map(e => e.n), 1);
  const escala = ESCALA_COMPROMISSO.map((e, i) => `<div class="arrlin">
      <div class="arrrot" style="white-space:normal;" title="${e.rot} — reverter exige: ${e.rev}"><b>${i + 1}</b> · ${e.rot}<br><span style="color:var(--muted);font-size:10.5px;">para reverter: ${e.rev}</span></div>
      <div class="arrbarra"><div class="arrfill" style="width:${(100 * e.n / max).toFixed(1)}%;background:${['#4F7FD4', '#6B8FC9', '#C9A33B', '#D05549'][i]};"></div></div>
      <div class="arrn">${e.n}</div></div>`).join('');
  // o que o ato escreve — responde ao recorte
  const atos = [];
  for (const m of rows) for (const a of custeioFor(m)) atos.push(a);
  const legiveis = atos.filter(a => LEIT_ORDEM.includes(a.leit));
  const c = {}; for (const a of legiveis) c[a.leit] = (c[a.leit] || 0) + 1;
  const maxL = Math.max(...Object.values(c), 1);
  const leit = LEIT_ORDEM.filter(k => c[k]).map(k => `<div class="arrlin">
      <div class="arrrot">${LEIT_ROT[k]}</div>
      <div class="arrbarra"><div class="arrfill" style="width:${(100 * c[k] / maxL).toFixed(1)}%;background:${LEIT_COR[k]};"></div></div>
      <div class="arrn">${c[k]} <span>${(100 * c[k] / legiveis.length).toFixed(0)}%</span></div></div>`).join('');
  const decretos = atos.filter(a => a.instr === 'decreto').length;
  const cond = atos.filter(a => a.cond).length;
  return `<div class="rmgrid" style="margin-top:18px;border-top:1px solid var(--border);padding-top:14px;">
    <div class="arrbloco"><h3>De onde vem o dinheiro — e quanto custa reverter</h3>
      <p class="sub">A escala de compromisso da tese ordena o custeio pelo que é preciso desfazer para acabar com a política. O retrato é o de uma política <b>orçamentária anual</b>: nenhuma política vigente tem receita própria vinculada e arrecadada, e ter fundo não garantiu a continuidade — 3 das 15 com fundo acabaram ou recuaram.</p>
      ${escala}
      <p class="sub" style="margin-top:7px;"><span class="selo-fixo">Brasil, fixo</span> Contagens do Quadro 28 sobre as 187 políticas; em 67 a fonte não foi apurada. A Constituição veda vincular receita de impostos (art. 167, IV), e a taxa, a espécie que sobra ao município, caiu na Justiça onde foi tentada (Vargem Grande Paulista e Paranaguá) — sem acabar com a política.</p></div>
    <div class="arrbloco"><h3>O que o ato da política escreve sobre o custeio</h3>
      <p class="sub">Leitura das cláusulas de custeio dos atos com texto legível, no recorte. O ato que não nomeia fonte nem classifica a despesa não tem o que desfazer para ser revertido.</p>
      ${legiveis.length ? leit : '<p class="sub">Nenhum ato lido neste recorte.</p>'}
      <p class="sub" style="margin-top:7px;">${legiveis.length} atos legíveis${atos.length > legiveis.length ? ` (outros ${atos.length - legiveis.length} são imagem sem texto extraível ou arquivo de outro objeto)` : ''}. Dos ${atos.length} atos lidos, <b>${decretos}</b> ${decretos === 1 ? 'é decreto' : 'são decretos'}, que outro decreto revoga; <b>${cond}</b> ${cond === 1 ? 'condiciona' : 'condicionam'} a própria gratuidade — à disponibilidade orçamentária, à capacidade financeira ou a um prazo.</p></div>
  </div>`;
}

function renderRemunPanel() {
  const el = document.getElementById('remunPanel');
  if (!el) return;
  const rows = subsetNoTz();
  const c1 = rows.filter(m => m.tz_status === 'Ativa');
  if (!c1.length) { el.innerHTML = '<div class="empty">Nenhum município com Tarifa Zero universal neste recorte.</div>'; return; }
  const barras = (pares, total, cores, extra) => {
    const max = Math.max(...pares.map(p => p[1]), 1);
    return pares.map(([k, n, rot]) => `<div class="arrlin">
      <div class="arrrot" title="${rot}">${rot}${extra ? extra(k) : ''}</div>
      <div class="arrbarra"><div class="arrfill" style="width:${(100 * n / max).toFixed(1)}%;background:${cores[k] || '#8F9FBE'};"></div></div>
      <div class="arrn">${n} <span>${(100 * n / total).toFixed(0)}%</span></div></div>`).join('');
  };
  // 1) quem recebe
  const cd = {}; let ndDest = 0;
  for (const m of c1) { const r = remunFor(m); if (r && r.dest) cd[r.dest] = (cd[r.dest] || 0) + 1; else ndDest++; }
  const apur = Object.values(cd).reduce((a, b) => a + b, 0) - (cd.privado_nd || 0);
  const ordemD = ['publica', 'oferta', 'demanda', 'usuario', 'privado_nd'].filter(k => cd[k]);
  const b1 = barras(ordemD.map(k => [k, cd[k], DEST_ROT[k]]), c1.length, DEST_COR);
  // 2) por qual fórmula, entre os pagos pela oferta
  const of = c1.filter(m => (remunFor(m) || {}).dest === 'oferta');
  const cf = {}, riscoDe = {};
  for (const m of of) { const comp = remunFor(m).comp; const g = grupoFormula(comp); cf[g] = (cf[g] || 0) + 1;
    if (comp) riscoDe[g] = riscoDaFormula(comp) === riscoDe[g] || !riscoDe[g] ? riscoDaFormula(comp) : 'varia'; }
  const ordemF = ['só o quilômetro rodado', 'valor global fixo', 'parcela fixa por veículo', 'custo apurado do serviço', 'combinação de parcelas', 'por passageiro', 'não lida'].filter(k => cf[k]);
  const b2 = of.length ? barras(ordemF.map(k => [k, cf[k], k]), of.length, {},
    k => riscoDe[k] && riscoDe[k] !== 'varia' ? `<span class="rmrisco">risco: ${riscoDe[k]}</span>` : '') : '<p class="sub">Nenhum operador pago pela oferta neste recorte.</p>';
  // 3) preço do km e 4) custo por habitante — contratos dos municípios do recorte
  const KM_COR = { 'A4 Prestação de serviço': '#C9A33B', 'A5 Concessão ou permissão': '#D05549', 'A3 Locação com motorista (L2, L3)': '#8F9FBE' };
  const kms = [], habs = [], fora = [];
  for (const m of rows) { const r = remunFor(m); if (!r) continue;
    for (const k of (r.km || [])) kms.push({ v: k.v, cor: KM_COR[k.arr] || '#6b7280', tit: `${m.nome}/${m.uf} — ${fmtR(k.v)}/km (maio/2026) · ${k.arr || 'arranjo não apurado'} · ${k.fonte}${k.nota ? ' · ' + k.nota : ''}` });
    for (const h of (r.hab || [])) { if (h.v >= 700) { fora.push(`${m.nome}/${m.uf} (${fmtR(h.v, 0)})`); continue; }
      habs.push({ v: h.v, cor: '#4F7FD4', tit: `${m.nome}/${m.uf} — ${fmtR(h.v, 0)} por habitante/ano (contrato de ${h.ano})` }); } }
  const legKm = Object.entries(KM_COR).map(([k, c]) => `<span class="rgchip"><i style="background:${c}"></i>${k.replace(/^A\d /, '')}</span>`).join('') + '<span class="rgchip"><i style="background:#6b7280"></i>outros</span>'
    + '<span class="rgchip"><i style="background:rgba(255,255,255,.18)"></i>CadTerc diurno (R$ 8,14–10,77)</span><span class="rgchip"><i style="background:rgba(255,255,255,.08)"></i>diuturno (até R$ 15,09)</span><span class="rgchip"><i style="background:#FF2D6B"></i>R$ 5,64 (Veloso et al., 2025)</span>';

  el.innerHTML = `
    <div class="rmgrid">
      <div class="arrbloco"><h3>Quem recebe o recurso</h3>
        <p class="sub">Entre as ${c1.length} políticas universais do recorte.${algumFiltroAtivo() ? '' : ' Onde está apurado, a Tarifa Zero brasileira custeia operação pública ou paga o operador pela oferta; o pagamento por passageiro é residual.'}</p>
        ${b1}
        <p class="sub" style="margin-top:7px;">${ndDest ? `<b>${ndDest}</b> sem destinatário apurado. ` : ''}${cd.usuario ? '' : 'Nenhuma política universal entrega o recurso ao usuário.'}</p></div>
      <div class="arrbloco"><h3>Por qual fórmula o operador é pago</h3>
        <p class="sub">Entre as ${of.length} pagas pela oferta. A fórmula diz quem carrega o risco: com preço fixado, o risco de a demanda variar fica com a prefeitura; pagando o custo apurado, ela carrega também o risco de custo.</p>
        ${b2}</div>
    </div>
    <div class="rmgrid" style="margin-top:18px;">
      <div class="arrbloco"><h3>Quanto custa o quilômetro</h3>
        <p class="sub">Preço do quilômetro nos contratos lidos, corrigido pelo IPCA para maio de 2026. As faixas são a referência pública do Estado de São Paulo para fretamento contínuo (CadTerc, ônibus de 44 lugares, 4 a 8 mil km por mês); a linha rosa, o parâmetro de R$ 5,64/km usado por Veloso et al. (2025) para estimar o custo da Tarifa Zero.</p>
        ${stripPlot(kms, { min: 4, max: 25, ticks: [5, 10, 15, 20], fmt: v => fmtR(v), fmtTick: v => fmtR(v, 0), ref: { v: 5.64, rot: 'R$ 5,64/km — Veloso et al. (2025)' },
          faixas: [{ a: 8.14, b: 10.77, rot: 'CadTerc, turno diurno: R$ 8,14 a R$ 10,77/km', tom: 'rgba(255,255,255,.09)' }, { a: 10.77, b: 15.09, rot: 'CadTerc, turno diuturno: até R$ 15,09/km', tom: 'rgba(255,255,255,.04)' }] })}
        <div class="rgchips" style="margin-top:2px;">${legKm}</div></div>
      <div class="arrbloco"><h3>Quanto custa por habitante, por ano</h3>
        <p class="sub">Valor anual do contrato lido dividido pela população de 2022, em preços nominais do ano do contrato. Mistura preço e quantidade de serviço — não diz se a Tarifa Zero paga caro ou barato.</p>
        ${stripPlot(habs, { min: 0, max: 330, ticks: [0, 100, 200, 300], fmt: v => fmtR(v, 0), fmtTick: v => fmtR(v, 0) })}
        ${fora.length ? `<p class="sub">Fora da escala: ${fora.join(', ')} — um valor anual com todas as despesas incluídas e um contrato que junta o transporte escolar.</p>` : ''}</div>
    </div>
    ${renderCusteioBloco(rows)}
    <p class="sub" style="margin-top:12px;border-top:1px solid var(--border);padding-top:9px;">O que os contratos permitem medir é menos do que a comparação pede: o preço do quilômetro mistura a parcela fixa do veículo e do motorista com a variável do quilômetro, e a frota quase nunca está no contrato. Os preços estão na ordem de grandeza da referência pública; a distância entre eles passa pela quilometragem por veículo e pela região, que os contratos deveriam trazer.</p>`;
}

// 12.4 — o arranjo agregado. Duas leituras, lado a lado: o que foi contratado
// (A1–A6) e por qual instrumento a gratuidade entrou (via jurídica). A segunda é a
// que a hipótese da tese observa: "concessão/permissão preexistente" quer dizer que a
// gratuidade foi enxertada no contrato de quem já estava lá.
const ARRANJO_ORDEM = ['A1 Prestação direta', 'A2 Locação só do veículo (L1)',
  'A3 Locação com motorista (L2, L3)', 'A4 Prestação de serviço',
  'A5 Concessão ou permissão', 'A6 Híbrido, terceirização ou empresa pública'];
const ARRANJO_COR = {
  'A1 Prestação direta': '#4F7FD4', 'A2 Locação só do veículo (L1)': '#6B8FC9',
  'A3 Locação com motorista (L2, L3)': '#8F9FBE', 'A4 Prestação de serviço': '#C9A33B',
  'A5 Concessão ou permissão': '#D05549',
  'A6 Híbrido, terceirização ou empresa pública': '#8a8f3a',
};
const VIA_COR = {
  'concessão/permissão preexistente': '#D05549', 'concessão/permissão nova, licitada': '#D98E3B',
  'contrato licitado': '#C9A33B', 'contratação emergencial ou dispensa': '#8a8f3a',
  'execução direta (sem contrato de operação)': '#4F7FD4',
  'empresa pública/autarquia municipal': '#6B8FC9',
  'adesão a ata de registro de preços': '#8F9FBE', 'convênio, consórcio ou cooperação': '#8F9FBE',
};

function renderArranjoPanel() {
  const el = document.getElementById('arranjoPanel');
  if (!el) return;
  const rows = subsetNoTz().filter(m => m.tz_bin === 'TZ' || m.tz_status === 'Parcial (ativa)');
  const dados = rows.map(arranjoFor);
  const n = rows.length;
  if (!n) { el.innerHTML = '<p class="sub">Nenhuma política de Tarifa Zero neste recorte.</p>'; return; }

  const conta = (campo) => {
    const c = {};
    let na = 0;
    for (const a of dados) {
      const v = a && a[campo];
      if (v) c[v] = (c[v] || 0) + 1; else na++;
    }
    return { c, na };
  };
  const bloco = (titulo, nota, campo, ordem, cores) => {
    const { c, na } = conta(campo);
    const chaves = (ordem || Object.keys(c).sort((a, b) => c[b] - c[a])).filter(k => c[k]);
    const max = Math.max(...chaves.map(k => c[k]), 1);
    const linhas = chaves.map(k => `
      <div class="arrlin">
        <div class="arrrot" title="${k}">${k}</div>
        <div class="arrbarra"><div class="arrfill" style="width:${(100 * c[k] / max).toFixed(1)}%;background:${(cores && cores[k]) || '#8F9FBE'};"></div></div>
        <div class="arrn">${c[k]} <span>${(100 * c[k] / (n - na) || 0).toFixed(0)}%</span></div>
      </div>`).join('');
    return `<div class="arrbloco">
      <h3>${titulo}</h3>
      <p class="sub">${nota}</p>
      ${linhas}
      <p class="sub" style="margin-top:7px;">${na ? `<b>${na}</b> de ${n} não ${na === 1 ? 'teve' : 'tiveram'} este campo apurado e ficam fora dos percentuais — não apurado não é zero.` : `Apurado em todos os ${n} casos do recorte.`}</p>
    </div>`;
  };

  const { c: cv } = conta('via');
  const pre = cv['concessão/permissão preexistente'] || 0;
  const { c: cp } = conta('prova');
  const comDoc = (cp.alta || 0);
  el.innerHTML = `
    <div class="arrgrid">
      ${bloco('O que foi contratado', 'Do arranjo mais público (a prefeitura opera) ao mais privado (o serviço é delegado por concessão).', 'a', ARRANJO_ORDEM, ARRANJO_COR)}
      ${bloco('Por qual instrumento a gratuidade entrou', 'A via jurídica diz se a política veio com contrato novo, com operação própria, ou enxertada num contrato que já existia.', 'via', null, VIA_COR)}
    </div>
    ${pre ? `<p class="sub" style="margin-top:10px;border-top:1px solid var(--border);padding-top:9px;">Em <b>${pre}</b> ${pre === 1 ? 'caso' : 'casos'} deste recorte a gratuidade entrou sobre uma <b>concessão que já existia</b>, com o operador que já estava lá — em geral por termo aditivo. É a forma de entrada que a tese acompanha com atenção, porque preserva o contrato e a receita de quem opera.</p>` : ''}
    <p class="sub" style="margin-top:7px;">Força da prova: <b>${comDoc}</b> ${comDoc === 1 ? 'codificação vem' : 'codificações vêm'} de cláusula de contrato, edital ou termo de referência lido; as demais, de fonte secundária ou da MUNIC. O objeto lido diz o que foi contratado, <b>não como o contrato é executado</b>.</p>`;
}

function renderRegua() {
  const el = document.getElementById('regua');
  if (!el) return;
  const rows = subsetNoTz();

  // Universal e encerrada vêm da régua da base-mestre; parcial vem da camada
  // (camadas_tz.json), que é a MESMA fonte do cartão "TZ parciais" do topo —
  // de propósito: a régua e o cartão têm de fechar o mesmo número, senão o leitor
  // vê 7 aqui e 43 ali e não tem como saber qual vale.
  const cont = Object.fromEntries(REGUA.map(r => [r.k, 0]));
  let encerradas = 0, universalSemSub = 0;
  for (const m of rows) {
    if (m.tz_status === 'Encerrada') { encerradas++; continue; }
    if (m.tz_bin === 'TZ') {
      const s = m.tz_regua_sub;
      if (s && s in cont && REGUA[REGUA_IDX[s]].grupo === 1) cont[s]++; else universalSemSub++;
      continue;
    }
    for (const c of camadasFor(m)) if (c.camada in cont) cont[c.camada]++;
  }
  const nProv = rows.reduce((a, m) => a + ((m.tz_bin === 'TZ' && m.tz_status !== 'Encerrada' && m.tz_prov) ? 1 : 0), 0);
  const nUniv = REGUA.filter(r => r.grupo === 1).reduce((a, r) => a + cont[r.k], 0) + universalSemSub;
  const nParc = countParciais(rows);
  const total = nUniv + nParc + encerradas;
  if (!total) { el.innerHTML = '<p class="sub">Nenhum caso classificado na régua neste recorte.</p>'; return; }

  const seg = (cor, n, titulo) => n
    ? `<div class="rgseg" style="flex:${n};background:${cor};" title="${titulo}"><span>${n}</span></div>` : '';
  const barra =
    REGUA.filter(r => r.grupo === 1).map(r => seg(r.cor, cont[r.k], `${r.k} · ${r.rot} — ${cont[r.k]} caso(s): ${r.desc}`)).join('')
    + seg('#8a8f3a', universalSemSub, `Universal, subtipo ainda não apurado — ${universalSemSub} caso(s)`)
    + REGUA.filter(r => r.grupo === 2).map(r => seg(r.cor, cont[r.k], `${r.k} · ${r.rot} — ${cont[r.k]} caso(s): ${r.desc}`)).join('')
    + seg('#6b7280', encerradas, `3 · Encerradas — ${encerradas} caso(s): a política parou`);

  const chip = r => cont[r.k]
    ? `<span class="rgchip" title="${r.desc}"><i style="background:${r.cor}"></i>${r.k} ${r.rot} <b>${cont[r.k]}</b></span>` : '';
  const somaCamadas = REGUA.filter(r => r.grupo === 2).reduce((a, r) => a + cont[r.k], 0);

  el.innerHTML = `
    <div class="rgtopo">
      <span class="rglado">← sem portão de acesso</span>
      <span class="rglado dir">portão condiciona quem ou quando viaja →</span>
    </div>
    <div class="rgbar">${barra}</div>
    <div class="rgchips">
      <span class="rggrupo">1 Universal <b>${nUniv}</b></span>${REGUA.filter(r => r.grupo === 1).map(chip).join('')}${universalSemSub ? `<span class="rgchip"><i style="background:#8a8f3a"></i>subtipo a apurar <b>${universalSemSub}</b></span>` : ''}
      <span class="rggrupo sep">2 Parcial <b>${nParc}</b></span>${REGUA.filter(r => r.grupo === 2).map(chip).join('')}
      ${encerradas ? `<span class="rggrupo sep">3 Encerradas <b>${encerradas}</b></span>` : ''}
    </div>
    ${somaCamadas !== nParc ? `<p class="sub" style="margin-top:6px;">Os subtipos somam ${somaCamadas} e os municípios parciais são ${nParc}: um mesmo município pode acumular mais de uma camada (Belo Horizonte e Brasília, por exemplo), e nesses casos ele conta uma vez como município e uma vez em cada camada.</p>` : ''}
    ${nProv ? `<p class="sub" style="margin-top:6px;">◇ <b>${nProv}</b> ${nProv === 1 ? 'caso universal está' : 'casos universais estão'} na barra pela <b>hipótese</b> de um pedido de acesso à informação ainda sem resposta, não por documento lido. A resposta pode trocar o subtipo, e a contagem com ela.</p>` : ''}
    <p class="sub" style="margin-top:8px;border-top:1px solid var(--border);padding-top:8px;">A régua não começa do zero. Antes do 1a existe um <b>piso nacional</b>, que vale em todo sistema urbano do país e por isso não distingue caso nenhum: a gratuidade a quem tem <b>65 anos ou mais</b> (Constituição, art. 230, § 2º; Estatuto da Pessoa Idosa), que alcança 11,0% da população brasileira, e, desde as eleições de 2024, a <b>gratuidade no dia de votação</b>, que o STF tornou obrigação do poder público e que alcança 76,0% da população adulta. O que cada município decide começa acima disso.</p>`;
}

// ---------- 3.3: TZ por região e por UF (pendente desde v0.3) ----------
// Proporção de municípios com histórico de TZ universal DENTRO de cada categoria.
// Mesma leitura do painel "% por eixo", em dois recortes territoriais que faltavam.
// O n de cada barra vai junto: uma UF com 2 municípios TZ em 20 dá 10%, e sem o n
// isso se lê como se fosse comparável a São Paulo.
// 23/10/2026 — redesenhado a pedido do autor ("essa visualização está ruim"). Três
// problemas do desenho anterior: (1) duas colunas de alturas muito diferentes (5 regiões
// ao lado de 27 UFs), com um vazio grande à esquerda; (2) metade da lista era barra
// zerada — 13 UFs sem nenhum caso ocupavam a mesma área das que têm; (3) contava o
// "histórico" (ativas + encerradas), enquanto a tese e o resto do painel contam a
// camada 1 — por isso o Sudeste aparecia com 118 e a tese diz 113.
// Agora: UFs agrupadas dentro da sua região, a barra mede QUANTOS casos (a leitura da
// Seção 5.4: quatro estados reúnem 77% dos casos) e o texto diz que FRAÇÃO dos
// municípios da UF isso representa (a leitura que pôs o RJ em destaque). UFs sem caso
// viram uma linha só.
const ORDEM_REGIAO = ['Sudeste', 'Sul', 'Centro-Oeste', 'Nordeste', 'Norte'];
function renderRegiaoUf() {
  const el = document.getElementById('regiaoUf');
  if (!el) return;
  const rows = subsetNoTz();
  const pctBR = v => (v).toFixed(1).replace('.', ',') + '%';

  const reg = new Map();   // regiao -> { tot, tz, ufs: Map(uf -> {tot, tz}) }
  for (const m of rows) {
    if (!m.regiao || !m.uf) continue;
    let r = reg.get(m.regiao);
    if (!r) { r = { tot: 0, tz: 0, ufs: new Map() }; reg.set(m.regiao, r); }
    let u = r.ufs.get(m.uf);
    if (!u) { u = { tot: 0, tz: 0 }; r.ufs.set(m.uf, u); }
    const tz = m.tz_status === 'Ativa';
    r.tot++; u.tot++;
    if (tz) { r.tz++; u.tz++; }
  }
  const totTZ = [...reg.values()].reduce((a, r) => a + r.tz, 0);
  if (!totTZ) { el.innerHTML = '<div class="empty">Nenhum município com Tarifa Zero universal neste recorte.</div>'; return; }
  const maxUf = Math.max(...[...reg.values()].flatMap(r => [...r.ufs.values()].map(u => u.tz)), 1);

  const zeradas = [];
  let html = '';
  for (const nome of ORDEM_REGIAO) {
    const r = reg.get(nome);
    if (!r) continue;
    const ufs = [...r.ufs.entries()].filter(([, u]) => u.tz > 0).sort((a, b) => b[1].tz - a[1].tz || b[1].tz / b[1].tot - a[1].tz / a[1].tot);
    for (const [uf, u] of r.ufs) if (!u.tz) zeradas.push(uf);
    if (!r.tz) continue;
    html += `<div class="rufreg">
      <div class="rufcab"><b>${nome}</b><span><b>${r.tz}</b> ${r.tz === 1 ? 'município' : 'municípios'} · ${pctBR(100 * r.tz / totTZ)} dos casos · ${pctBR(100 * r.tz / r.tot)} dos ${fmtNum(r.tot)} municípios da região</span></div>
      ${ufs.map(([uf, u]) => `<div class="rufuf" title="${uf}: ${u.tz} de ${u.tot} municípios com Tarifa Zero universal">
        <div class="rufsig">${uf}</div>
        <div class="ruftrack"><div class="ruffill" style="width:${(100 * u.tz / maxUf).toFixed(1)}%;"></div></div>
        <div class="rufn"><b>${u.tz}</b></div>
        <div class="rufpct">${pctBR(100 * u.tz / u.tot)} <span>dos ${fmtNum(u.tot)}</span></div>
      </div>`).join('')}
    </div>`;
  }
  if (zeradas.length) {
    zeradas.sort();
    html += `<p class="rufzero"><b>Sem Tarifa Zero universal neste recorte</b> (${zeradas.length} ${zeradas.length === 1 ? 'UF' : 'UFs'}): ${zeradas.join(', ')}.</p>`;
  }
  el.innerHTML = `<div class="rufleg"><span><i></i>a barra mede <b>quantos</b> municípios têm Tarifa Zero universal</span><span>o percentual diz que <b>fração</b> dos municípios da UF isso representa</span></div>${html}`;
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
  if (leg) leg.innerHTML = `<span><i style="background:var(--amarelo)"></i>TZ universal (${tz.filter(m => m.tz_status === 'Ativa').length})</span>
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
  { chave: 'Cardozo et al. 2024', ref: 'CARDOZO, Rodrigo Juan Martins; DE MELO, Iury Ribeiro; DA LUZ, Fernanda Catarina Ribeiro; BRASILEIRO, Anísio; DE ANDRADE, Maurício Oliveira. Tarifa zero no Brasil: uma análise exploratória das experiências atuais. In: CONGRESSO DE PESQUISA E ENSINO EM TRANSPORTES, 38., 2024, Florianópolis. <i>Anais</i> [...]. Florianópolis: ANPET, 2024.' },
  { chave: 'Cardozo et al. 2025', ref: 'CARDOZO, Rodrigo Juan Martins; DE MELO, Iury Ribeiro; DA LUZ, Fernanda Catarina Ribeiro; BRASILEIRO, Anísio. Impactos da Tarifa Zero na motorização urbana: análise multivariada de 44 experiências brasileiras. In: CONGRESSO DE PESQUISA E ENSINO EM TRANSPORTES (ANPET), 39., 2025, Goiânia. <i>Anais</i> [...]. Goiânia: ANPET, 2025. p. 1276-1281.' },
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
let tzSort = { k: 'nome', dir: 1 };   // 24/10/2026: alfabética por padrão (quem procura uma cidade)
const fontesExpandedIds = new Set();
function renderTZTable() {
  let rows = STATS.tz_list.concat(PARCIAL_LIST).filter(r => {
    if (state.uf && r.uf !== state.uf) return false;
    if (state.faixa && r.faixa_pop !== state.faixa) return false;
    if (state.regic && String(r.regic_nivel) !== state.regic) return false;
    if (state.arranjo && r.tipo_arranjo !== state.arranjo) return false;
    return true;
  });
  document.querySelectorAll('#tzTable th').forEach(th => { th.dataset.ord = th.dataset.k === tzSort.k ? (tzSort.dir > 0 ? '▲' : '▼') : ''; });
  rows = rows.slice().sort((a, b) => {
    if (tzSort.k === 'nome') return tzSort.dir * String(a.nome).localeCompare(String(b.nome), 'pt-BR');
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
      <td${(r.tz_ano != null && r.tz_ano_txt == null) ? ` title="base-mestre: ${String(r.tz_ano).replace(/"/g, '&quot;')}"` : ''}>${r.tz_ano_txt ?? (r.tz_ano != null ? '<span style="color:var(--muted);">a apurar</span>' : '—')}</td><td>${r.regic_label ?? '—'}</td><td>${r.tipo_arranjo ?? '—'}</td>
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
  const buscaEAbre = () => { if (selecionaMunicipioBuscado()) abrirFicha(munSelecionado); };
  inputBusca.addEventListener('change', buscaEAbre);
  inputBusca.addEventListener('keydown', e => { if (e.key === 'Enter') buscaEAbre(); });
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
  fecharFicha();
  resetZoom();
  render(); renderTZTable();
  atualizaBotaoLimpar();
}

if (btnLimpar) btnLimpar.addEventListener('click', limparTudo);

document.querySelectorAll('#tzTable th').forEach(th => {
  th.addEventListener('click', () => {
    const k = th.dataset.k;
    tzSort.dir = (tzSort.k === k) ? -tzSort.dir : (['nome', 'uf', 'tz_status', 'regic_label', 'tipo_arranjo'].includes(k) ? 1 : -1);
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
  abrirFicha(m);
});

// ---------- 12.10: a ficha lateral (Apêndice D da tese) ----------
// Formato decidido pelo autor em 23/10/2026: a ficha de cada uma das 187 políticas abre
// num painel lateral ao selecionar o município (no mapa, na tabela ou pela busca, ao
// confirmar o nome). O card continua com os dados e o mapa; a ficha traz o que a tese
// documenta caso a caso. O conteúdo já chega filtrado de build_fichas.py: sem régua
// analítica caso a caso, sem grupos econômicos e sem CNPJ.
const esc = t => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const linkifica = t => esc(t).replace(/(https?:\/\/[^\s)]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
function fichaFor(m) { return (m && FICHAS.fichas[String(m.id)]) || null; }

function renderFichaBloco(b) {
  // bullets viram lista; o resto, parágrafos. A lista de obras ("Onde aparece") é longa
  // e de consulta: vai recolhida.
  let html = '', lista = [], obras = null;
  const solta = () => { if (lista.length) { html += `<ul>${lista.map(x => `<li>${linkifica(x)}</li>`).join('')}</ul>`; lista = []; } };
  for (const t of b.itens) {
    if (/^Onde aparece/.test(t)) { solta(); obras = []; continue; }
    if (obras && t.startsWith('•')) { obras.push(t.replace(/^•\s*/, '')); continue; }
    if (t.startsWith('•')) { lista.push(t.replace(/^•\s*/, '')); continue; }
    solta();
    const m = t.match(/^([A-ZÀ-Ú][^.:]{2,48}[.:])\s+(.*)$/);
    html += m ? `<p><b>${esc(m[1])}</b> ${linkifica(m[2])}</p>` : `<p>${linkifica(t)}</p>`;
  }
  solta();
  if (obras && obras.length) {
    html += `<details><summary>Onde o caso aparece na literatura (${obras.length} ${obras.length === 1 ? 'obra' : 'obras'})</summary>
      <p style="color:var(--muted);font-size:11.5px;margin-top:6px;">Menções nos fichamentos da revisão sistemática — notas de leitura do autor, não os textos originais. Uma ou duas menções não distinguem caso analisado de nome numa lista.</p>
      <ul>${obras.map(x => `<li>${esc(x)}</li>`).join('')}</ul></details>`;
  }
  return html;
}

function abrirFicha(m) {
  const f = fichaFor(m);
  const el = document.getElementById('fichaLateral');
  if (!el) return;
  if (!f) { fecharFicha(); return; }
  document.getElementById('flNome').textContent = `${m.nome} – ${m.uf}`;
  const sub = (m.tz_regua_sub && REGUA_IDX[m.tz_regua_sub] != null) ? REGUA[REGUA_IDX[m.tz_regua_sub]] : null;
  document.getElementById('flTags').innerHTML =
    `<span class="tag ${m.tz_status === 'Ativa' ? 'ativa' : m.tz_status === 'Encerrada' ? 'encerrada' : 'parcial'}">${esc(m.tz_status)}</span>`
    + (sub ? ` <span class="tag parcial" style="background:${sub.cor};color:rgba(0,0,0,.78);">${sub.k} ${sub.rot}${m.tz_prov ? ' ◇' : ''}</span>` : '');
  const resumo = f.resumo.length
    ? `<h3>Ficha-resumo</h3><table class="fl-resumo">${f.resumo.map(([k, v]) => `<tr><td>${esc(k)}</td><td>${linkifica(v)}</td></tr>`).join('')}</table>` : '';
  const blocos = f.blocos.map(b => {
    const corpo = renderFichaBloco(b);
    if (!corpo) return '';
    if (b.t === 'Literatura e fontes') return `<details><summary>${esc(b.t)}</summary><div style="margin-top:8px;">${corpo}</div></details>`;
    return `<h3>${esc(b.t)}</h3>${corpo}`;
  }).join('');
  document.getElementById('flCorpo').innerHTML = resumo + blocos + `
    <div class="fl-nota"><b>Documento de trabalho da tese</b> (Apêndice D, versão ${esc(FICHAS.versao)}). Cada classificação remete a um documento datado. Campo vazio é dado <b>não apurado</b>, não fenômeno inexistente. Por decisão do autor, ficam fora desta ficha a leitura de contrapartida e a posição na régua analítica (até a defesa da tese) e os grupos econômicos (que têm página própria, a <a href="rede-ge.html">Rede de empresas</a>).</div>`;
  el.hidden = false;
  el.querySelector('.fl-corpo').scrollTop = 0;
}
function fecharFicha() {
  const el = document.getElementById('fichaLateral');
  if (el) el.hidden = true;
}
document.getElementById('flFecha')?.addEventListener('click', fecharFicha);
document.addEventListener('keydown', e => { if (e.key === 'Escape') fecharFicha(); });
document.getElementById('detail')?.addEventListener('click', e => {
  if (e.target.closest('.btn-ficha')) abrirFicha(munSelecionado);
});

// ---------- abas (23/10/2026) ----------
// O painel misturava dados para explorar (mapa, ficha, tabela) com a comparação
// TZ × Não-TZ e com o panorama, intercalados numa rolagem só. Separado em quatro
// áreas; o filtro fica fixo acima das abas e vale para todas. A aba aberta fica no
// endereço (#explorar, #comparar...), para um link levar direto a ela.
const ABAS = ['panorama', 'explorar', 'comparar', 'sobre'];
function abreAba(nome, semHash) {
  if (!ABAS.includes(nome)) nome = 'panorama';
  for (const a of ABAS) {
    const pane = document.getElementById('tab-' + a);
    const btn = document.getElementById('tabbtn-' + a);
    const on = a === nome;
    if (pane) pane.hidden = !on;
    if (btn) { btn.classList.toggle('on', on); btn.setAttribute('aria-selected', on ? 'true' : 'false'); }
  }
  if (!semHash && location.hash !== '#' + nome) history.replaceState(null, '', '#' + nome);
}
document.querySelectorAll('.tabbtn').forEach(b => b.addEventListener('click', () => abreAba(b.dataset.tab)));
window.addEventListener('hashchange', () => abreAba(location.hash.slice(1), true));
abreAba(location.hash.slice(1), true);

// ---------- celular (4.3, 23/10/2026) ----------
// Na primeira verificação formal no celular, o leitor rolava 1.271 px — o texto de
// apresentação inteiro e seis filtros empilhados — antes de ver a primeira aba. No
// celular, a apresentação abre resumida (com "ler mais") e os filtros abrem fechados,
// com a contagem de filtros ativos no título; no computador nada muda.
const mqCel = window.matchMedia('(max-width:640px)');
function ajustaCelular() {
  const box = document.getElementById('filtrosBox');
  if (box) box.open = !mqCel.matches;
  const ht = document.querySelector('.htext');
  const bt = document.getElementById('lerMais');
  if (ht && bt) {
    ht.classList.add('compacto');   // 24/10/2026: resumida em qualquer tela (parecer externo)
    bt.hidden = false;
    bt.textContent = 'Ler mais sobre a pesquisa ▾';
  }
}
document.getElementById('lerMais')?.addEventListener('click', () => {
  const ht = document.querySelector('.htext');
  const aberto = ht.classList.toggle('compacto') === false;
  document.getElementById('lerMais').textContent = aberto ? 'Recolher ▴' : 'Ler mais sobre a pesquisa ▾';
});
mqCel.addEventListener('change', ajustaCelular);
ajustaCelular();

// ---------- recorte ativo, visível em qualquer aba ----------
// Com abas, o risco é o leitor esquecer que há um filtro ligado numa aba que não está
// vendo. Cada filtro ativo vira uma etiqueta removível na barra fixa.
const ROTULO_FILTRO = {
  uf: ['ufFilter', 'UF'], faixa: ['faixaFilter', 'Porte'], regic: ['regicFilter', 'Hierarquia'],
  modelo: ['modeloFilter', 'Prestação'], tzFilter: ['tzFilter', 'Recorte'], camada: ['camadaFilter', 'Régua'],
  arranjo: [null, 'Arranjo'],
};
function renderRecorte() {
  const el = document.getElementById('recorteChips');
  if (!el) return;
  const chips = [];
  for (const k in ROTULO_FILTRO) {
    if (!state[k]) continue;
    const [selId, rot] = ROTULO_FILTRO[k];
    const sel = selId && document.getElementById(selId);
    const txt = sel && sel.selectedOptions[0] ? sel.selectedOptions[0].textContent : state[k];
    chips.push(`<button class="chip" data-k="${k}" title="Remover este filtro">${rot}: <b>${txt}</b> ✕</button>`);
  }
  el.innerHTML = chips.length ? chips.join('') : '<span class="chip-vazio">Brasil inteiro, sem filtro</span>';
  const res = document.getElementById('filtrosResumo');
  if (res) res.textContent = chips.length ? `Filtros · ${chips.length} ${chips.length === 1 ? 'ativo' : 'ativos'}` : 'Filtros';
}
document.getElementById('recorteChips')?.addEventListener('click', e => {
  const c = e.target.closest('.chip');
  if (!c) return;
  const k = c.dataset.k;
  state[k] = '';
  const selId = ROTULO_FILTRO[k][0];
  if (selId) { const sel = document.getElementById(selId); if (sel) sel.value = ''; }
  render(); renderTZTable(); atualizaBotaoLimpar();
});

document.getElementById('porteCtrl')?.addEventListener('change', renderBars);

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
    inner = `<b>${m.nome} – ${m.uf} ${m.tz_status === 'Ativa' ? '· TZ universal' : '· TZ encerrada'}</b>
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
      cadunico_cobertura: m.cadunico_cobertura != null ? fmtNum(m.cadunico_cobertura) + '%' : 'sem dado',
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
  abrirFicha(m);       // 12.10: a ficha lateral abre na seleção (fecha se o município não tem ficha)
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

renderReferenciasAbnt();
renderTZTable();
render(); // desenha mapa, legenda, barras, cards, linha do tempo e score de população
renderCurvaPorte();
// fim da montagem: some o aviso de carregamento (head.html)
document.getElementById('carregando')?.remove();
