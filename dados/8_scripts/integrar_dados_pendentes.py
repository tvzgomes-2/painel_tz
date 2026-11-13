#!/usr/bin/env python3
"""integrar_dados_pendentes.py — integra ao Banco Municipal v3 tudo que já foi
BAIXADO mas ainda não processado (auditoria de 20/07/2026):

  A) FINBRA Anexo I-E (despesa por FUNÇÃO) — Urbanismo (f.15, zeladoria/infra
     urbana) e Transporte (f.26), 2019–2023. CORRIGE um bug do script anterior
     (agregar_finbra_funcao.py): a extração do nº de função por regex NÃO
     ancorada somava a função-mãe + cada subfunção + o resíduo "FUNN" juntos,
     inflando o valor (ex.: função 8 contava "08 - ...", "08.244 - ..." e
     "FU08 - ..." como se fossem 3 valores distintos). Aqui a extração usa
     regex ANCORADA no início de 'conta' (padrão "NN - Nome"), que casa só a
     linha de nível função e exclui subfunções/resíduos automaticamente.

  B) SIMU / Ministério das Cidades (pacotes já baixados em _data/SIMU/):
     B1. mortes + feridos no trânsito, 2010–2019, 5.570 municípios -> a
         sinistralidade que faltava no banco.
     B2. Carteira de Empreendimentos -> INVESTIMENTOS em obras de mobilidade
         (PAC/OGU), por município (portfólio, não série).
     B3. tarifa + frota, 2010–2021, 5.570 municípios (cobertura nacional,
         complementa a série PEMOB/ANTP que só cobre ~102 municípios).
     B4. tempo de deslocamento (Censo 2010, ano único).
     B5. extensão de vias — ciclovias/ciclofaixas/calçadas (2017–2021, do
         pacote PEMOB do SIMU) -> resolve parte do item pendente
         "extensão viária e cicloviária" do blueprint (sem precisar de OSM).

Rodar da pasta que contém '03 - Dados' (o cofre), ou em qualquer lugar — o
script localiza _data sozinho a partir do próprio caminho do arquivo.

USO:  python integrar_dados_pendentes.py
Requer: pandas (já instalado). Não acessa rede — só lê o que já está no disco.
"""
import os, re, sys, traceback, warnings
import pandas as pd
import numpy as np
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
np.seterr(divide="ignore", invalid="ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..")), "03 - Dados", "_data")
FN = os.path.join(V, "FINBRA_nacional")
SIMU = os.path.join(V, "SIMU")
OUT = os.path.join(V, "Base Municipal v3")
BASE_CSV = os.path.join(OUT, "base_municipal_v3.csv")


def c7(x):
    try:
        return str(int(float(x))).zfill(7)
    except Exception:
        return None


def cagr(a, b, n):
    a = pd.to_numeric(a, errors="coerce")
    b = pd.to_numeric(b, errors="coerce")
    with np.errstate(invalid="ignore"):
        r = np.where((a > 0) & (b > 0), (b / a) ** (1 / n) - 1, np.nan)
    return np.round(r * 100, 2)


def log(msg):
    print(msg, flush=True)


# ======================================================================
# A) FINBRA Anexo I-E — despesa por FUNÇÃO (corrigido)
# ======================================================================
def parte_a_finbra_funcao():
    log("\n=== A) FINBRA — despesa por função (Anexo I-E) ===")
    ALVO = {4: "administracao", 15: "urbanismo", 16: "habitacao",
            17: "saneamento", 25: "energia", 26: "transporte"}
    padrao_funcao = re.compile(r"^\s*(\d{2})\s*-\s+\S")  # "NN - Nome" (ancorado!)

    recs = []
    cobertura = {}
    for ano in range(2019, 2024):
        f = os.path.join(FN, f"finbra_funcao_{ano}.csv")
        if not os.path.exists(f):
            log(f"  ! {f} não encontrado — pulando {ano}")
            continue
        log(f"  lendo {os.path.basename(f)} ...")
        d = pd.read_csv(f, usecols=["cod_ibge", "coluna", "conta", "valor"],
                         dtype={"cod_ibge": str, "coluna": str, "conta": str},
                         low_memory=False)
        d = d[d["coluna"] == "Despesas Empenhadas"]
        func = d["conta"].str.extract(padrao_funcao)[0]
        d = d.assign(func=pd.to_numeric(func, errors="coerce"))
        d = d[d["func"].isin(ALVO)]
        d["valor"] = pd.to_numeric(d["valor"], errors="coerce")
        d["cod_ibge"] = d["cod_ibge"].map(c7)
        g = d.groupby(["cod_ibge", "func"], as_index=False)["valor"].sum()
        g["ano"] = ano
        recs.append(g)
        cobertura[ano] = d["cod_ibge"].nunique()

    if not recs:
        log("  nenhum dado de função encontrado — abortando parte A.")
        return None

    sf = pd.concat(recs, ignore_index=True)
    sf["funcao_nome"] = sf["func"].map(ALVO)
    wide_sf = sf.pivot_table(index=["cod_ibge", "ano"], columns="funcao_nome",
                              values="valor").reset_index()
    wide_sf.columns = [f"desp_{c}" if c not in ("cod_ibge", "ano") else c
                        for c in wide_sf.columns]
    wide_sf.to_csv(os.path.join(OUT, "serie_funcao.csv"), index=False)

    log(f"  serie_funcao.csv: {wide_sf.shape[0]} linhas | anos: {sorted(sf.ano.unique())}")
    for ano, n in cobertura.items():
        alerta = "" if n >= 5560 else f"  ⚠️ cobertura parcial ({n}/5570 municípios)"
        log(f"    {ano}: {n} municípios com dado{alerta}")

    # sanidade: função 26 (Transporte) não deve superar ~30% da despesa total em município típico
    return wide_sf


