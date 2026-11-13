#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""processar_informalidade_censo2022.py — a partir do CSV bruto já baixado
por `baixar_censo2022_informalidade.py` (tabela SIDRA 10261, Censo 2022,
resultados preliminares da amostra), calcula a TAXA DE INFORMALIDADE AMPLA
por município e integra ao banco municipal.

DECISÃO METODOLÓGICA (combinada com o autor, 23-24/07/2026): definição
AMPLA de informalidade, não restrita a "empregado sem carteira".

COMO A COMPOSIÇÃO FOI DEFINIDA (não foi um chute — verificado nos dados):
a classificação "Posição na ocupação e categoria do emprego no trabalho
principal" (D3 da tabela 10261) é uma árvore de 2 níveis. Confirmado
numericamente (soma dos filhos = valor do pai, testado em São Paulo e nos
5.570 municípios, diferença média de 0,8 pessoa — arredondamento da amostra
expandida, não erro): existem 15 categorias-FOLHA, mutuamente exclusivas,
que somam exatamente ao Total (96165):

  Formais: privado c/carteira [31722], doméstico c/carteira [79367],
  militar/estatutário/bombeiro [79369], público estatutário [79370],
  público não-estatutário c/carteira [79372], estatais c/carteira [79375],
  empregador com CNPJ [45934], conta própria com CNPJ [45936]

  INFORMAIS (somados aqui): privado SEM carteira [31723], doméstico SEM
  carteira [79368], público não-estatutário SEM carteira [79373], estatais
  SEM carteira [79376], empregador SEM CNPJ [45935], conta própria SEM CNPJ
  [45937], trabalhador familiar auxiliar (sem remuneração direta) [31731]

Esta composição (sem carteira em qualquer categoria de empregado + sem CNPJ
em conta própria/empregador + trabalhador familiar auxiliar) é a definição
convencional de informalidade usada nas estatísticas de trabalho brasileiras
(mesmo critério citado por institutos estaduais de pesquisa econômica ao
comentar os dados do Censo 2022) — não é uma composição inventada aqui.

⚠️ RESSALVAS (repetir sempre que citar):
1. Dado AMOSTRAL preliminar do Censo 2022 (~10% da população) — maior erro
   amostral em municípios pequenos. Sem coluna de CV nesta tabela (SIDRA
   10261 não trouxe margem/CV junto do valor "V" nesta extração).
2. Não filtrar por Cor ou raça = qualquer coisa diferente de "Total" (código
   95251) — a tabela repete os mesmos números por raça (Total/Branca/Preta/
   Amarela/Parda/Indígena); somar todas as linhas sem filtrar por Total
   DOBRA os valores (Total já é o agregado, não é a soma das 5 raças a somar
   de novo). Este script já filtra isso.
3. Estatutário e militar são tratados como SEMPRE formais (não têm o
   conceito de "carteira assinada" — outro regime jurídico) — não entram no
   numerador de informalidade em nenhuma composição usual.
4. Ano-safra: Censo 2022, diferente do RAIS 2022 (mesma safra ano, mas
   fontes/métodos diferentes — RAIS é registro administrativo trabalhista,
   Censo é autodeclaração domiciliar).

SAÍDA: `serie_informalidade_censo2022.csv` (painel, todas as 15 categorias-
folha + agregados) + colunas resumo no wide (`ocupados_total_censo2022`,
`informais_ampla_censo2022`, `taxa_informalidade_ampla_censo2022_pct`).

USO: python processar_informalidade_censo2022.py"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..")), "03 - Dados", "_data")
OUT = os.path.join(V, "Base Municipal v3")
BASE_CSV = os.path.join(OUT, "base_municipal_v3.csv")
SIDRA_CSV = os.path.join(HERE, "saida_censo2022", "sidra_10261_posicao_ocupacao.csv")

# categorias-folha (D3C), com rótulo, pra painel completo
CATEGORIAS = {
    "31722": "privado_c_carteira", "31723": "privado_s_carteira",
    "79367": "domestico_c_carteira", "79368": "domestico_s_carteira",
    "79369": "militar_estatutario_bombeiro",
    "79370": "publico_estatutario",
    "79372": "publico_naoestat_c_carteira", "79373": "publico_naoestat_s_carteira",
    "79375": "estatal_c_carteira", "79376": "estatal_s_carteira",
    "45934": "empregador_com_cnpj", "45935": "empregador_sem_cnpj",
    "45936": "conta_propria_com_cnpj", "45937": "conta_propria_sem_cnpj",
    "31731": "trabalhador_familiar_auxiliar",
}
TOTAL_CODIGO = "96165"
COR_RACA_TOTAL = "95251"  # filtra a classificação "Cor ou raça" só pra Total (evita somar 6x)

