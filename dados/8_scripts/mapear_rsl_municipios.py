#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mapear_rsl_municipios.py — cruza os fichamentos da RSL com os municípios
da base-mestre e mede QUANTO da literatura lida trata de cada caso.

SOMENTE LEITURA. Não escreve em ficha nenhuma. Saídas:
  04 - Análises/Cobertura da literatura por município (gerado).md
  05 - Referências/Rede bibliométrica/cobertura_literatura_municipios.csv

MÉTODO, e os seus limites, declarados:
  * casamento por LIMITE DE PALAVRA sobre o texto normalizado do fichamento;
  * nomes longos são mascarados antes dos curtos, para que "Vargem Grande
    Paulista" não conte também como "Vargem";
  * imprentas bibliográficas ("São Paulo: Boitempo", "Belo Horizonte, ano 8")
    são removidas antes da contagem — sem isso toda capital vira falso caso;
  * nomes que também são palavra comum ou parte de outro nome exigem marca
    de UF a até 40 caracteres da ocorrência;
  * três níveis: A objeto (nome em título de seção com >=3 menções, ou >=8
    menções) · B seção substantiva (>=3) · C menção de passagem (1-2).

⚠️ O que a medida NÃO é: ela conta menções nos FICHAMENTOS, que são notas de
leitura do autor, não nos textos originais. Um caso pode aparecer muito na
nota porque interessou ao leitor. O nível A/B/C é indício de cobertura, não
prova dela — conferir antes de afirmar que a obra "trata" do município.
"""
import csv, collections, glob, os, re, sys, unicodedata

R = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FICHAS = os.path.join(R, "04 - Análises", "Casos municipais", "Fichas por município")
NOTAS  = os.path.join(R, "05 - Referências", "Notas de leitura")
XLSX   = os.path.join(R, "03 - Dados", "_data", "casos por fonte", "Municípios TZ - consolidado.xlsx")
SAI_MD = os.path.join(R, "04 - Análises", "Cobertura da literatura por município (gerado).md")
SAI_CSV= os.path.join(R, "05 - Referências", "Rede bibliométrica", "cobertura_literatura_municipios.csv")

def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()
def NORM(s): return norm(s).upper()

# nomes que são palavra comum do português ou parte de outro topônimo:
# exigem marca de UF perto da ocorrência
EXIGE_UF = {"salto","palma","vargem","carmo","assis","arcos","machado","piedade","portao","tiete",
            "formosa","goias","vitoria","natividade","costa rica","conchas","monte mor","caete",
            "dourado","lins","jales","pitanga","faxinal","matinhos","morretes","cantagalo","ibate",
            "itarare","parobe","tambau","sarzedo","cianorte","cacoal","holambra","palmas","antonina",
            "leopoldina","pirapora","itapeva","itaporanga","penapolis","sorriso","natal","vilhena",
            "canoas","mendes","picos","aruana","carambei","conchal"}
CAPITAIS = (r"sao paulo|rio de janeiro|belo horizonte|curitiba|brasilia|salvador|porto alegre|"
            r"florianopolis|recife|fortaleza|campinas|niteroi|teresina|goiania|belem|manaus")
EDITORAS = (r"boitempo|editora|autonomia literaria|malheiros|saraiva|atlas|companhia|hucitec|"
            r"annablume|paz e terra|expressao popular|alameda|senac|zahar|record|perspectiva|edusp|"
            r"unesp|cortez|fgv|elsevier|springer|routledge|blucher|ipea|antp|ntu|revista|cadernos|"
            r"anais|ed\.|universidade|puc|usp|unicamp|ufabc|ufmg|ufba|unb|ufsc|ufpr|instituto")

def limpa_imprenta(t):
    t = re.sub(r"(?:" + CAPITAIS + r")\s*[:,]\s*(?:" + EDITORAS + r")", " _imprenta_ ", t)
    t = re.sub(r"(?:" + CAPITAIS + r")\s*,\s*(?:v\.|n\.|ano|p\.|\d{4})", " _imprenta_ ", t)
    return t

def ler_municipios_das_fichas():
    out = []
    for p in sorted(glob.glob(os.path.join(FICHAS, "*.md"))):
        t = open(p, encoding="utf-8", errors="ignore").read()[:1500]
        m = re.search(r"^municipio:\s*(.+)$", t, re.M)
        u = re.search(r"^uf:\s*(.+)$", t, re.M)
        if m:
            out.append((m.group(1).strip(), (u.group(1).strip() if u else ""), os.path.basename(p)))
    return out

def ler_base():
    try:
        import pandas as pd
        d = pd.read_excel(XLSX)
        dentro, fora = set(), set()
        for _, r in d.iterrows():
            k = (NORM(r["Município"]), NORM(r["UF"]))
            (fora if str(r["Situação"]).startswith(("Excluída", "Reclassificada")) else dentro).add(k)
        return dentro, fora
    except Exception as e:
        print("AVISO: base-mestre não lida (%s) — o cruzamento sai sem denominador." % e)
        return set(), set()

def curto(arq):
    return arq.replace("Fichamento - ", "").replace(".md", "").split(" — ")[0].strip()

def nivel(mencoes, em_titulo):
    if mencoes >= 8 or (em_titulo and mencoes >= 3): return "A"
    return "B" if mencoes >= 3 else "C"

def extrair():
    muns = ler_municipios_das_fichas()
    ordem = sorted(((n, u, a, norm(n)) for n, u, a in muns), key=lambda x: -len(x[3]))
    hits = collections.defaultdict(list)
    for p in sorted(glob.glob(os.path.join(NOTAS, "Fichamento*.md"))):
        arq = os.path.basename(p)
        raw = open(p, encoding="utf-8", errors="ignore").read()
        titulos = set(norm(l) for l in raw.splitlines() if l.startswith("#"))
        t = limpa_imprenta(norm(raw))
        for n, u, _a, nn in ordem:
            if len(nn) < 5: continue
            pat = re.compile(r"(?<![a-z0-9])" + re.escape(nn) + r"(?![a-z0-9])")
            oc = list(pat.finditer(t))
            if not oc: continue
            if nn in EXIGE_UF:
                un = norm(u)
                c = sum(1 for m in oc
                        if re.search(r"[(/\-]\s?" + re.escape(un) + r"\b", t[max(0, m.start()-40):m.end()+40]))
                if c == 0:
                    t = pat.sub(" _m_ ", t); continue
            else:
                c = len(oc)
            hits[(n, u)].append((arq, c, any(nn in h for h in titulos)))
            t = pat.sub(" _m_ ", t)
    return hits

def main():
    hits = extrair()
    dentro, fora = ler_base()
    reg = {}
    for k, v in hits.items():
        v = sorted(v, key=lambda x: -x[1])
        nv = [(a, c, e, nivel(c, e)) for a, c, e in v]
        top = "A" if any(x[3] == "A" for x in nv) else ("B" if any(x[3] == "B" for x in nv) else "C")
        reg[k] = (nv, top)
    os.makedirs(os.path.dirname(SAI_CSV), exist_ok=True)
    with open(SAI_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["municipio","uf","na_base_mestre","nivel_municipio","fichamento","mencoes","em_titulo","nivel_par"])
        for (n, u), (nv, top) in sorted(reg.items()):
            nb = "sim" if (NORM(n), NORM(u)) in dentro else ("reclassificado" if (NORM(n), NORM(u)) in fora else "nao")
            for a, c, e, lv in nv:
                w.writerow([n, u, nb, top, a, c, int(e), lv])

    def emb(k): return (NORM(k[0]), NORM(k[1])) in dentro
    A = [k for k, (_, t) in reg.items() if t == "A"]
    B = [k for k, (_, t) in reg.items() if t == "B"]
    C = [k for k, (_, t) in reg.items() if t == "C"]
    semmen = len(dentro) - len([k for k in reg if emb(k)])
    L = []
    ap = L.append
    ap("---"); ap('title: "Cobertura da literatura por município (gerado)"')
    ap("tags: [rsl-tz, cobertura, casos-municipais, gerado]")
    ap("publish: false"); ap("created: 2026-09-03"); ap("---"); ap("")
    ap("# Cobertura da literatura por município")
    ap("")
    ap("> **Gerado por `_meta/scripts/mapear_rsl_municipios.py` — somente leitura.** Cruza os fichamentos da RSL com os municípios das fichas e da base-mestre. ⚠️ **Mede menções nos FICHAMENTOS, que são notas de leitura do autor, não nos textos originais.** O nível é indício de cobertura, não prova — conferir antes de afirmar que a obra *trata* do município.")
    ap("")
    ap("**Níveis:** **A** objeto (nome em título de seção com ≥3 menções, ou ≥8 menções) · **B** seção substantiva (≥3) · **C** menção de passagem (1-2).")
    ap("")
    ap("## O número que importa")
    ap("")
    ap(f"| | n |"); ap("|---|---:|")
    ap(f"| municípios em escopo na base-mestre | **{len(dentro)}** |")
    ap(f"| — com tratamento de **objeto** (nível A) | **{len([k for k in A if emb(k)])}** |")
    ap(f"| — com **seção substantiva** (nível B) | {len([k for k in B if emb(k)])} |")
    ap(f"| — com **menção de passagem** (nível C) | {len([k for k in C if emb(k)])} |")
    ap(f"| — **sem nenhuma menção em toda a literatura lida** | **{semmen}** |")
    ap("")
    ap(f"🔴 **{semmen} dos {len(dentro)} municípios em escopo ({100*semmen//max(1,len(dentro))}%) não são mencionados uma única vez nos fichamentos.** E o tratamento de objeto alcança **{len([k for k in A if emb(k)])}**.")
    ap("")
    for tit, grupo, dentro_flag in (("A — objeto, na base-mestre", A, True),
                                    ("A — objeto, FORA da base-mestre", A, False),
                                    ("B — seção substantiva, na base-mestre", B, True)):
        sel = [k for k in grupo if emb(k) == dentro_flag]
        if not sel: continue
        ap(f"## {tit}"); ap("")
        for k in sorted(sel, key=lambda k: -sum(c for _, c, _, _ in reg[k][0])):
            nv, _ = reg[k]
            tot = sum(c for _, c, _, _ in nv)
            forte = [f"{curto(a)} ({c})" for a, c, e, lv in nv if lv in ("A", "B")]
            ap(f"- **{k[0]} ({k[1]})** — {len(nv)} fichamentos, {tot} menções · " + "; ".join(forte[:8]))
        ap("")
    sel = sorted(f"{n} ({u})" for n, u in C if emb((n, u)))
    if sel:
        ap("## C — só menção de passagem, na base-mestre"); ap("")
        ap("⚠️ **Nível pouco confiável: 1-2 ocorrências não distinguem caso analisado de nome em lista.** Conferir antes de usar.")
        ap(""); ap("; ".join(sel)); ap("")
    open(SAI_MD, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print("gravado:", os.path.basename(SAI_MD))
    print("gravado:", os.path.basename(SAI_CSV))
    print(f"base em escopo {len(dentro)} · A {len([k for k in A if emb(k)])} · B {len([k for k in B if emb(k)])} · C {len([k for k in C if emb(k)])} · sem menção {semmen}")

if __name__ == "__main__":
    main()
