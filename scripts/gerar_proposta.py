#!/usr/bin/env python3
"""
gerar_proposta.py — gera painel-proposta.html e rede-ge-proposta.html (13/11/2026).

Versão de TESTE da revisão "rumo ao Capítulo 9" (plano no Claude Docs, aprovado o fio em
cinco passos). Não toca em painel.html nem em rede-ge.html: lê os HTML montados e os moldes
(head.html, logic.js, head-ge.html, logic-ge.js), aplica as transformações por âncora exata
e grava os arquivos com nome diferente, para comparar lado a lado. Rodar depois de
montar_html.sh e montar_rede_ge.sh. Se a proposta for aprovada, as transformações passam
para os moldes e este script é aposentado.
"""
import re, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
S = RAIZ / 'scripts'
TESE_PDF = 'tese/Tese%20-%20Volume%20I%20-%20Texto.pdf'

def troca(s, a, b, n=1):
    c = s.count(a)
    assert c == n, f'âncora com {c} ocorrência(s), esperado {n}: {a[:90]!r}'
    return s.replace(a, b)

# ------------------------------------------------------------------ sistema comum (as duas páginas)
CSS_COMUM = '''
  /* ===== proposta da revisão de lançamento (v1.0.0) (13/11/2026): sistema comum de navegação — o mesmo nas três páginas ===== */
  :root{ --accent: var(--rosa); }
  /* abas: as mesmas de Dados e conceitos (.abas button), com especificidade acima de "nav.tabs .tabbtn" dos moldes */
  nav.tabs{display:flex !important;gap:10px !important;margin:6px 0 26px !important;flex-wrap:wrap !important;padding:0 0 14px !important;border-bottom:1px solid var(--border) !important;overflow:visible !important;}
  nav.tabs .tabbtn{background:var(--panel2) !important;border:2px solid var(--border) !important;color:var(--text) !important;font:inherit;
    font-size:16px !important;font-weight:800 !important;letter-spacing:.01em;padding:12px 26px !important;border-radius:10px !important;margin:0 !important;
    box-shadow:none !important;cursor:pointer;transition:border-color .15s,background .15s;text-align:center;}
  nav.tabs .tabbtn:hover{border-color:var(--amarelo) !important;background:var(--panel2) !important;}
  nav.tabs .tabbtn.on{background:var(--amarelo) !important;border-color:var(--amarelo) !important;color:#0E0E10 !important;box-shadow:none !important;}
  nav.tabs .tabbtn:focus-visible{outline:3px solid var(--rosa);outline-offset:2px;}
  nav.tabs .tabbtn small{display:none !important;}
  @media (max-width:640px){ nav.tabs .tabbtn{flex:1 1 0 !important;padding:11px 12px !important;font-size:15px !important;} }
  .btn-clear,.maptools button,.forcas button,.lermais{border-radius:8px !important;}
  .btn-clear:hover,.maptools button:hover,.forcas button:hover,.zoombtns button:hover,.lermais:hover{border-color:var(--amarelo) !important;}
  .bt1,.bt2{display:inline-block;font:inherit;font-size:13px;font-weight:700;border-radius:8px;padding:9px 16px;text-decoration:none !important;cursor:pointer;margin:4px 8px 4px 0;}
  .bt1{background:var(--rosa);color:#fff !important;border:2px solid var(--rosa);}
  .bt1:hover{filter:brightness(1.12);}
  .bt2{background:var(--panel2);color:var(--text) !important;border:2px solid var(--border);}
  .bt2:hover{border-color:var(--amarelo);}
  .faixa-proposta{background:var(--amarelo);color:#0E0E10;font-size:12.5px;font-weight:600;padding:7px 16px;text-align:center;}
  .faixa-proposta a{color:#0E0E10 !important;text-decoration:underline;font-weight:800;}
  .resposta{font-size:15px;line-height:1.55;color:var(--text);margin:0 0 10px;max-width:900px;border-left:3px solid var(--rosa);padding:2px 0 2px 12px;}
  .passo-pe{display:flex;align-items:center;flex-wrap:wrap;gap:6px 14px;margin:12px 0 0;padding-top:10px;border-top:1px dashed var(--border);font-size:12.5px;color:var(--muted);}
  .passo-pe .na-tese a{color:var(--muted) !important;}
  details.mais{margin-top:14px;}
  details.mais > summary{cursor:pointer;font-weight:700;font-size:13.5px;color:var(--text);padding:8px 0;}
  .trilha{display:flex;flex-wrap:wrap;gap:6px 18px;align-items:center;font-size:13px;margin:14px 0 4px;padding:10px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;}
  .trilha b{color:var(--amarelo);}
  .trilha a{color:var(--text) !important;text-decoration:none;border-bottom:1px solid var(--rosa);}
  .trilha a:hover{color:var(--rosa) !important;}
'''
FAIXA = ('<div class="faixa-proposta">Proposta em teste para a revisão de lançamento (v1.0.0). '
         'Compare com a <a href="{atual}">página atual</a>.</div>\n')

