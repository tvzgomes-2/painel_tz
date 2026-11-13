#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""consolidar_4_abas.py — Fase 2 da propagação A.1.4 (20/09/2026): consolida
as 6 sub-abas de `Tipologias TZ - consolidado.xlsx` em 4 abas de primeiro
nível — uma por camada (1 Universal, 2 Parcial), uma para Encerradas (3) e
uma para Não TZ — por pedido explícito do autor.

======================================================================
O QUE MUDA
======================================================================
Antes (pós Fase 1): RESUMO, `1 Universal` (172), `1b Procedimento` (6),
`2a Grupo social (residual)` (4), `2b Espacial-periferico` (8),
`2c Temporal-dias` (26), `2d Temporal-eventos` (324).

Depois: RESUMO, `1 Universal`, `2 Parcial`, `3 Encerradas`, `Não TZ`.

Critério de destino — só reclassifica o que já está dito na própria planilha,
NENHUMA decisão de caso nova é aberta aqui:
  * Situação/Status == "Encerrada" (literal) → aba `3 Encerradas`, com o
    subtipo que o caso tinha antes de encerrar preservado numa coluna.
    (10 vêm de `1 Universal`, 1 de `1b Procedimento` = 11, batendo com o
    número canônico do CLAUDE.md: "167 ativas + 11 encerradas".)
  * Situação == "Excluída (fora de escopo)" (só Teresina/PI, decisão do
    autor de 03/08/2026 já registrada na própria célula) → aba `Não TZ`.
  * Linha com Status "JÁ TEMOS (como encerrada — REVER)" (em
    `2c Temporal-dias`) NÃO é movida — o "REVER" é do próprio autor, sinal
    de que não está fechado; fica em `2 Parcial` com o texto intacto.
  * São Caetano do Sul tinha DUAS linhas em `1 Universal` (uma antiga,
    "Reclassificada", desatualizada; uma nova, "Ativa (1c...)", da Fase 1).
    São mescladas em uma linha canônica só: mantém a decisão 1c da Fase 1,
    acrescenta ao histórico o texto da linha antiga (lei 6141/2023) para não
    perder o registro legislativo.
  * `1b Procedimento` (ativas) entra em `1 Universal` com Subtipo="1b" —
    já é universal por definição A.1.4, o portão de procedimento é atributo,
    não camada própria.
  * `2a`/`2b`/`2c`/`2d` (menos a linha "REVER" acima) entram em `2 Parcial`
    com coluna Subtipo (2a/2b/2c/2d) e esquema superset de colunas
    (decisão do autor, 20/09/2026: preservar tudo, sem perda de dado).

