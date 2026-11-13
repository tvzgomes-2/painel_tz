#!/usr/bin/env python3
"""
proposta_etapa2.py — segunda etapa da proposta de revisão de lançamento (v1.0.0), 13/11/2026.

Roda DEPOIS de gerar_proposta.py e altera painel-proposta.html no lugar. Pedidos do autor ("aplicar tudo!"):
  1. passos do argumento e blocos do Explorar recolhidos, com a identidade das caixas de Dados e conceitos
     (número rosa, título, frase de resumo, seta); fechada, a caixa já mostra a resposta do passo;
  2. as duas réguas cruzadas voltam ao passo 5, como gráfico (barras por destinatário, divididas pelo portão);
  3. fecho com o Quadro 36 (síntese dos achados), botões da tese no modelo de Dados e conceitos e sem o
     "Baixar os dados" repetido;
  4. filtros: "Hierarquia urbana" vira Sede / Franja / Isolado (posição no arranjo populacional) e sai
     "Modelo de prestação";
  5. "Envie para a pesquisa" volta a ter destaque (cartão no fim do argumento e no Explorar);
  6. menos texto recolhido: saem os "O que mostra e a ressalva" e os "Como ler"; fica uma legenda curta,
     visível, por gráfico, e uma ressalva única por passo ("não apurado não é zero").
Uso: python3 scripts/proposta_etapa2.py [painel-proposta.html]
"""
import os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, 'painel-proposta.html')
s = open(ARQ, encoding='utf-8').read()
assert 'proposta_etapa2' not in s, 'etapa 2 já aplicada — rode gerar_proposta.py antes'

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

TESE1 = 'tese/Tese%20-%20Volume%20I%20-%20Texto.pdf'
TESE2 = 'tese/Tese%20-%20Volume%20II%20-%20Ap%C3%AAndices.pdf'
def mb(nome):
    f = os.path.join(RAIZ, 'tese', nome)
    return (f'{os.path.getsize(f) / 1048576:.1f} MB'.replace('.', ',')) if os.path.exists(f) else None   # MB como em Dados e conceitos
V1 = mb('Tese - Volume I - Texto.pdf') or '16,6 MB'; V2 = mb('Tese - Volume II - Apêndices.pdf') or '11,9 MB'

# ------------------------------------------------------------------ CSS
troca('</style>\n</head>', '''  /* ===== proposta_etapa2 (13/11/2026) — caixas recolhidas no modelo de Dados e conceitos ===== */
  details.pacote{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin:0 0 16px;}
  .phead{display:flex;gap:14px;align-items:flex-start;margin:0;cursor:pointer;list-style:none;}
  .phead::-webkit-details-marker{display:none;}
  .phead > div{flex:1 1 auto;min-width:0;}
  .phead h2{margin:2px 0 4px;font-size:18px;}
  .phead p{margin:0 0 4px;font-size:13.5px;line-height:1.55;color:var(--text);}
  .pnum{flex:0 0 auto;width:32px;height:32px;border-radius:50%;background:var(--rosa);color:#fff;font-weight:800;display:flex;align-items:center;justify-content:center;font-size:15px;}
  .pmeta{font-size:11.5px;color:var(--muted);}
  .pseta{flex:0 0 auto;font-size:18px;color:var(--muted);transition:transform .15s;margin-top:2px;}
  details.pacote[open] > .phead{margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--border);}
  details.pacote[open] > .phead .pseta{transform:rotate(180deg);color:var(--amarelo);}
  details.pacote > .phead:hover .pseta, details.pacote > .phead:hover h2{color:var(--amarelo);}
  details.pacote .panel{background:var(--panel2);}
  .legenda{font-size:12.5px;color:var(--muted);margin:2px 0 10px;line-height:1.5;max-width:900px;}
  .ressalva-passo{font-size:11.5px;color:var(--muted);margin:10px 0 0;}
  .cruzbars{display:grid;gap:10px;margin:6px 0 4px;}
  .cb-lin{display:grid;grid-template-columns:minmax(150px,240px) 1fr 70px;gap:10px;align-items:center;}
  .cb-rot{font-size:13px;}
  .cb-bar{display:flex;height:22px;background:var(--panel2);border-radius:5px;overflow:hidden;}
  .cb-bar span{display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;color:#0E0E10;}
  .cb-tot{font-size:13px;text-align:right;white-space:nowrap;} .cb-hip{color:var(--muted);font-size:11.5px;}
  .cb-leg{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:12px;color:var(--muted);margin-top:10px;}
  .cb-leg i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:5px;vertical-align:-1px;}
  @media (max-width:640px){ .cb-lin{grid-template-columns:1fr 54px;} .cb-rot{grid-column:1 / -1;} }
  .q36{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0 4px;}
  .q36 td{padding:8px 8px;border-bottom:1px solid var(--border);vertical-align:top;line-height:1.45;}
  .q36 td.an{font-weight:800;white-space:nowrap;width:1%;}
  .q36 td.ev{white-space:nowrap;width:1%;} .q36 td.se{white-space:nowrap;width:1%;color:var(--muted);font-size:12px;}
  .q36 .chip{display:inline-block;font-size:11px;font-weight:700;border:1px solid var(--border);border-radius:10px;padding:1px 8px;color:var(--text);background:var(--panel2);}
  @media (max-width:640px){ .q36 td.an{white-space:normal;} .q36 td.ev, .q36 td.se{display:none;} }
  .tese-vols{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 0;}
  .rot-vols{font-size:11.5px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--amarelo);margin:16px 0 4px;}
  .contribua{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px 20px;background:var(--panel);
    border:2px solid var(--amarelo);border-radius:12px;padding:18px 22px;margin:18px 0 0;}
  .contribua b{display:block;font-size:17px;margin-bottom:3px;} .contribua span{font-size:13px;color:var(--muted);}
  .contribua .bt1{font-size:14px;padding:11px 20px;}
  /* hierarquia do fim da página (pedido do autor): conclusão discreta, contribuição em destaque, dados sem alarde */
  .fecho{background:var(--panel) !important;border:1px solid var(--border) !important;}
  .fecho .frase{font-size:17px !important;}
  .fecho .tese-vols .bt1{background:var(--panel2);border:2px solid var(--border);color:var(--text) !important;}
  .fecho .tese-vols .bt1:hover{border-color:var(--amarelo);filter:none;}
  .contribua.forte{background:rgba(245,228,0,.07);border:3px solid var(--amarelo);padding:26px 28px;margin:22px 0 0;}
  .contribua.forte b{font-size:23px;line-height:1.25;margin-bottom:6px;}
  .contribua.forte span{font-size:14.5px;color:var(--text);}
  .contribua.forte .bt1{font-size:16px;padding:14px 26px;}
  aside.cta-dados{background:none !important;border:none !important;border-top:1px solid var(--border) !important;border-radius:0 !important;padding:12px 0 !important;margin:22px 0 0 !important;}
  aside.cta-dados .cta-txt b{font-size:13px !important;display:inline !important;margin-right:6px;}
  aside.cta-dados .cta-txt span{display:inline !important;}
  aside.cta-dados .cta-btn{background:none !important;color:var(--text) !important;border:1px solid var(--border);padding:6px 12px !important;font-size:12.5px !important;}
  aside.cta-dados .cta-btn:hover{border-color:var(--amarelo);filter:none;}
  .arrbloco{min-width:0;}
  @media (max-width:640px){ details.pacote{padding:14px 12px;} .phead{gap:10px;} }
</style>
</head>''')

# ------------------------------------------------------------------ 6. menos texto recolhido
LEGENDA = {
 'Linha do tempo das adoções': 'Cada barra é um ano: em verde, as políticas universais que começaram nele; em amarelo, as parciais; em rosa, abaixo da linha, as que acabaram.',
 'Adoção por porte': 'Contando só os municípios que têm ônibus, a adoção é maior entre 20 e 50 mil habitantes e não chega acima de 500 mil.',
 'Condição de acesso à gratuidade': 'Cada política na escala que vai da gratuidade sem condição nenhuma (à esquerda) até os desenhos em que um portão decide quem pode viajar, ou quando (à direita).',
 'O que os testes de adoção dizem': 'Abaixo de 1, menos adoção do que em municípios parecidos sem empresa de grupo. É associação, e não causa.',
 'O arranjo do contrato': 'O que decide é o que foi contratado: a frota própria da prefeitura e a gratuidade por aditivo a uma concessão são arranjos opostos.',
 'Como o operador é pago': 'Pago pela oferta (por quilômetro, por veículo ou valor fixo), o operador recebe mesmo sem passageiro, e o risco da demanda fica com a prefeitura.',
 'A contrapartida': 'O que a norma ou o contrato exige em troca do recurso: controle social, transparência ou metas de desempenho.',
 'A régua analítica': 'Cada ponto é uma política. Quanto mais perto do centro, mais perto da gestão do comum, com controle social; por fora, o dinheiro vai ao operador sem nada em troca.',
 'As duas réguas cruzadas': 'Cada barra é um destinatário do recurso, dividida pelo portão de acesso: a gratuidade sem portão (1a) aparece em todos eles.',
 'Tarifa Zero por região e por UF': 'Quantos casos cada estado tem e que fração dos seus municípios isso representa.',
 'Do piso à Tarifa Zero universal': 'Cada linha é um portão de acesso, do piso nacional à Tarifa Zero universal; a barra é a população com direito.',
 'Do que a literatura fala': 'Quantos trabalhos tratam de cada fator; a parte cheia, os que têm achado empírico próprio.',
}
a = s.index('<section class="tabpane" id="tab-panorama"'); b = s.index('<footer>', a)
corpo = s[a:b]
def legenda(m):
    antes = corpo[:m.start()]
    tits = re.findall(r'<h3[^>]*>(.*?)</h3>', antes)
    tit = re.sub('<[^>]+>', '', tits[-1]) if tits else ''
    for k, v in LEGENDA.items():
        if tit.startswith(k): return f'<p class="legenda">{v}</p>'
    return m.group(0)   # sem legenda definida: fica como está
corpo2 = re.sub(r'<details class="nota"><summary>Como ler[^<]*</summary>.*?</details>', legenda, corpo, flags=re.S)
assert corpo2.count('class="legenda"') >= 10, corpo2.count('class="legenda"')
s = s[:a] + corpo2 + s[b:]
# "O que mostra e a ressalva" (gerado por put): fica só a frase de resultado
troca('''`<p class="resposta">${res}</p><details class="nota"><summary>O que mostra e a ressalva</summary><p class="sub" style="margin:6px 0 0;">${mostra}</p><p class="sub" style="margin:6px 0 0;"><b>Ressalva.</b> ${ress}</p></details>`''',
      '`<p class="resposta">${res}</p>`')
troca(' — o cruzamento com o portão está na tabela abaixo.', '.')