INFORMAL_CODIGOS = ["31723", "79368", "79373", "79376", "45935", "45937", "31731"]


def log(msg):
    print(msg, flush=True)


def salvar_atomico(df, path):
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def c7(x):
    try:
        return str(int(float(x))).zfill(7)
    except Exception:
        return None


def main():
    if not os.path.exists(SIDRA_CSV):
        sys.exit(f"Não achei {SIDRA_CSV} — rode baixar_censo2022_informalidade.py primeiro.")

    log(f"Lendo {SIDRA_CSV} ...")
    df = pd.read_csv(SIDRA_CSV, skiprows=[1], dtype=str, usecols=["D1C", "D3C", "D5C", "V"])
    df = df[df["D1C"] != "Município (Código)"]  # linha de cabeçalho repetida
    antes = len(df)
    df = df[df["D5C"] == COR_RACA_TOTAL].copy()  # crítico: evita somar as 6 categorias de raça
    log(f"  {antes} linhas -> {len(df)} após filtrar Cor ou raça = Total")
    df["V"] = pd.to_numeric(df["V"], errors="coerce")
    df["cod_ibge"] = df["D1C"].map(c7)

    piv = df.pivot_table(index="cod_ibge", columns="D3C", values="V", aggfunc="sum")

    faltando = [c for c in list(CATEGORIAS.keys()) + [TOTAL_CODIGO] if c not in piv.columns]
    if faltando:
        sys.exit(f"Categorias esperadas não encontradas na tabela: {faltando} — "
                  f"confira se a estrutura da tabela 10261 mudou.")

    # checagem de consistência: soma das folhas deve bater com o Total (SIDRA)
    soma_folhas = piv[list(CATEGORIAS.keys())].sum(axis=1, min_count=1)
    dif = (soma_folhas - piv[TOTAL_CODIGO]).abs()
    log(f"  checagem folhas vs Total: diferença média={dif.mean():.2f}, máxima={dif.max():.0f} "
        f"(arredondamento esperado da amostra expandida, não é erro)")

    painel = piv[[TOTAL_CODIGO] + list(CATEGORIAS.keys())].rename(
        columns={TOTAL_CODIGO: "ocupados_total_censo2022", **CATEGORIAS}
    ).reset_index()

    painel["informais_ampla_censo2022"] = painel[[CATEGORIAS[c] for c in INFORMAL_CODIGOS]].sum(axis=1, min_count=1)
    painel["taxa_informalidade_ampla_censo2022_pct"] = (
        painel["informais_ampla_censo2022"] / painel["ocupados_total_censo2022"] * 100
    ).round(1)

    log(f"\nResumo nacional:")
    log(f"  municípios: {len(painel)}")
    log(f"  taxa de informalidade ampla — mediana: {painel['taxa_informalidade_ampla_censo2022_pct'].median()}%, "
        f"min: {painel['taxa_informalidade_ampla_censo2022_pct'].min()}%, "
        f"max: {painel['taxa_informalidade_ampla_censo2022_pct'].max()}%")

    salvar_atomico(painel, os.path.join(OUT, "serie_informalidade_censo2022.csv"))
    log(f"  salvo: serie_informalidade_censo2022.csv ({painel.shape[0]} x {painel.shape[1]})")

    # integra colunas-resumo no wide
    base = pd.read_csv(BASE_CSV, dtype={"cod_ibge": str}, low_memory=False)
    base["cod_ibge"] = base["cod_ibge"].map(c7)
    resumo = painel[["cod_ibge", "ocupados_total_censo2022", "informais_ampla_censo2022",
                      "taxa_informalidade_ampla_censo2022_pct"]]
    base = base.drop(columns=[c for c in resumo.columns if c != "cod_ibge" and c in base.columns])
    base = base.merge(resumo, on="cod_ibge", how="left")
    salvar_atomico(base, BASE_CSV)
    log(f"\nOK — base_municipal_v3.csv: {base.shape[0]} x {base.shape[1]} (+3 colunas resumo)")
    log(
        "\nRESSALVAS a levar pra tese: (1) dado amostral preliminar do Censo 2022, sem CV "
        "nesta extração — maior incerteza em municípios pequenos; (2) estatutário/militar "
        "tratados como sempre formais; (3) ano-safra Censo 2022 x RAIS 2022 — fontes e "
        "métodos diferentes, não comparar diretamente linha a linha."
    )


if __name__ == "__main__":
    main()