def integra_finbra_funcao(base, wide_sf):
    if wide_sf is None:
        return base
    log("  integrando ao wide (snapshot 2022 + CAGR 2019->último ano completo)...")
    desp_emp = pd.to_numeric(base.get("despesa_empenhada_2022"), errors="coerce")
    d22 = wide_sf[wide_sf.ano == 2022].set_index("cod_ibge")
    for nome in ["urbanismo", "transporte"]:
        col = f"desp_{nome}"
        if col not in wide_sf.columns:
            continue
        v22 = pd.to_numeric(d22[col].reindex(base["cod_ibge"]).values, errors="coerce")
        base[f"{col}_2022"] = v22
        base[f"pct_{nome}_desp_2022"] = np.round(v22 / desp_emp * 100, 2)
        w = wide_sf.pivot_table(index="cod_ibge", columns="ano", values=col)
        if 2019 in w.columns and 2022 in w.columns:
            base[f"{nome}_cagr_2019_2022"] = cagr(
                w[2019].reindex(base["cod_ibge"]).values,
                w[2022].reindex(base["cod_ibge"]).values, 3)
        # 2023 pode estar parcial (cobertura < 100%) — incluído "como está", sem imputar
        if 2023 in w.columns:
            base[f"{col}_2023_parcial"] = pd.to_numeric(
                w[2023].reindex(base["cod_ibge"]).values, errors="coerce")
    return base


# ======================================================================
# B) SIMU
# ======================================================================
def le_simu(rel_path, usecols):
    f = os.path.join(SIMU, rel_path)
    if not os.path.exists(f):
        log(f"  ! {f} não encontrado — pulando.")
        return None
    d = pd.read_csv(f, usecols=usecols, encoding="utf-8-sig", low_memory=False)
    d.columns = [c.strip() for c in d.columns]
    cod_col = next(c for c in d.columns if "digo" in c.lower() and "ibge" in c.lower())
    d["cod_ibge"] = d[cod_col].map(c7)
    return d.drop(columns=[cod_col])


def parte_b1_sinistralidade():
    log("\n=== B1) SIMU — mortes e feridos no trânsito (sinistralidade) ===")
    m = le_simu("mortes/simu-mortes-mun-T.csv", ["Código IBGE", "ano", "total_mortes", "taxa_mun"])
    f = le_simu("feridos/simu-feridos-mun-T.csv", ["Código IBGE", "ano", "total_feridos", "taxa_mun"])
    if m is None or f is None:
        return None
    m = m.rename(columns={"total_mortes": "obitos_transito", "taxa_mun": "taxa_obitos_100k"})
    f = f.rename(columns={"total_feridos": "feridos_transito", "taxa_mun": "taxa_feridos_100k"})
    serie = m.merge(f, on=["cod_ibge", "ano"], how="outer")
    serie.to_csv(os.path.join(OUT, "serie_sinistralidade.csv"), index=False)
    log(f"  serie_sinistralidade.csv: {serie.shape} | anos: {sorted(serie.ano.dropna().unique())}")
    return serie


