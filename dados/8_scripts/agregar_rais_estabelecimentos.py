#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""agregar_rais_estabelecimentos.py — ETL municipal da RAIS ESTABELECIMENTOS.

Lê `RAIS_ESTAB_PUB.COMT` (1,46 GB, já no cofre em `03 - Dados/_data/RAIS/dados
brutos/RAIS_ESTAB_PUB.7z`) e produz um agregado por município com: número de
estabelecimentos, vínculos formais, composição por seção CNAE, e o recorte do
**Núcleo Transporte** da tese.

======================================================================
O QUE FALTAVA ERA O ETL, NÃO O DADO
======================================================================
Os microdados já estavam baixados desde mai/2025. O cache em
`_meta/scripts/rais_cache/` é resto de uma tentativa anterior via FTP que
**falhou**: os 54 arquivos de UF estão com **0 byte**. Não há o que aproveitar
ali — a fonte boa é o arquivo único de estabelecimentos.

======================================================================
🔴 RAIS NEGATIVA: A DISTINÇÃO QUE DECIDE O NÚMERO
======================================================================
A RAIS obriga a declarar **mesmo sem empregado** — é a "RAIS negativa". Contar
tudo como "estabelecimento" infla o número com CNPJs sem nenhum vínculo; contar
só quem tem vínculo esconde a empresa que existe e não emprega. O script grava
**os dois**, separados (`n_estab_total`, `n_estab_negativa`, `n_estab_com_vinculo`),
e nunca um só. Vale especialmente para o Núcleo Transporte, onde a empresa de
ônibus sem vínculo ativo é justamente o caso que interessa investigar.

======================================================================
NÚCLEO TRANSPORTE — MESMO RECORTE DA PESQUISA DOS CNPJs
======================================================================
Núcleo canônico: subclasses **4921-3/01** (coletivo municipal, itinerário fixo) e
**4921-3/02** (intermunicipal metropolitano) — a mesma definição de
[[Núcleo Transporte]] e da base de Grupos Econômicos. A expansão experimental
(4922-1, 4929-9) sai em coluna à parte, **nunca somada ao núcleo**, para não
misturar o recorte canônico com o que ainda está em avaliação.

✅ **Isto dá à tese uma fonte independente da Receita Federal para o mesmo
universo.** O pipeline CNPJ conta empresa registrada; a RAIS conta empresa que
declara emprego formal. Onde os dois divergem, a divergência é achado — não erro
a reconciliar.

⚠️ **Ano do arquivo NÃO declarado no layout.** O arquivo não traz coluna de ano.
O script imprime o total nacional de vínculos ativos para que o ano seja
identificado por cotejo com os totais publicados da RAIS, e grava o resultado com
sufixo `_rais` sem ano até essa confirmação. **Não inventar o ano.**

