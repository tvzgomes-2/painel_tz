#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""simular_ctp_ctpu.py — simula, por município, uma Contribuição sobre a
folha de pagamento para custear o transporte público (modelo francês
"versement mobilité", já discutido na tese via os fichamentos [[Fichamento
- Estudo R$ 78 bi Frente Parlamentar TZ (Folha, 2025)]] — CTP — e
[[Fichamento - Ipea CTPU contribuição x vale-transporte (Estadão, 2026)]] —
CTPU). Decisão com o autor (23/07/2026): rodar os DOIS modelos em paralelo,
para todos os 5.570 municípios, usando remuneração média oficial (SIDRA)
em vez de valor fixo chutado.

FONTES DE DADOS (3, todas já baixadas/localizadas nesta rodada):
  1. `_data/POLO/.../t_rais/rais_2022.csv` — RAIS 2022 (eSocial), vínculos
     por FAIXA DE TAMANHO DO ESTABELECIMENTO empregador, por município
     (nome+UF, sem cod_ibge). É a única fonte com HEADCOUNT (nº de
     vínculos, não nº de empresas) por faixa — por isso é a base da
     simulação de quem é isento/tributado. Tem um footer de linhas
     "Sem classificacao"/"total"/metadados que precisa ser descartado
     (uf nula identifica todas elas) — sem isso, a soma nacional dava
     105,6 milhões (quase o dobro do esperado); limpo, os 5.570 municípios
     somam ~52,79 milhões, hoje batendo com a ordem de grandeza esperada
     para RAIS/eSocial 2022.
  2. SIDRA 9509 (`saida_rais/sidra_9509_salario_medio_bruto.csv`) —
     salário médio mensal (R$) e pessoal ocupado assalariado, por
     município, ano 2024 — baixado localmente (ver
     `baixar_rais_cempre_sidra.py`) porque a API do SIDRA está bloqueada
     no sandbox do Claude.
  3. SIDRA 9582 (`saida_rais/sidra_9582_porte_filtrado.csv`) — Nº de
     EMPRESAS (não vínculos) por faixa de pessoal ocupado, por município,
     2024 — usado só para VALIDAÇÃO CRUZADA de porte (é uma variável
     diferente da 1, headcount x contagem de empresas, e um ano diferente,
     2022 x 2024 — não dá pra usar diretamente na simulação, é outra
     unidade de medida).

⚠️ QUEBRA METODOLÓGICA A DOCUMENTAR NA TESE: RAIS tradicional (declaração
anual) terminou no ano-base 2021; a série 2022+ é derivada do eSocial —
2022 (fonte 1) e 2024 (fontes 2/3) já são a mesma metodologia entre si, mas
o CORTE DE PORTE (fonte 1, 2022) e o SALÁRIO MÉDIO (fonte 2, 2024) são de
ANOS DIFERENTES — o resultado mistura 2 anos-safra, ressalva a registrar.

MODELO (dois cenários, lado a lado, nenhum escolhido como "o certo"):
  - CTP (inspirado na proposta da Frente Parlamentar/UnB): isenta
    estabelecimentos até 9 vínculos — base tributável = soma das faixas
    de 10-19 vínculos em diante.
  - CTPU (inspirado no Ipea): sem isenção — base tributável = total de
    vínculos.
  Para cada cenário, calcula a arrecadação simulada em VÁRIAS alíquotas
  (as mesmas usadas nos 2 estudos já fichados: 0,5% / 1% / 1,7% / 2,6% /
  3,8% / 4,8% / 8,5%), usando:
      arrecadação_simulada = base_tributável × salário_médio_mensal × alíquota
  Isso trata "folha" como (nº de vínculos tributáveis × salário médio do
  município) — uma APROXIMAÇÃO (a folha real soma salários individuais,
  não a média vezes a contagem; super/sub-estima em municípios com
  distribuição de renda muito desigual). Documentar essa simplificação
  sempre que citar os números.

SAÍDA: `serie_ctp_ctpu_simulacao.csv` (painel completo, 1 linha por
município, todas as alíquotas) + colunas resumo no wide (`base_tributavel_
ctp`, `base_tributavel_ctpu`, `arrecadacao_ctp_2pct`, `arrecadacao_ctpu_
2pct` — a 2% como referência única no wide; o painel completo tem todas
as alíquotas).

