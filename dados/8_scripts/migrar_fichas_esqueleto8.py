#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""migrar_fichas_esqueleto8.py — leva as fichas municipais do esqueleto antigo
(5 seções numeradas + blocos soltos) para o esqueleto de 8 blocos validado em
São Caetano do Sul e Maricá (21/09/2026), e já insere o Bloco 2 em prosa.

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni
Escrito em 25/09/2026. Rodar na máquina do autor (sem limite de tempo).

======================================================================
O QUE ELE FAZ (e o que NÃO faz)
======================================================================
FAZ — reorganização estrutural, sem reescrever conteúdo do autor:
  1. H1 limpo: "# 🏙️ X — UF · Ficha de Tarifa Zero" -> "# X — UF".
  2. Esqueleto na ordem exata de SCS/Maricá:
       ## 1. Briefing · ## 2. Principais dados · ## 3. Contexto da mobilidade
       ## 4. Transporte coletivo · ## 5. Classificação (### Régua descritiva,
       ### Régua analítica) · ## 6. Grupos econômicos
       ## 7. RSL, notícias e legislação/contratos (### Revisão sistemática da
       literatura (RSL), ### Notícias, ### Legislação e contratos)
       ## 8. Literatura e bibliografia (### Fontes e literatura sobre o caso,
       ### Dados NTU, ### Referências (formato ABNT))
       ## Pendências · ## Fichamentos e notas relacionadas
  3. Bloco 2 em prosa (gerador `enriquecer_prosa_municipal.py`, importado): o
     antigo "## 2. Principais dados" (fatos da política de TZ: situação,
     operador, frota) vira o começo do Bloco 4, como em Maricá. Se o gerador
     não achar o município na base, o antigo "### Perfil socioeconômico" é
     mantido como Bloco 2 (nada se perde).
  4. Blocos gerados com marcador (<!-- prosa:... -->) são movidos INTACTOS
     (mesmo hash) — o `enriquecer_prosa_municipal.py` continua reconhecendo
     e atualizando-os depois.
  5. Regras-padrão do autor: corta "## Dados quantitativos" (simulação
     CTP/CTPU) e a linha "Frota de ônibus (DENATRAN/SENATRAN)"; "—" vira
     "não apurado" nos campos do antigo Bloco 2 (NA ≠ 0).
  6. Wikilinks do corpo (blocos 1-8) viram texto simples e vão para
     "## Fichamentos e notas relacionadas". Embeds (![[...]]) ficam.
  7. Auditoria/alertas, trilha do portão (enriquecer_regua_portao.py) e
     listas de pendência vão para "## Pendências". Bloco sem conteúdo recebe
     "Não apurado (ver Pendências)." no corpo e um item em Pendências.
  8. Seção que não se encaixa em nenhum bloco é preservada, como ###, no fim
     do Bloco 5, e listada no relatório para você realocar à mão.

NÃO FAZ:
  - Não converte bullets em prosa nos blocos de pesquisa de caso (1, 4, régua
    analítica, 6, 7, 8) — isso não é mecanizável; fica em lista, na posição
    certa.
  - Não mexe no frontmatter.
  - Não toca fichas que já estão no esqueleto novo (SCS, Maricá).

======================================================================
COMO RODAR (na raiz do cofre ou de qualquer lugar)
======================================================================
  python _meta/scripts/migrar_fichas_esqueleto8.py
      -> SIMULA. Relatório no terminal + prévias em _meta/_scratch/migracao8/.
  python _meta/scripts/migrar_fichas_esqueleto8.py --municipio "Taquarituba" SP
      -> simula e imprime a ficha migrada de um município.
  python _meta/scripts/migrar_fichas_esqueleto8.py --gravar
      -> grava todas, com backup em _meta/_backups/migracao8-AAAA-MM-DD_HHMM/.
  python _meta/scripts/migrar_fichas_esqueleto8.py --gravar --com-prosa
      -> grava e depois roda enriquecer_prosa_municipal.py --gravar (atualiza
         Bloco 3 e Régua descritiva com os dados atuais da mestre/régua; só
         reescreve blocos que ninguém editou à mão — proteção por hash).
  Opções: --pular-stubs (não migra as fichas-stub da RSL, tag ficha-auto-rsl).

