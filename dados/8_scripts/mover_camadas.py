#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""mover_camadas.py — executa as reclassificacoes de camada autorizadas pelo
autor em 19/09/2026, com registro de trajetoria.

======================================================================
O QUE MOTIVA
======================================================================
O gerador do portao (`enriquecer_regua_portao.py`) expos 8 casos com **portao
identificado que seguiam na aba `1 Universal`** — pelo criterio validado em
10/09/2026 eles ja nao sao camada 1. Lendo a evidencia de cada um, porem, eles
NAO sao o mesmo caso:

  * 4 casos (5 linhas) tem **norma lida ou dispositivo citado** → movidos aqui.
  * 3 casos se apoiam **so em fonte secundaria** (Mariana/MG e Assis/SP por
    parafrase jornalistica, Vargem Grande Paulista/SP por blog, com o
    dispositivo "nao confirmado no texto literal") → NAO movidos.
  * 1 caso (Aquiraz/CE) tem evidencia da lei, mas a propria ficha registra que
    "nao fecha isto como reclassificacao de camada" → NAO movido.

➡️ Rebaixar de camada por parafrase e o erro simetrico do que a regua proibe:
assim como nao se promove a camada 1 por ausencia de evidencia, nao se rebaixa
por ausencia de norma lida. Os 4 nao movidos seguem com o alerta impresso na
ficha e entram em Pendencias dizendo QUAL documento falta.

======================================================================
🆕 A ABA `4c Temporal-prazo`, e por que ela precisou existir
======================================================================
Cacoal/RO e Palmas/TO tem portao de tempo **por prazo de vigencia declarado na
norma** (Cacoal: Art. 5o limita a 12 meses; Palmas: decretos de um mes). A regra
de 10/09 diz que "prazo declarado na norma e portao de tempo" — camada 4 —, mas
as abas temporais existentes sao `4a Temporal-dias` (fins de semana) e
`4b Temporal-eventos` (eleitoral). **Prazo de vigencia nao e nenhum dos dois.**

Arquiva-los em "dias" seria erro de registro: diria que a gratuidade vale em
certos dias da semana, o que e falso. Por isso a aba `4c Temporal-prazo`.
⚠️ **E uma decisao de taxonomia, reversivel:** se o autor preferir outro destino,
basta mover as linhas — o historico de cada uma fica gravado na propria linha.

USO  python mover_camadas.py [--gravar]
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
COL_HIST = "Histórico de camada"

# (município, UF, ano|None) -> (aba destino, motivo registrado na linha)
MOVER = {
    ("Eusébio", "CE", None): ("3 Grupo social",
        "portão de pessoa + procedimento — Art. 1º, § único condiciona a gratuidade a "
        "cadastro prévio comprovando residência ou vínculo laboral. Desempate: o mais "
        "restritivo prevalece, procedimento vira atributo."),
    ("Itapeva", "SP", None): ("2 Procedimento",
        "portão de procedimento — Decreto 13.734/2024, vigente: tarifa R$ 0,00 apenas no "
        "cartão múltiplo cadastrado; sem cadastro, cobra-se R$ 9,50 na catraca."),
    ("Cacoal", "RO", None): ("4c Temporal-prazo",
        "portão de tempo por prazo declarado — Lei 5.149/2023 lida diretamente, Art. 5º "
        "limita a vigência a até 12 meses, renovável por igual período."),
    ("Palmas", "TO", None): ("4c Temporal-prazo",
        "portão de tempo por prazo declarado — decretos com vigência de um mês, "
        "prorrogados por poucos dias (2.320 e 2.321/2023; 2.631 e 2.654/2025). "
        "⚠️ Pendência do autor: contar como 1 ou 2 episódios."),
}
NAO_MOVIDOS = [
    ("Mariana", "MG", "evidência só jornalística — texto da Lei 3.828/2025 não acessado; "
     "'renovado até 2028' pode ser prazo de contrato, não sunset na lei"),
    ("Assis", "SP", "evidência só jornalística — decreto não localizado; e o caso segue "
     "ATIVO desde 2021 com a pandemia encerrada, o que contradiz a cláusula descrita"),
    ("Vargem Grande Paulista", "SP", "fonte secundária (blog) — dispositivo da Lei "
     "1.092/2019 não confirmado no texto literal"),
    ("Aquiraz", "CE", "evidência é da lei, mas a própria ficha registra que não fecha "
     "isto como reclassificação de camada"),
]