# ------------------------------------------------------------------ 1. passos recolhidos
PASSO = {
 1: ('Onde há Tarifa Zero?', '173 políticas universais; 9,3% dos municípios com ônibus têm Tarifa Zero, e nenhum acima de 500 mil habitantes.', 'Capítulo 5'),
 2: ('Quem opera o ônibus?', 'Onde o mercado é atrativo, há grupo econômico: 22 unidades de controle detêm metade do capital, e com empresa de grupo presente há menos adoção nas sedes e franjas dos arranjos.', 'Capítulo 6 e Seção 8.1'),
 3: ('Como a gratuidade entra?', 'Onde o operador é privado, a gratuidade entra pelo contrato, paga pela oferta e com o risco de demanda no município.', 'Seções 7.2 e 8.2'),
 4: ('Quem paga?', 'O município, sozinho: nenhuma política vigente tem receita própria vinculada.', 'Seção 7.5'),
 5: ('A quem serve o subsídio?', 'Só 6 das 110 políticas com destinatário e contrapartida apurados chegam à gestão do comum.', 'Seções 7.2 e 7.6'),
}
for n, (tit, res, tese) in PASSO.items():
    sub1(r'<section class="secao" id="sec-p%d">\s*<div class="sechead">.*?</div>\n' % n,
         f'<details class="pacote passo" id="sec-p{n}">\n      <summary class="phead"><span class="pnum">{n}</span><div><h2>{tit}</h2>'
         f'<p>{res}</p><div class="pmeta">Na tese: {tese}</div></div><span class="pseta" aria-hidden="true">▾</span></summary>\n')
    # fecha o passo: o </section> logo depois do rodapé do passo
    i = s.index(f'id="sec-p{n}"'); j = s.index('<div class="passo-pe">', i); k = s.index('\n    </section>', j)
    s = s[:k] + '\n      <p class="ressalva-passo">Não apurado não é zero: é falta de informação. Método e limites, no Volume I da tese.</p>\n    </details>' + s[k + len('\n    </section>'):]
# frases-resposta estáticas dos passos 2 e 3 já estão no resumo da caixa
sub1(r'\n      <p class="resposta">Onde o mercado é atrativo, há grupo econômico:.*?</p>', '')
sub1(r'\n      <p class="resposta">Onde o operador é privado, a gratuidade entra pelo contrato.*?</p>', '')

# ------------------------------------------------------------------ 2b. passo 2 mais rico (pedido do autor: "ficou muito pobre")
# Concentração (números da Rede de empresas, base de 11/11/2026), os testes de adoção como gráfico de pontos
# (razões de chances da Seção 8.1, nacionais e fixas) e um ponto de trabalho: "que grupos têm endereço na sua cidade".
def _x(v): return 230 + v / 1.2 * 380
PONTOS = [('Franjas dos arranjos (satélites)', 0.28, '0,28'), ('Sedes dos arranjos (polos)', 0.36, '0,36'),
          ('Grandes grupos, acima de 100 mil hab.', 0.23, '0,23')]
svg = ['<svg viewBox="0 0 640 196" role="img" aria-label="Razões de chances de adotar a Tarifa Zero com empresa de grupo presente" style="width:100%;max-width:720px;height:auto;display:block;">']
svg.append(f'<line x1="{_x(0)}" x2="{_x(1.2)}" y1="164" y2="164" stroke="#3a3a44"/>')
for v, rot in ((0, '0'), (0.25, '0,25'), (0.5, '0,5'), (0.75, '0,75'), (1.0, '1')):
    svg.append(f'<line x1="{_x(v):.0f}" x2="{_x(v):.0f}" y1="22" y2="164" stroke="#26262d"/><text x="{_x(v):.0f}" y="180" text-anchor="middle" font-size="11" fill="#9a9aa6">{rot}</text>')
svg.append(f'<line x1="{_x(1):.0f}" x2="{_x(1):.0f}" y1="14" y2="164" stroke="#f0f0f2" stroke-dasharray="4 3"/><text x="{_x(1)-6:.0f}" y="18" text-anchor="end" font-size="11" fill="#f0f0f2">mesma chance (1) →</text>')
for i, (rot, v, txt) in enumerate(PONTOS):
    y = 42 + i * 34
    svg.append(f'<text x="0" y="{y+4}" font-size="12.5" fill="#f0f0f2">{rot}</text><line x1="{_x(v):.0f}" x2="{_x(1):.0f}" y1="{y}" y2="{y}" stroke="#FF2D6B" stroke-opacity=".35" stroke-width="3"/>'
               f'<circle cx="{_x(v):.0f}" cy="{y}" r="7" fill="#FF2D6B"/><text x="{_x(v)-12:.0f}" y="{y+4}" text-anchor="end" font-size="12.5" font-weight="800" fill="#F5E400">{txt}</text>')
y = 42 + 3 * 34
svg.append(f'<text x="0" y="{y+4}" font-size="12.5" fill="#f0f0f2">Cidades isoladas</text><text x="{_x(1)-10:.0f}" y="{y+4}" text-anchor="end" font-size="12" fill="#9a9aa6">sem diferença</text>')
svg.append('</svg>')
PASSO2 = ('<div class="p2grid">\n'
 '        <div class="panel"><h3 class="pt">Poucos donos, muito capital</h3>\n'
 '          <div class="p2num"><div><b>327</b><span>grupos econômicos controlam 1.040 empresas de ônibus</span></div><div><b>22</b><span>unidades de controle detêm metade do capital do setor</span></div><div><b>1.042</b><span>municípios têm endereço de empresa de grupo, onde vivem 136,8 milhões de pessoas</span></div></div>\n'
 '          <div class="conc"><div class="conc-l">Unidades de controle</div><div class="conc-b"><span style="width:7%;" class="hi"></span><span style="width:93%;"></span></div><div class="conc-v">22 de 316</div>\n'
 '            <div class="conc-l">Capital declarado</div><div class="conc-b"><span style="width:50%;" class="hi"></span><span style="width:50%;"></span></div><div class="conc-v">metade</div></div>\n'
 '          <p class="legenda">Em amarelo, as 22 maiores unidades de controle: 7% das unidades, metade do capital.</p>\n'
 '        </div>\n'
 '        <div class="panel"><h3 class="pt">Que grupos têm endereço na sua cidade?</h3>\n'
 '          <p class="legenda">Escolha o município e veja, na Rede de empresas, os grupos com estabelecimento nele.</p>\n'
 '          <div class="abre-busca" style="margin-top:4px;"><input id="buscaGrupo" list="muniList" placeholder="Digite o nome do município…" autocomplete="off" spellcheck="false" aria-label="Município"></div>\n'
 '          <p class="legenda" style="margin-top:10px;">Ter endereço não é operar o sistema: quem opera cada Tarifa Zero está no contrato, na ficha do município.</p>\n'
 '          <p style="margin:10px 0 0;"><a class="bt1" href="rede-ge-proposta.html">Abrir a Rede de empresas →</a></p>\n'
 '        </div>\n'
 '      </div>\n'
 '      <div class="panel" style="margin-top:14px;"><h3 class="pt">Com empresa de grupo presente, menos adoção — nas sedes e franjas dos arranjos</h3>\n'
 '        <p class="legenda">Razão de chances de adotar a Tarifa Zero com empresa de grupo presente, comparando municípios parecidos em porte, capacidade fiscal e estado. Abaixo de 1, menos adoção. É associação, e não causa.</p>\n'
 '        ' + ''.join(svg) + '\n'
 '      </div>')
i = s.index('<div class="panel"><h3 class="pt">O que os testes de adoção dizem')
j = s.index('Abrir a Rede de empresas →</a></p>\n      </div>', i) + len('Abrir a Rede de empresas →</a></p>\n      </div>')
s = s[:i] + PASSO2 + s[j:]
troca('</style>\n</head>', '  .p2grid{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:14px;}\n'
 '  @media (max-width:820px){ .p2grid{grid-template-columns:1fr;} }\n'
 '  .p2num{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:4px 0 14px;}\n'
 '  .p2num b{display:block;font-size:30px;font-weight:800;color:var(--amarelo);line-height:1.1;}\n'
 '  .p2num span{font-size:12.5px;color:var(--text);line-height:1.4;display:block;}\n'
 '  @media (max-width:640px){ .p2num{grid-template-columns:1fr;} .conc{grid-template-columns:1fr 70px !important;} .conc-l{grid-column:1 / -1;} }\n'
 '  .conc{display:grid;grid-template-columns:150px 1fr 74px;gap:8px 10px;align-items:center;font-size:12.5px;}\n'
 '  .conc-b{display:flex;height:18px;border-radius:5px;overflow:hidden;background:var(--panel);}\n'
 '  .conc-b span{display:block;height:100%;background:#3a3a44;} .conc-b span.hi{background:var(--amarelo);}\n'
 '  .conc-v{text-align:right;font-weight:700;}\n'
 '</style>\n</head>')
s = s.replace('</body>', '<script>\n'
 '// passo 2: que grupos têm endereço na sua cidade → Rede de empresas, já no município\n'
 "(() => { const t = document.getElementById('buscaGrupo'); if (!t) return;\n"
 "  t.addEventListener('input', () => { inputBusca.value = t.value; atualizaSugestoes(); });\n"
 "  const vai = () => { const m = MUNI_POR_ROTULO.get(t.value.trim()); if (m) location.href = 'rede-ge-proposta.html#mun-' + m.id + '-' + encodeURIComponent(m.nome); };\n"
 "  t.addEventListener('change', vai); t.addEventListener('keydown', e => { if (e.key === 'Enter') vai(); });\n"
 '})();\n</script>\n</body>', 1)

