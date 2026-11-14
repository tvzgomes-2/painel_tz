#!/usr/bin/env python3
"""
proposta_etapa3.py — Painel Brasil, os urgentes da Fase 13 do ROADMAP (13/11/2026). Roda depois de proposta_etapa2.py,
antes de oficializar_painel.py.

  13.1  a lista de municípios passa a obedecer a TODOS os filtros (antes ignorava "Somente TZ / não-TZ" e a régua),
        mostra quantos municípios há no recorte e diz quando não há nenhum
  13.2  "Como se conta?": uma caixa sob os destaques que liga 193 · 187 · 173 · 8 · 6 · 45, e o link no primeiro cartão
  13.3  a busca de município mostra as sugestões na própria página (sem depender do navegador), aceita Enter com o
        nome sem a UF e avisa quando a cidade está fora do recorte dos filtros
"""
import os, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, 'painel-proposta.html')
s = open(ARQ, encoding='utf-8').read()
assert 'proposta_etapa2' in s and 'proposta_etapa3' not in s, 'rode proposta_etapa2.py antes, uma vez só'

def troca(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, f'âncora com {c} ocorrência(s), esperado {n}: {a[:100]!r}'
    s = s.replace(a, b)

# ---------------------------------------------------------------- 13.1 lista = mesmo recorte
troca('''  let rows = STATS.tz_list.concat(PARCIAL_LIST).filter(r => {
    if (state.uf && r.uf !== state.uf) return false;
    if (state.faixa && r.faixa_pop !== state.faixa) return false;
    if (state.regic && String(r.regic_nivel) !== state.regic) return false;
    if (state.arranjo && r.tipo_arranjo !== state.arranjo) return false;
    return true;
  });''', '''  // proposta_etapa3 (13.1): a lista obedece aos mesmos filtros do mapa e dos cartões
  let rows = STATS.tz_list.concat(PARCIAL_LIST).filter(r => passesFilter(MUNI.get(String(r.id)) || MUNI.get(Number(r.id)) || r));''')
troca("  tbody.innerHTML = parts.join('');\n}", """  tbody.innerHTML = parts.length ? parts.join('') : '<tr><td colspan="10" class="tz-vazio">Nenhum município neste recorte. Mude ou limpe os filtros acima.</td></tr>';
  const ct = document.getElementById('tzConta');
  if (ct) { const filtro = algumFiltroAtivo && algumFiltroAtivo();
    ct.innerHTML = `<b>${rows.length.toLocaleString('pt-BR')}</b> ${rows.length === 1 ? 'município' : 'municípios'} ${filtro ? 'neste recorte' : 'na lista'} · ${rows.filter(r => r.tz_status === 'Ativa').length} universais, ${rows.filter(r => r.tz_status === 'Parcial').length} parciais da régua, ${rows.filter(r => r.tz_status === 'Encerrada').length} encerradas`; }
}""")
troca('<div class="tzlistwrap">', '<p class="tz-conta" id="tzConta"></p>\n    <div class="tzlistwrap">')
troca("document.getElementById('tzFilter').addEventListener('change', e => { state.tzFilter = e.target.value; render(); atualizaBotaoLimpar(); });",
      "document.getElementById('tzFilter').addEventListener('change', e => { state.tzFilter = e.target.value; render(); renderTZTable(); atualizaBotaoLimpar(); });")

# ---------------------------------------------------------------- 13.2 como se conta
troca('<div class="destaques" id="destaques"></div>',
      '<div class="destaques" id="destaques"></div>\n<details class="como-conta" id="comoConta"><summary>Como se conta? 193 · 187 · 173 · 8 · 6 · 45</summary><div id="comoContaTxt"></div></details>')
troca("d: `de ${baseVer.toLocaleString('pt-BR')} políticas verificadas na base · base de 11/11/2026` },",
      "d: `de ${baseVer.toLocaleString('pt-BR')} políticas verificadas na base · base de 11/11/2026 · <a href=\"#comoConta\" class=\"lk-conta\">como se conta?</a>` },")

# ---------------------------------------------------------------- CSS + JS
CSS3 = '''  /* ===== proposta_etapa3 (13/11/2026): Fase 13 do ROADMAP ===== */
  .tz-conta{font-size:13px;color:var(--text);margin:4px 0 8px;} .tz-conta b{color:var(--amarelo);font-size:15px;}
  td.tz-vazio{padding:18px 10px !important;color:var(--muted);font-style:italic;text-align:center;}
  details.como-conta{flex:1 1 100%;margin:8px 0 0;background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:8px 13px;font-size:13px;}
  details.como-conta > summary{cursor:pointer;font-weight:700;color:var(--amarelo);font-size:12.5px;}
  details.como-conta p{margin:8px 0 2px;line-height:1.6;color:var(--text);max-width:1000px;}
  .destaques .lk-conta{color:var(--amarelo) !important;white-space:nowrap;}
  .sug-box{position:absolute;z-index:60;left:0;right:0;top:calc(100% + 4px);background:var(--panel);border:1px solid var(--amarelo);border-radius:8px;max-height:300px;overflow:auto;box-shadow:0 10px 24px rgba(0,0,0,.45);text-align:left;}
  .sug-box button{display:flex;justify-content:space-between;gap:10px;width:100%;background:none;border:0;border-bottom:1px solid var(--border);color:var(--text);font:inherit;font-size:13.5px;padding:8px 12px;cursor:pointer;text-align:left;}
  .sug-box button:last-child{border-bottom:0;} .sug-box button:hover,.sug-box button.on{background:rgba(245,228,0,.12);}
  .sug-box button small{color:var(--muted);font-size:11.5px;white-space:nowrap;} .sug-box button small.fora{color:var(--rosa);}
  .sug-box .sug-nada{padding:9px 12px;font-size:13px;color:var(--muted);}
</style>'''
i = s.rindex('</style>'); s = s[:i] + CSS3 + s[i + len('</style>'):]
troca('</body>', r'''<script>
// proposta_etapa3 (13/11/2026)
// 13.2 como se conta: sempre o Brasil inteiro, calculado dos mesmos dados
(() => {
  const el = document.getElementById('comoContaTxt'); if (!el) return;
  const all = [...MUNI.values()], c = st => all.filter(m => m.tz_status === st).length;
  const uni = c('Ativa'), par = c('Parcial (ativa)'), enc = c('Encerrada');
  const exc = all.filter(m => /Excluída/.test(m.tz_status || '')).length, reg = all.filter(m => /Regulamentada/.test(m.tz_status || '')).length, pis = all.filter(m => /Pista/.test(m.tz_status || '')).length;
  const tot = uni + par + enc + exc + reg + pis, n45 = countParciais(all), f = n => n.toLocaleString('pt-BR');
  el.innerHTML = `<p>A base da pesquisa tem <b>${f(tot)}</b> municípios com alguma política de Tarifa Zero registrada. Destes, <b>${f(uni + par + enc)}</b> estão no escopo e foram verificados na norma, no contrato ou na prova de operação: <b>${f(uni)}</b> com Tarifa Zero universal em vigor, <b>${f(par)}</b> com gratuidade parcial confirmada e <b>${f(enc)}</b> encerradas. Ficam fora ${f(exc)} fora de escopo, ${f(reg)} regulamentadas e não implantadas e ${f(pis)} pistas a verificar.</p>
    <p>A régua descritiva conta <b>${f(n45)}</b> parciais: as ${f(par)} confirmadas e mais ${f(Math.max(0, n45 - par))} achadas na busca exploratória da camada 2, que não é exaustiva e por isso não entra na base verificada. Os cartões acima respondem ao recorte dos filtros; esta caixa é sempre o Brasil inteiro.</p>`;
  document.addEventListener('click', e => { const a = e.target.closest('.lk-conta'); if (!a) return; e.preventDefault(); const d = document.getElementById('comoConta'); d.open = true; d.scrollIntoView({ behavior: 'smooth', block: 'center' }); });
})();
// 13.1 a lista também acompanha o filtro da régua e o de Tarifa Zero; primeira contagem
renderTZTable();
// 13.3 busca de município: sugestões na página, Enter com o nome sem UF, aviso de fora do recorte
(() => {
  const rot = m => `${m.nome} – ${m.uf}`;
  const casa = q => {
    q = (q || '').trim(); if (!q) return [];
    const uf = (q.match(/(?:[–\-\/(,]\s*|\s)([A-Za-z]{2})\)?\s*$/) || [])[1];
    const nome = normBusca(uf ? q.replace(/\s*(?:[–\-\/(,]\s*|\s)[A-Za-z]{2}\)?\s*$/, '') : q);
    const okUf = x => !uf || x.m.uf === uf.toUpperCase();
    const ex = MUNI_BUSCA.filter(x => normBusca(x.m.nome) === nome && okUf(x));
    const ini = MUNI_BUSCA.filter(x => normBusca(x.m.nome).startsWith(nome) && okUf(x) && !ex.includes(x));
    const meio = nome.length >= 3 ? MUNI_BUSCA.filter(x => normBusca(x.rot).includes(nome) && !ex.includes(x) && !ini.includes(x)) : [];
    const pop = (a, b) => (b.m.pop || 0) - (a.m.pop || 0);
    return [...ex.sort(pop), ...ini.sort(pop), ...meio.sort(pop)].map(x => x.m);
  };
  for (const id of ['muniSearch', 'buscaTopo', 'buscaGrupo']) {
    const inp = document.getElementById(id); if (!inp) continue;
    inp.removeAttribute('list');
    const pai = inp.parentElement; if (getComputedStyle(pai).position === 'static') pai.style.position = 'relative';
    const box = document.createElement('div'); box.className = 'sug-box'; box.hidden = true; box.setAttribute('role', 'listbox'); pai.appendChild(box);
    let lista = [], ativo = -1;
    const escolhe = m => { inp.value = rot(m); box.hidden = true; inp.dispatchEvent(new Event('input')); inp.dispatchEvent(new Event('change')); };
    const mostra = () => {
      const q = inp.value.trim();
      if (q.length < 2 || MUNI_POR_ROTULO.has(q)) { box.hidden = true; return; }
      lista = casa(q).slice(0, 8); ativo = -1;
      box.innerHTML = lista.length ? lista.map((m, i) => {
        const fora = id === 'muniSearch' && typeof passesFilter === 'function' && !passesFilter(m);
        return `<button type="button" data-i="${i}">${m.nome} – ${m.uf}<small${fora ? ' class="fora"' : ''}>${fora ? 'fora do recorte dos filtros' : ({ 'Ativa': 'Tarifa Zero universal', 'Parcial (ativa)': 'gratuidade parcial', 'Encerrada': 'Tarifa Zero encerrada' }[m.tz_status] || (m.pop || 0).toLocaleString('pt-BR') + ' hab.')}</small></button>`; }).join('')
        : '<div class="sug-nada">Nenhum município com esse nome.</div>';
      box.hidden = false;
    };
    inp.addEventListener('input', mostra);
    inp.addEventListener('focus', mostra);
    inp.addEventListener('blur', () => setTimeout(() => { box.hidden = true; }, 160));
    box.addEventListener('mousedown', e => { const b = e.target.closest('button[data-i]'); if (!b) return; e.preventDefault(); escolhe(lista[+b.dataset.i]); });
    inp.addEventListener('keydown', e => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        if (box.hidden || !lista.length) return; e.preventDefault();
        ativo = (ativo + (e.key === 'ArrowDown' ? 1 : -1) + lista.length) % lista.length;
        box.querySelectorAll('button').forEach((b, i) => b.classList.toggle('on', i === ativo)); return;
      }
      if (e.key === 'Escape') { box.hidden = true; return; }
      if (e.key !== 'Enter') return;
      if (MUNI_POR_ROTULO.has(inp.value.trim())) { box.hidden = true; return; }
      const m = ativo >= 0 ? lista[ativo] : casa(inp.value)[0];
      if (m) { e.preventDefault(); escolhe(m); }
    });
  }
})();
</script>
<meta name="proposta" content="proposta_etapa3">
</body>''')
open(ARQ, 'w', encoding='utf-8').write(s)
print('etapa 3 do painel aplicada:', ARQ, len(s.encode()), 'bytes')