DEPOIS DE MIGRAR — atenção aos geradores antigos:
  NÃO rodar de novo enriquecer_contexto_mobilidade.py,
  enriquecer_perfil_socioeconomico.py, enriquecer_fichas_municipais.py,
  enriquecer_regua_portao.py nem enriquecer_fichas_rsl.py nas fichas
  migradas: eles recriariam as seções antigas que o Bloco 2/3 em prosa
  substituiu. enriquecer_grupos_economicos.py é seguro (reconhece
  "## 6. Grupos econômicos"). O gerador vigente é enriquecer_prosa_municipal.py.
  Rodar o auditor ao fim: python _meta/scripts/auditar_cofre.py --report
"""
import argparse
import datetime
import glob
import os
import re
import shutil
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(HERE, "..", ".."))
os.environ.setdefault("TZ_VAULT", RAIZ)
FICHAS_DIR = os.path.join(RAIZ, "04 - Análises", "Casos municipais", "Fichas por município")
PREVIA_DIR = os.path.join(RAIZ, "_meta", "_scratch", "migracao8")

NA = "Não apurado (ver Pendências)."
MARK_RE = re.compile(r"<!-- prosa:(\w+):inicio hash:[0-9a-f]+[^>]*-->\n.*?\n<!-- prosa:\1:fim -->", re.S)
WIKI_RE = re.compile(r"(?<!!)\[\[([^\]|#]+)(#[^\]|]*)?(?:\|([^\]]+))?\]\]")


# ------------------------------------------------------------------ utilidades
def norm(h):
    h = h.lstrip("#").strip()
    h = unicodedata.normalize("NFKD", h).encode("ascii", "ignore").decode().lower()
    h = re.sub(r"[^a-z0-9 ]", " ", h)
    h = re.sub(r"\s+", " ", h).strip()
    h = re.sub(r"^\d+[a-z]?\s+", "", h)
    return h


def rebaixar(body, n=1):
    """### -> #### (n níveis), sem passar de ######."""
    def f(m):
        return "#" * min(6, len(m.group(1)) + n) + " "
    return re.sub(r"(?m)^(#{2,5}) ", f, body)


def limpar_wikilinks(body, coletor):
    def f(m):
        alvo, alias = m.group(1).strip(), m.group(3)
        coletor.append(alvo)
        return (alias or alvo).strip()
    return WIKI_RE.sub(f, body)


def vazio(body):
    t = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    t = re.sub(r"(?m)^\s*[-*]\s*$", "", t)
    return len(t.strip()) < 3


def placeholder_so(body):
    """Seção só com 'não documentado/não verificado/a classificar'."""
    linhas = [l for l in body.splitlines() if l.strip()]
    if not linhas:
        return True
    return all(re.search(r"n[ãa]o documentad|n[ãa]o verificad|n[ãa]o apurad|a classificar|dado insuficiente", l, re.I)
               for l in linhas)


def na_nos_campos(body):
    body = re.sub(r"(\*\*[^*\n]+:\*\*)\s*[—–-]\s*(/\s*[—–-]\s*)*$", r"\1 não apurado", body, flags=re.M)
    body = re.sub(r"(\*\*[^*\n]+:\*\*)\s*[—–-]\s*·", r"\1 não apurado ·", body, flags=re.M)
    return body


def dividir_subsecoes(body):
    """-> (texto_antes_do_primeiro_###, [(titulo, corpo), ...])"""
    partes = re.split(r"(?m)^(?=### )", body)
    antes = partes[0]
    subs = []
    for p in partes[1:]:
        tit, _, corpo = p.partition("\n")
        subs.append((tit, corpo))
    return antes, subs


# ------------------------------------------------------------------ parsing
def separar(txt):
    fm = ""
    if txt.startswith("---\n"):
        fim = txt.find("\n---\n", 4)
        if fim > 0:
            fm, txt = txt[:fim + 5], txt[fim + 5:]
    marcados = {}
    for m in MARK_RE.finditer(txt):
        marcados[m.group(1)] = m.group(0)
    txt = MARK_RE.sub("", txt)
    partes = re.split(r"(?m)^(?=## )", txt)
    preambulo = partes[0]
    secoes = []
    for p in partes[1:]:
        tit, _, corpo = p.partition("\n")
        secoes.append((tit.rstrip(), corpo.strip("\n")))
    return fm, preambulo, marcados, secoes


