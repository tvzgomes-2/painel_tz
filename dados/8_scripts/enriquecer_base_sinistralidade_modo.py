#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""enriquecer_base_sinistralidade_modo.py — completa a decomposição por modo de
óbitos e feridos no trânsito (SIMU/Min. Cidades, 2019) na Base Municipal v3.

======================================================================
A LACUNA, E POR QUE ELA ERA MAIOR DO QUE PARECIA
======================================================================
A base tinha apenas **4 categorias de óbito** (pedestre, ciclista, motociclista,
ocupante de ônibus) e **3 de ferido** (pedestre, ciclista, ocupante de ônibus) —
faltando, entre os feridos, justamente **motociclista**, que é a maior categoria
do país. Daí o sintoma registrado na ficha de São Caetano do Sul: só 23 dos 69
feridos tinham modo.

🔴 **A fonte sempre teve as nove categorias.** `SIMU/feridos/simu-feridos-mun-T.csv`
e `SIMU/mortes/simu-mortes-mun-T.csv` trazem, para 5.570 municípios e 2010-2019:
Pedestre · Ciclista · Motociclista · Ocup. triciclo motor · Ocup. automóvel ·
Ocup. caminhonete · Ocup. veículo de transporte pesado · Ocup. ônibus · Outros.
O ETL anterior ingeriu um subconjunto; não havia dado a buscar fora do cofre.

======================================================================
O RESÍDUO É CONFERIDO, NÃO ASSUMIDO
======================================================================
O script soma as nove categorias e compara com o `total_feridos` / `total_mortes`
da própria fonte. Onde a soma não fecha, grava a diferença em
`*_residuo_2019` em vez de calar — se a fonte tem inconsistência interna, ela
aparece na base em vez de virar lacuna silenciosa.

⚠️ **NA ≠ 0 vale aqui de forma particularmente perigosa.** Zero óbitos de
ciclista é uma medida; município sem linha na fonte é ausência de medida. A
fonte SIMU registra 0 explicitamente, então **um município presente na fonte com
0 recebe 0**, e um município ausente da fonte fica **vazio**. As duas coisas não
podem virar a mesma célula.

USO  python enriquecer_base_sinistralidade_modo.py [--ano 2019] [--gravar]
"""
import argparse
import csv
import datetime
import os
import shutil
import sys

RAIZ = os.environ.get("TZ_VAULT") or os.getcwd()
DIR = os.path.join(RAIZ, "03 - Dados", "_data", "Base Municipal v3")
BASE = os.path.join(DIR, "base_municipal_v3.csv")
SIMU = os.path.join(RAIZ, "03 - Dados", "_data", "SIMU")
FONTES = {
    "obitos": (os.path.join(SIMU, "mortes", "simu-mortes-mun-T.csv"), "total_mortes"),
    "feridos": (os.path.join(SIMU, "feridos", "simu-feridos-mun-T.csv"), "total_feridos"),
}
# coluna na fonte -> sufixo na base (os 4 já existentes mantêm o nome de lá)
MODOS = [("Pedestre", "pedestre"), ("Ciclista", "ciclista"),
         ("Motociclista", "motociclista"), ("Ocup triciclo motor", "triciclo"),
         ("Ocup automovel", "automovel"), ("Ocup caminhonete", "caminhonete"),
         ("Ocup veic transp pesado", "veic_pesado"), ("Ocup onibus", "ocup_onibus"),
         ("Outros", "outros")]


def num(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def ler(caminho, col_total, ano):
    out = {}
    with open(caminho, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if str(r.get("ano", "")).strip() != ano:
                continue
            cod = str(r.get("Código IBGE", "")).strip()[:7]
            if not cod:
                continue
            d = {}
            for orig, suf in MODOS:
                d[suf] = num(r.get(orig))
            d["_total"] = num(r.get(col_total))
            out[cod] = d
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ano", default="2019")
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()
    for p in [BASE] + [v[0] for v in FONTES.values()]:
        if not os.path.exists(p):
            sys.exit(f"🔴 não achei {p}")

    dados = {k: ler(v[0], v[1], a.ano) for k, v in FONTES.items()}
    for k, v in dados.items():
        print(f"SIMU {k} {a.ano}: {len(v)} municípios")

    with open(BASE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        campos = list(rows[0].keys())
    cod_col = [c for c in campos if "ibge" in c.lower()][0]

    novas = []
    for fam in ("obitos", "feridos"):
        novas += [f"{fam}_{suf}_{a.ano}" for _, suf in MODOS]
        novas.append(f"{fam}_residuo_{a.ano}")

    preench = {c: 0 for c in novas}
    resid = {"obitos": 0, "feridos": 0}
    ausente = {"obitos": 0, "feridos": 0}
    for row in rows:
        cod = str(row[cod_col])[:7]
        for fam in ("obitos", "feridos"):
            d = dados[fam].get(cod)
            if d is None:
                ausente[fam] += 1
                for _, suf in MODOS:
                    row[f"{fam}_{suf}_{a.ano}"] = ""
                row[f"{fam}_residuo_{a.ano}"] = ""
                continue
            soma = 0.0
            for _, suf in MODOS:
                v = d[suf]
                row[f"{fam}_{suf}_{a.ano}"] = "" if v is None else f"{v:g}"
                soma += v or 0.0
            t = d["_total"]
            r = None if t is None else t - soma
            row[f"{fam}_residuo_{a.ano}"] = "" if r is None else f"{r:g}"
            if r:
                resid[fam] += 1
            for _, suf in MODOS:
                if row[f"{fam}_{suf}_{a.ano}"] != "":
                    preench[f"{fam}_{suf}_{a.ano}"] += 1
            if row[f"{fam}_residuo_{a.ano}"] != "":
                preench[f"{fam}_residuo_{a.ano}"] += 1

    print(f"\n{len(rows)} municípios · {len(novas)} colunas")
    for c in novas:
        marca = "  🆕" if c not in campos else ""
        print(f"   {preench[c]:>5}/{len(rows)}  {c}{marca}")
    print()
    for fam in ("obitos", "feridos"):
        print(f"{fam}: {ausente[fam]} municípios ausentes da fonte (ficam VAZIOS, "
              f"não zero) · {resid[fam]} com resíduo != 0 na soma dos 9 modos")

    # conferência contra as colunas antigas, onde elas existem
    print("\nconferência contra o ETL anterior (devem bater):")
    for fam, suf in (("obitos", "pedestre"), ("obitos", "ocup_onibus"),
                     ("feridos", "pedestre"), ("feridos", "ocup_onibus")):
        velho = f"{fam}_{suf}_{a.ano}"
        if velho not in campos:
            continue
        dif = sum(1 for r in rows
                  if (r.get(velho) or "") != "" and dados[fam].get(str(r[cod_col])[:7])
                  and num(r[velho]) != dados[fam][str(r[cod_col])[:7]][suf])
        print(f"   {velho}: {dif} divergências")

    if not a.gravar:
        print("\nnada foi escrito. Para aplicar: --gravar")
        return
    bk = BASE.replace(".csv", "-BACKUP-" + datetime.datetime.now().strftime("%Y%m%d-%H%M")
                      + "-pre-sinistralidade-modo.csv")
    shutil.copy2(BASE, bk)
    campos_out = campos + [c for c in novas if c not in campos]
    with open(BASE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos_out)
        w.writeheader()
        w.writerows(rows)
    print(f"\n✅ gravado · backup {os.path.basename(bk)}")


if __name__ == "__main__":
    main()