def nav_proposta(s):
    s = s.replace('href="painel.html"', 'href="painel-proposta.html"')
    s = s.replace('href="rede-ge.html"', 'href="rede-ge-proposta.html"')
    return s

# ================================================================== PAINEL
head = (S / 'head.html').read_text(encoding='utf-8')
logic = (S / 'logic.js').read_text(encoding='utf-8')
painel = (RAIZ / 'painel.html').read_text(encoding='utf-8')
assert painel.startswith(head), 'painel.html não começa com head.html — rode montar_html.sh antes'
i_logic = painel.rindex(logic)

h = head
h = troca(h, '</style>\n</head>', CSS_COMUM + '''  .abre-box{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin:0 0 22px;}
  .abre-box .pergunta{font-size:19px;font-weight:800;line-height:1.35;margin:0 0 8px;}
  .abre-box .passos{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 0;}
  .abre-box .passos a{background:var(--panel2);border:1px solid var(--border);border-radius:8px;padding:6px 11px;font-size:12.5px;color:var(--text) !important;text-decoration:none;}
  .abre-box .passos a:hover{border-color:var(--amarelo);}
  .abre-busca{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:12px;}
  .abre-busca input{flex:1 1 260px;max-width:420px;background:var(--panel2);border:2px solid var(--border);border-radius:8px;color:var(--text);font:inherit;font-size:14px;padding:9px 12px;}
  .abre-busca input:focus{border-color:var(--amarelo);outline:none;}
  .leitura{display:block !important;margin:0 0 12px;}
  .testes{width:100%;border-collapse:collapse;font-size:13px;margin:6px 0 4px;}
  .testes td{padding:7px 8px;border-bottom:1px solid var(--border);vertical-align:top;}
  .testes td.or{font-weight:800;font-size:16px;white-space:nowrap;color:var(--amarelo);}
  .fecho{background:rgba(255,45,107,.08);border:2px solid var(--rosa);border-radius:12px;padding:20px 22px;margin:8px 0 0;}
  .fecho .frase{font-size:20px;font-weight:800;line-height:1.35;margin:0 0 10px;}
  .explorar-nav{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:-4px 0 16px;font-size:12.5px;color:var(--muted);}
  .explorar-nav a{background:var(--panel2);border:1px solid var(--border);border-radius:8px;padding:5px 10px;color:var(--text) !important;text-decoration:none;}
  .explorar-nav a:hover{border-color:var(--amarelo);}
  .bloco-explorar{margin-top:30px;padding-top:6px;border-top:2px solid var(--border);}
  /* a barra de filtros fica presa no topo (110 px no computador): o alvo de uma âncora para logo abaixo dela */
  .secao,.bloco-explorar,.tabpane,.paneintro{scroll-margin-top:128px;}
  @media (max-width:640px){ .secao,.bloco-explorar,.tabpane,.paneintro{scroll-margin-top:12px;} }
</style>
</head>''')
h = troca(h, '<body>\n', '<body>\n' + FAIXA.format(atual='painel.html'))
h = nav_proposta(h)
h = troca(h, '<span class="badge">painel · v1.0.0</span>', '<span class="badge">painel · v1.0.0 · proposta</span>')
# cabeçalho: a apresentação longa sai (o argumento passa a ser a abertura do Panorama)
h = re.sub(r'\n    <p class="resumo">.*?</p>', '', h, count=1, flags=re.S)
h = re.sub(r'\n    <p class="univ">.*?</p>', '', h, count=1, flags=re.S)
h = re.sub(r'<p class="abertura">.*?</p>',
           '<p class="abertura">Siga o argumento da tese em cinco passos ou vá direto ao Explorar e trabalhe com os dados dos 5.570 municípios.</p>',
           h, count=1, flags=re.S)
