#!/usr/bin/env python3
"""
rede_etapa5.py — quinta rodada da Rede de empresas (13/11/2026). Roda depois de rede_etapa4.py.
Relê os Capítulos 6, 7 e 8 da tese e traz para a página o que eles dizem.

  GE × TZ        mapa das zonas na entrada (Mapa 9); o passo 1 explicado em probabilidade (Gráfico 19);
                 recuos e posição do setor numa caixa só (Seções 8.4 e 8.5, Quadros 32 a 35), com Tijucas do Sul;
                 "Os casos" sem repetir: quem opera a gratuidade (Tabela 6), com Caucaia e Paranaguá
  A rede         do cadastro ao grupo, passo a passo (Tabela 4); legenda que explica sócio e sócio do sócio;
                 filtro em maiúsculas; a roda do mouse volta a rolar a página
  Concentração   o funil do capital (Seção 6.2); "A rede em números" sai de dentro da caixa 1
  Além do ônibus o que a tese encontrou fora do ônibus (Seção 6.4 e Quadro 20) no lugar dos números soltos;
                 escolha por federação e grupo em listas; "Explore um grupo" passa a ser a caixa 1

Uso: python3 rede_etapa5.py rede-ge-proposta.html painel.html [arquivo do painel com os dados]
"""
import json, os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, 'rede-ge-proposta.html')
PAINEL = sys.argv[2] if len(sys.argv) > 2 else 'painel.html'
FONTE = sys.argv[3] if len(sys.argv) > 3 else next(p for p in (os.path.join(RAIZ, 'painel-proposta.html'), os.path.join(RAIZ, 'painel.html')) if os.path.exists(p))
s = open(ARQ, encoding='utf-8').read()
assert 'rede_etapa4' in s and 'rede_etapa5' not in s, 'rode rede_etapa4.py antes, uma vez só'