USO  python consolidar_4_abas.py [--gravar]
"""
import argparse
import datetime
import os
import shutil
import sys

RAIZ = os.environ.get("TZ_VAULT") or os.getcwd()
TIP = os.path.join(RAIZ, "03 - Dados", "_data", "casos por fonte",
                    "Tipologias TZ - consolidado.xlsx")
HOJE = datetime.date.today().strftime("%d/%m/%Y")

COLS_UNIVERSAL = ["Município", "UF", "Subtipo", "Situação", "Ano",
                   "Legislação", "Link Legislação", "Operador", "Fontes",
                   "Portão", "Portão — evidência"]
COLS_PARCIAL = ["Município", "UF", "Subtipo", "Situação/Status",
                 "Início/Ano", "Grupo", "Escopo", "Dias", "Programa",
                 "Código IBGE", "Modelo", "Confiança", "Fonte"]
COLS_ENCERRADAS = ["Município", "UF", "Subtipo (antes de encerrar)",
                     "Situação", "Ano", "Legislação", "Link Legislação",
                     "Operador", "Fontes", "Portão", "Portão — evidência"]
COLS_NAO_TZ = COLS_UNIVERSAL


def val(r, ci, nome):
    i = ci.get(nome)
    return r[i].value if i is not None and i < len(r) else None


def sheet_rows(ws):
    hdr = [str(c.value).strip() if c.value else "" for c in ws[1]]
    ci = {h: i for i, h in enumerate(hdr)}
    return hdr, ci, list(ws.iter_rows(min_row=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()
    import openpyxl
    if not os.path.exists(TIP):
        sys.exit(f"🔴 não achei {TIP}")
    wb = openpyxl.load_workbook(TIP)

    # ---------- 1 Universal + 1b Procedimento → 1 Universal / 3 Encerradas / Não TZ ----------
    ws1 = wb["1 Universal"]
    hdr1, ci1, rows1 = sheet_rows(ws1)

    scs_antiga = None
    scs_nova = None
    universal_novas, encerradas, nao_tz = [], [], []

    for r in rows1:
        m = val(r, ci1, "Município")
        u = val(r, ci1, "UF")
        sit = str(val(r, ci1, "Situação") or "")
        if not m:
            continue
        if m == "São Caetano do Sul" and sit.startswith("Reclassificada"):
            scs_antiga = {h: val(r, ci1, h) for h in hdr1}
            continue
        if m == "São Caetano do Sul" and sit.startswith("Ativa (1c"):
            scs_nova = {h: val(r, ci1, h) for h in hdr1}
            continue
        if sit.startswith("Excluída"):
            nao_tz.append({h: val(r, ci1, h) for h in hdr1})
            continue
        if sit == "Encerrada":
            d = {h: val(r, ci1, h) for h in hdr1}
            encerradas.append({
                "Município": m, "UF": u,
                "Subtipo (antes de encerrar)": d.get("Subtipo (A.1.4, 20-09-2026)") or "",
                "Situação": "Encerrada", "Ano": d.get("Ano"),
                "Legislação": d.get("Legislação"),
                "Link Legislação": d.get("Link Legislação"),
                "Operador": d.get("Operador"), "Fontes": d.get("Fontes"),
                "Portão": d.get("Portão"),
                "Portão — evidência": d.get("Portão — evidência"),
            })
            continue
        universal_novas.append({
            "Município": m, "UF": u,
            "Subtipo": val(r, ci1, "Subtipo (A.1.4, 20-09-2026)"),
            "Situação": sit, "Ano": val(r, ci1, "Ano"),
            "Legislação": val(r, ci1, "Legislação"),
            "Link Legislação": val(r, ci1, "Link Legislação"),
            "Operador": val(r, ci1, "Operador"), "Fontes": val(r, ci1, "Fontes"),
            "Portão": val(r, ci1, "Portão"),
            "Portão — evidência": val(r, ci1, "Portão — evidência"),
        })

    if not scs_nova:
        sys.exit("🔴 não achei a linha nova de São Caetano do Sul (1c) — abortando")
    fontes_merged = scs_nova.get("Fontes") or ""
    if scs_antiga:
        fontes_merged += (
            "\n\n[Linha histórica mesclada em " + HOJE + ", antes 'Reclassificada "
            "(parcial — grupo social)']: Legislação=" + str(scs_antiga.get("Legislação")) +
            " | Link=" + str(scs_antiga.get("Link Legislação")) +
            " | Operador=" + str(scs_antiga.get("Operador")) +
            " | Fontes=" + str(scs_antiga.get("Fontes")) +
            " | Portão — evidência=" + str(scs_antiga.get("Portão — evidência"))
        )
    universal_novas.append({
        "Município": "São Caetano do Sul", "UF": "SP",
        "Subtipo": scs_nova.get("Subtipo (A.1.4, 20-09-2026)") or "1c",
        "Situação": "Ativa (1c — universal, sub-marcado residência, desde 15/07/2026)",
        "Ano": scs_antiga.get("Ano") if scs_antiga else scs_nova.get("Ano"),
        "Legislação": scs_antiga.get("Legislação") if scs_antiga else scs_nova.get("Legislação"),
        "Link Legislação": scs_antiga.get("Link Legislação") if scs_antiga else scs_nova.get("Link Legislação"),
        "Operador": scs_antiga.get("Operador") if scs_antiga else scs_nova.get("Operador"),
        "Fontes": fontes_merged,
        "Portão": scs_nova.get("Portão"),
        "Portão — evidência": scs_nova.get("Portão — evidência"),
    })

    ws1b = wb["1b Procedimento"]
    hdr1b, ci1b, rows1b = sheet_rows(ws1b)
    for r in rows1b:
        m = val(r, ci1b, "Município")
        if not m:
            continue
        sit = str(val(r, ci1b, "Situação") or "")
        d = {h: val(r, ci1b, h) for h in hdr1b}
        if sit == "Encerrada":
            encerradas.append({
                "Município": m, "UF": d.get("UF"),
                "Subtipo (antes de encerrar)": "1b",
                "Situação": "Encerrada", "Ano": d.get("Ano"),
                "Legislação": d.get("Legislação"),
                "Link Legislação": d.get("Link Legislação"),
                "Operador": d.get("Operador"), "Fontes": d.get("Fontes"),
                "Portão": d.get("Portão"),
                "Portão — evidência": d.get("Portão — evidência"),
            })
            continue
        universal_novas.append({
            "Município": m, "UF": d.get("UF"), "Subtipo": "1b",
            "Situação": sit, "Ano": d.get("Ano"),
            "Legislação": d.get("Legislação"),
            "Link Legislação": d.get("Link Legislação"),
            "Operador": d.get("Operador"), "Fontes": d.get("Fontes"),
            "Portão": d.get("Portão"),
            "Portão — evidência": d.get("Portão — evidência"),
        })

    # ---------- 2a/2b/2c/2d → 2 Parcial ----------
    parcial = []
    for nome_aba, subtipo in [("2a Grupo social (residual)", "2a"),
                                ("2b Espacial-periferico", "2b"),
                                ("2c Temporal-dias", "2c"),
                                ("2d Temporal-eventos", "2d")]:
        ws = wb[nome_aba]
        hdr, ci, rows = sheet_rows(ws)
        for r in rows:
            m = val(r, ci, "Município")
            if not m:
                continue
            d = {h: val(r, ci, h) for h in hdr}
            linha = {
                "Município": m, "UF": d.get("UF"), "Subtipo": subtipo,
                "Situação/Status": d.get("Status") or d.get("Situação"),
                "Início/Ano": d.get("Início") or d.get("Ano"),
                "Grupo": d.get("Grupo"), "Escopo": d.get("Escopo"),
                "Dias": d.get("Dias"), "Programa": d.get("Programa"),
                "Código IBGE": d.get("Código IBGE"), "Modelo": d.get("Modelo"),
                "Confiança": d.get("Confiança"), "Fonte": d.get("Fonte"),
            }
            parcial.append(linha)

    print(f"1 Universal (novo):  {len(universal_novas)} linhas")
    print(f"2 Parcial (novo):    {len(parcial)} linhas")
    print(f"3 Encerradas (novo): {len(encerradas)} linhas")
    print(f"Não TZ (novo):       {len(nao_tz)} linhas")
    print(f"SCS mesclada: {'sim' if scs_antiga else 'NÃO havia linha antiga — só a nova'}")

    if not a.gravar:
        print("\nnada foi escrito. Para aplicar: --gravar")
        return

    bk = TIP.replace(".xlsx", f"-BACKUP-{datetime.datetime.now():%Y%m%d-%H%M}-pre-consolidar-4-abas.xlsx")
    shutil.copy2(TIP, bk)

    for nome in ["1b Procedimento", "2a Grupo social (residual)",
                 "2b Espacial-periferico", "2c Temporal-dias",
                 "2d Temporal-eventos"]:
        del wb[nome]

    ws1 = wb["1 Universal"]
    ws1.delete_rows(1, ws1.max_row)
    ws1.append(COLS_UNIVERSAL)
    for linha in universal_novas:
        ws1.append([linha.get(h) for h in COLS_UNIVERSAL])

    ws2 = wb.create_sheet("2 Parcial")
    ws2.append(COLS_PARCIAL)
    for linha in parcial:
        ws2.append([linha.get(h) for h in COLS_PARCIAL])

    ws3 = wb.create_sheet("3 Encerradas")
    ws3.append(COLS_ENCERRADAS)
    for linha in encerradas:
        ws3.append([linha.get(h) for h in COLS_ENCERRADAS])

    ws4 = wb.create_sheet("Não TZ")
    ws4.append(COLS_NAO_TZ)
    for linha in nao_tz:
        ws4.append([linha.get(h) for h in COLS_UNIVERSAL])

    rs = wb["RESUMO"]
    rs.append([f"⚠️ Nota de {HOJE}",
               "consolidação em 4 abas (decisão do autor)", "", "",
               f"Fase 2 da propagação A.1.4: 6 sub-abas (1 Universal, 1b Procedimento, "
               f"2a/2b/2c/2d) consolidadas em 4 — `1 Universal` ({len(universal_novas)}), "
               f"`2 Parcial` ({len(parcial)}, esquema superset de colunas), "
               f"`3 Encerradas` ({len(encerradas)}, bate com o canônico 11 do CLAUDE.md), "
               f"`Não TZ` ({len(nao_tz)} — Teresina/PI, exclusão de 03/08/2026). "
               f"São Caetano do Sul: duas linhas antigas mescladas em uma (1c), histórico "
               f"legislativo preservado no campo Fontes. Nenhuma decisão de caso nova "
               f"aberta — só reclassificação do que a própria planilha já dizia "
               f"(Situação='Encerrada'/'Excluída'). Script: "
               f"`_meta/scripts/consolidar_4_abas.py`."])
    wb.save(TIP)
    print(f"\n✅ consolidado em 4 abas · backup: {os.path.basename(bk)}")
    for s in wb.sheetnames:
        if s != "RESUMO":
            print(f"   {wb[s].max_row - 1:>4}  {s}")


if __name__ == "__main__":
    main()