def classificar(tit):
    n = norm(tit)
    regras = [
        ("B1", ("briefing",)),
        ("OLD2", ("principais dados",)),
        ("B3", ("contexto da mobilidade",)),
        ("B4", ("transporte coletivo",)),
        ("B5", ("classificacao",)),
        ("PORTAO", ("regua descritiva",)),
        ("RA", ("regua analitica",)),
        ("FAT", ("fatores impulsionadores",)),
        ("B6", ("grupos economicos",)),
        ("RSL", ("literatura da rsl", "revisao sistematica")),
        ("B7", ("rsl noticias",)),
        ("NOT", ("materias de jornais", "noticias")),
        ("CONTR", ("dados de contratacao",)),
        ("LEG", ("legislacao", "datacao")),
        ("BIB", ("bibliografia", "trabalhos que referenciam", "literatura e bibliografia")),
        ("NTU", ("dados ntu",)),
        ("CUT", ("dados quantitativos",)),
        ("PEND", ("auditoria", "pendencias", "pista a investigar", "lacunas de dado", "atualizacao")),
        ("LINKS", ("fichamentos", "ligacoes")),
    ]
    for chave, prefixos in regras:
        if any(n.startswith(p) for p in prefixos):
            return chave
    return "OTHER"


def ja_migrada(txt):
    return all(s in txt for s in ("\n## 4. Transporte coletivo", "\n## 5. Classificação", "\n## Fichamentos"))


def limpar_h1(preambulo):
    def f(m):
        t = m.group(1)
        t = re.sub(r"^[^\wÀ-ÿ]+", "", t)              # emoji/símbolos à esquerda
        t = re.sub(r"\s*·\s*Ficha de Tarifa Zero\s*$", "", t, flags=re.I)
        return "# " + t.strip()
    return re.sub(r"(?m)^# (.+)$", f, preambulo, count=1)


# ------------------------------------------------------------------ bloco 2
_GER = None


def gerador():
    global _GER
    if _GER is None:
        try:
            sys.path.insert(0, HERE)
            import enriquecer_prosa_municipal as epm
            df = epm.carregar_base()
            reg = epm.regua.carregar()
            _GER = (epm, df, reg)
        except Exception as e:  # sem pandas/base: segue sem Bloco 2 novo
            print(f"⚠️ gerador de prosa indisponível ({e}); Bloco 2 fica com o conteúdo antigo.")
            _GER = False
    return _GER


def bloco2_prosa(municipio, uf):
    g = gerador()
    if not g:
        return None
    epm, df, (portao, aba_de, sub, linhas, sit) = g
    b2, _b3, _rd, erro = epm.gerar_para_municipio(df, portao, aba_de, sub, linhas, sit, municipio, uf)
    if erro or not b2:
        return None
    return epm.envolver("bloco2", b2)


# ------------------------------------------------------------------ migração
COMPLEMENTOS_CONTEXTO = re.compile(r"Trajet[óo]ria institucional|Despesa com transporte|Emprego no setor", re.I)

# Seções próprias de alguns casos, sem bloco-padrão. Prefixo do título normalizado
# (sem acento/emoji/número, minúsculo) -> bloco de destino. Editável: o que não casar
# aqui vai para o fim do Bloco 5 e gera item em Pendências.
MAPA_OUTRAS = [
    ("entorno urbanistico", "B3"),                      # Araraquara — Censo por setor
    ("deslocamento para trabalho", "B3"),               # Araraquara — microdados
    ("cronologia", "B4"),                               # BH — trajetória da política
    ("reconciliacao das series de demanda", "B4"),      # Caucaia — demanda
    ("o contraste de corredor", "B6"),                  # Araraquara — mesmo grupo, dois regimes
    ("caso bh da tese", "B6"),                          # BH — grupos do consórcio
    ("o que as entrevistas mostram", "B6"),             # Viçosa — assimetria com o operador
    ("o que este caso falsifica", "B8"),                # 11 fichas — diálogo com a literatura causal
    ("o que foi medido", "B8"),                         # Fortaleza — estimativa causal
    ("o fundo de", "B5"),                               # Formosa × VGP — desenho do custeio (régua analítica)
    ("onde ", "B5"),                                    # Araraquara — posição no estrato
    ("explicacoes rivais", "B5"),                       # Viçosa — explicações rivais
]
NOME_BLOCO = {"B3": "Bloco 3", "B4": "Bloco 4", "B5": "Bloco 5", "B6": "Bloco 6", "B8": "Bloco 8"}


