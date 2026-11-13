#!/usr/bin/env python3
"""
rede_etapa3.py — Rede de empresas reorganizada em torno da tese (13/11/2026, comentários do autor:
"reflete pouco a tese — fala pouquíssimo do Capítulo 8"; "falta uma aba GE × TZ").

Roda depois de rede_etapa2.py, sobre rede-ge-proposta.html. Abas:
  GE × TZ        o Capítulo 8 em cinco caixas (8.1 a 8.5), os casos e a conclusão (Seção 9.1)
  A rede         a rede, o grupo selecionado na horizontal, onde os grupos estão, as medidas da rede
  Concentração   quanto o capital se concentra e a lista dos 327 grupos
  Além do ônibus a cadeia fixa no topo; "Explore um grupo" por federação
Números do Capítulo 8 tirados do Quadro 36 e da Seção 9.1 da r103 (base de 11/11/2026).
"""
import os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, 'rede-ge-proposta.html')
PAINEL = sys.argv[2] if len(sys.argv) > 2 else 'painel.html'
TESE1 = 'tese/Tese%20-%20Volume%20I%20-%20Texto.pdf'
s = open(ARQ, encoding='utf-8').read()
assert 'rede_etapa2' in s and 'rede_etapa3' not in s, 'rode rede_etapa2.py antes, uma vez só'