# ------------------------------------------------------------------ 2. réguas cruzadas: de volta, como gráfico
sub1(r'<details class="mais"><summary>Ver as duas réguas cruzadas — o portão e o destinatário</summary>\n(.*?)\n      </details>', r'\1')
i = s.index('function renderCruzadas() {'); j = s.index('\n}\n', i) + 3
s = s[:i] + r'''function renderCruzadas() {
  // proposta_etapa2: barras por destinatário do recurso, divididas pelo subtipo de portão (Quadro 29 da tese)
  const el = document.getElementById('cruzadasPanel');
  if (!el) return;
  const c1 = subsetNoTz().filter(m => m.tz_status === 'Ativa');
  const SUB = [['1a', 'sem portão', '#6FBE44'], ['1b', 'cadastro aberto', '#B5E39A'], ['1c', 'residência', '#3B7C29'], ['1d', 'prazo declarado', '#D4E157']];
  const LIN = [['publica', 'Operação pública'], ['oferta', 'Operador pago pela oferta'], ['demanda', 'Operador pago pela demanda'],
    ['privado_nd', 'Operador privado, pagamento não apurado'], ['nd', 'Destinatário não apurado']];
  const t = {}, prov = {};
  for (const m of c1) { const d = (remunFor(m) || {}).dest || 'nd', k = LIN.some(l => l[0] === d) ? d : 'nd';
    t[k] = t[k] || {}; t[k][m.tz_regua_sub] = (t[k][m.tz_regua_sub] || 0) + 1; if (m.tz_prov) prov[k] = (prov[k] || 0) + 1; }
  const linhas = LIN.filter(([k]) => t[k]);
  const soma = k => SUB.reduce((a, [s]) => a + ((t[k] || {})[s] || 0), 0);
  const max = Math.max(1, ...linhas.map(([k]) => soma(k)));
  el.innerHTML = `<div class="cruzbars">${linhas.map(([k, rot]) => `<div class="cb-lin"><div class="cb-rot">${rot}</div><div class="cb-bar" style="width:${(100 * soma(k) / max).toFixed(1)}%;min-width:4px;">${
      SUB.map(([s, sr, cor]) => { const v = (t[k] || {})[s] || 0; return v ? `<span style="width:${(100 * v / soma(k)).toFixed(2)}%;background:${cor};" title="${rot} · ${s} (${sr}): ${v}">${v / max >= 0.05 ? v : ''}</span>` : ''; }).join('')
    }</div><div class="cb-tot"><b>${soma(k)}</b>${prov[k] ? ` <span class="cb-hip" title="classe por hipótese, já incluída">${prov[k]}&#9671;</span>` : ''}</div></div>`).join('')}</div>
    <div class="cb-leg">${SUB.map(([s, sr, cor]) => `<span><i style="background:${cor}"></i>${s} · ${sr}</span>`).join('')}<span>&#9671; por hipótese (já incluída na barra)</span></div>`;
}
''' + s[j:]

# ------------------------------------------------------------------ 3. fecho: Quadro 36, tese no modelo de Dados e conceitos
Q36 = [
 ('Destinatário do recurso', 'Das 152 políticas com destinatário apurado, 68 são operação pública, 82 pagam o operador pela oferta e 2 pela demanda.', 'Documental', '7.2'),
 ('Contrapartida', 'Apurada em 125 das 173 e presente em 31; nos 67 contratos pagos pela oferta com informação, ausente em 46.', 'Documental', '7.2'),
 ('Distância do comum', 'Das 110 políticas com destinatário e contrapartida apurados, 6 atendem aos critérios da gestão do comum.', 'Documental', '7.6'),
 ('Custeio', 'Nenhuma política vigente com receita própria vinculada já arrecadada; 59 dependem do orçamento geral e 70 têm dotação identificada.', 'Documental', '7.5'),
 ('Território', 'As taxas de adoção são próximas com e sem grupo nos diferentes arranjos; o padrão não é uniforme no território.', 'Exploratória', '8.1'),
 ('Adoção', 'Com empresa de grupo presente, menos adoção nas franjas (0,28) e nas sedes (0,36) dos arranjos; nos isolados, não.', 'Estatística', '8.1'),
 ('Rival fiscal', 'A dependência do FPM acompanha menos adoção (0,54), mas não entre os municípios que já têm ônibus.', 'Estatística', '8.1'),
 ('Porta de entrada', 'A gratuidade entrou por aditivo à concessão em 10 de 20 casos com operador de grupo, contra 12 de 71 sem grupo.', 'Limitada', '8.2'),
 ('Incumbente', 'O operador que já estava continua na mesma proporção, com ou sem grupo (11 de 18 e 16 de 25).', 'Baixa', '8.3'),
 ('Desenho depois da entrada', 'Destinatário, risco de demanda e custeio não distinguem os operadores de grupo dos demais.', 'Inconclusiva', '8.3'),
 ('Permanência e saída', 'Nenhuma das cinco políticas encerradas tinha operador de grupo; os fins se ligam a custeio e capacidade.', 'Baixa', '8.4'),
 ('Preço', 'De R$ 5,79 a R$ 23,75 por quilômetro, mediana de R$ 10,37, em 43 contratos; sem padrão ligado a grupo.', 'Descritiva', '7.4'),
 ('Posição do setor', 'NTU e ANTP defendem o apoio público condicionado à preservação dos contratos.', 'Qualitativa', '8.5'),
]
q36 = ''.join(f'<tr><td class="an">{a}</td><td>{f}</td><td class="ev"><span class="chip">{e}</span></td><td class="se">Seção {sec}</td></tr>' for a, f, e, sec in Q36)
sub1(r'<div class="fecho">.*?\n    </div>\n',
     f'''<div class="fecho">
      <p class="frase">A gratuidade amplia o acesso, mas não decide a quem serve o subsídio. Essa decisão está no contrato.</p>
      <p class="sub" style="font-size:13.5px;color:var(--text);max-width:900px;">Quem paga é o município, sozinho. Onde o operador é privado, o recurso que substitui a tarifa o paga pela oferta, quase sempre sem nada em troca. Tarifa Zero sem controle público é transferência de renda ao operador com um benefício social acoplado; com custos e dados abertos e controle social, é a gestão do transporte como um comum.</p>
      <p class="rot-vols">O que cada análise encontrou (Quadro 36 da tese)</p>
      <div style="overflow-x:auto;"><table class="q36">{q36}</table></div>
      <p class="legenda">"Não apurado" é falta de informação, e não ausência. A evidência diz o alcance de cada achado: a hipótese se sustenta melhor como hipótese sobre o contrato do que sobre o grupo (Seção 9.1).</p>
      <p class="rot-vols">A tese, em dois volumes</p>
      <div class="tese-vols"><a class="bt1" href="{TESE1}" target="_blank" rel="noopener">Volume I — Texto (PDF, {V1})</a><a class="bt1" href="{TESE2}" target="_blank" rel="noopener">Volume II — Apêndices (PDF, {V2})</a><a class="bt2" href="#explorar">Trabalhar com os dados no Explorar</a></div>
    </div>
    <div class="contribua forte"><div><b>Conhece um caso que não está aqui?</b><span>Envie um caso municipal, um estudo, um relatório ou um dado de operação. Cada contribuição é revisada antes de entrar no painel.</span></div><a class="bt1" href="pesquisa.html">Envie para a pesquisa →</a></div>
''')

# ------------------------------------------------------------------ 1b. blocos do Explorar recolhidos
sub1(r'<div class="bloco-explorar" id="uf-alcance">\n    <div class="paneintro"><h2>(.*?)</h2><p>(.*?)</p></div>\n(.*?)\n  </div>(\s*\n  </section>)',
     r'<details class="pacote bloco-explorar" id="uf-alcance"><summary class="phead"><div><h2>\1</h2><p>\2</p></div><span class="pseta" aria-hidden="true">▾</span></summary>\n\3\n  </details>\4')
for aba in ('comparar', 'literatura', 'sobre'):
    sub1(r'(<section class="tabpane" id="tab-%s"[^>]*>)<div class="bloco-explorar"></div>\s*<div class="paneintro"><h2>(.*?)</h2><p>(.*?)</p></div>(.*?)(\n  </section>)' % aba,
         r'\1<details class="pacote bloco-explorar" id="%s-caixa"><summary class="phead"><div><h2>\2</h2><p>\3</p></div><span class="pseta" aria-hidden="true">▾</span></summary>\4\n  </details>\5' % aba)
# âncora para um trecho recolhido: abre a caixa antes de rolar; ao abrir, os gráficos se redesenham
troca("  if (rolarPara) setTimeout(() => document.getElementById(rolarPara)?.scrollIntoView({ behavior: 'smooth' }), 60);",
      """  if (rolarPara) setTimeout(() => {
    const alvo = document.getElementById(rolarPara);
    if (!alvo) return;
    const cx = alvo.matches('details') ? alvo : (alvo.querySelector(':scope > details.pacote') || alvo.closest('details.pacote'));
    if (cx) cx.open = true;
    alvo.scrollIntoView({ behavior: 'smooth' });
  }, 60);""")
s = s.replace('</body>', '''<script>
// proposta_etapa2: ao abrir uma caixa, avisa os gráficos (alguns medem a largura ao desenhar)
document.querySelectorAll('details.pacote').forEach(d => d.addEventListener('toggle', () => { if (d.open) window.dispatchEvent(new Event('resize')); }));
// os atalhos para o mesmo trecho também abrem a caixa quando o endereço não muda
document.querySelectorAll('a[href^="#sec-p"], .explorar-nav a').forEach(a => a.addEventListener('click', () => {
  const id = a.getAttribute('href').slice(1), el = document.getElementById(id) || document.getElementById('tab-' + id);
  const cx = el && (el.matches('details') ? el : (el.querySelector(':scope > details.pacote') || el.closest('details.pacote')));
  if (cx) cx.open = true;
}));
</script>
</body>''', 1)

# ------------------------------------------------------------------ 4. filtros: posição no arranjo; sem modelo de prestação
sub1(r'<div><label for="regicFilter">Hierarquia urbana</label>\s*<select id="regicFilter">.*?</select>\s*</div>',
     '''<div><label for="arranjoFilter">Posição no arranjo</label>
      <select id="arranjoFilter">
        <option value="">Todas</option>
        <option value="Sede/co-sede do arranjo">Sede do arranjo</option>
        <option value="Satélite do arranjo">Franja do arranjo (satélite)</option>
        <option value="Fora de arranjo">Isolado (fora de arranjo)</option>
      </select>
    </div>''')
sub1(r'\s*<div><label for="modeloFilter">Modelo de prestação</label>\s*<select id="modeloFilter">.*?</select>\s*</div>', '')
troca("document.getElementById('regicFilter').addEventListener('change', e => { state.regic = e.target.value; render(); renderTZTable(); atualizaBotaoLimpar(); });",
      "document.getElementById('arranjoFilter').addEventListener('change', e => { state.arranjo = e.target.value; render(); renderTZTable(); atualizaBotaoLimpar(); });")
troca("document.getElementById('modeloFilter').addEventListener('change', e => { state.modelo = e.target.value; render(); atualizaBotaoLimpar(); });\n", '')
troca("for (const id of ['ufFilter', 'faixaFilter', 'regicFilter', 'modeloFilter', 'tzFilter', 'camadaFilter']) {",
      "for (const id of ['ufFilter', 'faixaFilter', 'arranjoFilter', 'tzFilter', 'camadaFilter']) {")
troca("  arranjo: [null, 'Arranjo'],", "  arranjo: ['arranjoFilter', 'Arranjo'],")

# ------------------------------------------------------------------ 5. "Envie para a pesquisa" com destaque no Explorar
sub1(r'<div class="cta-pesquisa">.*?</div>',
     '<div class="contribua"><div><b>Não achou o seu município, ou tem um estudo ou dado para a pesquisa?</b><span>Cada contribuição é revisada antes de entrar no painel.</span></div><a class="bt1" href="pesquisa.html">Envie para a pesquisa →</a></div>')

