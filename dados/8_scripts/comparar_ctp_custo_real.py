#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""comparar_ctp_custo_real.py — cruza a arrecadação simulada de CTP/CTPU
(`simular_ctp_ctpu.py`) com o CUSTO REAL do sistema de TP, onde esse custo
é conhecido. Não existe custo total do sistema por município para os 5.570
— é um dado que nem a NTU/Ipea conseguem (por isso os próprios estudos
fichados se restringem a 12 capitais ou 25/12 cidades TZ). Aqui usamos os
únicos benchmarks de custo já no cofre:

  - `casos por fonte/NTU 2023.csv` (25 cidades TZ, custo total anual,
    vintage do relatório NTU "Tarifa Zero" 2024)
  - `casos por fonte/NTU 2025 - TZ maiores cidades.csv` (12 cidades TZ,
    vintage mais recente, maio/2025) — usado como PRIORITÁRIO quando a
    cidade aparece nos dois (9 de 12 se sobrepõem, com custo diferente —
    evolução real entre as datas, não erro)

`simu_servicos_grandes_cidades.csv` (61 municípios, custo_operacao) foi
CONSIDERADO e DESCARTADO aqui: os valores estão em ordem de grandeza
incompatível com custo total (ex. Campinas 0,290 — não dá pra saber se é
R$ bilhão, custo per capita ou outra unidade sem retornar à fonte SIMU
original) e a maioria dos municípios está com NaN. Não usar sem investigar
a unidade primeiro (ver Auditoria de dados, item 3 — já registrado como
"inviável como variável de panorama nacional").

