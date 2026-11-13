#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""calcular_gini_censo2022.py — calcula o índice de Gini do **rendimento
domiciliar per capita** por município, a partir dos microdados da amostra do
Censo 2022, e grava o agregado municipal.

======================================================================
POR QUE CALCULAR, E NÃO BAIXAR
======================================================================
`03 - Dados/_data/osf_vrc59_gomes-filho-2025/gini.xlsx` está **corrompido**: uma
linha, uma coluna, só o cabeçalho `id_municipio`. Não é dado incompleto — é
arquivo truncado, e não há o que recuperar dele.

O cofre já tem a matéria-prima: os microdados de **acesso controlado** do Censo
2022, cuja tabela de Domicílios traz `D0080` (município), `D0111` (peso amostral),
`D0150` (moradores) e `D0360` (**rendimento domiciliar per capita**) — que é
exatamente a base da definição usual do Gini municipal do IBGE. Calcular é mais
defensável que baixar de terceiro: o caminho fica documentado e reproduzível, que
é o requisito de King (Replicação) já adotado pela pesquisa.

⚠️ **Restrição de replicação, herdada do LEIA-ME dos microdados:** os arquivos de
acesso controlado **não** entram no pacote do Zenodo. O que pode ser depositado é
**este script** e o **agregado municipal** que ele produz — nunca o insumo.

======================================================================
AS DECISÕES DE MÉTODO, DECLARADAS
======================================================================
1. **A unidade é a pessoa, não o domicílio.** O Gini do rendimento domiciliar per
   capita descreve a distribuição entre *pessoas*, então cada domicílio entra com
   peso `D0111 × D0150` (peso amostral × moradores). Ponderar por domicílio daria
   outro número, e um número que não é o que a literatura chama de Gini municipal.
2. **Renda zero entra; renda não declarada fica de fora.** Domicílio com
   rendimento per capita 0 é medida — e é justamente a cauda que o Gini precisa
   enxergar. Domicílio sem valor declarado é ausência de medida e é excluído do
   cálculo, com a contagem registrada em `gini_domic_sem_renda` para que a
   exclusão seja auditável. **NA ≠ 0.**
3. **Só domicílios particulares permanentes ocupados** (`D0130`/espécie), que é o
   recorte usual. Domicílio coletivo e improvisado distorceriam a cauda.
4. **O Gini de amostra pequena não é confiável, e o script diz quando.** Grava
   `gini_n_domicilios` (domicílios da amostra, não expandidos) ao lado do índice.
   Município com poucos domicílios amostrados tem Gini instável — quem usar o
   número precisa poder filtrar por isso. Nenhum município é descartado em
   silêncio.

RESUMÍVEL: grava um parcial por UF e pula o que já existe. Rode quantas vezes
precisar; a janela curta do shell não atrapalha.

