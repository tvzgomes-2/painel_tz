// logic-ge.js — página "Rede de empresas" (rede-ge.html). Montada por montar_rede_ge.sh:
// head-ge.html + rede_ge.json + este arquivo. Lógica em JavaScript puro, sem dependência.
//
// FRONTEIRA DE EXPOSIÇÃO (decisões do autor de 26/08, 22/10 e 23/10/2026):
// empresa, grupo e agrupamentos de grupos. Nome de mercado e capital social por grupo
// SAEM (23/10: "reverter os dois"), com o nome de mercado limpo das anotações de trabalho
// no build. Nenhum nome de pessoa física, CPF ou CNPJ; nenhuma narrativa de conduta; e
// nenhum cruzamento entre presença de grupo e adoção da Tarifa Zero (é o teste da
// hipótese, adiado até a defesa). A auditoria disso roda no build_rede_ge.py.
'use strict';
const ARS = JSON.parse(document.getElementById('data-rede').textContent);
const NOS = new Map(ARS.nos.map(n => [n.id, n]));
const UNI = new Map(ARS.unidades.map(u => [u.id, u]));
const LIN = new Map(ARS.linhagens.map(l => [l.id, l]));
const FC = new Map(ARS.familias.map(f => [f.id, f]));
const FED = new Map(ARS.federacoes.map(f => [f.id, f]));
const fmt = v => Number(v).toLocaleString('pt-BR');
const esc = t => String(t ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const CAP_TOTAL = ARS.nos.reduce((a, n) => a + (n.capital || 0), 0);
const mi = v => v == null ? '—' : (v / 1e6).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const pct = (v, c = 1) => (v ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: c, maximumFractionDigits: c }) + '%';
const pctCap = v => v ? pct(100 * v / CAP_TOTAL, 2) : '—';
// rótulo da federação: o código e a maior unidade (federação é articulação, não controle)
const maiorDaFed = f => UNI.get(f.unidades[0])?.nome || '';

// vizinhança e contagem de ligações
const VIZ = new Map(ARS.nos.map(n => [n.id, []]));
for (const e of ARS.arestas) { VIZ.get(e.a)?.push({ id: e.b, t: e.t, w: e.w }); VIZ.get(e.b)?.push({ id: e.a, t: e.t, w: e.w }); }
for (const n of ARS.nos) n.lig = VIZ.get(n.id).length;
// municípios de cada grupo, a partir do índice município -> grupos
const MUN_DO_GRUPO = new Map(ARS.nos.map(n => [n.id, []]));
for (const [cod, gs] of Object.entries(ARS.presenca)) for (const g of gs) MUN_DO_GRUPO.get(g)?.push(cod);
// maior grupo de uma unidade (para selecionar a unidade a partir das listas)
const grupoPrincipal = u => [...u.membros].filter(m => NOS.has(m)).sort((a, b) => (NOS.get(b).capital || 0) - (NOS.get(a).capital || 0))[0];

// ---------- o que a tese encontra (Capítulo 6) ----------
function renderFind() {
  const r = ARS.resumo, f = ARS.funil;
  const empresas = ARS.nos.reduce((a, n) => a + (n.n_emp || 0), 0);
  const itens = [
    [fmt(r.n_grupos), `grupos econômicos no transporte coletivo, reunindo ${fmt(empresas)} das 7.681 empresas do recorte de transporte de passageiros`],
    [fmt(ARS.unidades.length), 'unidades de controle, quando os grupos com controle comum demonstrado ou provável (graus A e B) são somados'],
    [String(ARS.n_topo_ub), `unidades de controle detêm, juntas, metade dos R$ ${(CAP_TOTAL / 1e9).toFixed(2).replace('.', ',')} bilhões de capital declarado — entre ${f[2].meia} e ${f[0].meia} conforme a confiança exigida`],
    [fmt(r.n_mun), `municípios com estabelecimento de algum desses grupos, onde vivem ${(r.pop_mun / 1e6).toFixed(1).replace('.', ',')} milhões de pessoas — dois terços do país`],
  ];
  document.getElementById('geFind').innerHTML = itens.map(([b, s]) => `<div><b>${b}</b><span>${s}</span></div>`).join('');
  const nota = document.getElementById('nMunNota'); if (nota) nota.textContent = fmt(r.n_mun);
}

// ---------- cartões da rede ----------
function renderCards() {
  const conect = ARS.nos.filter(n => n.lig > 0).length;
  const fus = ARS.arestas.filter(e => e.t === 'fusao').length;
  const soc = ARS.arestas.length - fus;
  const cards = [
    [fmt(conect), `grupos com alguma ligação mapeada — os que aparecem no mapa`],
    [fmt(fus), 'ligações de mesmo bloco de controle (a análise trata os dois grupos como uma estrutura só)'],
    [fmt(soc), 'ligações por sócio compartilhado — vínculo fraco, que não indica controle comum'],
    [fmt(ARS.nos.length - conect), 'grupos sem ligação com nenhum outro (quase sempre pequenos e fechados)'],
  ];
  document.getElementById('cards').innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;">${cards.map(([n, l]) => `<div class="card"><div class="n">${n}</div><div class="l">${l}</div></div>`).join('')}</div>`;
}

// ---------- a rede (ARS interativa) ----------
// Reescrita em 23/10/2026, a pedido do autor ("a rede está meio tosca, fixa, sem zoom").
// Parte do layout calculado no build (componentes empacotados) e roda por cima uma simulação
// de forças leve, só para responder ao arraste: cada nó é puxado de volta à posição do build,
// o que mantém a leitura estável. Zoom e arraste por roda, arraste do fundo, pinça no celular
// e botões. Sem dependência externa.
const svg = document.getElementById('redeSvg');
const NS = 'http://www.w3.org/2000/svg';
let selecionado = null, modoMapa = 'grupo';
function el(tag, at) { const e = document.createElementNS(NS, tag); for (const k in at) e.setAttribute(k, at[k]); return e; }
const tooltip = document.getElementById('tooltip');
function mostraTip(e, html) {
  tooltip.innerHTML = html; tooltip.style.display = 'block';
  tooltip.style.left = Math.min(e.clientX + 14, innerWidth - 240) + 'px'; tooltip.style.top = (e.clientY + 14) + 'px';
}

const R = {   // estado da rede
  tam: 'n_emp', cor: 'topo', fus: true, soc: true, minW: 1, isolados: false,
  k: 1, tx: 0, ty: 0, W: 1000, H: 640, alpha: 0, raf: 0,
  // forças (23/10/2026, pedido do autor): no modo livre, a âncora no desenho original sai
  // e valem repulsão, gravidade e comprimento da ligação, ajustáveis
  livre: false, rep: 50, grav: 3, dist: 40,
};
// nós da simulação: só os com posição do build; os sem ligação ganham grade própria
const SIM = ARS.nos.map(n => ({ n, id: n.id, x: n.x, y: n.y, x0: n.x, y0: n.y, vx: 0, vy: 0, fixo: false, iso: n.x == null }));
const SIMI = new Map(SIM.map(s => [s.id, s]));
function gradeIsolados() {
  // os grupos sem ligação vão em fileiras sob a rede, do maior para o menor capital;
  // o passo respeita o raio de cada nó (com "tamanho = capital" eles variam muito)
  const lig = SIM.filter(s => !s.iso), iso = SIM.filter(s => s.iso).sort((a, b) => (b.n.capital || 0) - (a.n.capital || 0));
  const xs = lig.map(s => s.x), ys = lig.map(s => s.y);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y1 = Math.max(...ys);
  let x = x0, y = y1 + 70, hLin = 0;
  for (const s of iso) {
    const r = raio(s.n);
    if (x > x0 && x + 2 * r > x1) { x = x0; y += hLin + 8; hLin = 0; }
    s.x = s.x0 = x + r; s.y = s.y0 = y + r; x += 2 * r + 8; hLin = Math.max(hLin, 2 * r);
  }
}
const raio = n => R.tam === 'capital' ? 2.5 + Math.sqrt((n.capital || 0) / 1e6) * 0.95 : 3 + Math.sqrt(n.n_emp || 1) * 2.1;