# a nota longa "Como os números foram calculados" (Do piso à Tarifa Zero universal) vira uma linha
sub1(r"  h \+= `<details class=\"nota\" style=\"margin-top:10px;\"><summary>Como os números foram calculados</summary>.*?</p></details>`;\n",
     "  h += `<p class=\"legenda\" style=\"margin-top:10px;\">As linhas não se somam: a mesma pessoa pode ter direito por mais de um portão. E ter direito não é o mesmo que usar.</p>`;\n")
# ------------------------------------------------------------------ 7. "Colorir mapa por": uma variável por passo (decisão do autor, 13/11/2026)
# Ficam situação da TZ, porte, posição no arranjo, receita própria, PIB per capita e motorização; entram
# "Como o operador é pago" (passo 3) e "Posição no plano — o alvo" (passo 5), só para quem tem TZ universal.
sub1(r'<select id="colorBy">.*?</select>',
     '<select id="colorBy">\n'
     '        <option value="tz">Situação da Tarifa Zero</option>\n'
     '        <optgroup label="Os passos do argumento">\n'
     '        <option value="faixa_pop">1 · Porte do município</option>\n'
     '        <option value="tipo_arranjo">2 · Posição no arranjo (sede, franja, isolado)</option>\n'
     '        <option value="dest">3 · Como o operador é pago (só Tarifa Zero universal)</option>\n'
     '        <option value="rec_prop_pc">4 · Receita própria per capita</option>\n'
     '        <option value="posicao">5 · Posição no plano, o alvo (só Tarifa Zero universal)</option>\n'
     '        </optgroup>\n'
     '        <optgroup label="Contexto">\n'
     '        <option value="pib_pc">PIB per capita</option>\n'
     '        <option value="motorizacao">Motorização (veículos por habitante)</option>\n'
     '        </optgroup>\n'
     '      </select>')
troca("  if (!m) return nt.noData;\n  if (colorBy === 'tz') {",
      """  if (!m) return nt.noData;
  if (colorBy === 'dest' || colorBy === 'posicao') {
    if (m.tz_status !== 'Ativa') return nt.naoTz;
    if (colorBy === 'posicao') { const p = posicaoPlano(m); return p ? MAPA_POS[p] : nt.noData; }
    return (MAPA_DEST[(remunFor(m) || {}).dest] || [nt.noData])[0];
  }
  if (colorBy === 'tz') {""")
troca("function renderLegend() {\n  const el = document.getElementById('legend');\n  const nt = neutrals();\n  let html = '';\n",
      """// proposta_etapa2: cores das duas variáveis novas do mapa
const MAPA_DEST = { publica: ['#6FBE44', 'Operação pública'], oferta: ['#E2892C', 'Operador pago pela oferta'],
  demanda: ['#1A54C7', 'Operador pago pela demanda'], privado_nd: ['#B9B9C4', 'Operador privado, pagamento não apurado'] };
const MAPA_POS = { comum: '#2E9E3F', parcial: '#98D97B', ruptura: '#98D97B', pub: '#C9C9D3', receita: '#E2892C', bolsa: '#1A54C7' };
const ROT_ARRANJO = { 'Sede/co-sede do arranjo': 'Sede do arranjo', 'Satélite do arranjo': 'Franja do arranjo (satélite)', 'Fora de arranjo': 'Isolado (fora de arranjo)' };
function renderLegend() {
  const el = document.getElementById('legend');
  const nt = neutrals();
  let html = '';
  if (state.colorBy === 'dest' || state.colorBy === 'posicao') {
    const itens = state.colorBy === 'dest' ? Object.values(MAPA_DEST)
      : ['comum', 'parcial', 'pub', 'receita', 'bolsa'].map(k => [MAPA_POS[k], POS_ROT[k]]);
    el.innerHTML = itens.map(([c, r]) => `<span><span class="sw" style="background:${c}"></span>${r}</span>`).join('')
      + `<span><span class="sw" style="background:${nt.noData}"></span>Não apurado</span><span><span class="sw" style="background:${nt.naoTz}"></span>Sem Tarifa Zero universal</span>`;
    return;
  }
""")
troca("html = STATS.arranjo_order.map(a => `<span><span class=\"sw\" style=\"background:${ARRANJO_COLORS[a]}\"></span>${a}</span>`).join('');",
      "html = STATS.arranjo_order.map(a => `<span><span class=\"sw\" style=\"background:${ARRANJO_COLORS[a]}\"></span>${ROT_ARRANJO[a] || a}</span>`).join('');")
troca("      regic_nivel: m.regic_label, tipo_arranjo: m.tipo_arranjo,",
      "      regic_nivel: m.regic_label, tipo_arranjo: ROT_ARRANJO[m.tipo_arranjo] || m.tipo_arranjo,\n"
      "      dest: m.tz_status !== 'Ativa' ? 'sem Tarifa Zero universal' : ((MAPA_DEST[(remunFor(m) || {}).dest] || [0, 'não apurado'])[1]),\n"
      "      posicao: m.tz_status !== 'Ativa' ? 'sem Tarifa Zero universal' : (posicaoPlano(m) ? POS_ROT[posicaoPlano(m)] : 'não apurada'),")
# os botões "Cruze você" dos passos 3 e 5 passam a usar as variáveis novas
troca('data-cruze="modelo_prestacao_simples">Cruze você: modelo de prestação no mapa →', 'data-cruze="dest">Cruze você: como o operador é pago, no mapa →')
troca('data-cruze="tz">Cruze você: situação da Tarifa Zero no mapa →', 'data-cruze="posicao">Cruze você: posição no plano, no mapa →')
troca('data-cruze="tipo_arranjo">Cruze você: arranjo no mapa →', 'data-cruze="tipo_arranjo">Cruze você: sede, franja e isolado no mapa →')

# ------------------------------------------------------------------ 8. abas: O argumento · Do piso à Tarifa Zero · Comparar TZ × Não-TZ · Explorar
# (pedidos do autor, 13/11/2026). A dispersão PIB × motorização fica no Explorar; "% de municípios com TZ
# por eixo" e "Partição modal" vão para o argumento (passo 1); a hierarquia urbana sai também desse quadro.
def _corta(ini, fim_incl):
    global s
    i = s.index(ini); j = s.index(fim_incl, i) + len(fim_incl)
    trecho = s[i:j]; s = s[:i] + s[j:]
    return trecho
DISP = _corta('  <div class="panel" style="margin-top:16px;">\n    <h2 id="dispTitulo">', '<div class="mslegend" id="dispersaoLegenda"></div>\n  </div>\n')
CROSS = _corta('  <details class="panel" style="margin-top:16px;" open>\n    <summary>% de municípios com Tarifa Zero por eixo</summary>', '<div class="crosstabgrid" id="crosstabs"></div>\n  </details>\n')
MODAL = _corta('  <details class="panel" style="margin-top:16px;" open>\n    <summary>Partição modal — TZ × Não-TZ (Censo 2022)</summary>', '<div id="modalStack" class="modalstack"></div>\n  </details>\n')
# os dois quadros no passo 1, como painéis com título e legenda curta (sem o texto longo)
CROSS = re.sub(r'<details class="panel" style="margin-top:16px;" open>\s*<summary>(.*?)</summary>\s*<p class="sub">.*?</p>', r'<div class="panel" style="margin-top:14px;"><h3 class="pt">\1</h3><p class="legenda">Que fração dos municípios de cada grupo tem Tarifa Zero universal, no recorte atual.</p>', CROSS, count=1, flags=re.S).replace('</details>', '</div>')
MODAL = re.sub(r'<details class="panel" style="margin-top:16px;" open>\s*<summary>(.*?)</summary>\s*<p class="sub">.*?</p>', r'<div class="panel" style="margin-top:14px;"><h3 class="pt">Como as pessoas se deslocam — com e sem Tarifa Zero (Censo 2022)</h3><p class="legenda">Modo de deslocamento para trabalho e estudo; com Tarifa Zero, só as políticas iniciadas até 2022. É correlação, e não causa.</p>', MODAL, count=1, flags=re.S).replace('</details>', '</div>')
i = s.index('<div class="passo-pe">', s.index('id="sec-p1"'))
s = s[:i] + CROSS.strip() + '\n      ' + MODAL.strip() + '\n      ' + s[i:]
troca("    { key: 'regic_nivel', title: 'Hierarquia urbana (REGIC)', order: STATS.regic_order, labelFn: k => `${k} · ${REGIC_LABELS[k]}` },\n", '')
troca("{ key: 'tipo_arranjo', title: 'Sede × satélite de arranjo', order: STATS.arranjo_order, labelFn: k => k },",
      "{ key: 'tipo_arranjo', title: 'Sede, franja ou isolado', order: STATS.arranjo_order, labelFn: k => ROT_ARRANJO[k] || k },")
# dispersão: caixa própria no Explorar, antes de "Por região e UF"
DISP_CX = ('<details class="pacote bloco-explorar" id="dispersao-caixa"><summary class="phead"><div><h2>Cruze duas variáveis</h2>'
           '<p>Cada ponto é um município; escolha os eixos (começa em PIB per capita × motorização) e veja onde ficam os que têm Tarifa Zero.</p></div>'
           '<span class="pseta" aria-hidden="true">▾</span></summary>\n' + DISP + '  </details>\n  ')
i = s.index('<details class="pacote bloco-explorar" id="uf-alcance">')
s = s[:i] + DISP_CX + s[i:]
# "Do piso à Tarifa Zero universal" sai de "Por UF e quem é alcançado" e vira aba
PISO = _corta('      <div class="leitura" id="leit-alcance" style="margin-top:14px;"></div>\n', '<div id="popScore"></div></div>')
troca('<h2>Por UF e quem é alcançado</h2><p>As políticas por região e UF e, para cada portão, quem tem direito à gratuidade e quando.</p>',
      '<h2>Por região e UF</h2><p>Quantos casos cada estado tem e que fração dos seus municípios isso representa.</p>')
i = s.index('<section class="tabpane" id="tab-explorar"')
s = s[:i] + ('<section class="tabpane" id="tab-piso" role="tabpanel" aria-labelledby="tabbtn-piso" hidden>\n'
             '    <div class="paneintro"><h2>Do piso à Tarifa Zero universal</h2><p>Quem tem direito a andar de ônibus de graça no Brasil, por qual portão e quando: do piso que vale no país inteiro à Tarifa Zero universal, decidida por cada município.</p></div>\n'
             + PISO.replace(' style="margin-top:14px;"', '', 1) + '\n  </section>\n  ') + s[i:]
# Comparar volta a ser aba: a caixa recolhida vira o cabeçalho da aba
sub1(r'(<section class="tabpane" id="tab-comparar"[^>]*>)<details class="pacote bloco-explorar" id="comparar-caixa"><summary class="phead"><div><h2>(.*?)</h2><p>(.*?)</p></div><span class="pseta" aria-hidden="true">▾</span></summary>(.*?)\n  </details>(\n  </section>)',
     r'\1<div class="paneintro"><h2>\2</h2><p>\3</p></div>\4\5')