h = troca(h, '<button class="lermais" id="lerMais" type="button" hidden>Ler mais sobre a pesquisa ▾</button>\n', '')
# abas: duas
h = re.sub(r'<nav class="tabs" role="tablist" aria-label="Áreas do painel">.*?</nav>',
           '<nav class="tabs" role="tablist" aria-label="Áreas do painel">\n'
           '    <button class="tabbtn" role="tab" id="tabbtn-panorama" data-tab="panorama">O argumento</button>\n'
           '    <button class="tabbtn" role="tab" id="tabbtn-explorar" data-tab="explorar">Explorar</button>\n  </nav>',
           h, count=1, flags=re.S)

# ---- o Panorama, refeito nos cinco passos
a = h.index('<section class="tabpane" id="tab-panorama"'); b = h.index('<section class="tabpane" id="tab-explorar"')
L = h[a:b].split('\n')
def linha(trecho):
    achadas = [l for l in L if trecho in l]
    assert len(achadas) == 1, (trecho, len(achadas)); return achadas[0]
def bloco(ini, fim):
    i = next(k for k, l in enumerate(L) if ini in l); j = next(k for k in range(i, len(L)) if fim in L[k])
    return '\n'.join(L[i:j + 1])
P = {
 'uf': linha('Tarifa Zero por região e por UF'), 'tempo': linha('Linha do tempo das adoções'),
 'porte': linha('Adoção por porte'), 'regua': bloco('<div class="reguabox">', '<p class="relunivs"'),
 'arranjo': linha('O arranjo do contrato'), 'pago': linha('Como o operador é pago'),
 'contra': linha('A contrapartida —'), 'alvo': linha('A régua analítica — a quem serve'),
 'cruz': linha('As duas réguas cruzadas'), 'custo': linha('id="custoPanel"'),
 'alcance': linha('Do piso à Tarifa Zero universal'),
}
def cab(n, tit, sid):
    return (f'    <section class="secao" id="{sid}">\n      <div class="sechead"><span class="secnum">{n}</span><h2>{tit}</h2>'
            f'<a class="topo-sec" href="#tab-panorama">↑ topo</a></div>\n')
def pe(cruze, rotulo, tese):
    return (f'      <div class="passo-pe"><button type="button" class="bt2" data-cruze="{cruze}">Cruze você: {rotulo} no mapa →</button>'
            f'<span class="na-tese">Na tese: <a href="{TESE_PDF}" target="_blank" rel="noopener">{tese}</a></span></div>\n    </section>\n')
