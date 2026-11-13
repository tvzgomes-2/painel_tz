#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""enriquecer_base_fpm.py — acrescenta o FPM (Fundo de Participação dos
Municípios) à Base Municipal v3, 2019–2025.

======================================================================
O DADO JÁ ESTAVA NO COFRE — FALTAVA O ETL
======================================================================
`Base Municipal v3/contas_alvo_siconfi_v2_2019_2025.csv` já traz 106.526 linhas
de FPM extraídas do Siconfi, e a coluna `papel` já carrega a regra de agregação
que a mudança de plano de contas exige:

  * **2022–2025** — conta `1.7.1.1.51.0.0`, papel `total`: uma linha por ano, já
    somada na origem.
  * **2019–2021** — conta `1.7.1.8.01.x`, papéis `cota_mensal`, `dezembro_1pct` e
    `julho_1pct`: **três** linhas que precisam ser somadas.

✅ Conferido antes de somar: os dois planos **nunca co-ocorrem** no mesmo
município-ano (22.032 município-ano só no plano antigo, 16.623 só no novo, **0**
com ambos). Não há risco de dupla contagem.

======================================================================
BRUTO ≠ LÍQUIDO, E A DIFERENÇA NÃO É DETALHE
======================================================================
A coluna `coluna` do arquivo separa `Receitas Brutas Realizadas` das deduções
(FUNDEB, transferências constitucionais, outras). **O que chega ao caixa do
município é o líquido** — e a dedução do FUNDEB sozinha é da ordem de 20% do FPM
bruto. Guardar só o bruto superestimaria a capacidade de gasto livre; guardar só
o líquido esconderia o tamanho do repasse. **O script grava os dois**, e a
dedução como terceira coluna, para que a inferência fique declarada.

======================================================================
POR QUE O FPM IMPORTA PARA ESTA TESE
======================================================================
Não como valor absoluto: como **medida de dependência fiscal**. Um município cujo
orçamento é majoritariamente FPM tem pouca receita própria para bancar um
subsídio permanente de Tarifa Zero, e a política fica exposta à oscilação de um
repasse que ele não controla. Por isso o script deriva:

  * `fpm_liquido_pc_<ano>` — FPM líquido per capita (pop. 2022)
  * `fpm_share_receita_corrente_2022` — FPM líquido / receita corrente FINBRA 2022

⚠️ **A derivada per capita usa a população de 2022 em todos os anos** — é
denominador fixo, não série. Serve para comparar municípios entre si, **não** para
ler a trajetória de um município no tempo. Está dito no nome e aqui.

⚠️ **NA ≠ 0:** município-ano sem linha no Siconfi fica **vazio**, nunca zero. O
Siconfi depende de o município ter declarado, e não declarar não é não receber.

IDEMPOTENTE (reescreve as próprias colunas). Simula por padrão. Backup antes.

USO  python enriquecer_base_fpm.py [--gravar]
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
CONTAS = os.path.join(DIR, "contas_alvo_siconfi_v2_2019_2025.csv")
ANOS = [str(a) for a in range(2019, 2026)]


