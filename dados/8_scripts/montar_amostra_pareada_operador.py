# -*- coding: utf-8 -*-
"""
montar_amostra_pareada_operador.py — monta a amostra pareada do item 3 de
[[Análise - O que e um grande grupo e o teste pre-tratamento (06-09-2026)]] e
PRÉ-PREENCHE os candidatos a `operador_urbano_local`.

O que este script NÃO faz: ele não descobre quem opera o serviço urbano. Isso
exige fonte primária (contrato, licitação, e-SIC, Diário Oficial) e é trabalho
humano. O que ele faz é transformar "procurar no escuro" em "conferir uma lista
curta": para cada município da amostra, lista as empresas que têm
estabelecimento ATIVO com CNAE de transporte coletivo de passageiros por
itinerário fixo (4921-3/01 municipal e 4921-3/02 intermunicipal metropolitano)
naquele município, com o grupo econômico a que pertencem e o porte do grupo.

Desenho da amostra (§5 da nota):
  tratados  = TZ universal ATIVA em arranjo populacional (exclui os arranjos
              internacionais de fronteira — ver ressalva abaixo)
  controles = 1 por tratado, do MESMO arranjo, sem TZ, pareado por posição no
              arranjo e faixa de porte; sem reuso de controle entre tratados

⚠️ Arranjos internacionais: os 32 municípios em arranjo transfronteiriço ficam
FORA dos tratados porque o arranjo não tem outro município brasileiro — não há
sistema metropolitano nacional ao qual pertençam, que é a premissa do teste.
Quaraí/RS é o único caso de TZ nessa condição e sai listado à parte.

Ponte de código: o CNPJ da Receita usa código SIAFI/TOM no campo
`municipio_codigo_rfb`; a conversão para IBGE sai de
`_data/CNPJ/Receita Federal - dados brutos/municipios.csv` (coluna siafi_id).

Saídas em `03 - Dados/_data/Amostra pareada operador/`:
  amostra_pareada_operador.csv        — 1 linha por município, com as colunas de
                                        verificação primária EM BRANCO para preencher
  candidatos_operador_por_municipio.csv — 1 linha por empresa candidata
  amostra_pareada_operador.xlsx       — as duas abas, para trabalhar à mão
"""
import math
import os
import re
import unicodedata
import pandas as pd