novo = '''<section class="tabpane" id="tab-panorama" role="tabpanel" aria-labelledby="tabbtn-panorama">
    <div class="abre-box">
      <p class="pergunta">Por que a Tarifa Zero é mais adotada onde o sistema de ônibus é menos consolidado?</p>
      <p class="resposta">A resposta da tese: onde não há contrato de ônibus a preservar, a gratuidade entra por qualquer via; onde o mercado é atrativo, ela entra quando cabe no contrato vigente.</p>
      <div class="passos"><a href="#sec-p1">1 · Onde há Tarifa Zero</a><a href="#sec-p2">2 · Quem opera o ônibus</a><a href="#sec-p3">3 · Como a gratuidade entra</a><a href="#sec-p4">4 · Quem paga</a><a href="#sec-p5">5 · A quem serve o subsídio</a></div>
      <div class="abre-busca"><input id="buscaTopo" list="muniList" placeholder="Procure a sua cidade…" autocomplete="off" spellcheck="false" aria-label="Procure a sua cidade"><span class="sub">abre a ficha do município no Explorar</span></div>
    </div>
''' + cab(1, 'Onde há Tarifa Zero?', 'sec-p1') + '''      <div class="leitura" id="leit-onde"></div>
''' + P['tempo'] + '\n' + P['porte'] + '''
      <div class="leitura" id="leit-como" style="margin-top:18px;"></div>
''' + P['regua'] + '\n' + pe('faixa_pop', 'porte', 'Capítulo 5') + '\n' + cab(2, 'Quem opera o ônibus?', 'sec-p2') + '''      <p class="resposta">Onde o mercado é atrativo, há grupo econômico: 327 grupos controlam empresas de transporte coletivo, e 22 unidades de controle detêm metade do capital do setor.</p>
      <div class="panel"><h3 class="pt">O que os testes de adoção dizem — presença de empresa de grupo no município</h3>
        <table class="testes">
          <tr><td class="or">0,28</td><td><b>Municípios satélites de arranjo.</b> Com empresa de grupo presente, a chance de adotar a Tarifa Zero é pouco mais de um quarto da chance sem grupo.</td></tr>
          <tr><td class="or">0,36</td><td><b>Polos de arranjo.</b> Cerca de um terço da chance.</td></tr>
          <tr><td class="or">—</td><td><b>Cidades isoladas.</b> A presença de grupo não faz diferença.</td></tr>
        </table>
        <details class="nota"><summary>Como ler</summary><p class="sub" style="margin:6px 0 0;">Razão de chances, com controle de porte, capacidade fiscal e estado (Seção 8.1). Abaixo de 1, menos adoção. É associação, e não causa; e presença de empresa no cadastro não prova que o grupo opere o sistema. Por isso a tese fala do <i>papel</i>, e não da influência, dos grupos.</p></details>
        <p style="margin:12px 0 0;"><a class="bt1" href="rede-ge-proposta.html">Abrir a Rede de empresas →</a></p>
      </div>
''' + pe('tipo_arranjo', 'arranjo', 'Capítulo 6 e Seção 8.1') + '\n' + cab(3, 'Como a gratuidade entra?', 'sec-p3') + '''      <p class="resposta">Onde o operador é privado, a gratuidade entra pelo contrato, paga pela oferta e com o risco de demanda no município. Nos municípios de arranjo com operador de grupo, entrou por aditivo à concessão em 8 de 11 casos.</p>
''' + P['arranjo'] + '\n' + P['pago'] + '\n' + pe('modelo_prestacao_simples', 'modelo de prestação', 'Seções 7.2 e 8.2') + '\n' + cab(4, 'Quem paga?', 'sec-p4') + '''      <div class="leitura" id="leit-paga"></div>
''' + P['custo'] + '\n' + pe('rec_prop_pc', 'receita própria per capita', 'Seção 7.5') + '\n' + cab(5, 'A quem serve o subsídio?', 'sec-p5') + '''      <div class="leitura" id="leit-opera"></div>
''' + P['contra'] + '\n' + P['alvo'] + '''
      <details class="mais"><summary>Ver as duas réguas cruzadas — o portão e o destinatário</summary>
''' + P['cruz'] + '''
      </details>
''' + pe('tz', 'situação da Tarifa Zero', 'Seções 7.2 e 7.6') + '''
    <div class="fecho">
      <p class="frase">A gratuidade amplia o acesso, mas não decide a quem serve o subsídio. Essa decisão está no contrato.</p>
      <p class="sub" style="font-size:13.5px;color:var(--text);max-width:900px;">Quem paga é o município, sozinho. Onde o operador é privado, o recurso que substitui a tarifa o paga pela oferta, quase sempre sem nada em troca. Tarifa Zero sem controle público é transferência de renda ao operador com um benefício social acoplado; com custos e dados abertos e controle social, é a gestão do transporte como um comum.</p>
      <p style="margin:12px 0 0;"><a class="bt1" href="''' + TESE_PDF + '''" target="_blank" rel="noopener">Ler a tese (Capítulo 9) →</a><a class="bt2" href="#explorar">Trabalhar com os dados no Explorar</a><a class="bt2" href="dados.html#dados">Baixar os dados</a></p>
    </div>
  </section>
'''
h = h[:a] + novo + h[b:]