sub1(r'<nav class="tabs" role="tablist" aria-label="Áreas do painel">.*?</nav>',
     '<nav class="tabs" role="tablist" aria-label="Áreas do painel">\n'
     '    <button class="tabbtn" role="tab" id="tabbtn-panorama" data-tab="panorama">O argumento</button>\n'
     '    <button class="tabbtn" role="tab" id="tabbtn-piso" data-tab="piso">Do piso à Tarifa Zero</button>\n'
     '    <button class="tabbtn" role="tab" id="tabbtn-comparar" data-tab="comparar">Comparar TZ × Não-TZ</button>\n'
     '    <button class="tabbtn" role="tab" id="tabbtn-explorar" data-tab="explorar">Explorar</button>\n  </nav>')
troca("const ABAS = ['panorama', 'explorar', 'comparar', 'literatura', 'sobre'];", "const ABAS = ['panorama', 'piso', 'explorar', 'comparar', 'literatura', 'sobre'];")
troca("const DENTRO_EXPLORAR = { comparar: 1, literatura: 1, sobre: 1 };", "const DENTRO_EXPLORAR = { literatura: 1, sobre: 1 };")
troca("['panorama', 'explorar']", "['panorama', 'piso', 'comparar', 'explorar']", n=2)
sub1(r'<nav class="explorar-nav" aria-label="Nesta aba">.*?</nav>',
     '<nav class="explorar-nav" aria-label="Nesta aba"><span>Nesta aba:</span><a href="#tab-explorar">Mapa e ficha</a><a href="#dispersao-caixa">Cruze duas variáveis</a>'
     '<a href="#uf-alcance">Por região e UF</a><a href="#literatura">Literatura</a><a href="#sobre">Sobre os dados</a></nav>')

# ------------------------------------------------------------------ 9. Literatura vira aba; "Sobre os dados" enxuto (pedidos do autor, 13/11/2026)
sub1(r'(<section class="tabpane" id="tab-literatura"[^>]*>)<details class="pacote bloco-explorar" id="literatura-caixa"><summary class="phead"><div><h2>(.*?)</h2><p>(.*?)</p></div><span class="pseta" aria-hidden="true">▾</span></summary>(.*?)\n  </details>(\n  </section>)',
     r'\1<div class="paneintro"><h2>\2</h2><p>\3</p></div>\4\5')
troca('    <button class="tabbtn" role="tab" id="tabbtn-explorar" data-tab="explorar">Explorar</button>\n',
      '    <button class="tabbtn" role="tab" id="tabbtn-literatura" data-tab="literatura">Literatura</button>\n'
      '    <button class="tabbtn" role="tab" id="tabbtn-explorar" data-tab="explorar">Explorar</button>\n')
troca("const DENTRO_EXPLORAR = { literatura: 1, sobre: 1 };", "const DENTRO_EXPLORAR = { sobre: 1 };")
troca("['panorama', 'piso', 'comparar', 'explorar']", "['panorama', 'piso', 'comparar', 'literatura', 'explorar']", n=2)
troca('<a href="#literatura">Literatura</a>', '')
# Sobre os dados: o essencial para quem não é da área; o método completo está na tese
sub1(r'(<details class="pacote bloco-explorar" id="sobre-caixa"><summary class="phead"><div><h2>.*?</h2><p>).*?(</p>)',
     r'\1O que ler antes dos números e o glossário dos termos. O método completo está na tese.\2')
sub1(r'<details class="panel" style="margin-top:16px;" open>\s*<summary>Notas metodológicas e achados a interpretar com cautela</summary>.*?</div>\s*</details>',
     '''<div class="panel" style="margin-top:14px;"><h3 class="pt">O que ler antes dos números</h3>
    <ul class="leve">
      <li><b>187 políticas verificadas uma a uma</b>, na norma, no contrato ou na prova de funcionamento: 173 universais, 8 parciais ativas e 6 encerradas. Muitas não se chamam "tarifa zero" ("Ônibus Social", "Circular Gratuito") e por isso escapam das buscas comuns.</li>
      <li><b>Não apurado não é zero.</b> Quando falta informação, o painel diz que falta.</li>
      <li><b>Classe por hipótese (◇).</b> Ao fim da coleta, 26 políticas ficaram sem resposta ao pedido de acesso à informação que fechasse o caso; mantêm a classe que o pedido testava, com ressalva.</li>
      <li><b>As parciais são um piso.</b> A busca da camada 2 não foi exaustiva e acha mais facilmente as cidades grandes; não compare o número delas com o das universais.</li>
      <li><b>A régua lê o desenho da política</b>, e não se ela funciona bem: não mede frequência, horários nem quem deixa de usar a gratuidade.</li>
      <li><b>Endereço não é operação.</b> Ter empresa de grupo registrada no município não prova que ela opere o ônibus de lá.</li>
    </ul>
    <p class="legenda">Método, fontes e limites: Volume I da tese (Capítulo 5 e Seção 9.3).</p>
  </div>''')
sub1(r'<details class="panel" style="margin-top:16px;">\s*<summary>Referências bibliográficas</summary>.*?<div id="referenciasAbnt"></div>\s*</details>',
     '<div class="panel" style="margin-top:14px;"><h3 class="pt">Referências bibliográficas</h3><p class="legenda">Os livros, teses e artigos citados, com o corpus da revisão sistemática, estão em Dados e conceitos.</p><a class="bt2" href="dados.html#referencias">Ver as referências →</a></div>')
# glossário: saem os termos de variáveis que deixaram o painel
for termo in ('IBEU', 'IDH', 'PDMU', 'REGIC', 'Arranjo metropolitano', 'Modelo de prestação', 'NTU', 'CadÚnico', 'Trabalho em outro município'):
    sub1(r'\n\s*<dt>%s</dt><dd>.*?</dd>' % re.escape(termo), '')
troca('</style>\n</head>', '  ul.leve{margin:6px 0 4px;padding-left:18px;font-size:13.5px;line-height:1.6;} ul.leve li{margin:0 0 6px;}\n</style>\n</head>')

# ------------------------------------------------------------------ 10. card do município: os carimbos das réguas e das categorias em primeiro lugar
# (decisão do autor, 13/11/2026: "principal — carimbos das réguas e categorias listadas")
troca("""  el.innerHTML = `<div><b style="font-size:15px;">${m.nome} – ${m.uf}</b> ${tzTag}${subTag ? ' ' + subTag : ''}${camadasTag ? ' ' + camadasTag : ''}</div>
    ${paragrafoTZ}""",
      """  el.innerHTML = `<div><b style="font-size:17px;">${m.nome} – ${m.uf}</b></div>
    ${carimbosHtml(m)}
    ${paragrafoTZ}""")
troca(' — morador não é usuário (ver Quem é alcançado, no Panorama).`;', ' — morador não é usuário (ver a aba Do piso à Tarifa Zero).`;')
# dados do município: só o que o painel ainda usa
for rot in ('Hierarquia urbana', 'Modelo de prestação', 'IBEU', 'IDH', 'Cobertura do CadÚnico (ago/2025)', 'Cobertura do CadÚnico (set/2022)',
            'Cadastro atualizado (ago/2025)', 'Óbitos no trânsito /100mil (2019)', 'Tarifa', '% do custo subsidiado', 'PlanMob (2025)'):
    sub1(r'\n      <tr><td>%s</td><td>.*?</td></tr>' % re.escape(rot), '')
troca("<tr><td>Arranjo metropolitano</td><td>${m.tipo_arranjo ?? '—'}", "<tr><td>Posição no arranjo</td><td>${ROT_ARRANJO[m.tipo_arranjo] || m.tipo_arranjo || '—'}")
troca('<details class="fichapol"><summary>Indicadores do município</summary>', '<details class="fichapol"><summary>Dados do município</summary>')
# ações no pé do card, no sistema comum de botões
sub1(r'<p class="ponte-rede"><a href="rede-ge-proposta.html#mun-\$\{m\.id\}-\$\{encodeURIComponent\(m\.nome \+ \'/\' \+ m\.uf\)\}">.*?</p>`;',
     '''<div class="card-acoes"><a class="bt2" href="rede-ge-proposta.html#mun-${m.id}-${encodeURIComponent(m.nome + '/' + m.uf)}">Grupos com endereço aqui →</a><button type="button" class="bt2" data-copia-mun="${m.id}">Copiar o link deste município</button><a class="bt2" href="pesquisa.html?municipio=${encodeURIComponent(m.nome + ' - ' + m.uf)}">Corrigir ou contribuir</a></div>
    <p class="legenda" style="margin-top:6px;">Ter endereço de empresa de grupo não comprova que ela opere o ônibus do município.</p>`;''')
# estado vazio: busca e três exemplos
troca("""    el.innerHTML = '<div class="empty">Clique em um município no mapa ou na lista abaixo.</div>';""",
      """    el.innerHTML = '<div class="empty">Clique num município no mapa, busque pelo nome acima ou experimente: <a href="#mun-3302700">Maricá</a>, <a href="#mun-2303709">Caucaia</a>, <a href="#mun-3548807">São Caetano do Sul</a>.</div>';""")