USO  python calcular_gini_censo2022.py [--uf 35] [--consolidar] [--gravar-base]
"""
import argparse
import csv
import datetime
import os
import shutil
import sys
import zipfile

V = os.environ.get("TZ_VAULT") or r"C:\Users\HOME\OneDrive\doutorado"
DATA = os.path.join(V, "03 - Dados", "_data")
ZIP = os.environ.get("TZ_MICRODADOS") or (
    r"C:\Users\HOME\Downloads\07_Academico\Censo2022_Microdados"
    r"\microdados_censo_amostra_2022_csv_20260908_140041.zip")
OUT = os.path.join(DATA, "Censo2022_Microdados", "agregados")
CONSOL = os.path.join(DATA, "Base Municipal v3", "gini_censo2022_municipal.csv")
BASE = os.path.join(DATA, "Base Municipal v3", "base_municipal_v3.csv")

COLS = ["D0080", "D0111", "D0150", "D0360", "D0130"]
# espécie: 1 = domicílio particular permanente ocupado (layout do Censo 2022)
ESPECIE_OK = {"1", "01", "1.0"}


def gini_ponderado(pares):
    """pares = [(renda, peso)]. Fórmula padrão do Gini ponderado:
       G = sum(w_i x_i (2F_i - 1)) / sum(w_i x_i),
       com F_i a posição relativa acumulada no meio do intervalo do próprio peso.
       Retorna None se a renda total for zero (Gini indefinido)."""
    pares = sorted(pares)
    W = sum(w for _, w in pares)
    S = sum(x * w for x, w in pares)
    if W <= 0 or S <= 0:
        return None
    acum, num = 0.0, 0.0
    for x, w in pares:
        f = (acum + w / 2.0) / W
        num += w * x * (2.0 * f - 1.0)
        acum += w
    return num / S


def parcial(uf):
    return os.path.join(OUT, f"_parcial_gini_{uf}.csv")


def processa_uf(uf, z):
    nome = next((n for n in z.namelist()
                 if n.upper().endswith(f"DOMICILIOS_{uf}_CONTROLADO.CSV")), None)
    if not nome:
        return None, f"🔴 UF {uf}: arquivo de Domicílios não encontrado no zip"
    por_mun, sem_renda, fora_especie = {}, {}, 0
    with z.open(nome) as fh:
        import io
        rd = csv.DictReader(io.TextIOWrapper(fh, encoding="latin-1"), delimiter=";")
        faltam = [c for c in COLS if c not in (rd.fieldnames or [])]
        if faltam:
            return None, f"🔴 UF {uf}: faltam colunas {faltam}"
        for r in rd:
            esp = (r.get("D0130") or "").strip()
            if esp and esp not in ESPECIE_OK:
                fora_especie += 1
                continue
            mun = (r.get("D0080") or "").strip()
            if not mun:
                continue
            mun = mun.zfill(7) if len(mun) >= 6 else mun
            try:
                w = float((r.get("D0111") or "").replace(",", "."))
                mor = float((r.get("D0150") or "").replace(",", "."))
            except ValueError:
                continue
            bruto = (r.get("D0360") or "").strip().replace(",", ".")
            if bruto == "":
                sem_renda[mun] = sem_renda.get(mun, 0) + 1
                continue
            try:
                renda = float(bruto)
            except ValueError:
                sem_renda[mun] = sem_renda.get(mun, 0) + 1
                continue
            if w <= 0 or mor <= 0:
                continue
            por_mun.setdefault(mun, []).append((renda, w * mor))
    linhas = []
    for mun, pares in sorted(por_mun.items()):
        g = gini_ponderado(pares)
        linhas.append({"cod_ibge": mun,
                       "gini_dom_pc_2022": "" if g is None else f"{g:.4f}",
                       "gini_n_domicilios": len(pares),
                       "gini_domic_sem_renda": sem_renda.get(mun, 0)})
    return linhas, (f"UF {uf}: {len(linhas)} municípios · "
                    f"{sum(l['gini_n_domicilios'] for l in linhas):,} domicílios "
                    f"na amostra · {sum(sem_renda.values()):,} sem renda declarada "
                    f"· {fora_especie:,} fora do recorte de espécie")


def consolidar():
    linhas = []
    for f in sorted(os.listdir(OUT)):
        if f.startswith("_parcial_gini_") and f.endswith(".csv"):
            with open(os.path.join(OUT, f), encoding="utf-8") as fh:
                linhas += list(csv.DictReader(fh))
    if not linhas:
        sys.exit("🔴 nenhum parcial para consolidar")
    with open(CONSOL, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)
    vals = sorted(float(l["gini_dom_pc_2022"]) for l in linhas
                  if l["gini_dom_pc_2022"])
    print(f"✅ {CONSOL}\n   {len(linhas)} municípios · {len(vals)} com Gini")
    if vals:
        print(f"   min {vals[0]:.3f} · p25 {vals[len(vals)//4]:.3f} · "
              f"mediana {vals[len(vals)//2]:.3f} · p75 {vals[3*len(vals)//4]:.3f} "
              f"· max {vals[-1]:.3f}")
        peq = [l for l in linhas if int(l["gini_n_domicilios"]) < 50]
        print(f"   ⚠️ {len(peq)} municípios com menos de 50 domicílios na amostra "
              "— Gini instável, filtrar antes de usar")
    return linhas


def gravar_base(linhas):
    idx = {l["cod_ibge"]: l for l in linhas}
    with open(BASE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        campos = list(rows[0].keys())
    cod_col = [c for c in campos if "ibge" in c.lower()][0]
    novas = ["gini_dom_pc_2022", "gini_n_domicilios", "gini_domic_sem_renda"]
    ok = 0
    for row in rows:
        d = idx.get(str(row[cod_col])[:7])
        for c in novas:
            row[c] = (d or {}).get(c, "")
        if row["gini_dom_pc_2022"]:
            ok += 1
    print(f"base: {ok}/{len(rows)} municípios com Gini")
    bk = BASE.replace(".csv", "-BACKUP-"
                      + datetime.datetime.now().strftime("%Y%m%d-%H%M") + "-pre-gini.csv")
    shutil.copy2(BASE, bk)
    with open(BASE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos + [c for c in novas if c not in campos])
        w.writeheader()
        w.writerows(rows)
    print(f"✅ gravado · backup {os.path.basename(bk)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uf", nargs="*", help="UFs a processar (código IBGE, ex. 35)")
    ap.add_argument("--consolidar", action="store_true")
    ap.add_argument("--gravar-base", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.uf is not None or not (a.consolidar or a.gravar_base):
        if not os.path.exists(ZIP):
            sys.exit(f"🔴 não achei o zip dos microdados em {ZIP}")
        z = zipfile.ZipFile(ZIP)
        ufs = a.uf or sorted({n.split("/")[0] for n in z.namelist()
                              if n.split("/")[0].isdigit()})
        for uf in ufs:
            if os.path.exists(parcial(uf)):
                print(f"UF {uf}: parcial já existe, pulando")
                continue
            linhas, msg = processa_uf(uf, z)
            print(msg)
            if linhas:
                with open(parcial(uf), "w", encoding="utf-8", newline="") as fh:
                    w = csv.DictWriter(fh, fieldnames=list(linhas[0].keys()))
                    w.writeheader()
                    w.writerows(linhas)
    if a.consolidar or a.gravar_base:
        linhas = consolidar()
        if a.gravar_base:
            gravar_base(linhas)


if __name__ == "__main__":
    main()