def num(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def coletar():
    """bruto · fundeb · outras deduções, por (município, ano) — somando os
    componentes de 2019-2021 e tomando o total único de 2022-2025, sem misturar
    os dois planos.

    🔴 **Só o FUNDEB é subtraído, e a decisão é medida, não de gosto.** A razão
    FUNDEB/bruto tem mediana **0,183** com p5-p95 de 0,178-0,185 em 36.975
    município-ano: é a regra constitucional dos 20% aparecendo no dado, e por
    isso é dedução confiável. Já `Deduções - Transferências Constitucionais`
    aparece em poucos casos e chega a **superar o próprio FPM bruto** (Feira de
    Santana/BA, 2022: dedução de R$ 16,1 mi contra bruto de R$ 12,0 mi) — o FPM
    **é** uma transferência constitucional, não tem dedução desse tipo. Subtraí-la
    produzia 8 municípios com FPM líquido negativo. Ela vai para coluna própria,
    **não subtraída e sinalizada**, em vez de contaminar o líquido."""
    bruto, fundeb, outras, vistos = {}, {}, {}, set()
    with open(CONTAS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            conta = r.get("conta", "")
            if "Participa" not in conta or "Munic" not in conta:
                continue
            cod, ano = str(r["cod_ibge"])[:7], str(r["ano"])
            v = num(r.get("valor"))
            if v is None:
                continue
            vistos.add((cod, ano))
            col = r.get("coluna", "")
            if "FUNDEB" in col:
                alvo = fundeb
            elif col.startswith(("Deduções", "Outras Dedu")):
                alvo = outras
            else:
                alvo = bruto
            alvo[(cod, ano)] = alvo.get((cod, ano), 0.0) + v
    return bruto, fundeb, outras, vistos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()
    for p in (BASE, CONTAS):
        if not os.path.exists(p):
            sys.exit(f"🔴 não achei {p}")
    bruto, fundeb, outras, vistos = coletar()
    print(f"Siconfi: {len(vistos)} pares município-ano com FPM declarado")
    for ano in ANOS:
        print(f"   {ano}: {sum(1 for c, y in vistos if y == ano):>5} municípios")

    with open(BASE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        campos = list(rows[0].keys())
    cod_col = [c for c in campos if "ibge" in c.lower()][0]

    novas = []
    for ano in ANOS:
        novas += [f"fpm_bruto_{ano}", f"fpm_deducao_fundeb_{ano}",
                  f"fpm_outras_deducoes_{ano}", f"fpm_liquido_{ano}",
                  f"fpm_liquido_pc_{ano}"]
    novas.append("fpm_share_receita_corrente_2022")

    preench = {c: 0 for c in novas}
    anom, inconsistentes = [], []
    for row in rows:
        cod = str(row[cod_col])[:7]
        pop = num(row.get("pop_2022"))
        for ano in ANOS:
            b = bruto.get((cod, ano))
            fu = fundeb.get((cod, ano)) if (cod, ano) in vistos else None
            ou = outras.get((cod, ano))
            # 🔴 Declaração inconsistente no Siconfi: a dedução do FUNDEB é ~18%
            # do FPM bruto pela regra constitucional. Onde ela SUPERA o bruto, o
            # valor declarado como bruto está errado ou incompleto — e o líquido
            # sairia negativo. Não se conserta o que não se sabe: o líquido fica
            # VAZIO (NA != 0) e o caso é marcado, em vez de publicar um negativo
            # impossível ou um zero inventado.
            incons = b is not None and fu is not None and fu > b
            if incons:
                inconsistentes.append((row.get("municipio", cod), row.get("uf", ""),
                                       ano, b, fu))
            liq = None if (b is None or incons) else (b - (fu or 0.0))
            row[f"fpm_bruto_{ano}"] = "" if b is None else f"{b:.2f}"
            row[f"fpm_deducao_fundeb_{ano}"] = "" if fu is None else f"{fu:.2f}"
            row[f"fpm_outras_deducoes_{ano}"] = "" if ou is None else f"{ou:.2f}"
            row[f"fpm_liquido_{ano}"] = "" if liq is None else f"{liq:.2f}"
            row[f"fpm_liquido_pc_{ano}"] = (f"{liq/pop:.2f}"
                                           if liq is not None and pop else "")
            if b and ou and ou > b:
                anom.append((row.get("municipio", cod), row.get("uf", ""), ano, b, ou))
            for c in (f"fpm_bruto_{ano}", f"fpm_deducao_fundeb_{ano}",
                      f"fpm_outras_deducoes_{ano}", f"fpm_liquido_{ano}",
                      f"fpm_liquido_pc_{ano}"):
                if row[c] != "":
                    preench[c] += 1
        rc = num(row.get("finbra_receita_corrente_2022"))
        l22 = num(row.get("fpm_liquido_2022"))
        row["fpm_share_receita_corrente_2022"] = (f"{l22/rc:.4f}"
                                                  if l22 is not None and rc else "")
        if row["fpm_share_receita_corrente_2022"] != "":
            preench["fpm_share_receita_corrente_2022"] += 1

    print(f"\n{len(rows)} municípios na base · {len(novas)} colunas novas")
    for c in novas:
        print(f"   {preench[c]:>5}/{len(rows)}  {c}")

    # sanidade: FPM líquido 2022 deve ser positivo e menor que a receita corrente
    ruins = [r for r in rows if r["fpm_share_receita_corrente_2022"]
             and not (0 < float(r["fpm_share_receita_corrente_2022"]) < 1.5)]
    print(f"\nsanidade — share fora de (0, 1.5): {len(ruins)} municípios")
    for r in ruins[:5]:
        print(f"   {r.get('municipio', r[cod_col])}: "
              f"{r['fpm_share_receita_corrente_2022']}")
    print(f"⚠️ município-ano com 'outras deduções' MAIOR que o FPM bruto "
          f"(não subtraídas, por isso): {len(anom)}")
    for m, uf, ano, b, ou in anom[:5]:
        print(f"   {m}/{uf} {ano}: bruto {b:,.0f} · outras deduções {ou:,.0f}")
    print(f"🔴 município-ano com FUNDEB > bruto (declaração inconsistente no "
          f"Siconfi — líquido deixado VAZIO): {len(inconsistentes)}")
    for m, uf, ano, b, fu in inconsistentes[:8]:
        print(f"   {m}/{uf} {ano}: bruto {b:,.0f} · FUNDEB {fu:,.0f} "
              f"({fu/b:.2f}x)")

    if not a.gravar:
        print("\nnada foi escrito. Para aplicar: --gravar")
        return
    bk = BASE.replace(".csv", "-BACKUP-"
                      + datetime.datetime.now().strftime("%Y%m%d-%H%M") + "-pre-fpm.csv")
    shutil.copy2(BASE, bk)
    campos_out = campos + [c for c in novas if c not in campos]
    with open(BASE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos_out)
        w.writeheader()
        w.writerows(rows)
    print(f"\n✅ gravado · backup {os.path.basename(bk)}")


if __name__ == "__main__":
    main()