troca("function renderDetail(m) {", r'''// proposta_etapa2: carimbos do card — régua descritiva, régua analítica e categorias
const ROT_DEST = { publica: 'Operação pública', oferta: 'Operador pago pela oferta', demanda: 'Operador pago pela demanda', privado_nd: 'Operador privado, pagamento não apurado' };
const ROT_CPI = { C: 'controle social', T: 'transparência', D: 'desempenho' };
function carimbo(txt, cor, titulo, apagado) {
  return `<span class="carimbo${apagado ? ' apagado' : ''}" style="${cor ? '--c:' + cor : ''}"${titulo ? ` title="${String(titulo).replace(/"/g, '&quot;')}"` : ''}>${txt}</span>`;
}
function carimbosHtml(m) {
  const nt = neutrals(), uni = m.tz_status === 'Ativa';
  // régua descritiva
  const desc = [];
  const ST = { 'Ativa': ['Tarifa Zero universal', '#6FBE44'], 'Encerrada': ['Encerrada', '#FF2D6B'], 'Parcial (ativa)': ['Gratuidade parcial', '#E2892C'],
    'Regulamentada — não implantada': ['Lei aprovada, sem operação', '#9a9aa6'], 'Pista (a verificar)': ['Pista a verificar', '#9a9aa6'] };
  if (ST[m.tz_status]) desc.push(carimbo(ST[m.tz_status][0], ST[m.tz_status][1]));
  const sub = (m.tz_bin === 'TZ' && m.tz_regua_sub && REGUA_IDX[m.tz_regua_sub] != null) ? REGUA[REGUA_IDX[m.tz_regua_sub]] : null;
  if (sub) desc.push(carimbo(`${sub.k} · ${sub.rot}${m.tz_prov ? ' ◇' : ''}`, sub.cor, `${sub.desc}${m.tz_prov ? ' — classe por hipótese (lacuna declarada)' : ''}`));
  for (const c of camadasFor(m)) desc.push(carimbo(`${c.camada} · ${(CAMADA_LABELS[c.camada] || '').replace(/^\S+\s·\s/, '') || 'parcial'}`, '#E2892C', c.detalhe || ''));
  if (!desc.length) desc.push(carimbo('Sem Tarifa Zero', '#9a9aa6'));
  // régua analítica (só a camada 1)
  const ana = [];
  if (uni) {
    const r = remunFor(m) || {};
    ana.push(ROT_DEST[r.dest] ? carimbo(ROT_DEST[r.dest], (MAPA_DEST[r.dest] || [])[0]) : carimbo('Destinatário não apurado', '', '', true));
    if (r.cp === 'com') ana.push(carimbo('Contrapartida: ' + (r.cpi || '').split('').map(k => ROT_CPI[k]).filter(Boolean).join(', '), '#98D97B', r.cpl || ''));
    else if (r.cp === 'sem') ana.push(carimbo('Sem contrapartida', '#E2892C', r.cpl || ''));
    else ana.push(carimbo('Contrapartida não apurada', '', '', true));
    const p = posicaoPlano(m);
    ana.push(p ? carimbo(POS_ROT[p], MAPA_POS[p], 'Posição no plano da régua analítica (o alvo, passo 5)') : carimbo('Posição no plano não apurada', '', '', true));
  }
  // categorias
  const cat = [];
  if (m.faixa_pop) cat.push(carimbo(m.faixa_pop.replace('Inferior a', 'Até').replace('Entre ', '').replace(' e ', ' a ') + ' hab.', '#c4c4cf'));
  if (m.tipo_arranjo) cat.push(carimbo(ROT_ARRANJO[m.tipo_arranjo] || m.tipo_arranjo, ARRANJO_COLORS[m.tipo_arranjo] === '#5c6470' ? '#9aa3b0' : ARRANJO_COLORS[m.tipo_arranjo], m.arranjo_nome || ''));
  const a = arranjoFor(m);
  if (a && a.a) cat.push(carimbo(a.a.replace(/^A\d\s/, ''), '#c4c4cf', 'Arranjo operacional (D1)'));
  if (a && a.via) cat.push(carimbo('Entrou por ' + a.via.replace(/\s*\(.*\)$/, ''), '#c4c4cf', 'Instrumento de entrada da gratuidade'));
  if (m.tz_bin === 'TZ' && m.tz_ano_num) cat.push(carimbo('Desde ' + m.tz_ano_num, '#c4c4cf'));
  // municípios parecidos (mesmo porte e mesma posição no arranjo)
  let par = '';
  if (!uni && m.faixa_pop && m.tipo_arranjo) {
    const pr = [...MUNI.values()].filter(x => x.faixa_pop === m.faixa_pop && x.tipo_arranjo === m.tipo_arranjo);
    const n = pr.filter(x => x.tz_status === 'Ativa').length;
    par = `<p class="legenda" style="margin:6px 0 0;">Entre os ${fmtNum(pr.length)} municípios do mesmo porte e da mesma posição no arranjo, <b>${fmtNum(n)}</b> (${(100 * n / Math.max(1, pr.length)).toFixed(1).replace('.', ',')}%) têm Tarifa Zero universal.</p>`;
  }
  const linha = (rot, xs) => xs.length ? `<div class="cb-g"><span class="cb-t">${rot}</span><div>${xs.join('')}</div></div>` : '';
  return `<div class="carimbos">${linha('Régua descritiva', desc)}${linha('Régua analítica', ana)}${linha('Categorias', cat)}</div>${par}`;
}
function renderDetail(m) {''')
troca('</style>\n</head>', '''  .carimbos{margin:10px 0 4px;display:grid;gap:8px;}
  .cb-g{display:grid;grid-template-columns:96px 1fr;gap:8px;align-items:start;}
  .cb-t{font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);padding-top:6px;}
  .carimbo{--c:#c4c4cf;display:inline-block;border:2px solid var(--c);color:var(--c);border-radius:6px;padding:2px 8px;margin:2px 6px 4px 0;
    font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.03em;line-height:1.35;transform:rotate(-1.5deg);background:rgba(255,255,255,.02);}
  .carimbo:nth-child(even){transform:rotate(1deg);}
  .carimbo.apagado{--c:#6b6b78;border-style:dashed;}
  @media (max-width:640px){ .cb-g{grid-template-columns:1fr;gap:2px;} .cb-t{padding-top:0;} }
  .card-acoes{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0 0;}
  .card-acoes .bt2{font-size:12px;padding:7px 11px;margin:0;}
</style>
</head>''')
s = s.replace('</body>', """<script>
// card: copiar o link do município
document.addEventListener('click', e => {
  const b = e.target.closest('[data-copia-mun]'); if (!b) return;
  const url = location.href.split('#')[0] + '#mun-' + b.dataset.copiaMun;
  (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(() => { b.textContent = 'Link copiado'; }, () => { b.textContent = url; });
});
</script>
</body>""", 1)

troca('const paragrafoTZ = `<p style="margin:8px 0 0;font-size:12.5px;line-height:1.55;color:var(--text);">${gerarParagrafoTZ(m)}</p>',
      'const paragrafoTZ = `<p style="margin:8px 0 0;font-size:12.5px;line-height:1.55;color:var(--text);">${(m.tz_bin !== \'TZ\' && !camadasFor(m).length) ? \'Nenhuma política de Tarifa Zero registrada nesta pesquisa. Isso não prova que nunca houve: a busca pode não ter achado.\' : gerarParagrafoTZ(m)}</p>')
# ------------------------------------------------------------------ 11. "Normas e literatura": normas primeiro, com link para o texto limpo (normas padronizadas)
sub1(r"\n  if \(L\.padr && L\.padr\.length\) linhas\.push\([^\n]*",
     "\n  if (L.padr && L.padr.length) linhas.splice(1, 0, `<div class=\"normas-limpas\"><b>${L.padr.length === 1 ? 'A norma, em texto limpo' : L.padr.length + ' normas, em texto limpo'}</b><span>transcrição padronizada pela pesquisa: ementa, artigos da gratuidade, vínculo com a Tarifa Zero e fontes</span><div>${L.padr.map(p => `<a class=\"bt2\" href=\"${p.arq}\" target=\"_blank\" rel=\"noopener\">${p.rot} →</a>`).join('')}</div></div>`);")
troca('<b style="font-size:12.5px;">Base legal</b>${linhas.join(\'\')}', '<b style="font-size:12.5px;">Normas</b>${linhas.join(\'\')}')
i = s.index('${secFicha(`Literatura e legislação${rslFor(m).length')
j = s.index('\n', i)
linha = s[i:j]
m_ = re.match(r"\$\{secFicha\(`Literatura e legislação(\$\{.*?\})`, (levantHtml\(m\) \+ .*?) \+ renderLegislacaoDetail\(m\) \+ renderNoticiasDetail\(m\)\)\}$", linha)
assert m_, linha[:200]
s = s[:i] + "${secFicha(`Normas e literatura" + m_.group(1) + "`, renderLegislacaoDetail(m) + `<div style=\"margin-top:12px;border-top:1px dashed var(--border);padding-top:8px;\"><b style=\"font-size:12.5px;\">Literatura</b></div>` + " + m_.group(2) + " + renderNoticiasDetail(m))}" + s[j:]
troca('</style>\n</head>', '  .normas-limpas{margin:8px 0 4px;padding:10px 12px;background:var(--panel2);border-left:3px solid var(--rosa);border-radius:6px;font-size:12.5px;}\n'
      '  .normas-limpas > b{display:block;color:var(--text);} .normas-limpas > span{display:block;font-size:11.5px;color:var(--muted);margin:2px 0 6px;}\n'
      '  .normas-limpas .bt2{font-size:11.5px;padding:5px 9px;margin:3px 6px 0 0;}\n</style>\n</head>')

# ------------------------------------------------------------------ 12. card: três blocos + o ponto no alvo + card fixo ao lado do mapa
troca("${secFicha('Contrato, arranjo e régua', renderArranjoDetail(m) + renderCamadaDetail(m))}",
      "${secFicha('Por trás dos carimbos: contrato e régua', renderArranjoDetail(m) + renderCamadaDetail(m))}")
troca("    </table></details>\n    ${secFicha('Deslocamentos e meio de transporte', renderODDetail(m) + renderModalDetail(m))}",
      "    </table>${renderODDetail(m)}${renderModalDetail(m)}</details>")
troca("\n  desenharFluxos(m);\n}", """
  desenharFluxos(m);
  // proposta_etapa2: o município escolhido fica marcado no alvo do passo 5
  document.querySelectorAll('#alvoPanel circle.sel').forEach(c => c.classList.remove('sel'));
  document.querySelector(`#alvoPanel circle[data-mun="${m.id}"]`)?.classList.add('sel');
}""")
troca('</style>\n</head>', '  #alvoPanel circle.sel{stroke:#F5E400 !important;stroke-width:3.5 !important;r:7;}\n'
      '  @media (min-width:821px){ #tab-explorar .rightcol > .panel{position:sticky;top:124px;max-height:calc(100vh - 140px);overflow:auto;} }\n</style>\n</head>')

# ------------------------------------------------------------------ 13. comentários do autor (13/11/2026, rodada 3)
# 13a. frase do fecho em rosa
troca('</style>\n</head>', '  .fecho .frase{color:var(--rosa) !important;}\n</style>\n</head>')
# 13b. ordem das abas: O argumento · Explorar · Literatura · Comparar TZ × Não-TZ · Do piso à Tarifa Zero
sub1(r'<nav class="tabs" role="tablist" aria-label="Áreas do painel">.*?</nav>',
     '<nav class="tabs" role="tablist" aria-label="Áreas do painel">\n'
     '    <button class="tabbtn" role="tab" id="tabbtn-panorama" data-tab="panorama">O argumento</button>\n'
     '    <button class="tabbtn" role="tab" id="tabbtn-explorar" data-tab="explorar">Explorar</button>\n'
     '    <button class="tabbtn" role="tab" id="tabbtn-literatura" data-tab="literatura">Literatura</button>\n'
     '    <button class="tabbtn" role="tab" id="tabbtn-comparar" data-tab="comparar">Comparar TZ × Não-TZ</button>\n'
     '    <button class="tabbtn" role="tab" id="tabbtn-piso" data-tab="piso">Do piso à Tarifa Zero</button>\n  </nav>')