def integra_sinistralidade(base, serie):
    if serie is None:
        return base
    ult = int(serie.ano.max())
    prim = int(serie.ano.min())
    w_ob = serie.pivot_table(index="cod_ibge", columns="ano", values="obitos_transito")
    w_fe = serie.pivot_table(index="cod_ibge", columns="ano", values="feridos_transito")
    w_tx = serie.pivot_table(index="cod_ibge", columns="ano", values="taxa_obitos_100k")
    base[f"obitos_transito_{ult}"] = pd.to_numeric(w_ob[ult].reindex(base.cod_ibge).values, errors="coerce")
    base[f"feridos_transito_{ult}"] = pd.to_numeric(w_fe[ult].reindex(base.cod_ibge).values, errors="coerce")
    base[f"taxa_obitos_transito_100k_{ult}"] = pd.to_numeric(w_tx[ult].reindex(base.cod_ibge).values, errors="coerce")
    if prim in w_ob.columns:
        base[f"obitos_transito_cagr_{prim}_{ult}"] = cagr(
            w_ob[prim].reindex(base.cod_ibge).values, w_ob[ult].reindex(base.cod_ibge).values, ult - prim)
    log(f"  integrado: obitos_transito_{ult}, feridos_transito_{ult}, taxa_obitos_transito_100k_{ult}")
    return base


