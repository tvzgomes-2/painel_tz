#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consolidar_legislacao.py — funde os arquivos de controle de legislação/PlanMob
dos 176 casos da camada universal num único arquivo canônico.

CONTEXTO
  Entre 07 e 09/09/2026, a consolidação de legislação foi tentada por partes,
  em sessões diferentes, e produziu MAIS arquivos em vez de menos:
  `base_legislacao_contratos_175` (3 versões), `Estado da legislacao - 176
  casos` (4 versões), `normas_padronizadas` (3 versões), mais dois arquivos
  de cruzamento com PlanMob. O `LEIA-ME.md` que deveria dizer qual é
  canônico ficou defasado no processo (não chegou a listar a v4 do Estado).

  Este script funde as três peças município-a-município (base de
  legislação/contrato, estado documental A-C, PlanMob+fontes) num único
  arquivo, mantendo `normas_padronizadas` (grão de norma, não de município)
  como tabela satélite — granularidades diferentes não se fundem numa só
  tabela sem perda.

FONTES (município-a-município, 176 linhas cada)
  - `base_legislacao_contratos_175 (v3, 09-09-2026).csv` — espinha: tem as
    colunas de contrato/operador que são o insumo do Cap 7.
  - `Estado da legislacao - 176 casos (v4, 09-09-2026).csv` — classificação
    documental A/B1/B2/B3/C, prioridade de busca, URLs.
  - `Municipios TZ - legislacao, PlanMob e pesquisas (09-09-2026).csv` —
    PlanMob e flags de cobertura por fonte da literatura (175 linhas — ver
    nota sobre Palmas/TO abaixo).

JUNÇÃO E CASOS ESPECIAIS
  - Chave preferencial: `cod_ibge` (mais confiável que nome, dados os pares
    Palmas/TO×PR, Pirapora/MG×Pirapora do Bom Jesus/SP, Vargem/SP×Vargem
    Grande Paulista/SP já registrados no cofre).
  - **Palmas/TO tem 2 políticas (2023 e 2025) sob o mesmo `cod_ibge`.** A
    base e o Estado têm 2 linhas cada (176 no total); o arquivo de
    PlanMob/fontes tem só 175 — 1 linha por município, não por política,
    porque PlanMob é instrumento municipal, não vinculado à política de TZ.
    Por isso a junção com esse arquivo é `cod_ibge` (N:1) — as duas linhas
    de Palmas/TO recebem o mesmo PlanMob, corretamente.
  - Junção com o Estado usa `(município, uf, ano_inicio)` — sem `cod_ibge`
    nesse arquivo — com verificação de que nenhuma linha fica sem par.

COLISÕES DE NOME RESOLVIDAS (sem apagar nenhum dado)
  - `prioridade` existe nos dois com sentidos diferentes (base: rótulo tipo
    "2 - ativa sem norma"; Estado: 1-5 por custo de busca) → Estado entra
    como `prioridade_estado`.
  - `data_verificacao` existe nos dois → Estado entra como
    `data_verificacao_estado`.
  - Colunas de junção repetidas (`municipio`, `uf`, `situacao`, `ano_inicio`,
    `pop_2022`, `cod_ibge`) são mantidas uma vez só, vindas da base.
  - Colunas do arquivo de PlanMob que duplicam o que já vem do Estado
    (`estado_legislacao`, `prioridade_legislacao`, `norma_declarada`,
    `descoberto_09_09`, `falta_legislacao`, `ano_inicio_tz`) são descartadas
    — ficariam redundantes e um dos dois lados ficaria mais desatualizado
    sem ninguém notar.

VERIFICAÇÃO DE INTEGRIDADE (roda sempre, imprime no console)
  - confirma 176 linhas na saída;
  - confirma 0 linhas sem par no Estado e 0 sem par no PlanMob;
  - confirma que `TZ x PlanMob - 176 casos` (arquivo mais antigo, superado
    pelo de PlanMob+fontes) não diverge do que foi absorvido — se divergir,
    o script avisa e não decide por conta própria.

USO
  python consolidar_legislacao.py
  (roda de dentro de `_meta/scripts/`; espera as fontes em
  `../../03 - Dados/_data/Legislacao e contratos TZ/`, e escreve o resultado
  no mesmo diretório, sem apagar nenhum arquivo de entrada)

SAÍDA
  `Controle unico - legislacao PlanMob e contratos, 176 casos (AAAA-MM-DD).csv`
  no mesmo diretório das fontes — nunca sobrescreve; cada rodada gera um
  arquivo novo datado, e o autor decide quando promover a versão anterior a
  histórico (mesma regra do LEIA-ME.md desta pasta).

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof. Dra. Silvana Zioni
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd

PASTA = Path(__file__).resolve().parent.parent.parent / "03 - Dados" / "_data" / "Legislacao e contratos TZ"

