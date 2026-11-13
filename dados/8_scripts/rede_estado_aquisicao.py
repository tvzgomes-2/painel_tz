#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rede_estado_aquisicao.py — mapas bibliométricos da RSL coloridos pelo
ESTADO DE AQUISIÇÃO de cada obra, e não por agrupamento temático.

Responde a uma pergunta operacional, não conceitual: no mapa que o campo desenha
com suas próprias citações, o que já lemos, o que falta pegar e o que não
conseguimos pegar?

CATEGORIAS (excludentes, nesta ordem de precedência)
  fichado ............. há fichamento no cofre (nota em "Notas de leitura")
  corpus não fichado .. está no corpus_rsl.csv, sem fichamento
  a adquirir .......... identificado na lista de aquisição do RSL1, com localização
  inacessível ......... identificado e SEM via de acesso conhecida (servidor fora
                        do ar, repositório sem URL, item não localizado)
  não avaliado ........ referência que o corpus cita e que nunca foi triada

SAÍDAS  dois SVGs em _attachments/, cores fixas em hex, fundo branco, e um
        relatório .md com as listas nominais por categoria.

REUSO   importa o layout VOS e a normalização de rede_vos.py — não duplica o
        método, só troca a codificação de cor e a legenda.
"""
import csv, io, math, os, re, sys, collections, unicodedata, datetime

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rede_vos as rv

DIR   = os.path.join(_RAIZ, "05 - Referências", "Rede bibliométrica")
NOTAS = os.path.join(_RAIZ, "05 - Referências", "Notas de leitura")
RSL1  = os.path.join(_RAIZ, "06 - Acadêmico", "Artigos", "1 - Em elaboração",
                     "PGT-092 (revisão sistemática)", "RSL1_BDTD_lista_de_aquisicao.csv")
OUT   = os.path.join(_RAIZ, "_attachments")
DATA  = datetime.date.today().strftime("%d/%m/%Y")

# ---- categorias e paleta (fixa, hex, legível em claro e escuro) -------------
CATS = ["fichado", "corpus não fichado", "no acervo, sem ficha", "a adquirir", "inacessível", "fora do escopo", "não avaliado"]
COR  = {"fichado":            "#1e8449",   # verde — está lido
        "corpus não fichado": "#b7860b",   # âmbar — é nosso, falta ler
        "no acervo, sem ficha": "#0e8f9e", # turquesa — a referência está catalogada, falta ler
        "a adquirir":         "#2e86c1",   # azul — sabemos onde está
        "inacessível":        "#c0392b",   # vermelho — sabemos que existe e não alcançamos
        "fora do escopo":     "#7d3c98",   # roxo — triado e excluído por critério
        "não avaliado":       "#95a5a6"}   # cinza — o campo cita e nunca triamos

# ---- itens sem via de acesso conhecida, curados à mão ----------------------
# chave normalizada (sobrenome+ano) -> motivo
INACESSIVEL = {
    "cadaval1993": "repositório da UnB retornando 503 em todo o site (03/09/2026)",
}

def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())

def chave(sobrenome, ano):
    return "%s%s" % (norm(sobrenome), str(ano).strip())

def primeiro_sobrenome(autor):
    """Primeiro sobrenome de um campo de autoria em qualquer formato do cofre."""
    a = str(autor).strip('" ').split(";")[0].strip()
    if "," in a:
        return a.split(",")[0].strip()
    return a.split()[-1] if a.split() else a

# ---------------------------------------------------------------- inventário
def ler_fichados():
    """(sobrenome, ano) de cada fichamento existente, pelo nome do arquivo."""
    out = {}
    if not os.path.isdir(NOTAS):
        return out
    for nome in os.listdir(NOTAS):
        if not nome.startswith("Fichamento") or not nome.endswith(".md"):
            continue
        m = re.match(r"Fichamento\s*-\s*(.+?)\s*\((\d{4})\)", nome)
        if not m:
            continue
        bloco, ano = m.group(1), m.group(2)
        # "Cardozo et al.", "Fix, Ribeiro e Prado", "Gomes Filho" -> primeiro sobrenome
        bloco = re.split(r",| e | et al\.?|&", bloco)[0].strip()
        if bloco:
            out[chave(bloco.split()[-1] if len(bloco.split()) > 1 else bloco, ano)] = nome
            # nomes compostos ("Gomes Filho", "Moraes da Silva"): registra também o 1º token
            out.setdefault(chave(bloco.split()[0], ano), nome)
    return out

def ler_e1():
    """chave -> (status, url, titulo) da lista de aquisição do RSL1."""
    out = {}
    if not os.path.exists(RSL1):
        return out
    with open(RSL1, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            st = (r.get("status") or "").strip()
            au = (r.get("autor") or "").strip()
            an = (r.get("ano") or "").strip()
            if not au or not an:
                continue
            out[chave(primeiro_sobrenome(au), an)] = (st, (r.get("url") or "").strip(),
                                                     (r.get("titulo") or "").strip())
    return out

def sem_via_de_acesso(url):
    u = (url or "").strip().lower()
    if not u:
        return True
    return ("sem url" in u) or (u in ("repositório usp", "repositorio usp"))


BIB = os.path.join(_RAIZ, "05 - Referências", "_zotero", "biblioteca.bib")
_STOP = set("de da do das dos e a o as os um uma no na nos nas em para por com the of and in on to "
            "urbano urbana publico publica transporte cidade brasil".split())

def _campo(e, nome):
    m = re.search(r"\b%s\s*=\s*" % nome, e, re.I)
    if not m:
        return ""
    i = m.end()
    while i < len(e) and e[i] in " \t":
        i += 1
    if i >= len(e):
        return ""
    if e[i] in "{\"":
        op = e[i]; cl = "}" if op == "{" else '"'; d = 1; j = i+1
        while j < len(e) and d > 0:
            if e[j] == op and op == "{": d += 1
            elif e[j] == cl: d -= 1
            j += 1
        return e[i+1:j-1]
    j = i
    while j < len(e) and e[j] not in ",\n":
        j += 1
    return e[i:j].strip()

def _tokens(txt):
    txt = unicodedata.normalize("NFKD", str(txt))
    txt = "".join(c for c in txt if not unicodedata.combining(c)).lower()
    return {w for w in re.findall(r"[a-z]{4,}", txt) if w not in _STOP}

def ler_acervo():
    """(sobrenome+ano) -> lista de conjuntos de tokens de título, da biblioteca Zotero.

    O casamento exige sobrenome + ano E sobreposição de título, porque só
    sobrenome+ano contra 1.500 entradas produz falso positivo em série.
    """
    out = collections.defaultdict(list)
    if not os.path.exists(BIB):
        return out
    txt = io._io.open(BIB, encoding="utf-8", errors="replace").read() if hasattr(io, "_io") else open(BIB, encoding="utf-8", errors="replace").read()
    for e in txt.split("\n@"):
        au = _campo(e, "author"); an = _campo(e, "year") or _campo(e, "date")
        ti = _campo(e, "title")
        m = re.search(r"((?:19|20)\d{2})", str(an))
        if not au or not m:
            continue
        primeiro = au.split(" and ")[0].strip()
        sob = primeiro.split(",")[0].strip() if "," in primeiro else (primeiro.split()[-1] if primeiro.split() else "")
        if not sob:
            continue
        out[chave(sob, m.group(1))].append(_tokens(ti))
    return out

# ---------------------------------------------------------------- classificação
def classificar(chaves, corpus_por_chave, fichados, e1, acervo=None, refs_txt=None):
    """chave da rede -> categoria + motivo."""
    cat, motivo = {}, {}
    refs_txt = refs_txt or {}
    for k in chaves:
        base = norm(re.sub(r"((?:19|20)\d{2}[a-z]?|sd)$", "", k))
        ano  = re.search(r"((?:19|20)\d{2})", k)
        kk   = chave(base, ano.group(1)) if ano else norm(k)

        if kk in INACESSIVEL or k in INACESSIVEL:
            cat[k] = "inacessível"; motivo[k] = INACESSIVEL.get(kk) or INACESSIVEL.get(k); continue
        if kk in fichados or k in fichados:
            cat[k] = "fichado"; motivo[k] = fichados.get(kk) or fichados.get(k); continue
        if kk in corpus_por_chave or k in corpus_por_chave:
            r = corpus_por_chave.get(kk) or corpus_por_chave.get(k)
            if (r.get("estado") or "").strip() == "fichado":
                cat[k] = "fichado"; motivo[k] = "corpus, item %s" % r["id"]
            else:
                cat[k] = "corpus não fichado"; motivo[k] = "corpus, item %s (%s)" % (r["id"], r.get("estado") or "sem estado")
            continue
        if acervo is not None and kk in acervo:
            tk = _tokens(refs_txt.get(k, ""))
            if any(len(tk & t) >= 2 for t in acervo[kk]):
                cat[k] = "no acervo, sem ficha"
                motivo[k] = "biblioteca.bib — referência catalogada, sem nota de leitura"
                continue
        if kk in e1:
            st, url, tit = e1[kk]
            U = st.upper()
            if U.startswith(("FICHADO", "JA_FICHADO")):
                cat[k] = "fichado"; motivo[k] = "RSL1: %s" % st
            elif U.startswith(("FORA", "JA_CORPUS")):
                # triado e excluído por critério — NÃO é falta de acesso
                cat[k] = "fora do escopo"; motivo[k] = "RSL1: %s" % st
            elif U.startswith(("PEGAR", "REFERENCIAL", "VERIFICAR")):
                if sem_via_de_acesso(url) or "503" in st:
                    cat[k] = "inacessível"; motivo[k] = "RSL1: %s — sem via de acesso registrada" % st
                else:
                    cat[k] = "a adquirir"; motivo[k] = "RSL1: %s — %s" % (st, url[:60])
            else:
                cat[k] = "não avaliado"; motivo[k] = "RSL1: %s" % st
            continue
        cat[k] = "não avaliado"; motivo[k] = ""
    return cat, motivo

# ---------------------------------------------------------------- desenho
def largura_texto(t, fs):
    return rv.largura_texto(t, fs)

def desenhar(caminho, nos, pos, peso, cat, rot, titulo, subtitulo, nota,
             sim, contagem, rodape_fonte="", W=1600, H=1080):
    esc = rv.esc
    M, TOP, BOT = 86, 112, 168
    xs = [pos[u][0] for u in nos]; ys = [pos[u][1] for u in nos]
    x0, x1 = min(xs), max(xs); y0, y1 = min(ys), max(ys)
    s = min((W-2*M)/((x1-x0) or 1), (H-TOP-BOT)/((y1-y0) or 1)) * 0.94
    ox = M + ((W-2*M)-(x1-x0)*s)/2; oy = TOP + ((H-TOP-BOT)-(y1-y0)*s)/2
    def T(u):
        x, y = pos[u]; return (ox+(x-x0)*s, oy+(y1-y)*s)
    pmax = max(peso.values()) or 1
    def raio(u):  return 4.5 + 17.0*math.sqrt(peso[u]/pmax)
    def fonte(u): return 10.0 + 11.0*math.sqrt(peso[u]/pmax)

    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (W,H,W,H),
         '<rect width="%d" height="%d" fill="#ffffff"/>' % (W,H),
         '<style>text{font-family:Aptos,Calibri,"Segoe UI",Helvetica,Arial,sans-serif}</style>',
         '<defs><pattern id="hach" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">'
         '<rect width="6" height="6" fill="#ffffff"/><line x1="0" y1="0" x2="0" y2="6" stroke="#c0392b" stroke-width="2.6"/>'
         '</pattern></defs>']
    o.append('<text x="%d" y="48" font-size="23" font-weight="700" fill="#111111">%s</text>' % (M, esc(titulo)))
    o.append('<text x="%d" y="74" font-size="13.5" fill="#555555">%s</text>' % (M, esc(subtitulo)))

    # arestas — cinza neutro, para que a cor signifique só o estado
    ares = sorted(((k, v) for k, v in sim.items() if k[0] in peso and k[1] in peso), key=lambda kv: kv[1])
    smax = max((v for _, v in ares), default=1)
    for (a, b), v in ares:
        (xa, ya), (xb, yb) = T(a), T(b)
        mxp, myp = (xa+xb)/2, (ya+yb)/2
        dx, dy = xb-xa, yb-ya; L = math.hypot(dx, dy) or 1
        cxp, cyp = mxp-dy/L*L*0.07, myp+dx/L*L*0.07
        t = v/smax
        o.append('<path d="M%.1f,%.1f Q%.1f,%.1f %.1f,%.1f" fill="none" stroke="#9aa7b4" '
                 'stroke-width="%.2f" opacity="%.2f"/>' % (xa, ya, cxp, cyp, xb, yb, 0.6+3.0*t, 0.16+0.34*t))

    # nós — inacessível recebe tratamento visual próprio (anel hachurado)
    for u in sorted(nos, key=lambda z: peso[z]):
        x, y = T(u); r = raio(u); c = COR[cat[u]]
        if cat[u] == "inacessível":
            o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="url(#hach)" stroke="%s" '
                     'stroke-width="2.4"/>' % (x, y, r, c))
            d = r*0.62
            o.append('<path d="M%.1f,%.1f L%.1f,%.1f M%.1f,%.1f L%.1f,%.1f" stroke="%s" '
                     'stroke-width="2.2" stroke-linecap="round"/>' % (x-d, y-d, x+d, y+d, x-d, y+d, x+d, y-d, c))
        else:
            o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" fill-opacity="0.62" '
                     'stroke="%s" stroke-opacity="0.9" stroke-width="1.0"/>' % (x, y, r, c, c))

    # rótulos com supressão de sobreposição
    caixas = []
    def cabe(bx):
        for c in caixas:
            if not (bx[2] < c[0] or bx[0] > c[2] or bx[3] < c[1] or bx[1] > c[3]):
                return False
        return True
    for u in sorted(nos, key=lambda z: -peso[z]):
        x, y = T(u); fs = fonte(u); txt = rot[u]
        w = largura_texto(txt, fs); h = fs*1.15
        bx = (x-w/2-6, y-h/2-4, x+w/2+6, y+h/2+4)
        if not cabe(bx):
            continue
        caixas.append(bx); yy = y+fs*0.35
        o.append('<text x="%.1f" y="%.1f" font-size="%.1f" font-weight="600" text-anchor="middle" '
                 'fill="none" stroke="#ffffff" stroke-width="%.1f" stroke-linejoin="round" opacity="0.92">%s</text>'
                 % (x, yy, fs, max(2.0, fs*0.30), esc(txt)))
        o.append('<text x="%.1f" y="%.1f" font-size="%.1f" font-weight="600" text-anchor="middle" '
                 'fill="#1a1a1a">%s</text>' % (x, yy, fs, esc(txt)))

    # legenda
    ly = H-BOT+34; lx = M
    o.append('<text x="%d" y="%d" font-size="12" font-weight="700" fill="#333333">estado de aquisição</text>' % (M, ly-16))
    for nome in CATS:
        n = contagem.get(nome, 0)
        if not n:
            continue
        c = COR[nome]
        if nome == "inacessível":
            o.append('<circle cx="%.0f" cy="%.0f" r="7" fill="url(#hach)" stroke="%s" stroke-width="2"/>' % (lx+7, ly, c))
        else:
            o.append('<circle cx="%.0f" cy="%.0f" r="7" fill="%s" fill-opacity="0.85" stroke="#ffffff" stroke-width="1.2"/>' % (lx+7, ly, c))
        txt = "%s (%d)" % (nome, n)
        o.append('<text x="%.0f" y="%.1f" font-size="11.5" fill="#333333">%s</text>' % (lx+20, ly+4.5, esc(txt)))
        lx += largura_texto(txt, 11.5)+42
        if lx > W-320:
            lx = M; ly += 24
    o.append('<text x="%d" y="%d" font-size="10.5" fill="#6a6a6a">%s</text>' % (M, H-32, esc(nota)))
    if rodape_fonte:
        o.append('<text x="%d" y="%d" font-size="10.5" fill="#6a6a6a">%s</text>' % (M, H-14, esc(rodape_fonte)))
    o.append("</svg>")
    open(caminho, "w", encoding="utf-8", newline="\n").write("\n".join(o))
    print("gravado:", os.path.basename(caminho), len(nos), "nós")


# ---------------------------------------------------------------- figura 3
def mapa_aquisicao(caminho, linhas, W=1600, H=None):
    """Mapa do estrato RSL1 por estado de aquisição.

    NÃO é uma rede: as obras ainda não lidas não têm lista de referências
    extraída e, portanto, não têm arestas. A figura existe justamente porque
    o item INACESSÍVEL não pode aparecer num mapa de cocitação — Cadaval (1993)
    não é citado por nenhum item do corpus.
    """
    esc = rv.esc
    M, TOP, BOT = 86, 122, 92
    cols = [c for c in CATS if any(r["cat"] == c for r in linhas)]
    if H is None:
        maior = max((sum(1 for r in linhas if r["cat"] == c) for c in cols), default=0)
        H = max(430, TOP + 46 + maior*18 + BOT)
    n = len(cols) or 1
    cw = (W - 2*M) / n
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (W,H,W,H),
         '<rect width="%d" height="%d" fill="#ffffff"/>' % (W,H),
         '<style>text{font-family:Aptos,Calibri,"Segoe UI",Helvetica,Arial,sans-serif}</style>',
         '<defs><pattern id="hach3" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">'
         '<rect width="6" height="6" fill="#ffffff"/><line x1="0" y1="0" x2="0" y2="6" stroke="#c0392b" stroke-width="2.6"/>'
         '</pattern></defs>',
         '<text x="%d" y="48" font-size="23" font-weight="700" fill="#111111">%s</text>'
         % (M, esc("Mapa de aquisição do estrato RSL1 — o que temos, o que falta, o que não alcançamos")),
         '<text x="%d" y="74" font-size="13.5" fill="#555555">%s</text>'
         % (M, esc("Cada ponto é uma obra identificada na varredura da BDTD (03/09/2026). "
                   "Não é uma rede: obras ainda não lidas não têm referências extraídas e por isso não têm arestas.")),
         '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#dddddd" stroke-width="1"/>' % (M, TOP-16, W-M, TOP-16)]
    for i, c in enumerate(cols):
        itens = [r for r in linhas if r["cat"] == c]
        itens.sort(key=lambda r: (r.get("prio",""), r["rot"]))
        x = M + i*cw
        o.append('<rect x="%.0f" y="%d" width="%.0f" height="26" fill="%s" fill-opacity="0.13"/>' % (x, TOP-8, cw-14, COR[c]))
        o.append('<circle cx="%.0f" cy="%d" r="6.5" fill="%s" fill-opacity="0.9"/>' % (x+16, TOP+5, COR[c]))
        o.append('<text x="%.0f" y="%d" font-size="13" font-weight="700" fill="#222222">%s (%d)</text>'
                 % (x+29, TOP+10, esc(c), len(itens)))
        y = TOP + 46
        for r in itens:
            if y > H-BOT-8:
                o.append('<text x="%.0f" y="%.0f" font-size="11" fill="#777777">%s</text>'
                         % (x+29, y, esc("… e mais %d" % (len(itens)-((y-TOP-46)//18)))))
                break
            if c == "inacessível":
                o.append('<circle cx="%.0f" cy="%.0f" r="5.5" fill="url(#hach3)" stroke="%s" stroke-width="2"/>' % (x+16, y-4, COR[c]))
                d = 3.4
                o.append('<path d="M%.1f,%.1f L%.1f,%.1f M%.1f,%.1f L%.1f,%.1f" stroke="%s" stroke-width="1.8" stroke-linecap="round"/>'
                         % (x+16-d, y-4-d, x+16+d, y-4+d, x+16-d, y-4+d, x+16+d, y-4-d, COR[c]))
            else:
                o.append('<circle cx="%.0f" cy="%.0f" r="5.5" fill="%s" fill-opacity="0.62" stroke="%s" stroke-width="1"/>'
                         % (x+16, y-4, COR[c], COR[c]))
            txt = r["rot"]
            mx = int((cw-58)/5.7)
            if len(txt) > mx: txt = txt[:mx-1]+"…"
            o.append('<text x="%.0f" y="%.0f" font-size="11" fill="#333333">%s</text>' % (x+29, y, esc(txt)))
            y += 18
    o.append('<text x="%d" y="%d" font-size="10.5" fill="#6a6a6a">%s</text>'
             % (M, H-52, esc("Universo: %d obras da lista de aquisição do RSL1 (BDTD) mais os itens do corpus nela registrados. "
                             "Levantamento em %s." % (len(linhas), DATA))))
    o.append('<text x="%d" y="%d" font-size="10.5" fill="#6a6a6a">%s</text>'
             % (M, H-34, esc("Inacessível = obra identificada, com existência confirmada, e sem via de acesso conhecida na data.")))
    o.append('<text x="%d" y="%d" font-size="10.5" fill="#6a6a6a">%s</text>'
             % (M, H-16, esc("Fonte: Elaboração do autor, a partir de E1_BDTD_lista_de_aquisicao.csv, corpus_rsl.csv e dos fichamentos do cofre.")))
    o.append("</svg>")
    open(caminho, "w", encoding="utf-8", newline="\n").write("\n".join(o))
    print("gravado:", os.path.basename(caminho), len(linhas), "obras")

# ---------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    fichados = ler_fichados()
    e1       = ler_e1()
    corpus   = rv.ler_corpus()
    corpus_por_chave = {}
    for r in corpus.values():
        corpus_por_chave[chave(primeiro_sobrenome(r["autores"]), r["ano"])] = r
        for alt in (r.get("chaves_alternativas") or "").split(","):
            if alt.strip():
                corpus_por_chave[norm(alt)] = r

    relat = []

    # ---------- 1. cocitação de referências externas, por estado ----------
    nos, pesos, forca, peso, rot, ano, ncomp, nitens = rv.rede_cocitacao(minimo=2)
    sim = rv.normalizar(pesos, forca)
    pos = rv.vos_layout(nos, sim)
    _refs = rv.ler_refs()
    acervo = ler_acervo()
    cat, motivo = classificar(nos, corpus_por_chave, fichados, e1, acervo,
                              {k: v.get('referencia','') for k, v in _refs.items()})
    cont = collections.Counter(cat.values())
    desenhar(os.path.join(OUT, "Rede de cocitacao por estado de aquisicao - RSL (set-2026).svg"),
             nos, pos, peso, cat, rot,
             "Cocitação de referências — por estado de aquisição",
             "Referências citadas por 2 ou mais itens do corpus da RSL. Tamanho do nó = nº de itens que a citam; "
             "proximidade = cocitação normalizada (força de associação).",
             "Nós: %d de %d referências distintas · componente gigante · layout VOS (van Eck e Waltman) · levantamento em %s."
             % (len(nos), len(rv.ler_refs()), DATA),
             sim, cont,
             "Fonte: Elaboração do autor, a partir de corpus_rsl.csv, citacoes_completas.csv, "
             "dos fichamentos do cofre e da lista de aquisição do estrato RSL1 (BDTD).")
    relat.append(("Cocitação de referências (nós com 2+ citações)", nos, cat, motivo, peso, rot))

    # ---------- 2. citações internas do corpus, por estado ----------
    nos2, pares, grau, peso2, rot2, ano2, corp = rv.rede_interna()
    sim2 = rv.normalizar(pares, grau)
    pos2 = rv.vos_layout(nos2, sim2)
    cat2, motivo2 = {}, {}
    for i in nos2:
        r = corp[i]
        est = (r.get("estado") or "").strip()
        k = chave(primeiro_sobrenome(r["autores"]), r["ano"])
        if est == "fichado" or k in fichados:
            cat2[i] = "fichado";            motivo2[i] = "item %s do corpus" % i
        else:
            cat2[i] = "corpus não fichado"; motivo2[i] = "item %s — estado: %s" % (i, est or "sem estado")
    cont2 = collections.Counter(cat2.values())
    desenhar(os.path.join(OUT, "Rede de citacoes internas por estado de aquisicao - RSL (set-2026).svg"),
             nos2, pos2, peso2, cat2, rot2,
             "Citações internas do corpus — por estado de aquisição",
             "Itens do corpus da RSL que citam ou são citados por outro item do corpus. "
             "Tamanho do nó = grau (citações trocadas dentro do corpus).",
             "Nós: %d itens do corpus com ao menos uma citação interna · layout VOS · levantamento em %s." % (len(nos2), DATA),
             sim2, cont2,
             "Fonte: Elaboração do autor, a partir de corpus_rsl.csv e citacoes_completas.csv.")
    relat.append(("Citações internas do corpus", nos2, cat2, motivo2, peso2, rot2))

    # ---------- 3. mapa de aquisição do RSL1 (carrega os inacessíveis) ----------
    linhas = []
    with open(RSL1, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            au = (r.get("autor") or "").strip(); an = (r.get("ano") or "").strip()
            if not au or not an:
                continue
            st = (r.get("status") or "").strip(); U = st.upper(); url = (r.get("url") or "").strip()
            k = chave(primeiro_sobrenome(au), an)
            if U.startswith(("FICHADO", "JA_FICHADO")) or k in fichados:
                c = "fichado"
            elif U.startswith("JA_CORPUS"):
                c = "corpus não fichado"
            elif U.startswith("FORA"):
                c = "fora do escopo"
            elif U.startswith(("PEGAR", "VERIFICAR", "REFERENCIAL")):
                c = "inacessível" if (sem_via_de_acesso(url) or "503" in st) else "a adquirir"
            else:
                c = "não avaliado"
            sob = primeiro_sobrenome(au)
            sob = sob[:1].upper() + sob[1:].lower() if sob.isupper() else sob
            frag = re.split(r"[:;.\u2014-]", (r.get("titulo") or ""))[0].strip()
            frag = " ".join(frag.split()[:3])
            rot = "%s, %s" % (sob, an)
            if frag:
                rot += " — %s" % frag
            linhas.append({"cat": c, "prio": (r.get("prioridade") or ""), "rot": rot,
                           "_k": (c, rot)})
    vistos = set(); dedup = []
    for r in linhas:
        if r["_k"] in vistos:
            continue
        vistos.add(r["_k"]); dedup.append(r)
    linhas = dedup
    mapa_aquisicao(os.path.join(OUT, "Mapa de aquisicao do estrato RSL1 por estado - RSL (set-2026).svg"), linhas)
    relat.append(("Mapa de aquisição do estrato RSL1", [i for i, _ in enumerate(linhas)],
                  {i: r["cat"] for i, r in enumerate(linhas)},
                  {i: r["prio"] for i, r in enumerate(linhas)},
                  {i: 1 for i, _ in enumerate(linhas)},
                  {i: r["rot"] for i, r in enumerate(linhas)}))

    # ---------- relatório ----------
    L = ["---", 'title: "Estado de aquisição no mapa bibliométrico (gerado)"',
         "tags: [rsl-tz, bibliometria, aquisicao, gerado]", "publish: false",
         "created: %s" % datetime.date.today().isoformat(), "---", "",
         "# Estado de aquisição no mapa bibliométrico", "",
         "> **Gerado por `_meta/scripts/rede_estado_aquisicao.py`. Não editar à mão — a próxima execução sobrescreve.**",
         "> Duas figuras em `_attachments/`, e abaixo as listas nominais por categoria.", "",
         "**Precedência das categorias:** inacessível → fichado → corpus → lista de aquisição do RSL1 → não avaliado.", "",
         "> ⚠️ **Limites declarados desta classificação.** O casamento entre um nó da rede e uma obra do cofre é feito por "
         "**primeiro sobrenome + ano**, extraídos do nome do arquivo de fichamento e das colunas de autoria. "
         "Isso produz **falsos negativos** em três situações conhecidas: nomes compostos grafados de forma diferente "
         "nas duas pontas; obras citadas com ano divergente do ano canônico; e o travessão de continuação ABNT, cujo ano "
         "pode vir do título e não da imprenta (ver o limite residual registrado no LEIA-ME da pasta). "
         "🔴 **\"Não avaliado\" significa que a obra não foi triada NEM casada — não que o cofre não a tenha.** "
         "✅ **Conferir nominalmente antes de usar a contagem como medida.**",
         "",
         "> ⚠️ **E \"fichado\" aqui significa existir nota de leitura, não possuir o arquivo.** Várias obras do "
         "`Corpus Tarifa Zero (índice)` têm PDF e não têm fichamento — aparecem como não avaliadas.", ""]
    for titulo, ns, cc, mm, pp, rr in relat:
        L += ["## %s" % titulo, ""]
        cont = collections.Counter(cc.values())
        L += ["| categoria | nós |", "|---|---|"]
        for c in CATS:
            if cont.get(c):
                L.append("| %s | %d |" % (c, cont[c]))
        L.append("")
        for c in CATS:
            itens = [u for u in ns if cc[u] == c]
            if not itens:
                continue
            itens.sort(key=lambda u: (-pp[u], rr[u]))
            L += ["### %s (%d)" % (c, len(itens)), "",
                  "| obra | peso | observação |", "|---|---|---|"]
            for u in itens:
                L.append("| %s | %s | %s |" % (rr[u], pp[u], (mm.get(u) or "").replace("|", "/")))
            L.append("")
    io = open(os.path.join(DIR, "Estado de aquisição no mapa bibliométrico (gerado).md"), "w", encoding="utf-8")
    io.write("\n".join(L)); io.close()
    print("gravado: Estado de aquisição no mapa bibliométrico (gerado).md")

if __name__ == "__main__":
    main()
