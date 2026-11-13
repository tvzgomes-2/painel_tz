#!/usr/bin/env python3
"""
rede_etapa2.py — leva à Rede de empresas a padronização do painel de teste (13/11/2026).

Roda DEPOIS de gerar_proposta.py e altera rede-ge-proposta.html no lugar, como proposta_etapa2.py faz
com o painel: caixas recolhidas e numeradas no modelo de Dados e conceitos, setas grandes, menos texto
(resumo curto no cabeçalho de cada caixa), card do grupo com ações no topo e carimbos, chamada para
contribuir em destaque, "Baixar os dados" discreto e as notas de método recolhidas no pé da página.
Uso: python3 scripts/rede_etapa2.py [rede-ge-proposta.html]
"""
import os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, 'rede-ge-proposta.html')
s = open(ARQ, encoding='utf-8').read()
assert 'rede_etapa2' not in s, 'etapa 2 já aplicada — rode gerar_proposta.py antes'

def troca(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, f'âncora com {c} ocorrência(s), esperado {n}: {a[:100]!r}'
    s = s.replace(a, b)

def sub1(padrao, novo, flags=re.S):
    global s
    s2, k = re.subn(padrao, novo, s, count=1, flags=flags)
    assert k == 1, f'padrão não achado: {padrao[:100]!r}'
    s = s2

# ------------------------------------------------------------------ 0. versão: proposta da revisão de lançamento (v1.0.0)
s = s.replace('Versão de teste da revisão (proposta v1.1). ', 'Proposta em teste para a revisão de lançamento (v1.0.0). ')
s = s.replace('<span class="badge">rede · proposta v1.1</span>', '<span class="badge">rede · v1.0.0 · proposta</span>')
s = s.replace('Rede de empresas v0.2 · 2026<br>', 'Rede de empresas v1.0.0 · era Canoa · base de 11/11/2026<br>')
s = s.replace(' — instrumento exploratório da pesquisa; não substitui a análise da tese (Capítulo 6 e Apêndice E).', ' — o método completo e os limites estão na tese (Capítulo 6 e Apêndice E).')

# ------------------------------------------------------------------ 1. CSS comum com o painel
troca('</style>\n</head>', '''  /* ===== rede_etapa2 (13/11/2026) — o mesmo sistema do painel de teste ===== */
  nav.tabs .tabbtn small{display:none !important;}
  details.pacote{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin:16px 0 0;}
  .phead{display:flex;gap:14px;align-items:flex-start;margin:0;cursor:pointer;list-style:none;}
  .phead::-webkit-details-marker{display:none;}
  .phead > div{flex:1 1 auto;min-width:0;}
  .phead h2{margin:2px 0 4px;font-size:18px;text-transform:none;letter-spacing:0;border:none;padding:0;}
  .phead h2::after{display:none !important;}
  .phead p{margin:0 0 4px;font-size:13.5px;line-height:1.55;color:var(--text);}
  .pnum{flex:0 0 auto;width:32px;height:32px;border-radius:50%;background:var(--rosa);color:#fff;font-weight:800;display:flex;align-items:center;justify-content:center;font-size:15px;}
  .pseta{flex:0 0 auto;font-size:30px;line-height:.8;color:var(--muted);transition:transform .15s;}
  details.pacote[open] > .phead{margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--border);}
  details.pacote[open] > .phead .pseta{transform:rotate(180deg);color:var(--amarelo);}
  details.pacote > .phead:hover .pseta, details.pacote > .phead:hover h2{color:var(--amarelo);}
  details > summary::marker{font-size:1.35em;}
  .legenda{font-size:12.5px;color:var(--muted);margin:2px 0 10px;line-height:1.5;max-width:900px;}
  .carimbos{margin:10px 0 4px;display:grid;gap:8px;}
  .cb-g{display:grid;grid-template-columns:96px 1fr;gap:8px;align-items:start;}
  .cb-t{font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);padding-top:6px;}
  .carimbo{--c:#c4c4cf;display:inline-block;border:2px solid var(--c);color:var(--c);border-radius:6px;padding:2px 8px;margin:2px 6px 4px 0;
    font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.03em;line-height:1.35;transform:rotate(-1.5deg);background:rgba(255,255,255,.02);}
  .carimbo:nth-child(even){transform:rotate(1deg);}
  @media (max-width:640px){ .cb-g{grid-template-columns:1fr;gap:2px;} .cb-t{padding-top:0;} }
  .card-acoes{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 4px;padding:0 0 8px;border-bottom:1px solid var(--border);}
  .card-acoes .bt2{font-size:12px;padding:7px 11px;margin:0;}
  details.fichapol{background:var(--panel2);border:1px solid var(--border);border-radius:8px;padding:8px 12px;margin:10px 0 0;}
  details.fichapol > summary{cursor:pointer;font-weight:700;font-size:14px;}
  .contribua{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px 20px;background:rgba(245,228,0,.07);
    border:3px solid var(--amarelo);border-radius:12px;padding:26px 28px;margin:22px 0 0;}
  .contribua b{display:block;font-size:23px;line-height:1.25;margin-bottom:6px;} .contribua span{font-size:14.5px;color:var(--text);}
  .contribua .bt1{font-size:16px;padding:14px 26px;}
  aside.cta-dados{background:none !important;border:none !important;border-top:1px solid var(--border) !important;border-radius:0 !important;padding:12px 0 !important;margin:22px 0 0 !important;}
  aside.cta-dados .cta-txt b{font-size:13px !important;display:inline !important;margin-right:6px;}
  aside.cta-dados .cta-txt span{display:inline !important;}
  aside.cta-dados .cta-btn{background:none !important;color:var(--text) !important;border:1px solid var(--border);padding:6px 12px !important;font-size:12.5px !important;}
  aside.cta-dados .cta-btn:hover{border-color:var(--amarelo);filter:none;}
  details.rodape-sobre{margin:26px 0 0;padding:10px 0 0;border-top:1px solid var(--border);font-size:12.5px;color:var(--muted);}
  details.rodape-sobre > summary{cursor:pointer;font-size:12.5px;color:var(--muted);}
  details.rodape-sobre[open] > summary{margin-bottom:10px;color:var(--text);}
  details.rodape-sobre h3{font-size:13px;margin:14px 0 6px;color:var(--text);}
  .ponte-tz{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin:16px 0 0;}
  .ponte-tz h2{color:var(--rosa);}
</style>
</head>''')

# ------------------------------------------------------------------ 2. caixas recolhidas e numeradas (Quem controla)
def caixa_de_panel(abre_regex, n, titulo, resumo, ident=None, aberta=False):
    """Troca '<div class="panel" ...>\\n    <h2>Título</h2>\\n    <p class="sub">…</p>' pelo cabeçalho de caixa; o </div> final vira </details>."""
    global s
    m = re.search(abre_regex, s, flags=re.S)
    assert m, abre_regex[:80]
    i = m.start()
    # fecha a div do painel: acha o </div> que equilibra a abertura
    prof, k = 0, i
    while True:
        a = s.find('<div', k); f = s.find('</div>', k)
        if a != -1 and a < f: prof += 1; k = a + 4
        else:
            prof -= 1; k = f + 6
            if prof == 0: break
    bloco = s[m.end():f]
    cab = (f'<details class="pacote"{f" id={chr(34)}{ident}{chr(34)}" if ident else ""}{" open" if aberta else ""}><summary class="phead"><span class="pnum">{n}</span>'
           f'<div><h2>{titulo}</h2><p>{resumo}</p></div><span class="pseta" aria-hidden="true">▾</span></summary>')
    s = s[:i] + cab + bloco + '</details>' + s[k:]

caixa_de_panel(r'<div class="panel" style="margin-top:16px;" id="agrupamentos">\n    <h2>Do grupo à federação</h2>\n    <p class="sub">.*?</p>',
               1, 'Quanto o capital se concentra', '22 unidades de controle detêm metade do capital do setor. A tese junta os grupos numa escala de confiança, de A a D.', 'agrupamentos')
caixa_de_panel(r'<div class="panel" style="margin-top:16px;">\n    <h2>Os 327 grupos econômicos mapeados</h2>\n    <p class="sub">.*?</p>',
               2, 'Os 327 grupos econômicos', 'A lista completa, com capital, empresas, sócios e municípios. Ordene pelo cabeçalho; clique numa linha para abrir a ficha.', 'lista-grupos')
caixa_de_panel(r'<div class="panel" style="margin-top:16px;">\n    <h2>Onde os grupos estão</h2>\n    <p class="sub">.*?</p>',
               3, 'Onde os grupos estão', 'Os grupos de maior alcance e os que têm endereço em cada município. Endereço não é operação.', 'onde-grupos')
# "E a Tarifa Zero?": ponte para o painel, visível; e a chamada para contribuir logo depois
sub1(r'<div class="panel" style="margin-top:16px;border:2px solid var\(--rosa\);">\n    <h2>E a Tarifa Zero\?</h2>',
     '<div class="ponte-tz">\n    <h2>E a Tarifa Zero?</h2>')
i = s.index('<div class="ponte-tz">'); j = s.index('\n  </div>', i) + len('\n  </div>')
s = s[:j] + ('\n  <div class="contribua"><div><b>Conhece um grupo ou uma empresa que falta aqui?</b><span>Envie para a pesquisa um grupo, uma ligação societária ou um contrato de operação. Cada contribuição é revisada antes de entrar no site.</span></div>'
             '<a class="bt1" href="pesquisa.html">Envie para a pesquisa →</a></div>') + s[j:]

# rede: legenda curta, ajustes do desenho recolhidos, medidas fechadas
sub1(r'(<h2>A rede dos grupos</h2>\n      )<p class="sub">.*?</p>',
     r'\1<p class="legenda">Cada círculo é um grupo; cada linha, uma ligação: <b style="color:var(--rosa);">rosa</b>, mesmo bloco de controle; <b>cinza</b>, sócio em comum. Clique num grupo para abrir a ficha.</p>')
troca('        <div class="forcas" id="redeForcas">', '        <details class="mais forcas-cx"><summary>Ajustes do desenho</summary>\n        <div class="forcas" id="redeForcas">')
troca('          <button id="fOrig" title="Volta ao desenho empacotado por componente">Desenho original</button>\n        </div>',
      '          <button id="fOrig" title="Volta ao desenho empacotado por componente">Desenho original</button>\n        </div>\n        </details>')
troca('<details class="medidas" open><summary>Medidas da rede (ARS)</summary>', '<details class="medidas"><summary>Medidas da rede (ARS)</summary>')
troca('</style>\n</head>', '  details.forcas-cx{display:inline-block;margin:0 8px 0 0;font-size:12px;} details.forcas-cx > summary{cursor:pointer;color:var(--muted);}\n</style>\n</head>')

# ------------------------------------------------------------------ 3. Além do ônibus: as mesmas caixas
sub1(r'<div class="paneintro">\n    <p>A aba <a href="#" class="ponte-aba" data-aba="controle" style="margin:0">Quem controla</a>.*?</div>\n',
     '<div class="paneintro"><p class="resposta" style="border-left:3px solid var(--rosa);padding-left:12px;font-size:15px;color:var(--text);">Além do ônibus: as holdings sócias das empresas de transporte e os negócios dos sócios dessas holdings em outros setores. Vínculo de sócio não é controle.</p></div>\n')
ALEM = [
 (r'<div class="panel">\n    <h2>Como se lê a cadeia</h2>\n    <p class="sub">.*?</p>', 1, 'Como se lê a cadeia', 'Do grupo de ônibus à holding sócia e às empresas de outros setores dos sócios dela, em três camadas.', 'alem-cadeia', True),
 (r'<div class="panel" style="margin-top:16px;">\n    <h2>Em que setores</h2>\n    <p class="sub">.*?</p>', 2, 'Em que setores', 'Os setores das empresas em que os sócios das holdings também são sócios.', 'alem-setores', False),
 (r'<div class="panel" style="margin-top:16px;" id="patGrupo">\n    <h2>Explorar um grupo</h2>\n    <p class="sub">.*?</p>', 3, 'Explore um grupo', 'Escolha um grupo e veja as holdings sócias e os negócios dos sócios fora do ônibus.', 'patGrupo', True),
 (r'<div class="panel" style="margin-top:16px;">\n    <h2>Os grupos com mais negócios fora do ônibus</h2>\n    <p class="sub">.*?</p>', 4, 'Os grupos com mais negócios fora do ônibus', 'Quantas empresas de outros setores cada grupo alcança pelos sócios das holdings. Clique numa linha para explorar o grupo.', 'alem-ranking', False),
 (r'<div class="panel" style="margin-top:16px;">\n    <h2>Onde os grupos se encontram fora do ônibus</h2>\n    <p class="sub">.*?</p>', 5, 'Onde os grupos se encontram fora do ônibus', 'Empresas de outros setores em que sócios de grupos diferentes estão juntos.', 'alem-encontros', False),
]
for rx, n, tit, res, ident, aberta in ALEM:
    caixa_de_panel(rx, n, tit, res, ident, aberta)

# ------------------------------------------------------------------ 4. notas de método e "o que esta página não mostra": no pé da página, recolhidos
def corta(ini, fim_incl):
    global s
    i = s.index(ini); j = s.index(fim_incl, i) + len(fim_incl)
    t = s[i:j]; s = s[:i] + s[j:]; return t
nao = corta('\n    <details class="nota"><summary>O que esta página não mostra</summary>', '</details>')
n1 = corta('  <details class="panel" style="margin-top:16px;">\n    <summary>Notas metodológicas e limites de leitura</summary>', '  </details>\n')
n2 = corta('  <details class="panel" style="margin-top:16px;" open>\n    <summary>Notas metodológicas e limites de leitura</summary>', '  </details>\n')
notas = lambda t: t[t.index('<div class="notes">'):t.rindex('</div>') + 6]
nao_txt = re.sub(r'^.*?<p class="sub" style="margin:6px 0 0;">', '<p>', nao, flags=re.S).replace('</p></details>', '</p>')
i = s.index('  <aside class="cta-dados"')
s = s[:i] + ('  <details class="rodape-sobre" id="sobre"><summary>Sobre os dados, o método e os limites</summary>\n'
             '    <h3>O que esta página não mostra</h3>' + nao_txt +
             '\n    <h3>Quem controla</h3>' + notas(n1) + '\n    <h3>Além do ônibus</h3>' + notas(n2) + '\n  </details>\n') + s[i:]

# ------------------------------------------------------------------ 5. card do grupo: ações no topo, carimbos, números recolhidos
troca("""  box.innerHTML = `<div><b style="font-size:15px;">${esc(nomeG(n))}</b>${n.topo ? ' <span class="tag" style="background:rgba(245,228,0,.16);color:#F5E400;">topo do capital</span>' : ''}</div>
    ${subG(n) ? `<div class="mercado">${esc(subG(n))} <span class="muted">· rótulo do cálculo</span></div>` : ''}
    <table>""", """  const car = (t, c, tt) => `<span class="carimbo" style="--c:${c}"${tt ? ` title="${String(tt).replace(/"/g, '&quot;')}"` : ''}>${t}</span>`;
  const cbs = [];
  if (n.topo) cbs.push(car('Topo do capital', '#F5E400', 'Entre os grupos que, juntos, detêm metade do capital declarado do setor'));
  if (u && multi) cbs.push(car(`Unidade ${u.id} · grau ${u.grau || 'B'}`, '#FF2D6B', `${u.membros.length} grupos fundidos por controle comum`));
  if (fc) cbs.push(car('Família de controle', '#FF2D6B', fc.nome));
  if (lin) cbs.push(car('Linhagem', '#B48CFF', lin.nome));
  if (fed) cbs.push(car(`Federação ${fed.id}`, '#4C8DFF', 'Articulação, e não controle'));
  const cbn = [car(`${fmt(n.n_emp || 0)} ${n.n_emp === 1 ? 'empresa' : 'empresas'}`, '#c4c4cf'), car(`${fmt(cods.length)} ${cods.length === 1 ? 'município' : 'municípios'} com endereço`, '#c4c4cf')];
  if (n.capital) cbn.push(car(`R$ ${mi(n.capital)} mi de capital`, '#c4c4cf', `${pctCap(n.capital)} do capital declarado do setor`));
  if (n.lig) cbn.push(car(`${n.lig} ${n.lig === 1 ? 'ligação' : 'ligações'} na rede`, '#c4c4cf'));
  if (window.PAT?.tem(id)) cbn.push(car('Negócios fora do ônibus', '#6FBE44'));
  box.innerHTML = `<div><b style="font-size:17px;">${esc(nomeG(n))}</b></div>
    ${subG(n) ? `<div class="mercado">${esc(subG(n))} <span class="muted">· rótulo do cálculo</span></div>` : ''}
    <div class="card-acoes"><button type="button" class="bt2" data-copia-ge="${id}">Copiar o link deste grupo</button><a class="bt2" href="pesquisa.html?grupo=${encodeURIComponent(nomeG(n))}">Corrigir ou contribuir</a></div>
    <div class="carimbos">${cbs.length ? `<div class="cb-g"><span class="cb-t">Controle</span><div>${cbs.join('')}</div></div>` : ''}<div class="cb-g"><span class="cb-t">Tamanho</span><div>${cbn.join('')}</div></div></div>
    <details class="fichapol"><summary>Os números do grupo</summary>
    <table>""")
troca("""    </table>
    <div class="agrup">""", """    </table></details>
    <details class="fichapol"><summary>Por trás dos carimbos: agrupamentos</summary>
    <div class="agrup">""")
troca("""    <p class="sub" style="margin:12px 0 4px;"><b>Onde tem endereço</b>""", """    </details>
    <p class="sub" style="margin:12px 0 4px;"><b>Onde tem endereço</b>""")
troca("document.getElementById('muniBusca').closest('.panel').scrollIntoView", "document.getElementById('muniBusca').closest('.panel, details.pacote').scrollIntoView")
s = s.replace('</body>', """<script>
// rede_etapa2: copiar o link do grupo; abrir a caixa certa quando se chega por endereço; avisar os gráficos ao abrir
document.addEventListener('click', e => {
  const b = e.target.closest('[data-copia-ge]'); if (!b) return;
  const url = location.href.split('#')[0] + '#' + b.dataset.copiaGe;
  (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(() => { b.textContent = 'Link copiado'; }, () => { b.textContent = url; });
});
document.querySelectorAll('details.pacote').forEach(d => d.addEventListener('toggle', () => { if (d.open) window.dispatchEvent(new Event('resize')); }));
if (/^#mun-/.test(location.hash)) { const cx = document.getElementById('onde-grupos'); if (cx) { cx.open = true; setTimeout(() => cx.scrollIntoView({ behavior: 'smooth' }), 120); } }
</script>
<meta name="proposta" content="rede_etapa2">
</body>""", 1)
open(ARQ, 'w', encoding='utf-8').write(s)
print('etapa 2 da rede aplicada:', ARQ, len(s.encode()), 'bytes')