def parte_b2_carteira():
    log("\n=== B2) SIMU — Carteira de Empreendimentos (investimentos em mobilidade) ===")
    d = le_simu("carteira/simu-carteira-mun-T.csv",
                ["Código IBGE", "vlr_investimento_num", "vlr_desembolsado_num", "situacao_obra"])
    if d is None:
        return None
    for c in ["vlr_investimento_num", "vlr_desembolsado_num"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    g = d.groupby("cod_ibge").agg(
        simu_investimento_carteira_total=("vlr_investimento_num", "sum"),
        simu_desembolsado_carteira_total=("vlr_desembolsado_num", "sum"),
        simu_empreendimentos_n=("vlr_investimento_num", "size"),
    ).reset_index()
    concl = (d.assign(concl=d["situacao_obra"].astype(str).str.upper().str.contains("CONCLU"))
             .groupby("cod_ibge")["concl"].sum().reset_index()
             .rename(columns={"concl": "simu_empreendimentos_concluidos_n"}))
    g = g.merge(concl, on="cod_ibge", how="left")
    g.to_csv(os.path.join(OUT, "simu_carteira_investimentos.csv"), index=False)
    log(f"  simu_carteira_investimentos.csv: {g.shape[0]} municípios com ao menos 1 empreendimento")
    return g


def integra_carteira(base, g):
    if g is None:
        return base
    base = base.merge(g, on="cod_ibge", how="left")
    log("  integrado: simu_investimento_carteira_total, simu_desembolsado_carteira_total, "
        "simu_empreendimentos_n, simu_empreendimentos_concluidos_n")
    return base


def parte_b3_tarifa_frota():
    log("\n=== B3) SIMU — tarifa e frota, 2010-2021 (cobertura nacional) ===")
    tar = le_simu("tarifas/simu-tarifas-mun_T.csv", ["Código IBGE", "ano", "Tarifa"])
    fr = le_simu("frota/simu-frota-mun_T.csv", ["Código IBGE", "ano", "TOTAL_VEICULOS", "ONIBUS"])
    if tar is not None:
        tar = tar.rename(columns={"Tarifa": "tarifa_simu"})
        tar.to_csv(os.path.join(OUT, "serie_tarifa_simu.csv"), index=False)
        log(f"  serie_tarifa_simu.csv: {tar.shape} | anos: {sorted(tar.ano.dropna().unique())}")
    if fr is not None:
        fr = fr.rename(columns={"TOTAL_VEICULOS": "frota_total_simu", "ONIBUS": "frota_onibus_simu"})
        fr.to_csv(os.path.join(OUT, "serie_frota_simu.csv"), index=False)
        log(f"  serie_frota_simu.csv: {fr.shape} | anos: {sorted(fr.ano.dropna().unique())}")
    return tar, fr


def integra_tarifa_frota(base, tar, fr):
    if tar is not None:
        ult = int(tar.ano.max()); prim = int(tar.ano.min())
        w = tar.pivot_table(index="cod_ibge", columns="ano", values="tarifa_simu")
        base[f"tarifa_simu_{ult}"] = pd.to_numeric(w[ult].reindex(base.cod_ibge).values, errors="coerce")
        if prim in w.columns:
            base[f"tarifa_simu_cagr_{prim}_{ult}"] = cagr(
                w[prim].reindex(base.cod_ibge).values, w[ult].reindex(base.cod_ibge).values, ult - prim)
        log(f"  integrado: tarifa_simu_{ult}, tarifa_simu_cagr_{prim}_{ult}")
    if fr is not None:
        ult = int(fr.ano.max()); prim = int(fr.ano.min())
        wo = fr.pivot_table(index="cod_ibge", columns="ano", values="frota_onibus_simu")
        wt = fr.pivot_table(index="cod_ibge", columns="ano", values="frota_total_simu")
        base[f"frota_onibus_simu_{ult}"] = pd.to_numeric(wo[ult].reindex(base.cod_ibge).values, errors="coerce")
        base[f"frota_total_simu_{ult}"] = pd.to_numeric(wt[ult].reindex(base.cod_ibge).values, errors="coerce")
        if prim in wo.columns:
            base[f"frota_onibus_simu_cagr_{prim}_{ult}"] = cagr(
                wo[prim].reindex(base.cod_ibge).values, wo[ult].reindex(base.cod_ibge).values, ult - prim)
        log(f"  integrado: frota_onibus_simu_{ult}, frota_total_simu_{ult}")
    return base


def parte_b4_tempo_deslocamento(base):
    log("\n=== B4) SIMU — tempo de deslocamento (Censo 2010, ano único) ===")
    d = le_simu("tempo_deslocamento/simu-tempo-deslocamento_mun_T.csv",
                ["Código IBGE", "Tempo_medio_desloc_min", "Prc_pessoas_mais_1h_desloc"])
    if d is None:
        return base
    d = d.rename(columns={"Tempo_medio_desloc_min": "tempo_medio_desloc_min_2010",
                          "Prc_pessoas_mais_1h_desloc": "prc_desloc_mais_1h_2010"})
    base = base.merge(d.drop_duplicates("cod_ibge"), on="cod_ibge", how="left")
    log("  integrado: tempo_medio_desloc_min_2010, prc_desloc_mais_1h_2010")
    return base


def parte_b5_infra_viaria(base):
    log("\n=== B5) SIMU — infraestrutura viária/cicloviária (via pacote PEMOB, 2017-2021) ===")
    d = le_simu("pemob/simu-pemob-mun_T.csv",
                ["Código IBGE", "ano", "km_via_ciclovias", "km_via_ciclofaixas", "km_via_calcadas"])
    if d is None:
        return base
    for c in ["km_via_ciclovias", "km_via_ciclofaixas", "km_via_calcadas"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    # pega o valor mais recente não nulo por município (dado esparso ao longo dos anos)
    d = d.sort_values("ano")
    ult = d.groupby("cod_ibge").last().reset_index()
    ult = ult.rename(columns={"km_via_ciclovias": "km_ciclovias_simu",
                              "km_via_ciclofaixas": "km_ciclofaixas_simu",
                              "km_via_calcadas": "km_calcadas_simu"})
    ult.to_csv(os.path.join(OUT, "simu_infra_viaria.csv"), index=False)
    base = base.merge(ult[["cod_ibge", "km_ciclovias_simu", "km_ciclofaixas_simu", "km_calcadas_simu"]],
                       on="cod_ibge", how="left")
    log(f"  integrado: km_ciclovias_simu ({ult.km_ciclovias_simu.notna().sum()} munic. com dado), "
        f"km_ciclofaixas_simu, km_calcadas_simu (último ano disponível por município, 2017-2021)")
    return base


# ======================================================================
def main():
    log(f"_data em: {V}")
    if not os.path.exists(BASE_CSV):
        log(f"ERRO: {BASE_CSV} não encontrado."); sys.exit(1)

    # --- parte A: calcula fora do wide primeiro ---
    wide_sf = safe(parte_a_finbra_funcao)

    # --- parte B: calcula tudo fora do wide também ---
    serie_sinistr = safe(parte_b1_sinistralidade)
    carteira = safe(parte_b2_carteira)
    tar, fr = safe(parte_b3_tarifa_frota) or (None, None)

    # --- agora um único load + merge + save do wide ---
    log("\n=== Integrando tudo ao base_municipal_v3.csv (uma única leitura/escrita) ===")
    base = pd.read_csv(BASE_CSV, dtype={"cod_ibge": str}, low_memory=False)
    base["cod_ibge"] = base["cod_ibge"].map(c7)

    base = integra_finbra_funcao(base, wide_sf)
    base = integra_sinistralidade(base, serie_sinistr)
    base = integra_carteira(base, carteira)
    base = integra_tarifa_frota(base, tar, fr)
    r4 = safe(lambda: parte_b4_tempo_deslocamento(base))
    base = r4 if r4 is not None else base
    r5 = safe(lambda: parte_b5_infra_viaria(base))
    base = r5 if r5 is not None else base

    base.to_csv(BASE_CSV, index=False)
    log(f"\nOK — base_municipal_v3.csv atualizado: {base.shape[0]} municípios x {base.shape[1]} colunas.")
    log("Lembrete: atualizar metadados.csv e a documentação (Banco Municipal v3 / ETL / Auditoria) "
        "com as novas variáveis, e rodar auditar_cofre.py.")


def safe(fn):
    """Executa fn(); em caso de erro, imprime o traceback e segue (não derruba o script)."""
    try:
        return fn()
    except Exception:
        log(f"  !! ERRO em {getattr(fn, '__name__', fn)}:")
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()
