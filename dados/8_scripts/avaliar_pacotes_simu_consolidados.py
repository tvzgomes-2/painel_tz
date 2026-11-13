#!/usr/bin/env python3
"""avaliar_pacotes_simu_consolidados.py — Avalia os 4 pacotes "indicador
consolidado" do SIMU (`acidentes`, `infraestrutura`, `politica_tarifaria`,
`servicos`) que ficaram pendentes na Auditoria de dados (20/07/2026, item 3):
"confirmar se agregam algo além dos microdados já integrados". Resultado
(22/07/2026), com o método de checagem:

  A) `acidentes/Acidentes de Transportes.csv` — 5.570/5.570 municípios,
     2010-2019, TODOS os anos com cobertura completa. Comparado o
     `total_mortes` de 2019 contra `obitos_transito_2019` (já integrado, via
     `mortes/simu-mortes-mun-T.csv`): **soma idêntica (31.939)** — é a MESMA
     fonte, só que aqui vem com a QUEBRA por tipo de vítima (pedestre,
     ciclista, motociclista, ocupante de automóvel/ônibus/veículo pesado,
     outros), que NÃO estava integrada. NÃO É REDUNDANTE — integrado abaixo
     (mortes de pedestre/ciclista/motociclista/ocupante de ônibus, 2019).

  B) `infraestrutura/Infraestrutura de Mobilidade Urbana.csv` — a frota por
     tipo de veículo (TOTAL_VEICULOS/ONIBUS/AUTOMOVEL/...) tem cobertura
     completa (5.526-5.570), mas é A MESMA fonte SIMU já integrada como
     `frota_onibus_simu_2021`/`frota_total_simu_2021` (via
     `frota/simu-frota-mun_T.csv`) — REDUNDANTE, não integrado de novo. As
     variáveis extras anexadas a este arquivo (custo_operacao, IPK, divisão
     modal) têm preenchimento de **9 a 57 municípios por ano** (0,2%-1%) —
     ver pacote C, é o mesmo bloco dessas variáveis.

  C) `politica_tarifaria/Política Tarifária.csv` — o campo `tarifa` tem
     45-66 municípios preenchidos por ano — mesma ordem de grandeza da
     série PEMOB/ANTP + SIMU tarifa JÁ integradas (~102 municípios,
     2016-2024) — REDUNDANTE, não integrado. Mesmo bloco de variáveis extras
     de C) que D).

  D) `servicos/Serviços de Mobilidade Urbana.csv` — bloco de variáveis
     (`custo_operacao` + detalhamento combustível/veículos/remuneração/
     peças/impostos/despesas administrativas, `IPK`, `divmodal_perc_*`,
     `idade_media_frota_onibus`, `arrec_*`, `pontos_emb_desemb`) com
     preenchimento de **apenas 9 a 64 municípios por ano (2017-2021)** —
     0,2%-1,2% de 5.570. MUITO ESPARSO para servir de variável de panorama
     nacional (mesmo problema já registrado para ciclovia/calçada do pacote
     pemob). NÃO integrado ao `base_municipal_v3.csv`.
     MAS: os ~60 municípios cobertos em 2020-2021 são, sistematicamente,
     capitais e grandes cidades de RM — e isso inclui **4 dos 7 municípios
     do Grande ABC** (Diadema, Mauá, Santo André, São Bernardo do Campo,
     todos 2021) — útil para estudo de caso (Eixo 3, ou a nota de apoio à
     proposta técnica do edital do Grande ABC), não para o panorama
     nacional. Extraído como tabela separada (`simu_servicos_grandes_cidades.csv`),
     NÃO fundido ao wide.

RESUMO: só o pacote A) tinha informação genuinamente nova e com cobertura
nacional. B) e C) são redundantes com o que já estava integrado. D) tem
informação nova mas inviável em escala nacional — guardada à parte.

USO:  python avaliar_pacotes_simu_consolidados.py
Requer: pandas. Não acessa rede."""
import os, sys
import pandas as pd
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..")), "03 - Dados", "_data")
SIMU = os.path.join(V, "SIMU")
OUT = os.path.join(V, "Base Municipal v3")
BASE_CSV = os.path.join(OUT, "base_municipal_v3.csv")


def c7(x):
    try:
        return str(int(float(x))).zfill(7)
    except Exception:
        return None


def log(msg):
    print(msg, flush=True)


