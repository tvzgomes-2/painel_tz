# -*- coding: utf-8 -*-
"""Conciliação entre base-mestre, régua, log jurídico, fichas, e-SIC e índice de normas (read-only).
Imprime as divergências por par de bases. Uso: python conciliar_bases.py
Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni"""
import os, re, glob, unicodedata, openpyxl
R = os.environ.get("TZ_VAULT", os.path.expanduser("~/mnt/doutorado")); P = lambda *a: os.path.join(R, *a)
n = lambda s: unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()
wb = openpyxl.load_workbook(P("03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx"), read_only=True)
rows = list(wb["consolidado"].iter_rows(values_only=True)); H = rows[0]
g = lambda r, k: "" if r[H.index(k)] is None else str(r[H.index(k)]).strip()
mest = {}
for r in rows[1:]:
    k = (n(g(r, "Município")), g(r, "UF")); mest.setdefault(k, []).append(r)
esc = {k: v for k, v in mest.items() if any(g(r, "Situação") in ("Ativa", "Encerrada") for r in v)}
pist = {k: v for k, v in mest.items() if any(g(r, "Situação").startswith("Pista") for r in v)}
out = {}
# A) régua
w = openpyxl.load_workbook(P("03 - Dados/_data/casos por fonte/Tipologias TZ - consolidado.xlsx"), read_only=True)
reg = {}
for aba in ("1 Universal", "2 Parcial", "3 Encerradas", "Não TZ"):
    for x in list(w[aba].iter_rows(values_only=True))[1:]:
        if x[0]: reg.setdefault((n(x[0]), str(x[1] or "").strip()), []).append((aba, str(x[2] or "").strip()))
A = []
for k, rs in esc.items():
    abas = {a for a, _ in reg.get(k, [])}
    if not abas & {"1 Universal", "3 Encerradas"} and not any("2 Parcial" in g(r, "Régua — aba") for r in rs):
        A.append(f"{k}: em escopo na mestre, mas fora das abas 1/3 da régua ({sorted(abas) or 'ausente'})")
    sm = {g(r, "Régua — subtipo") for r in rs if g(r, "Situação") == "Ativa" and "1 Universal" in g(r, "Régua — aba")} - {""}  # 28/09: só linhas da aba 1 (antes acusava 2b/2c da aba 2)
    sr = {s for a, s in reg.get(k, []) if a == "1 Universal"} - {"", "None"}
    if sm != sr and (sm or sr): A.append(f"{k}: subtipo mestre {sorted(sm)} × régua aba 1 {sorted(sr)}")
for k, v in reg.items():
    if any(a == "1 Universal" for a, _ in v) and k not in esc: A.append(f"{k}: na aba 1 da régua, mas fora do escopo da mestre")
out["A mestre × régua"] = A
# B) log
L = open(P("04 - Análises/Pesquisa legal/Log de busca jurídica e contratual — municípios.md"), encoding="utf-8").read()
blocos = {}
for m in re.finditer(r"^#### (.+?) \(([A-Z]{2})\)\n(.*?)(?=^#### |\Z)", L, re.M | re.S):
    st = re.search(r"- \*\*Status:\*\* ([^\n]*)", m.group(3)); blocos[(n(m.group(1)), m.group(2))] = st.group(1) if st else ""
idx = {}
for m in re.finditer(r"^\| ([^|]+?) \| ([A-Z]{2}) \| ([^|]*?) \|", L, re.M):
    if m.group(1) != "Município": idx[(n(m.group(1)), m.group(2))] = m.group(3)
def classe(s):
    s = n(s).replace("*", "")
    for c in ("resolvido", "em verificacao", "pista", "pendente", "achado (nota)", "regua 2d"):
        if s.startswith(c) or ("ativa desde" in s and c == "resolvido"): return c
    return s[:20]