USO: python simular_ctp_ctpu.py"""
import os
import re
import unicodedata

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..")), "03 - Dados", "_data")
OUT = os.path.join(V, "Base Municipal v3")
BASE_CSV = os.path.join(OUT, "base_municipal_v3.csv")
POLO_RAIS_CSV = os.path.join(V, "POLO", "_extraido", "rais_2022.csv")  # ajuste se o caminho local for outro
SIDRA_SALARIO_CSV = os.path.join(HERE, "saida_rais", "sidra_9509_salario_medio_bruto.csv")
SIDRA_PORTE_CSV = os.path.join(HERE, "saida_rais", "sidra_9582_porte_filtrado.csv")

FAIXAS_ISENTAS_CTP = ["de_1_a_4", "de_5_a_9"]  # isentas no cenário CTP (até 9 vínculos)
FAIXAS_TODAS = ["de_1_a_4", "de_5_a_9", "de_10_a_19", "de_20_a_49", "de_50_a_99",
                "de_100_a_249", "de_250_a_499", "de_500_a_999", "1000_ou_mais"]

ALIQUOTAS = [0.005, 0.01, 0.017, 0.02, 0.026, 0.038, 0.048, 0.085]  # cenários já usados na literatura fichada
# 0,02 (2%) incluída à parte: é a alíquota de referência citada pelo Ipea
# ("uma CTPU de 2% cobriria mais de 50% dos custos na maioria das
# capitais") — usada como coluna-resumo no wide, além do painel completo.
ALIQUOTA_RESUMO = 0.02

# reaproveitado de corrige_nomes_tse_2024.py (mesmo problema de nome
# desatualizado em nome_mun — não é específico do TSE, é da base toda)
CORRECOES_NOME = {
    "BA|CAMACA": "2905602", "SE|GRACCHOCARDOSO": "2802601", "MG|BRAZOPOLIS": "3108909",
    "RN|ASSU": "2400208", "RN|SERRACAIADA": "2410306", "PB|SAOVICENTEDOSERIDO": "2515401",
    "TO|TABOCAO": "1708254", "PE|IGUARACY": "2606903", "CE|ITAPAJE": "2306306",
    "SP|MOGIMIRIM": "3530805", "RO|ALVORADADOOESTE": "1100346", "MT|POXOREU": "5107008",
    "SP|FLORINEA": "3516101", "RN|CAMPOGRANDE": "2401305", "SP|EMBUDASARTES": "3515004",
    "PB|JOCACLAUDINO": "2513653", "RN|BOASAUDE": "2405306", "BA|SANTATEREZINHA": "2928505",
    "BA|MUQUEMDOSAOFRANCISCO": "2922250", "RO|ESPIGAODOOESTE": "1100098", "RN|AREZ": "2401206",
}

# específicas do rais_2022.csv da POLO (achadas nesta rodada, 23/07/2026) —
# não são renomeação, são variante de preposição (de/do/dos) ou grafia
# (Izabel/Isabel) entre o nome usado pela POLO no ETL e o nome_mun do banco.
# Único candidato em cada UF, conferido no banco antes de codificar aqui.
CORRECOES_NOME_POLO = {
    "PA|ELDORADODOCARAJAS": "1502954",       # base: "Eldorado Dos Carajás"
    "PA|SANTAIZABELDOPARA": "1506500",       # base: "Santa Isabel Do Pará" (Izabel/Isabel)
    "PE|BELEMDESAOFRANCISCO": "2601607",     # base: "Belém Do São Francisco" (de/do)
    "PE|LAGOADOITAENGA": "2608503",          # base: "Lagoa De Itaenga" (do/de)
}


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


def carregar_polo_rais(base_nomes):
    if not os.path.exists(POLO_RAIS_CSV):
        raise FileNotFoundError(
            f"Não achei {POLO_RAIS_CSV}. Ajuste POLO_RAIS_CSV no topo do script para o "
            f"caminho onde você extraiu 't_rais/rais_2022.csv' do "
            f"banco_geral_nacional_csv_20260717.zip."
        )
    df = pd.read_csv(POLO_RAIS_CSV)
    antes = len(df)
    df = df[df["uf"].notna()].copy()  # descarta "Sem classificacao"/linhas em branco/"total" (footer)
    log(f"POLO rais_2022.csv: {antes} linhas brutas -> {len(df)} após descartar footer/uf nula")

    df["chave"] = df["uf"].str.upper().str.strip() + "|" + df["municipio"].map(norm)
    bridge = base_nomes.assign(chave=base_nomes.uf.str.upper().str.strip() + "|" + base_nomes.nome_mun.map(norm))
    d = df.merge(bridge[["chave", "cod_ibge"]], on="chave", how="left")

    sem_match = d[d.cod_ibge.isna()]
    for _, row in sem_match.iterrows():
        cod = CORRECOES_NOME.get(row["chave"]) or CORRECOES_NOME_POLO.get(row["chave"])
        if cod:
            d.loc[d["chave"] == row["chave"], "cod_ibge"] = cod
    ainda_sem = d[d.cod_ibge.isna()][["municipio", "uf"]].drop_duplicates()
    if len(ainda_sem):
        log(f"  ⚠️ ainda sem cod_ibge após correções conhecidas ({len(ainda_sem)} casos):")
        log(f"  {ainda_sem.to_string(index=False)}")
    d = d.dropna(subset=["cod_ibge"])
    d["cod_ibge"] = d["cod_ibge"].map(c7)
    log(f"  {d.cod_ibge.nunique()} municípios com cod_ibge (de {df.municipio.nunique()} nomes distintos no bruto)")
    return d


def carregar_sidra_salario():
    df = pd.read_csv(SIDRA_SALARIO_CSV, skiprows=[1])
    df = df[df["D1C"] != "Município (Código)"].copy()  # linha de cabeçalho repetida (header='y' do sidrapy)
    df["cod_ibge"] = df["D1C"].astype(str).map(c7)
    # o SIDRA usa "-", ".." ou "..." para valores ausentes/sigilosos — vira
    # NaN em vez de quebrar a multiplicação mais adiante (object * float)
    df["V"] = pd.to_numeric(df["V"], errors="coerce")
    piv = df.pivot_table(index="cod_ibge", columns="D3N", values="V", aggfunc="first")
    piv.columns = [norm(c) for c in piv.columns]
    piv = piv.reset_index()
    col_salario = [c for c in piv.columns if "SALARIOMEDIOMENSALEMREAIS" in c]
    col_pessoal = [c for c in piv.columns if c == "PESSOALOCUPADOASSALARIADO"]
    if not col_salario:
        log(f"  ⚠️ não achei a coluna de salário médio em reais entre: {piv.columns.tolist()}")
    ren = {}
    if col_salario:
        ren[col_salario[0]] = "salario_medio_mensal_r"
    if col_pessoal:
        ren[col_pessoal[0]] = "pessoal_ocupado_assalariado_sidra"
    piv = piv.rename(columns=ren)
    keep = ["cod_ibge"] + list(ren.values())
    log(f"SIDRA 9509: {piv.cod_ibge.nunique()} municípios, colunas usadas: {list(ren.values())}")
    return piv[keep]


def main():
    base = pd.read_csv(BASE_CSV, dtype={"cod_ibge": str}, low_memory=False)
    base["cod_ibge"] = base["cod_ibge"].map(c7)
    base_nomes = base[["cod_ibge", "nome_mun", "uf"]].copy()

    rais = carregar_polo_rais(base_nomes)
    salario = carregar_sidra_salario()

    for f in FAIXAS_TODAS:
        rais[f] = pd.to_numeric(rais[f], errors="coerce").fillna(0)
    rais["base_tributavel_ctpu"] = rais[FAIXAS_TODAS].sum(axis=1)
    rais["base_tributavel_ctp"] = rais[[f for f in FAIXAS_TODAS if f not in FAIXAS_ISENTAS_CTP]].sum(axis=1)

    painel = rais[["cod_ibge", "base_tributavel_ctp", "base_tributavel_ctpu"] + FAIXAS_TODAS].merge(
        salario, on="cod_ibge", how="left"
    )
    sem_salario = painel["salario_medio_mensal_r"].isna().sum()
    if sem_salario:
        log(f"  ⚠️ {sem_salario} municípios com base RAIS mas sem salário médio SIDRA (não simulados)")

    for aliq in ALIQUOTAS:
        rotulo = f"{aliq*100:.1f}pct".replace(".0pct", "pct")
        painel[f"arrecadacao_ctp_{rotulo}"] = (
            painel["base_tributavel_ctp"] * painel["salario_medio_mensal_r"] * aliq
        )
        painel[f"arrecadacao_ctpu_{rotulo}"] = (
            painel["base_tributavel_ctpu"] * painel["salario_medio_mensal_r"] * aliq
        )

    salvar_atomico(painel, os.path.join(OUT, "serie_ctp_ctpu_simulacao.csv"))
    log(f"\nserie_ctp_ctpu_simulacao.csv: {painel.shape[0]} municípios x {painel.shape[1]} colunas")
    log(f"  base tributável CTP (mediana): {painel.base_tributavel_ctp.median():,.0f} vínculos")
    log(f"  base tributável CTPU (mediana): {painel.base_tributavel_ctpu.median():,.0f} vínculos")
    log(f"  arrecadação simulada CTPU a 2% (mediana): "
        f"R$ {painel.get('arrecadacao_ctpu_2pct', pd.Series(dtype=float)).median():,.0f}/mês")

    # resumo no wide: só a alíquota de referência (2%) + as bases tributáveis
    resumo = painel[["cod_ibge", "base_tributavel_ctp", "base_tributavel_ctpu",
                      "salario_medio_mensal_r", "arrecadacao_ctp_2pct", "arrecadacao_ctpu_2pct"]]
    base = base.drop(columns=[c for c in resumo.columns if c != "cod_ibge" and c in base.columns])
    base = base.merge(resumo, on="cod_ibge", how="left")
    salvar_atomico(base, BASE_CSV)
    log(f"\nOK — base_municipal_v3.csv: {base.shape[0]} x {base.shape[1]} "
        f"(+5 colunas resumo; painel completo com todas as alíquotas em serie_ctp_ctpu_simulacao.csv)")
    log(
        "\nRESSALVAS a levar pra tese: (1) mistura ano-safra 2022 (porte, POLO) "
        "com 2024 (salário, SIDRA); (2) 'folha' = nº vínculos tributáveis × "
        "salário MÉDIO do município, não soma de salários reais — "
        "sub/superestima em municípios desiguais; (3) nenhuma comparação "
        "com custo do sistema de TP foi feita aqui ainda (falta cruzar com "
        "tarifa_reconciliada/subsidio_pct_custo_ntu/custo das fichas NTU "
        "TZ) — próximo passo, não incluído nesta rodada."
    )


if __name__ == "__main__":
    main()