// --- medidas de ARS: grau, intermediação (Brandes, sem peso) e componentes ---
const ADJ = new Map(ARS.nos.map(n => [n.id, new Set()]));
for (const e of ARS.arestas) { ADJ.get(e.a)?.add(e.b); ADJ.get(e.b)?.add(e.a); }
const BETW = new Map(ARS.nos.map(n => [n.id, 0]));
for (const s of ARS.nos.map(n => n.id)) {
  const S = [], P = new Map(), sig = new Map([[s, 1]]), d = new Map([[s, 0]]), Q = [s];
  while (Q.length) { const v = Q.shift(); S.push(v);
    for (const w of ADJ.get(v)) { if (!d.has(w)) { d.set(w, d.get(v) + 1); Q.push(w); }
      if (d.get(w) === d.get(v) + 1) { sig.set(w, (sig.get(w) || 0) + sig.get(v)); (P.get(w) || P.set(w, []).get(w)).push(v); } } }
  const dl = new Map();
  while (S.length) { const w = S.pop(); for (const v of P.get(w) || []) dl.set(v, (dl.get(v) || 0) + sig.get(v) / sig.get(w) * (1 + (dl.get(w) || 0)));
    if (w !== s) BETW.set(w, BETW.get(w) + (dl.get(w) || 0)); }
}
for (const [k, v] of BETW) BETW.set(k, v / 2);
const COMP = new Map(); let nComp = 0;
for (const n of ARS.nos) { if (COMP.has(n.id) || !ADJ.get(n.id).size) continue; nComp++;
  const fila = [n.id]; COMP.set(n.id, nComp); while (fila.length) { const v = fila.pop(); for (const w of ADJ.get(v)) if (!COMP.has(w)) { COMP.set(w, nComp); fila.push(w); } } }
const TAM_COMP = new Map(); for (const c of COMP.values()) TAM_COMP.set(c, (TAM_COMP.get(c) || 0) + 1);
// componentes renumerados por tamanho (1 = o maior)
const ORD_COMP = [...TAM_COMP.entries()].sort((a, b) => b[1] - a[1]).map(([c]) => c);
for (const [id, c] of COMP) COMP.set(id, ORD_COMP.indexOf(c) + 1);
const rankBet = [...ARS.nos].filter(n => BETW.get(n.id) > 0).sort((a, b) => BETW.get(b.id) - BETW.get(a.id));
const posBet = new Map(rankBet.map((n, i) => [n.id, i + 1]));

// --- layout na página: Fruchterman-Reingold por componente, com folga pelo raio dos nós,
// e empacotamento dos componentes na proporção do quadro. Parte das posições do build (semente
// estável: a mesma rede sempre desenha igual).
function layoutPagina() {
  const porComp = new Map();
  for (const s of SIM) { const c = COMP.get(s.id); if (c) (porComp.get(c) || porComp.set(c, []).get(c)).push(s); }
  const blocos = [];
  for (const [c, ss] of porComp) {
    const ids = new Set(ss.map(s => s.id));
    const ars = ARS.arestas.filter(e => ids.has(e.a) && ids.has(e.b));
    const L = 52, n = ss.length;
    // semente: posições do build, re-centradas e esticadas
    const cx = ss.reduce((a, s) => a + s.x, 0) / n, cy = ss.reduce((a, s) => a + s.y, 0) / n;
    for (const s of ss) { s.x = (s.x - cx) * 1.6; s.y = (s.y - cy) * 1.6; }
    let T = L * Math.sqrt(n) * .5;
    for (let it = 0; it < 420; it++) {
      for (const s of ss) { s.dx = 0; s.dy = 0; }
      for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
        const p = ss[i], q = ss[j]; let dx = p.x - q.x, dy = p.y - q.y; let d = Math.hypot(dx, dy) || .01;
        const m = raio(p.n) + raio(q.n) + 6, f = (L * L) / d + (d < m ? (m - d) * 4 : 0);
        dx /= d; dy /= d; p.dx += dx * f; p.dy += dy * f; q.dx -= dx * f; q.dy -= dy * f; }
      for (const e of ars) { const p = SIMI.get(e.a), q = SIMI.get(e.b); let dx = p.x - q.x, dy = p.y - q.y; const d = Math.hypot(dx, dy) || .01;
        // panelinhas de sócio compartilhado (todos ligados a todos) se fecham num novelo:
        // a atração da ligação fraca cai com o grau dos dois grupos
        const f = d * d / L * (e.t === 'fusao' ? 1.6 : 1 / Math.sqrt(Math.min(ADJ.get(e.a).size, ADJ.get(e.b).size))); dx /= d; dy /= d; p.dx -= dx * f; p.dy -= dy * f; q.dx += dx * f; q.dy += dy * f; }
      for (const s of ss) { s.dx -= s.x * .02 * L; s.dy -= s.y * .02 * L;   // gravidade fraca ao centro do componente
        const d = Math.hypot(s.dx, s.dy) || 1, st = Math.min(d, T); s.x += s.dx / d * st; s.y += s.dy / d * st; }
      T = Math.max(.6, T * .985);
    }
    const x0 = Math.min(...ss.map(s => s.x - raio(s.n))), x1 = Math.max(...ss.map(s => s.x + raio(s.n))) + 70;
    const y0 = Math.min(...ss.map(s => s.y - raio(s.n))), y1 = Math.max(...ss.map(s => s.y + raio(s.n))) + 12;
    blocos.push({ ss, x0, y0, w: x1 - x0, h: y1 - y0 });
  }
  // empacota em prateleiras, maiores primeiro, na proporção do quadro
  blocos.sort((a, b) => b.w * b.h - a.w * a.h);
  const area = blocos.reduce((a, b) => a + (b.w + 30) * (b.h + 30), 0);
  const larg = Math.max(blocos[0].w, Math.sqrt(area * (R.W / R.H)) * 1.05);
  let x = 0, y = 0, hPrat = 0;
  for (const b of blocos) {
    if (x > 0 && x + b.w > larg) { x = 0; y += hPrat + 30; hPrat = 0; }
    for (const s of b.ss) { s.x = s.x0 = s.x - b.x0 + x; s.y = s.y0 = s.y - b.y0 + y; }
    x += b.w + 30; hPrat = Math.max(hPrat, b.h);
  }
  gradeIsolados();
}