def titulo_limpo(tit):
    t = re.sub(r"^#+\s*", "", tit).strip()
    t = re.sub(r"^[^\wÀ-ÿ]+", "", t)                       # emoji à esquerda
    t = re.sub(r"^\d+[a-z]?\.\s*", "", t)                   # 5a. / 3.
    t = re.sub(r"^[^\wÀ-ÿ]+", "", t)
    t = re.sub(r"\s*[—–-]\s*reconstitu[íi]da em \d{2}/\d{2}/\d{4}", "", t)
    t = re.sub(r"\s*\(\d{2}/\d{2}/\d{4}\)", "", t)
    return t.strip()


def migrar(txt, municipio, uf, relatorio):
    fm, pre, marc, secoes = separar(txt)
    pre = limpar_h1(pre).rstrip() + "\n"
    links, pend, outros = [], [], []
    b = {k: [] for k in ("B1", "OLD2", "B3", "B4", "B5", "RA", "FAT", "B6", "RSL", "B7",
                         "NOT", "LEG", "CONTR", "BIB", "NTU", "PEND", "LINKS", "PORTAO")}
    perfil_antigo, complementos = "", []

    for tit, corpo in secoes:
        k = classificar(tit)
        if k == "CUT":
            relatorio["cortadas"] += 1
            continue
        if k == "OTHER":
            outros.append((tit, corpo))
            continue
        if k == "B1":
            antes, subs = dividir_subsecoes(corpo)
            resto = [antes.strip()]
            for st, sc in subs:
                ns = norm(st)
                if ns.startswith("contexto de mobilidade"):
                    complementos += [l for l in sc.splitlines() if COMPLEMENTOS_CONTEXTO.search(l)]
                elif ns.startswith("perfil socioeconomico"):
                    perfil_antigo = sc.strip()
                else:
                    resto.append(st + "\n" + sc)
            corpo = "\n\n".join(x for x in resto if x.strip())
        b[k].append((tit, corpo))

    extras = {k: [] for k in NOME_BLOCO}
    for tit, corpo in outros:
        n = norm(re.sub(r"^#+\s*\d+[a-z]?\.\s*", "", tit))
        destino = next((bl for pref, bl in MAPA_OUTRAS if n.startswith(pref)), None)
        tl = titulo_limpo(tit)
        extras[destino or "B5"].append((tl, corpo, destino is None))
        relatorio["outras"].append(f"{municipio} ({uf}): {tl} -> " + (NOME_BLOCO[destino] if destino else "fim do Bloco 5 (SEM REGRA — revisar)"))

    def extras_txt(k):
        return "\n\n".join(f"### {tl}\n\n{rebaixar(c, 1).strip()}" for tl, c, _ in extras[k])

    def junta(k, rebaixa=0, rotular_extras=True, nivel_rotulo="####"):
        """Corpo único; seções extras entram com o título original como sub-rótulo."""
        out = []
        for i, (tit, corpo) in enumerate(b[k]):
            c = rebaixar(corpo, rebaixa) if rebaixa else corpo
            if i > 0 and rotular_extras:
                t = re.sub(r"^#+\s*(\d+[a-z]?\.\s*)?", "", tit).strip()
                out.append(f"{nivel_rotulo} {t}\n\n{c.strip()}")
            else:
                out.append(c.strip())
        return "\n\n".join(x for x in out if x.strip())

    def corpo_limpo(s):
        return limpar_wikilinks(s, links) if s else s

    # ---- Bloco 1
    b1 = corpo_limpo(junta("B1", 1))
    # ---- Bloco 2
    b2 = marc.get("bloco2") or bloco2_prosa(municipio, uf)
    if b2:
        relatorio["bloco2_prosa"] += 1
    else:
        corpo2 = perfil_antigo or ""
        corpo2 = "\n".join(l for l in corpo2.splitlines() if not re.search(r"Frota de ônibus", l))
        b2 = "## 2. Principais dados\n\n" + (corpo2.strip() or NA)
        if not corpo2.strip():
            pend.append("- **Principais dados:** base municipal sem correspondência para este município — Bloco 2 não gerado.")
    # ---- Bloco 3
    if marc.get("bloco3"):
        b3 = marc["bloco3"]
        resid = junta("B3")
        if resid.strip():
            b3 += "\n\n" + corpo_limpo(resid)
    else:
        resid = junta("B3")
        b3 = "## 3. Contexto da mobilidade\n\n" + (corpo_limpo(resid) or NA)
        if not resid.strip():
            pend.append("- **Contexto da mobilidade:** bloco não gerado (rodar enriquecer_prosa_municipal.py --gravar).")
    if extras["B3"]:
        b3 += "\n\n" + corpo_limpo(extras_txt("B3"))
    # ---- Bloco 4
    old2 = junta("OLD2")
    old2 = "\n".join(l for l in old2.splitlines()
                     if not re.match(r"\s*-\s*\*\*Popula", l) and not re.search(r"Frota de ônibus \(DENATRAN", l))
    old2 = na_nos_campos(old2)
    comp = [l for l in complementos if not re.search(r"Frota de ônibus", l)]
    partes4 = [old2.strip()]
    if comp:
        partes4.append("\n".join(comp))
    partes4.append(junta("B4", 0))
    partes4.append(extras_txt("B4"))
    b4 = corpo_limpo("\n\n".join(x for x in partes4 if x.strip()))
    if not b4.strip():
        b4 = NA
        pend.append("- **Transporte coletivo — dados operacionais:** operador, frota, linhas e demanda não apurados.")
    elif "não apurado" in b4:
        pend.append("- **Transporte coletivo — dados operacionais:** campos marcados 'não apurado' no Bloco 4.")
    # ---- Bloco 5
    rd = marc.get("regua_descritiva") or ("### Régua descritiva\n\n" + NA)
    if "regua_descritiva" not in marc:
        pend.append("- **Classificação — régua descritiva:** parágrafo não gerado (rodar enriquecer_prosa_municipal.py --gravar).")
    ra = junta("RA", 1)
    fat = junta("FAT", 1)
    if fat and not placeholder_so(fat):
        ra = (ra + "\n\n" if ra else "") + "Fatores impulsionadores/limitantes registrados:\n\n" + fat
    if not ra.strip():
        ra = NA
        pend.append("- **Classificação — régua analítica:** tipologia, custeio e remuneração não apurados.")
    elif placeholder_so(ra):
        pend.append("- **Classificação — régua analítica:** tipologia, custeio e remuneração não apurados.")
    extra5 = junta("B5", 0)
    for tl, corpo, sem_regra in extras["B5"]:
        extra5 += f"\n\n### {tl}\n\n{rebaixar(corpo, 1).strip()}"
        if sem_regra:
            pend.append(f"- **Estrutura:** a seção “{tl}” não tinha bloco correspondente e foi preservada no fim do Bloco 5 — revisar posição.")
    b5 = corpo_limpo(f"{rd}\n\n### Régua analítica\n\n{ra.strip()}" + (f"\n\n{extra5.strip()}" if extra5.strip() else ""))
    # ---- Bloco 6
    b6 = corpo_limpo("\n\n".join(x for x in (junta("B6", 0), extras_txt("B6")) if x.strip()))
    if not b6.strip():
        b6 = NA
        pend.append("- **Grupos econômicos:** sem registro na base de CNPJ para este município.")
    # ---- Bloco 7
    rsl = corpo_limpo(junta("RSL", 1)) or NA
    noti = corpo_limpo(junta("NOT", 1)) or NA
    leg = junta("LEG", 1)
    contr = junta("CONTR", 1)
    if contr:
        leg = (leg + "\n\n" if leg else "") + "#### Dados de contratação\n\n" + contr
    leg = corpo_limpo(leg) or NA
    b7_extra = corpo_limpo(junta("B7", 0))
    if rsl == NA:
        pend.append("- **RSL:** cobertura da literatura não registrada nesta ficha.")
    if noti == NA:
        pend.append("- **Notícias:** nenhuma matéria registrada.")
    if leg == NA:
        pend.append("- **Legislação e contratos:** nenhuma norma ou contrato registrado.")
    b7 = (f"### Revisão sistemática da literatura (RSL)\n\n{rsl}\n\n### Notícias\n\n{noti}\n\n"
          f"### Legislação e contratos\n\n{leg}" + (f"\n\n{b7_extra}" if b7_extra.strip() else ""))
    # ---- Bloco 8
    bib = corpo_limpo(junta("BIB", 1)) or NA
    ntu = corpo_limpo(junta("NTU", 1))
    b8 = f"### Fontes e literatura sobre o caso\n\n{bib}"
    if ntu.strip():
        b8 += f"\n\n### Dados NTU — dado de fonte citada\n\n{ntu}"
    if extras["B8"]:
        b8 += "\n\n" + corpo_limpo(extras_txt("B8"))
    b8 += "\n\n### Referências (formato ABNT)\n\n" + NA
    pend.append("- **Literatura e bibliografia — Referências ABNT:** ainda não compiladas (cruzar com biblioteca.bib).")
    # ---- Pendências (auditoria + trilha do portão + itens gerados)
    pend_txt = []
    for tit, corpo in b["PEND"]:
        t = re.sub(r"^#+\s*(\d+\.\s*)?", "", tit).strip()
        pend_txt.append(f"**{t} (conteúdo anterior):**\n\n{corpo.strip()}")
    for tit, corpo in b["PORTAO"]:
        pend_txt.append("**Régua descritiva — trilha do portão (registro gerado por enriquecer_regua_portao.py, a conferir):**\n\n"
                        + rebaixar(corpo.strip(), 1))
    pendencias = "\n".join(dict.fromkeys(pend))
    if pend_txt:
        pendencias += "\n\n" + "\n\n".join(pend_txt)
    # ---- Fichamentos
    links_antigos = junta("LINKS", 1, rotular_extras=False)
    uniq = list(dict.fromkeys(links))
    fich = links_antigos.strip()
    if uniq:
        fich += ("\n\n" if fich else "") + "Notas citadas no corpo desta ficha: " + " · ".join(f"[[{u}]]" for u in uniq)
    fich = fich or "—"

    novo = (fm + pre + "\n"
            + f"## 1. Briefing\n\n{b1.strip() or NA}\n\n"
            + b2.strip() + "\n\n"
            + b3.strip() + "\n\n"
            + f"## 4. Transporte coletivo\n\n{b4.strip()}\n\n"
            + f"## 5. Classificação\n\n{b5.strip()}\n\n"
            + f"## 6. Grupos econômicos\n\n{b6.strip()}\n\n"
            + f"## 7. RSL, notícias e legislação/contratos\n\n{b7.strip()}\n\n"
            + f"## 8. Literatura e bibliografia\n\n{b8.strip()}\n\n"
            + f"## Pendências\n\n{pendencias.strip()}\n\n"
            + f"## Fichamentos e notas relacionadas\n\n{fich.strip()}\n")
    novo = re.sub(r"\n{3,}", "\n\n", novo)
    # headings sempre precedidos de linha em branco (pandoc)
    novo = re.sub(r"([^\n>])\n(#{1,6} )", r"\1\n\n\2", novo)  # não separa o marcador <!-- prosa --> do título
    return novo