# ---- Explorar: atalhos no topo e o que desceu, no fim
# atalhos internos do Explorar: um sumário discreto ("Nesta aba"), abaixo do título — não uma segunda fileira de abas
h = re.sub(r'(<div class="paneintro"><h2>Explorar</h2><p>.*?</p></div>)',
           r'\1\n    <nav class="explorar-nav" aria-label="Nesta aba"><span>Nesta aba:</span><a href="#tab-explorar">Mapa e ficha</a><a href="#uf-alcance">Por UF e quem é alcançado</a>'
           r'<a href="#comparar">Comparar TZ × Não-TZ</a><a href="#literatura">Literatura</a><a href="#sobre">Sobre os dados</a></nav>',
           h, count=1, flags=re.S)
assert 'class="explorar-nav"' in h
m = re.search(r'\n  </section>\s*\n\s*<section class="tabpane" id="tab-comparar"', h)
assert m
extra = ('\n  <div class="bloco-explorar" id="uf-alcance">\n    <div class="paneintro"><h2>Por UF e quem é alcançado</h2><p>As políticas por região e UF e, para cada portão, quem tem direito à gratuidade e quando.</p></div>\n' + P['uf'] + '\n'
         '      <div class="leitura" id="leit-alcance" style="margin-top:14px;"></div>\n' + P['alcance'] + '\n  </div>')
h = h[:m.start()] + extra + h[m.start():]
# os 81 trabalhos do corpus vão para Dados e conceitos → Referências (decisão do autor, 13/11/2026)
h = re.sub(r'<div class="panel" style="margin-top:14px;"><h3 class="pt">Os 81 trabalhos do corpus</h3>.*?Apêndice C da tese\.</p></div>',
           '<div class="panel" style="margin-top:14px;"><h3 class="pt">Os 81 trabalhos do corpus</h3><p class="sub" style="margin:0 0 10px;">A lista completa do corpus, com a referência de cada trabalho e busca por autor, título ou ano, está nas referências bibliográficas.</p><a class="bt2" href="dados.html#ref-corpus">Ver o corpus em Dados e conceitos → Referências</a></div>',
           h, count=1, flags=re.S)
assert 'dados.html#ref-corpus' in h
for aba in ('comparar', 'literatura', 'sobre'):
    h = re.sub(r'(<section class="tabpane" id="tab-%s"[^>]*>)' % aba, r'\1<div class="bloco-explorar"></div>', h, count=1)

# ---- logic
g = logic
g = g.replace("'rede-ge.html", "'rede-ge-proposta.html").replace('"rede-ge.html', '"rede-ge-proposta.html').replace('`rede-ge.html', '`rede-ge-proposta.html').replace('href="rede-ge.html', 'href="rede-ge-proposta.html')
g = troca(g, "el.innerHTML =\n    `<div><i>O que mostra</i>${mostra}</div><div class=\"res\"><i>Resultado no Brasil</i>${res}</div><div><i>Ressalva</i>${ress}</div>`; };",
          "el.innerHTML =\n    `<p class=\"resposta\">${res}</p><details class=\"nota\"><summary>O que mostra e a ressalva</summary><p class=\"sub\" style=\"margin:6px 0 0;\">${mostra}</p><p class=\"sub\" style=\"margin:6px 0 0;\"><b>Ressalva.</b> ${ress}</p></details>`; };")