def troca(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, f'âncora com {c} ocorrência(s), esperado {n}: {a[:100]!r}'
    s = s.replace(a, b)
def fim(i, tag='details'):
    prof, k = 0, i
    while True:
        a = s.find('<' + tag, k); f = s.find('</' + tag + '>', k)
        if a != -1 and a < f: prof += 1; k = a + len(tag) + 1
        else:
            prof -= 1; k = f + len(tag) + 3
            if prof == 0: return k
def bloco(ini, tag='details'):
    global s
    i = s.index(ini); k = fim(i, tag); t = s[i:k]; s = s[:i] + s[k:]; return t
def J(t, i): return json.loads(re.search(r'<script[^>]*id="%s"[^>]*>(.*?)</script>' % i, t, re.S).group(1))

# ------------------------------------------------------------------ dados do mapa das zonas (Mapa 9)
# Universal = camada 1 da régua; grupo presente = estabelecimento de grupo com mais de uma empresa (endereço, 2024).
# Os pontos dos municípios sem grupo vêm do centroide da malha do painel, levado à projeção da rede por ajuste afim.
p = open(FONTE, encoding='utf-8').read()
M = J(p, 'data-muni'); C = M['cols']; D = {r[0]: dict(zip(C, r)) for r in M['data']}
ARS = J(s, 'data-rede'); NOS = {n['id']: n for n in ARS['nos']}; PT = ARS['geo']['pontos']
T = J(p, 'topo-data'); sc, tr = T['transform']['scale'], T['transform']['translate']
arcs = []
for a in T['arcs']:
    x = y = 0; q = []
    for dx, dy in a: x += dx; y += dy; q.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
    arcs.append(q)
cent = {}
for g in T['objects']['municipios_simpl']['geometries']:
    if g['type'] not in ('Polygon', 'MultiPolygon'): continue
    best = None
    for poly in (g['arcs'] if g['type'] == 'MultiPolygon' else [g['arcs']]):
        r = []
        for i in poly[0]: r += arcs[i] if i >= 0 else arcs[~i][::-1]
        cr = [r[k][0] * r[k + 1][1] - r[k + 1][0] * r[k][1] for k in range(len(r) - 1)]; ar = sum(cr) / 2
        if ar: cx = sum((r[k][0] + r[k + 1][0]) * cr[k] for k in range(len(cr))) / (6 * ar); cy = sum((r[k][1] + r[k + 1][1]) * cr[k] for k in range(len(cr))) / (6 * ar)
        else: cx = sum(v[0] for v in r) / len(r); cy = sum(v[1] for v in r) / len(r)
        if best is None or abs(ar) > abs(best[0]): best = (ar, cx, cy)
    cent[str(g['properties']['cod_ibge'])] = best[1:]
# ajuste afim lon/lat -> projeção da rede, por mínimos quadrados (equações normais 3x3)
com = [c for c in PT if c in cent]
def resolve(Mx, v):
    Mx = [row[:] + [v[i]] for i, row in enumerate(Mx)]
    for i in range(3):
        piv = max(range(i, 3), key=lambda r: abs(Mx[r][i])); Mx[i], Mx[piv] = Mx[piv], Mx[i]
        for r in range(3):
            if r != i:
                f = Mx[r][i] / Mx[i][i]; Mx[r] = [a - f * b for a, b in zip(Mx[r], Mx[i])]
    return [Mx[i][3] / Mx[i][i] for i in range(3)]
X = [(cent[c][0], cent[c][1], 1.0) for c in com]
XtX = [[sum(x[i] * x[j] for x in X) for j in range(3)] for i in range(3)]
coef = [resolve(XtX, [sum(x[i] * PT[c][d] for x, c in zip(X, com)) for i in range(3)]) for d in (0, 1)]
def proj(c):
    if c in PT: return PT[c]
    lo, la = cent[c]; return [round(coef[0][0] * lo + coef[0][1] * la + coef[0][2], 1), round(coef[1][0] * lo + coef[1][1] * la + coef[1][2], 1)]
uni = {c for c, d in D.items() if str(d['tz_regua_sub'] or '').startswith('1')}
gp = {c for c, gs in ARS['presenca'].items() if any(NOS[g]['n_emp'] > 1 for g in gs)}
POS = {'Fora de arranjo': 0, 'Satélite do arranjo': 1, 'Sede/co-sede do arranjo': 2}
zon = []
for c in sorted(gp | uni):
    if c not in D or (c not in PT and c not in cent): continue
    z = 1 if c in gp and c in uni else (0 if c in gp else 2)
    x, y = proj(c)
    zon.append([c, f"{D[c]['nome']}/{D[c]['uf']}", x, y, z, POS.get(D[c]['tipo_arranjo'], 0)])
DADOS_Z = json.dumps(zon, ensure_ascii=False, separators=(',', ':'))

# ------------------------------------------------------------------ GE × TZ: o mapa na entrada
troca('<div class="passos"><a href="#ge-81">1 · Adoção</a><a href="#ge-82">2 · Porta de entrada</a><a href="#ge-83">3 · Quem fica e o que muda</a><a href="#ge-84">4 · Recuos e encerramentos</a><a href="#ge-85">5 · O que o setor pede</a><a href="#ge-casos">Os casos</a></div></div>',
      '<div class="passos"><a href="#ge-81">1 · Adoção</a><a href="#ge-82">2 · Porta de entrada</a><a href="#ge-83">3 · Quem fica e o que muda</a><a href="#ge-84">4 · Recuos e o que o setor pede</a><a href="#ge-casos">Os casos</a></div></div>\n'
      '  <div class="panel mapa-zonas" id="ge-mapa"><h2>Onde os grupos encontram a Tarifa Zero</h2>'
      '<p class="legenda">Cada ponto é um município com empresa de grupo econômico ou com Tarifa Zero universal. <b>Grupo presente</b> é ter estabelecimento de empresa de grupo com mais de uma empresa, pelo endereço do cadastro de 2024: presença não é operação. Clique num ponto para ver o município.</p>'
      '<div class="mz-ctl"><button type="button" class="on" data-pos="todos">Todos</button><button type="button" data-pos="arranjo">Só os de arranjo (satélites e sedes)</button></div>'
      '<div class="mz-grid"><div class="mz-mapa" id="mzMapa"></div><div class="mz-lado"><div id="mzLeg"></div><div id="mzInfo" class="mz-info">Clique num ponto.</div>'
      '<p class="legenda" style="margin-top:12px;">Sozinho, o mapa não mostra barreira. Sem nenhum controle, a adoção com e sem grupo é quase igual nos satélites (10,7% e 11,2%) e nas sedes dos arranjos (8,2% e 8,3%); nas cidades isoladas, é maior com grupo (9,4% e 1,9%), porque a empresa de grupo marca que ali há um sistema de ônibus. A diferença só aparece quando se comparam cidades parecidas: é o passo 1.</p>'
      '<p class="legenda">Os municípios de arranjo com grupo e sem a política, concentrados no Sudeste e no Sul, são onde a hipótese pode ser posta à prova: completar neles o operador e o contrato permitiria trocar a presença pela operação comprovada.</p></div></div>'
      '<p class="pmeta" style="margin-top:6px;">Na tese: Mapa 9 e Seção 8.1. Universal: camada 1 da régua descritiva; política parcial fica fora.</p></div>\n'
      f'  <script type="application/json" id="data-zonas">{DADOS_Z}</script>')

# ------------------------------------------------------------------ GE × TZ: passo 1 em probabilidade
i = s.index('<details class="pacote" id="ge-81"'); k = fim(i)
velho = s[i:k]
svg_rc = re.search(r'<svg viewBox="0 0 640 264".*?</svg>', velho, re.S).group(0).replace('Franjas dos arranjos (satélites)', 'Satélites dos arranjos')
def barra_p(rot, sem, com, nota):
    w = lambda v: f'{v / 10 * 100:.0f}%'
    f = lambda v: f'{v:.1f}'.replace('.', ',') + '%'
    return (f'<div class="pb-lin"><div class="pb-rot"><b>{rot}</b><span>{nota}</span></div><div class="pb-bars">'
            f'<div class="pb-b"><span>sem grupo</span><i style="width:{w(sem)};background:#9a9aa6;"></i><b>{f(sem)}</b></div>'
            f'<div class="pb-b"><span>com grupo</span><i style="width:{w(com)};background:var(--rosa);"></i><b>{f(com)}</b></div></div></div>')
novo81 = ('<details class="pacote" id="ge-81" open><summary class="phead"><span class="pnum">1</span><div><h2>Onde há grupo, há menos Tarifa Zero</h2>'
          '<p>Entre duas cidades parecidas que gravitam em torno de uma metrópole, a que tem empresa de grupo adota a Tarifa Zero universal com cerca de um terço da frequência. Nas cidades isoladas, ter ou não grupo não muda nada.</p>'
          '<div class="pmeta">Na tese: Seção 8.1, Gráfico 19 e Figura 26</div></div><span class="pseta" aria-hidden="true">▾</span></summary>\n'
          '<p class="explica">O teste compara cidades parecidas, do mesmo porte, com a mesma capacidade fiscal e no mesmo estado (4.103 municípios das 14 UFs com ao menos uma adoção universal), e calcula a chance de adotar a Tarifa Zero universal com e sem empresa de grupo no município, em cada posição no arranjo populacional do IBGE.</p>'
          '<div class="pbar">'
          + barra_p('Satélites dos arranjos', 9.5, 3.2, 'gravitam em torno de um centro: é onde o ônibus local encosta no mercado metropolitano · cerca de um terço')
          + barra_p('Sedes dos arranjos', 6.6, 2.7, 'polos e co-polos · menos da metade')
          + barra_p('Cidades isoladas', 3.6, 4.9, 'fora de arranjo · sem diferença')
          + '</div><p class="legenda">Probabilidade ajustada: a média das previsões do modelo como se todos os municípios estivessem naquela posição, mantidas as demais características. Regressão logística de Firth, com efeito fixo de UF.</p>'
          '<ul class="leve leitura81">'
          '<li><b>Os grandes grupos acentuam a queda nos satélites.</b> Com os 26 grupos que detêm metade do capital, a chance cai de 8,1% para 1,9% nos satélites; nas sedes, a diferença é pequena (4,3% e 3,4%).</li>'
          '<li><b>O resultado resiste a outro universo.</b> Refeito só nos municípios que têm ônibus, por três critérios (MUNIC 2017, MUNIC 2020 e indício de sistema), a associação negativa nos satélites se mantém nos três.</li>'
          '<li><b>O dinheiro pesa onde falta o serviço.</b> A dependência do Fundo de Participação dos Municípios também acompanha menos adoção, mas só onde não há ônibus: é a barreira de criar o serviço, e não a do operador.</li>'
          '<li><b>O que o teste não prova.</b> Presença de grupo no cadastro não é operação, e a posição no arranjo aproxima a atratividade do mercado sem medi-la. A tese conclui que o padrão é compatível com a hipótese, e não que a demonstra.</li></ul>'
          '<details class="mais"><summary>O número do modelo: razão de chances</summary><p class="legenda">Quanto a chance de adotar com grupo representa da chance sem grupo. Abaixo de 1, menos adoção.</p>' + svg_rc + '</details>'
          '<p style="margin:12px 0 0;"><a class="bt2" href="#ge-mapa">Ver no mapa ↑</a><a class="bt2" href="#" data-ir="onde-grupos">Filtrar a rede por cidade →</a></p>\n  </details>')
s = s[:i] + novo81 + s[k:]

# ------------------------------------------------------------------ casos ricos (fichas do Apêndice H e Seções 6.6, 8.4)
def caso(nome, linha, hist, leitura, ge=None, cod=None):
    h = ''.join(f'<li><b>{d}</b> {t}</li>' for d, t in hist)
    lk = (f'<a href="{PAINEL}#mun-{cod}">ver no painel →</a>' if cod else '') + (f'<a href="#{ge}" class="lk-rede" data-ge="{ge}">ver o grupo na rede →</a>' if ge else '')
    return (f'<div class="caso-rico"><div class="cr-cab"><b>{nome}</b><span>{linha}</span></div><ol class="cr-hist">{h}</ol>'
            f'<p class="cr-leit">{leitura}</p><div class="cr-lk">{lk}</div></div>')
MONTE_MOR = caso('Monte Mor (SP)', '65 mil habitantes · satélite do arranjo de Campinas · universal de 2023 a 2025',
    [('29/12/2023', 'Tarifa Zero universal, por aditivo à concessão da Rápido Luxo Campinas.'),
     ('09/09/2025', 'A Câmara aprova por 13 a 2 a lei que revoga a gratuidade universal.'),
     ('01/11/2025', 'Vale a "Tarifa do Bem": gratuidade só para idosos, pessoas com deficiência e famílias do CadÚnico em extrema pobreza, com cadastro; os demais pagam R$ 6,00.'),
     ('o motivo', 'O recuo é atribuído à restrição orçamentária.')],
    'A rede de sócios põe a concessionária no grupo Belarmino, uma das unidades do topo. A gratuidade entrou e saiu sem que a concessão mudasse de mão: é o único recuo com operador de grupo.', 'GE-003', '3531803')
SAO_CAETANO = caso('São Caetano do Sul (SP)', '166 mil habitantes · satélite do arranjo de São Paulo · universal desde 2023',
    [('out/2023', 'Tarifa Zero universal, por aditivo à concessão da Vipe.'),
     ('2024 a 2026', 'A demanda passa de 20 mil para 80 mil passageiros por dia, contra 50% de aumento previsto.'),
     ('14/07/2026', 'O 4º aditivo troca a remuneração por veículo e por quilômetro pelo custo apurado menos a receita.'),
     ('15/07/2026', 'Um dia depois, a gratuidade passa a ser só de moradores cadastrados; quem vem de fora volta a pagar R$ 5.')],
    'O recuo veio com o mesmo operador, e o contrato foi refeito antes da norma.', None, '3548807')
TIJUCAS = caso('Tijucas do Sul (PR)', '18 mil habitantes · Região Metropolitana de Curitiba · universal desde 2015, com interrupção',
    [('dez/2015', 'A Prefeitura passa a operar a gratuidade universal nas cinco linhas municipais.'),
     ('2020 a 2023', 'O Município loca ônibus com motorista e paga a operação.'),
     ('2022 e 2023', 'Uma concessão com tarifa de R$ 5,00 e subsídio do déficit substitui a gratuidade e é anulada em novembro de 2023.'),
     ('desde dez/2023', 'O Município volta a pagar a operação sem tarifa: por contrato emergencial e, desde julho de 2025, por quilômetro.')],
    'Um recuo revertido, sem grupo. A lei de 2015 foi revogada em 2021: hoje a gratuidade está no contrato, que proíbe qualquer cobrança.', None, '4127601')
ITABORAI = caso('Itaboraí (RJ)', '224 mil habitantes · satélite do arranjo do Rio de Janeiro · universal desde 2025',
    [('nov/2023', 'O Executivo decide a gratuidade sem negociar com a concessionária.'),
     ('dez/2023 a jul/2024', 'Uma liminar suspende o serviço.'),
     ('mai/2025', 'A gratuidade vira universal, por aditivo à concessão da Maravilha Auto Ônibus, que opera desde 1985.'),
     ('hoje', 'A lei só autoriza o subsídio ao operador; a empresa alega não receber, e a dívida é contestada.')],
    'A gratuidade coube no contrato que já existia. O operador é empresa familiar local, sem grupo: o contrato condiciona a política com ou sem grupo.', None, '3301900')
MARICA = caso('Maricá (RJ)', '197 mil habitantes · satélite do arranjo do Rio de Janeiro · universal desde 2014',
    [('2013', 'A gratuidade cobre parte das linhas, em concorrência com as concessionárias privadas.'),
     ('dez/2014', 'A Empresa Pública de Transportes assume e a gratuidade vira universal, paga sobretudo pelos royalties do petróleo. As concessionárias contestam na Justiça.'),
     ('2024 e 2025', 'A empresa pública passa a alugar ônibus com motorista, pagos por quilômetro: hoje, 132 dos 157 ônibus da frota gratuita são de empresas contratadas.'),
     ('2025', 'Uma empresa do grupo Barata, o maior do país, volta como locadora, pelo maior contrato anual de Tarifa Zero do levantamento.')],
    'A cidade rompeu com a concessão, e o incumbente de grande grupo voltou por outro contrato.', 'GE-001', '3302700')
CAUCAIA = caso('Caucaia (CE)', '356 mil habitantes · satélite do arranjo de Fortaleza · universal desde 2021',
    [('antes de 2021', 'Segundo a literatura, o operador não abandona uma linha pouco rentável: pressiona por mais subsídio municipal para continuar.'),
     ('ago/2021', 'A Prefeitura lança o "Passe Livre", gratuidade universal por aditivo à concessão da Empresa Vitória, contratada em 2016.'),
     ('dez/2024', 'Com dívida da Prefeitura de R$ 14 milhões, a frota é reduzida em 23%.'),
     ('2026', 'Uma lei torna o programa permanente, e a concessão é renovada por dez anos em junho.')],
    'Uma empresa do grupo Barata, unidade do topo do capital, opera a gratuidade pela concessão que já detinha, agora renovada: renegociação com o incumbente, e não ruptura.', 'GE-001', '2303709')
PARANAGUA = caso('Paranaguá (PR)', '146 mil habitantes · fora de arranjo populacional · universal desde 2022',
    [('2021', 'Uma lei complementar cria a Tarifa Zero, com um fundo de transporte próprio.'),
     ('2022', 'A gratuidade começa por aditivo à concessão existente, com cadastro prévio para medir a demanda.'),
     ('um ano depois', 'A demanda sobe 146%.'),
     ('depois', 'A taxa criada para custear a política cai no Judiciário.')],
    'Uma empresa da família Gulin, unidade do topo do capital, opera a gratuidade pela concessão que já detinha.', 'GE-014', '4118204')

# ------------------------------------------------------------------ GE × TZ: 8.4 e 8.5 numa caixa só
Q32 = [('Ubiratã (PR)', '24.749', 'jan. a mar. 2025', 'Prefeitura, com ônibus e motorista próprios', 'fim sem ato formal citado'),
       ('Porto Real (RJ)', '20.373', '2011 a 2017', 'Prefeitura', 'serviço interrompido e retomado pago, por concessão'),
       ('Jaboticabal (SP)', '71.821', 'nov. 2020 a abr. 2021', 'empresa contratada, sem grupo', 'lei revogada; o fundo não tinha receita'),
       ('Pirapora do Bom Jesus (SP)', '18.370', '2020 a 2022', 'Prefeitura', 'ato do fim não localizado; retomada anunciada em 2025'),
       ('Getulina (SP)', '10.232', 'abr. a jul. 2026', 'Prefeitura, com motorista concursado', 'baixa demanda')]
tab32 = ('<div class="getabwrap" style="max-height:none;"><table class="getab q32"><thead><tr><th>Município</th><th>População</th><th>Gratuidade</th><th>Quem operava</th><th>Como acabou</th></tr></thead><tbody>'
         + ''.join(f'<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td><td>{e}</td></tr>' for a, b, c, d, e in Q32) + '</tbody></table></div>')
SETOR = [('NTU, 2024', 'Chama a Tarifa Zero de "promissora", concentrada em cidades pequenas, e liga a expansão à renovação da frota.'),
         ('NTU, 2025', 'A universal "não pode ser considerada tendência nacional para qualquer perfil de cidade"; seria inviável nas metrópoles.'),
         ('NTU, nota oficial de 6/11/2025', 'Aceita a gratuidade como inclusão social, com duas condições: respeito aos contratos de concessão vigentes e a "Tarifa Zero para Quem Precisa", focalizada.'),
         ('ANTP', 'Um fundo nacional, com o Estado como "financiador do financiador" e liberdade de operação para as empresas.'),
         ('NTU, "Transportes para Todos", 2026', 'Cerca de 85% do custo dos sistemas pagos pelo vale-transporte modernizado, por um vale social e pelas pastas de cada gratuidade; o resto, pelo município.')]
novo84 = ('<details class="pacote" id="ge-84"><summary class="phead"><span class="pnum">4</span><div><h2>Recuos, encerramentos e o que o setor pede</h2>'
          '<p>Fins e recuos são raros, e nenhuma das políticas universais encerradas tinha operador de grupo. Onde houve recuo com grupo, a concessão ficou. O setor não recusa o dinheiro público: pede que ele preserve os contratos.</p>'
          '<div class="pmeta">Na tese: Seções 8.4 e 8.5, Estudo de caso 1 e Quadros 32 a 35</div></div><span class="pseta" aria-hidden="true">▾</span></summary>\n'
          '<h3 class="h3c">Os recuos</h3><div class="casos-ricos">' + MONTE_MOR + SAO_CAETANO + TIJUCAS + '</div>'
          '<h3 class="h3c">As cinco políticas universais encerradas</h3>' + tab32 +
          '<p class="explica">Em quatro delas, a Prefeitura operava o serviço; a quinta tinha operador local, sem grupo. Os fins documentados são de custeio e de capacidade, em municípios pequenos e médios: isso favorece a explicação rival do custo, e não a pressão de um incumbente. O que a hipótese prevê aparece em outro lugar: no desenho que acomoda a gratuidade sem tocar no contrato, como em Monte Mor.</p>'
          '<p class="explica">A 3ª pesquisa da NTU (2026) contou oito municípios que deixaram a Tarifa Zero. Conferidos com a base: em dois, a gratuidade universal voltou (Picos e Tijucas do Sul); em um, virou parcial (Monte Mor); cinco estão encerradas, uma delas desde 2018. Só Monte Mor tinha operador de grupo.</p>'
          '<h3 class="h3c">O que o setor pede</h3><ol class="linha-setor">' + ''.join(f'<li><b>{a}</b><span>{b}</span></li>' for a, b in SETOR) + '</ol>'
          '<p class="cr-leit" style="font-size:14px;">Nenhuma proposta muda o destinatário do recurso nem a forma de remunerar o operador; o que muda é quem paga. Na régua da tese, o desenho do setor é o da garantia de receita sem controle: rompe o incentivo da remuneração por passageiro, mas não traz transparência, controle social nem exigência de desempenho.</p>'
          '<p class="legenda">A fonte é interessada: é declaração de entidade de representação, e não conduta das empresas dos grupos, e a filiação das empresas às entidades não foi levantada. Em Belo Horizonte, as federações contrárias ao PL 60/2025 não têm vínculo identificado com os grupos da rede.</p>\n  </details>')
i = s.index('<details class="pacote" id="ge-84"'); k = fim(i)
s = s[:i] + novo84 + s[k:]
bloco('<details class="pacote" id="ge-85"')

# ------------------------------------------------------------------ GE × TZ: os casos, sem repetir, com a Tabela 6
T6 = [('Empresa de um dos 327 grupos', 21, 8, [12, 7, 1, 1]), ('Empresa de ônibus sem grupo', 29, 3, [8, 11, 10, 0]), ('Empresa fora do núcleo do ônibus', 49, 3, [3, 27, 16, 3])]
CORF = ['#FF2D6B', '#F5E400', '#4C8DFF', '#3a3f4a']
ROTF = ['aditivo à concessão existente', 'contrato novo, licitado', 'emergencial, locação com motorista ou operação pública', 'forma não apurada']
def lin6(rot, n, g100, f):
    seg = ''.join(f'<i style="width:{v / n * 100:.1f}%;background:{CORF[k]};" title="{ROTF[k]}: {v}">{v if v >= 3 else ""}</i>' for k, v in enumerate(f) if v)
    return f'<div class="t6-lin"><div class="t6-rot"><b>{rot}</b><span>{n} políticas · {g100} com 100 mil habitantes ou mais</span></div><div class="t6-bar" style="width:{n / 49 * 100:.0f}%">{seg}</div></div>'
casos = ('<div class="panel" id="ge-casos" style="margin-top:16px;"><h2>Os casos: quem opera a gratuidade</h2>'
         '<p class="explica">O contrato diz o que a presença no cadastro não diz. Em 99 políticas, o operador está comprovado em documento (contrato, edital, empenho, norma ou notícia datada); nas demais, a operação é pública ou o operador não foi apurado, e não apurado não é zero.</p>'
         '<div class="t6">' + ''.join(lin6(*t) for t in T6) + '</div>'
         '<div class="legend t6-leg">' + ''.join(f'<span><i style="background:{c};"></i>{r}</span>' for c, r in zip(CORF, ROTF)) + '</div>'
         '<p class="explica">Com grupo, a gratuidade entra sobretudo por aditivo à concessão (12 de 21); fora do núcleo do ônibus, por contrato novo (27 de 49), quase sempre em municípios pequenos, onde não há empresa de ônibus urbano a contratar. Das 21 políticas de grupo, 7 são de empresas de cinco unidades do topo do capital: Barata (Caucaia e, como locadora, Maricá), Gulin (Paranaguá), Belarmino (Monte Mor, até 2025), SOU (Palmas, com gratuidade parcial) e Turin (Mariana e Ouro Branco).</p>'
         '<p class="pmeta">Na tese: Seção 6.6 e Tabela 6; casos resumidos das fichas do Apêndice H e das Seções 7.3 a 7.5.</p>'
         '<div class="casos-ricos">' + CAUCAIA + MARICA + PARANAGUA + '</div></div>\n')
i = s.index('<div class="panel" id="ge-casos"'); k = fim(i, 'div')
s = s[:i] + casos + s[k:].lstrip('\n')

# ------------------------------------------------------------------ A rede: do cadastro ao grupo (Tabela 4) e a legenda
PASSOS = [('48,4 mil', 'estabelecimentos com o ônibus municipal ou metropolitano como atividade principal, em qualquer situação', 48400),
          ('14.988', 'estabelecimentos ativos, de 12.907 empresas (CNPJ)', 14988),
          ('13.569', 'sócios distintos, em 16.547 vínculos; só 7.680 empresas têm sócio com capital registrado', 13569),
          ('1.238', 'sócios-ponte, que ligam duas empresas ou mais', 1238),
          ('327', 'grupos econômicos, com 1.040 empresas', 327),
          ('316', 'unidades de controle, somados os grupos com controle comum', 316),
          ('22', 'unidades detêm metade do capital declarado', 22)]
import math
funil = ('  <div class="panel do-cadastro"><h2>Do cadastro ao grupo</h2><p class="legenda">Como a pesquisa chegou aos grupos, a partir do cadastro de empresas da Receita Federal (maio de 2024). Cada passo foi conferido em 136 rodadas de verificação em fontes externas: órgãos gestores, ANTT, processos e imprensa.</p><ol class="dc">'
         + ''.join(f'<li><b>{n}</b><i style="width:{math.log10(v) / math.log10(48400) * 100:.0f}%"></i><span>{t}</span></li>' for n, t, v in PASSOS)
         + '</ol><p class="pmeta">Na tese: Tabela 4 e Seção 6.1. Grupo econômico é uma inferência a partir dos sócios em comum; endereço não é operação.</p></div>\n')
troca('  <div class="filtro-rede">', funil + '  <div class="filtro-rede">')
troca('<p class="legenda">Cada círculo é um grupo; cada linha, uma ligação: <b style="color:var(--rosa);">rosa</b>, mesmo bloco de controle; <b>cinza</b>, sócio em comum. Clique num grupo para abrir a ficha.</p>',
      '<div class="como-ler"><p><b>O círculo é um grupo.</b> Dentro dele, as empresas já estão ligadas por um <b>sócio em comum</b>: é o que define o grupo econômico (1º nível). O tamanho segue o número de empresas ou o capital.</p>'
      '<p><b>A linha liga dois grupos.</b> Ela aparece quando se segue a cadeia além do grupo, o <b>sócio do sócio</b>: as holdings sócias e os sócios delas. <b style="color:var(--rosa);">Rosa</b>: a ligação basta para tratar os dois grupos como um só controle (graus A e B). <b>Cinza</b>: sócios em comum, sem prova de controle comum. A espessura conta os sócios em comum.</p>'
      '<p class="legenda">Como essas ligações viram unidades de controle, linhagens familiares e federações, e quanto isso muda a concentração, está na aba <a href="#concentracao" data-ir-aba="concentracao">Concentração</a>. Clique num grupo para abrir a ficha.</p></div>')

# ------------------------------------------------------------------ Concentração: o funil do capital; "A rede em números" fora da caixa 1
MED = bloco('<details class="pacote" id="medidas-cx">')
i = s.index('<details class="pacote" id="agrupamentos"'); k = fim(i)
s = s[:k] + '\n  ' + MED.strip() + s[k:]
i = s.index('</summary>', s.index('<details class="pacote" id="agrupamentos"')) + len('</summary>')
s = s[:i] + '\n<div id="funilCapital" class="funil-cap"></div>' + s[i:]
troca('<p class="legenda">Como a tese junta os 327 grupos econômicos, do vínculo mais forte ao mais fraco, e quanto cada passo muda a concentração. A leitura principal é a das unidades de controle (A + B).</p>',
      '<p class="legenda">Como a tese junta os 327 grupos econômicos seguindo o sócio do sócio, do vínculo mais forte ao mais fraco, e quanto cada passo muda a concentração. A leitura principal é a das unidades de controle (A + B); a das federações mede articulação entre famílias, e não controle.</p>')

# ------------------------------------------------------------------ Além do ônibus: o que a tese encontrou; listas; ordem
troca('Além do ônibus: as holdings sócias das empresas de transporte e os negócios dos sócios dessas holdings em outros setores. Vínculo de sócio não é controle.',
      'Além do ônibus: o que os donos das empresas de ônibus têm fora dele. Seguindo o sócio do sócio, a tese encontra holdings de família, capital fechado e negócios na cadeia do veículo, nos trilhos, na bilhetagem, nas finanças e nos imóveis. Vínculo de sócio não é controle.')
ACH = [('A holding é a forma da herança', 'É o instrumento da sucessão, uma por ramo ou herdeiro: os Gulin têm 30 holdings com o sobrenome entre os sócios. O controle repousa na família: só em 9 dos 165 grupos com três empresas ou mais a holding é o sócio cuja saída desconectaria o grupo.'),
       ('Capital fechado, nenhum em bolsa', 'Nenhuma empresa dos 327 grupos nem das 361 holdings sócias é companhia aberta. A financeirização documentada é de capital fechado: holdings, fundo de investimento em participações, banco, securitizadoras e crédito direto. O capital estrangeiro entra pela holding, como o português no grupo Barata.'),
       ('Fora do ônibus, imóveis antes de finanças', 'Os sócios das 98 holdings que ligam os grupos médios e grandes estão em 1.164 empresas de outros setores. Das 255 classificadas como financeiras, 242 são outras holdings; os setores que pesam são o transporte fora do recorte (227), os imóveis (144), o comércio (106) e a construção (96).'),
       ('O ônibus como ativo-âncora', 'O contrato de operação dá escala, crédito e acesso à bilhetagem, sobre os quais os outros negócios se apoiam. É aí que a Tarifa Zero toca o patrimônio dos grupos: ao suprimir a tarifa, suprime também a receita antecipada que circula pela bilhetagem.')]
Q20C = ['Veículo e carroceria', 'Trilhos', 'Bilhetagem e passagens', 'Finanças', 'Energia, mídia e imóveis']
Q20 = [('GE-001', 'Barata', ['Guanabara Diesel e Ceará Diesel (C); concessionárias e fábrica de ônibus em 1998 (I)', '', 'conselho da holding da RioCard (I); ClickBus (I)', 'Banco Guanabara; duas securitizadoras; gestora de recursos (C)', 'dezenas de imobiliárias (C)']),
       ('GE-003', 'Belarmino', ['Sambaíba Distribuidora e mais três revendas de veículos (C); concessionárias Mercedes-Benz (I)', '', '', '', '']),
       ('GE-004', 'Ruas', ['Caio Induscar; concessionárias Mercedes-Benz (I)', 'Linhas 5 e 17 do Metrô de São Paulo (I)', '', '', 'publicidade nos pontos de ônibus de São Paulo, até 2021 (I)']),
       ('GE-005', 'Comporte', ['Renovabus e Mapa Comércio (C)', 'Metrô BH, conselho (C); VLT da Baixada Santista, diretoria (C); Linhas 7, 11, 12 e 13 em São Paulo (I)', 'Mobifácil (C e I)', 'sociedade de crédito direto (C)', 'usina eólica (I); dezenas de imobiliárias (C); Gol (I)']),
       ('GE-011', 'NSO', ['', '', '11,4% do fundo da Autopass (I)', '', 'imobiliárias (C)']),
       ('GE-012', 'Auto Viação ABC', ['Eletra, ônibus elétricos (C e I)', '', '38,1% do fundo da Autopass (I)', '', '']),
       ('GE-014', 'Gulin (cinco códigos)', ['', '', 'Embarca (I)', '', 'cinco holdings de energia (C); Elejor, com a Copel (I); imóveis (I)']),
       ('GE-018', 'Carvalho / Mobi', ['', '', '', '', 'cerca de 12 sociedades de energia solar (C)']),
       ('GE-151', 'Santo André', ['', '', '', '', 'jornal Diário do Grande ABC (I)'])]
achados = ('  <div class="panel alem-achados"><h2>O que a tese encontrou fora do ônibus</h2><div class="ach">'
           + ''.join(f'<div><b>{t}</b><p>{x}</p></div>' for t, x in ACH) + '</div>'
           '<h3 class="h3c">Os negócios correlatos dos grupos, por setor</h3><div class="getabwrap q20wrap" style="max-height:none;"><table class="getab q20"><thead><tr><th>Grupo</th>'
           + ''.join(f'<th>{c}</th>' for c in Q20C) + '</tr></thead><tbody>'
           + ''.join(f'<tr><td><a href="#{g}" class="lk-rede" data-ge="{g}">{n}</a></td>' + ''.join(f'<td>{v or "<span class=muted>—</span>"}</td>' for v in vs) + '</tr>' for g, n, vs in Q20)
           + '</tbody></table></div><p class="legenda">C: vínculo de sócio ou de cargo no cadastro; I: imprensa ou documento público. Vínculo no cadastro não é controle unificado; o travessão indica que nada foi encontrado, e não ausência comprovada. As sociedades anônimas só registram administradores e ficam fora da rede: a forma que dá acesso ao mercado de capitais é a que o método não enxerga.</p>'
           '<p class="pmeta">Na tese: Seção 6.4, Figura 19 e Quadro 20.</p></div>\n')
i = s.index('<div class="panel cadeia-fixa" id="alem-cadeia">'); k = fim(i, 'div')
s = s[:k] + '\n' + achados + s[k:]
GRUPO = bloco('<details class="pacote" id="patGrupo" open>')
GRUPO = GRUPO.replace('<span class="pnum">2</span>', '<span class="pnum">1</span>', 1)
troca('<details class="pacote" id="alem-setores"><summary class="phead"><span class="pnum">1</span>', GRUPO + '\n\n  <details class="pacote" id="alem-setores"><summary class="phead"><span class="pnum">2</span>')

# ------------------------------------------------------------------ CSS
troca('</style>\n</head>', '''  /* ===== rede_etapa5 (13/11/2026) ===== */
  .mapa-zonas{margin:14px 0 16px;}
  .mz-ctl{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 10px;}
  .mz-ctl button{background:var(--panel2);border:1px solid var(--border);border-radius:999px;color:var(--text);font:inherit;font-size:12.5px;font-weight:700;padding:6px 14px;cursor:pointer;}
  .mz-ctl button.on{background:var(--amarelo);border-color:var(--amarelo);color:#0E0E10;}
  .mz-grid{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:18px;align-items:start;} @media (max-width:820px){ .mz-grid{grid-template-columns:1fr;} }
  .mz-mapa svg{width:100%;height:auto;display:block;background:var(--panel2);border-radius:10px;}
  .mz-mapa .ufb{fill:#17171d;stroke:#4a4a58;stroke-width:.8;} .mz-mapa circle{cursor:pointer;} .mz-mapa circle.sel{stroke:#fff;stroke-width:2;}
  #mzLeg .mz-l{display:grid;grid-template-columns:16px 1fr auto;gap:8px;align-items:center;padding:7px 0;border-bottom:1px solid var(--border);font-size:13px;}
  #mzLeg .mz-l i{width:12px;height:12px;border-radius:50%;display:block;} #mzLeg .mz-l b{font-size:18px;color:var(--amarelo);} #mzLeg .mz-l span small{display:block;color:var(--muted);font-size:11.5px;}
  .mz-info{margin-top:10px;background:var(--panel2);border:1px solid var(--border);border-radius:10px;padding:10px 12px;font-size:12.5px;min-height:40px;}
  .mz-info a{color:var(--rosa) !important;margin-right:12px;}
  p.explica{font-size:13.5px;line-height:1.6;color:var(--text);margin:8px 0 10px;max-width:920px;}
  .pbar{display:grid;gap:14px;margin:10px 0 8px;}
  .pb-lin{display:grid;grid-template-columns:minmax(0,260px) minmax(0,1fr);gap:16px;align-items:center;} @media (max-width:640px){ .pb-lin{grid-template-columns:1fr;gap:6px;} }
  .pb-rot b{display:block;font-size:14px;} .pb-rot span{font-size:11.5px;color:var(--muted);line-height:1.4;display:block;}
  .pb-b{display:grid;grid-template-columns:76px minmax(0,1fr) 46px;gap:8px;align-items:center;font-size:12px;margin:3px 0;} .pb-b span{color:var(--muted);}
  .pb-b i{display:block;height:16px;border-radius:3px;} .pb-b b{font-size:13.5px;color:var(--text);text-align:right;}
  ul.leitura81 li{margin:6px 0;line-height:1.55;font-size:13px;}
  details.mais > summary{cursor:pointer;font-weight:700;font-size:13px;margin:10px 0 6px;}
  h3.h3c{font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--amarelo);margin:18px 0 8px;}
  table.q32 td,table.q32 th{font-size:12.5px;vertical-align:top;}
  ol.linha-setor{list-style:none;margin:6px 0 10px;padding:0 0 0 14px;border-left:2px solid var(--amarelo);display:grid;gap:9px;}
  ol.linha-setor li b{display:block;font-size:12px;color:var(--amarelo);} ol.linha-setor li span{font-size:13px;line-height:1.5;}
  .t6{display:grid;gap:12px;margin:12px 0 8px;}
  .t6-lin{display:grid;grid-template-columns:minmax(0,280px) minmax(0,1fr);gap:14px;align-items:center;} @media (max-width:640px){ .t6-lin{grid-template-columns:1fr;gap:4px;} }
  .t6-rot b{display:block;font-size:13.5px;} .t6-rot span{font-size:11.5px;color:var(--muted);}
  .t6-bar{display:flex;height:26px;border-radius:4px;overflow:hidden;min-width:60px;} .t6-bar i{display:flex;align-items:center;justify-content:center;font-style:normal;font-size:11.5px;font-weight:800;color:#0E0E10;}
  .t6-leg{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:11.5px;color:var(--muted);} .t6-leg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px;}
  .do-cadastro{margin:0 0 14px;}
  ol.dc{list-style:none;margin:10px 0 6px;padding:0;display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:10px;}
  ol.dc li{background:var(--panel2);border:1px solid var(--border);border-radius:10px;padding:10px;display:flex;flex-direction:column;gap:6px;position:relative;}
  ol.dc li b{font-size:20px;color:var(--amarelo);line-height:1;} ol.dc li i{display:block;height:6px;background:var(--rosa);border-radius:3px;} ol.dc li span{font-size:11.5px;color:var(--muted);line-height:1.4;}
  ol.dc li:not(:last-child)::after{content:'→';position:absolute;right:-9px;top:12px;color:var(--muted);font-size:12px;}
  @media (max-width:1100px){ ol.dc{grid-template-columns:repeat(4,minmax(0,1fr));} } @media (max-width:640px){ ol.dc{grid-template-columns:repeat(2,minmax(0,1fr));} ol.dc li::after{display:none;} }
  #geFind{display:none !important;} #patFind{display:none !important;}
  .como-ler p{font-size:12.5px;line-height:1.55;margin:4px 0;color:var(--text);max-width:980px;} .como-ler a{color:var(--rosa) !important;}
  .filtro-rede label{text-transform:uppercase;font-size:11px;font-weight:800;letter-spacing:.06em;}
  .filtro-rede input::placeholder{text-transform:uppercase;font-size:11.5px;letter-spacing:.04em;}
  .filtro-rede .bt2{text-transform:uppercase;letter-spacing:.05em;}
  .funil-cap{margin:4px 0 16px;}
  .fc-bar{display:flex;height:42px;border-radius:6px;overflow:hidden;margin:8px 0 6px;}
  .fc-bar i{display:flex;align-items:center;justify-content:center;font-style:normal;font-size:12px;font-weight:800;color:#0E0E10;border-right:1px solid #0E0E10;white-space:nowrap;overflow:hidden;}
  .fc-rot{display:flex;font-size:11.5px;color:var(--muted);} .fc-rot span{overflow:hidden;padding-right:4px;line-height:1.35;}
  .fc-tam{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-top:12px;} @media (max-width:640px){ .fc-tam{grid-template-columns:repeat(2,minmax(0,1fr));} }
  .fc-tam div{background:var(--panel2);border:1px solid var(--border);border-radius:8px;padding:8px 10px;font-size:12px;color:var(--muted);} .fc-tam b{display:block;font-size:18px;color:var(--text);}
  .alem-achados{margin:14px 0;}
  .ach{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;} @media (max-width:820px){ .ach{grid-template-columns:1fr;} }
  .ach div{background:var(--panel2);border:1px solid var(--border);border-left:3px solid var(--rosa);border-radius:8px;padding:10px 12px;}
  .ach b{font-size:13.5px;} .ach p{font-size:12.5px;line-height:1.55;margin:4px 0 0;color:var(--text);}
  table.q20 td{font-size:12px;vertical-align:top;min-width:120px;} table.q20 td:first-child{min-width:110px;font-weight:700;} table.q20 a{color:var(--amarelo) !important;}
  #patFedChips.patctl{display:flex;flex-wrap:wrap;gap:10px 16px;margin:6px 0 10px;}
  #patFedChips select{max-width:min(420px,80vw);}
  .dica-zoom{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);background:rgba(14,14,16,.92);border:1px solid var(--amarelo);color:var(--text);font-size:13px;font-weight:700;padding:10px 14px;border-radius:10px;pointer-events:none;opacity:0;transition:opacity .2s;z-index:5;text-align:center;}
  .dica-zoom.on{opacity:1;}
  @media (pointer:coarse){ #redeSvg,#patSvg{touch-action:pan-y !important;} }
</style>
</head>''')

# ------------------------------------------------------------------ JS
s = s.replace('<meta name="proposta" content="rede_etapa4">\n</body>', r'''<script>
// rede_etapa5
// a roda do mouse rola a página; para aproximar, clique na rede (ou Ctrl + roda, ou os botões + e −)
(() => {
  for (const id of ['redeSvg', 'patSvg']) {
    const el = document.getElementById(id); if (!el) continue;
    const pai = el.parentElement; if (getComputedStyle(pai).position === 'static') pai.style.position = 'relative';
    const dica = document.createElement('div'); dica.className = 'dica-zoom'; dica.textContent = 'Para aproximar: clique na rede e use a roda, ou Ctrl + roda'; pai.appendChild(dica);
    let ativo = false, t = 0;
    el.addEventListener('pointerdown', () => { ativo = true; });
    el.addEventListener('pointerleave', () => { ativo = false; });
    pai.addEventListener('wheel', e => {
      if (!e.target.closest('#' + id) || ativo || e.ctrlKey || e.metaKey) return;
      e.stopPropagation(); dica.classList.add('on'); clearTimeout(t); t = setTimeout(() => dica.classList.remove('on'), 1300);
    }, { capture: true });
  }
})();
// GE × TZ: o mapa das zonas (Mapa 9)
(() => {
  const box = document.getElementById('mzMapa'); if (!box) return;
  const Z = JSON.parse(document.getElementById('data-zonas').textContent);
  const COR = ['#5b78b8', '#FF2D6B', '#F5E400'], RAIO = [2.3, 4.2, 3.6];
  const ROT = [['Grupo presente, sem a política', 'o que a tese chama de bloqueio aparente'], ['Tarifa Zero universal com grupo presente', 'permeabilidade'], ['Tarifa Zero universal sem grupo', 'nas franjas do setor']];
  const POSN = ['cidade isolada', 'satélite de arranjo', 'sede de arranjo'];
  let filtro = 'todos', sel = null;
  const desenhaZ = () => {
    const vis = Z.filter(z => filtro === 'todos' || z[5] > 0);
    const ord = [...vis].sort((a, b) => a[4] - b[4] || (a[4] === 0 ? 0 : 0));
    box.innerHTML = `<svg viewBox="-6 -6 600 604" role="img" aria-label="Mapa das zonas de presença de grupo e Tarifa Zero">${ARS.geo.ufs.map(d => `<path d="${d}" class="ufb"/>`).join('')}${ord.map(z => `<circle cx="${z[2]}" cy="${z[3]}" r="${RAIO[z[4]]}" fill="${COR[z[4]]}" fill-opacity="${z[4] ? .95 : .55}" data-c="${z[0]}"${z[0] === sel ? ' class="sel"' : ''}><title>${esc(z[1])}</title></circle>`).join('')}</svg>`;
    const n = [0, 0, 0]; vis.forEach(z => n[z[4]]++);
    document.getElementById('mzLeg').innerHTML = [1, 2, 0].map(k => `<div class="mz-l"><i style="background:${COR[k]}"></i><span>${ROT[k][0]}<small>${ROT[k][1]}</small></span><b>${fmt(n[k])}</b></div>`).join('');
  };
  box.addEventListener('click', e => {
    const c = e.target.closest('circle[data-c]'); if (!c) return; sel = c.dataset.c;
    const z = Z.find(z => z[0] === sel); desenhaZ();
    const temG = z[4] < 2;
    document.getElementById('mzInfo').innerHTML = `<b>${esc(z[1])}</b> · ${POSN[z[5]]}<br><span style="color:${COR[z[4]]}">●</span> ${ROT[z[4]][0]}<div style="margin-top:6px;">${z[4] > 0 ? `<a href="painel.html#mun-${z[0]}">ver no painel →</a>` : ''}${temG ? `<a href="#" class="mz-rede" data-c="${z[0]}">ver os grupos da cidade na rede →</a>` : ''}</div>`;
  });
  document.getElementById('mzInfo').addEventListener('click', e => {
    const a = e.target.closest('.mz-rede'); if (!a) return; e.preventDefault();
    const nome = ARS.mun[a.dataset.c]; if (!nome) return;
    abreAba('controle'); busca.value = nome; busca.dispatchEvent(new Event('input'));
    setTimeout(() => document.querySelector('.filtro-rede')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60);
  });
  document.querySelectorAll('.mz-ctl button').forEach(b => b.addEventListener('click', () => {
    document.querySelectorAll('.mz-ctl button').forEach(x => x.classList.toggle('on', x === b)); filtro = b.dataset.pos; desenhaZ(); }));
  desenhaZ();
})();
// links para as abas a partir do texto
document.addEventListener('click', e => { const a = e.target.closest('[data-ir-aba]'); if (!a) return; e.preventDefault(); abreAba(a.dataset.irAba); window.scrollTo({ top: document.querySelector('.tabs, [role=tablist]')?.offsetTop || 0, behavior: 'smooth' }); });
// Concentração: o funil do capital
(() => {
  const el = document.getElementById('funilCapital'); if (!el) return;
  const us = [...ARS.unidades].sort((a, b) => (b.capital || 0) - (a.capital || 0));
  const tot = us.reduce((t, u) => t + (u.capital || 0), 0);
  const ac = n => us.slice(0, n).reduce((t, u) => t + (u.capital || 0), 0) / tot * 100;
  const pc = v => v.toFixed(1).replace('.', ',') + '%';
  const cortes = [[1, 'a maior unidade'], [5, 'da 2ª à 5ª'], [10, 'da 6ª à 10ª'], [22, 'da 11ª à 22ª']];
  const cores = ['#F5E400', '#d9c900', '#b3a600', '#8c8200', '#3a3f4a'];
  let ant = 0, antN = 0; const seg = [];
  for (const [n, r] of cortes) { const v = ac(n); seg.push({ r, p: v - ant, acum: v, n: n - antN }); ant = v; antN = n; }
  seg.push({ r: `as outras ${us.length - 22}`, p: 100 - ant, acum: 100, n: us.length - 22 });
  const tam = [[u => u.n_emp === 1, 'com uma empresa'], [u => u.n_emp === 2, 'com duas'], [u => u.n_emp >= 3 && u.n_emp <= 9, 'de três a nove'], [u => u.n_emp >= 10, 'com dez ou mais']];
  el.innerHTML = `<h3 style="font-size:14px;margin:4px 0 2px;">O funil do capital</h3>
    <p class="explica" style="margin:2px 0 4px;">Os R$ ${(tot / 1e9).toFixed(2).replace('.', ',')} bilhões de capital social declarado, divididos entre as ${us.length} unidades de controle, da maior para a menor. <b>A maior detém ${pc(ac(1))}; as 5 maiores, ${pc(ac(5))}; as 10 maiores, ${pc(ac(10))}; as 22 maiores, ${pc(ac(22))}.</b> Uma em cada catorze unidades reúne metade do capital.</p>
    <div class="fc-bar">${seg.map((g, k) => `<i style="width:${g.p}%;background:${cores[k]};${k === 4 ? 'color:#e8e8ee;' : ''}" title="${g.r}: ${pc(g.p)}">${g.p > 6 ? pc(g.p) : ''}</i>`).join('')}</div>
    <div class="fc-rot">${seg.map(g => `<span style="width:${g.p}%">${g.r}${g.n > 1 && g.r.startsWith('da') ? ` (${g.n})` : ''}<br><b style="color:var(--text);">${pc(g.acum)}</b> acumulado</span>`).join('')}</div>
    <div class="fc-tam">${tam.map(([f, r]) => `<div><b>${us.filter(f).length}</b>unidades ${r}</div>`).join('')}</div>
    <p class="legenda" style="margin-top:8px;">Capital social é o registrado no cadastro: não equivale ao faturamento nem à frota, mas é a única medida de porte disponível para todas as unidades na mesma base. A Itapemirim, segunda pelo capital, está falida desde 2022.</p>`;
})();
// Além do ônibus: escolher por federação e por grupo, em listas
(() => {
  const box = document.getElementById('patFedChips'); if (!box || !window.PAT) return;
  const fedDe = new Map();
  ARS.federacoes.forEach(f => f.unidades.forEach(u => (UNI.get(u)?.membros || []).forEach(g => fedDe.set(g, f.id))));
  const gs = ARS.nos.filter(n => window.PAT.tem(n.id)).sort((a, b) => nomeG(a).localeCompare(nomeG(b), 'pt-BR'));
  const maior = f => { const ms = f.unidades.map(u => UNI.get(u)).filter(Boolean).sort((a, b) => (b.capital || 0) - (a.capital || 0)); return ms[0]?.nome || ''; };
  const feds = ARS.federacoes.filter(f => gs.some(n => fedDe.get(n.id) === f.id));
  box.className = 'patctl';
  box.innerHTML = `<label>Federação <select id="patFedSel"><option value="">todas</option>${feds.map(f => `<option value="${f.id}">${f.id} · ${esc(maior(f))} e outras ${f.unidades.length - 1} unidades</option>`).join('')}<option value="-">grupos sem federação</option></select></label>
    <label>Grupo <select id="patGrupoSel"></select></label>`;
  const fs = box.querySelector('#patFedSel'), gsel = box.querySelector('#patGrupoSel');
  const enche = () => {
    const f = fs.value;
    const lst = gs.filter(n => !f || (f === '-' ? !fedDe.has(n.id) : fedDe.get(n.id) === f));
    gsel.innerHTML = `<option value="">escolha (${lst.length})…</option>` + lst.map(n => `<option value="${n.id}">${esc(nomeG(n))}</option>`).join('');
  };
  fs.addEventListener('change', () => { enche(); if (gsel.options.length === 2) { gsel.selectedIndex = 1; window.PAT.mostra(gsel.value); } });
  gsel.addEventListener('change', () => { if (gsel.value) window.PAT.mostra(gsel.value); });
  enche();
})();
</script>
<meta name="proposta" content="rede_etapa5">
</body>''', 1)
assert 'rede_etapa5' in s
open(ARQ, 'w', encoding='utf-8').write(s)
print('etapa 5 da rede aplicada:', ARQ, len(s.encode()), 'bytes;', len(zon), 'municípios no mapa das zonas')