def val(r, ci, nome):
    i = ci.get(nome)
    return r[i].value if i is not None and i < len(r) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()
    import openpyxl
    if not os.path.exists(TIP):
        sys.exit(f"🔴 não achei {TIP}")
    wb = openpyxl.load_workbook(TIP)
    orig = wb["1 Universal"]
    hdr = [str(c.value).strip() if c.value else "" for c in orig[1]]
    ci = {h: i for i, h in enumerate(hdr)}

    achados = []
    for r in list(orig.iter_rows(min_row=2)):
        m = val(r, ci, "Município")
        u = val(r, ci, "UF")
        if not m:
            continue
        chave = (str(m).strip(), str(u or "").strip(), None)
        if chave in MOVER:
            achados.append((r, chave))
    print(f"aba `1 Universal`: {orig.max_row - 1} linhas · {len(achados)} a mover\n")

    plano = []
    for r, chave in achados:
        destino, motivo = MOVER[chave]
        dados = {h: val(r, ci, h) for h in hdr if h}
        plano.append((r[0].row, chave, destino, motivo, dados))
        print(f"  {chave[0]}/{chave[1]}  ·  ano {dados.get('Ano')}  →  {destino}")

    print(f"\nNÃO movidos, e o motivo ({len(NAO_MOVIDOS)}):")
    for m, u, por in NAO_MOVIDOS:
        print(f"  {m}/{u}: {por}")

    if not a.gravar:
        print("\nnada foi escrito. Para aplicar: --gravar")
        return

    bk = TIP.replace(".xlsx", f"-BACKUP-{datetime.datetime.now():%Y%m%d-%H%M}-pre-mover.xlsx")
    shutil.copy2(TIP, bk)

    for _, chave, destino, motivo, dados in plano:
        if destino not in wb.sheetnames:
            ws = wb.create_sheet(destino)
            ws.append(["Município", "UF", "Situação", "Ano", "Legislação",
                       "Link Legislação", "Operador", "Fontes", "Portão",
                       "Portão — evidência", COL_HIST])
            print(f"🆕 aba criada: {destino}")
        ws = wb[destino]
        dh = [str(c.value).strip() if c.value else "" for c in ws[1]]
        if COL_HIST not in dh:
            ws.cell(row=1, column=len(dh) + 1, value=COL_HIST)
            dh.append(COL_HIST)
        linha = []
        for h in dh:
            if h == COL_HIST:
                linha.append(f"{HOJE}: movido de `1 Universal` — {motivo}")
            else:
                linha.append(dados.get(h, ""))
        ws.append(linha)

    for rownum in sorted({p[0] for p in plano}, reverse=True):
        orig.delete_rows(rownum)

    # nota datada no RESUMO, que já era declarado não recalculado
    rs = wb["RESUMO"]
    rs.append([f"⚠️ Nota de {HOJE}",
               "reclassificações por portão (decisão do autor)", "", "",
               f"{len(plano)} linhas saíram de `1 Universal`: "
               + " · ".join(f"{c[0]}/{c[1]} → {d}" for _, c, d, _, _ in plano)
               + f". Aba `4c Temporal-prazo` criada para prazo de vigência declarado, que "
                 f"não é 'dias' nem 'eventos'. NÃO movidos, por evidência só secundária: "
               + ", ".join(f"{m}/{u}" for m, u, _ in NAO_MOVIDOS)
               + ". Os números desta aba seguem NÃO recalculados."])
    wb.save(TIP)
    print(f"\n✅ {len(plano)} linhas movidas · backup: {os.path.basename(bk)}")
    for s in wb.sheetnames:
        if s != "RESUMO":
            print(f"   {wb[s].max_row - 1:>4}  {s}")


if __name__ == "__main__":
    main()