B = []
for k in list(esc) + list(pist):
    if k not in blocos: B.append(f"{k}: sem bloco no log"); continue
    cm = classe(g(mest[k][0], "Status no log")); cl = classe(blocos[k])
    if cm != cl: B.append(f"{k}: mestre '{g(mest[k][0], 'Status no log')[:60]}' × log '{blocos[k][:60]}'")
    if k in idx and classe(idx[k]) != cl: B.append(f"{k}: índice rápido '{idx[k][:50]}' × bloco '{blocos[k][:50]}'")
    if k not in idx: B.append(f"{k}: sem linha no índice rápido do log")
out["B mestre × log"] = B
# C) fichas
C = []; fich = {}
for p in glob.glob(P("04 - Análises/Casos municipais/Fichas por município/Ficha - *.md")):
    if "BACKUP" in p: continue
    t = open(p, encoding="utf-8").read(); fm = t.split("---")[1] if t.startswith("---") else ""
    mu = re.search(r"^municipio:\s*\"?(.+?)\"?\s*$", fm, re.M); uf = re.search(r"^uf:\s*\"?([A-Z]{2})", fm, re.M)
    if mu and uf: fich[(n(mu.group(1)), uf.group(1))] = (p, fm)
for k, rs in esc.items():
    if k not in fich: C.append(f"{k}: em escopo sem ficha"); continue
    fm = fich[k][1]; r = rs[0]
    sit = re.search(r"^situacao:\s*(.+)$", fm, re.M); ano = re.search(r"^ano_inicio:\s*(.+)$", fm, re.M); cam = re.search(r"^camada:\s*(.+)$", fm, re.M)
    sm = g(r, "Situação") if len(rs) == 1 else "/".join(sorted({g(x, "Situação") for x in rs}))
    if sit and not any(n(sit.group(1)).strip('"').startswith(n(s)) for s in sm.split("/")): C.append(f"{k}: ficha situacao '{sit.group(1)}' × mestre '{sm}'")
    am = re.match(r"\d{4}", g(r, "Ano início"))
    if ano and am and am.group(0) not in ano.group(1): C.append(f"{k}: ficha ano_inicio '{ano.group(1)}' × mestre '{g(r, 'Ano início')[:30]}'")
    sub = g(r, "Régua — subtipo")
    if cam and sub and g(r, "Situação") != "Encerrada" and sub not in cam.group(1): C.append(f"{k}: ficha camada '{cam.group(1)}' × mestre subtipo '{sub}'")
out["C mestre × fichas"] = C
# D) e-SIC
E = open(P("04 - Análises/Pesquisa legal/e-SIC — pedidos de informação por município.md"), encoding="utf-8").read()
tab = {}
for m in re.finditer(r"^\| (\d+) \| ([^|]+?) \| ([A-Z]{2}) \|", E, re.M): tab[(n(m.group(2)), m.group(3))] = m.group(1)
D = []
for k, rs in list(esc.items()) + list(pist.items()):
    en = re.match(r"\d+", g(rs[0], "e-SIC / varredura nº"))
    if en and tab.get(k) != en.group(0): D.append(f"{k}: mestre e-SIC nº {en.group(0)} × tabela {tab.get(k)}")
for k, num in tab.items():
    if k in esc or k in pist:
        en = re.match(r"\d+", g(mest[k][0], "e-SIC / varredura nº"))
        if not en: D.append(f"{k}: na tabela do e-SIC (nº {num}) sem nº na mestre")
out["D mestre × e-SIC"] = D
# E) índice de normas
ND = P("04 - Análises/Pesquisa legal/Normas padronizadas"); I = open(os.path.join(ND, "_índice - Normas padronizadas.md"), encoding="utf-8").read()
notas = {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(ND, "Norma — *.md"))}
links = set(re.findall(r"\[\[(Norma — [^\]|]+)", I))
out["E índice de normas"] = [f"sem linha no índice: {x}" for x in sorted(notas - links)] + [f"linha sem nota: {x}" for x in sorted(links - notas)]
for k, v in out.items():
    print(f"\n### {k}: {len(v)}")
    for x in v: print(" -", x)