USO  python agregar_rais_estabelecimentos.py --entrada <arquivo.COMT> [--gravar-base]
"""
import argparse
import csv
import datetime
import os
import shutil
import sys

V = os.environ.get("TZ_VAULT") or r"C:\Users\HOME\OneDrive\doutorado"
DATA = os.path.join(V, "03 - Dados", "_data")
SAIDA = os.path.join(DATA, "RAIS", "rais_estabelecimentos_por_municipio.csv")
BASE = os.path.join(DATA, "Base Municipal v3", "base_municipal_v3.csv")

NUCLEO = {"4921301", "4921302"}
EXPANSAO = {"4922101", "4922102", "4922103", "4929901", "4929902",
            "4929903", "4929904", "4929999"}

# divisão CNAE 2.0 -> seção (IBGE). Faixas oficiais.
SECOES = [(1, 3, "A"), (5, 9, "B"), (10, 33, "C"), (35, 35, "D"), (36, 39, "E"),
          (41, 43, "F"), (45, 47, "G"), (49, 53, "H"), (55, 56, "I"), (58, 63, "J"),
          (64, 66, "K"), (68, 68, "L"), (69, 75, "M"), (77, 82, "N"), (84, 84, "O"),
          (85, 85, "P"), (86, 88, "Q"), (90, 93, "R"), (94, 96, "S"), (97, 97, "T"),
          (99, 99, "U")]


def secao(sub):
    try:
        d = int(str(sub)[:2])
    except ValueError:
        return None
    for a, b, s in SECOES:
        if a <= d <= b:
            return s
    return None


def i(v):
    try:
        return int(float(str(v).strip().strip('"').replace(",", ".")))
    except (TypeError, ValueError):
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", required=True)
    ap.add_argument("--gravar-base", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(a.entrada):
        sys.exit(f"🔴 não achei {a.entrada}")

    # ⚡ csv.reader + índices, não DictReader: são ~5 milhões de linhas, e montar
    # um dicionário por linha custa mais que todo o resto do laço somado. O shell
    # da ponte tem janela curta; o ETL precisa caber nela de uma vez.
    campos_sec = [s for _, _, s in SECOES]
    CHAVES = (["n_estab_total", "n_estab_negativa", "n_estab_com_vinculo",
               "vinculos_ativos", "nucleo_estab", "nucleo_vinculos",
               "expansao_estab", "expansao_vinculos"]
              + [f"sec_{s}_estab" for s in campos_sec]
              + [f"sec_{s}_vinc" for s in campos_sec])
    POS = {k: n for n, k in enumerate(CHAVES)}
    SEC_E = {s: POS[f"sec_{s}_estab"] for s in campos_sec}
    SEC_V = {s: POS[f"sec_{s}_vinc"] for s in campos_sec}
    P_TOT, P_NEG, P_COM, P_VIN = (POS["n_estab_total"], POS["n_estab_negativa"],
                                  POS["n_estab_com_vinculo"], POS["vinculos_ativos"])
    P_NE, P_NV = POS["nucleo_estab"], POS["nucleo_vinculos"]
    P_XE, P_XV = POS["expansao_estab"], POS["expansao_vinculos"]
    # divisão (2 primeiros dígitos) -> posições da seção, resolvido uma vez só
    DIV = {}
    for d0 in range(1, 100):
        for lo, hi, s in SECOES:
            if lo <= d0 <= hi:
                DIV[f"{d0:02d}"] = (SEC_E[s], SEC_V[s])
                break

    mun = {}
    nac = [0, 0, 0]          # estabelecimentos · RAIS negativa · vínculos
    with open(a.entrada, encoding="latin-1", newline="", buffering=1 << 22) as f:
        rd = csv.reader(f, delimiter=",")
        cab = [c.strip().strip('"') for c in next(rd)]
        need = ["Município - Código", "CNAE 2.0 Subclasse - Codigo",
                "Qtd Vínculos Ativos", "Ind RAIS Negativa - Código"]
        falta = [c for c in need if c not in cab]
        if falta:
            sys.exit(f"🔴 faltam colunas: {falta}\ndisponíveis: {cab}")
        iM, iC, iV, iN = (cab.index(need[0]), cab.index(need[1]),
                          cab.index(need[2]), cab.index(need[3]))
        for r in rd:
            try:
                cod6 = r[iM].strip()
            except IndexError:
                continue
            if cod6 in ("999999", "999997") or not cod6.isdigit():
                continue
            v = i(r[iV])
            d = mun.get(cod6)
            if d is None:
                d = mun[cod6] = [0] * len(CHAVES)
            d[P_TOT] += 1
            nac[0] += 1
            if i(r[iN]) == 1:
                d[P_NEG] += 1
                nac[1] += 1
            if v > 0:
                d[P_COM] += 1
            d[P_VIN] += v
            nac[2] += v
            sub = r[iC].strip()
            p = DIV.get(sub[:2])
            if p:
                d[p[0]] += 1
                d[p[1]] += v
            if sub in NUCLEO:
                d[P_NE] += 1
                d[P_NV] += v
            elif sub in EXPANSAO:
                d[P_XE] += 1
                d[P_XV] += v
    mun = {k: dict(zip(CHAVES, v)) for k, v in mun.items()}
    nac = {"estab": nac[0], "neg": nac[1], "vinc": nac[2]}

    print(f"nacional: {nac['estab']:,} estabelecimentos · {nac['neg']:,} RAIS "
          f"negativa · {nac['vinc']:,} vínculos ativos")
    print("⚠️ conferir o ANO do arquivo cotejando este total nacional de vínculos "
          "com os totais publicados da RAIS — o layout não traz coluna de ano.")
    print(f"municípios com registro: {len(mun)}")
    tn = sum(d["nucleo_estab"] for d in mun.values())
    tv = sum(d["nucleo_vinculos"] for d in mun.values())
    print(f"Núcleo Transporte (4921-3/01 e /02): {tn:,} estabelecimentos · "
          f"{tv:,} vínculos · em {sum(1 for d in mun.values() if d['nucleo_estab']):,} "
          "municípios")
    print(f"Expansão (4922/4929, NÃO somada ao núcleo): "
          f"{sum(d['expansao_estab'] for d in mun.values()):,} estabelecimentos")

    cols = ["cod_ibge6"] + list(next(iter(mun.values())).keys())
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for k in sorted(mun):
            w.writerow({"cod_ibge6": k, **mun[k]})
    print(f"\n✅ {SAIDA}")

    if not a.gravar_base:
        print("base não alterada. Para integrar: --gravar-base")
        return
    with open(BASE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        campos = list(rows[0].keys())
    cod_col = [c for c in campos if "ibge" in c.lower()][0]
    novas = ["rais_n_estab_total", "rais_n_estab_negativa", "rais_n_estab_com_vinculo",
             "rais_vinculos_ativos", "rais_nucleo_estab", "rais_nucleo_vinculos",
             "rais_expansao_estab", "rais_expansao_vinculos"]
    de_para = dict(zip(novas, ["n_estab_total", "n_estab_negativa",
                               "n_estab_com_vinculo", "vinculos_ativos",
                               "nucleo_estab", "nucleo_vinculos",
                               "expansao_estab", "expansao_vinculos"]))
    ok = 0
    for row in rows:
        d = mun.get(str(row[cod_col])[:6])
        for c in novas:
            row[c] = "" if d is None else str(d[de_para[c]])
        if d is not None:
            ok += 1
    print(f"base: {ok}/{len(rows)} municípios pareados (⚠️ os demais ficam VAZIOS, "
          "não zero — ausência da RAIS não é ausência de estabelecimento)")
    bk = BASE.replace(".csv", "-BACKUP-"
                      + datetime.datetime.now().strftime("%Y%m%d-%H%M") + "-pre-rais.csv")
    shutil.copy2(BASE, bk)
    with open(BASE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos + [c for c in novas if c not in campos])
        w.writeheader()
        w.writerows(rows)
    print(f"✅ gravado · backup {os.path.basename(bk)}")


if __name__ == "__main__":
    main()