def salvar_atomico(df, path):
    """Escreve em .tmp e substitui com os.replace() — ver incidente de
    22/07/2026 (corrige_nomes_tse_2024.py) sobre por que isso é obrigatório
    em qualquer script que reescreva base_municipal_v3.csv inteiro."""
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def parte_a_acidentes_por_modo():
    log("=== A) acidentes — quebra por tipo de vítima (2019, não redundante) ===")
    f = os.path.join(SIMU, "acidentes", "Acidentes de Transportes.csv")
    d = pd.read_csv(f, encoding="utf-8-sig", dtype=str, low_memory=False,
                     usecols=["Código IBGE", "ano", "Pedestre_mortes", "Ciclista_mortes",
                              "Motociclista_mortes", "Ocup_onibus_mortes",
                              "Pedestre_feridos", "Ciclista_feridos", "Ocup_onibus_feridos"])
    d = d.rename(columns={"Código IBGE": "cod_ibge"})
    d["cod_ibge"] = d["cod_ibge"].map(c7)
    d19 = d[d.ano == "2019"].copy()
    for c in d19.columns:
        if c not in ("cod_ibge", "ano"):
            d19[c] = pd.to_numeric(d19[c], errors="coerce")
    ren = {"Pedestre_mortes": "obitos_pedestre_2019", "Ciclista_mortes": "obitos_ciclista_2019",
           "Motociclista_mortes": "obitos_motociclista_2019", "Ocup_onibus_mortes": "obitos_ocup_onibus_2019",
           "Pedestre_feridos": "feridos_pedestre_2019", "Ciclista_feridos": "feridos_ciclista_2019",
           "Ocup_onibus_feridos": "feridos_ocup_onibus_2019"}
    d19 = d19.rename(columns=ren)[["cod_ibge"] + list(ren.values())]
    log(f"  {len(d19)} municípios | soma óbitos pedestre={d19.obitos_pedestre_2019.sum():.0f}, "
        f"ciclista={d19.obitos_ciclista_2019.sum():.0f}, motociclista={d19.obitos_motociclista_2019.sum():.0f}, "
        f"ocup. ônibus={d19.obitos_ocup_onibus_2019.sum():.0f}")
    return d19


def parte_d_servicos_grandes_cidades():
    log("\n=== D) servicos — subconjunto de grandes cidades (NÃO fundido ao wide) ===")
    f = os.path.join(SIMU, "servicos", "Serviços de Mobilidade Urbana.csv")
    d = pd.read_csv(f, encoding="utf-8-sig", dtype=str, low_memory=False)
    d = d.rename(columns={"Código IBGE": "cod_ibge"})
    d["cod_ibge"] = d["cod_ibge"].map(c7)
    numcols = ["custo_operacao", "custo_combustivel", "custo_veiculos", "custo_remuneracao_servico",
               "custo_pecas", "custo_impostos", "custo_despesas_adm", "IPK", "idade_media_frota_onibus",
               "divmodal_perc_a_pe", "divmodal_perc_bicicleta", "divmodal_perc_transp_coletivo",
               "divmodal_perc_automovel", "divmodal_perc_moto", "num_passageiros_transp"]
    for c in numcols:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d[d.ano.isin(["2020", "2021"])]
    cov = d[d["custo_operacao"].notna() | d["IPK"].notna()].sort_values(["Município", "ano"])
    keep = ["cod_ibge", "Município", "ano"] + numcols
    cov = cov[keep].drop_duplicates("cod_ibge", keep="last")
    out = os.path.join(OUT, "simu_servicos_grandes_cidades.csv")
    cov.to_csv(out, index=False)
    log(f"  {len(cov)} municípios (grandes cidades/capitais, 2020-2021) salvos em "
        f"simu_servicos_grandes_cidades.csv — NÃO integrado ao base_municipal_v3.csv (esparso demais "
        f"para variável de panorama nacional; ver docstring)")
    abc = ["3547809", "3548708", "3548807", "3513801", "3529401", "3543303", "3544103"]
    log(f"  cobertura no Grande ABC: {cov[cov.cod_ibge.isin(abc)]['Município'].tolist()}")


def main():
    if not os.path.exists(BASE_CSV):
        log(f"ERRO: {BASE_CSV} não encontrado."); sys.exit(1)

    acidentes = parte_a_acidentes_por_modo()
    parte_d_servicos_grandes_cidades()

    log("\n=== Integrando ao base_municipal_v3.csv (só o pacote A) ===")
    base = pd.read_csv(BASE_CSV, dtype={"cod_ibge": str}, low_memory=False)
    base["cod_ibge"] = base["cod_ibge"].map(c7)
    novas = [c for c in acidentes.columns if c != "cod_ibge"]
    base = base.drop(columns=[c for c in novas if c in base.columns])
    base = base.merge(acidentes, on="cod_ibge", how="left")
    salvar_atomico(base, BASE_CSV)
    log(f"OK — base_municipal_v3.csv atualizado: {base.shape[0]} x {base.shape[1]} "
        f"(+{len(novas)} colunas: {', '.join(novas)})")
    log("Lembrete: atualizar metadados.csv e a Auditoria de dados; rodar auditar_cofre.py.")


if __name__ == "__main__":
    main()