g = troca(g, "  bx.addEventListener('input', desenha); desenha();", "  if (tb && bx) { bx.addEventListener('input', desenha); desenha(); }")
g = troca(g, 'g += `<circle cx="${px.toFixed(1)}"', 'g += `<circle data-mun="${x.m.id}" style="cursor:pointer" cx="${px.toFixed(1)}"')
g = troca(g, """function abreAba(nome, semHash) {
  if (!ABAS.includes(nome)) nome = 'panorama';
  for (const a of ABAS) {
    const pane = document.getElementById('tab-' + a);
    const btn = document.getElementById('tabbtn-' + a);
    const on = a === nome;""", """// proposta da revisão de lançamento (v1.0.0): duas abas; Comparar, Literatura e Sobre os dados descem para dentro do Explorar
const DENTRO_EXPLORAR = { comparar: 1, literatura: 1, sobre: 1 };
function abreAba(nome, semHash) {
  let rolarPara = null;
  if (DENTRO_EXPLORAR[nome]) { rolarPara = 'tab-' + nome; nome = 'explorar'; }
  if (/^mun-\\d+/.test(nome || '')) nome = 'explorar';
  // âncora para um trecho (#uf-alcance, #sec-p3, #tab-explorar…): abre a aba que contém o trecho e rola até ele
  if (nome && !['panorama', 'explorar'].includes(nome) && !/^mun-\\d+/.test(nome)) {
    const el = document.getElementById(nome), pane = el && el.closest('.tabpane');
    if (el && (pane || el.classList.contains('tabpane'))) {
      rolarPara = nome;
      nome = (pane || el).id.replace('tab-', '');
      if (DENTRO_EXPLORAR[nome]) nome = 'explorar';
    }
  }
  if (!['panorama', 'explorar'].includes(nome)) nome = 'panorama';
  if (rolarPara) setTimeout(() => document.getElementById(rolarPara)?.scrollIntoView({ behavior: 'smooth' }), 60);
  for (const a of ABAS) {
    const pane = document.getElementById('tab-' + a);
    const btn = document.getElementById('tabbtn-' + a);
    const on = !!(a === nome || (nome === 'explorar' && DENTRO_EXPLORAR[a]));""")
g += r'''

// ---------- proposta da revisão de lançamento (v1.0.0) (13/11/2026): pontos de trabalho com os dados ----------
function abreMunicipio(m) {
  if (!m) return;
  abreAba('explorar', true);
  renderDetail(m);
  const ft = features.find(x => x.id === String(m.id));
  if (ft) zoomToMuni(ft);
  setTimeout(() => document.getElementById('detail')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80);
}
// procure a sua cidade (abertura)
(() => {
  const t = document.getElementById('buscaTopo');
  if (!t || !inputBusca) return;
  t.addEventListener('input', () => { inputBusca.value = t.value; atualizaSugestoes(); });
  const vai = () => { const m = MUNI_POR_ROTULO.get(t.value.trim()); if (m) { inputBusca.value = t.value; abreMunicipio(m); } };
  t.addEventListener('change', vai);
  t.addEventListener('keydown', e => { if (e.key === 'Enter') vai(); });
})();
// cruze você: abre o Explorar com a variável do passo na cor do mapa
document.querySelectorAll('[data-cruze]').forEach(bt => bt.addEventListener('click', () => {
  const sel = document.getElementById('colorBy');
  if (sel) { sel.value = bt.dataset.cruze; sel.dispatchEvent(new Event('change')); }
  abreAba('explorar');
  setTimeout(() => document.getElementById('mapSvg')?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 80);
}));
// o alvo: clique num ponto abre o município
document.getElementById('alvoPanel')?.addEventListener('click', e => {
  const c = e.target.closest('circle[data-mun]');
  if (c) abreMunicipio(MUNI.get(String(c.dataset.mun)) || MUNI.get(Number(c.dataset.mun)));
});
// endereço direto para um município: painel-proposta.html#mun-3550308 (ponte vinda da Rede)
function irParaMunDoEndereco(tent = 0) {
  const mm = /^#mun-(\d+)/.exec(location.hash);
  if (!mm) return;
  const m = MUNI.get(mm[1]) || MUNI.get(Number(mm[1]));
  if (m && features.length) abreMunicipio(m);
  else if (tent < 40) setTimeout(() => irParaMunDoEndereco(tent + 1), 250);
}
window.addEventListener('hashchange', () => irParaMunDoEndereco());
irParaMunDoEndereco();
'''
saida = h + painel[len(head):i_logic] + g + painel[i_logic + len(logic):]
(RAIZ / 'painel-proposta.html').write_text(saida, encoding='utf-8')
print('gerado: painel-proposta.html', len(saida.encode()), 'bytes')