ARQ_BASE = "_historico/base_legislacao_contratos_175 (v3, 09-09-2026).csv"
ARQ_ESTADO = "_historico/Estado da legislacao - 176 casos (v4, 09-09-2026).csv"
ARQ_PLANMOB = "_historico/Municipios TZ - legislacao, PlanMob e pesquisas (09-09-2026).csv"
ARQ_TZPLANMOB_HISTORICO = "_historico/TZ x PlanMob - 176 casos (09-09-2026).csv"
ARQ_NORMAS = "_historico/normas_padronizadas (v3, 09-09-2026).csv"


def carregar(nome):
    caminho = PASTA / nome
    with open(caminho, encoding="utf-8-sig") as f:
        primeira = f.readline()
    sep = ";" if primeira.count(";") > primeira.count(",") else ","
    return pd.read_csv(caminho, sep=sep, encoding="utf-8-sig", dtype=str)


def main():
    base = carregar(ARQ_BASE)
    estado = carregar(ARQ_ESTADO)
    planmob = carregar(ARQ_PLANMOB)
    tzplanmob_hist = carregar(ARQ_TZPLANMOB_HISTORICO)
    normas = carregar(ARQ_NORMAS)

    print(f"base: {len(base)} linhas · estado: {len(estado)} · planmob: {len(planmob)} "
          f"· normas_padronizadas: {len(normas)}")

    # 1) verificação: TZ x PlanMob (histórico) não diverge do que foi absorvido
    chk = tzplanmob_hist.merge(planmob, on="cod_ibge", suffixes=("_tzp", "_pm"), how="left")
    divergiu = chk[chk.possui_planmob.astype(str) != chk.planmob_declarado.astype(str)]
    if len(divergiu):
        print(f"⚠️ ATENÇÃO: {len(divergiu)} linhas de '{ARQ_TZPLANMOB_HISTORICO}' divergem do "
              f"arquivo de PlanMob mais novo — não descartar sem olhar. Rodando mesmo assim.")
    else:
        print(f"✅ '{ARQ_TZPLANMOB_HISTORICO}' confirmado como redundante (0 divergências) — "
              f"seguro marcar como histórico.")

    # 2) junção com Estado, por (municipio, uf, ano_inicio) — cobre Palmas/TO (2 políticas)
    chave_estado = ["municipio", "uf", "ano_inicio"]
    cols_estado = [c for c in estado.columns if c not in ("municipio", "uf", "situacao", "ano_inicio", "pop_2022")]
    estado_renomeado = estado[["municipio", "uf", "ano_inicio"] + [c for c in cols_estado]].rename(
        columns={"prioridade": "prioridade_estado", "data_verificacao": "data_verificacao_estado"}
    )
    fundido = base.merge(estado_renomeado, on=chave_estado, how="left", validate="one_to_one")
    sem_par_estado = fundido[fundido["estado"].isna()]
    print(f"linhas sem par no Estado: {len(sem_par_estado)}")

    # 3) junção com PlanMob+fontes, por cod_ibge (N:1 — Palmas/TO recebe o mesmo PlanMob 2x)
    cols_planmob_manter = [c for c in planmob.columns if c.startswith("planmob_") or c.startswith("fonte_")]
    planmob_renomeado = planmob[["cod_ibge"] + cols_planmob_manter].rename(
        columns={"obs_cruzamento": "obs_cruzamento_planmob"} if "obs_cruzamento" in planmob.columns else {}
    )
    fundido = fundido.merge(planmob_renomeado, on="cod_ibge", how="left")
    sem_par_planmob = fundido[fundido["planmob_declarado"].isna()]
    print(f"linhas sem par no PlanMob: {len(sem_par_planmob)}")

    # 4) contagem de normas_padronizadas por município — só a contagem, o detalhe fica na tabela satélite
    contagem_normas = normas.groupby(["municipio", "uf"]).size().reset_index(name="n_normas_padronizadas")
    fundido = fundido.merge(contagem_normas, on=["municipio", "uf"], how="left")
    fundido["n_normas_padronizadas"] = fundido["n_normas_padronizadas"].fillna(0).astype(int)

    print(f"\nresultado final: {len(fundido)} linhas, {len(fundido.columns)} colunas")
    if len(fundido) != 176:
        print(f"🔴 ATENÇÃO: esperava 176 linhas, saiu {len(fundido)} — não escrevendo saída. Investigar antes de rodar de novo.")
        return 1
    if len(sem_par_estado) or len(sem_par_planmob):
        print("🔴 ATENÇÃO: há linhas sem par — confira acima antes de considerar a fusão completa.")

    hoje = date.today().isoformat()
    saida = PASTA / f"Controle unico - legislacao PlanMob e contratos, 176 casos ({hoje}).csv"
    fundido.to_csv(saida, index=False, encoding="utf-8-sig")
    print(f"\nSalvo em: {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
