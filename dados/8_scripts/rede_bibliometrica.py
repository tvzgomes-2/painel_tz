#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rede_bibliometrica.py — rede de citações e panorama do corpus da RSL.

Substitui o VOSviewer para o que a tese precisa: não há base Scopus/WoS com
cobertura do corpus (é o achado de Lightner et al., 2026), então a rede é
construída à mão a partir dos fichamentos, com cobertura declarada.

ENTRADAS  05 - Referências/Rede bibliométrica/corpus_rsl.csv
          05 - Referências/Rede bibliométrica/arestas_manuais.csv
          05 - Referências/Rede bibliométrica/citacoes_completas.csv (de extrair_referencias.py)
SAÍDAS    _attachments/rede_rsl_citacoes.svg     rede de citações internas
          _attachments/rsl_generos_por_ano.svg   gêneros por ano
          05 - Referências/Rede bibliométrica/Relatório da rede (gerado).md
          _attachments/rsl_cocitacao.svg

Layout determinístico (spring/Fruchterman-Reingold com semente fixa), cores
fixas em hex e fundo branco, conforme o padrão de figuras do cofre.

--- Reescrita de 16/09/2026 — o que mudou e por quê -------------------------
O autor reportou que "as visualizações das últimas estavam terríveis".
Investigação encontrou três defeitos, não só estética:

1) BUG DE DADOS (não só de cor): o dicionário de cores `COR` foi fixado com
   12 valores de `genero` numa fase anterior da pesquisa. O campo `genero`
   no corpus_rsl.csv de hoje já tem **29 valores distintos** (a classificação
   ficou mais fina ao longo da RSL). Consequência real, não cosmética:
   - na rede de citações, todo item com `genero` fora desses 12 virava
     cinza "a_confirmar" — parecendo não classificado, quando está;
   - no gráfico de gêneros por ano, esses itens eram **omitidos da
     contagem** (o filtro `for g in gens` só cobria as chaves de COR) —
     53 dos 183 itens do acervo (29%) não apareciam na coluna do seu ano,
     que ficava mais baixa que o total real, sem aviso.
   Correção: a REDE agora colore por `genero_suporte` — o vocabulário que o
   próprio cofre desenhou em 07/09/2026 exatamente para agregar o `genero`
   fino em categorias estáveis (ver `gsup()`, já existia, só não era usado
   para cor). Esse campo também cresceu (14 valores hoje, não os 8
   originais) — os 7 mais frequentes têm cor própria; o restante (6% do
   acervo: entrevista, livro avulso, documento_tecnico, reportagem, manual
   técnico, TCC) entra num 8º grupo "outros suportes", declarado no
   relatório, não escondido. O gráfico de gêneros por ano ganhou a mesma
   correção mínima (uma coluna "outros gêneros" visível, nada mais omitido);
   ele continua usando `genero` fino, que é o que a tabela precisa mostrar.

2) COR NÃO VALIDADA: a paleta antiga não passava no validador de
   acessibilidade (CVD) do skill de visualização do cofre — duas laranjas
   adjacentes (ensaio_intervencao/analise_conjuntura) tinham Delta E 4,4,
   abaixo do piso de 15 mesmo para visão normal (i.e., ilegíveis lado a
   lado até para quem enxerga cor normalmente). Trocado pela paleta
   categórica de 8 matizes validada do skill (ordem fixa, cada par
   adjacente ≥ 15 Delta E em visão normal).

3) LAYOUT: o spring layout antigo prendia todo nó sem aresta (isolado) no
   raio unitário (`if r>1: clamp`) — isso produzia o arco decorativo que
   varria metade do canvas na versão anterior, sem nenhuma informação nova.
   E não havia nenhum tratamento de colisão de rótulos — no núcleo denso da
   rede (onde estão os itens mais citados), os nomes se sobrepunham a ponto
   de ficarem ilegíveis.
   Correção: (a) isolados saem do layout de forças e vão para um painel
   compacto em grade, separado e identificado, em vez de dominar o canvas;
   (b) o layout dos conectados usa gravidade suave ao centro em vez de
   clamp radial — sem anel artificial; (c) rótulos tentam 8 posições ao
   redor do nó e, se nenhuma está livre, são suprimidos com aviso explícito
   no rodapé da figura (nunca sobrepostos silenciosamente) — o id sempre
   permanece legível dentro do nó, e a lista completa está no relatório.
------------------------------------------------------------------------------

--- Reescrita de 17/09/2026 — restrição à população do corpus (81 itens) ----
Instrução do autor: "vamos refazer baseado exclusivamente nos 81 do corpus
selecionado". Até aqui as três figuras eram calculadas sobre TODO o acervo
lido (183 itens, sem filtro de `estado`/`estrato`) — não sobre os 81 itens
que efetivamente compõem o corpus da revisão (RSL1-4, `estado=fichado`; ver
"RSL — fechamento (16-09-2026)"). Não era só rótulo: a figura de citações
internas e a de co-citação incluíam, sem aviso, itens do acervo mais amplo
(fonte documental, sem estrato, e mesmo os 59 excluídos após leitura) como
se fossem corpus.

Efeito real de restringir a população a 81 (medido antes de aplicar, não
suposto): das 178 arestas `interno` do acervo, só 25 têm as DUAS pontas
dentro dos 81 — as outras 93 saem porque um dos lados é um item fora do
corpus estrito, e 60 nem citam nem são citadas por item algum do corpus.
Na co-citação, dos 88 itens do acervo com referências extraídas, 55
pertencem ao corpus dos 81. **A rede de citações internas fica bem mais
esparsa — é o retrato correto da população pedida, não um defeito da
figura.** Ver "Relatório da rede (gerado).md" para os números completos.

`filtra_corpus81()` é o único ponto de filtro: `estrato in {RSL1..RSL4} AND
estado==fichado`. Não usar `estrato` isolado — id117 (Marinho, 2023) mantém
`estrato=RSL1` no CSV mas foi reclassificado para `excluido_apos_leitura`
em 16/09/2026, e por isso fica fora do corpus dos 81 apesar do campo.