def conferir_perda(original, novo):
    """Heurística de segurança: nenhuma linha substantiva do original pode sumir,
    exceto as cortadas por regra (CTP/CTPU, frota DENATRAN, população duplicada,
    blocos antigos substituídos pela prosa)."""
    def linhas(t):
        t = WIKI_RE.sub(lambda m: (m.group(3) or m.group(1)).strip(), t)
        return {re.sub(r"\s+", " ", l).strip() for l in t.splitlines()
                if len(l.strip()) > 25 and not l.lstrip().startswith("#") and not l.startswith("<!--")}
    novo_n = WIKI_RE.sub(lambda m: (m.group(3) or m.group(1)).strip(), novo)
    novo_n = re.sub(r"[ \t]+", " ", novo_n)
    faltam = [l for l in linhas(original) if l not in novo_n]
    return faltam


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true")
    ap.add_argument("--com-prosa", action="store_true")
    ap.add_argument("--pular-stubs", action="store_true")
    ap.add_argument("--municipio", nargs=2, metavar=("MUNICIPIO", "UF"))
    ap.add_argument("--aceitar-perdas", action="store_true")
    a = ap.parse_args()

    arquivos = sorted(glob.glob(os.path.join(FICHAS_DIR, "Ficha - *.md")))
    if not arquivos:
        sys.exit(f"🔴 nenhuma ficha em {FICHAS_DIR}")
    rel = {"migradas": 0, "ja": 0, "stubs": 0, "cortadas": 0, "bloco2_prosa": 0, "outras": [], "perdas": {}}
    plano = []
    for path in arquivos:
        txt = open(path, encoding="utf-8").read()
        mm = re.search(r"^municipio:\s*(.+)$", txt, re.M)
        uu = re.search(r"^uf:\s*(.+)$", txt, re.M)
        if not (mm and uu):
            continue
        mun, uf = mm.group(1).strip().strip('"'), uu.group(1).strip().strip('"')
        if a.municipio and (mun.lower() != a.municipio[0].lower() or uf.upper() != a.municipio[1].upper()):
            continue
        if ja_migrada(txt):
            rel["ja"] += 1
            continue
        if a.pular_stubs and "ficha-auto-rsl" in txt:
            rel["stubs"] += 1
            continue
        novo = migrar(txt, mun, uf, rel)
        # descarta das "perdas" o que foi cortado por regra
        faltam = [l for l in conferir_perda(txt, novo)
                  if not re.search(r"CTP|CTPU|Frota de ônibus|Popula[çc][ãa]o|Simula[çc][ãa]o|folha|n[ãa]o documentad|:\*\*\s*[—–-]|[—–-] / [—–-]|"
                                   r"Modal split|Gest[ãa]o do transporte|Segurança viária \(2019\)|"
                                   r"Renda e desenvolvimento|Posi[çc][ãa]o na rede|Motoriza[çc][ãa]o|CadÚnico|"
                                   r"Faixas de renda|disjuntas|Renda m[ée]dia do trabalho|base_municipal_v3|"
                                   r"Emprego formal|Sal[áa]rio m[ée]dio|Informalidade|Ressalvas: mistura", l)]
        if faltam:
            rel["perdas"][os.path.basename(path)] = faltam
        plano.append((path, novo))
        rel["migradas"] += 1

    print(f"Fichas: {len(arquivos)} · a migrar: {rel['migradas']} · já no esqueleto novo: {rel['ja']} · stubs pulados: {rel['stubs']}")
    print(f"Bloco 2 em prosa: {rel['bloco2_prosa']} · seções 'Dados quantitativos' cortadas: {rel['cortadas']}")
    if rel["outras"]:
        print(f"\nSeções próprias de caso realocadas (MAPA_OUTRAS no topo do script): {len(rel['outras'])}")
        for o in rel["outras"][:40]:
            print("  -", o)
    if rel["perdas"]:
        print(f"\n⚠️ Linhas do original não reencontradas na versão migrada ({len(rel['perdas'])} fichas) — CONFERIR antes de gravar:")
        for f, ls in list(rel["perdas"].items())[:30]:
            print(f"  {f}: {len(ls)} linha(s) — ex.: {ls[0][:110]}")
    else:
        print("\n✅ Conferência de perda: nenhuma linha substantiva do original sumiu (fora os cortes por regra).")

    if a.municipio and plano:
        print("\n" + "=" * 70 + "\n" + plano[0][1])

    if not a.gravar:
        os.makedirs(PREVIA_DIR, exist_ok=True)
        for path, novo in plano[:400]:
            # prévia com sufixo .txt: não vira nota duplicada no Obsidian nem no auditor
            open(os.path.join(PREVIA_DIR, os.path.basename(path) + ".txt"), "w", encoding="utf-8", newline="\n").write(novo)
        print(f"\nSIMULAÇÃO — nada gravado nas fichas. Prévias em {os.path.relpath(PREVIA_DIR, RAIZ)}. Para aplicar: --gravar")
        return

    if rel["perdas"] and not a.aceitar_perdas:
        print("\n🔴 Há linhas não reencontradas (lista acima). Confira as prévias; para gravar mesmo assim, "
              "repita com --gravar --aceitar-perdas.")
        return
    bk = os.path.join(RAIZ, "_meta", "_backups", "migracao8-" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M"))
    os.makedirs(bk, exist_ok=True)
    for path, novo in plano:
        # backup com sufixo .bak (não cria nome de nota duplicado); newline="\n" evita CRLF no Windows
        shutil.copy2(path, os.path.join(bk, os.path.basename(path) + ".bak"))
        open(path, "w", encoding="utf-8", newline="\n").write(novo)
    print(f"\n✅ {len(plano)} fichas gravadas · backup em {os.path.relpath(bk, RAIZ)}")

    if a.com_prosa:
        import subprocess
        print("\n→ enriquecer_prosa_municipal.py --gravar (Bloco 3 + Régua descritiva com dados atuais)")
        subprocess.run([sys.executable, os.path.join(HERE, "enriquecer_prosa_municipal.py"), "--gravar"],
                       env=dict(os.environ, TZ_VAULT=RAIZ), check=False)
    print("\nPróximo passo: python _meta/scripts/auditar_cofre.py --report")


if __name__ == "__main__":
    main()