# 13c. lista dos municípios com TZ: caixa recolhida e numerada, como as demais do Explorar (1 lista · 2 cruze · 3 região e UF)
sub1(r'<div class="panel" style="margin-top:16px;">\n    <h2>Municípios com Tarifa Zero \(universal \+ parcial\)</h2>\n    <p class="sub">.*?</p>\n(.*?<div class="contribua">.*?</div>)\n  </div>\n',
     r'''<details class="pacote bloco-explorar" id="lista-tz"><summary class="phead"><span class="pnum">1</span><div><h2>Os municípios com Tarifa Zero</h2><p>173 universais em vigor, 6 encerradas e os municípios com gratuidade parcial, numa lista que se ordena e responde aos filtros. Clique numa linha para abrir a ficha.</p></div><span class="pseta" aria-hidden="true">▾</span></summary>
\1
  </details>
''')
troca('<details class="pacote bloco-explorar" id="dispersao-caixa"><summary class="phead"><div>', '<details class="pacote bloco-explorar" id="dispersao-caixa"><summary class="phead"><span class="pnum">2</span><div>')
troca('<details class="pacote bloco-explorar" id="uf-alcance"><summary class="phead"><div>', '<details class="pacote bloco-explorar" id="uf-alcance"><summary class="phead"><span class="pnum">3</span><div>')
# 13d. "Sobre os dados" sai do Explorar e vai para o pé da página, recolhido; referências saem
i = s.index('<section class="tabpane" id="tab-sobre"'); j = s.index('\n  </section>', i) + len('\n  </section>')
sobre = s[i:j]; s = s[:i] + s[j:]
gloss = sobre[sobre.index('<details class="gloss">'):sobre.index('</details>', sobre.index('<details class="gloss">')) + len('</details>')]
ler = sobre[sobre.index('<div class="panel" style="margin-top:14px;"><h3 class="pt">O que ler antes dos números</h3>'):]
ler = ler[:ler.index('</div>', ler.index('<p class="legenda">Método, fontes e limites')) + len('</div>')]
i = s.index('<footer>')
s = s[:i] + ('<details class="rodape-sobre" id="sobre"><summary>Sobre os dados e glossário</summary>\n' + ler + '\n' + gloss + '\n  </details>\n  ') + s[i:]
troca("const DENTRO_EXPLORAR = { sobre: 1 };", "const DENTRO_EXPLORAR = {};")
troca('<a href="#sobre">Sobre os dados</a>', '')
sub1(r'<nav class="explorar-nav" aria-label="Nesta aba"><span>Nesta aba:</span><a href="#tab-explorar">Mapa e ficha</a>',
     '<nav class="explorar-nav" aria-label="Nesta aba"><span>Nesta aba:</span><a href="#tab-explorar">Mapa e ficha</a><a href="#lista-tz">Os municípios com Tarifa Zero</a>')
troca('</style>\n</head>', '  details.rodape-sobre{margin:26px 0 0;padding:10px 0 0;border-top:1px solid var(--border);font-size:12.5px;color:var(--muted);}\n'
      '  details.rodape-sobre > summary{cursor:pointer;font-size:12.5px;color:var(--muted);}\n'
      '  details.rodape-sobre[open] > summary{margin-bottom:10px;color:var(--text);}\n</style>\n</head>')
# 13e. card: ações fixas no topo (copiar o link em destaque), ficha-resumo do Apêndice H visível, sem "Dados do município"
sub1(r'<div class="card-acoes"><a class="bt2" href="rede-ge-proposta\.html#mun-.*?</div>\n    <p class="legenda" style="margin-top:6px;">Ter endereço de empresa de grupo não comprova que ela opere o ônibus do município\.</p>`;',
     '`;')
troca("""    ${carimbosHtml(m)}
    ${paragrafoTZ}""", """    <div class="card-acoes topo"><button type="button" class="bt1" data-copia-mun="${m.id}">Copiar o link deste município</button><a class="bt2" href="rede-ge-proposta.html#mun-${m.id}-${encodeURIComponent(m.nome + '/' + m.uf)}" title="Ter endereço de empresa de grupo não comprova que ela opere o ônibus do município">Grupos com endereço aqui →</a><a class="bt2" href="pesquisa.html?municipio=${encodeURIComponent(m.nome + ' - ' + m.uf)}">Corrigir ou contribuir</a></div>
    ${carimbosHtml(m)}
    ${fichaFor(m) ? `<div class="ficha-resumo"><div class="fr-tit">Ficha-resumo · Apêndice H da tese</div>${(fichaHtml(m).match(/<table class="fl-resumo">[\\s\\S]*?<\\/table>/) || [''])[0]}</div>` : paragrafoTZ}""")
troca("""${fichaFor(m) ? `<details class="fichapol"><summary>Ficha da política — Apêndice H da tese</summary><div class="fl-corpo">${fichaHtml(m)}</div></details>` : ''}""",
      """${fichaFor(m) ? `<details class="fichapol"><summary>Ficha completa — Apêndice H da tese</summary><div class="fl-corpo">${fichaHtml(m).replace(/<h3>Ficha-resumo<\\/h3><table class="fl-resumo">[\\s\\S]*?<\\/table>/, '')}</div></details>` : ''}""")
sub1(r'\n    <details class="fichapol"><summary>Dados do município</summary>.*?</table>\$\{renderODDetail\(m\)\}\$\{renderModalDetail\(m\)\}</details>', '')
troca('</style>\n</head>', '''  .card-acoes.topo{position:sticky;top:0;z-index:3;background:var(--panel);margin:8px 0 4px;padding:6px 0 8px;border-bottom:1px solid var(--border);}
  .card-acoes.topo .bt1{font-size:13.5px;padding:9px 14px;}
  .ficha-resumo{margin:10px 0 4px;} .fr-tit{font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:4px;}
  .ficha-resumo table.fl-resumo{width:100%;border-collapse:collapse;font-size:12px;}
  .ficha-resumo table.fl-resumo td{padding:5px 6px;border-bottom:1px solid var(--border);vertical-align:top;line-height:1.45;}
  .ficha-resumo table.fl-resumo td:first-child{color:var(--muted);width:38%;}
</style>
</head>''')

# ------------------------------------------------------------------ 14. comentários do autor (13/11/2026, rodada 4)
# 14a. Quadro 36: a coluna misturava tipo de evidência e força. Agora: tipo (Documental, Estatística, Qualitativa)
#      num selo e, sob o achado, o limite que a tese registra para ele (coluna "Evidência e limite" do Quadro 36).
Q36B = [
 ('Destinatário do recurso', 'Documental', 'destinatário não apurado em 21 das 173 políticas'),
 ('Contrapartida', 'Documental', 'não apurada em 48 políticas e lida só no ato em 65'),
 ('Distância do comum', 'Documental', 'análise restrita aos 110 casos completos'),
 ('Custeio', 'Documental', 'custeio não apurado em 67 casos'),
 ('Território', 'Estatística', 'exploratória: os padrões locais não sustentam conclusão nacional'),
 ('Adoção', 'Estatística', 'presença de grupo no cadastro não prova que ele opere o sistema'),
 ('Rival fiscal', 'Estatística', 'associação, e não mecanismo causal'),
 ('Porta de entrada', 'Estatística', 'amostra pequena de operadores de grupo'),
 ('Incumbente', 'Estatística', 'incumbente identificado em 43 de 97 casos'),
 ('Desenho depois da entrada', 'Estatística', 'diferença sem significância depois do controle de porte'),
 ('Permanência e saída', 'Documental', 'só cinco políticas encerradas'),
 ('Preço', 'Documental', 'descritivo: só dois aditivos com preço identificado'),
 ('Posição do setor', 'Qualitativa', 'posição declarada pelas entidades, e não conduta medida'),
]
for an, tipo, lim in Q36B:
    sub1(r'(<tr><td class="an">%s</td><td>)(.*?)(</td><td class="ev"><span class="chip">)[^<]*(</span>)' % re.escape(an),
         r'\g<1>\g<2><span class="q36lim">%s</span>\g<3>%s\g<4>' % (lim, tipo))
troca('<p class="legenda">"Não apurado" é falta de informação, e não ausência. A evidência diz o alcance de cada achado:',
      '<p class="legenda">Tipo de evidência: documental (normas, contratos e atos lidos), estatística (testes entre municípios) ou qualitativa (posições declaradas). Em cinza, o limite de cada achado. "Não apurado" é falta de informação, e não ausência;')
troca('</style>\n</head>', '  .q36lim{display:block;font-size:11.5px;color:var(--muted);margin-top:2px;}\n</style>\n</head>')
# 14b. setas de recolher maiores em todo lugar
troca('</style>\n</head>', '''  .pseta{font-size:30px !important;line-height:.8;margin-top:0 !important;}
  details > summary::marker{font-size:1.35em;}
  details.fichapol > summary, details.gloss > summary, details.rodape-sobre > summary{font-size:14px;}
</style>
</head>''')
# 14c. card: "Copiar o link" em amarelo; "Explore os grupos"; ficha-resumo dentro de "Por trás dos carimbos"; sem a ficha completa;
#      "Normas e literatura" remete à tese
troca('<button type="button" class="bt1" data-copia-mun="${m.id}">Copiar o link deste município</button>',
      '<button type="button" class="bt1 amarelo" data-copia-mun="${m.id}">Copiar o link deste município</button>')
troca('" title="Ter endereço de empresa de grupo não comprova que ela opere o ônibus do município">Grupos com endereço aqui →</a>',
      '" title="Ter endereço de empresa de grupo não comprova que ela opere o ônibus do município">Explore os grupos da cidade →</a>')
troca('''    ${fichaFor(m) ? `<div class="ficha-resumo"><div class="fr-tit">Ficha-resumo · Apêndice H da tese</div>${(fichaHtml(m).match(/<table class="fl-resumo">[\\s\\S]*?<\\/table>/) || [''])[0]}</div>` : paragrafoTZ}''',
      '''    ${fichaFor(m) ? '' : paragrafoTZ}''')
sub1(r"\$\{fichaFor\(m\) \? `<details class=\"fichapol\"><summary>Ficha completa — Apêndice H da tese</summary>.*?</details>` : ''\}\n", '')
troca("${secFicha('Por trás dos carimbos: contrato e régua', renderArranjoDetail(m) + renderCamadaDetail(m))}",
      "${secFicha('Por trás dos carimbos: ficha-resumo, contrato e régua', (fichaFor(m) ? `<div class=\"ficha-resumo\"><div class=\"fr-tit\">Ficha-resumo · Apêndice H da tese</div>${(fichaHtml(m).match(/<table class=\"fl-resumo\">[\\s\\S]*?<\\/table>/) || [''])[0]}</div>` : '') + renderArranjoDetail(m) + renderCamadaDetail(m))}")
troca("renderLegislacaoDetail(m) + `<div style=\"margin-top:12px;border-top:1px dashed var(--border);padding-top:8px;\"><b style=\"font-size:12.5px;\">Literatura</b></div>` + ",
      "renderLegislacaoDetail(m) + `<div style=\"margin-top:12px;border-top:1px dashed var(--border);padding-top:8px;\"><b style=\"font-size:12.5px;\">Literatura</b></div>` + ")
