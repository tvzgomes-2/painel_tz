#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""classificar_confianca_nucleo.py — em vez de excluir municípios do
recorte núcleo (CNAE 4921301/4921302) por filtros binários, que descartam
desproporcionalmente municípios pequenos (ver `pesquisa dos CNPJs.md` §
"Tabela comparativa de filtros de limpeza"), atribui um ESCORE DE
CONFIANÇA (0 a 5) a cada um dos 3.405 municípios do núcleo, somando 5
sinais binários independentes:

  1. tem CNAE núcleo como PRINCIPAL (não só secundária)
  2. tem empresa cuja natureza jurídica NÃO é Empresário Individual (2135)
  3. tem empresa de porte NÃO micro-empresa (porte_empresa != "01")
  4. OpenStreetMap confirma presença de ônibus (`presenca_onibus_osm`)
  5. MUNIC 2020 confirma ônibus intramunicipal (`munic_onibus_intramun_2020`)

NÍVEL: ALTO (4-5 pontos) | MÉDIO (2-3 pontos) | BAIXO (0-1 pontos).

POR QUE ESTE DESENHO (24/07/2026): testes anteriores mostraram que (a) os
3 filtros internos (principal/natureza/porte) removem 45-64% do universo
bruto, majoritariamente municípios pequenos — exatamente o estrato que a
tese central estuda; (b) a MUNIC sozinha é uma fonte pouco confiável (mais
da metade das divergências CNPJ×MUNIC são corroboradas pelo OSM, ou seja,
parecem ser falha da MUNIC, não do CNPJ); (c) 30% dos municípios do núcleo
têm só 1 CNPJ, e esse subgrupo é o mais ambíguo nas 3 fontes ao mesmo
tempo. Um escore aditivo preserva TODOS os municípios na amostra (nenhum é
excluído), com o nível de confiança como informação explícita para as
análises seguintes (Passo 9, espacialização) decidirem como usar.

RESULTADO DA VALIDAÇÃO (rodado direto no acervo, 24/07/2026):
  ALTO  (4-5): 1.544 municípios (45,3%) — pop. mediana 36.716, 25,2% < 20 mil hab.
  MÉDIO (2-3): 1.320 municípios (38,8%) — pop. mediana 12.113, 73,6% < 20 mil hab.
  BAIXO (0-1):   541 municípios (15,9%) — pop. mediana  7.848, 86,9% < 20 mil hab.

USO:
    python "C:\Users\HOME\OneDrive\doutorado\_meta\scripts\classificar_confianca_nucleo.py"
"""
import csv
import os
from collections import defaultdict

import pandas as pd

RAIZ_CNPJ = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\CNPJ"
PASTA_FILTRADOS = os.path.join(RAIZ_CNPJ, "filtrados (6 CNAEs transporte, 24-07-2026)")
ARQUIVO_ESTAB_ATIVOS = os.path.join(PASTA_FILTRADOS, "estabelecimentos_ativos_6cnaes.csv")
ARQUIVO_EMPRESAS = os.path.join(PASTA_FILTRADOS, "empresas_filtrado_6cnaes.csv")
ARQUIVO_MUNICIPIOS_RFB = os.path.join(RAIZ_CNPJ, "Receita Federal - dados brutos", "municipios.csv")
BASE_MUNICIPAL_V3 = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\Base Municipal v3\base_municipal_v3.csv"
ARQUIVO_SAIDA = os.path.join(PASTA_FILTRADOS, "confianca_nucleo_por_municipio.csv")


def c7(x):
    try:
        return str(int(float(x))).zfill(7)
    except Exception:
        return None


def log(msg):
    print(msg, flush=True)


def nivel(pontos):
    if pontos >= 4:
        return "ALTO"
    if pontos >= 2:
        return "MEDIO"
    return "BAIXO"


def main():
    ponte = {}
    with open(ARQUIVO_MUNICIPIOS_RFB, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ponte[row["siafi_id"]] = c7(row["codigo_ibge"])

    empresas = {}
    with open(ARQUIVO_EMPRESAS, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["camada"] not in ("nucleo", "ambos"):
                continue
            empresas[row["cnpj_basico"]] = row

    por_muni = defaultdict(list)
    with open(ARQUIVO_ESTAB_ATIVOS, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["camada"] != "nucleo":
                continue
            cod = ponte.get(row["municipio_codigo_rfb"])
            if cod is None:
                continue
            e = empresas.get(row["cnpj_basico"])
            por_muni[cod].append({
                "cnpj_basico": row["cnpj_basico"],
                "tipo_match": row["tipo_match"],
                "natureza_juridica": e["natureza_juridica"] if e else None,
                "porte_empresa": e["porte_empresa"] if e else None,
            })

    base = pd.read_csv(BASE_MUNICIPAL_V3, dtype={"cod_ibge": str}, low_memory=False)
    base["cod_ibge"] = base["cod_ibge"].map(c7)
    munic_onibus = base.set_index("cod_ibge")["munic_onibus_intramun_2020"].to_dict()
    osm_presenca = base.set_index("cod_ibge")["presenca_onibus_osm"].to_dict()
    pop2022 = base.set_index("cod_ibge")["pop_2022"].to_dict()
    nome_uf = base.set_index("cod_ibge")[["nome_mun", "uf"]].to_dict("index")

    linhas = []
    for cod, regs in por_muni.items():
        tem_principal = any(r["tipo_match"] == "principal" for r in regs)
        tem_nao_ei = any(r["natureza_juridica"] != "2135" for r in regs)
        tem_nao_micro = any(r["porte_empresa"] != "01" for r in regs)
        osm = osm_presenca.get(cod) == 1
        munic = munic_onibus.get(cod) == 1
        pontos = sum([tem_principal, tem_nao_ei, tem_nao_micro, osm, munic])
        nu = nome_uf.get(cod, {})
        linhas.append({
            "cod_ibge": cod, "nome_mun": nu.get("nome_mun"), "uf": nu.get("uf"),
            "n_cnpj_nucleo": len(set(r["cnpj_basico"] for r in regs)),
            "pop_2022": pop2022.get(cod),
            "sinal_cnae_principal": int(tem_principal),
            "sinal_nao_empresario_individual": int(tem_nao_ei),
            "sinal_porte_nao_micro": int(tem_nao_micro),
            "sinal_osm": int(osm),
            "sinal_munic": int(munic),
            "escore_confianca": pontos,
            "nivel_confianca": nivel(pontos),
        })

    df = pd.DataFrame(linhas).sort_values(["nivel_confianca", "cod_ibge"])
    tmp = ARQUIVO_SAIDA + ".tmp"
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, ARQUIVO_SAIDA)

    log(f"{len(df)} municípios classificados.")
    for niv in ["ALTO", "MEDIO", "BAIXO"]:
        sub = df[df["nivel_confianca"] == niv]
        pop_mediana = sub["pop_2022"].median()
        pct_pequeno = (sub["pop_2022"] < 20000).mean() * 100
        log(f"  {niv}: {len(sub)} ({len(sub)/len(df)*100:.1f}%) | pop. mediana {pop_mediana:,.0f} | {pct_pequeno:.1f}% < 20 mil hab.")
    log(f"\nSalvo em: {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    main()