// --- cores ---
const HUES = ['#F5E400', '#FF2D6B', '#4F7FD4', '#6FBE44', '#FF8A3D', '#B57CFF', '#2EC4C4', '#E85DB0', '#C9A227', '#7FA8FF', '#9BD46A', '#FF6F61', '#5AD1A0', '#D9A0FF', '#F0B47A', '#62B0E8', '#C0D85A', '#FF9EC4', '#8FD3FF', '#E0C060'];
const CINZA = '#5b5b68';
function corDe(n) {
  const u = UNI.get(n.ub);
  if (R.cor === 'topo') return n.topo ? '#F5E400' : '#4F7FD4';
  if (R.cor === 'unidade') { const multi = ARS.unidades.filter(x => x.membros.length > 1); const i = multi.indexOf(u); return i >= 0 ? HUES[i % HUES.length] : CINZA; }
  if (R.cor === 'federacao') { const i = u?.fed ? ARS.federacoes.findIndex(f => f.id === u.fed) : -1; return i >= 0 ? HUES[i % HUES.length] : CINZA; }
  if (R.cor === 'linhagem') { const i = u?.lin ? ARS.linhagens.findIndex(l => l.id === u.lin) : -1; return i >= 0 ? HUES[i % HUES.length] : CINZA; }
  if (R.cor === 'componente') { const c = COMP.get(n.id); return c ? HUES[(c - 1) % HUES.length] : CINZA; }
  return CINZA;
}
function legenda() {
  const box = document.getElementById('redeLeg'); if (!box) return;
  const it = (c, t) => `<span><i style="background:${c}"></i>${t}</span>`;
  let h = '';
  if (R.cor === 'topo') h = it('#F5E400', `entre os ${ARS.resumo.n_topo} grupos com metade do capital`) + it('#4F7FD4', 'demais grupos');
  else if (R.cor === 'unidade') h = ARS.unidades.filter(u => u.membros.length > 1).map((u, i) => it(HUES[i % HUES.length], `${esc(u.nome)} <span class="muted">(${u.membros.length})</span>`)).join('') + it(CINZA, 'unidade de um só grupo');
  else if (R.cor === 'federacao') h = ARS.federacoes.map((f, i) => it(HUES[i % HUES.length], `${f.id} <span class="muted">${esc(maiorDaFed(f))}</span>`)).join('') + it(CINZA, 'fora de federação');
  else if (R.cor === 'linhagem') h = ARS.linhagens.map((l, i) => it(HUES[i % HUES.length], esc(l.nome))).join('') + it(CINZA, 'sem linhagem');
  else if (R.cor === 'componente') h = ORD_COMP.slice(0, 8).map((c, i) => it(HUES[i], `componente ${i + 1} <span class="muted">(${TAM_COMP.get(c)} grupos)</span>`)).join('') + (ORD_COMP.length > 8 ? `<span class="muted">e mais ${ORD_COMP.length - 8} componentes</span>` : '') + it(CINZA, 'sem ligação');
  box.innerHTML = h + `<span class="lg-lig"><b style="color:var(--rosa)">━</b> mesmo bloco de controle</span><span class="lg-lig"><b style="color:#8a8a98">━</b> sócio compartilhado</span>`;
}

// rótulo na rede: o nome de mercado, quando há (mais legível que a razão social da holding)
function rotRede(n) { const m = n.mercado; return m && m.length <= 34 ? m : (m ? m.slice(0, 32) + '…' : n.rot); }
// --- desenho ---
const vp = el('g', {}), gE = el('g', {}), gN = el('g', {}), gT = el('g', { 'pointer-events': 'none' });
vp.append(gE, gN, gT);
const LIN_EL = ARS.arestas.map(e => { const l = el('line', { 'data-a': e.a, 'data-b': e.b }); l._e = e; gE.appendChild(l); return l; });
const NO_EL = new Map(), TX_EL = new Map();
for (const s of [...SIM].sort((a, b) => (b.n.n_emp || 0) - (a.n.n_emp || 0))) {
  const c = el('circle', { 'data-id': s.id, class: 'no' }); gN.appendChild(c); NO_EL.set(s.id, c);
  const t = el('text', { class: 'rot' }); t.textContent = rotRede(s.n); gT.appendChild(t); TX_EL.set(s.id, t);
}
const visivel = s => !s.iso || R.isolados;
const arestaVisivel = e => (e.t === 'fusao' ? R.fus : (R.soc && e.w >= R.minW));
function desenha() {
  const k = R.k;
  vp.setAttribute('transform', `translate(${R.tx},${R.ty}) scale(${k})`);
  const foco = selecionado ? new Set([selecionado, ...ADJ.get(selecionado), ...(UNI.get(NOS.get(selecionado).ub)?.membros || [])]) : null;
  for (const l of LIN_EL) {
    const e = l._e, a = SIMI.get(e.a), b = SIMI.get(e.b);
    const on = arestaVisivel(e);
    l.style.display = on ? '' : 'none'; if (!on) continue;
    l.setAttribute('x1', a.x); l.setAttribute('y1', a.y); l.setAttribute('x2', b.x); l.setAttribute('y2', b.y);
    l.setAttribute('stroke', e.t === 'fusao' ? '#FF2D6B' : '#8a8a98');
    l.setAttribute('stroke-opacity', foco ? (e.a === selecionado || e.b === selecionado ? .95 : .06) : (e.t === 'fusao' ? .85 : .4));
    l.setAttribute('stroke-width', ((e.t === 'fusao' ? 1.8 : .8) + Math.log1p(e.w) * .55) / Math.sqrt(k));
  }
  for (const s of SIM) {
    const c = NO_EL.get(s.id), t = TX_EL.get(s.id), n = s.n, vis = visivel(s);
    c.style.display = vis ? '' : 'none'; t.style.display = 'none'; if (!vis) continue;
    const r = raio(n);
    c.setAttribute('cx', s.x); c.setAttribute('cy', s.y); c.setAttribute('r', r);
    c.setAttribute('fill', corDe(n)); c.setAttribute('fill-opacity', foco && !foco.has(s.id) ? .15 : .9);
    c.setAttribute('stroke', s.id === selecionado ? '#fff' : '#0E0E10'); c.setAttribute('stroke-width', (s.id === selecionado ? 3 : 1) / k);
    const mostra = foco ? foco.has(s.id) : (n.topo || k >= 1.9 || (k >= 1.25 && (n.n_emp || 0) >= 6));
    if (mostra) {
      t.style.display = ''; t.setAttribute('x', s.x + r + 3 / k); t.setAttribute('y', s.y + 3.5 / k);
      t.setAttribute('font-size', (s.id === selecionado ? 12.5 : 10.5) / k);
      t.setAttribute('font-weight', s.id === selecionado ? 700 : 400);
    }
  }
}
// --- simulação leve (só depois de arrastar ou mudar tamanhos) ---
function passo() {
  const ativos = SIM.filter(s => visivel(s) && (R.livre || !s.iso));
  const a = R.alpha, n = ativos.length;
  if (!R.livre) for (const s of ativos) { s.vx += (s.x0 - s.x) * .045 * a; s.vy += (s.y0 - s.y) * .045 * a; }
  else {
    // gravidade: puxa todos para o centro do desenho (sem ela, os componentes se afastam sem fim)
    const cx = ativos.reduce((t, s) => t + s.x0, 0) / n, cy = ativos.reduce((t, s) => t + s.y0, 0) / n, g = R.grav / 1000;
    for (const s of ativos) { s.vx += (cx - s.x) * g * a; s.vy += (cy - s.y) * g * a; }
    // repulsão: todos se empurram, mais forte de perto (carga elétrica)
    const Q = R.rep * R.rep;
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
      const p = ativos[i], q = ativos[j], dx = q.x - p.x, dy = q.y - p.y, d2 = Math.max(dx * dx + dy * dy, 25);
      if (d2 > 160000) continue;
      const f = Q / d2 * .02 * a; p.vx -= dx * f; p.vy -= dy * f; q.vx += dx * f; q.vy += dy * f; }
  }
  for (const l of LIN_EL) { const e = l._e; if (!arestaVisivel(e)) continue;
    const p = SIMI.get(e.a), q = SIMI.get(e.b); if (p.iso || q.iso) continue;
    const dx = q.x - p.x, dy = q.y - p.y, d = Math.hypot(dx, dy) || 1;
    const alvo = raio(p.n) + raio(q.n) + (R.livre ? R.dist * (e.t === 'fusao' ? .5 : 1) : (e.t === 'fusao' ? 14 : 30));
    const f = (d - alvo) / d * (e.t === 'fusao' ? .12 : .05) * (R.livre ? 2 : 1) * a; p.vx += dx * f; p.vy += dy * f; q.vx -= dx * f; q.vy -= dy * f; }
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {   // colisão
    const p = ativos[i], q = ativos[j], dx = q.x - p.x, dy = q.y - p.y, d = Math.hypot(dx, dy) || .01, m = raio(p.n) + raio(q.n) + 2.5;
    if (d < m) { const f = (m - d) / d * .5; p.vx -= dx * f; p.vy -= dy * f; q.vx += dx * f; q.vy += dy * f; } }
  for (const s of ativos) { if (s.fixo) { s.vx = s.vy = 0; continue; }
    s.vx *= .6; s.vy *= .6; const v = Math.hypot(s.vx, s.vy); if (v > 25) { s.vx *= 25 / v; s.vy *= 25 / v; }
    s.x += s.vx; s.y += s.vy; }
  R.alpha *= R.livre ? .985 : .965; desenha();
  R.raf = R.alpha > .01 ? requestAnimationFrame(passo) : 0;
}
function aquece(a = .5) { R.alpha = Math.max(R.alpha, a); if (!R.raf) R.raf = requestAnimationFrame(passo); }