def troca(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, f'âncora com {c} ocorrência(s), esperado {n}: {a[:100]!r}'
    s = s.replace(a, b)
def corta(ini, fim_incl):
    global s
    i = s.index(ini); j = s.index(fim_incl, i) + len(fim_incl)
    t = s[i:j]; s = s[:i] + s[j:]; return t
def bloco_details(ident):
    """corta o <details ... id="ident"> inteiro (equilibra details aninhados)"""
    global s
    i = s.index(f'<details class="pacote" id="{ident}"')
    i = s.rindex('\n', 0, i) + 1
    prof, k = 0, i
    while True:
        a = s.find('<details', k); f = s.find('</details>', k)
        if a != -1 and a < f: prof += 1; k = a + 8
        else:
            prof -= 1; k = f + 10
            if prof == 0: break
    t = s[i:k]; s = s[:i] + s[k:]; return t

# ------------------------------------------------------------------ links do painel: a página oficial
s = s.replace('painel-proposta.html', PAINEL)

# ------------------------------------------------------------------ fora: a faixa da trilha, os cartões de números, "E a Tarifa Zero?"
corta('  <div class="trilha">', '</div>\n')
troca('  <div class="cards" id="cards"></div>\n', '  <div class="cards" id="cards" hidden></div>\n')
corta('  <div class="ponte-tz">', '\n  </div>\n')
CONTRIBUA = corta('  <div class="contribua">', '</a></div>\n')

# ------------------------------------------------------------------ A rede: grupo selecionado na horizontal, embaixo da rede
troca('  <div class="grid">\n    <div class="panel" id="painelRede">', '  <div class="grid rede-grid">\n    <div class="panel" id="painelRede">')
troca('      <details class="medidas"><summary>Medidas da rede (ARS)</summary><div id="redeMedidas"></div></details>\n', '')
troca('Math.min(4, Math.max(.2, Math.min((R.W - 2 * pad)', 'Math.min(2.2, Math.max(.2, Math.min((R.W - 2 * pad)')
ONDE = bloco_details('onde-grupos')
AGR = bloco_details('agrupamentos')
LST = bloco_details('lista-grupos')
ONDE = ONDE.replace('<span class="pnum">3</span>', '<span class="pnum">1</span>').replace('<details class="pacote" id="onde-grupos">', '<details class="pacote" id="onde-grupos" open>')
MED_CX = ('  <details class="pacote" id="medidas-cx"><summary class="phead"><span class="pnum">2</span><div><h2>A rede em números</h2>'
          '<p>Quantos grupos se ligam, quem é mais conectado e quem está no caminho entre os demais (análise de redes sociais, Seção 6.2).</p></div>'
          '<span class="pseta" aria-hidden="true">▾</span></summary><div id="redeMedidas"></div></details>\n')
i = s.index('\n  </section>\n  <section class="tabpane" id="tab-alem"')
s = s[:i] + '\n' + ONDE + MED_CX + s[i:]

# ------------------------------------------------------------------ Concentração: aba própria
CONC = ('  <section class="tabpane" id="tab-concentracao" role="tabpanel" hidden>\n'
        '  <div class="paneintro"><p class="resposta-rede">Poucos donos, muito capital: 22 unidades de controle detêm metade do capital declarado do setor. A tese junta os grupos numa escala de confiança, de A (controle comum demonstrado) a D (federação: articulação, e não controle).</p></div>\n'
        + AGR.replace('<details class="pacote" id="agrupamentos">', '<details class="pacote" id="agrupamentos" open>')
        + LST.replace('<span class="pnum">2</span>', '<span class="pnum">2</span>') + '  </section>\n')
i = s.index('  <section class="tabpane" id="tab-alem"')
s = s[:i] + CONC + s[i:]

# ------------------------------------------------------------------ Além do ônibus: a cadeia fixa, sem número; as demais renumeradas
sub = re.search(r'<details class="pacote" id="alem-cadeia" open><summary class="phead"><span class="pnum">1</span><div><h2>Como se lê a cadeia</h2><p>(.*?)</p></div><span class="pseta" aria-hidden="true">▾</span></summary>', s)
assert sub
s = s[:sub.start()] + f'<div class="panel cadeia-fixa" id="alem-cadeia"><h2>Como se lê a cadeia</h2><p class="legenda">{sub.group(1)}</p>' + s[sub.end():]
i = s.index('id="alem-cadeia"'); j = s.index('</details>', i)
s = s[:j] + '</div>' + s[j + len('</details>'):]
for velho, novo in (('2', '1'), ('3', '2'), ('4', '3'), ('5', '4')):
    ident = {'2': 'alem-setores', '3': 'patGrupo', '4': 'alem-ranking', '5': 'alem-encontros'}[velho]
    m = re.search(r'(<details class="pacote" id="%s"[^>]*><summary class="phead"><span class="pnum">)%s(</span>)' % (ident, velho), s)
    assert m, ident
    s = s[:m.start()] + m.group(1) + novo + m.group(2) + s[m.end():]
# "Explore um grupo": escolha por federação (a lista livre não funcionava)
troca('<label>Grupo <input id="patBusca" list="patBuscaList"',
      '<label>Federação e grupo <select id="patFed"><option value="">escolha…</option></select></label><label hidden>Grupo <input id="patBusca" list="patBuscaList"')

# ------------------------------------------------------------------ GE × TZ: o Capítulo 8
def barras(linhas):
    """linhas: (rótulo, n, total, cor) → barras horizontais de proporção"""
    out = []
    for rot, n, t, cor in linhas:
        p = 100 * n / t
        out.append(f'<div class="gb-lin"><div class="gb-rot">{rot}</div><div class="gb-bar"><span style="width:{p:.1f}%;background:{cor};"></span></div>'
                   f'<div class="gb-val"><b>{round(p)}%</b> <span>{n} de {t}</span></div></div>')
    return '<div class="gbarras">' + ''.join(out) + '</div>'
def _x(v): return 250 + v / 1.2 * 360
PT = [('Franjas dos arranjos (satélites)', 0.28, '0,28'), ('Sedes dos arranjos (polos)', 0.36, '0,36'),
      ('Grandes grupos, acima de 100 mil hab.', 0.23, '0,23'), ('Grandes grupos, onde 20% usam ônibus', 0.37, '0,37'),
      ('Dependência do FPM (rival fiscal)', 0.54, '0,54')]
svg = [f'<svg viewBox="0 0 640 {60 + 34 * (len(PT) + 1)}" role="img" aria-label="Razões de chances da adoção da Tarifa Zero" class="gsvg">']
H = 40 + 34 * (len(PT) + 1)
for v, r in ((0, '0'), (0.25, '0,25'), (0.5, '0,5'), (0.75, '0,75'), (1.0, '1')):
    svg.append(f'<line x1="{_x(v):.0f}" x2="{_x(v):.0f}" y1="24" y2="{H - 14}" stroke="#26262d"/><text x="{_x(v):.0f}" y="{H}" text-anchor="middle" font-size="11" fill="#9a9aa6">{r}</text>')
svg.append(f'<line x1="{_x(1):.0f}" x2="{_x(1):.0f}" y1="16" y2="{H - 14}" stroke="#f0f0f2" stroke-dasharray="4 3"/><text x="{_x(1) - 6:.0f}" y="18" text-anchor="end" font-size="11" fill="#f0f0f2">mesma chance (1) →</text>')
for i, (rot, v, t) in enumerate(PT):
    y = 44 + i * 34; cor = '#9a9aa6' if 'FPM' in rot else '#FF2D6B'
    svg.append(f'<text x="0" y="{y + 4}" font-size="12.5" fill="#f0f0f2">{rot}</text><line x1="{_x(v):.0f}" x2="{_x(1):.0f}" y1="{y}" y2="{y}" stroke="{cor}" stroke-opacity=".35" stroke-width="3"/>'
               f'<circle cx="{_x(v):.0f}" cy="{y}" r="7" fill="{cor}"/><text x="{_x(v) - 12:.0f}" y="{y + 4}" text-anchor="end" font-size="12.5" font-weight="800" fill="#F5E400">{t}</text>')
y = 44 + len(PT) * 34
svg.append(f'<text x="0" y="{y + 4}" font-size="12.5" fill="#f0f0f2">Cidades isoladas</text><text x="{_x(1) - 10:.0f}" y="{y + 4}" text-anchor="end" font-size="12" fill="#9a9aa6">sem diferença</text></svg>')

def caixa(n, ident, tit, res, corpo, sec, aberta=False):
    return (f'  <details class="pacote" id="{ident}"{" open" if aberta else ""}><summary class="phead"><span class="pnum">{n}</span><div><h2>{tit}</h2><p>{res}</p>'
            f'<div class="pmeta">Na tese: {sec}</div></div><span class="pseta" aria-hidden="true">▾</span></summary>\n{corpo}\n  </details>\n')
def caso(cod, nome, txt):
    return f'<a class="caso" href="{PAINEL}#mun-{cod}"><b>{nome}</b><span>{txt}</span><i>ver no painel →</i></a>'

GETZ = ('  <section class="tabpane" id="tab-getz" role="tabpanel">\n'
 '  <div class="abre-getz"><p class="pergunta">Os grupos econômicos barram a Tarifa Zero?</p>'
 '<p class="resposta-rede">Não se opõem ao dinheiro público: querem que ele preserve os contratos. Onde estão, a gratuidade entra pelo contrato que já detêm. A tese se sustenta melhor como hipótese sobre o <b>contrato</b> do que sobre o <b>grupo</b>: por isso fala do papel, e não da influência, dos grupos.</p>'
 '<div class="passos"><a href="#ge-81">1 · Adoção</a><a href="#ge-82">2 · Porta de entrada</a><a href="#ge-83">3 · Quem fica e o que muda</a><a href="#ge-84">4 · Recuos e encerramentos</a><a href="#ge-85">5 · O que o setor pede</a><a href="#ge-casos">Os casos</a></div></div>\n'
 + caixa(1, 'ge-81', 'Onde há grupo, há menos Tarifa Zero', 'Comparados municípios parecidos, a presença de empresa de grupo acompanha menos adoção nas franjas e nas sedes dos arranjos; nas cidades isoladas, não.',
   '<p class="legenda">Razão de chances de adotar a Tarifa Zero universal com empresa de grupo presente, controlando porte, capacidade fiscal e estado. Abaixo de 1, menos adoção. É associação, e não causa: a presença de grupo no cadastro não prova que ele opere o sistema.</p>'
   + ''.join(svg) +
   '<p class="legenda" style="margin-top:8px;">A dependência do Fundo de Participação dos Municípios (em cinza) também acompanha menos adoção, mas some entre os municípios que já têm ônibus: é uma barreira de dinheiro para criar o serviço, e não do operador.</p>'
   '<p style="margin:10px 0 0;"><a class="bt2" href="#" data-ir="onde-grupos">Que grupos têm endereço na sua cidade? →</a></p>', 'Seção 8.1', True)
 + caixa(2, 'ge-82', 'Onde há grupo, a gratuidade entra pela concessão', 'Com operador de grupo, a gratuidade entrou por aditivo ao contrato de concessão na metade dos casos; sem grupo, em menos de um em cada cinco.',
   '<p class="legenda">Políticas cuja gratuidade entrou por aditivo à concessão vigente, pelo operador atual.</p>'
   + barras([('Operador de grupo', 10, 20, '#FF2D6B'), ('Operador sem grupo', 12, 71, '#5c6470'),
             ('Municípios de arranjo, operador de grupo', 8, 11, '#FF2D6B'), ('Municípios de arranjo, sem grupo', 7, 36, '#5c6470')]) +
   '<p class="legenda" style="margin-top:8px;">Com controle de porte, a razão de chances é 2,8, sem passar no limiar (p = 0,08); nos municípios de arranjo, 8,1 (p = 0,02). Nas cidades isoladas, não há diferença. A amostra de operadores de grupo é pequena.</p>', 'Seção 8.2')
 + caixa(3, 'ge-83', 'Quem fica e o que muda depois da entrada', 'Ser de grupo não muda a chance de o operador continuar quando a gratuidade chega, nem quem recebe o recurso, quem corre o risco de demanda ou de onde vem o custeio.',
   '<p class="legenda">Operadores que já estavam no sistema e continuaram quando a gratuidade chegou.</p>'
   + barras([('Empresas de grupo', 11, 18, '#FF2D6B'), ('Empresas sem grupo', 16, 25, '#5c6470')]) +
   '<p class="legenda" style="margin-top:8px;">Sete empresas de grupo saíram na entrada da gratuidade. O incumbente foi identificado em 43 de 97 casos.</p>'
   '<p class="legenda" style="margin-top:14px;">Políticas com contrapartida escrita (transparência, desempenho ou controle social), pelo operador.</p>'
   + barras([('Operador de grupo', 8, 16, '#FF2D6B'), ('Operador sem grupo', 14, 62, '#5c6470')]) +
   '<p class="legenda" style="margin-top:8px;">A diferença fica no limite do acaso (p = 0,06) e é quase toda de desempenho ou de transparência. Controle social escrito, com operador de grupo, só em Agudos.</p>', 'Seção 8.3')
 + caixa(4, 'ge-84', 'Recuos e encerramentos', 'Nenhuma das cinco políticas universais encerradas tinha operador de grupo; os fins se ligam a custeio e capacidade. Onde houve recuo com grupo, a concessão foi preservada.',
   '<div class="casos">' + caso('3531803', 'Monte Mor (SP)', 'A gratuidade universal virou focalizada sem trocar a concessão.')
   + caso('3548807', 'São Caetano do Sul (SP)', 'A gratuidade de todos virou de moradores um dia depois de um aditivo que trocou a remuneração por quilômetro pelo custo operacional menos a receita tarifária.') + '</div>'
   '<p class="legenda" style="margin-top:8px;">O conjunto não confirma a previsão inicial de reversões concentradas onde o custo de saída do incumbente é alto: são só cinco políticas encerradas.</p>', 'Seção 8.4 e Estudo de caso 1')
 + caixa(5, 'ge-85', 'O que o setor pede', 'As entidades do setor não recusam o dinheiro público: querem que ele preserve os contratos e transfira ao Estado o risco de demanda.',
   '<ul class="leve"><li><b>NTU e ANTP</b> defendem apoio condicionado à preservação dos contratos e à transferência do risco de demanda ao Estado.</li>'
   '<li><b>Belo Horizonte:</b> as federações contrárias ao PL 60/2025 não têm vínculo identificado com os grupos da rede.</li></ul>'
   '<p class="legenda">É posição declarada pelas entidades, e não conduta medida em cada município.</p>', 'Seção 8.5')
 + '  <div class="panel" id="ge-casos" style="margin-top:16px;"><h2>Os casos: o contrato condiciona a política</h2><p class="legenda">As trajetórias que a tese documenta, caso a caso (Seções 7.3 a 7.5 e 8.4).</p><div class="casos">'
 + caso('3301900', 'Itaboraí (RJ)', 'A lei amarrou o subsídio à concessão vigente.')
 + caso('3302700', 'Maricá (RJ)', 'As concessionárias contestaram na Justiça a operação pública; o incumbente de grande grupo voltou em 2025 como locador de ônibus com motorista, pelo maior contrato anual de Tarifa Zero do levantamento.')
 + caso('3548807', 'São Caetano do Sul (SP)', 'O recuo da gratuidade preservou o operador.')
 + caso('3531803', 'Monte Mor (SP)', 'O recuo da gratuidade preservou a concessão.') + '</div></div>\n'
 '  <div class="fecho-rede"><p class="frase">O que a gratuidade preserva, no mercado atrativo, é o contrato, com ou sem grupo.</p>'
 '<p class="legenda">Os grupos são donos de parte dos operadores e são a forma mais concentrada do contrato, mas a pesquisa não mediu um efeito próprio deles sobre a adoção ou o desenho (Seção 9.1).</p>'
 f'<p style="margin:10px 0 0;"><a class="bt2" href="{PAINEL}#sec-p3">No painel: como a gratuidade entra →</a><a class="bt2" href="{TESE1}" target="_blank" rel="noopener">Volume I — Capítulo 8 (PDF)</a></p></div>\n'
 '  </section>\n')
i = s.index('  <section class="tabpane" id="tab-controle">')
s = s[:i] + GETZ + s[i:]
troca('  <section class="tabpane" id="tab-controle">', '  <section class="tabpane" id="tab-controle" hidden>')

# contribuição: fora das abas, uma vez só, antes do pé
i = s.index('  <details class="rodape-sobre"')
s = s[:i] + CONTRIBUA + s[i:]

# abas
s, k = re.subn(r'<nav class="tabs" role="tablist">.*?</nav>',
     '<nav class="tabs" role="tablist">\n'
     '    <button class="tabbtn on" id="tabbtn-getz" data-tab="getz" role="tab" aria-selected="true">GE × TZ</button>\n'
     '    <button class="tabbtn" id="tabbtn-controle" data-tab="controle" role="tab" aria-selected="false">A rede</button>\n'
     '    <button class="tabbtn" id="tabbtn-concentracao" data-tab="concentracao" role="tab" aria-selected="false">Concentração</button>\n'
     '    <button class="tabbtn" id="tabbtn-alem" data-tab="alem" role="tab" aria-selected="false">Além do ônibus</button>\n  </nav>', s, count=1, flags=re.S)
assert k == 1
# cabeçalho
s, k = re.subn(r'(<p class="resumo" style="font-size:15px;[^"]*">).*?(</p>)',
     r'\1Quem controla o ônibus no Brasil e o que isso muda na Tarifa Zero. Os grupos econômicos são donos de parte dos operadores e são a forma mais concentrada do contrato; onde estão, a gratuidade entra pelo contrato que já detêm.\2', s, count=1, flags=re.S)
assert k == 1

# ------------------------------------------------------------------ CSS
troca('</style>\n</head>', '''  /* ===== rede_etapa3 (13/11/2026) ===== */
  #cards{display:none !important;}
  .rede-grid{display:block !important;}
  .rede-grid > .rightcol{margin-top:14px;}
  #redeSvg{height:min(680px,72vh) !important;}
  #fichaPanel #detail{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:8px 22px;align-items:start;}
  #fichaPanel #detail > .empty{grid-column:1 / -1;}
  #fichaPanel .gd-esq, #fichaPanel .gd-dir{min-width:0;}
  @media (max-width:820px){ #fichaPanel #detail{grid-template-columns:1fr;} }
  #fichaPanel .munmapa{max-height:340px;}
  .medgrid{display:grid !important;grid-template-columns:repeat(3,minmax(0,1fr)) !important;gap:12px !important;margin:4px 0 12px;}
  .medgrid > div{background:var(--panel2);border-radius:8px;padding:10px 12px;}
  .medgrid b{display:block;font-size:26px !important;font-weight:800;color:var(--amarelo);line-height:1.1;}
  .medgrid span{font-size:12.5px;color:var(--text);}
  .medlistas{display:grid;grid-template-columns:1fr 1fr;gap:16px;} .medlistas ol{margin:4px 0 0;padding-left:20px;font-size:13px;line-height:1.7;}
  @media (max-width:640px){ .medgrid{grid-template-columns:1fr 1fr !important;} .medlistas{grid-template-columns:1fr;} }
  .resposta-rede{font-size:15px;line-height:1.55;color:var(--text);border-left:3px solid var(--rosa);padding:2px 0 2px 12px;margin:0 0 14px;max-width:920px;}
  .abre-getz{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin:0 0 6px;}
  .abre-getz .pergunta{font-size:19px;font-weight:800;margin:0 0 8px;}
  .abre-getz .passos{display:flex;flex-wrap:wrap;gap:8px;}
  .abre-getz .passos a{background:var(--panel2);border:1px solid var(--border);border-radius:8px;padding:6px 11px;font-size:12.5px;color:var(--text) !important;text-decoration:none;}
  .abre-getz .passos a:hover{border-color:var(--amarelo);}
  .pmeta{font-size:11.5px;color:var(--muted);}
  .gsvg{width:100%;max-width:760px;height:auto;display:block;}
  .gbarras{display:grid;gap:8px;margin:6px 0 4px;max-width:820px;}
  .gb-lin{display:grid;grid-template-columns:minmax(150px,280px) 1fr 110px;gap:10px;align-items:center;font-size:13px;}
  .gb-bar{height:18px;background:var(--panel2);border-radius:5px;overflow:hidden;} .gb-bar span{display:block;height:100%;}
  .gb-val b{font-size:15px;} .gb-val span{font-size:11.5px;color:var(--muted);}
  @media (max-width:640px){ .gb-lin{grid-template-columns:1fr 90px;} .gb-rot{grid-column:1 / -1;} }
  .casos{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin:6px 0 0;}
  a.caso{display:flex;flex-direction:column;gap:4px;background:var(--panel2);border:1px solid var(--border);border-radius:10px;padding:12px 14px;color:var(--text) !important;text-decoration:none;}
  a.caso:hover{border-color:var(--amarelo);} a.caso b{font-size:14px;} a.caso span{font-size:12.5px;line-height:1.5;} a.caso i{font-style:normal;font-size:11.5px;color:var(--rosa);margin-top:auto;}
  .fecho-rede{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin:16px 0 0;}
  .fecho-rede .frase{font-size:17px;font-weight:800;color:var(--rosa);margin:0 0 8px;}
  ul.leve{margin:6px 0 4px;padding-left:18px;font-size:13.5px;line-height:1.6;} ul.leve li{margin:0 0 6px;}
  .cadeia-fixa h2{margin-top:0;}
  #patFed{min-width:280px;max-width:100%;}
</style>
</head>''')

# ------------------------------------------------------------------ JS
s = s.replace('<meta name="proposta" content="rede_etapa2">\n</body>', '''<script>
// rede_etapa3: abas, grupo selecionado na horizontal, zoom ao selecionar, "Explore um grupo" por federação
const ABAS_R = ['getz', 'controle', 'concentracao', 'alem'];
abreAba = function (nome) {
  if (!ABAS_R.includes(nome)) nome = 'getz';
  for (const a of ABAS_R) {
    const p = document.getElementById('tab-' + a), b = document.getElementById('tabbtn-' + a);
    if (p) p.hidden = a !== nome;
    if (b) { b.classList.toggle('on', a === nome); b.setAttribute('aria-selected', a === nome); }
  }
  if (nome === 'alem') setTimeout(() => window.PAT?.enquadra(), 0);
  if (nome === 'controle') setTimeout(() => { mede(); if (selecionado) enquadra([selecionado, ...ADJ.get(selecionado)], false); else enquadra(null, false); }, 0);
  if (!/^#(GE-|mun-|alem-)/.test(location.hash)) history.replaceState(null, '', nome === 'getz' ? location.pathname : '#' + nome);
};
function arrumaFicha() {
  const box = document.getElementById('detail'); if (!box || box.querySelector('.gd-esq')) return;
  const filhos = [...box.children]; const k = filhos.findIndex(e => /Onde tem endereço/.test(e.textContent || '') && e.matches('p'));
  if (k < 0) return;
  const esq = document.createElement('div'), dir = document.createElement('div'); esq.className = 'gd-esq'; dir.className = 'gd-dir';
  filhos.slice(0, k).forEach(e => esq.appendChild(e)); filhos.slice(k).forEach(e => dir.appendChild(e));
  box.append(esq, dir);
  // menos informação: a tabela de números sai (os carimbos já dizem), a lista de municípios recolhe
  [...box.querySelectorAll('details.fichapol')].find(d => /Os números do grupo/.test(d.textContent))?.remove();
  const ml = box.querySelector('.munlista');
  if (ml) { const d = document.createElement('details'); d.className = 'fichapol'; d.innerHTML = '<summary>Ver a lista dos municípios</summary>'; ml.replaceWith(d); d.appendChild(ml); }
}
const _sel0 = seleciona;
seleciona = function (id, rolar, modo) {
  _sel0(id, false, modo); arrumaFicha();
  if (id) {
    if (document.getElementById('tab-controle').hidden) abreAba('controle');
    const s = SIMI.get(id); if (s && visivel(s)) enquadra([id, ...ADJ.get(id)]);
    if (rolar) document.getElementById('painelRede')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
};
// a rede abre a aba certa conforme o endereço
(() => { const h = location.hash;
  if (/^#(GE-|mun-)/.test(h)) { abreAba('controle'); const g = decodeURIComponent(h.slice(1)); if (NOS.has(g)) seleciona(g, false); }
  else if (/^#alem/.test(h)) abreAba('alem');
  else if (h === '#concentracao') abreAba('concentracao');
  else if (h === '#controle') abreAba('controle');
  else abreAba('getz');
})();
// atalhos internos (passos do GE × TZ, "que grupos têm endereço")
document.addEventListener('click', e => {
  const a = e.target.closest('.abre-getz .passos a, [data-ir]'); if (!a) return;
  const id = a.dataset.ir || a.getAttribute('href').slice(1), el = document.getElementById(id); if (!el) return;
  e.preventDefault();
  const aba = el.closest('.tabpane'); if (aba && aba.hidden) abreAba(aba.id.replace('tab-', ''));
  if (el.matches('details')) el.open = true;
  setTimeout(() => el.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60);
});
// Explore um grupo: escolha por federação (só os grupos que têm holdings levantadas)
(() => {
  const sel = document.getElementById('patFed'); if (!sel || !window.PAT) return;
  const ops = ARS.federacoes.map(f => {
    const gs = f.unidades.flatMap(u => (UNI.get(u)?.membros || [])).filter(g => NOS.has(g) && window.PAT.tem(g));
    return gs.length ? `<optgroup label="${f.id} · ${gs.length} ${gs.length === 1 ? 'grupo' : 'grupos'}">${gs.map(g => `<option value="${g}">${esc(nomeG(NOS.get(g)))}</option>`).join('')}</optgroup>` : '';
  }).join('');
  sel.innerHTML += ops;
  sel.addEventListener('change', () => { if (sel.value) window.PAT.mostra(sel.value); });
})();
</script>
<meta name="proposta" content="rede_etapa3">
</body>''', 1)
assert 'rede_etapa3' in s
open(ARQ, 'w', encoding='utf-8').write(s)
print('etapa 3 da rede aplicada:', ARQ, len(s.encode()), 'bytes')