s = s.replace("+ renderNoticiasDetail(m))}", "+ renderNoticiasDetail(m) + `<p class=\"na-tese-card\">Na tese: a ficha de ${m.nome} no Apêndice H; as normas lidas no Apêndice D; a revisão sistemática no Apêndice C. <a href=\"" + 'tese/Tese%20-%20Volume%20II%20-%20Ap%C3%AAndices.pdf' + "\" target=\"_blank\" rel=\"noopener\">Abrir o Volume II (PDF) →</a></p>`)}", 1)
assert 'na-tese-card' in s
troca('</style>\n</head>', '''  .bt1.amarelo{background:var(--amarelo) !important;border-color:var(--amarelo) !important;color:#0E0E10 !important;}
  .na-tese-card{margin:12px 0 0;padding-top:8px;border-top:1px dashed var(--border);font-size:11.5px;color:var(--muted);line-height:1.5;}
  .na-tese-card a{color:var(--rosa);}
</style>
</head>''')
# 14d. cores do mapa: uma régua sequencial só, legível no fundo escuro; arranjo com três cores distintas; legenda do contorno
troca("  pib_pc: ['#c6dbef', '#9ecae1', '#4292c6', '#2171b5', '#084594'],", "  pib_pc: ['#2E3F6E', '#3D6FA8', '#43A3A3', '#8CCB7E', '#F5E400'],")
troca("  motorizacao: ['#e5d8ec', '#c2a5cf', '#9970ab', '#762a83', '#40004b'],", "  motorizacao: ['#2E3F6E', '#3D6FA8', '#43A3A3', '#8CCB7E', '#F5E400'],")
troca("  rec_prop_pc: ['#deebf7', '#9ecae1', '#4292c6', '#2171b5', '#08306b'],", "  rec_prop_pc: ['#2E3F6E', '#3D6FA8', '#43A3A3', '#8CCB7E', '#F5E400'],")
troca("""  'Inferior a 20 mil': '#c6dbef', 'Entre 20 e 100 mil': '#6baed6',
  'Entre 100 e 250 mil': '#3182bd', 'Entre 250 e 500 mil': '#08519c', 'Acima de 500 mil': '#08306b'""",
      """  'Inferior a 20 mil': '#2E3F6E', 'Entre 20 e 100 mil': '#3D6FA8',
  'Entre 100 e 250 mil': '#43A3A3', 'Entre 250 e 500 mil': '#8CCB7E', 'Acima de 500 mil': '#F5E400'""")
troca("const ARRANJO_COLORS = { 'Sede/co-sede do arranjo': '#08519c', 'Satélite do arranjo': '#6baed6', 'Fora de arranjo': '#5c6470' };",
      "const ARRANJO_COLORS = { 'Sede/co-sede do arranjo': '#4C8DFF', 'Satélite do arranjo': '#B48CFF', 'Fora de arranjo': '#3a3f4a' };")
troca("""    el.innerHTML = itens.map(([c, r]) => `<span><span class="sw" style="background:${c}"></span>${r}</span>`).join('')""",
      """    document.getElementById('mapSvg')?.classList.add('contorno-forte');
    el.innerHTML = itens.map(([c, r]) => `<span><span class="sw" style="background:${c}"></span>${r}</span>`).join('')""")
troca("  el.innerHTML = html;\n}\n\nfunction fmtNum(v) {",
      """  const outro = state.colorBy !== 'tz';
  document.getElementById('mapSvg')?.classList.toggle('contorno-forte', outro);
  if (outro) html += `<span><span class="sw" style="background:transparent;border:2px solid var(--verde);"></span>Contorno verde: tem Tarifa Zero universal</span><span><span class="sw" style="background:transparent;border:2px solid var(--rosa);"></span>Contorno rosa: encerrada</span>`;
  el.innerHTML = html;
}

function fmtNum(v) {""")
troca('</style>\n</head>', '  #mapSvg.contorno-forte path.mun.tzpath{stroke-width:1.8;}\n</style>\n</head>')
# 14e. o espaço vazio ao lado do mapa: busca e "Colorir mapa por" vão para a coluna da direita, acima do card
i = s.index('  <div class="toolbar">\n    <div class="munisearch">'); j = s.index('  <div class="grid">', i)
ctl = s[i:j]; s = s[:i] + s[j:]
troca('    <div class="rightcol">\n      <div class="panel">\n        <h2>Município selecionado</h2>',
      '    <div class="rightcol">\n      <div class="panel ctl-mapa">\n' + ctl.replace('\n  ', '\n        ') + '      </div>\n      <div class="panel" style="margin-top:14px;">\n        <h2>Município selecionado</h2>')
troca('</style>\n</head>', '''  .ctl-mapa .toolbar, .ctl-mapa .controls{margin:0 !important;display:block !important;}
  .ctl-mapa .controls{margin-top:10px !important;}
  .ctl-mapa label{display:block;font-size:12px;color:var(--muted);margin-bottom:4px;}
  .ctl-mapa input, .ctl-mapa select{width:100%;box-sizing:border-box;}
  @media (max-width:820px){ #tab-explorar .grid > .rightcol{order:-1;} }
</style>
</head>''')
# 14f. "novo" na literatura era marca de trabalho (fator ausente do memorial de qualificação): sai
troca("${x.novo ? '<span class=\"novo\">novo</span>' : ''}", '')

# 14g. a coluna da direita (busca, cor do mapa e card) fica fixa inteira, sem sobrepor; carimbo do isolado legível
troca("  @media (min-width:821px){ #tab-explorar .rightcol > .panel{position:sticky;top:124px;max-height:calc(100vh - 140px);overflow:auto;} }",
      "  @media (min-width:821px){ #tab-explorar .rightcol{position:sticky;top:124px;align-self:start;max-height:calc(100vh - 140px);overflow:auto;} }")
troca("ARRANJO_COLORS[m.tipo_arranjo] === '#5c6470' ? '#9aa3b0' : ARRANJO_COLORS[m.tipo_arranjo]", "m.tipo_arranjo === 'Fora de arranjo' ? '#9aa3b0' : ARRANJO_COLORS[m.tipo_arranjo]")
troca("  .card-acoes.topo{position:sticky;top:0;z-index:3;", "  .card-acoes.topo{position:relative;z-index:3;")

# ------------------------------------------------------------------ 15. comentários do autor (13/11/2026, rodada 5 — fechamento)
# 15a. "Colorir mapa por": entra o uso do ônibus (Censo 2022), em quintis, na mesma escala de cores
troca('        <option value="pib_pc">PIB per capita</option>',
      '        <option value="onibus">Uso do ônibus para trabalho ou estudo (Censo 2022)</option>\n        <option value="pib_pc">PIB per capita</option>')
troca("  const v = colorBy === 'rec_prop_pc' ? m.rec_prop_pc : m[colorBy];", "  const v = colorBy === 'rec_prop_pc' ? m.rec_prop_pc : valorMetrica(m, colorBy);")
troca("      posicao: m.tz_status !== 'Ativa'", "      onibus: valorMetrica(m, 'onibus') != null ? fmtNum(valorMetrica(m, 'onibus')) + '% vão de ônibus' : 'sem dado',\n      posicao: m.tz_status !== 'Ativa'")
s = s.replace('</body>', """<script>
// uso do ônibus no mapa: quintis calculados dos dados do Censo embutidos no painel
(() => { const v = [...MUNI.values()].map(m => valorMetrica(m, 'onibus')).filter(x => x != null && !Number.isNaN(x)).sort((a, b) => a - b);
  if (!v.length) return; const q = p => v[Math.floor(p * (v.length - 1))];
  STATS.breaks.onibus = [q(0), q(.2), q(.4), q(.6), q(.8), q(1)]; PALETTES.onibus = PALETTES.pib_pc; })();
</script>
</body>""", 1)
# 15b. busca e "Colorir mapa por" acima do mapa, lado a lado; a coluna da direita fica só com o card
i = s.index('      <div class="panel ctl-mapa">\n'); j = s.index('      <div class="panel" style="margin-top:14px;">\n        <h2>Município selecionado</h2>', i)
ctl = s[i:j]; s = s[:i] + s[j:].replace('      <div class="panel" style="margin-top:14px;">\n        <h2>Município selecionado</h2>', '      <div class="panel">\n        <h2>Município selecionado</h2>', 1)
ctl = ctl.replace('<div class="panel ctl-mapa">', '<div class="ctl-mapa linha">', 1)
troca('      <p class="sub">Duplo clique num município aproxima; selecionar uma UF no filtro enquadra o estado automaticamente.</p>\n',
      '      <p class="sub">Duplo clique num município aproxima; selecionar uma UF no filtro enquadra o estado automaticamente.</p>\n' + ctl)
troca('</style>\n</head>', '''  .ctl-mapa.linha{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:10px 0 12px;}
  .ctl-mapa.linha .controls{margin-top:0 !important;}
  @media (max-width:640px){ .ctl-mapa.linha{grid-template-columns:1fr;} }
</style>
</head>''')
# 15c. comparações e dispersão: só as variáveis que o painel usa (saem IBEU, IDH, óbitos no trânsito e CadÚnico)
for k in ('ibeu', 'idh', 'taxa_obitos_transito', 'cadunico_cobertura'):
    sub1(r"\n  \{ k: '%s', label: [^\n]*\}," % k, '')
# 15d. Literatura: chamada para contribuir logo depois de "Quais municípios a literatura estuda"
troca('<div class="panel" style="margin-top:14px;"><h3 class="pt">Quais municípios a literatura estuda</h3><div id="rslMunis"></div></div>',
      '<div class="panel" style="margin-top:14px;"><h3 class="pt">Quais municípios a literatura estuda</h3><div id="rslMunis"></div></div>\n'
      '    <div class="contribua"><div><b>Conhece um estudo sobre a Tarifa Zero que não está aqui?</b><span>Artigo, tese, relatório ou levantamento: envie para a pesquisa. Cada contribuição é revisada antes de entrar no painel.</span></div><a class="bt1" href="pesquisa.html">Envie para a pesquisa →</a></div>')
# 15e. "Copiar o link": cinza, no sistema dos botões secundários, e o primeiro da fila
troca('<button type="button" class="bt1 amarelo" data-copia-mun="${m.id}">Copiar o link deste município</button>',
      '<button type="button" class="bt2" data-copia-mun="${m.id}">Copiar o link deste município</button>')

s = s.replace('<!-- proposta -->', '')
s = s.replace('</head>', '<meta name="proposta" content="proposta_etapa2">\n</head>', 1)
open(ARQ, 'w', encoding='utf-8').write(s)
print('etapa 2 aplicada:', ARQ, len(s.encode()), 'bytes')
