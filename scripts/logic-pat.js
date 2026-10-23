// logic-pat.js — aba "Além do ônibus" da Rede de empresas (rede-ge.html), Seção 6.4 da tese.
// Até 23/10/2026 era a página patrimonio.html; o autor juntou as duas ("queria que fossem a
// mesma página"). montar_rede_ge.sh embrulha este arquivo numa função própria, para os nomes
// daqui não colidirem com os de logic-ge.js; o que a outra aba usa sai por window.PAT.
// FRONTEIRA DE EXPOSIÇÃO: nenhum nome de pessoa, CPF ou CNPJ; a pessoa que liga a holding à
// empresa de outro setor nunca aparece (só a contagem de sócios em comum); razão social com
// nome de pessoa chega mascarada do build. Vínculo de sócio não é controle.
'use strict';
const P = JSON.parse(document.getElementById('data-pat').textContent);
const fmt = v => Number(v).toLocaleString('pt-BR');
const esc = t => String(t ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const MASC = '[razão social com nome de pessoa]';
const nomeHtml = n => !n ? '<span class="mask">[sem razão social na base]</span>' : n === MASC ? `<span class="mask">${MASC}</span>` : esc(n);
// nome de mercado repetido (ramos da mesma família) leva o rótulo do cálculo entre parênteses
const _rep = {}; for (const g in P.nomes) { const m = P.nomes[g].mercado; if (m) _rep[m] = (_rep[m] || 0) + 1; }
const rotG = g => { const x = P.nomes[g]; if (!x) return g; return x.mercado ? (_rep[x.mercado] > 1 ? `${x.mercado} (${x.rot})` : x.mercado) : x.rot; };
const HUES = ['#F5E400', '#FF8A3D', '#6FBE44', '#2EC4C4', '#B57CFF', '#7FA8FF', '#E85DB0', '#C9A227', '#9BD46A', '#FF6F61', '#5AD1A0', '#62B0E8'];
const SETORES = P.setores.map(s => s.s);
const corSetor = s => { const i = SETORES.indexOf(s); return i >= 0 && i < HUES.length ? HUES[i] : '#6b6b78'; };
let soAtivas = false, setorFiltro = '', grupoSel = null;
const tooltip = document.getElementById('tooltip');
function tip(e, h) { tooltip.innerHTML = h; tooltip.style.display = 'block'; tooltip.style.left = Math.min(e.clientX + 14, innerWidth - 260) + 'px'; tooltip.style.top = (e.clientY + 14) + 'px'; }

// ---------- achados ----------
function renderFind() {
  const r = P.resumo, f = r.formas;
  const itens = [
    [fmt(r.holdings), `holdings fora dos grupos são sócias das empresas de ônibus (${fmt(f['Sociedade limitada'] || 0)} limitadas, ${fmt(f['Sociedade anônima fechada'] || 0)} sociedades anônimas fechadas, ${fmt(f['Sociedade simples limitada'] || 0)} sociedades simples) — nenhuma companhia aberta, nenhum fundo`],
    [fmt(r.cruzadas), `empresas dos próprios grupos são sócias de outras empresas de ônibus: dos ${fmt(r.cnpj_pj)} CNPJs que aparecem como sócio pessoa jurídica`],
    [fmt(r.n_emp), `empresas de 28 setores, fora do transporte coletivo, têm sócio em comum com as holdings dos grupos — ${fmt(r.n_ativas)} ativas`],
    [`${fmt(r.n_fin_hold)} de ${fmt(r.n_fin)}`, `das "financeiras" são, na verdade, outras holdings; ${fmt(r.n_fin - r.n_fin_hold)} são finanças em sentido estrito — banco, securitizadora, crédito, seguro, gestora`],
  ];
  document.getElementById('patFind').innerHTML = itens.map(([b, s]) => `<div><b>${b}</b><span>${s}</span></div>`).join('');
  document.getElementById('cadH').textContent = `${fmt(r.holdings)} holdings`;
  document.getElementById('cadE').textContent = `${fmt(r.n_emp)} empresas, 28 setores`;
}

// ---------- setores ----------
function renderSetores() {
  const lin = P.setores.map(s => ({ ...s, v: soAtivas ? s.a : s.n })).sort((a, b) => b.v - a.v);
  const max = Math.max(...lin.map(s => s.n));
  document.getElementById('patSetores').innerHTML = lin.map(s => `<div class="setbar${s.s === setorFiltro ? ' on' : ''}" data-s="${esc(s.s)}">
    <div class="r" title="${esc(s.s)}">${esc(s.s)}</div>
    <div class="t">${soAtivas ? '' : `<div class="f" style="width:${(100 * s.n / max).toFixed(1)}%;background:${corSetor(s.s)}"></div>`}<div class="f a" style="width:${(100 * s.a / max).toFixed(1)}%;background:${corSetor(s.s)}"></div></div>
    <div class="n">${soAtivas ? fmt(s.a) : `${fmt(s.n)} <span class="muted">(${fmt(s.a)})</span>`}</div></div>`).join('');
}
document.getElementById('patSetores').addEventListener('click', e => {
  const b = e.target.closest('.setbar'); if (!b) return;
  setorFiltro = setorFiltro === b.dataset.s ? '' : b.dataset.s; document.getElementById('patSetor').value = setorFiltro;
  renderSetores(); if (grupoSel) mostraGrupo(grupoSel, false);
});
document.getElementById('soAtivas').addEventListener('change', e => { soAtivas = e.target.checked; renderSetores(); renderTabela(); if (grupoSel) mostraGrupo(grupoSel, false); });

// ---------- rede do grupo (força simples, zoom e arraste) ----------
const svg = document.getElementById('patSvg'), NS = 'http://www.w3.org/2000/svg';
const V = { k: 1, tx: 0, ty: 0, W: 600, H: 500, nos: [], ars: [] };
const el = (t, a) => { const x = document.createElementNS(NS, t); for (const k in a) x.setAttribute(k, a[k]); return x; };
function layout(nos, ars) {
  const n = nos.length, L = n > 120 ? 26 : 40;
  nos.forEach((o, i) => { const a = i * 2.39996, r = 8 * Math.sqrt(i + 1); o.x = Math.cos(a) * r; o.y = Math.sin(a) * r; });
  let T = L * 3;
  for (let it = 0; it < 260; it++) {
    for (const o of nos) { o.dx = 0; o.dy = 0; }
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
      const p = nos[i], q = nos[j]; let dx = p.x - q.x, dy = p.y - q.y; const d = Math.hypot(dx, dy) || .01, f = L * L / d;
      dx /= d; dy /= d; p.dx += dx * f; p.dy += dy * f; q.dx -= dx * f; q.dy -= dy * f; }
    for (const [a, b] of ars) { const p = nos[a], q = nos[b]; let dx = p.x - q.x, dy = p.y - q.y; const d = Math.hypot(dx, dy) || .01, f = d * d / L;
      dx /= d; dy /= d; p.dx -= dx * f; p.dy -= dy * f; q.dx += dx * f; q.dy += dy * f; }
    for (const o of nos) { o.dx -= o.x * .03 * L; o.dy -= o.y * .03 * L; const d = Math.hypot(o.dx, o.dy) || 1, s = Math.min(d, T); o.x += o.dx / d * s; o.y += o.dy / d * s; }
    T = Math.max(.5, T * .98);
  }
}
function desenhaRede() {
  const g = el('g', { transform: `translate(${V.tx},${V.ty}) scale(${V.k})` });
  for (const [a, b, w] of V.ars) { const p = V.nos[a], q = V.nos[b];
    g.appendChild(el('line', { x1: p.x, y1: p.y, x2: q.x, y2: q.y, stroke: p.t === 'g' ? '#F5E400' : '#8a8a98', 'stroke-opacity': p.t === 'g' ? .6 : .35, 'stroke-width': (.7 + Math.log1p(w || 1) * .6) / Math.sqrt(V.k) })); }
  V.nos.forEach((o, i) => {
    g.appendChild(el('circle', { cx: o.x, cy: o.y, r: o.r, fill: o.cor, 'fill-opacity': o.baixa ? .35 : .92, stroke: '#0E0E10', 'stroke-width': 1 / V.k, 'data-i': i, style: 'cursor:default' }));
    if (o.t === 'g' || (o.t === 'h' && V.k > 1.5) || V.k > 2.6) { const t = el('text', { x: o.x + o.r + 3 / V.k, y: o.y + 3.5 / V.k, 'font-size': (o.t === 'g' ? 13 : 10) / V.k, 'font-weight': o.t === 'g' ? 700 : 400 }); t.textContent = o.rot; g.appendChild(t); }
  });
  svg.replaceChildren(g);
}
function enquadra() {
  const r = svg.getBoundingClientRect(); V.W = r.width || 600; V.H = r.height || 500; svg.setAttribute('viewBox', `0 0 ${V.W} ${V.H}`);
  if (!V.nos.length) return;
  const x0 = Math.min(...V.nos.map(o => o.x - o.r)), x1 = Math.max(...V.nos.map(o => o.x + o.r)) + 80, y0 = Math.min(...V.nos.map(o => o.y - o.r)), y1 = Math.max(...V.nos.map(o => o.y + o.r));
  V.k = Math.min(3, (V.W - 30) / (x1 - x0), (V.H - 30) / (y1 - y0)); V.tx = (V.W - V.k * (x0 + x1)) / 2; V.ty = (V.H - V.k * (y0 + y1)) / 2; desenhaRede();
}
function zoom(px, py, f) { const k = Math.min(10, Math.max(.2, V.k * f)); f = k / V.k; V.tx = px - (px - V.tx) * f; V.ty = py - (py - V.ty) * f; V.k = k; desenhaRede(); }
const pt = e => { const r = svg.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
svg.addEventListener('wheel', e => { e.preventDefault(); const [x, y] = pt(e); zoom(x, y, Math.exp(-e.deltaY * .0016)); }, { passive: false });
let arr = null; const toques = new Map();
svg.addEventListener('pointerdown', e => { svg.setPointerCapture(e.pointerId); toques.set(e.pointerId, pt(e));
  if (toques.size === 2) { const [a, b] = [...toques.values()]; arr = { pin: Math.hypot(a[0] - b[0], a[1] - b[1]) }; } else arr = { p: pt(e), tx: V.tx, ty: V.ty }; });
svg.addEventListener('pointermove', e => {
  if (toques.has(e.pointerId)) toques.set(e.pointerId, pt(e));
  if (arr?.pin && toques.size === 2) { const [a, b] = [...toques.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]); zoom((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, d / arr.pin); arr.pin = d; return; }
  if (arr?.p) { const p = pt(e); V.tx = arr.tx + p[0] - arr.p[0]; V.ty = arr.ty + p[1] - arr.p[1]; desenhaRede(); return; }
  const c = e.target.closest('circle'); if (!c) { tooltip.style.display = 'none'; return; }
  const o = V.nos[+c.dataset.i]; tip(e, o.tip);
});
const solta = e => { toques.delete(e.pointerId); if (!toques.size) arr = null; };
svg.addEventListener('pointerup', solta); svg.addEventListener('pointercancel', solta);
svg.addEventListener('mouseleave', () => { tooltip.style.display = 'none'; });
document.getElementById('pzMais').onclick = () => zoom(V.W / 2, V.H / 2, 1.4);
document.getElementById('pzMenos').onclick = () => zoom(V.W / 2, V.H / 2, 1 / 1.4);
document.getElementById('pzFit').onclick = enquadra;
addEventListener('resize', enquadra);

// ---------- o grupo ----------
const passa = e => (!soAtivas || e.sit === 'ativa') && (!setorFiltro || e.setor === setorFiltro);
function mostraGrupo(g, rolar = true) {
  grupoSel = g; const d = P.grupos[g]; if (!d) return;
  document.getElementById('patBusca').value = rotG(g);
  const hs = d.h, hset = new Set(hs);
  const es = d.e.filter(i => passa(P.empresas[i]));
  const eset = new Set(es);
  // rede: grupo -> holdings -> empresas
  const nos = [{ t: 'g', rot: rotG(g), r: 11, cor: '#F5E400', tip: `<b>${esc(rotG(g))}</b>${P.nomes[g].rot !== rotG(g) ? `<div class="muted">${esc(P.nomes[g].rot)}</div>` : ''}` }];
  const ih = new Map(), ie = new Map(), ars = [];
  for (const h of hs) { const H = P.holdings[h]; ih.set(h, nos.length);
    nos.push({ t: 'h', rot: H.nome === MASC ? 'holding (nome de pessoa)' : (H.nome || 'holding'), r: 6.5, cor: '#FF2D6B',
      tip: `<b>${nomeHtml(H.nome)}</b><div class="muted">holding · ${esc(H.forma)}${H.grupos.length > 1 ? ` · sócia em ${H.grupos.length} grupos` : ''}</div>` });
    ars.push([0, nos.length - 1, 2]); }
  for (const [h, i, w] of P.lig) { if (!hset.has(h) || !eset.has(i)) continue;
    if (!ie.has(i)) { const E = P.empresas[i]; ie.set(i, nos.length);
      nos.push({ t: 'e', rot: E.nome === MASC ? '' : (E.nome || ''), r: 4, cor: corSetor(E.setor), baixa: E.sit !== 'ativa',
        tip: `<b>${nomeHtml(E.nome)}</b><div class="tt-grid"><span>Setor</span><span>${esc(E.setor)}</span><span>UF</span><span>${E.uf || '—'}</span><span>Situação</span><span>${E.sit}</span>${E.grupos.length > 1 ? `<span>Grupos</span><span>${E.grupos.length}</span>` : ''}</div>` }); }
    ars.push([ih.get(h), ie.get(i), w]); }
  layout(nos, ars); V.nos = nos; V.ars = ars; enquadra();
  // kpis
  const set = {}; for (const i of es) { const s = P.empresas[i].setor; set[s] = (set[s] || 0) + 1; }
  const top = Object.entries(set).sort((a, b) => b[1] - a[1]);
  const fins = es.filter(i => P.empresas[i].setor.startsWith('Finanças')).length;
  document.getElementById('patVerRede').innerHTML = `<a href="#" class="ponte-aba" data-aba="controle" data-g="${g}">ver ${esc(rotG(g))} na rede e no mapa →</a>`;
  document.getElementById('patKpi').innerHTML = [[hs.length, 'holdings sócias das empresas do grupo'], [es.length, `empresas de outros setores${setorFiltro ? ' (setor filtrado)' : ''}${soAtivas ? ', ativas' : ''}`], [top.length, 'setores'], [fins, 'finanças em sentido estrito']]
    .map(([b, s]) => `<div><b>${fmt(b)}</b><span>${s}</span></div>`).join('');
  // lista por setor
  const porSetor = {}; for (const i of es) (porSetor[P.empresas[i].setor] = porSetor[P.empresas[i].setor] || []).push(P.empresas[i]);
  const ordem = Object.keys(porSetor).sort((a, b) => porSetor[b].length - porSetor[a].length);
  document.getElementById('patLista').innerHTML =
    `<h4>Holdings sócias (${hs.length})</h4><ul>${hs.map(h => { const H = P.holdings[h]; return `<li>${nomeHtml(H.nome)} <span class="muted">— ${esc(H.forma)}${H.grupos.length > 1 ? `; também sócia de ${H.grupos.filter(x => x !== g).map(x => `<a href="#" class="glink" data-g="${x}">${esc(rotG(x))}</a>`).join(', ')}` : ''}</span></li>`; }).join('')}</ul>`
    + (ordem.length ? ordem.map(s => `<h4><i style="background:${corSetor(s)}"></i>${esc(s)} (${porSetor[s].length})</h4><ul>${porSetor[s].sort((a, b) => (a.sit !== 'ativa') - (b.sit !== 'ativa') || String(a.nome).localeCompare(String(b.nome))).map(E => `<li class="${E.sit !== 'ativa' ? 'baixa' : ''}">${nomeHtml(E.nome)} <span class="muted">${E.uf || ''}</span>${E.sit !== 'ativa' ? `<span class="sitag">${E.sit}</span>` : ''}${E.grupos.length > 1 ? ` <span class="muted">· também: ${E.grupos.filter(x => x !== g).slice(0, 3).map(x => `<a href="#" class="glink" data-g="${x}">${esc(rotG(x))}</a>`).join(', ')}</span>` : ''}</li>`).join('')}</ul>`).join('')
      : '<p class="sub" style="margin-top:8px;">Nenhuma empresa de outro setor levantada para os sócios das holdings deste grupo' + (setorFiltro || soAtivas ? ' com o filtro atual' : '') + '. O 2º nível foi levantado só a partir das holdings que ligam os grupos médios e grandes (ver notas).</p>');
  if (rolar) document.getElementById('patGrupo').scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (!document.getElementById('tab-alem')?.hidden) history.replaceState(null, '', '#alem-' + g);
}
document.addEventListener('click', e => { const a = e.target.closest('.glink'); if (a) { e.preventDefault(); mostraGrupo(a.dataset.g); } });
(function busca() {
  const ROT = new Map(); for (const g in P.grupos) { ROT.set(rotG(g), g); ROT.set(P.nomes[g].rot, g); }
  document.getElementById('patBuscaList').innerHTML = [...ROT.keys()].sort((a, b) => a.localeCompare(b, 'pt-BR')).map(k => `<option value="${esc(k)}">`).join('');
  const bx = document.getElementById('patBusca');
  const vai = () => { const g = ROT.get(bx.value.trim()); if (g && g !== grupoSel) mostraGrupo(g, false); };
  bx.addEventListener('change', vai); bx.addEventListener('input', vai);
  const sel = document.getElementById('patSetor');
  sel.innerHTML += SETORES.map(s => `<option>${esc(s)}</option>`).join('');
  sel.addEventListener('change', () => { setorFiltro = sel.value; renderSetores(); if (grupoSel) mostraGrupo(grupoSel, false); });
})();

// ---------- ranking ----------
const COLS = [['Holdings e participações', 'Holdings'], ['Finanças (banco, crédito, seguro, gestão)', 'Finanças'], ['Atividades imobiliárias', 'Imobiliárias'], ['Construção', 'Construção'], ['Transporte terrestre', 'Transporte fora do recorte'], ['Comércio', 'Comércio']];
const ord = { k: 'n', dir: -1 };
function linhasTabela() {
  return Object.entries(P.grupos).map(([g, d]) => {
    const es = d.e.map(i => P.empresas[i]).filter(e => !soAtivas || e.sit === 'ativa');
    const o = { g, nome: rotG(g), h: d.h.length, n: es.length };
    for (const [s] of COLS) o[s] = es.filter(e => e.setor === s).length;
    o.outros = es.length - COLS.reduce((t, [s]) => t + o[s], 0);
    return o;
  });
}
function renderTabela() {
  const tb = document.getElementById('patTabela');
  tb.querySelector('thead').innerHTML = `<tr><th data-k="nome">Grupo</th><th data-k="h" class="num">Holdings sócias</th><th data-k="n" class="num">Empresas fora do ônibus</th>${COLS.map(([s, r]) => `<th data-k="${esc(s)}" class="num">${r}</th>`).join('')}<th data-k="outros" class="num">Outros setores</th></tr>`;
  const L = linhasTabela().sort((a, b) => typeof a[ord.k] === 'string' ? ord.dir * a[ord.k].localeCompare(b[ord.k], 'pt-BR') : ord.dir * (a[ord.k] - b[ord.k]) || b.h - a.h);
  tb.querySelector('tbody').innerHTML = L.map(o => `<tr data-g="${o.g}"><td>${esc(o.nome)}${P.nomes[o.g].topo ? ' <span class="topo-marca">●</span>' : ''}</td><td class="num">${o.h}</td><td class="num"><b>${o.n}</b></td>${COLS.map(([s]) => `<td class="num">${o[s] || ''}</td>`).join('')}<td class="num">${o.outros || ''}</td></tr>`).join('');
  tb.querySelectorAll('th').forEach(th => th.onclick = () => { const k = th.dataset.k; ord.dir = ord.k === k ? -ord.dir : (k === 'nome' ? 1 : -1); ord.k = k; renderTabela(); });
}
document.querySelector('#patTabela tbody').addEventListener('click', e => { const tr = e.target.closest('tr'); if (tr) mostraGrupo(tr.dataset.g); });

// ---------- encontros fora do ônibus ----------
function renderBlocos() {
  const nomeU = u => P.unidades[u] || u;
  const grupoDaU = u => Object.keys(P.nomes).find(g => P.nomes[g].ub === u);
  const npar = new Map(P.pontes.map(([a, b, k]) => [a + '|' + b, k]));
  document.getElementById('patBlocos').innerHTML = P.blocos.map(us => {
    let tot = 0; for (let i = 0; i < us.length; i++) for (let j = i + 1; j < us.length; j++) tot += npar.get(us[i] + '|' + us[j]) || npar.get(us[j] + '|' + us[i]) || 0;
    return `<li><b>${us.length} unidades de controle</b> <span class="muted">· ${tot} ${tot === 1 ? 'encontro' : 'encontros'} em empresas de outros setores</span><br>${us.map(u => { const g = grupoDaU(u); return g ? `<a href="#" class="glink" data-g="${g}">${esc(nomeU(u))}</a>` : esc(nomeU(u)); }).join(' · ')}</li>`;
  }).join('');
}

// ---------- início ----------
renderFind(); renderSetores(); renderTabela(); renderBlocos();
const h0 = decodeURIComponent(location.hash.slice(1)).replace(/^alem-/, '');
mostraGrupo(P.grupos[h0] ? h0 : 'GE-001', false);

// o que a aba "Quem controla" usa: saber se o grupo tem dados aqui e abrir o grupo nesta aba
window.PAT = {
  tem: g => !!P.grupos[g],
  conta: g => { const d = P.grupos[g]; return d ? { h: d.h.length, e: d.e.length } : null; },
  mostra: g => mostraGrupo(g, true),
  enquadra,
};