// --- zoom e enquadramento ---
function mede() { const r = svg.getBoundingClientRect(); R.W = r.width || 1000; R.H = r.height || 640; svg.setAttribute('viewBox', `0 0 ${R.W} ${R.H}`); }
function enquadra(ids, anima = true) {
  const ss = (ids ? ids.map(i => SIMI.get(i)) : SIM).filter(s => s && visivel(s));
  if (!ss.length) return;
  const x0 = Math.min(...ss.map(s => s.x - raio(s.n))), x1 = Math.max(...ss.map(s => s.x + raio(s.n))) + (ids ? 90 : 60);
  const y0 = Math.min(...ss.map(s => s.y - raio(s.n))), y1 = Math.max(...ss.map(s => s.y + raio(s.n)));
  const pad = 24, k = Math.min(4, Math.max(.2, Math.min((R.W - 2 * pad) / Math.max(40, x1 - x0), (R.H - 2 * pad) / Math.max(40, y1 - y0))));
  const alvo = { k, tx: (R.W - k * (x0 + x1)) / 2, ty: (R.H - k * (y0 + y1)) / 2 };
  if (!anima) { Object.assign(R, alvo); desenha(); return; }
  const ini = { k: R.k, tx: R.tx, ty: R.ty }, t0 = performance.now();
  (function anda(t) { const u = Math.min(1, (t - t0) / 420), e = u * (2 - u);
    R.k = ini.k + (alvo.k - ini.k) * e; R.tx = ini.tx + (alvo.tx - ini.tx) * e; R.ty = ini.ty + (alvo.ty - ini.ty) * e; desenha();
    if (u < 1) requestAnimationFrame(anda); })(t0);
}
function zoomEm(px, py, f) {
  const k = Math.min(8, Math.max(.15, R.k * f)); f = k / R.k;
  R.tx = px - (px - R.tx) * f; R.ty = py - (py - R.ty) * f; R.k = k; desenha();
}
const ptSvg = e => { const r = svg.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
const mundo = ([x, y]) => [(x - R.tx) / R.k, (y - R.ty) / R.k];
svg.addEventListener('wheel', e => { e.preventDefault(); const [x, y] = ptSvg(e); zoomEm(x, y, Math.exp(-e.deltaY * .0016)); }, { passive: false });
// arraste: do fundo move a vista; de um nó move o nó; dois dedos fazem pinça
const toques = new Map(); let arr = null;
svg.addEventListener('pointerdown', e => {
  svg.setPointerCapture(e.pointerId); toques.set(e.pointerId, ptSvg(e));
  if (toques.size === 2) { const [a, b] = [...toques.values()]; arr = { tipo: 'pinca', d: Math.hypot(a[0] - b[0], a[1] - b[1]), m: [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2] }; return; }
  const c = e.target.closest('circle.no'); const p = ptSvg(e);
  arr = c ? { tipo: 'no', s: SIMI.get(c.dataset.id), p0: p, moveu: false } : { tipo: 'vista', p0: p, tx: R.tx, ty: R.ty, moveu: false };
  if (c && (!arr.s.iso || R.livre)) arr.s.fixo = true;
});
svg.addEventListener('pointermove', e => {
  if (toques.has(e.pointerId)) toques.set(e.pointerId, ptSvg(e));
  if (!arr) {   // dica ao passar o mouse
    const c = e.target.closest('circle.no'); if (!c) { tooltip.style.display = 'none'; return; }
    const n = NOS.get(c.dataset.id), u = UNI.get(n.ub);
    mostraTip(e, `<b>${esc(n.rot)}${n.topo ? ' · <span class="topo-marca">topo do capital</span>' : ''}</b>${n.mercado ? `<div style="color:var(--muted);margin:-2px 0 4px;">${esc(n.mercado)}</div>` : ''}<div class="tt-grid"><span>Capital (R$ mi)</span><span>${mi(n.capital)}</span><span>Empresas</span><span>${n.n_emp}</span><span>Ligações</span><span>${n.lig}</span><span>Intermediação</span><span>${posBet.has(n.id) ? posBet.get(n.id) + 'º' : '—'}</span>${u && u.membros.length > 1 ? `<span>Unidade</span><span>${u.id}</span>` : ''}${u?.fed ? `<span>Federação</span><span>${u.fed}</span>` : ''}</div>`);
    return;
  }
  tooltip.style.display = 'none';
  if (arr.tipo === 'pinca' && toques.size === 2) { const [a, b] = [...toques.values()]; const d = Math.hypot(a[0] - b[0], a[1] - b[1]); const m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
    R.tx += m[0] - arr.m[0]; R.ty += m[1] - arr.m[1]; zoomEm(m[0], m[1], d / arr.d); arr.d = d; arr.m = m; return; }
  const p = ptSvg(e); if (Math.hypot(p[0] - arr.p0[0], p[1] - arr.p0[1]) > 3) arr.moveu = true;
  if (arr.tipo === 'vista') { R.tx = arr.tx + p[0] - arr.p0[0]; R.ty = arr.ty + p[1] - arr.p0[1]; desenha(); }
  else if (arr.tipo === 'no' && arr.moveu && (!arr.s.iso || R.livre)) { const [x, y] = mundo(p); arr.s.x = x; arr.s.y = y; if (!R.livre) { arr.s.x0 = x; arr.s.y0 = y; } aquece(.35); desenha(); }
});
function solta(e) {
  toques.delete(e.pointerId);
  if (!arr) return;
  if (arr.tipo === 'no') { arr.s.fixo = false; if (!arr.moveu) seleciona(arr.s.id === selecionado ? null : arr.s.id); }
  else if (arr.tipo === 'vista' && !arr.moveu && !e.target.closest('circle.no')) seleciona(null);
  arr = toques.size ? arr : null;
}
svg.addEventListener('pointerup', solta); svg.addEventListener('pointercancel', solta);
svg.addEventListener('mouseleave', () => { tooltip.style.display = 'none'; });

function destaca(id) {
  desenha();
  const s = id && SIMI.get(id);
  document.getElementById('redeHint').textContent = s && s.iso && !R.isolados ? 'Este grupo não tem ligação mapeada; ligue "grupos sem ligação" para vê-lo na grade.' : '';
  if (s && visivel(s)) {   // traz o grupo e a vizinhança para a vista se estiverem fora
    const [x, y] = [s.x * R.k + R.tx, s.y * R.k + R.ty];
    if (x < 20 || y < 20 || x > R.W - 20 || y > R.H - 20) enquadra([id, ...ADJ.get(id)]);
  }
}

// --- controles ---
function desenhaRede() {
  svg.innerHTML = ''; svg.appendChild(vp); mede(); layoutPagina(); legenda(); enquadra(null, false);
  const q = id => document.getElementById(id);
  q('redeTam')?.addEventListener('change', e => { R.tam = e.target.value; gradeIsolados(); aquece(.4); desenha(); });
  q('redeCor')?.addEventListener('change', e => { R.cor = e.target.value; legenda(); desenha(); });
  q('redeFus')?.addEventListener('change', e => { R.fus = e.target.checked; desenha(); });
  q('redeSoc')?.addEventListener('change', e => { R.soc = e.target.checked; desenha(); });
  const maxW = Math.max(...ARS.arestas.filter(e => e.t !== 'fusao').map(e => e.w));
  if (q('redeMinW')) { q('redeMinW').max = maxW; q('redeMinW').addEventListener('input', e => { R.minW = +e.target.value; q('redeMinWv').textContent = R.minW; desenha(); }); }
  q('redeIso')?.addEventListener('change', e => { R.isolados = e.target.checked; enquadra(); });
  // forças
  const liga = () => { q('redeForcas').classList.toggle('on', R.livre); q('redeLivre').checked = R.livre; };
  q('redeLivre')?.addEventListener('change', e => { R.livre = e.target.checked; liga(); if (!R.livre) { layoutPagina(); enquadra(); } aquece(1); });
  for (const [id, k] of [['fRep', 'rep'], ['fGrav', 'grav'], ['fDist', 'dist']]) q(id)?.addEventListener('input', e => {
    R[k] = +e.target.value; q(id + 'v').textContent = e.target.value; if (!R.livre) { R.livre = true; liga(); } aquece(.8); });
  q('fReorg')?.addEventListener('click', () => { R.livre = true; liga();
    for (const s of SIM) if (visivel(s)) { s.x += (Math.random() - .5) * 200; s.y += (Math.random() - .5) * 200; }
    aquece(1); setTimeout(() => enquadra(), 2600); });
  q('fOrig')?.addEventListener('click', () => { R.livre = false; liga(); layoutPagina(); aquece(.3); enquadra(); });
  q('zoomMais')?.addEventListener('click', () => zoomEm(R.W / 2, R.H / 2, 1.4));
  q('zoomMenos')?.addEventListener('click', () => zoomEm(R.W / 2, R.H / 2, 1 / 1.4));
  q('resetRede')?.addEventListener('click', () => { seleciona(null); enquadra(); });
  q('telaCheia')?.addEventListener('click', () => alternaTela());
  addEventListener('keydown', e => { if (e.key === 'Escape' && document.body.classList.contains('rede-cheia')) alternaTela(); });
  addEventListener('resize', () => { mede(); desenha(); });
  // busca de grupo dentro da rede
  const bx = q('redeBusca'), dl = q('redeBuscaList');
  if (bx) {
    const ROT = new Map(); for (const n of ARS.nos) { ROT.set(n.rot, n.id); if (n.mercado && !ROT.has(n.mercado)) ROT.set(n.mercado, n.id); }
    dl.innerHTML = [...ROT.keys()].sort((a, b) => a.localeCompare(b, 'pt-BR')).map(k => `<option value="${esc(k)}">`).join('');
    const vai = () => { const id = ROT.get(bx.value.trim()); if (!id) return;
      if (SIMI.get(id).iso && !R.isolados) { R.isolados = true; q('redeIso').checked = true; }
      seleciona(id); enquadra([id, ...ADJ.get(id)]); };
    bx.addEventListener('change', vai); bx.addEventListener('input', vai);
  }
  renderMedidas();
}
function alternaTela() {
  const on = document.body.classList.toggle('rede-cheia');
  document.getElementById('telaCheia').textContent = on ? '✕ Sair da tela cheia' : '⛶ Tela cheia';
  setTimeout(() => { mede(); enquadra(selecionado ? [selecionado, ...ADJ.get(selecionado)] : null, false); }, 30);
}
function renderMedidas() {
  const box = document.getElementById('redeMedidas'); if (!box) return;
  const N = ARS.nos.length, E = ARS.arestas.length, lig = ARS.nos.filter(n => ADJ.get(n.id).size).length;
  const dens = 2 * E / (N * (N - 1)), grauMed = 2 * E / N;
  const maior = TAM_COMP.get(ORD_COMP[0]);
  const fmtD = v => v.toLocaleString('pt-BR', { maximumFractionDigits: 3 });
  const topGrau = [...ARS.nos].sort((a, b) => ADJ.get(b.id).size - ADJ.get(a.id).size).slice(0, 8);
  const topBet = rankBet.slice(0, 8);
  const li = (n, v) => `<li><a href="#" class="gelink" data-id="${n.id}">${esc(n.rot)}</a> <span class="muted">${v}</span></li>`;
  box.innerHTML = `<div class="medgrid">
      <div><b>${fmt(N)}</b><span>nós (grupos)</span></div><div><b>${fmt(E)}</b><span>ligações</span></div>
      <div><b>${fmtD(dens)}</b><span>densidade da rede</span></div><div><b>${grauMed.toFixed(2).replace('.', ',')}</b><span>ligações por grupo, em média</span></div>
      <div><b>${ORD_COMP.length}</b><span>componentes com ligação (${fmt(lig)} grupos)</span></div><div><b>${maior}</b><span>grupos no maior componente</span></div>
    </div>
    <div class="medlistas">
      <div><p class="sub" style="margin:8px 0 3px;"><b>Mais conectados</b> (grau: com quantos grupos se liga)</p><ol>${topGrau.map(n => li(n, ADJ.get(n.id).size)).join('')}</ol></div>
      <div><p class="sub" style="margin:8px 0 3px;"><b>Mais intermediários</b> (estão no caminho entre outros grupos)</p><ol>${topBet.map(n => li(n, BETW.get(n.id).toLocaleString('pt-BR', { maximumFractionDigits: 0 }))).join('')}</ol></div>
    </div>
    <p class="sub" style="margin:6px 0 0;">Medidas calculadas nesta página sobre as ligações entre grupos (sem peso). A intermediação conta em quantos dos caminhos mais curtos entre dois grupos o grupo está no meio: é quem articula partes da rede que, sem ele, ficariam mais longe. Uma ligação por sócio compartilhado é vínculo fraco — leia a centralidade como posição na rede de sócios, não como poder de controle.</p>`;
}

// ---------- mapa dos municípios do grupo selecionado ----------
// Contornos das UFs e um ponto por município com estabelecimento (projeção simples, feita no
// build). Em cinza, todos os 1.042 municípios com presença de algum grupo; em amarelo, os do
// grupo — ou, no modo "unidade", os de todos os grupos da mesma unidade de controle.
let geoBase = null;
function mapaMunicipios(cods) {
  if (!geoBase) {
    geoBase = ARS.geo.ufs.map(d => `<path d="${d}" class="ufb"/>`).join('')
      + Object.values(ARS.geo.pontos).map(([x, y]) => `<circle cx="${x}" cy="${y}" r="1.3" class="pfundo"/>`).join('');
  }
  const pts = cods.map(c => [c, ARS.geo.pontos[c]]).filter(([, p]) => p)
    .map(([c, [x, y]]) => `<circle cx="${x}" cy="${y}" r="4" class="pgrupo" data-c="${c}"><title>${esc(ARS.mun[c])}</title></circle>`).join('');
  return `<svg class="munmapa" viewBox="-6 -6 600 604" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Mapa dos municípios">${geoBase}${pts}</svg>`;
}
function listaMunicipios(cods) {
  const porUf = {};
  for (const c of cods) { const [nm, uf] = String(ARS.mun[c]).split('/'); (porUf[uf] = porUf[uf] || []).push(nm); }
  const ufs = Object.keys(porUf).sort((a, b) => porUf[b].length - porUf[a].length || a.localeCompare(b));
  return `<div class="munlista">${ufs.map(uf => `<p><b>${uf}</b> <span class="muted">(${porUf[uf].length})</span> ${porUf[uf].sort((a, b) => a.localeCompare(b, 'pt-BR')).map(esc).join(' · ')}</p>`).join('')}</div>`;
}

// ---------- ficha do grupo ----------
function seleciona(id, rolar, modo) {
  selecionado = id; if (modo) modoMapa = modo; destaca(id);
  const box = document.getElementById('detail');
  document.querySelectorAll('#geTable tbody tr').forEach(tr => tr.classList.toggle('sel', tr.dataset.id === id));
  if (!id) { box.innerHTML = '<div class="empty">Clique num grupo na rede, na tabela ou nas listas de unidades.</div>'; return; }
  const n = NOS.get(id), u = UNI.get(n.ub);
  const multi = u && u.membros.length > 1;
  if (!multi) modoMapa = 'grupo';
  const lin = u?.lin && LIN.get(u.lin), fc = u?.fc && FC.get(u.fc), fed = u?.fed && FED.get(u.fed);
  const viz = VIZ.get(id).map(v => ({ ...v, n: NOS.get(v.id) })).sort((a, b) => (a.t === b.t ? b.w - a.w : a.t === 'fusao' ? -1 : 1));
  const gruposMapa = modoMapa === 'unidade' && multi ? u.membros.filter(m => NOS.has(m)) : [id];
  const cods = [...new Set(gruposMapa.flatMap(g => MUN_DO_GRUPO.get(g) || []))];
  const linha = (k, v) => v == null || v === '' ? '' : `<tr><td>${k}</td><td>${v}</td></tr>`;
  const links = ids => ids.filter(m => NOS.has(m)).map(m => m === id ? `<b>${esc(NOS.get(m).rot)}</b>` : `<a href="#" class="gelink" data-id="${m}">${esc(NOS.get(m).rot)}</a>`).join(', ');
  box.innerHTML = `<div><b style="font-size:15px;">${esc(n.rot)}</b>${n.topo ? ' <span class="tag" style="background:rgba(245,228,0,.16);color:#F5E400;">topo do capital</span>' : ''}</div>
    ${n.mercado ? `<div class="mercado">${esc(n.mercado)}</div>` : ''}
    <table>
      ${linha('Capital social declarado', n.capital ? `R$ ${mi(n.capital)} mi <span class="muted">(${pctCap(n.capital)} do setor)</span>` : '—')}
      ${linha('Empresas sob o mesmo controle', n.n_emp)}
      ${linha('Empresa central na rede', esc(n.central))}
      ${linha('Sócios (contagem)', n.n_soc)}
      ${linha('Sócios-ponte', n.ponte)}
      ${linha('Sócios de articulação', n.artic)}
      ${linha('Densidade interna', n.dens != null ? String(n.dens).replace('.', ',') : null)}
      ${linha('Ligações com outros grupos', n.lig)}
      ${linha('Intermediação na rede', posBet.has(id) ? `${posBet.get(id)}º de ${rankBet.length} grupos intermediários` : (n.lig ? 'não está no caminho entre outros' : null))}
      ${linha('Componente da rede', COMP.get(id) ? `${COMP.get(id)}º, com ${TAM_COMP.get(ORD_COMP[COMP.get(id) - 1])} grupos` : null)}
    </table>
    <div class="agrup">
      <p class="sub" style="margin:10px 0 4px;"><b>Agrupamentos</b> (escala de confiança, Seção 6.1)</p>
      ${u ? `<div><span class="grau g${multi ? (u.grau || 'B') : 'x'}">${multi ? (u.grau || 'B') : '—'}</span> <b>Unidade de controle ${u.id}</b> · ${esc(u.nome)}<br><span class="muted">${multi ? `${u.membros.length} grupos fundidos por controle ${u.grau === 'A' ? 'comum demonstrado' : 'provável'}: ${links(u.membros)}` : 'um só grupo'} · R$ ${mi(u.capital)} mi · ${pct(u.pct, 2)} do capital${u.id && ARS.unidades.indexOf(u) < ARS.n_topo_ub ? ' · <span class="topo-marca">entre as ' + ARS.n_topo_ub + ' unidades com metade do capital</span>' : ''}</span></div>` : ''}
      ${fc ? `<div><span class="grau gA">A</span> <b>Família de controle</b> · ${esc(fc.nome)}<br><span class="muted">ramos: ${links(fc.membros)}</span></div>` : ''}
      ${lin ? `<div><span class="grau gC">C</span> <b>Linhagem</b> · ${esc(lin.nome)} <span class="muted">— ${esc(lin.tipo)}, ${esc(lin.status)}</span><br><span class="muted">${links(lin.membros)}</span></div>` : ''}
      ${fed ? `<div><span class="grau gD">D</span> <b>Federação ${fed.id}</b> · ${fed.unidades.length} unidades articuladas, R$ ${mi(fed.capital)} mi <span class="muted">— articulação, não controle</span></div>` : ''}
      ${!lin && !fed && !multi ? '<p class="sub" style="margin:0;">Sem linhagem nem federação registradas.</p>' : ''}
      ${window.PAT?.tem(id) ? (c => `<a href="#" class="ponte-aba" data-aba="alem" data-g="${id}">Além do ônibus: ${c.h} ${c.h === 1 ? 'holding sócia' : 'holdings sócias'}${c.e ? `, ${c.e} empresas de outros setores` : ''} →</a>`)(window.PAT.conta(id)) : ''}
    </div>
    <p class="sub" style="margin:12px 0 4px;"><b>Onde tem endereço</b> — ${fmt(cods.length)} ${cods.length === 1 ? 'município' : 'municípios'} (presença, não operação)</p>
    ${multi ? `<div class="modomapa"><button data-m="grupo" class="${modoMapa === 'grupo' ? 'on' : ''}">Este grupo</button><button data-m="unidade" class="${modoMapa === 'unidade' ? 'on' : ''}">Toda a unidade ${u.id} (${u.membros.length} grupos)</button></div>` : ''}
    ${cods.length ? mapaMunicipios(cods) + listaMunicipios(cods) : '<p class="sub">Sem estabelecimento com município identificado.</p>'}
    ${viz.length ? `<p class="sub" style="margin:10px 0 3px;"><b>Ligado a</b></p><ul style="margin:0;padding-left:16px;font-size:12px;">${viz.slice(0, 12).map(v => `<li><a href="#" data-id="${v.id}" class="gelink">${esc(v.n.rot)}</a> — ${v.t === 'fusao' ? '<span style="color:#FF2D6B;">mesmo bloco de controle</span>' : `${v.w} ${v.w === 1 ? 'sócio' : 'sócios'} em comum`}</li>`).join('')}${viz.length > 12 ? `<li style="color:var(--muted);">e mais ${viz.length - 12}</li>` : ''}</ul>` : '<p class="sub" style="margin-top:9px;">Sem ligação societária mapeada com outro grupo.</p>'}`;
  if (rolar) document.getElementById('fichaPanel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
document.addEventListener('click', e => {
  const a = e.target.closest('.gelink'); if (a) { e.preventDefault(); seleciona(a.dataset.id, true, a.dataset.modo || 'grupo'); return; }
  const b = e.target.closest('.modomapa button'); if (b && selecionado) seleciona(selecionado, false, b.dataset.m);
});
document.getElementById('detail').addEventListener('mousemove', e => {
  const p = e.target.closest('circle.pgrupo'); if (!p) { tooltip.style.display = 'none'; return; }
  const c = p.dataset.c, gs = (ARS.presenca[c] || []).length;
  mostraTip(e, `<b>${esc(ARS.mun[c])}</b><span style="color:var(--muted);">${gs} ${gs === 1 ? 'grupo tem' : 'grupos têm'} endereço aqui</span>`);
});
document.getElementById('detail').addEventListener('mouseleave', () => { tooltip.style.display = 'none'; });

// ---------- do grupo à federação ----------
function renderAgrupamentos() {
  const efeito = { A: 'funde os grupos numa unidade', B: 'funde os grupos numa unidade', C: 'atributo — não funde', D: 'atributo — não funde; só teto', E: 'registrado, sem efeito' };
  document.getElementById('geEscala').innerHTML = `<table class="getab escala"><thead><tr><th>Grau</th><th>O que é</th><th>Regra</th><th>Efeito na contagem</th></tr></thead><tbody>${ARS.escala.map(e => `<tr><td><span class="grau g${e.grau}">${e.grau}</span></td><td><b>${esc(e.nome)}</b></td><td class="regra">${esc(e.regra)}</td><td>${efeito[e.grau]}</td></tr>`).join('')}</tbody></table>`;
  const maxN = Math.max(...ARS.funil.map(f => f.n)), maxM = Math.max(...ARS.funil.map(f => f.meia));
  document.getElementById('geFunil').innerHTML = ARS.funil.map(f => `<div class="funlin${f.grau === '+D' ? ' teto' : ''}">
      <div class="fr"><b>${esc(f.rot)}</b></div>
      <div class="fb"><div class="fbar" style="width:${(100 * f.n / maxN).toFixed(1)}%"></div><span>${fmt(f.n)} unidades</span></div>
      <div class="fb"><div class="fbar m" style="width:${(100 * f.meia / maxM).toFixed(1)}%"></div><span>metade do capital em <b>${f.meia}</b></span></div>
      <div class="fx">Gini ${String(f.gini.toFixed(3)).replace('.', ',')} · maior ${pct(f.maior)}</div></div>`).join('')
    + `<p class="sub" style="margin-top:6px;">Mesmos números da Tabela 5 da tese, recalculados aqui a partir da Tabela mestre v5 e da escala de confiança. A leitura principal é a das unidades de controle (A + B); a das federações encadeia articulações sem controle comum e serve só de teto.</p>`;
  // as unidades com metade do capital
  const nt = document.getElementById('nTopoUb'); if (nt) nt.textContent = ARS.n_topo_ub;
  const topo = ARS.unidades.slice(0, ARS.n_topo_ub);
  document.getElementById('geTopoUb').innerHTML = `<table class="getab"><thead><tr><th>#</th><th>Unidade de controle</th><th class="num">Grupos</th><th class="num">Capital (R$ mi)</th><th class="num">% do setor</th><th class="num">Acumulado</th><th>Linhagem · federação</th></tr></thead><tbody>${topo.map((u, i) => {
      const g = grupoPrincipal(u); const l = u.lin && LIN.get(u.lin);
      return `<tr><td class="num">${i + 1}</td><td><a href="#" class="gelink" data-id="${g}" data-modo="${u.membros.length > 1 ? 'unidade' : 'grupo'}">${esc(u.nome)}</a></td><td class="num">${u.membros.length}${u.membros.length > 1 ? ` <span class="grau g${u.grau}">${u.grau}</span>` : ''}</td><td class="num">${mi(u.capital)}</td><td class="num">${pct(u.pct, 2)}</td><td class="num">${pct(u.acum, 1)}</td><td>${l ? `<span class="grau gC">C</span> ${esc(l.nome)} ` : ''}${u.fed ? `<span class="grau gD">D</span> ${u.fed}` : ''}</td></tr>`; }).join('')}</tbody></table>`;
  // famílias de controle (A, ramos com capital cruzado)
  document.getElementById('geFamilias').innerHTML = ARS.familias.map(f => `<li><span class="grau gA">A</span> <b>${esc(f.nome.replace(/\s*\(.*$/, ''))}</b> — ramos ${f.membros.filter(m => NOS.has(m)).map(m => `<a href="#" class="gelink" data-id="${m}" data-modo="unidade">${esc(NOS.get(m).rot)}</a>`).join(' e ')} <span class="muted">· R$ ${mi(f.capital)} mi</span></li>`).join('');
  document.getElementById('geLinhagens').innerHTML = ARS.linhagens.map(l => `<li><span class="grau gC">C</span> <b>${esc(l.nome)}</b> <span class="muted">— ${esc(l.tipo)}, ${esc(l.status)}</span><br>${l.membros.filter(m => NOS.has(m)).map(m => `<a href="#" class="gelink" data-id="${m}">${esc(NOS.get(m).rot)}</a>`).join(' · ')} <span class="muted">· R$ ${mi(l.capital)} mi</span></li>`).join('');
  document.getElementById('geFederacoes').innerHTML = ARS.federacoes.map(f => `<details class="fed"><summary><span class="grau gD">D</span> <b>${f.id}</b> · ${f.unidades.length} unidades · R$ ${mi(f.capital)} mi <span class="muted">(${pctCap(f.capital)}) — maior: ${esc(maiorDaFed(f))}</span></summary>
      <p>${f.unidades.map(x => UNI.get(x)).filter(Boolean).map(u => `<a href="#" class="gelink" data-id="${grupoPrincipal(u)}" data-modo="${u.membros.length > 1 ? 'unidade' : 'grupo'}">${esc(u.nome)}</a>`).join(' · ')}</p></details>`).join('');
}

// ---------- tabela ----------
const ordem = { k: 'capital', dir: -1 };
function renderTabela() {
  const linhas = [...ARS.nos].sort((a, b) => {
    const va = a[ordem.k], vb = b[ordem.k];
    if (typeof va === 'string' || typeof vb === 'string') return ordem.dir * String(va ?? '').localeCompare(String(vb ?? ''), 'pt-BR');
    return ordem.dir * ((va ?? -1) - (vb ?? -1));
  });
  document.querySelector('#geTable tbody').innerHTML = linhas.map(n => {
    const u = UNI.get(n.ub); const multi = u && u.membros.length > 1;
    return `<tr data-id="${n.id}"${n.id === selecionado ? ' class="sel"' : ''}>
    <td>${esc(n.rot)}${n.mercado ? `<div class="merc">${esc(n.mercado)}</div>` : ''}</td>
    <td class="num">${mi(n.capital)}</td><td class="num">${n.topo ? '<span class="topo-marca">●</span>' : ''}</td>
    <td>${u ? `${u.id}${multi ? ` <span class="grau g${u.grau}">${u.grau}</span>` : ''}` : '—'}</td>
    <td class="num">${n.n_emp}</td><td class="num">${n.n_soc ?? '—'}</td><td class="num">${n.ponte ?? '—'}</td>
    <td class="num">${n.dens != null ? String(n.dens).replace('.', ',') : '—'}</td><td class="num">${n.n_mun}</td><td class="num">${n.lig}</td></tr>`; }).join('');
}
document.querySelectorAll('#geTable th').forEach(th => th.addEventListener('click', () => {
  const k = th.dataset.k === 'nome' ? 'rot' : th.dataset.k;
  ordem.dir = ordem.k === k ? -ordem.dir : (k === 'rot' || k === 'ub' ? 1 : -1); ordem.k = k; renderTabela();
}));
document.querySelector('#geTable tbody').addEventListener('click', e => { const tr = e.target.closest('tr'); if (tr) seleciona(tr.dataset.id, true, 'grupo'); });

// ---------- onde os grupos estão ----------
function renderTerritorio() {
  const top = [...ARS.nos].sort((a, b) => b.n_mun - a.n_mun || b.n_emp - a.n_emp).slice(0, 20);
  const max = top[0]?.n_mun || 1;
  document.getElementById('geTerr').innerHTML = top.map(n => `<div class="terrlin">
      <div class="r" data-id="${n.id}" title="${esc(n.mercado || n.rot)}">${esc(n.rot)}${n.topo ? ' <span class="topo-marca">●</span>' : ''}</div>
      <div class="t"><div class="f" style="width:${(100 * n.n_mun / max).toFixed(1)}%"></div></div>
      <div class="n">${n.n_mun}</div></div>`).join('')
    + `<p class="sub" style="margin-top:6px;">Municípios em que o grupo tem ao menos um estabelecimento. <span class="topo-marca">●</span> topo do capital. Clique para ver o mapa do grupo.</p>`;
}
document.getElementById('geTerr')?.addEventListener('click', e => { const r = e.target.closest('.r'); if (r) seleciona(r.dataset.id, true, 'grupo'); });

const ROT2COD = new Map(Object.entries(ARS.mun).map(([c, nm]) => [nm, c]));
const busca = document.getElementById('muniBusca'), lista = document.getElementById('muniBuscaList');
function sugere() {
  const q = busca.value.trim().toLowerCase(); if (q.length < 2) { lista.innerHTML = ''; return; }
  const nq = q.normalize('NFD').replace(/[̀-ͯ]/g, '');
  const hits = [...ROT2COD.keys()].filter(k => k.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').includes(nq)).slice(0, 30);
  lista.innerHTML = hits.map(h => `<option value="${esc(h)}">`).join('');
}
function mostraMuni() {
  const cod = ROT2COD.get(busca.value.trim()); const box = document.getElementById('muniGrupos');
  if (!cod) return;
  const gs = (ARS.presenca[cod] || []).map(id => NOS.get(id)).sort((a, b) => (b.topo - a.topo) || (b.capital || 0) - (a.capital || 0));
  box.innerHTML = `<p class="sub" style="margin-top:8px;"><b>${esc(ARS.mun[cod])}</b>: ${gs.length} ${gs.length === 1 ? 'grupo tem' : 'grupos têm'} endereço no município.</p>
    <ul>${gs.map(n => `<li><a href="#" class="gelink" data-id="${n.id}">${esc(n.rot)}</a>${n.topo ? ' <span class="topo-marca">●</span>' : ''} <span style="color:var(--muted);">— ${n.mercado ? esc(n.mercado) + ', ' : ''}${n.n_emp} ${n.n_emp === 1 ? 'empresa' : 'empresas'}</span></li>`).join('')}</ul>
    <p class="sub">Ter endereço não é operar o sistema do município. Quem opera a Tarifa Zero de cada caso está no contrato, no <a href="painel.html#explorar">Painel Brasil</a>.</p>`;
}
busca?.addEventListener('input', () => { sugere(); mostraMuni(); });
busca?.addEventListener('change', mostraMuni);

// ---------- abas: "Quem controla" e "Além do ônibus" ----------
function abreAba(nome) {
  if (nome !== 'alem') nome = 'controle';
  for (const a of ['controle', 'alem']) {
    document.getElementById('tab-' + a).hidden = a !== nome;
    const b = document.getElementById('tabbtn-' + a); b.classList.toggle('on', a === nome); b.setAttribute('aria-selected', a === nome);
  }
  // os quadros escondidos não têm tamanho: mede de novo ao mostrar
  if (nome === 'alem') setTimeout(() => window.PAT?.enquadra(), 0); else setTimeout(() => { mede(); desenha(); }, 0);
  if (nome === 'alem' && !location.hash.startsWith('#alem')) history.replaceState(null, '', '#alem');
  if (nome === 'controle' && location.hash.startsWith('#alem')) history.replaceState(null, '', location.pathname);
}
document.querySelectorAll('.tabbtn').forEach(b => b.addEventListener('click', () => abreAba(b.dataset.tab)));
document.addEventListener('click', e => {
  const a = e.target.closest('.ponte-aba'); if (!a) return;
  e.preventDefault(); abreAba(a.dataset.aba);
  const g = a.dataset.g; if (!g) { scrollTo({ top: document.querySelector('nav.tabs').offsetTop, behavior: 'smooth' }); return; }
  if (a.dataset.aba === 'alem') window.PAT?.mostra(g); else seleciona(g, true);
});

// ---------- início ----------
renderFind(); renderCards(); desenhaRede(); renderAgrupamentos(); renderTabela(); renderTerritorio();
const h = decodeURIComponent(location.hash.slice(1));
if (NOS.has(h)) seleciona(h);
// a aba "Além do ônibus" é aberta no fim da montagem (montar_rede_ge.sh), depois de window.PAT existir