Títulos deixaram de ser desenhados dentro do SVG (ficam só na legenda em
markdown ao redor do embed, padrão ABNT já usado no resto do cofre) — o
design system de figuras (doc do projeto, 16/09/2026) veda título e "Fonte"
embutidos na imagem. A paleta de cor (`PALETA8`, 8 matizes, validada em
16/09/2026 para as figuras desta rede) NÃO foi trocada pela paleta
categórica de 4 cores do mesmo design system — são dois sistemas
"validados" no mesmo dia que não conversam entre si, e esta rede tem 7-8
categorias de suporte que não cabem no teto de 4; forçar o encaixe
apagaria distinções que a figura existe para mostrar. Sinalizado ao autor
para decisão, não resolvido em silêncio (ver relatório do agente).
------------------------------------------------------------------------------
"""
import csv, math, os, random, collections

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR  = os.path.join(RAIZ, "05 - Referências", "Rede bibliométrica")
ATT  = os.path.join(RAIZ, "_attachments")
TXT  = os.path.join(RAIZ, "_meta", "textos_rsl")

def com_texto():
    """ids cujo texto foi extraído — é a base real das arestas.
    ⚠️ 'estado=fichado' NÃO serve como proxy: um item pode estar fichado e sem
    texto extraído, e nesse caso nenhuma aresta pode partir dele."""
    if not os.path.isdir(TXT): return set()
    return {f[:-4] for f in os.listdir(TXT) if f.endswith(".txt")}

# Paleta categórica validada (skill de dataviz do cofre, 8 matizes, ordem
# fixa — a ordem é o mecanismo de segurança para daltonismo, não é estético;
# não reordenar). Checagem: node scripts/validate_palette.js "<hex,...>"
# --mode light → todos os 6 testes passam em pares adjacentes.
PALETA8 = [
    ("#2a78d6", "#184f95"),  # 1 azul
    ("#eb6834", "#a8441c"),  # 2 laranja
    ("#1baf7a", "#0e6d4c"),  # 3 água
    ("#eda100", "#a86f00"),  # 4 amarelo
    ("#e87ba4", "#a84d70"),  # 5 magenta
    ("#008300", "#0b4a0b"),  # 6 verde
    ("#4a3aa7", "#2c2266"),  # 7 violeta
    ("#e34948", "#a13030"),  # 8 vermelho
]
CINZA = ("#b7b6ae", "#7c7b74")  # fora da paleta categórica — reservado p/ "outros"

# genero_suporte -> cor, por frequência no corpus (16/09/2026). Valores fora
# dos 7 mais frequentes caem no grupo "outros suportes" (cinza, listado no
# relatório, não escondido — ver nota de reescrita no topo do arquivo).
SUPORTE_TOPO = [
    "artigo_periodico", "tese_dissertacao", "comunicacao_congresso",
    "apresentacao_slides", "relatorio_tecnico", "livro_capitulo",
    "documento_institucional",
]
SUPORTE_ALIAS = {"capitulo_livro": "livro_capitulo"}  # variante de grafia, só para exibição
ROT_SUPORTE = {
    "artigo_periodico": "artigo em periódico", "tese_dissertacao": "tese ou dissertação",
    "comunicacao_congresso": "comunicação em congresso", "apresentacao_slides": "apresentação/slides",
    "relatorio_tecnico": "relatório ou estudo técnico", "livro_capitulo": "livro ou capítulo",
    "documento_institucional": "documento institucional", "outros_suportes": "outros suportes*",
}
def cor_suporte(s):
    s = SUPORTE_ALIAS.get(s, s)
    if s in SUPORTE_TOPO:
        return PALETA8[SUPORTE_TOPO.index(s)]
    return CINZA

def gsup(n):
    """suporte do item — usa o vocabulário controlado quando existir, senão cai no gênero fino."""
    return (n.get("genero_suporte") or "").strip() or n.get("genero", "a_confirmar")

# `genero` fino (29 valores em 16/09/2026) — usado só no gráfico de gêneros
# por ano, que existe justamente para mostrar essa granularidade. As 8 mais
# frequentes têm cor própria; o resto entra em "outros gêneros" (visível,
# nunca omitido — era esse o bug real da versão anterior).
GENERO_TOPO = [
    "pesquisa_academica", "comunicacao_congresso", "artigo_academico",
    "ensaio_teorico", "artigo_tecnico_setorial", "relato_de_gestao",
    "livro", "revisao_de_literatura",
]
ROT_GENERO = {
    "pesquisa_academica": "pesquisa acadêmica (dado primário)", "comunicacao_congresso": "comunicação em congresso",
    "artigo_academico": "artigo em periódico", "ensaio_teorico": "ensaio teórico",
    "artigo_tecnico_setorial": "artigo técnico-setorial", "relato_de_gestao": "relato de gestão",
    "livro": "livro", "revisao_de_literatura": "revisão de literatura",
    "outros_generos": "outros gêneros*",
}
def cor_genero(g):
    if g in GENERO_TOPO:
        return PALETA8[GENERO_TOPO.index(g)]
    return CINZA

def esc(s): return (str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))

def ler():
    with open(os.path.join(DIR,"corpus_rsl.csv"), encoding="utf-8-sig") as f:
        nos={r["id"]:r for r in csv.DictReader(f,delimiter=";")}
    with open(os.path.join(DIR,"arestas_manuais.csv"), encoding="utf-8-sig") as f:
        ar=[r for r in csv.DictReader(f,delimiter=";")]
    return nos,ar

ESTRATOS_CORPUS = {"RSL1", "RSL2", "RSL3", "RSL4"}

def filtra_corpus81(nos):
    """Restringe ao corpus estrito da RSL (81 itens, 17/09/2026): estrato em
    RSL1-4 E estado=fichado. Não usar `estrato` isolado (ver nota no topo
    do arquivo sobre id117/Marinho 2023, que mantém estrato=RSL1 mas foi
    reclassificado para excluido_apos_leitura)."""
    return {i: r for i, r in nos.items()
            if r.get("estrato") in ESTRATOS_CORPUS and r["estado"] == "fichado"}

# ---------------------------------------------- caso concreto x teórico ---
# 17/09/2026 (a pedido do autor): Figuras A1 e A2 do Anexo recategorizadas —
# de gênero textual/suporte bibliográfico para "cita caso(s) concreto(s)" x
# "teórico/conceitual", eixo mais direto para o argumento do capítulo.
#
# Critério: 52 dos 81 itens já tinham `tipo_de_alegacao` preenchido no
# fichamento — usa-se esse campo direto (mapeamento abaixo). Os outros 29
# (36% do corpus) têm tipo_de_alegacao="a_confirmar" (nunca foi preenchido);
# para esses, `_RESOLVE_A_CONFIRMAR` é uma LEITURA MANUAL feita por Claude
# em 17/09/2026 a partir do título e do `escopo` de cada item — NÃO é um
# campo do fichamento nem um algoritmo genérico, é julgamento item a item,
# incluído aqui só para não excluir 36% do corpus das duas figuras.
# A REVISAR PELO AUTOR — em especial os itens 28, 74 e 82 (motivo de cada
# um no dicionário; são os mais discutíveis do lote). Um item que caia em
# "a_confirmar" no futuro sem entrada aqui dispara aviso no console em vez
# de ser classificado às cegas (ver fallback ao fim de classifica_caso).
# 18/09/2026: itens 7, 67, 84, 86 e 92 saíram deste dicionário — leitura
# completa dos fichamentos (resolução do grupo P do Anexo RSL, ver
# "RSL — contribuição empírica vs. teórico-retórico") já fixou o
# `tipo_de_alegacao` de cada um no corpus_rsl.csv (revisao_de_literatura,
# ensaio_teorico, normativo_juridico, posicionamento e ensaio_teorico,
# respectivamente) — não dependem mais de leitura manual aqui.
# 18/09/2026 (2a rodada): item 81 tambem saiu — mesma leitura completa,
# tipo_de_alegacao fixado como ensaio_teorico no corpus_rsl.csv (o
# fichamento e explicito: "nao ha dado empirico proprio... e doutrina
# mais raciocinio tecnico"). Itens 55, 75 e 76 nao estavam neste
# dicionario (ja tinham tipo_de_alegacao preenchido, so que impreciso:
# eram doutrina/posicionamento classificados como normativo_juridico ou
# dado_primario, generos que este script bucketiza como empirico por
# padrao) -- corrigidos para posicionamento direto no CSV, mesmo termo
# que o proprio fichamento de Reale (id75) ja usava. Item 115 tambem
# corrigido no CSV (revisao_de_literatura -> analise_secundaria: a
# dissertacao nao so sintetiza literatura, verifica e cruza dado de
# terceiros -- Vermander e planilha Santini -- com contagem propria).
CASO_EMPIRICO = {"dado_primario","dado_secundario","analise_secundaria",
                  "estudo_de_caso","empirico_historico","normativo_juridico",
                  "proposta_de_politica"}
CASO_TEORICO  = {"ensaio_teorico","posicionamento","revisao_de_literatura",
                  "proposta_metodologica"}
_RESOLVE_A_CONFIRMAR = {
    "14":  ("empirico", "caso unico: Mariana/MG"),
    "18":  ("empirico", "efeitos da pandemia com dados de SP"),
    "27":  ("empirico", "caso unico: Sao Caetano do Sul/SP"),
    "28":  ("empirico", "analise multifatorial entre municipios reais na faixa 20-500 mil hab. -- a revisar"),
    "29":  ("empirico", "escopo_n_casos=19"),
    "30":  ("empirico", "escopo_n_casos=106"),
    "38":  ("empirico", "escopo_n_casos=117"),
    "39":  ("empirico", "pesquisa de atitude da populacao do DF"),
    "40":  ("empirico", "escopo_n_casos=44"),
    "41":  ("empirico", "caso unico: Belo Horizonte/MG, camada 4"),
    "68":  ("empirico", "relatorio tecnico sobre gratuidade na RMSP e municipios de SP"),
    "74":  ("empirico", "dados reais de RMSP/RMBS/RMC, 2004-2005"),
    "82":  ("empirico", "5 municipios nomeados: BH, Agudos, Marica, Porto Real, Monte Carmelo -- a revisar"),
    "83":  ("empirico", "caso unico: Sao Paulo/SP, viabilidade orcamentaria"),
    "85":  ("empirico", "caso unico: Sao Paulo/SP, TZ aos domingos"),
    "87":  ("empirico", "caso unico: Sistema BRT em Maceio/AL"),
    "89":  ("empirico", "caso unico: Montes Claros/MG"),
    "90":  ("empirico", "caso unico: Queimados/RJ"),
    "91":  ("empirico", "caso unico: Maceio/AL"),
    "93":  ("empirico", "serie historica 1998-2024 de Belo Horizonte/MG"),
    "94":  ("empirico", "7 organizacoes ativistas em BH e RM, estudo empirico"),
    "112": ("empirico", "atualizacao do item 83, mesmo caso (Sao Paulo/SP)"),
    "118": ("empirico", "estudo econometrico (DiD) com 82-297 municipios e dados do TSE"),
}

def classifica_caso(r):
    """Retorna 'empirico' ou 'teorico' -- ver nota de codificação acima."""
    t=(r.get("tipo_de_alegacao") or "").strip()
    if t in CASO_TEORICO: return "teorico"
    if t in CASO_EMPIRICO: return "empirico"
    over=_RESOLVE_A_CONFIRMAR.get(r.get("id"))
    if over: return over[0]
    print(f"AVISO: id {r.get('id')} sem tipo_de_alegacao e sem leitura manual em _RESOLVE_A_CONFIRMAR -- caiu em 'teorico' por padrao, precisa de revisao")
    return "teorico"

# Paleta do Design System das Figuras (Project "obsidian - doutorado",
# claude/design-system-figuras-2026-09-16): #FF2D6B / #1A54C7 / #326F00 /
# #BAAD00, ordem fixa, validada contra daltonismo (deltaE>=8) e contraste
# (>=3:1 em 3 de 4). Só 2 categorias aqui -> usa os dois primeiros slots
# (rosa, azul) no hex original, sem precisar dos tons escurecidos de
# verde/amarelo. Contorno escurecido a partir do mesmo matiz (fator 0,62),
# no mesmo padrão das tuplas (fill, stroke) do restante do script.
COR_CASO = {"empirico": ("#FF2D6B","#9E1B42"), "teorico": ("#1A54C7","#10347B")}
ROT_CASO = {"empirico": "cita caso(s) concreto(s)", "teorico": "teórico / conceitual"}

# ---------------------------------------------------------------- layout ---
def layout_forcas(ids, edges, it=900, seed=42, k_mult=1.0):
    """Fruchterman-Reingold com gravidade suave ao centro (não clamp radial —
    isso é o que produzia o anel decorativo de nós isolados na versão
    anterior). Só deve receber nós com grau > 0; isolados têm painel próprio."""
    n=len(ids)
    if n==0: return {}
    if n==1: return {ids[0]: (0.0,0.0)}
    random.seed(seed)
    idx={k:i for i,k in enumerate(ids)}
    pos=[(random.uniform(-0.4,0.4), random.uniform(-0.4,0.4)) for _ in range(n)]
    k=k_mult*1.55/math.sqrt(n)
    E=[(idx[a],idx[b]) for a,b in edges if a in idx and b in idx]
    gravidade=0.05  # 🩹 16/09/2026: 0.02 deixava sub-componentes pequenos (ex. um par
    # isolado do resto) derivarem para longe do núcleo, esvaziando o centro do canvas.
    for step in range(it):
        t=0.12*(1-step/it)+0.004
        dx=[0.0]*n; dy=[0.0]*n
        for i in range(n):
            for j in range(i+1,n):
                ax,ay=pos[i]; bx,by=pos[j]; ex,ey=ax-bx,ay-by
                d=math.hypot(ex,ey) or 1e-4; f=(k*k)/d
                dx[i]+=ex/d*f; dy[i]+=ey/d*f; dx[j]-=ex/d*f; dy[j]-=ey/d*f
        for a,b in E:
            ax,ay=pos[a]; bx,by=pos[b]; ex,ey=ax-bx,ay-by
            d=math.hypot(ex,ey) or 1e-4; f=(d*d)/k
            dx[a]-=ex/d*f; dy[a]-=ey/d*f; dx[b]+=ex/d*f; dy[b]+=ey/d*f
        for i in range(n):
            x,y=pos[i]; dx[i]-=x*gravidade; dy[i]-=y*gravidade
        for i in range(n):
            m=math.hypot(dx[i],dy[i]) or 1e-9; s=min(m,t)/m
            pos[i]=(pos[i][0]+dx[i]*s, pos[i][1]+dy[i]*s)
    return {k:pos[idx[k]] for k in ids}

def normalizar(pos_dict, margem=0.06):
    """Reenquadra pela caixa delimitadora real (em vez de raio unitário fixo)
    — usa o canvas inteiro por igual, seja a rede espalhada ou compacta.
    🩹 16/09/2026: winsoriza outliers (um par/trio pequeno de nós que a física
    empurrou longe do núcleo) para não esvaziar o canvas com espaço morto —
    o nó fica perto da borda, não desaparece, só não define mais a escala."""
    if not pos_dict: return pos_dict, (-1,1,-1,1)
    ks=list(pos_dict.keys())
    xs=[pos_dict[k][0] for k in ks]; ys=[pos_dict[k][1] for k in ks]
    n=len(ks)
    if n>=6:
        cx=sum(xs)/n; cy=sum(ys)/n
        dists=sorted(math.hypot(x-cx,y-cy) for x,y in zip(xs,ys))
        mediana=dists[n//2]
        # 🩹 mediana, não p90: com poucos nós (~40-90) um par/trio isolado já é
        # >5% da amostra e infla o próprio p90, deixando de funcionar como teto.
        cap=max(mediana*1.5, 1e-6)
        for k in ks:
            x,y=pos_dict[k]; ex,ey=x-cx,y-cy; d=math.hypot(ex,ey)
            if d>cap:
                s=cap/d
                pos_dict[k]=(cx+ex*s, cy+ey*s)
        xs=[pos_dict[k][0] for k in ks]; ys=[pos_dict[k][1] for k in ks]
    minx,maxx=min(xs),max(xs); miny,maxy=min(ys),max(ys)
    if maxx-minx<1e-6: minx-=0.5; maxx+=0.5
    if maxy-miny<1e-6: miny-=0.5; maxy+=0.5
    padx=(maxx-minx)*margem; pady=(maxy-miny)*margem
    minx-=padx; maxx+=padx; miny-=pady; maxy+=pady
    return pos_dict, (minx,maxx,miny,maxy)

def resolve_sobreposicoes(P, raios, ids, it=300, pad=4.0):
    """17/09/2026 (a pedido do autor: "este agrupamento ainda esta ruim,
    dificulta a leitura") — layout_forcas() espaça os nós pela física de
    Fruchterman-Reingold, que ignora o raio de desenho de cada círculo; um
    par ou trio pouco conectado (poucas arestas no grafo) pode ficar perto
    o bastante no layout para os círculos se sobreporem de verdade no SVG.
    Esta função roda DEPOIS da normalização, em espaço de pixel — separa
    par a par qualquer círculo que esteja mais perto do que a soma dos dois
    raios + uma margem, empurrando os dois para longe um do outro. Não mexe
    em nós que já não se tocam, então a topologia geral do layout de forças
    é preservada; só remove a sobreposição literal do desenho."""
    pos = {i: list(P[i]) for i in ids}
    n = len(ids)
    for _ in range(it):
        moveu = False
        for a_i in range(n):
            a = ids[a_i]
            ax, ay = pos[a]
            for b_i in range(a_i+1, n):
                b = ids[b_i]
                bx, by = pos[b]
                dx, dy = bx-ax, by-ay
                d = math.hypot(dx, dy) or 1e-6
                minimo = raios[a] + raios[b] + pad
                if d < minimo:
                    moveu = True
                    push = (minimo - d) / 2
                    ux, uy = dx/d, dy/d
                    pos[a][0] -= ux*push; pos[a][1] -= uy*push
                    pos[b][0] += ux*push; pos[b][1] += uy*push
                    ax, ay = pos[a]
        if not moveu:
            break
    return {i: (pos[i][0], pos[i][1]) for i in ids}

# ------------------------------------------------------- rótulos (colisão) --
def _bbox(cx, cy, texto, fs, anchor):
    w=0.56*fs*len(texto); h=fs*1.12
    if anchor=="middle": x0=cx-w/2
    elif anchor=="start": x0=cx
    else: x0=cx-w
    return (x0, cy-h, x0+w, cy+3)

def _sobrepoe(a,b):
    return not (a[2]<b[0] or b[2]<a[0] or a[3]<b[1] or b[3]<a[1])

def posiciona_rotulo(x, y, r, texto, fs, ocupados):
    """Tenta 8 posições ao redor do nó; se nenhuma está livre, tenta fonte
    menor na posição padrão (acima); se ainda colide, suprime (retorna None)
    em vez de desenhar por cima de outro rótulo."""
    cands=[
        (x, y-r-6, "middle"), (x, y+r+13, "middle"),
        (x+r+7, y+3.5, "start"), (x-r-7, y+3.5, "end"),
        (x+r*0.72, y-r-6, "start"), (x-r*0.72, y-r-6, "end"),
        (x+r*0.72, y+r+13, "start"), (x-r*0.72, y+r+13, "end"),
    ]
    for lx,ly,anchor in cands:
        bb=_bbox(lx,ly,texto,fs,anchor)
        if not any(_sobrepoe(bb,o) for o in ocupados):
            ocupados.append(bb)
            return (lx,ly,anchor,fs)
    fs2=fs-1.5
    lx,ly,anchor=x,y-r-6,"middle"
    bb=_bbox(lx,ly,texto,fs2,anchor)
    if not any(_sobrepoe(bb,o) for o in ocupados):
        ocupados.append(bb)
        return (lx,ly,anchor,fs2)
    return None

# ------------------------------------------------------------- figura 1 ----
def svg_rede(nos,ar,path):
    TIPOS_OK={"interno","externo","externo_recorrente","externo_para_interno"}
    _maus=sorted({r["tipo"] for r in ar if r["tipo"] not in TIPOS_OK})
    if _maus:
        print("AVISO: tipos desconhecidos em arestas_manuais.csv (ignorados):", ", ".join(_maus))
    internas=[(r["origem"],r["destino"]) for r in ar if r["tipo"]=="interno"]
    grau=collections.Counter()
    for a,b in internas: grau[a]+=1; grau[b]+=1
    todos=sorted(nos.keys(),key=int)
    conectados=[i for i in todos if grau[i]>0]
    isolados=[i for i in todos if grau[i]==0]

    W,M = 1760, 130
    por_linha_iso = 34
    linhas_iso = max(1, -(-len(isolados)//por_linha_iso)) if isolados else 0
    painel_h = 70 + linhas_iso*40 if isolados else 0  # cabeçalho + grade — reservado ANTES do layout
    H = 1100
    # 17/09/2026: sem cabeçalho de texto embutido (Design System das Figuras
    # — título e metodologia vão na legenda ABNT do corpo do texto, não na
    # imagem). Cor do nó trocada de suporte/gênero para classifica_caso().
    topo_rede, base_rede = 50, H - (painel_h + 90 if isolados else 90)  # 90 = legenda+rodapé
    pos_raw=layout_forcas(conectados, internas, it=1100, seed=42)
    pos_raw,(minx,maxx,miny,maxy)=normalizar(pos_raw)
    def T(p):
        x=M+(p[0]-minx)/(maxx-minx)*(W-2*M)
        y=topo_rede+(1-(p[1]-miny)/(maxy-miny))*(base_rede-topo_rede)
        return (x,y)
    P={i:T(pos_raw[i]) for i in conectados}
    raios={i:9+2.6*grau[i] for i in conectados}
    if conectados:
        P=resolve_sobreposicoes(P, raios, conectados)

    o=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
       '<style>text{font-family:Aptos,Calibri,Helvetica,Arial,sans-serif}</style>',
       '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#9a9a9a"/></marker></defs>']

    for a,b in internas:
        if a not in P or b not in P: continue
        (x1,y1),(x2,y2)=P[a],P[b]
        o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#a9a9a9" stroke-width="1.5" marker-end="url(#a)" opacity="0.65"/>')

    ocupados=[]  # bboxes de rótulos já colocados (evasão de colisão)
    suprimidos=[]
    ordem = sorted(conectados, key=lambda i: (-grau[i], int(i)))  # hubs primeiro: ganham a melhor posição
    for i in ordem:
        x,y=P[i]; r=raios[i]
        ocupados.append((x-r,y-r,x+r,y+r))  # o próprio nó também bloqueia posições de rótulo
    for i in ordem:
        x,y=P[i]; r=raios[i]
        nome=nos[i]["autores"].split(";")[0].strip('" ')[:24]
        texto=f'{esc(nome)} {nos[i]["ano"]}'
        res=posiciona_rotulo(x,y,r,texto,10.5,ocupados)
        if res is None: suprimidos.append(i)

    # nós (depois dos cálculos de rótulo, mas desenhados agora — rótulos usam coordenadas já resolvidas)
    ocupados2=[]
    for i in ordem:
        x,y=P[i]; r=raios[i]; ocupados2.append((x-r,y-r,x+r,y+r))
    for i in ordem:
        x,y=P[i]; r=raios[i]
        f,s=COR_CASO[classifica_caso(nos[i])]
        dash=' stroke-dasharray="3,2"' if nos[i]["estado"]=="a_receber" else ''
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{f}" stroke="{s}" stroke-width="2"{dash}/>')
        o.append(f'<text x="{x:.1f}" y="{y+4:.1f}" font-size="11" font-weight="700" text-anchor="middle" fill="#ffffff">{i}</text>')
    ocupados3=list(ocupados2)
    for i in ordem:
        if i in suprimidos: continue
        x,y=P[i]; r=raios[i]
        nome=nos[i]["autores"].split(";")[0].strip('" ')[:24]
        texto=f'{esc(nome)} {nos[i]["ano"]}'
        res=posiciona_rotulo(x,y,r,texto,10.5,ocupados3)
        if res:
            lx,ly,anchor,fs=res
            o.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="{fs}" text-anchor="{anchor}" fill="#222222">{texto}</text>')
        else:
            suprimidos.append(i)

    # ---- painel de isolados: grade compacta, separada, sem disputar espaço com a rede ----
    py0 = base_rede + 44  # logo abaixo da área reservada à rede — nunca sobrepõe
    if isolados:
        o.append(f'<line x1="{M}" y1="{py0-14}" x2="{W-M+50}" y2="{py0-14}" stroke="#dddddd" stroke-width="1"/>')
        o.append(f'<text x="{M}" y="{py0+6}" font-size="13" font-weight="700" fill="#333333">Sem citação interna registrada ({len(isolados)} itens) — não citam nem são citados por outro item do corpus</text>')
    cx0, cy0, passo, por_linha = M, py0+38, 40, por_linha_iso
    for k,i in enumerate(isolados):
        row,col = divmod(k, por_linha)
        x = cx0 + col*passo; y = cy0 + row*passo
        f,s=COR_CASO[classifica_caso(nos[i])]
        dash=' stroke-dasharray="2,2"' if nos[i]["estado"]=="a_receber" else ''
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="{f}" stroke="{s}" stroke-width="1.6"{dash}/>')
        o.append(f'<text x="{x:.1f}" y="{y+3.5:.1f}" font-size="9" font-weight="700" text-anchor="middle" fill="#ffffff">{i}</text>')

    ly=H-58; lx=M
    o.append(f'<text x="{lx}" y="{ly-16}" font-size="11.5" font-weight="700" fill="#333333">cor do nó</text>')
    for g in ("empirico","teorico"):
        f,s = COR_CASO[g]
        rot = ROT_CASO[g]
        o.append(f'<circle cx="{lx+6}" cy="{ly}" r="6" fill="{f}" stroke="{s}" stroke-width="1.5"/>')
        o.append(f'<text x="{lx+17}" y="{ly+4}" font-size="10.5" fill="#333333">{esc(rot)}</text>')
        lx+=len(rot)*5.9+34
        if lx>W-260: lx=M; ly+=20
    rodape = "Borda tracejada = item ainda não lido."
    if suprimidos:
        rodape += f" {len(suprimidos)} rótulo(s) suprimido(s) por densidade (id sempre visível no nó; nome completo no relatório): " + ", ".join(sorted(suprimidos,key=int))
    o.append(f'<text x="{M}" y="{H-14}" font-size="10" fill="#777777">*classificação por `tipo_de_alegacao`; 29 dos 81 itens (36%) sem esse campo preenchido foram lidos manualmente pelo escopo do item — a revisar, ver Relatório da rede (gerado). {esc(rodape)}</text>')
    o.append('</svg>')
    open(path,"w",encoding="utf-8", newline="\n").write("\n".join(o))
    return internas,grau,suprimidos

def svg_rede_suporte(nos,ar,path):
    """18/09/2026 (a pedido do autor: "as versoes anteriores, com a
    classificacao por tipo podem ir para o anexo") -- figura complementar a
    A1, mesma rede e mesmo layout (com resolve_sobreposicoes), mas cor do no
    pelo suporte documental (genero_suporte / cor_suporte / SUPORTE_TOPO),
    a classificacao original antes da troca para caso concreto x teorico.
    Sem cabecalho de texto embutido no SVG (Design System das Figuras)."""
    TIPOS_OK={"interno","externo","externo_recorrente","externo_para_interno"}
    internas=[(r["origem"],r["destino"]) for r in ar if r["tipo"]=="interno"]
    grau=collections.Counter()
    for a,b in internas: grau[a]+=1; grau[b]+=1
    todos=sorted(nos.keys(),key=int)
    conectados=[i for i in todos if grau[i]>0]
    isolados=[i for i in todos if grau[i]==0]

    W,M = 1760, 130
    por_linha_iso = 34
    linhas_iso = max(1, -(-len(isolados)//por_linha_iso)) if isolados else 0
    painel_h = 70 + linhas_iso*40 if isolados else 0
    H = 1100
    topo_rede, base_rede = 50, H - (painel_h + 110 if isolados else 110)  # +20 vs A1: legenda de 8 categorias quebra em mais linhas
    pos_raw=layout_forcas(conectados, internas, it=1100, seed=42)
    pos_raw,(minx,maxx,miny,maxy)=normalizar(pos_raw)
    def T(p):
        x=M+(p[0]-minx)/(maxx-minx)*(W-2*M)
        y=topo_rede+(1-(p[1]-miny)/(maxy-miny))*(base_rede-topo_rede)
        return (x,y)
    P={i:T(pos_raw[i]) for i in conectados}
    raios={i:9+2.6*grau[i] for i in conectados}
    if conectados:
        P=resolve_sobreposicoes(P, raios, conectados)

    o=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
       '<style>text{font-family:Aptos,Calibri,Helvetica,Arial,sans-serif}</style>',
       '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#9a9a9a"/></marker></defs>']

    for a,b in internas:
        if a not in P or b not in P: continue
        (x1,y1),(x2,y2)=P[a],P[b]
        o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#a9a9a9" stroke-width="1.5" marker-end="url(#a)" opacity="0.65"/>')

    ocupados=[]
    suprimidos=[]
    ordem = sorted(conectados, key=lambda i: (-grau[i], int(i)))
    for i in ordem:
        x,y=P[i]; r=raios[i]
        ocupados.append((x-r,y-r,x+r,y+r))
    for i in ordem:
        x,y=P[i]; r=raios[i]
        nome=nos[i]["autores"].split(";")[0].strip('" ')[:24]
        texto=f'{esc(nome)} {nos[i]["ano"]}'
        res=posiciona_rotulo(x,y,r,texto,10.5,ocupados)
        if res is None: suprimidos.append(i)

    ocupados2=[]
    for i in ordem:
        x,y=P[i]; r=raios[i]; ocupados2.append((x-r,y-r,x+r,y+r))
    for i in ordem:
        x,y=P[i]; r=raios[i]
        f,s=cor_suporte(gsup(nos[i]))
        dash=' stroke-dasharray="3,2"' if nos[i]["estado"]=="a_receber" else ''
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{f}" stroke="{s}" stroke-width="2"{dash}/>')
        o.append(f'<text x="{x:.1f}" y="{y+4:.1f}" font-size="11" font-weight="700" text-anchor="middle" fill="#ffffff">{i}</text>')
    ocupados3=list(ocupados2)
    for i in ordem:
        if i in suprimidos: continue
        x,y=P[i]; r=raios[i]
        nome=nos[i]["autores"].split(";")[0].strip('" ')[:24]
        texto=f'{esc(nome)} {nos[i]["ano"]}'
        res=posiciona_rotulo(x,y,r,texto,10.5,ocupados3)
        if res:
            lx,ly,anchor,fs=res
            o.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="{fs}" text-anchor="{anchor}" fill="#222222">{texto}</text>')
        else:
            suprimidos.append(i)

    py0 = base_rede + 44
    if isolados:
        o.append(f'<line x1="{M}" y1="{py0-14}" x2="{W-M+50}" y2="{py0-14}" stroke="#dddddd" stroke-width="1"/>')
        o.append(f'<text x="{M}" y="{py0+6}" font-size="13" font-weight="700" fill="#333333">Sem citação interna registrada ({len(isolados)} itens) — não citam nem são citados por outro item do corpus</text>')
    cx0, cy0, passo, por_linha = M, py0+38, 40, por_linha_iso
    for k,i in enumerate(isolados):
        row,col = divmod(k, por_linha)
        x = cx0 + col*passo; y = cy0 + row*passo
        f,s=cor_suporte(gsup(nos[i]))
        dash=' stroke-dasharray="2,2"' if nos[i]["estado"]=="a_receber" else ''
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="{f}" stroke="{s}" stroke-width="1.6"{dash}/>')
        o.append(f'<text x="{x:.1f}" y="{y+3.5:.1f}" font-size="9" font-weight="700" text-anchor="middle" fill="#ffffff">{i}</text>')

    ly=H-78; lx=M
    o.append(f'<text x="{lx}" y="{ly-16}" font-size="11.5" font-weight="700" fill="#333333">cor do nó — suporte documental</text>')
    legenda = SUPORTE_TOPO + ["outros_suportes"]
    for g in legenda:
        f,s = (PALETA8[SUPORTE_TOPO.index(g)] if g in SUPORTE_TOPO else CINZA)
        rot = ROT_SUPORTE.get(g,g)
        o.append(f'<circle cx="{lx+6}" cy="{ly}" r="6" fill="{f}" stroke="{s}" stroke-width="1.5"/>')
        o.append(f'<text x="{lx+17}" y="{ly+4}" font-size="10.5" fill="#333333">{esc(rot)}</text>')
        lx+=len(rot)*5.9+34
        if lx>W-260: lx=M; ly+=20
    rodape = "Borda tracejada = item ainda não lido."
    if suprimidos:
        rodape += f" {len(suprimidos)} rótulo(s) suprimido(s) por densidade (id sempre visível no nó; nome completo no relatório): " + ", ".join(sorted(suprimidos,key=int))
    o.append(f'<text x="{M}" y="{H-14}" font-size="10" fill="#777777">*outros suportes: entrevista, livro (avulso), documento técnico, reportagem, manual técnico, TCC — ver relatório. {esc(rodape)}</text>')
    o.append('</svg>')
    open(path,"w",encoding="utf-8", newline="\n").write("\n".join(o))

# ------------------------------------------------------------- figura 2 ----
ANO_PARCIAL = 2026   # janela 2015-2026: 2026 vai até a data da busca (set/2026)

def svg_generos(nos,path):
    # 17/09/2026 (a pedido do autor): eixo de categoria trocado de gênero
    # textual/suporte para "cita caso concreto" x "teórico" (classifica_caso,
    # ver nota acima de filtra_corpus81) — mais direto para o argumento do
    # capítulo do que o suporte bibliográfico do item. Sem cabeçalho de
    # texto embutido (Design System das Figuras) — legenda/metodologia no
    # corpo do texto (Anexo §5), não na imagem.
    # 18/09/2026 (a pedido do autor: "preferia ter todos os anos com uma
    # barra mais fina e o ano inclinado") — a tentativa anterior de resolver
    # a largura de impressão agrupando 1991-2019 em faixas foi revertida:
    # volta a mostrar cada ano individualmente (nenhuma perda de resolução),
    # e a compactação vem de coluna mais estreita + rótulo do eixo rotacionado
    # -45°, técnica padrão para linha do tempo densa (ver dataviz skill).
    anos_com_dado=sorted({int(n["ano"]) for n in nos.values()})
    ano_min, ano_max = anos_com_dado[0], max(anos_com_dado[-1], ANO_PARCIAL)
    anos=list(range(ano_min, ano_max+1))
    gens = ["empirico","teorico"]
    cont=collections.Counter((int(n["ano"]),classifica_caso(n)) for n in nos.values())
    COLW = 32  # largura de coluna (pitch) — antes 56px; mais estreito, ano inclinado no eixo compensa
    W,H=max(1180, round(COLW*len(anos))),500; L,B,R,T_=110,110,60,50
    maxv=max(sum(cont[(a,g)] for g in gens) for a in anos)
    ALTURA_MIN_PX = 3.5   # piso de altura visivel para barra com valor>0 mas pequeno (ex.: 2026 com 1 item)
    bw=(W-L-R)/len(anos)*0.5   # barra mais fina (era 0.68 do pitch)
    o=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
       '<style>text{font-family:Aptos,Calibri,Helvetica,Arial,sans-serif}</style>']
    for v in range(0,maxv+1,2):
        y=H-B-(v/maxv)*(H-T_-B)
        o.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="#e4e4e4" stroke-width="1"/>')
        o.append(f'<text x="{L-10}" y="{y+4:.1f}" font-size="11" text-anchor="end" fill="#666666">{v}</text>')
    for i,a in enumerate(anos):
        x=L+(i+0.5)*((W-L-R)/len(anos))-bw/2; acc=0
        parcial = (a == ANO_PARCIAL)
        # 18/09/2026 (achado do autor: "o tracejado esta na frente e nao
        # conseguimos ver o item") -- o retangulo de destaque do ano parcial
        # tinha fill opaco e era desenhado DEPOIS da barra, cobrindo o dado.
        # Corrigido: desenha antes (fica atras) e sem fill (so o contorno
        # tracejado), para nunca conseguir esconder a barra por cima dele.
        if parcial:
            o.append(f'<rect x="{x:.1f}" y="{T_:.1f}" width="{bw:.1f}" height="{H-B-T_:.1f}" fill="none" stroke="#cfcfcf" stroke-width="1" stroke-dasharray="4,3"/>')
        for g in gens:
            v=cont[(a,g)]
            if not v: continue
            h=(v/maxv)*(H-T_-B)
            if h < ALTURA_MIN_PX: h = ALTURA_MIN_PX
            y=H-B-acc-h
            f,s = COR_CASO[g]
            o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{f}" stroke="{s}" stroke-width="1"/>')
            if h>=15:
                o.append(f'<text x="{x+bw/2:.1f}" y="{y+h/2+4:.1f}" font-size="9.5" font-weight="700" text-anchor="middle" fill="#ffffff">{v}</text>')
            else:
                o.append(f'<text x="{x+bw/2:.1f}" y="{y-4:.1f}" font-size="9" font-weight="700" text-anchor="middle" fill="{s}">{v}</text>')
            acc+=h
        if parcial and acc == 0:
            o.append(f'<text x="{x+bw/2:.1f}" y="{H-B-12:.1f}" font-size="10.5" text-anchor="middle" fill="#a33">0</text>')
        rot = f"{a}*" if parcial else f"{a}"
        peso = ' font-weight="700"' if parcial else ''
        cor  = "#a33" if parcial else "#333333"
        lblx, lbly = x+bw/2, H-B+16
        o.append(f'<text x="{lblx:.1f}" y="{lbly:.1f}" font-size="9.5" text-anchor="end" fill="{cor}"{peso} transform="rotate(-45 {lblx:.1f} {lbly:.1f})">{rot}</text>')
    ly=H-52; lx=L
    for g in gens:
        f,s = COR_CASO[g]
        rot=ROT_CASO[g]
        o.append(f'<rect x="{lx}" y="{ly-8}" width="11" height="11" fill="{f}" stroke="{s}" stroke-width="1"/>')
        o.append(f'<text x="{lx+16}" y="{ly+1}" font-size="10.5" fill="#333333">{esc(rot)}</text>')
        lx+=len(rot)*5.9+38
        if lx>W-250: lx=L; ly+=19
    o.append(f'<text x="{L}" y="{H-12}" font-size="10.5" fill="#a33">* {ANO_PARCIAL} é ANO PARCIAL (até a data da busca, set/2026) — não comparar com ano fechado. Classificação por `tipo_de_alegacao`; itens sem esse campo (29 de 81) lidos manualmente pelo escopo — a revisar, ver Relatório da rede (gerado).</text>')
    o.append('</svg>')
    open(path,"w",encoding="utf-8", newline="\n").write("\n".join(o))

def svg_generos_genero(nos,path):
    """18/09/2026 (a pedido do autor: "as versoes anteriores, com a
    classificacao por tipo podem ir para o anexo") -- figura complementar a
    A2, mesma reversao a colunas individuais/barra fina/rotulo inclinado de
    svg_generos(), mas cor pelo genero textual fino (GENERO_TOPO/cor_genero),
    a classificacao original antes da troca para caso concreto x teorico."""
    def gfino(n):
        g=(n.get("genero") or "").strip() or "outros_generos"
        return g if g in GENERO_TOPO else "outros_generos"
    anos_com_dado=sorted({int(n["ano"]) for n in nos.values()})
    ano_min, ano_max = anos_com_dado[0], max(anos_com_dado[-1], ANO_PARCIAL)
    anos=list(range(ano_min, ano_max+1))
    gens = GENERO_TOPO + ["outros_generos"]
    cont=collections.Counter((int(n["ano"]),gfino(n)) for n in nos.values())
    COLW = 32
    W,H=max(1180, round(COLW*len(anos))),560; L,B,R,T_=110,110,60,50
    maxv=max(sum(cont[(a,g)] for g in gens) for a in anos)
    ALTURA_MIN_PX = 3.5
    bw=(W-L-R)/len(anos)*0.5
    o=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
       '<style>text{font-family:Aptos,Calibri,Helvetica,Arial,sans-serif}</style>']
    for v in range(0,maxv+1,2):
        y=H-B-(v/maxv)*(H-T_-B)
        o.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="#e4e4e4" stroke-width="1"/>')
        o.append(f'<text x="{L-10}" y="{y+4:.1f}" font-size="11" text-anchor="end" fill="#666666">{v}</text>')
    for i,a in enumerate(anos):
        x=L+(i+0.5)*((W-L-R)/len(anos))-bw/2; acc=0
        parcial = (a == ANO_PARCIAL)
        if parcial:
            o.append(f'<rect x="{x:.1f}" y="{T_:.1f}" width="{bw:.1f}" height="{H-B-T_:.1f}" fill="none" stroke="#cfcfcf" stroke-width="1" stroke-dasharray="4,3"/>')
        for g in gens:
            v=cont[(a,g)]
            if not v: continue
            h=(v/maxv)*(H-T_-B)
            if h < ALTURA_MIN_PX: h = ALTURA_MIN_PX
            y=H-B-acc-h
            f,s = (PALETA8[GENERO_TOPO.index(g)] if g in GENERO_TOPO else CINZA)
            o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{f}" stroke="{s}" stroke-width="1"/>')
            if h>=15:
                o.append(f'<text x="{x+bw/2:.1f}" y="{y+h/2+4:.1f}" font-size="9.5" font-weight="700" text-anchor="middle" fill="#ffffff">{v}</text>')
            else:
                o.append(f'<text x="{x+bw/2:.1f}" y="{y-4:.1f}" font-size="9" font-weight="700" text-anchor="middle" fill="{s}">{v}</text>')
            acc+=h
        if parcial and acc == 0:
            o.append(f'<text x="{x+bw/2:.1f}" y="{H-B-12:.1f}" font-size="10.5" text-anchor="middle" fill="#a33">0</text>')
        rot = f"{a}*" if parcial else f"{a}"
        peso = ' font-weight="700"' if parcial else ''
        cor  = "#a33" if parcial else "#333333"
        lblx, lbly = x+bw/2, H-B+16
        o.append(f'<text x="{lblx:.1f}" y="{lbly:.1f}" font-size="9.5" text-anchor="end" fill="{cor}"{peso} transform="rotate(-45 {lblx:.1f} {lbly:.1f})">{rot}</text>')
    # 18/09/2026 (achado do autor: "no que tem mais legenda, tambem temos a
    # legenda sobrepondo o ano") -- com o rotulo do eixo inclinado a -45 graus
    # (18/09/2026), a extensao vertical do rotulo cresceu (diagonal, nao mais
    # uma linha horizontal rasa) e passou a invadir a zona da legenda de 2
    # linhas desta figura (a unica com legenda de 2 linhas; a A2 tem so 2
    # itens e cabe em 1 linha, por isso so esta figura apresentou o problema).
    # Legenda empurrada mais para baixo para abrir vao livre do rotulo.
    ly=H-70; lx=L
    for g in gens:
        f,s = (PALETA8[GENERO_TOPO.index(g)] if g in GENERO_TOPO else CINZA)
        rot=ROT_GENERO.get(g,g)
        o.append(f'<rect x="{lx}" y="{ly-8}" width="11" height="11" fill="{f}" stroke="{s}" stroke-width="1"/>')
        o.append(f'<text x="{lx+16}" y="{ly+1}" font-size="10.5" fill="#333333">{esc(rot)}</text>')
        lx+=len(rot)*5.9+38
        if lx>W-250: lx=L; ly+=19
    o.append(f'<text x="{L}" y="{H-26}" font-size="10.5" fill="#555555">"outros gêneros" agrupa as 21 categorias menos frequentes do vocabulário fino (ver relatório).</text>')
    o.append(f'<text x="{L}" y="{H-12}" font-size="10.5" fill="#a33">* {ANO_PARCIAL} é ANO PARCIAL (até a data da busca, set/2026) — não comparar com ano fechado.</text>')
    o.append('</svg>')
    open(path,"w",encoding="utf-8", newline="\n").write("\n".join(o))

def le_completas():
    p=os.path.join(DIR,"citacoes_completas.csv")
    if not os.path.exists(p): return []
    with open(p,encoding="utf-8") as f: return [r for r in csv.DictReader(f,delimiter=";")]

# ------------------------------------------------------------- figura 3 ----
def svg_coc(nos,path,minimo=2):
    """Rede de co-citação: itens do corpus ligados quando compartilham referência externa."""
    cc=le_completas()
    if not cc:
        return
    por=collections.defaultdict(set)
    for r in cc:
        if r["tipo"]=="externo" and r["id_origem"] in nos: por[r["id_origem"]].add(r["chave_citada"])
    todos=[i for i in sorted(por,key=lambda s:(len(s),s))]
    pesos={}
    for a in range(len(todos)):
        for b in range(a+1,len(todos)):
            w=len(por[todos[a]] & por[todos[b]])
            if w>=minimo: pesos[(todos[a],todos[b])]=w
    conectados=sorted({x for par in pesos for x in par}, key=lambda s:(len(s),s))
    isolados=[i for i in todos if i not in conectados]

    W,M=1760,130
    por_linha_iso = 34
    linhas_iso = max(1, -(-len(isolados)//por_linha_iso)) if isolados else 0
    painel_h = 70 + linhas_iso*40 if isolados else 0
    H = 1160
    topo_rede, base_rede = 110, H - (painel_h + 90 if isolados else 90)
    pos_raw=layout_forcas(conectados,[(a,b) for (a,b) in pesos],it=1100,seed=7)
    pos_raw,(minx,maxx,miny,maxy)=normalizar(pos_raw)
    def T(p):
        x=M+(p[0]-minx)/(maxx-minx)*(W-2*M)
        y=topo_rede+(1-(p[1]-miny)/(maxy-miny))*(base_rede-topo_rede)
        return (x,y)
    P={i:T(pos_raw[i]) for i in conectados}
    wmax=max(pesos.values()) if pesos else 1

    o=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
       '<style>text{font-family:Aptos,Calibri,Helvetica,Arial,sans-serif}</style>',
       f'<text x="{M}" y="44" font-size="13.5" fill="#555555">{len(todos)} itens do corpus RSL (81, estrato RSL1–RSL4) com referências extraídas · aresta = ao menos {minimo} referências externas em comum · espessura = quantas · cor = suporte (genero_suporte)</text>']

    for (a,b),w in sorted(pesos.items(),key=lambda x:x[1]):
        (x1,y1),(x2,y2)=P[a],P[b]
        sw=1.0+3.6*(w/wmax)
        o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#7a9bb0" stroke-width="{sw:.1f}" opacity="0.58"/>')
        if w>=6:
            o.append(f'<text x="{(x1+x2)/2:.1f}" y="{(y1+y2)/2:.1f}" font-size="9.5" text-anchor="middle" fill="#33586e">{w}</text>')

    forca=collections.Counter()
    for (a,b),w in pesos.items(): forca[a]+=w; forca[b]+=w
    ordem=sorted(conectados,key=lambda i:(-forca[i], i))
    raios={i:9+0.14*forca[i] for i in conectados}
    ocupados=[]
    for i in ordem:
        x,y=P[i]; r=raios[i]; ocupados.append((x-r,y-r,x+r,y+r))
    for i in ordem:
        x,y=P[i]; r=raios[i]
        nome=nos.get(i,{}).get("autores","?").strip(chr(34)).split(";")[0][:22]
        posiciona_rotulo(x,y,r,esc(nome),10.5,ocupados)  # reserva o espaço; desenho abaixo

    ocupados2=[]
    for i in ordem:
        x,y=P[i]; r=raios[i]; ocupados2.append((x-r,y-r,x+r,y+r))
    for i in ordem:
        x,y=P[i]; r=raios[i]
        g=nos.get(i,{}).get("genero_suporte") or nos.get(i,{}).get("genero","a_confirmar")
        f,s=cor_suporte(g)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{f}" stroke="{s}" stroke-width="2"/>')
        rotulo_id = i if i.isdigit() else "L"
        o.append(f'<text x="{x:.1f}" y="{y+4:.1f}" font-size="11" font-weight="700" text-anchor="middle" fill="#ffffff">{rotulo_id}</text>')
    suprimidos=[]
    ocupados3=list(ocupados2)
    for i in ordem:
        x,y=P[i]; r=raios[i]
        nome=nos.get(i,{}).get("autores","?").strip(chr(34)).split(";")[0][:22]
        res=posiciona_rotulo(x,y,r,esc(nome),10.5,ocupados3)
        if res:
            lx,ly,anchor,fs=res
            o.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="{fs}" text-anchor="{anchor}" fill="#222222">{esc(nome)}</text>')
        else:
            suprimidos.append(i)

    py0 = base_rede + 44
    if isolados:
        o.append(f'<line x1="{M}" y1="{py0-14}" x2="{W-M+50}" y2="{py0-14}" stroke="#dddddd" stroke-width="1"/>')
        o.append(f'<text x="{M}" y="{py0+6}" font-size="13" font-weight="700" fill="#333333">Sem {minimo}+ referências em comum com nenhum outro item ({len(isolados)}) — leem literaturas distintas</text>')
    cx0, cy0, passo, por_linha = M, py0+38, 40, por_linha_iso
    for k,i in enumerate(isolados):
        row,col = divmod(k, por_linha)
        x = cx0 + col*passo; y = cy0 + row*passo
        g=nos.get(i,{}).get("genero_suporte") or nos.get(i,{}).get("genero","a_confirmar")
        f,s=cor_suporte(g)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="{f}" stroke="{s}" stroke-width="1.6"/>')
        rid = i if i.isdigit() else "L"
        o.append(f'<text x="{x:.1f}" y="{y+3.5:.1f}" font-size="9" font-weight="700" text-anchor="middle" fill="#ffffff">{rid}</text>')

    rodape = "L = Lightner et al. (2026), fora dos itens do corpus."
    if suprimidos:
        rodape += f" {len(suprimidos)} rótulo(s) suprimido(s) por densidade: " + ", ".join(suprimidos)
    o.append(f'<text x="{M}" y="{H-14}" font-size="10" fill="#777777">{esc(rodape)}</text>')
    o.append('</svg>')
    open(path,"w",encoding="utf-8", newline="\n").write("\n".join(o))

def relatorio(nos,ar,internas,grau,suprimidos,path,nos_acervo=None):
    L=[]; A=L.append
    A("---"); A('title: "Relatório — rede bibliométrica da RSL"'); A("tags: [dados, rsl-tz, bibliometria]")
    A("publish: false"); A("created: 2026-09-02"); A("---"); A("")
    A("# Relatório — rede bibliométrica da RSL"); A("")
    A("> Gerado por `_meta/scripts/rede_bibliometrica.py`. Não substitui o VOSviewer por escolha:")
    A("> **não há base Scopus/WoS com cobertura deste corpus** — é o achado de Lightner et al. (2026),")
    A("> 45 estudos e zero brasileiros. A rede é construída a partir dos fichamentos, com cobertura declarada.")
    A("")
    A("> 🔧 **Reescrita de 17/09/2026 — população restrita aos 81 itens do corpus.** A pedido do autor "
      "(\"vamos refazer baseado exclusivamente nos 81 do corpus selecionado\"), as três figuras e este "
      "relatório passaram a operar **só** sobre o corpus estrito da RSL — `estrato` em RSL1-4 **e** "
      "`estado=fichado`, 81 itens — em vez do acervo inteiro (183, sem filtro), que era a base real da "
      "versão anterior apesar de o texto já falar em \"corpus\". Efeito medido: das 178 arestas `interno` "
      "do acervo, só 25 têm as duas pontas dentro dos 81 (as outras citam ou são citadas por itens fora "
      "do corpus estrito — documental, sem estrato, ou excluído); na co-citação, de 88 itens do acervo "
      "com referências extraídas, 55 pertencem ao corpus. **A rede fica mais esparsa — é o retrato "
      "correto da população pedida, não um defeito.**")
    A("")
    A("> 🔧 Reescrita de 16/09/2026 (mantida): o dicionário de cores por `genero` só cobria 12 dos 29 "
      "valores em uso — itens fora disso viravam cinza \"a_confirmar\" na rede e eram omitidos da contagem "
      "no gráfico de gêneros por ano, sem aviso; a paleta antiga não passava no validador de "
      "acessibilidade do skill de visualização do cofre; nós isolados ficavam presos a um anel "
      "decorativo. As três causas foram corrigidas — ver o cabeçalho do script para o detalhe técnico.")
    A("")
    if nos_acervo is not None:
        exc_acervo=[i for i,n in nos_acervo.items() if n.get("estado")=="excluido_apos_leitura"]
        A(f"**Três populações — não confundir.** `corpus_rsl.csv` tem **{len(nos_acervo)}** itens no "
          f"total (o acervo lido pela revisão). Deste total: **{len(nos)} formam o corpus estrito** usado "
          f"em todas as tabelas e figuras abaixo (RSL1-4, fichado); **{len(exc_acervo)}** estão marcados "
          "`excluido_apos_leitura` e permanecem no arquivo só como referencial da tese; o restante é "
          "`fonte_documental`, sem estrato atribuído, ou reclassificado/indisponível. Ver "
          "`Anexo - RSL completa e fichamentos (Tarifa Zero)` §3 para a reconciliação completa "
          "dos números.")
        A("")
    LIDOS_EST={"fichado","excluido_apos_leitura"}
    lidos=[n for n in nos.values() if n["estado"] in LIDOS_EST]
    CT=com_texto(); fonte=[i for i in nos if i in CT]
    A(f"**Cobertura dentro do corpus ({len(nos)} itens), em dois números — e são diferentes.**")
    A("")
    A(f"- **fichados:** {len(lidos)} de {len(nos)} — por definição, 100% (o corpus já é filtrado a `estado=fichado`).")
    A(f"- 🔴 **com texto extraído, que é a base real das arestas:** {len(fonte)} de {len(nos)} "
      f"({len(fonte)/len(nos)*100:.0f}%). **Uma aresta só pode PARTIR de um item cujo texto foi extraído.**")
    A("")
    A("⚠️ **Portanto a densidade abaixo é um piso duplo:** limitada pelos itens com texto e pelo "
      "parser heurístico de referências. **Não é a densidade real da rede.**")
    if len(fonte) < len(lidos):
        falta=sorted((i for i in nos if nos[i]["estado"] in LIDOS_EST and i not in CT), key=int)
        A("")
        A(f"🔴 **Fichados SEM texto extraído ({len(falta)}), que não podem originar aresta:** " + ", ".join(falta))
    if suprimidos:
        A("")
        A(f"🟡 **Rótulos suprimidos por densidade na figura de citações ({len(suprimidos)}):** o id continua "
          "visível no nó; nome e ano por extenso aqui: " + " · ".join(
              f"{i} ({nos[i]['autores'].strip(chr(34)).split(';')[0]}, {nos[i]['ano']})" for i in sorted(suprimidos,key=int)))
    A("")
    A("## Gêneros (vocabulário fino — 29 valores em 16/09/2026)")
    A(""); A("| gênero | itens | lidos |"); A("|---|---:|---:|")
    c=collections.Counter(n["genero"] for n in nos.values())
    cl=collections.Counter(n["genero"] for n in lidos)
    for g,v in c.most_common(): A(f"| {g} | {v} | {cl[g]} |")
    A("")
    A("## Suporte (`genero_suporte` — vocabulário controlado, 14 valores em 16/09/2026)")
    A("")
    A("> Campo usado para **cor** nas redes (7 categorias mais frequentes + \"outros suportes\").")
    A(""); A("| suporte | itens | fichados |"); A("|---|---:|---:|")
    cs=collections.Counter(gsup(n) for n in nos.values()); csl=collections.Counter(gsup(n) for n in lidos)
    for g,v in cs.most_common(): A(f"| {g} | {v} | {csl[g]} |")
    A("")
    A("## 🚨 Tipo de alegação — quantos itens MEDEM e quantos POSICIONAM")
    A("")
    A("> Campo criado em 07/09/2026 para a calibragem de Becker: distinguir **dado, evidência e inferência**.")
    A("")
    ROT_ALEGACAO = {
     "dado_primario":"dado primário","analise_secundaria":"análise de dado de terceiros",
     "revisao_de_literatura":"revisão de literatura","ensaio_teorico":"ensaio teórico",
     "posicionamento":"posicionamento de ator","normativo_juridico":"normativo ou jurídico",
     "a_confirmar":"a confirmar",
    }
    ca=collections.Counter(n.get("tipo_de_alegacao","") or "(vazio)" for n in nos.values())
    A("| tipo de alegação | itens | % |"); A("|---|---:|---:|")
    for g,v in ca.most_common(): A(f"| {ROT_ALEGACAO.get(g,g)} | {v} | {v/len(nos)*100:.0f}% |")
    A("")
    ROT_POLO = {
     "academico":"acadêmico","advocacia_setorial":"advocacia setorial","patronal":"patronal",
     "gestao_municipal":"gestão municipal","gestao_estadual_federal":"gestão estadual ou federal",
     "legislativo":"legislativo","sociedade_civil":"sociedade civil",
     "consultoria_tarifaria":"consultoria tarifária","arena_mista":"arena mista (concedente + patronal)",
     "a_confirmar":"a confirmar",
    }
    A("## 🚨 Polo institucional (8 valores + arena mista)")
    A(""); A("| polo | itens | % |"); A("|---|---:|---:|")
    cp=collections.Counter(n.get("polo_8","") or n.get("polo","") for n in nos.values())
    for g,v in cp.most_common(): A(f"| {ROT_POLO.get(g,g)} | {v} | {v/len(nos)*100:.0f}% |")
    A("")
    A("**Instituição produtora declarada** (posicionalidade — insumo do §4 da nota do RSL4):")
    A(""); A("| instituição | itens |"); A("|---|---:|")
    for g,v in collections.Counter(n.get("instituicao_produtora","") for n in nos.values() if n.get("instituicao_produtora")).most_common():
        A(f"| {g} | {v} |")
    A("")
    A("**Origem:** " + " · ".join(f"{k} **{v}**" for k,v in collections.Counter(n.get("origem","") or "?" for n in nos.values()).most_common()))
    A("")
    A("## Escopo geográfico")
    A("")
    A("> 🔒 Decomposto em 07/09/2026. **`escopo_nota` é texto livre e NÃO entra em contagem.**")
    A("")
    A("| país / região | itens |"); A("|---|---:|")
    for e,v in collections.Counter(n.get("escopo_pais","") or "?" for n in nos.values()).most_common(): A(f"| {e} | {v} |")
    A("")
    ufs=collections.Counter(n.get("escopo_uf","") for n in nos.values() if n.get("escopo_uf"))
    A(f"**UF, quando declarada ({sum(ufs.values())} de {len(nos)} itens):** " + " · ".join(f"{k} **{v}**" for k,v in ufs.most_common()))
    A("")
    ns=[n for n in nos.values() if n.get("escopo_n_casos")]
    def _n_lider(z):
        # 🩹 16/09/2026: alguns valores vêm com nota entre parênteses (ex. "1 (Região
        # de Bruxelas)"), não só o inteiro — int(z) puro quebrava aqui. Ordena pelo
        # número líder e cai para 0 se não achar dígito, em vez de travar o relatório.
        m=""
        for ch in str(z).strip():
            if ch.isdigit(): m+=ch
            else: break
        return -int(m) if m else 0
    A(f"**Itens com n de casos declarado: {len(ns)}** — " + ", ".join(sorted(set(x["escopo_n_casos"] for x in ns), key=_n_lider)))
    A("")
    A("## Polo institucional")
    A(""); A("| polo | itens |"); A("|---|---:|")
    for e,v in collections.Counter(n["polo"] for n in nos.values()).most_common(): A(f"| {e} | {v} |")
    A("")
    A("## Rede de citações internas")
    A("")
    A(f"- arestas internas identificadas: **{len(internas)}**")
    A(f"- nós com ao menos uma ligação interna: **{len([i for i in nos if grau[i]>0])}**")
    poss=len(fonte)*(len(fonte)-1)
    if poss:
        A(f"- densidade entre os itens **com texto extraído**: **{len(internas)/poss*100:.1f}%** "
          f"({len(internas)} de {poss} pares dirigidos possíveis)")
    possl=len(lidos)*(len(lidos)-1)
    if possl:
        A(f"- densidade se todos os fichados tivessem texto (piso mais baixo, para comparação): "
          f"**{len(internas)/possl*100:.1f}%** ({len(internas)} de {possl})")
    A("")
    A("**Mais citados dentro do corpus:**"); A("")
    rec=collections.Counter(b for a,b in internas)
    A("| id | autor | ano | citações internas recebidas |"); A("|---|---|---:|---:|")
    for i,v in rec.most_common(8):
        n=nos.get(i,{});  A(f"| {i} | {n.get('autores','?').strip(chr(34))} | {n.get('ano','?')} | {v} |")
    A("")
    iso=[i for i in sorted(nos,key=int) if grau[i]==0 and i in CT]
    _refs = collections.Counter(r["id_origem"] for r in le_completas())
    _real = [i for i in iso if _refs.get(i, 0) > 0]
    _indet = [i for i in iso if _refs.get(i, 0) == 0]
    def _rot(Ls):
        return ", ".join(f"{i} ({nos[i]['autores'].strip(chr(34)).split(';')[0]} {nos[i]['ano']})" for i in Ls)
    A(f"🔒 **ISOLAMENTO REAL ({len(_real)} de {len(iso)}) — o item CITA (1 ou mais referências extraídas) e nenhuma é do corpus.** "
      f"**É este o grupo que sustenta afirmação de tese:** " + _rot(_real))
    A("")
    A(f"⚠️ **INDETERMINADO ({len(_indet)} de {len(iso)}) — nenhuma referência extraída, portanto NÃO se sabe se o item cita o corpus.** "
      f"Parte não tem seção de referências (editorial, parecer, apresentação, normativo) e o resultado é correto; "
      f"parte é falha do parser. 🔴 **Não usar como evidência de isolamento:** " + _rot(_indet))
    A("")
    ext=collections.Counter(r["destino"] for r in ar if r["tipo"].startswith("externo") and r["destino"].startswith("EXT:") and r["origem"] in nos)
    A("**Referências externas recorrentes (citadas por mais de um item do corpus):**"); A("")
    A("| referência externa | itens do corpus que a citam |"); A("|---|---:|")
    for e,v in ext.most_common():
        if v>1: A(f"| {e.replace('EXT:','')} | {v} |")
    A("")
    cc=le_completas()
    if cc:
        A("## Referências extraídas dos itens lidos")
        A("")
        cc_corpus=[r for r in cc if r["id_origem"] in nos]
        porit=collections.defaultdict(set)
        for r in cc_corpus:
            if r["tipo"]=="externo": porit[r["id_origem"]].add(r["chave_citada"])
        A(f"- itens do corpus com referências extraídas: **{len(porit)}**")
        A(f"- citações registradas (partindo de itens do corpus): **{len(cc_corpus)}**")
        A(f"- referências distintas: **{len({r['chave_citada'] for r in cc_corpus})}**")
        A(f"- citações a itens do próprio corpus: **{sum(1 for r in cc_corpus if r['tipo']=='interno')}**")
        A("")
        A("**Referências mais co-citadas e AUSENTES do corpus — o que falta procurar:**")
        A(""); A("| co-citações | citada pelos itens | referência |"); A("|---:|---|---|")
        fr=collections.Counter(r["chave_citada"] for r in cc_corpus)
        prim={}
        for r in cc_corpus: prim.setdefault(r["chave_citada"],r)
        for k,v in fr.most_common():
            if v<3: break
            if prim[k]["id_corpus_citado"]: continue
            quem=",".join(sorted({r["id_origem"] for r in cc_corpus if r["chave_citada"]==k},key=lambda s:(len(s),s)))
            A(f"| {v} | {quem} | {esc(prim[k]['referencia'][:150])} |")
        A("")
        A("**Co-citação entre itens (referências externas em comum, mínimo 4):**")
        A(""); A("| par | referências em comum |"); A("|---|---:|")
        ids2=sorted(porit,key=lambda s:(len(s),s)); pares=[]
        for a in range(len(ids2)):
            for b in range(a+1,len(ids2)):
                w=len(porit[ids2[a]] & porit[ids2[b]])
                if w>=4: pares.append((ids2[a],ids2[b],w))
        for a,b,w in sorted(pares,key=lambda x:-x[2])[:15]: A(f"| {a} ↔ {b} | {w} |")
        A("")
    A("## Figuras")
    A("- `_attachments/rede_rsl_citacoes.svg`")
    A("- `_attachments/rsl_generos_por_ano.svg`")
    A("- `_attachments/rsl_cocitacao.svg`")
    open(path,"w",encoding="utf-8", newline="\n").write("\n".join(L)+"\n")

if __name__=="__main__":
    nos_acervo,ar=ler(); os.makedirs(ATT,exist_ok=True)
    nos=filtra_corpus81(nos_acervo)
    assert len(nos)==81, f"corpus81 tem {len(nos)} itens, esperado 81 — checar corpus_rsl.csv"
    # 17/09/2026: uma aresta so conta como "interno" (rede de citacoes do corpus)
    # se as DUAS pontas estiverem nos 81 - senao ela cita/e citada por algo fora
    # da populacao restrita e nao pertence a esta figura.
    ar81=[r for r in ar if not (r["tipo"]=="interno" and (r["origem"] not in nos or r["destino"] not in nos))]
    internas,grau,suprimidos=svg_rede(nos,ar81,os.path.join(ATT,"rede_rsl_citacoes.svg"))
    svg_generos(nos,os.path.join(ATT,"rsl_generos_por_ano.svg"))
    relatorio(nos,ar81,internas,grau,suprimidos,os.path.join(DIR,"Relatório da rede (gerado).md"),nos_acervo)
    svg_coc(nos,os.path.join(ATT,"rsl_cocitacao.svg"))
    # 18/09/2026 (a pedido do autor): companheiras com a classificação original
    # (suporte documental / gênero fino) para o Anexo, ao lado das novas A1/A2
    # por caso concreto x teórico -- ver notas de svg_rede_suporte/svg_generos_genero.
    svg_rede_suporte(nos,ar81,os.path.join(ATT,"rede_rsl_citacoes_suporte.svg"))
    svg_generos_genero(nos,os.path.join(ATT,"rsl_generos_por_ano_genero.svg"))
    print(f"OK  _attachments/rede_rsl_citacoes.svg  ({len(nos)} itens do corpus, {len(internas)} arestas internas)")
    print("OK  _attachments/rsl_generos_por_ano.svg")
    print("OK  05 - Referências/Rede bibliométrica/Relatório da rede (gerado).md")
    print("OK  _attachments/rsl_cocitacao.svg")
    print("OK  _attachments/rede_rsl_citacoes_suporte.svg  (companheira A1b, suporte documental)")
    print("OK  _attachments/rsl_generos_por_ano_genero.svg  (companheira A2b, gênero fino)")
