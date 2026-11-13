#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera um .xlsx a partir do Log de busca jurídica e contratual (markdown),
com coluna de situação resumida (Resolvido / Verificar / Pendente) para
retomada das buscas manuais.
"""
import re
from collections import Counter
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

SRC = "04 - Análises/Pesquisa legal/Log de busca jurídica e contratual — municípios.md"
OUT = "04 - Análises/Pesquisa legal/Log de busca jurídica e contratual — para Excel (22-09-2026).xlsx"

FIELDS = [
    ("Status", "Status"),
    ("Confiança real", "Confiança real"),
    ("Fundamento legal/contratual (planilha-mestre)", "Fundamento legal-contratual (mestre)"),
    ("Nome do programa", "Nome do programa"),
    ("Observação (worklist manual, 07–18/09/2026)", "Observação (worklist manual)"),
    ("Nota automatizada (18/09)", "Nota automatizada (18/09)"),
    ("Achado PNCP", "Achado PNCP"),
    ("Pista original (07/09)", "Pista original (07/09)"),
    ("Ano de início (registrado)", "Ano de início"),
    ("Notas de norma padronizada", "Notas de norma padronizada"),
    ("Próximo passo", "Próximo passo"),
    ("Última atualização deste log", "Última atualização do log"),
]

def bucket(status: str) -> str:
    s = status.strip()
    if s.startswith("Candidato"):
        return "Candidato (fora do universo)"
    if s.startswith("Fora do universo"):
        return "Fora do universo (parcial/não TZ)"
    if s.startswith("Resolvido"):
        return "Resolvido"
    if s.startswith("Em verificação") or "leitura provável, requer confirmação humana" in s:
        return "Verificar"
    return "Pendente"

def parse_block(block: str):
    m = re.match(r"#### (.+?) \(([A-Z]{2})\)", block)
    municipio, uf = (m.group(1), m.group(2)) if m else ("?", "?")
    data = {}
    for label_md, _ in FIELDS:
        pat = re.escape(label_md)
        m2 = re.search(r"\*\*" + pat + r"(?: \([^)]*\))?:\*\*\s*(.+?)(?=\n- \*\*|\n\n|\Z)", block, re.S)
        if m2:
            data[label_md] = m2.group(1).strip().replace("\n", " ")
    return municipio, uf, data

def main():
    content = open(SRC, encoding="utf-8").read()
    m = re.search(r"## Detalhe por município\n\n(.*)", content, re.S)
    detail = m.group(1)
    blocks = [b for b in re.split(r"\n(?=#### )", detail) if b.strip().startswith("#### ")]

    rows = []
    for b in blocks:
        municipio, uf, data = parse_block(b)
        status = data.get("Status", "")
        row = {
            "Município": municipio,
            "UF": uf,
            "Situação (resumo)": bucket(status),
        }
        for label_md, header in FIELDS:
            row[header] = data.get(label_md, "")
        rows.append(row)

    order = {"Candidato (fora do universo)": 0, "Pendente": 1, "Verificar": 2, "Resolvido": 3, "Fora do universo (parcial/não TZ)": 4}
    rows.sort(key=lambda r: (order.get(r["Situação (resumo)"], 9), r["Município"]))

    counts = Counter(r["Situação (resumo)"] for r in rows)

    headers = ["Município", "UF", "Situação (resumo)"] + [h for _, h in FIELDS]

    wb = openpyxl.Workbook()

    ws0 = wb.active
    ws0.title = "Resumo"
    ws0["A1"] = "Log de busca jurídica e contratual — retomada das buscas manuais"
    ws0["A1"].font = Font(bold=True, size=13)
    ws0["A2"] = "Gerado em 22/09/2026 a partir de: " + SRC
    ws0["A3"] = "Total de municípios no log:"
    ws0["B3"] = len(rows)
    r = 5
    ws0.cell(row=r, column=1, value="Situação").font = Font(bold=True)
    ws0.cell(row=r, column=2, value="Municípios").font = Font(bold=True)
    for situacao in ["Candidato (fora do universo)", "Pendente", "Verificar", "Resolvido", "Fora do universo (parcial/não TZ)"]:
        r += 1
        ws0.cell(row=r, column=1, value=situacao)
        ws0.cell(row=r, column=2, value=counts.get(situacao, 0))
    r += 2
    ws0.cell(row=r, column=1, value="Como usar:").font = Font(bold=True, italic=True)
    r += 1
    notas_uso = [
        "Aba 'Log' tem 1 linha por município, ordenada Candidato -> Pendente -> Verificar -> Resolvido.",
        "'Candidato (fora do universo)' = achado novo (ex.: varredura QD nacional), NAO conta nos 178/177 do panorama ate decisao do autor.",
        "'Situação (resumo)' é derivada do campo 'Status' detalhado (mesma aba, coluna ao lado).",
        "'Pendente' inclui: sem achado ainda, achados só de triagem automática (não é leitura jurídica),",
        "  e achados em catálogo (nota existe mas o texto integral não foi lido nesta rodada) - todos",
        "  são bons candidatos a busca manual, do mais fraco (triagem) ao mais forte (catálogo).",
        "'Verificar' = já há leitura provável (cita artigo da lei) ou uma pista com ressalva; confirmar, não buscar do zero.",
        "'Resolvido' = já fechado; só reabrir se achar algo que contradiga.",
        "Ao concluir uma busca manual, atualizar também o log fonte",
        "  (" + SRC + "),",
        "  para não se perder de novo - este .xlsx é um instantâneo, não é editado de volta automaticamente.",
    ]
    for linha in notas_uso:
        ws0.cell(row=r, column=1, value=linha)
        r += 1
    ws0.column_dimensions["A"].width = 100
    ws0.column_dimensions["B"].width = 14

    ws = wb.create_sheet("Log")
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4472C4")
        cell.alignment = Alignment(vertical="top", wrap_text=True)
    for row in rows:
        ws.append([row.get(h, "") for h in headers])

    fills = {
        "Candidato (fora do universo)": PatternFill("solid", fgColor="D9E1F2"),
        "Fora do universo (parcial/não TZ)": PatternFill("solid", fgColor="EDEDED"),
        "Pendente": PatternFill("solid", fgColor="FCE4E4"),
        "Verificar": PatternFill("solid", fgColor="FFF3CD"),
        "Resolvido": PatternFill("solid", fgColor="E2F0D9"),
    }
    sit_col = headers.index("Situação (resumo)") + 1
    for i, row in enumerate(rows, start=2):
        fill = fills.get(row["Situação (resumo)"])
        if fill:
            ws.cell(row=i, column=sit_col).fill = fill
        for c in range(1, len(headers) + 1):
            ws.cell(row=i, column=c).alignment = Alignment(vertical="top", wrap_text=True)

    widths = {
        "Município": 22, "UF": 6, "Situação (resumo)": 16, "Status": 42,
        "Confiança real": 24, "Fundamento legal-contratual (mestre)": 34,
        "Nome do programa": 22, "Observação (worklist manual)": 46,
        "Nota automatizada (18/09)": 30, "Achado PNCP": 40,
        "Pista original (07/09)": 30, "Ano de início": 12,
        "Notas de norma padronizada": 46, "Próximo passo": 40,
        "Última atualização do log": 20,
    }
    for i, h in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(i)].width = widths.get(h, 20)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(rows) + 1}"

    wb.save(OUT)
    print("OK ->", OUT)
    print(dict(counts))

if __name__ == "__main__":
    main()