VAULT = os.environ.get("TZ_VAULT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
D = os.path.join(VAULT, "03 - Dados", "_data")
CNPJ = os.path.join(D, "CNPJ", "filtrados (6 CNAEs transporte, 24-07-2026)")
OUT = os.path.join(D, "Amostra pareada operador")
os.makedirs(OUT, exist_ok=True)

CNAE_URBANO = {4921301: "municipal (urbano)", 4921302: "intermunicipal metropolitano"}
CAPITAL_GRANDE = 100_000_000     # R$ 100 mi -- critério proposto na nota
TAMANHO_GRANDE = 10             # 10+ empresas no componente

FAIXAS = ["Inferior a 20 mil", "Entre 20 e 100 mil", "Entre 100 e 250 mil",
          "Entre 250 e 500 mil", "Acima de 500 mil"]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


# ---------------------------------------------------------------- base
COLS = ["cod_ibge", "nome_mun", "uf", "pop_2022", "faixa_pop_2022", "tz_universal",
        "tz_situacao", "tz_ano_inicio", "posicao_arranjo", "arranjo_pop_ibge",
        "arranjo_internacional", "regic_nivel_2018", "regic_hierarquia_2018",
        "munic_onibus_intramun_2017", "munic_concessao_2017", "munic_permissao_2017",
        "munic_autorizacao_2017", "munic_prestacao_direta_2017", "munic_nao_regulamentado_2017",
        "munic_onibus_intramun_2012", "munic_concessao_2020", "munic_prestacao_direta_2020",
        "frota_bus", "concessionioria", "cadunico_cobertura_pct_202508"]
base = pd.read_csv(os.path.join(D, "Base Municipal v3", "base_municipal_v3.csv"),
                   usecols=lambda c: c in COLS, low_memory=False)
for c in ["pop_2022", "tz_universal", "arranjo_internacional", "regic_nivel_2018"]:
    base[c] = pd.to_numeric(base[c], errors="coerce")


def outorga_2017(r):
    m = {"Concessão": "munic_concessao_2017", "Permissão": "munic_permissao_2017",
         "Autorização": "munic_autorizacao_2017", "Prestação direta": "munic_prestacao_direta_2017",
         "Não regulamentado": "munic_nao_regulamentado_2017"}
    if pd.isna(r.get("munic_onibus_intramun_2017")):
        return "sem resposta MUNIC 2017"
    if str(r.get("munic_onibus_intramun_2017")) not in ("1", "1.0"):
        return "sem sistema intramunicipal em 2017"
    ativos = [k for k, c in m.items() if str(r.get(c)) in ("1", "1.0")]
    return " + ".join(ativos) if ativos else "sistema sem outorga informada"


base["outorga_2017"] = base.apply(outorga_2017, axis=1)

# ---------------------------------------------------------------- grupos e porte
cap = pd.read_csv(os.path.join(CNPJ, "capital_social_por_grupo.csv"))
cap["porte_capital"] = cap["capital_social_total_reais"] >= CAPITAL_GRANDE
cap["porte_tamanho"] = cap["tamanho"] >= TAMANHO_GRANDE
cap["grande"] = cap["porte_capital"] | cap["porte_tamanho"]
# CHAVE: id_grupo é nulo em 294 dos 517 componentes (componentes sem nome atribuído,
# tipicamente pares de 2 empresas sem sócio-âncora identificado). O join tem de ser por
# componente_id, que é único e cobre os 517 — usar id_grupo perderia 57% dos componentes.
porte = cap.drop_duplicates("componente_id").set_index("componente_id")

# 25/09/2026: lia o CSV de 04/08 (165 grupos, numeração superada); passa a ler a tabela mestre XLSX (12/08, 327 grupos)
mestre = pd.read_excel(os.path.join(os.path.dirname(os.path.dirname(CNPJ)), "..", "Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx"), sheet_name="Empresas").replace({"None": None})
mestre_por_cnpj = mestre.drop_duplicates("cnpj_basico").set_index("cnpj_basico")

# ---------------------------------------------------------------- estabelecimentos urbanos
mun_rfb = pd.read_csv(os.path.join(D, "CNPJ", "Receita Federal - dados brutos", "municipios.csv"), dtype=str)
mun_rfb["siafi_id"] = pd.to_numeric(mun_rfb["siafi_id"], errors="coerce")
mun_rfb["codigo_ibge"] = pd.to_numeric(mun_rfb["codigo_ibge"], errors="coerce")
siafi2ibge = mun_rfb.dropna(subset=["siafi_id"]).set_index("siafi_id")["codigo_ibge"]

est = pd.read_csv(os.path.join(CNPJ, "estabelecimentos_ativos_6cnaes.csv"), low_memory=False)
est = est[est["cnae_fiscal_principal"].isin(CNAE_URBANO)].copy()
est["cod_ibge"] = pd.to_numeric(est["municipio_codigo_rfb"], errors="coerce").map(siafi2ibge)
print(f"estabelecimentos com CNAE urbano: {len(est)} | sem ponte SIAFI->IBGE: {est['cod_ibge'].isna().sum()}")
est = est.dropna(subset=["cod_ibge"])
est["cod_ibge"] = est["cod_ibge"].astype(int)

est["razao_social"] = est["cnpj_basico"].map(mestre_por_cnpj["razao_social"])
est["id_grupo"] = est["cnpj_basico"].map(mestre_por_cnpj["id_grupo"])
est["nome_grupo"] = est["cnpj_basico"].map(mestre_por_cnpj["nome_grupo"])
est["componente"] = est["cnpj_basico"].map(mestre_por_cnpj["componente_id_v4"])
est["capital_grupo"] = est["componente"].map(porte["capital_social_total_reais"])
est["empresas_grupo"] = est["componente"].map(porte["tamanho"])
est["grupo_grande"] = est["componente"].map(porte["grande"])
est["cnae_desc"] = est["cnae_fiscal_principal"].map(CNAE_URBANO)
est["cnpj_raiz"] = est["cnpj_basico"].astype(str).str.zfill(8)

# ---------------------------------------------------------------- amostra
tratados = base[(base["tz_universal"] == 1) & (base["posicao_arranjo"] != "isolado")
                & (base["arranjo_internacional"] == 0)].copy()
fora = base[(base["tz_universal"] == 1) & (base["posicao_arranjo"] != "isolado")
            & (base["arranjo_internacional"] == 1)]
print(f"tratados: {len(tratados)} | TZ em arranjo internacional (fora): {len(fora)} "
      f"{fora['nome_mun'].tolist()}")

pool = base[(base["tz_universal"] != 1) & (base["posicao_arranjo"] != "isolado")
            & (base["arranjo_internacional"] == 0)].copy()
fx = {f: i for i, f in enumerate(FAIXAS)}
pool["_fx"] = pool["faixa_pop_2022"].map(fx)
tratados["_fx"] = tratados["faixa_pop_2022"].map(fx)

def ranquear(cand, t):
    """Ordena candidatos a controle: primeiro mesma posição no arranjo, depois faixa
    de porte, depois proximidade populacional em escala log (2x maior e 2x menor
    pesam igual)."""
    c = cand.copy()
    c["_d_pos"] = (c["posicao_arranjo"] != t["posicao_arranjo"]).astype(int)
    c["_d_fx"] = (c["_fx"] - t["_fx"]).abs().fillna(9)
    razao = c["pop_2022"] / t["pop_2022"]
    c["_d_pop"] = razao.apply(lambda v: abs(math.log(v)) if pd.notna(v) and v > 0 else 9)
    return c.sort_values(["_d_pos", "_d_fx", "_d_pop"])


# Pareamento em duas camadas, e a razão de haver duas:
#   controle PRIMÁRIO  = mesmo arranjo (mantém o sistema metropolitano constante)
#   controle ALTERNATIVO = mesma posição no arranjo, de outro arranjo da mesma UF —
#     só é preenchido quando o primário saiu com posição DIFERENTE do tratado.
# Os dois desenhos trocam um controle pelo outro: um segura o sistema, o outro segura
# a posição. Qual usar é decisão do autor; por isso saem os dois, em vez de eu escolher.
usados, pares = set(), []
for _, t in tratados.sort_values("pop_2022", ascending=False).iterrows():
    mesmo_arr = pool[(pool["arranjo_pop_ibge"] == t["arranjo_pop_ibge"])
                     & (~pool["cod_ibge"].isin(usados))]
    if mesmo_arr.empty:
        pares.append((t["cod_ibge"], None, "sem controle no mesmo arranjo", None)); continue
    esc = ranquear(mesmo_arr, t).iloc[0]
    usados.add(esc["cod_ibge"])
    qual = ("mesmo arranjo, mesma posição, mesma faixa" if esc["_d_pos"] == 0 and esc["_d_fx"] == 0
            else "mesmo arranjo, mesma posição, faixa vizinha" if esc["_d_pos"] == 0
            else "mesmo arranjo, posição diferente")
    alt = None
    if esc["_d_pos"] != 0:
        outros = pool[(pool["uf"] == t["uf"]) & (pool["posicao_arranjo"] == t["posicao_arranjo"])
                      & (pool["arranjo_pop_ibge"] != t["arranjo_pop_ibge"])
                      & (~pool["cod_ibge"].isin(usados))]
        if not outros.empty:
            a = ranquear(outros, t).iloc[0]
            usados.add(a["cod_ibge"]); alt = a["cod_ibge"]
    pares.append((t["cod_ibge"], esc["cod_ibge"], qual, alt))

linhas = []
for cod_t, cod_c, qual, cod_a in pares:
    for papel, cod in (("tratado", cod_t), ("controle", cod_c),
                       ("controle_alt_mesma_posicao", cod_a)):
        if cod is None:
            continue
        r = base[base["cod_ibge"] == cod].iloc[0]
        cands = est[est["cod_ibge"] == cod]
        linhas.append({
            "par_id": f"P{[p[0] for p in pares].index(cod_t) + 1:03d}",
            "papel": papel,
            "qualidade_pareamento": qual if papel == "controle" else (
                "mesma posição, outro arranjo da UF" if papel.startswith("controle_alt") else ""),
            "cod_ibge": cod, "nome_mun": r["nome_mun"], "uf": r["uf"],
            "arranjo": r["arranjo_pop_ibge"], "posicao_arranjo": r["posicao_arranjo"],
            "pop_2022": r["pop_2022"], "faixa_pop": r["faixa_pop_2022"],
            "regic": r.get("regic_hierarquia_2018"),
            "tz_situacao": r["tz_situacao"], "tz_ano_inicio": r["tz_ano_inicio"],
            "outorga_2017": r["outorga_2017"],
            "concessionaria_polo_2016": r.get("concessionioria"),
            "cobertura_cadunico_pct": r.get("cadunico_cobertura_pct_202508"),
            "n_candidatos_cnae_urbano": len(cands),
            "candidatos_razao_social": " | ".join(cands["razao_social"].dropna().astype(str).unique()[:8]),
            "candidatos_grupo": " | ".join(cands["nome_grupo"].dropna().astype(str).unique()[:8]),
            "algum_candidato_de_grande_grupo": ("sim" if cands["grupo_grande"].astype("boolean").fillna(False).any()
                                                else ("não" if len(cands) else "sem candidato")),
            # ---- a preencher em fonte primária ----
            "operador_urbano_local": "", "grupo_do_operador": "",
            "operador_e_grande_grupo": "", "fonte": "", "url_ou_documento": "",
            "data_verificacao": "", "confianca": "", "observacoes": "",
        })

am = pd.DataFrame(linhas)
cand_out = est[est["cod_ibge"].isin(am["cod_ibge"])][
    ["cod_ibge", "cnpj_raiz", "razao_social", "nome_fantasia", "cnae_fiscal_principal", "cnae_desc",
     "componente", "id_grupo", "nome_grupo", "capital_grupo", "empresas_grupo", "grupo_grande", "uf"]
].merge(base[["cod_ibge", "nome_mun"]], on="cod_ibge", how="left").sort_values(["cod_ibge", "razao_social"])

am.to_csv(os.path.join(OUT, "amostra_pareada_operador.csv"), index=False)
cand_out.to_csv(os.path.join(OUT, "candidatos_operador_por_municipio.csv"), index=False)
with pd.ExcelWriter(os.path.join(OUT, "amostra_pareada_operador.xlsx")) as w:
    am.to_excel(w, sheet_name="amostra", index=False)
    cand_out.to_excel(w, sheet_name="candidatos", index=False)

print(f"\namostra: {len(am)} municípios ({(am.papel=='tratado').sum()} tratados + "
      f"{(am.papel=='controle').sum()} controles primários + "
      f"{am.papel.str.startswith('controle_alt').sum()} controles alternativos)")
print("qualidade do pareamento:")
print(am[am.papel == 'controle']['qualidade_pareamento'].value_counts().to_string())
print("\ncandidatos com CNAE urbano:", len(cand_out),
      f"| municípios sem nenhum candidato: {am['n_candidatos_cnae_urbano'].eq(0).sum()}")
print("\nalgum candidato de grande grupo, por papel:")
print(pd.crosstab(am['papel'], am['algum_candidato_de_grande_grupo']).to_string())
print(f"\ngravado em: {OUT}")
