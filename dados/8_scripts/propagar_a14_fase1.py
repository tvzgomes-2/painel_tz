#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""propagar_a14_fase1.py — Fase 1 (mecânica) da propagação da renumeração de
camadas A.1.4 (18/09/2026) à planilha Tipologias TZ - consolidado.xlsx.

Escopo deliberadamente estreito, por pedido do autor (20/09/2026): só toca
casos já assentados/decididos (A.1.4, D.1, e a confirmação do autor de hoje
sobre SCS/Aquiraz/Eusébio). NÃO abre nenhuma decisão de caso nova — Palmas/TO
(episódios), Cacoal/RO, Ubiratã/PR, Picos/PI, Getulina/SP, Itapeva/SP e os
"a verificar"/"não determinável" de `1 Universal` ficam de fora, exatamente
como estavam.

Uso: python propagar_a14_fase1.py [--gravar]
"""
import argparse, datetime, os, shutil, sys
import openpyxl

RAIZ = os.environ.get("TZ_VAULT") or os.path.expanduser("~/mnt/doutorado")
TIP = os.path.join(RAIZ, "03 - Dados", "_data", "casos por fonte", "Tipologias TZ - consolidado.xlsx")
HOJE = datetime.date.today().strftime("%d/%m/%Y")
COL_SUB = "Subtipo (A.1.4, 20-09-2026)"

RENOMEAR = {
    "2 Procedimento": "1b Procedimento",
    "5 Espacial-periferico": "2b Espacial-periferico",
    "4a Temporal-dias": "2c Temporal-dias",
    "4b Temporal-eventos": "2d Temporal-eventos",
    "3 Grupo social": "2a Grupo social (residual)",
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(TIP):
        sys.exit(f"não achei {TIP}")

    wb = openpyxl.load_workbook(TIP)

    print("=== Plano ===\n")

    # 1) Renomear abas assentadas
    for antigo, novo in RENOMEAR.items():
        if antigo in wb.sheetnames:
            n = wb[antigo].max_row - 1
            print(f"RENOMEAR aba: '{antigo}' ({n} linhas) -> '{novo}'")
        else:
            print(f"⚠️ aba '{antigo}' não encontrada, pulando")

    # 2) Mover a linha de SCS de '3 Grupo social' para '1 Universal' (Subtipo 1c)
    ws_grupo = wb["3 Grupo social"]
    hdr_grupo = [str(c.value).strip() if c.value else "" for c in ws_grupo[1]]
    ci_grupo = {h: i for i, h in enumerate(hdr_grupo)}
    scs_row = None
    scs_rownum = None
    for r in ws_grupo.iter_rows(min_row=2):
        mun = r[ci_grupo.get("Município", 0)].value
        if mun and str(mun).strip() == "São Caetano do Sul":
            scs_row = {h: r[ci_grupo[h]].value for h in hdr_grupo if h in ci_grupo}
            scs_rownum = r[0].row
            break
    if scs_row:
        print(f"\nMOVER: São Caetano do Sul/SP, linha {scs_rownum} de '3 Grupo social' -> "
              f"'1 Universal', Subtipo=1c (residência não retira universalidade, A.1.4/D.1; "
              f"confirmado pelo autor 20/09/2026 apesar da formulação ainda desatualizada no CLAUDE.md)")
        print(f"   dados atuais: {scs_row}")
    else:
        print("\n⚠️ Linha de São Caetano do Sul não encontrada em '3 Grupo social'")

    # 3) '1 Universal': nova coluna Subtipo, preenchida só onde já está assentado
    ws_uni = wb["1 Universal"]
    hdr_uni = [str(c.value).strip() if c.value else "" for c in ws_uni[1]]
    ci_uni = {h: i for i, h in enumerate(hdr_uni)}
    col_portao = ci_uni.get("Portão")

    tag_1a = []
    tag_1c = []
    for r in ws_uni.iter_rows(min_row=2):
        mun = r[ci_uni.get("Município", 0)].value
        if not mun:
            continue
        portao = (r[col_portao].value or "").strip() if col_portao is not None else ""
        if portao == "nenhum":
            tag_1a.append(str(mun))
        elif str(mun).strip() in ("Aquiraz", "Eusébio"):
            tag_1c.append(str(mun))

    print(f"\n'1 Universal': nova coluna '{COL_SUB}' (última coluna)")
    print(f"  Subtipo=1a (Portão='nenhum'): {len(tag_1a)} linhas -> {tag_1a}")
    print(f"  Subtipo=1c (residência, Aquiraz/Eusébio, confirmado hoje): {tag_1c}")
    print(f"  Demais linhas (a verificar / não determinável / tempo / prazo / procedimento "
          f"isolado): ficam com Subtipo em branco, sem decisão nova")

    # 4) Nota no RESUMO
    print(f"\nRESUMO: nova linha de nota datada {HOJE}")

    if not a.gravar:
        print("\n\nnada foi escrito. Para aplicar: --gravar")
        return

    # === EXECUÇÃO ===
    bk = TIP.replace(".xlsx", f".BACKUP-{datetime.datetime.now():%Y%m%d-%H%M}-pre-propagacao-A14-fase1.xlsx")
    shutil.copy2(TIP, bk)
    print(f"\nbackup: {os.path.basename(bk)}")

    # mover SCS primeiro (antes de renomear '3 Grupo social', para achar a aba pelo nome antigo)
    if scs_row:
        # remove da aba de origem
        ws_grupo.delete_rows(scs_rownum)
        # adiciona coluna Subtipo em '1 Universal' se ainda não existir (feito abaixo tb)
        if COL_SUB not in hdr_uni:
            ws_uni.cell(row=1, column=len(hdr_uni) + 1, value=COL_SUB)
            hdr_uni.append(COL_SUB)
            ci_uni[COL_SUB] = len(hdr_uni) - 1
        linha = []
        for h in hdr_uni:
            if h == "Subtipo (A.1.4, 20-09-2026)":
                linha.append("1c")
            elif h == "Situação":
                linha.append("Ativa (1c — universal, sub-marcado residência, desde 15/07/2026)")
            elif h == "Portão":
                linha.append("pessoa (residência)")
            elif h == "Portão — evidência":
                linha.append(
                    f"{HOJE}: movida de '3 Grupo social' — A.1.4/D.1 (18/09/2026): residência não "
                    f"retira a universalidade (segue Kębłowski 2020, não Huré/Passalacqua/Poinsot "
                    f"2025 — questão Tallinn fechada). SCS é universal com sub-marcação (1c), não "
                    f"grupo social parcial. ⚠️ Confirmado pelo autor em 20/09/2026 apesar de o "
                    f"CLAUDE.md, na mesma data, ainda descrever o caso como 'revogou a "
                    f"universalidade'/'hoje camada 4 — grupo social' — nomenclatura desatualizada, "
                    f"não decisão substantiva conflitante. Dados originais desta linha (aba '3 Grupo "
                    f"social', Grupo/Programa/Confiança/Fonte): {scs_row}"
                )
            else:
                linha.append(scs_row.get(h, ""))
        ws_uni.append(linha)
        print("SCS: linha movida para '1 Universal' com Subtipo=1c")

    # coluna Subtipo em '1 Universal' — preencher 1a e 1c (Aquiraz/Eusébio) nas linhas existentes
    if COL_SUB not in hdr_uni:
        ws_uni.cell(row=1, column=len(hdr_uni) + 1, value=COL_SUB)
        hdr_uni.append(COL_SUB)
    col_sub_idx = hdr_uni.index(COL_SUB) + 1  # 1-based
    hdr_uni2 = [str(c.value).strip() if c.value else "" for c in ws_uni[1]]
    ci_uni2 = {h: i for i, h in enumerate(hdr_uni2)}
    col_portao2 = ci_uni2.get("Portão")
    col_mun2 = ci_uni2.get("Município", 0)
    n_1a = n_1c = 0
    for r in ws_uni.iter_rows(min_row=2):
        mun = r[col_mun2].value
        if not mun:
            continue
        portao = (r[col_portao2].value or "").strip() if col_portao2 is not None else ""
        rownum = r[0].row
        if portao == "nenhum":
            ws_uni.cell(row=rownum, column=col_sub_idx, value="1a")
            n_1a += 1
        elif str(mun).strip() in ("Aquiraz", "Eusébio"):
            ws_uni.cell(row=rownum, column=col_sub_idx, value="1c")
            n_1c += 1
    print(f"'1 Universal': Subtipo preenchido — {n_1a} como 1a, {n_1c} como 1c")

    # renomear abas assentadas (por último, depois de mexer em '3 Grupo social' pelo nome antigo)
    for antigo, novo in RENOMEAR.items():
        if antigo in wb.sheetnames:
            wb[antigo].title = novo
    print("abas renomeadas:", ", ".join(RENOMEAR.values()))

    # nota no RESUMO
    rs = wb["RESUMO"]
    rs.append([
        f"⚠️ Nota de {HOJE}",
        "propagação Fase 1 da renumeração A.1.4 (mecânica, decisão do autor)",
        "", "",
        f"Abas renomeadas para a numeração de 18/09/2026 (A.1.4): '2 Procedimento'→'1b Procedimento', "
        f"'5 Espacial-periferico'→'2b Espacial-periferico', '4a Temporal-dias'→'2c Temporal-dias', "
        f"'4b Temporal-eventos'→'2d Temporal-eventos', '3 Grupo social'→'2a Grupo social (residual)'. "
        f"São Caetano do Sul movida de '2a Grupo social' para '1 Universal' com Subtipo=1c (residência "
        f"não retira universalidade — A.1.4/D.1, confirmado pelo autor hoje). Em '1 Universal' (172 "
        f"linhas + SCS), nova coluna '{COL_SUB}': {n_1a} linhas com Portão='nenhum' marcadas 1a; "
        f"Aquiraz/CE e Eusébio/CE marcadas 1c (residência, mesma decisão de SCS). "
        f"NÃO tocado, propositalmente — segue sem Subtipo, nenhuma decisão de caso nova aberta: "
        f"Palmas/TO (episódios), Cacoal/RO, Ubiratã/PR, Picos/PI, Getulina/SP, Itapeva/SP "
        f"(procedimento, confiança média) e as {172 - n_1a - 2} linhas 'a verificar'/'não "
        f"determinável'/'tempo' de '1 Universal'. Ver [[Regras de classificacao das reguas]] A.1.4, "
        f"D.1 e [[Pendências]]. Números desta aba RESUMO seguem NÃO recalculados."
    ])
    print("RESUMO: nota adicionada")

    wb.save(TIP)
    print(f"\n✅ gravado: {TIP}")

if __name__ == "__main__":
    main()
