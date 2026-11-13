#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consolida na planilha-mestre (Municípios TZ - consolidado.xlsx) as informações da Base integrada.
Decisões do autor (24/09/2026): a mestre continua canônica e é AMPLIADA (colunas originais preservadas, novas no fim);
desempate = valor apoiado em documento > fonte mais recente; o valor preterido fica em '… — outras versões' e o caso
é marcado em 'Revisar'. Idempotente: reescreve só as colunas que ele mesmo cria (+ Operador, com histórico)."""
import re, unicodedata, shutil, datetime, collections, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
M = "03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx"
BI = "03 - Dados/_data/casos por fonte/Base integrada - casos TZ (23-09-2026).xlsx"
def n(s): return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip())
def k(s): return re.sub(r"[^a-z0-9]", "", n(s))
ws = openpyxl.load_workbook(BI, read_only=True)["Municípios"]
rr = list(ws.iter_rows(values_only=True)); H = rr[0]
B = {(n(x[0]), x[1]): {h: (str(v) if v not in (None, "") else "") for h, v in zip(H, x)} for x in rr[1:]}
def g(d, *cols):
    for c in cols:
        v = d.get(c, "")
        if v: return v
    return ""
FONTES = {"fonte_brinco_2017": "Brinco (2017)", "fonte_santini_2019": "Santini (2019)", "fonte_vermander_2021": "Vermander (2021)", "fonte_fernandes_pereira_et_al_2023": "Fernandes Pereira et al. (2023)", "fonte_angelo_2023": "Angelo (2023)", "fonte_ntu_2024_1a_ed": "NTU (2024)", "fonte_ntu_2025_2a_ed": "NTU (2025)", "fonte_ntu_2026_3a_ed": "NTU (2026)", "fonte_unb_geourb_2025": "UnB/Geourb (2025)"}
CU = "[CONTROLE-ÚNICO-11-09] "; LC = "[LEITURA-CRÍTICA] "; UN = "[CONTROLE-UNIFICADO] "; E1 = "[INSTRUMENTO-EIXO1] "; E2 = "[CONTRATOS-EIXO2] "; CS = "[CONSOLIDADA-18-09] "
def novas(d, mestre_op):
    out = collections.OrderedDict(); rev = []
    # régua descritiva
    out["Régua — aba"] = g(d, UN + "Aba na régua")
    out["Régua — subtipo"] = g(d, UN + "Subtipo (régua)")
    out["Régua — portão"] = g(d, "[RÉGUA-1] Portão", "[RÉGUA-3] Portão", UN + "Portão (régua)")
    out["Régua — evidência do portão"] = g(d, "[RÉGUA-1] Portão — evidência", "[RÉGUA-3] Portão — evidência")[:3000]
    out["Cobertura da rede"] = " — ".join(x for x in (g(d, LC + "Cobertura da rede"), g(d, LC + "Cobertura — evidência")) if x)
    out["Vigência — última evidência (leitura 23/09)"] = " · ".join(x for x in (g(d, LC + "Vigência"), g(d, LC + "Última evidência"), g(d, LC + "Fonte da vigência")) if x)
    out["Trajetória (régua descritiva, ficha)"] = g(d, CS + "Régua descritiva — trajetória (Cap 5, texto da ficha)")[:3000]
    # eixo 1
    out["Instrumento — base da decisão"] = g(d, E1 + "Base da decisão")
    out["Portão visível no texto da norma"] = g(d, E1 + "Portão visível no texto")
    # eixo 2 e operador
    out["Prestação (eixo 2)"] = g(d, E2 + "eixo2")
    op2 = g(d, E2 + "operador_vigente")
    GEN = r"^(prefeitura|empresa privada|privad[ao]|privad[ao] \(nome nao identificado\)|publica|governo municipal|municipio|nao mencionado|nao identificado.*|nao informado)?$"
    op2_ok = bool(op2) and not re.search(r"mestre|n[aã]o identificad|indeterminad|n[aã]o nomead", op2, re.I)
    # regra: documento > mais recente, sem perder detalhe — só substitui o valor da mestre quando ele é vazio ou genérico
    escolhido = op2 if (op2_ok and (not mestre_op or re.match(GEN, n(mestre_op)))) else (mestre_op or (op2 if op2_ok else ""))
    out["_Operador"] = escolhido
    outras = []
    for c in ("[MESTRE] Operador", "[RÉGUA-1] Operador", CU + "operador_planilha", CU + "operador_confirmado", CS + "Operador — §2 da ficha", LC + "Operador", "[LEG-A-LOCALIZAR-94-07-09] operador", E2 + "operador_vigente"):
        v = d.get(c, "")
        STOP = r"^(empresa|viacao|transportes?|auto|prefeitura|municipio|de|da|do)+"
        kv, ke = re.sub(STOP, "", k(v)), re.sub(STOP, "", k(escolhido))
        mesma = k(v) == k(escolhido) or k(v) in k(escolhido) or (bool(kv and ke) and (kv[:6] == ke[:6] or kv[:12] in ke or ke[:12] in kv))
        if v and not mesma and v not in [o.split(": ", 1)[-1] for o in outras]:
            outras.append(c.split("]")[0][1:] + ": " + v[:300])
    out["Operador — outras versões"] = " ‖ ".join(outras)
    if escolhido and escolhido != mestre_op and mestre_op: rev.append("operador substituído (mestre era genérico) — conferir outras versões")
    if re.search(r"nova empresa|substitu|troca de operador|desde \d{2}/\d{2}/20\d{2}", op2 or "", re.I) and escolhido != op2: rev.append("operador pode ter mudado (ver outras versões)")
    if len(outras) >= 2: rev.append("operador: fontes nomeiam entidades diferentes")
    out["Operador — CNPJ"] = g(d, E2 + "cnpj")
    out["Remuneração do operador"] = g(d, E2 + "remuneracao_vigente", CU + "modelo_remuneracao", CU + "remuneracao_operador_ficha", LC + "Remuneração")
    out["Trajetória contratual"] = g(d, E2 + "trajetoria")
    out["Lacuna contratual"] = g(d, E2 + "lacuna")
    # régua analítica
    out["Tipologia analítica"] = g(d, CS + "Tipologia analítica (frontmatter da ficha)", CU + "tipologia_analitica", LC + "Tipologia analítica (ficha)")
    out["Mecanismo de custeio"] = g(d, CU + "mecanismo_custeio")
    out["Fonte de custeio"] = g(d, LC + "Fonte de custeio")
    out["Contrapartida"] = g(d, LC + "Contrapartida")
    out["Grupo econômico"] = g(d, LC + "Grupo econômico")
    # PlanMob
    out["PlanMob — declarado"] = g(d, CU + "planmob_declarado")
    out["PlanMob — ano"] = g(d, CU + "planmob_ano")
    out["PlanMob — instrumento"] = g(d, CU + "planmob_instrumento")
    out["PlanMob — nº da lei"] = g(d, CU + "planmob_num_lei")
    out["PlanMob — data da lei"] = g(d, "[TZxPLANMOB-09-09] data_lei_planmob")
    out["PlanMob — obrigado a ter"] = g(d, CU + "planmob_obrigado")
    out["PlanMob — ordem temporal (TZ × PlanMob)"] = g(d, CU + "planmob_ordem_temporal", "[TZxPLANMOB-09-09] ordem_temporal")
    # fontes do caso
    out["Fontes que registram o caso"] = "; ".join(v for c, v in FONTES.items() if d.get(CU + c))
    out["Nº de fontes"] = g(d, CU + "fonte_n_de_fontes", "[CRUZAMENTO-BIBLIO-02-09] n de fontes")
    out["Proveniência do caso"] = g(d, LC + "Proveniência do caso", CU + "fonte_do_caso", "[LEG-A-LOCALIZAR-94-07-09] fonte_do_caso")
    out["Caso temporário/eleitoral (fontes)"] = g(d, CU + "fonte_caso_temporario_eleitoral", "[CRUZAMENTO-BIBLIO-02-09] Caso temporário/eleitoral")
    # dados operacionais
    out["Dados operacionais (ficha §2)"] = g(d, CS + "Dados operacionais — §2 da ficha (texto completo)")[:3000]
    # estado da pesquisa
    out["Situação unificada (controle)"] = g(d, UN + "Situação unificada")
    out["Status no log"] = g(d, UN + "Status no log")
    out["Próximo passo"] = g(d, UN + "Próximo passo")
    out["e-SIC / varredura nº"] = g(d, UN + "e-SIC / varredura nº")
    out["Classe da leitura crítica (23/09)"] = g(d, LC + "Classe desta leitura", UN + "Classe da leitura 23/09 (original)")
    out["Tensão crítica (leitura 23/09)"] = g(d, LC + "Tensão crítica")
    out["Busca recomendada (leitura 23/09)"] = g(d, LC + "Busca recomendada (não executada)")
    out["O que faltava / onde buscar (09/09)"] = " · ".join(x for x in (g(d, CU + "o_que_falta"), g(d, CU + "onde_buscar")) if x)
    out["URLs de busca (leismunicipais / SAPL)"] = " · ".join(x for x in (g(d, CU + "url_leismunicipais"), g(d, CU + "url_sapl_provavel")) if x)
    out["Pista antiga (worklist 07/09)"] = " · ".join(x for x in (g(d, "[WORKLIST-89-07-09] pista_ja_levantada"), g(d, "[WORKLIST-89-07-09] termos_de_busca")) if x)
    out["Ficha — status"] = g(d, LC + "Status ficha")
    out["Ficha — completude (0-6)"] = g(d, "[COMPLETUDE-FICHAS] Score (0-6)")
    div = g(d, UN + "Divergências entre controles")
    if div: rev.append(div)
    out["Revisar"] = "; ".join(rev)
    out["Consolidado em"] = "2026-09-24"
    return out
ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy2(M, M.replace(".xlsx", f".BACKUP-{ts}-consolidacao.xlsx"))
wb = openpyxl.load_workbook(M); ws = wb["consolidado"]; h = [c.value for c in ws[1]]
cop = h.index("Operador") + 1
novos_h = None; trocas = 0; nrev = 0
for row in ws.iter_rows(min_row=2):
    if not row[0].value: continue
    d = B.get((n(row[0].value), row[1].value), {})
    mop = str(row[cop - 1].value or "")
    o = novas(d, mop)
    if novos_h is None:
        novos_h = [c for c in o if not c.startswith("_")]
        for c in novos_h:
            if c not in h: ws.cell(1, len(h) + 1, c); h.append(c)
    if o["_Operador"] and o["_Operador"] != mop:
        ws.cell(row[0].row, cop, o["_Operador"]); trocas += 1
    for c in novos_h: ws.cell(row[0].row, h.index(c) + 1, o[c] or None)
    if o["Revisar"]: nrev += 1
# formatação do cabeçalho: blocos novos em outra cor
for i, c in enumerate(h, 1):
    x = ws.cell(1, i); x.font = Font(bold=True, color="FFFFFF"); x.alignment = Alignment(wrap_text=True, vertical="top")
    x.fill = PatternFill("solid", fgColor="4472C4" if i <= 22 else "548235")
wb.save(M)
print("colunas", len(h), "| novas", len(novos_h), "| operador trocado", trocas, "| marcados Revisar", nrev)
