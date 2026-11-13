#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exportar_lista_busca_ativa.py — lista de trabalho da busca ativa (varredura manual antes do e-SIC).
Lê a Fase 2 do arquivo do e-SIC + a planilha-mestre e grava
'04 - Análises/Pesquisa legal/Busca ativa — lista de trabalho.xlsx' (nome estável, sobrescreve).
Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni"""
import re, os, datetime, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ES = os.path.join(R, "04 - Análises/Pesquisa legal/e-SIC — pedidos de informação por município.md")
MP = os.path.join(R, "03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx")
OUT = os.path.join(R, "04 - Análises/Pesquisa legal/Busca ativa — lista de trabalho.xlsx")

txt = open(ES, encoding="utf-8").read()
linhas = []
secao = 0  # 24/09/2026: a fase vem da seção do arquivo (## Fase 1 / ## Fase 2), não do número
for l in txt.splitlines():
    if l.startswith("## Fase 1"): secao = 1
    elif l.startswith("## Fase 2"): secao = 2
    elif l.startswith("## "): secao = 0
    m = re.match(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([A-Z]{2})\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|", l)
    if m:
        linhas.append(dict(secao=secao, n=int(m.group(1)), mun=m.group(2), uf=m.group(3), grupo=m.group(4), porque=m.group(5), pergunta=m.group(6)))
wb = openpyxl.load_workbook(MP, read_only=True); ws = wb["consolidado"]
it = ws.iter_rows(values_only=True); h = next(it)
mestre = {(r[h.index("Município")], r[h.index("UF")]): r for r in it if r[0]}
def g(r, k):
    return (str(r[h.index(k)]) if r is not None and k in h and r[h.index(k)] not in (None, "None") else "")

rows = []
for d in linhas:
    r = mestre.get((d["mun"], d["uf"]))
    status = g(r, "Status no log")
    fechado = d["grupo"].startswith("✅") or status.startswith("Resolvido")
    fase = "Fase 1 — enviar e-SIC" if (d["secao"] == 1 and not fechado) else ("Fechado (não enviar)" if fechado else "Fase 2 — varredura manual")
    acessivel = bool(re.search(r"lida|lido|PDF|SISCAM|SAPL|PNCP|Portal|decreto|edital", d["porque"] + g(r, "Próximo passo"), re.I))
    rows.append([fase, d["n"], d["mun"], d["uf"], d["grupo"], g(r, "Régua — aba"), g(r, "Instrumento (eixo 1)"),
                 status, d["porque"], d["pergunta"], g(r, "Busca recomendada (leitura 23/09)"), g(r, "Próximo passo"),
                 g(r, "URLs de busca (leismunicipais / SAPL)"), "", ""])
ordem = {"Fase 2 — varredura manual": 0, "Fase 1 — enviar e-SIC": 1, "Fechado (não enviar)": 2}
rows.sort(key=lambda x: (ordem[x[0]], x[1]))

cab = ["Fase", "Nº e-SIC", "Município", "UF", "Grupo / risco", "Aba na régua", "Instrumento (eixo 1)",
       "Status no log", "Por que está aqui", "O que falta (pergunta específica)", "Onde buscar (leitura 23/09)",
       "Próximo passo (mestre)", "URLs de busca", "Resultado da busca (preencher)", "Data"]
# ---------------------------------------------------------------- preserva o que o autor preencheu
preench = {}
if os.path.exists(OUT):
    try:
        wbo = openpyxl.load_workbook(OUT, read_only=True)
        for sh in wbo.sheetnames:
            it2 = wbo[sh].iter_rows(values_only=True); h2 = next(it2, None)
            if not h2 or "Município" not in h2: continue
            ir = next((i for i, c in enumerate(h2) if c and str(c).startswith("Resultado da busca")), None)
            idt = h2.index("Data") if "Data" in h2 else None
            for r2 in it2:
                if ir is not None and r2[ir] not in (None, ""):
                    preench[(r2[h2.index("Município")], r2[h2.index("UF")])] = (r2[ir], r2[idt] if idt is not None else "")
    except Exception as e:
        print("aviso: não li a lista anterior:", e)
for r in rows:
    if (r[2], r[3]) in preench: r[13], r[14] = preench[(r[2], r[3])]

# ---------------------------------------------------------------- fila completa (todos os casos abertos)
import urllib.parse, glob as _glob
wbm = openpyxl.load_workbook(MP, read_only=True); wsm = wbm["consolidado"]
itm = wsm.iter_rows(values_only=True); H = next(itm)
def G(r, k): return (str(r[H.index(k)]) if k in H and r[H.index(k)] not in (None, "None", "nan") else "")
ESIC = {(d["mun"], d["uf"]): d["n"] for d in linhas}
LEG = os.path.join(R, "03 - Dados/_data/Legislacao e contratos TZ")
arquivos = {}
for p in _glob.glob(os.path.join(LEG, "normas", "*", "*")) + _glob.glob(os.path.join(LEG, "contratos", "*", "*")):
    b = os.path.basename(p); mm = re.match(r"^(?:[A-Z]{2}__)?(.+?)-([A-Z]{2}) - ", b)
    if mm: arquivos.setdefault((mm.group(1).strip(), mm.group(2)), []).append(("N" if os.sep + "normas" + os.sep in p else "C"))
fila = []
for r in itm:
    if not r[0] or G(r, "Situação") not in ("Ativa", "Encerrada", "Pista (a verificar)"): continue
    su = G(r, "Situação unificada (controle)")
    if su == "Fechado": continue
    mun, uf = G(r, "Município"), G(r, "UF")
    pop = r[H.index("População (2022)")]
    try: pop = int(float(str(pop).replace(".", "").replace(",", "."))) if pop not in (None, "") else None
    except ValueError: pop = None
    classe = G(r, "Classe da leitura crítica (23/09)"); portao = G(r, "Régua — portão").lower()
    inst = G(r, "Instrumento (eixo 1)").lower(); vig = G(r, "Vigência — última evidência (leitura 23/09)").lower()
    opge = G(r, "Operador × GE — resultado (cruzamento)"); sug = G(r, "Operador × GE — sugestão por nome (a conferir)")
    nlev = G(r, "Fontes — nº de levantamentos (recontagem)"); lev = G(r, "Fontes — levantamentos (recontagem)")
    port_ind = (not portao) or portao.startswith("a verificar") or portao.startswith("não determinável")
    # 25/09/2026: não pedir ao autor texto de norma que já foi lido (erro apontado por ele: 4 de 9 da prioridade A já estavam lidos)
    _txt = " ".join([G(r, "Status no log"), G(r, "Obs. legal"), G(r, "Instrumento — base da decisão"), G(r, "Régua — evidência do portão")])
    lido = bool(re.search(r"(?<!não )(?<!nao )\b(lid[ao]s?|transcrit[ao]s?)\b", _txt, re.I))
    direta = opge.startswith("sem operador privado") or opge.startswith("operador público")
    tarefas = []
    if classe.startswith("Risco de falso positivo") or G(r, "Situação").startswith("Pista"):
        tarefas.append("EXISTÊNCIA: confirmar que há TZ para todos (não só eleitoral, temporária, por grupo ou linha)")
    if G(r, "Situação") == "Encerrada" or "ler prazo" in su.lower():
        tarefas.append("ENCERRAMENTO: ato que encerrou e data; havia prazo na norma?")
    if not lido and (inst in ("", "não encontrado", "a verificar", "nenhum ato") or "localizar norma" in (su + classe).lower()):
        tarefas.append("NORMA: localizar lei/decreto que institui (nº, data, texto integral)")
    if port_ind and not lido:
        tarefas.append("PORTÃO: ler o dispositivo — há cadastro, residência, categoria, prazo ou linha?")
    elif port_ind and lido:
        tarefas.append("PORTÃO: norma já lida — falta regulamento ou prova de como opera (não reenviar a lei)")
    if not direta and (opge in ("", "não apurado") or opge.startswith("operador nomeado") or opge.startswith("sugestão")):
        tarefas.append("OPERADOR: contrato vigente e CNPJ da operadora" + (f" (conferir sugestão: {sug.split(' (')[0]})" if sug else ""))
    if opge.startswith("sem operador privado (declarado"):
        tarefas.append("OPERADOR: confirmar que a própria Prefeitura opera (frota, motoristas)")
    if not vig or vig.startswith("duvidosa") or vig.startswith("não apurada"):
        tarefas.append("VIGÊNCIA: prova de operação em 2025–2026 (notícia oficial, contrato, empenho)")
    if not G(r, "Nº linhas"):
        tarefas.append("COBERTURA: nº de linhas da rede municipal")
    esc = 0.0
    esc += 3 if tarefas and tarefas[0].startswith("EXISTÊNCIA") else 0
    esc += 2 if port_ind else 0
    esc += (2 if pop < 50000 else 0) + (1 if pop < 20000 else 0) if pop else 0
    esc += 1 if any(x.startswith("OPERADOR") for x in tarefas) else 0
    esc += 1 if nlev in ("0", "") else (0.5 if nlev == "1" else 0)
    esc += 1 if any(x.startswith("VIGÊNCIA") for x in tarefas) else 0
    if su.startswith("Aguarda e-SIC"): esc -= 5
    prio = "A" if esc >= 7 else ("B" if esc >= 4 else "C")
    if su.startswith("Aguarda e-SIC"): prio = "D — aguarda e-SIC"
    ibge = G(r, "Código IBGE").split(".")[0]
    q = urllib.parse.quote(f'"{mun}" {uf} "tarifa zero" OR "transporte gratuito" OR "passe livre" lei')
    qd = f"https://queridodiario.ok.org.br/pesquisa?term=%22tarifa+zero%22&territory_id={ibge}" if len(ibge) == 7 else ""
    arq = arquivos.get((mun, uf), [])
    fila.append([prio, round(esc, 1), mun, uf, pop or "", G(r, "Situação"), su, " · ".join(tarefas),
                 ("[TEXTO JÁ LIDO] " if lido else "") + G(r, "Legislação")[:200], G(r, "Link Legislação"), G(r, "Régua — portão")[:120], G(r, "Operador")[:150],
                 opge, f"{nlev} — {lev}" if lev else (nlev or "—"), f"{arq.count('N')} norma(s), {arq.count('C')} contrato(s)",
                 G(r, "Busca recomendada (leitura 23/09)")[:400], G(r, "URLs de busca (leismunicipais / SAPL)"),
                 f"https://www.google.com/search?q={q}", qd, ESIC.get((mun, uf), ""), "", ""])
    if (mun, uf) in preench: fila[-1][-2], fila[-1][-1] = preench[(mun, uf)]
fila.sort(key=lambda x: (x[0], -x[1], x[4] if isinstance(x[4], int) else 10**9))
cabf = ["Prioridade", "Escore", "Município", "UF", "População 2022", "Situação", "Situação unificada", "O que buscar (tarefas)",
        "Legislação conhecida", "Link legislação", "Portão atual", "Operador (mestre)", "Operador × GE (cruzamento 25/09)",
        "Levantamentos externos", "Arquivos já salvos", "Onde buscar (leitura 23/09)", "URLs (leismunicipais / SAPL)",
        "Busca Google", "Querido Diário", "Nº e-SIC", "Resultado da busca (preencher)", "Data"]

out = openpyxl.Workbook(); wf = out.active; wf.title = "Fila completa"
wf.append(cabf)
for r in fila: wf.append(r)
corp = {"A": "F8CBAD", "B": "FFF2CC", "C": "E2EFDA", "D": "EDEDED"}
for c in wf[1]:
    c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1F4E78"); c.alignment = Alignment(wrap_text=True, vertical="top")
for i, w in enumerate([10, 7, 22, 5, 10, 12, 24, 70, 40, 30, 30, 30, 30, 30, 16, 50, 35, 18, 18, 8, 40, 11], 1):
    wf.column_dimensions[get_column_letter(i)].width = w
for row in wf.iter_rows(min_row=2):
    fcor = PatternFill("solid", fgColor=corp[str(row[0].value)[0]])
    for c in row: c.alignment = Alignment(wrap_text=True, vertical="top"); c.fill = fcor
    for c in (row[9], row[17], row[18]):
        if c.value and str(c.value).startswith("http"): c.hyperlink = str(c.value).split(" ")[0]; c.value = "abrir" if c is not row[9] else c.value
wf.freeze_panes = "D2"; wf.auto_filter.ref = wf.dimensions
ws = out.create_sheet("e-SIC (Fases 1-2)")
ws.append(cab)
for r in rows:
    ws.append(r)
hdr = PatternFill("solid", fgColor="1F4E78"); cores = {"Fase 2": "FFF2CC", "Fase 1": "DDEBF7", "Fechad": "E2EFDA"}
for c in ws[1]:
    c.font = Font(bold=True, color="FFFFFF"); c.fill = hdr; c.alignment = Alignment(wrap_text=True, vertical="top")
larg = [22, 8, 22, 5, 22, 13, 16, 45, 50, 60, 50, 45, 40, 40, 11]
for i, w in enumerate(larg, 1):
    ws.column_dimensions[get_column_letter(i)].width = w
for row in ws.iter_rows(min_row=2):
    f = PatternFill("solid", fgColor=cores[row[0].value[:6]])
    for c in row:
        c.alignment = Alignment(wrap_text=True, vertical="top"); c.fill = f
ws.freeze_panes = "D2"; ws.auto_filter.ref = ws.dimensions
lm = out.create_sheet("Leia-me")
for l in [f"Busca ativa — lista de trabalho (gerada em {datetime.date.today():%d/%m/%Y} por _meta/scripts/exportar_lista_busca_ativa.py).",
          "Fonte: Fase 1/Fase 2 de 'e-SIC — pedidos de informação por município.md' + planilha-mestre (Status no log, Próximo passo, Busca recomendada).",
          "Ordem: Fase 2 (varredura manual, amarelo) → Fase 1 (enviar e-SIC, azul) → Fechados (verde, só referência).",
          "Regra para fechar subtipo (A.2c): norma lida no dispositivo + notícia de operação datada, OU documento de operação (contrato/edital/aditivo/empenho).",
          "Preencha 'Resultado da busca' e mande os documentos no chat; a atualização do log/mestre/régua é feita por script.",
          "Regra do autor (25/09/2026): nenhum caso vai para a Fase 1 antes de uma rodada de busca do autor.",
          "Regra do autor (25/09/2026): nenhum caso sai da lista sem os arquivos da norma/contrato salvos em 03 - Dados/_data/Legislacao e contratos TZ/.",
          "",
          "Aba 'Fila completa' (desde 25/09/2026): todos os casos abertos da base-mestre (Ativa, Encerrada, Pista; exceto Situação unificada = Fechado).",
          "Prioridade A/B/C pelo escore: +3 existência em dúvida (risco de falso positivo ou pista) · +2 portão indeterminado · +2 população < 50 mil (+1 se < 20 mil) · +1 operador a identificar · +1 sem levantamento externo (+0,5 se só 1) · +1 vigência duvidosa. A ≥ 7 · B 4–6,5 · C < 4 · D = aguarda e-SIC.",
          "O escore reflete o diagnóstico de 25/09 (lacunas de portão e operador nos municípios pequenos). Não é juízo sobre o caso.",
          "'Resultado da busca' e 'Data' preenchidos à mão são preservados quando a lista é regerada (casados por Município + UF).",
          "Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni"]:
    lm.append([l])
lm.column_dimensions["A"].width = 140
out.save(OUT)
print("OK ->", os.path.relpath(OUT, R), "| e-SIC:", {k: sum(1 for r in rows if r[0] == k) for k in ordem}, "| fila:", {p: sum(1 for r in fila if r[0] == p) for p in sorted(set(r[0] for r in fila))})