⚠️ AVISO DE ESCOPO: a comparação abaixo só vale para os ~25-37 municípios
que JÁ TÊM tarifa zero e JÁ TÊM custo divulgado — não é uma amostra
aleatória dos 5.570 (são, por definição, os casos "de sucesso" da TZ,
tipicamente pequenos/médios). NÃO GENERALIZAR o resultado ("CTP cobriria
X% do custo") para os municípios que NÃO têm TZ — a pergunta que a tese
faz (será que a CTP viabilizaria TZ em municípios de maior porte,
onde não há hoje) não é respondida por este exercício; só mostra se a
CTP RECUPERARIA o custo onde a TZ JÁ EXISTE.

SAÍDA: `serie_ctp_vs_custo_real.csv` (município, custo real anual,
arrecadação simulada anual em cada alíquota, alíquota necessária p/ 100% de
cobertura, razão de cobertura a 2%).

USO: python comparar_ctp_custo_real.py"""
import os
import re
import unicodedata

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..")), "03 - Dados", "_data")
OUT = os.path.join(V, "Base Municipal v3")
BASE_CSV = os.path.join(OUT, "base_municipal_v3.csv")
PAINEL_CTP_CSV = os.path.join(OUT, "serie_ctp_ctpu_simulacao.csv")
CASOS_DIR = os.path.join(V, "casos por fonte")
NTU_2023_CSV = os.path.join(CASOS_DIR, "NTU 2023.csv")
NTU_2025_CSV = os.path.join(CASOS_DIR, "NTU 2025 - TZ maiores cidades.csv")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def c7(x):
    try:
        return str(int(float(x))).zfill(7)
    except Exception:
        return None


def log(msg):
    print(msg, flush=True)


def salvar_atomico(df, path):
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def parse_custo_br(v):
    """'87,6' (vírgula decimal, formato brasileiro) ou já-float -> float."""
    if pd.isna(v):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    v = str(v).strip().replace(".", "").replace(",", ".")
    try:
        return float(v)
    except Exception:
        return None


def bridge_cidade_uf(series_cidade_uf, base_nomes):
    """'Caucaia-CE' -> cod_ibge, via UF+nome normalizado (mesmo padrão do
    resto do pipeline)."""
    cidade, uf = zip(*series_cidade_uf.str.rsplit("-", n=1))
    chave = pd.Series(uf).str.upper().str.strip() + "|" + pd.Series(cidade).map(norm)
    bridge = base_nomes.assign(chave=base_nomes.uf.str.upper().str.strip() + "|" + base_nomes.nome_mun.map(norm))
    m = pd.DataFrame({"chave": chave}).merge(bridge[["chave", "cod_ibge"]], on="chave", how="left")
    return m["cod_ibge"].values


def main():
    base = pd.read_csv(BASE_CSV, dtype={"cod_ibge": str}, low_memory=False)
    base["cod_ibge"] = base["cod_ibge"].map(c7)
    base_nomes = base[["cod_ibge", "nome_mun", "uf"]].copy()

    n23 = pd.read_csv(NTU_2023_CSV, sep=";", encoding="utf-8-sig")
    n23["custo_milhao"] = n23["Custo total do TP anual em R$ milhão"].map(parse_custo_br)
    n23["cod_ibge"] = bridge_cidade_uf(n23["Cidade"], base_nomes)
    n23 = n23.dropna(subset=["cod_ibge", "custo_milhao"])[["cod_ibge", "custo_milhao"]]
    n23["fonte_custo"] = "NTU 2023 (relatório TZ 2024)"

    n25 = pd.read_csv(NTU_2025_CSV, sep=";", encoding="utf-8-sig")
    n25["custo_milhao"] = pd.to_numeric(n25["Custo_total_TP_anual_R_milhao"], errors="coerce")
    n25["cod_ibge"] = bridge_cidade_uf(n25["Cidade"], base_nomes)
    n25 = n25.dropna(subset=["cod_ibge", "custo_milhao"])[["cod_ibge", "custo_milhao"]]
    n25["fonte_custo"] = "NTU 2025 (relatório TZ 2025, maio/2025)"

    log(f"NTU 2023: {len(n23)} municípios com custo | NTU 2025: {len(n25)} municípios com custo")

    # prioriza 2025 (mais recente) quando o município aparece nos dois
    custo = pd.concat([n25, n23]).drop_duplicates(subset="cod_ibge", keep="first")
    log(f"Custo real conhecido (união, 2025 prioritário): {len(custo)} municípios distintos")

    painel = pd.read_csv(PAINEL_CTP_CSV, dtype={"cod_ibge": str}, low_memory=False)
    painel["cod_ibge"] = painel["cod_ibge"].map(c7)

    d = custo.merge(painel, on="cod_ibge", how="left")
    d = d.merge(base_nomes, on="cod_ibge", how="left")
    d["custo_anual_r"] = d["custo_milhao"] * 1_000_000

    cols_arrec = [c for c in painel.columns if c.startswith("arrecadacao_ctp_") or c.startswith("arrecadacao_ctpu_")]
    faltando = d[cols_arrec[0]].isna().sum() if cols_arrec else len(d)
    if faltando:
        log(f"⚠️ {faltando} municípios com custo conhecido mas sem simulação CTP/CTPU "
            f"(provavelmente sem RAIS ou sem salário médio SIDRA) — excluídos da comparação.")
    d = d.dropna(subset=[cols_arrec[0]]) if cols_arrec else d

    for c in cols_arrec:
        d[c.replace("arrecadacao_", "cobertura_") + "_anual"] = (d[c] * 12) / d["custo_anual_r"]

    # alíquota necessária pra cobrir 100% do custo, nos dois cenários (linear: arrecadação ∝ alíquota)
    d["aliquota_necessaria_ctp_100pct"] = d["custo_anual_r"] / (12 * d["base_tributavel_ctp"] * d["salario_medio_mensal_r"])
    d["aliquota_necessaria_ctpu_100pct"] = d["custo_anual_r"] / (12 * d["base_tributavel_ctpu"] * d["salario_medio_mensal_r"])

    cols_saida = (["cod_ibge", "nome_mun", "uf", "custo_anual_r", "fonte_custo",
                    "base_tributavel_ctp", "base_tributavel_ctpu", "salario_medio_mensal_r",
                    "aliquota_necessaria_ctp_100pct", "aliquota_necessaria_ctpu_100pct"]
                   + [c.replace("arrecadacao_", "cobertura_") + "_anual" for c in cols_arrec])
    d_out = d[cols_saida].sort_values("aliquota_necessaria_ctpu_100pct")
    salvar_atomico(d_out, os.path.join(OUT, "serie_ctp_vs_custo_real.csv"))

    log(f"\nserie_ctp_vs_custo_real.csv: {len(d_out)} municípios")
    log("\nResumo — alíquota CTPU necessária pra cobrir 100% do custo real (menor->maior):")
    with pd.option_context("display.float_format", "{:.2%}".format):
        log(d_out[["nome_mun", "uf", "aliquota_necessaria_ctpu_100pct", "aliquota_necessaria_ctp_100pct"]].to_string(index=False))

    cob_2pct_ctpu = "cobertura_ctpu_2pct_anual"
    if cob_2pct_ctpu in d_out.columns:
        log(f"\nCobertura mediana a 2% (CTPU): {d_out[cob_2pct_ctpu].median():.1%}")
        log(f"Cobertura mediana a 2% (CTP): {d_out['cobertura_ctp_2pct_anual'].median():.1%}")


if __name__ == "__main__":
    main()
