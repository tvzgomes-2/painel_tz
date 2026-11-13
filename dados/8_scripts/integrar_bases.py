#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base integrada dos casos de Tarifa Zero — junta as tabelas que o cofre acumulou (09/09 → 23/09/2026)
sem perder coluna: uma linha por município, blocos de colunas prefixados pela fonte; versões antigas de uma
mesma tabela só entram com o que a versão mais nova perdeu (colunas ou municípios). Read-only sobre as fontes."""
import csv, os, re, json, unicodedata, datetime, collections
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
csv.field_size_limit(10**8)
B = "03 - Dados/_data"; L = B + "/Legislacao e contratos TZ"; K = B + "/casos por fonte"
OUT = "03 - Dados/_data/casos por fonte/Base integrada - casos TZ (23-09-2026).xlsx"
def n(s): return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip())
def clean(v):
    if v is None: return ""
    v = str(v).strip()
    return "" if v in ("None", "nan", "—", "-") else v
def read_csv(p):
    raw = open(p, encoding="utf-8-sig", errors="ignore").read()
    delim = ";" if raw.split("\n", 1)[0].count(";") > raw.split("\n", 1)[0].count(",") else ","
    rows = list(csv.reader(raw.splitlines(), delimiter=delim))
    return [c.strip() for c in rows[0]], rows[1:]
def read_xlsx(p, sheet):
    ws = openpyxl.load_workbook(p, read_only=True, data_only=True)[sheet]
    rows = list(ws.iter_rows(values_only=True))
    return [clean(c) for c in rows[0]], rows[1:]
# (rótulo curto, arquivo, aba, coluna município, coluna UF, data)
FONTES = [
 ("MESTRE", K+"/Municípios TZ - consolidado.xlsx", "consolidado", "Município", "UF", "vivo"),
 ("RÉGUA-1", K+"/Tipologias TZ - consolidado.xlsx", "1 Universal", "Município", "UF", "vivo"),
 ("RÉGUA-2", K+"/Tipologias TZ - consolidado.xlsx", "2 Parcial", "Município", "UF", "vivo"),
 ("RÉGUA-3", K+"/Tipologias TZ - consolidado.xlsx", "3 Encerradas", "Município", "UF", "vivo"),
 ("RÉGUA-NãoTZ", K+"/Tipologias TZ - consolidado.xlsx", "Não TZ", "Município", "UF", "vivo"),
 ("CONTROLE-UNIFICADO", "04 - Análises/Pesquisa legal/Controle unificado dos casos — base, régua, log e leitura.xlsx", "Controle", "Município", "UF", "23/09"),
 ("INSTRUMENTO-EIXO1", "04 - Análises/Pesquisa legal/Instrumentos da gratuidade — categorizacao das notas de norma (23-09-2026).xlsx", "Por município", "Município", "UF", "23/09"),
 ("CONTRATOS-EIXO2", "04 - Análises/Pesquisa legal/Contratos e licitacoes — catalogo das camadas 1-3 (23-09-2026).xlsx", "Eixo 2 por município", "municipio", "uf", "23/09"),
 ("LEITURA-CRÍTICA", "04 - Análises/Leitura crítica integral — matriz (23-09-2026).xlsx", "Matriz", "Município", "UF", "23/09"),
 ("CONSOLIDADA-18-09", K+"/_historico/Tabela consolidada - Legislação, contratos e réguas (18-09-2026).xlsx", "consolidado", "Município", "UF", "18/09"),
 ("COMPLETUDE-FICHAS", K+"/Completude das fichas.xlsx", "completude", "Município", "UF", "—"),
 ("CONTROLE-ÚNICO-11-09", L+"/_historico/Controle unico - legislacao PlanMob e contratos, 176 casos (2026-09-11).csv", None, "municipio", "uf", "11/09"),
 ("PESQUISAS-PLANMOB-09-09", L+"/_historico/Municipios TZ - legislacao, PlanMob e pesquisas (09-09-2026).csv", None, "municipio", "uf", "09/09"),
 ("TZxPLANMOB-09-09", L+"/_historico/TZ x PlanMob - 176 casos (09-09-2026).csv", None, "municipio", "uf", "09/09"),
 ("ESTADO-LEG-v4", L+"/_historico/Estado da legislacao - 176 casos (v4, 09-09-2026).csv", None, "municipio", "uf", "09/09"),
 ("ESTADO-LEG-v1", L+"/_historico/Estado da legislacao - 176 casos (09-09-2026).csv", None, "municipio", "uf", "09/09"),
 ("BASE-LEG-CONTRATOS-v3", L+"/_historico/base_legislacao_contratos_175 (v3, 09-09-2026).csv", None, "municipio", "uf", "09/09"),
 ("BASE-LEG-CONTRATOS-v1", L+"/_historico/base_legislacao_contratos_175.csv", None, "municipio", "uf", "09/09"),
 ("WORKLIST-89-07-09", L+"/_historico/Worklist - 89 casos sem norma (07-09-2026).csv", None, "municipio", "uf", "07/09"),
 ("LEG-A-LOCALIZAR-94-07-09", K+"/_historico/Legislacao a localizar - 94 casos (07-09-2026).csv", None, "municipio", "uf", "07/09"),
 ("OCR-B3-12-09", L+"/_historico/OCR B3 - 5 casos avancados (12-09-2026).csv", None, "municipio", "uf", "12/09"),
 ("CRUZAMENTO-BIBLIO-02-09", K+"/_historico/Cruzamento cidade x bibliografia (v2, 02-09-2026).csv", None, "Cidade", "UF", "02/09"),
]
data = collections.OrderedDict(); cols = collections.OrderedDict(); mapa = []
for lab, p, sh, cm, cu, dt in FONTES:
    if not os.path.exists(p): mapa.append((lab, p, sh or "", dt, "AUSENTE", 0, 0)); continue
    H, R = read_xlsx(p, sh) if sh else read_csv(p)
    H = [h if h else f"col{i}" for i, h in enumerate(H)]
    if cm not in H or cu not in H: mapa.append((lab, p, sh or "", dt, f"sem colunas-chave ({cm}/{cu})", 0, 0)); continue
    im, iu = H.index(cm), H.index(cu); nrow = 0; seen = collections.Counter()
    for r in R:
        r = list(r) + [""] * (len(H) - len(r))
        if not clean(r[im]): continue
        k = (n(r[im]), clean(r[iu]).upper()); seen[k] += 1
        rec = data.setdefault(k, {"_m": clean(r[im]), "_uf": clean(r[iu]).upper()})
        for h, v in zip(H, r):
            if h in (cm, cu): continue
            v = clean(v)
            if not v: continue
            c = f"[{lab}] {h}"; cols.setdefault(c, lab)
            if seen[k] > 1:  # linha repetida na mesma fonte (ex.: 2 políticas): concatena
                old = rec.get(c, "")
                if v not in old.split(" ‖ "): rec[c] = (old + " ‖ " + v) if old else v
            else: rec[c] = v
        nrow += 1
    mapa.append((lab, p, sh or "", dt, "ok", nrow, len(H)))
# versões antigas: manter só o que a nova perdeu (valores iguais aos da versão nova são apagados)
def podar(old, new):
    oc = [c for c in cols if cols[c] == old]
    for c in oc:
        base = c.split("] ", 1)[1]; nc = f"[{new}] {base}"
        for rec in data.values():
            if c in rec and nc in cols and rec.get(nc) == rec[c]: del rec[c]
podar("ESTADO-LEG-v1", "ESTADO-LEG-v4"); podar("BASE-LEG-CONTRATOS-v1", "BASE-LEG-CONTRATOS-v3")
# colunas vazias e idênticas a outra já incluída
alive = [c for c in cols if any(c in r for r in data.values())]
sig = {}; dup = {}
for c in alive:
    s = tuple((k, data[k].get(c, "")) for k in data)
    if s in sig: dup[c] = sig[s]
    else: sig[s] = c
final = [c for c in alive if c not in dup]
# universo
def uni(rec):
    s = rec.get("[MESTRE] Situação", "")
    if not s:
        if rec.get("[RÉGUA-2] Modelo") == "temporaria" and rec.get("[RÉGUA-2] Início/Ano") == "0" and not any(k.startswith(("[RÉGUA-1]", "[RÉGUA-3]", "[CONTROLE-ÚNICO")) for k in rec):
            return "2d eleitoral (IDEC+IPEA)"
        if any(k.startswith("[RÉGUA-2]") for k in rec): return "camada 2 (fora da mestre)"
        return "fora da base-mestre"
    return "fora de escopo" if s.startswith(("Excluída", "Reclassificada")) else "em escopo"
rows = []
for k, rec in data.items():
    r = {"Município": rec["_m"], "UF": rec["_uf"], "Universo": uni(rec), "Nº de fontes com o município": len({cols[c] for c in rec if c.startswith("[")})}
    r.update({c: rec.get(c, "") for c in final}); rows.append(r)
rows.sort(key=lambda r: (r["Universo"] != "em escopo", r["UF"], r["Município"]))
# conflitos em conceitos-chave
CONC = {
 "Situação": ["[MESTRE] Situação", "[CONTROLE-ÚNICO-11-09] situacao", "[PESQUISAS-PLANMOB-09-09] situacao", "[CONSOLIDADA-18-09] Situação", "[ESTADO-LEG-v4] situacao"],
 "Ano início": ["[MESTRE] Ano início", "[CONTROLE-ÚNICO-11-09] ano_inicio", "[PESQUISAS-PLANMOB-09-09] ano_inicio_tz", "[CONSOLIDADA-18-09] Ano início", "[RÉGUA-1] Ano", "[RÉGUA-3] Ano"],
 "Operador": ["[MESTRE] Operador", "[CONTROLE-ÚNICO-11-09] operador_planilha", "[CONTROLE-ÚNICO-11-09] operador_confirmado", "[CONSOLIDADA-18-09] Operador — §2 da ficha", "[CONTRATOS-EIXO2] operador_vigente", "[RÉGUA-1] Operador"],
 "Legislação": ["[MESTRE] Legislação", "[CONTROLE-ÚNICO-11-09] legislacao_planilha", "[CONTROLE-ÚNICO-11-09] norma_encontrada", "[RÉGUA-1] Legislação", "[INSTRUMENTO-EIXO1] Ato que concede"],
}
conf = []
for r in rows:
    if r["Universo"] != "em escopo": continue
    for conc, cs in CONC.items():
        vals = {c: data[(n(r["Município"]), r["UF"])].get(c, "") for c in cs}
        vs = {v for v in vals.values() if v}
        norm = {re.sub(r"[^a-z0-9]", "", n(v))[:40] for v in vs}
        if len(norm) > 1:
            conf.append({"Município": r["Município"], "UF": r["UF"], "Conceito": conc, **{"Valores": " ‖ ".join(f"{c.split(']')[0][1:]}: {v}" for c, v in vals.items() if v)}})
# normas (nível ato) e atos contratuais
NORM = []
p4 = L + "/_historico/normas_padronizadas (v4, 12-09-2026).csv"
cat = "_meta/scripts/_scratch/instrumentos/categorias_normas.json"
if os.path.exists(cat):
    for x in json.load(open(cat, encoding="utf-8")):
        NORM.append({"Município": x["municipio"], "UF": x["uf"], "Nota": x["arquivo"][:-3], "Instrumento": x["instrumento"], "Nº": x["numero"], "Ano": x["ano"], "Função": x["funcao"], "Concede ao usuário": x["concede_gratuidade_usuario"], "Trecho": x["trecho"], "Leitura": x["leitura"], "Vínculo (frontmatter original)": x["vinculo_tz_frontmatter"], "A conferir": x["divergencia"]})
if os.path.exists(p4):
    H, R = read_csv(p4); have = {(n(r["Município"]), r["UF"], str(r["Nº"]).replace(".", "")) for r in NORM}
    for r in R:
        d = dict(zip(H, r))
        if (n(d["municipio"]), d["uf"], d["numero"].replace(".", "")) not in have:
            NORM.append({"Município": d["municipio"], "UF": d["uf"], "Nota": d.get("ficha_md", ""), "Instrumento": d["tipo_norma"], "Nº": d["numero"], "Ano": d["ano"], "Função": "(só na tabela v4 de 12/09 — sem nota atual)", "Concede ao usuário": "", "Trecho": d.get("ementa", ""), "Leitura": "", "Vínculo (frontmatter original)": d["vinculo_tz"], "A conferir": d.get("identidade_divergente", "")})
ATOS = []
cc = "_meta/scripts/_scratch/instrumentos/catalogo_contratos.json"
if os.path.exists(cc): ATOS = json.load(open(cc, encoding="utf-8"))["atos"]
# gravar
wb = openpyxl.Workbook(); w = wb.active; w.title = "Leia-me"
hoje = datetime.date.today().strftime("%d/%m/%Y")
lines = [f"Base integrada dos casos de Tarifa Zero — gerada em {hoje} por _meta/scripts/integrar_bases.py (read-only; regenerar em vez de editar)",
 "Junta, numa linha por município, TODAS as colunas das tabelas que o cofre acumulou de 02/09 a 23/09/2026. Cada coluna leva o prefixo [FONTE]. Nada é sobrescrito: quando duas fontes dizem coisas diferentes, as duas ficam, e a aba 'Conflitos' lista os casos em Situação, Ano início, Operador e Legislação.",
 "Versões antigas da mesma tabela (Estado da legislação v1; base_legislacao_contratos v1) entram só com o que a versão nova perdeu. Colunas totalmente vazias ou idênticas a outra já incluída foram omitidas (lista abaixo).",
 "Canônico continua sendo: universo = base-mestre; camada = régua; evidência = log e notas. Esta base é para consulta e para recuperar informação perdida entre versões.", "",
 "Fontes (rótulo · arquivo · aba · data · status · linhas · colunas):"]
for i, l in enumerate(lines, 1): w.cell(i, 1, l)
r0 = len(lines) + 1
for m in mapa:
    for j, v in enumerate(m, 1): w.cell(r0, j, v)
    r0 += 1
r0 += 1; w.cell(r0, 1, f"Colunas omitidas por serem idênticas a outra ({len(dup)}):").font = Font(bold=True); r0 += 1
for c, o in dup.items(): w.cell(r0, 1, c); w.cell(r0, 2, "= " + o); r0 += 1
w["A1"].font = Font(bold=True, size=13); w.column_dimensions["A"].width = 60; w.column_dimensions["B"].width = 70
def sheet(name, H, data_, widths=None, freeze="C2"):
    ws = wb.create_sheet(name); ws.append(H)
    for c in range(1, len(H) + 1):
        x = ws.cell(1, c); x.font = Font(bold=True, color="FFFFFF"); x.fill = PatternFill("solid", fgColor="4472C4"); x.alignment = Alignment(wrap_text=True, vertical="top")
    for d in data_: ws.append([str(d.get(h, ""))[:32000] for h in H])
    for i, h in enumerate(H, 1): ws.column_dimensions[get_column_letter(i)].width = (widths or {}).get(h, 22)
    ws.freeze_panes = freeze; ws.auto_filter.ref = f"A1:{get_column_letter(len(H))}{len(data_) + 1}"
    return ws
sheet("Municípios", ["Município", "UF", "Universo", "Nº de fontes com o município"] + final, rows, {"Município": 22, "UF": 5, "Universo": 14})
sheet("Conflitos", ["Município", "UF", "Conceito", "Valores"], conf, {"Valores": 140})
sheet("Normas", list(NORM[0].keys()) if NORM else ["-"], NORM, {"Nota": 45, "Trecho": 60, "A conferir": 60})
sheet("Atos contratuais", list(ATOS[0].keys()) if ATOS else ["-"], ATOS, {"objeto": 45, "fonte": 45})
wb.save(OUT)
print("OK", OUT, "| municípios", len(rows), "| em escopo", sum(r["Universo"] == "em escopo" for r in rows), "| colunas", len(final), "| duplicadas omitidas", len(dup), "| conflitos", len(conf), "| normas", len(NORM), "| atos", len(ATOS))
for m in mapa: print(m[0], m[4], m[5])