# ================================================================== REDE
hg = (S / 'head-ge.html').read_text(encoding='utf-8')
alem = (S / 'secao-alem.html').read_text(encoding='utf-8')
hgm = hg.replace('<!--ALEM-->', alem)
lg = (S / 'logic-ge.js').read_text(encoding='utf-8')
rede = (RAIZ / 'rede-ge.html').read_text(encoding='utf-8')
assert rede.startswith(hgm), 'rede-ge.html não começa com o molde — rode montar_rede_ge.sh antes'
i_lg = rede.index(lg)

r = hgm
r = troca(r, '</style>\n</head>', CSS_COMUM + '</style>\n</head>')
r = troca(r, '<body>\n', '<body>\n' + FAIXA.format(atual='rede-ge.html'))
r = nav_proposta(r)
r = troca(r, '<span class="badge">rede · v1.0.0</span>', '<span class="badge">rede · v1.0.0 · proposta</span>')
r = re.sub(r'<p class="resumo">.*?</p>',
           '<p class="resumo" style="font-size:15px;color:var(--text);border-left:3px solid var(--rosa);padding-left:12px;">'
           'Os grupos econômicos são donos de parte dos operadores de ônibus e são a forma mais concentrada do contrato: '
           '22 unidades de controle detêm metade do capital do setor. A tese descreve o papel deles, sem medir um efeito próprio sobre a adoção da Tarifa Zero.</p>',
           r, count=1, flags=re.S)
r = re.sub(r'<p><b>O que esta página não mostra:</b>(.*?)</p>',
           r'<details class="nota"><summary>O que esta página não mostra</summary><p class="sub" style="margin:6px 0 0;">\1</p></details>',
           r, count=1, flags=re.S)
r = troca(r, '<div class="wrap">\n  <nav class="tabs" role="tablist">',
          '<div class="wrap">\n  <div class="trilha"><a href="painel-proposta.html#sec-p1">← Passo 1 · Onde há Tarifa Zero</a>'
          '<span>Você está no <b>passo 2 · Quem opera o ônibus</b></span>'
          '<a href="painel-proposta.html#sec-p3">Passo 3 · Como a gratuidade entra →</a></div>\n  <nav class="tabs" role="tablist">')
r = troca(r, '    <div class="agrgrid" style="margin-top:6px;">',
          '    <details class="mais"><summary>Famílias de controle, linhagens e federações</summary>\n    <div class="agrgrid" style="margin-top:6px;">')
r = troca(r, '        <div id="geFederacoes"></div></div>\n    </div>\n',
          '        <div id="geFederacoes"></div></div>\n    </div>\n    </details>\n')
_k = r.index('id="tab-alem"'); r, _resto = r[:_k], r[_k:]
r = troca(r, '  <details class="panel" style="margin-top:16px;" open>\n    <summary>Notas metodológicas e limites de leitura</summary>',
          '''  <div class="panel" style="margin-top:16px;border:2px solid var(--rosa);">
    <h2>E a Tarifa Zero?</h2>
    <p class="resposta">Os grupos operam uma parte pequena das políticas, mas, onde estão, a gratuidade entra pelo contrato que já detêm: das políticas cujo operador atual é de grupo, 10 de 20 entraram por aditivo à concessão, contra 12 de 71 sem grupo.</p>
    <p class="sub">Ser de grupo não muda a chance de o operador continuar quando a gratuidade chega (Seção 8.3). O que a gratuidade preserva, no mercado atrativo, é o contrato, com ou sem grupo (Seção 9.1).</p>
    <p style="margin:10px 0 0;"><a class="bt1" href="painel-proposta.html#sec-p3">Passo 3 no Painel: como a gratuidade entra →</a><a class="bt2" href="painel-proposta.html#explorar">Ver o operador de cada caso no Explorar</a></p>
  </div>
  <details class="panel" style="margin-top:16px;">
    <summary>Notas metodológicas e limites de leitura</summary>''')
r = r + _resto
lgn = troca(lg, '<a href="painel.html#explorar">Painel Brasil</a>', '<a href="painel-proposta.html#mun-${cod}">Painel Brasil</a>', n=2)
saida = r + rede[len(hgm):i_lg] + lgn + rede[i_lg + len(lg):]
(RAIZ / 'rede-ge-proposta.html').write_text(saida, encoding='utf-8')
print('gerado: rede-ge-proposta.html', len(saida.encode()), 'bytes')
