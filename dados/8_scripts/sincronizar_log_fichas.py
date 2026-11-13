#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sincronizar_log_fichas.py — leva para a ficha municipal os registros do log jurídico-contratual
datados a partir de --desde (padrão 30/09/2026) e o retrato atual da base-mestre (situação, estado terminal,
legislação, status, prova 2025–2026).

Bloco gerado (não editar à mão), dentro de "### Legislação e contratos", logo antes de "## 8. Literatura e bibliografia":
  <!-- log-ficha:inicio -->  ...  <!-- log-ficha:fim -->
Idempotente: o bloco é refeito inteiro a cada rodada; a ficha só é gravada se o conteúdo mudar. Backup em _meta/_backups/.
Só entram fichas com ao menos um registro do log na janela. Registros copiados verbatim (achado e 'leitura (a revisar)'
são do log; a decisão de régua continua sendo do autor).

USO: python3 sincronizar_log_fichas.py [--desde 30/09/2026] [--so "Mun" UF] [--gravar]
Criado em 01/10/2026 (saneamento das rodadas de 30/09 e 01/10/2026).
"""
import os, re, sys, shutil, argparse, datetime, openpyxl
V = os.environ.get("TZ_VAULT") or os.path.expanduser("~/mnt/doutorado"); os.chdir(V)
L = "04 - Análises/Pesquisa legal/Log de busca jurídica e contratual — municípios.md"
MP = "03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx"
FD = "04 - Análises/Casos municipais/Fichas por município/"
INI, FIM = "<!-- log-ficha:inicio -->", "<!-- log-ficha:fim -->"
ANC = "\n## 8. Literatura e bibliografia"
ap = argparse.ArgumentParser(); ap.add_argument("--desde", default="30/09/2026"); ap.add_argument("--so", nargs=2); ap.add_argument("--gravar", action="store_true")
a = ap.parse_args(); D0 = datetime.datetime.strptime(a.desde, "%d/%m/%Y").date()
def datas(s): 
    out=[]
    for d,m,y in re.findall(r"(\d{2})/(\d{2})/(\d{4})", s):
        try: out.append(datetime.date(int(y),int(m),int(d)))
        except ValueError: pass
    return out
t = open(L, encoding="utf-8").read(); det = t[t.find("## Detalhe por município"):]
REG = {}
for b in re.split(r"\n(?=#### )", det):
    m = re.match(r"#### (.+) \(([A-Z]{2})\)\n", b)
    if not m: continue
    bul = []
    for l in b.split("\n"):
        if not l.startswith("- **") or l.startswith(("- **Última atualização", "- **Status:")): continue
        lab = re.match(r"- \*\*(.+?)\*\*", l); lab = lab.group(1) if lab else ""
        ds = datas(lab)
        if ds and max(ds) >= D0: bul.append(l)
    if bul: REG[(m.group(1), m.group(2))] = bul
ws = openpyxl.load_workbook(MP, read_only=True, data_only=True)["consolidado"]
rows = list(ws.iter_rows(values_only=True)); H = {k: i for i, k in enumerate(rows[0])}
g = lambda r, k: ("" if k not in H or r[H[k]] in (None, "None") else str(r[H[k]]).strip())
M = {(r[0], r[1]): r for r in rows[1:] if r[0]}
hoje = datetime.date.today().strftime("%d/%m/%Y"); mud = []; sem_anc = []; sem_ficha = []
for (mu, uf), bul in sorted(REG.items()):
    if a.so and (mu, uf) != (a.so[0], a.so[1]): continue
    F = FD + f"Ficha - {mu} ({uf}).md"
    if not os.path.exists(F): sem_ficha.append(f"{mu}/{uf}"); continue
    f = open(F, encoding="utf-8").read(); r = M.get((mu, uf))
    linhas = [INI, f"#### Registro do log e da base-mestre (gerado em {hoje}; registros desde {a.desde})", ""]
    if r is not None:
        for rot, k in (("Situação", "Situação"), ("Estado terminal (A.2e)", "Estado terminal (completude)"), ("Legislação (base-mestre)", "Legislação"),
                       ("Status no log", "Status no log"), ("Prova de operação 2025–2026 (A.2d)", "Prova de operação — atualidade (2025/2026)"), ("Próximo passo", "Próximo passo")):
            v = g(r, k)
            if v: linhas.append(f"- **{rot}:** {v}")
        linhas.append("")
    linhas += ["Registros do [[Log de busca jurídica e contratual — municípios]] (verbatim):", ""] + bul + ["", FIM]
    novo = "\n".join(linhas)
    if INI in f:
        i = f.index(INI); j = f.index(FIM, i) + len(FIM); fn = f[:i] + novo + f[j:]
    else:
        if f.count(ANC) != 1: sem_anc.append(f"{mu}/{uf}"); continue
        fn = f.replace(ANC, "\n" + novo + "\n" + ANC, 1)
    if fn != f: mud.append((F, fn))
print(f"casos com registros desde {a.desde}: {len(REG)} | fichas a gravar: {len(mud)} | sem âncora: {sem_anc} | sem ficha: {sem_ficha}")
if a.gravar and mud:
    BK = f"_meta/_backups/log-fichas-{datetime.datetime.now():%Y%m%d-%H%M%S}"; os.makedirs(BK)
    for F, fn in mud: shutil.copy2(F, BK); open(F, "w", encoding="utf-8", newline="\n").write(fn)
    print("gravado", BK)
