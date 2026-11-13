#!/usr/bin/env python3
"""baixar_regic_2018.py — REGIC 2018 (IBGE): hierarquia urbana / centralidade e
arranjos populacionais por município. Baixa da geoftp do IBGE e integra ao v3.
Rode na SUA máquina (a geoftp é bloqueada no sandbox do Cowork).

Fonte (Regiões de Influência das Cidades 2018 — resultados definitivos):
  https://www.ibge.gov.br/geociencias/organizacao-do-territorio/redes-e-fluxos-geograficos/15798-regioes-de-influencia-das-cidades.html

USO:  python3 baixar_regic_2018.py
Saídas: _data/REGIC/*.xlsx (brutos) + _data/Base Municipal v3/regic_2018.csv
        e colunas no base_municipal_v3.csv: regic_hierarquia_2018 (texto),
        regic_nivel_2018 (ordinal 1=metrópole … 5=centro local)."""
import urllib.request, os, re, pandas as pd, numpy as np
# autodetecta _data: o script vive em <cofre>/_meta/scripts/
HERE=os.path.dirname(os.path.abspath(__file__))
V=os.path.join(os.path.abspath(os.path.join(HERE,"..","..")),"03 - Dados","_data")
REGIC=os.path.join(V,"REGIC"); OUT=os.path.join(V,"Base Municipal v3")
BASE=("https://geoftp.ibge.gov.br/organizacao_do_territorio/divisao_regional/"
      "regioes_de_influencia_das_cidades/"
      "Regioes_de_influencia_das_cidades_2018_Resultados_definitivos/base_tabular/")
ARQS=["REGIC2018_Municipios_Hierarquia_e_regiao.xlsx",
      "REGIC2018_Arranjos_Populacionais_v2.xlsx"]
def c7(x):
    try: return str(int(float(x))).zfill(7)
    except: return None
def nivel_de(grupo):
    m=re.match(r'\s*(\d)',str(grupo))     # "5 - Centro Local" -> 5
    return int(m.group(1)) if m else np.nan

os.makedirs(REGIC,exist_ok=True)
for a in ARQS:
    dest=os.path.join(REGIC,a)
    if not os.path.exists(dest):
        print("baixando",a,"..."); urllib.request.urlretrieve(BASE+a,dest)
    print("ok",dest)

# --- hierarquia (colunas exatas do REGIC 2018)
h=pd.read_excel(os.path.join(REGIC,"REGIC2018_Municipios_Hierarquia_e_regiao.xlsx"),dtype=str)
h.columns=[str(c).strip() for c in h.columns]
h["cod_ibge"]=h["codmun"].map(c7)
h["regic_hierarquia_2018"]=h["Hierarquia"]              # ex.: "Centro Sub-Regional A (3A)"
h["regic_grupo_2018"]=h["Hierarquia - grupo"]           # ex.: "3 - Centro Sub-Regional"
h["regic_nivel_2018"]=h["Hierarquia - grupo"].map(nivel_de)   # 1=metrópole … 5=centro local
h["arranjo_pop_2018"]=h["Arranjo Populacional"]
h["regic_regiao_infl_2018"]=h["Região de influência - vínculação imediata consolidada"]
cols=["cod_ibge","regic_hierarquia_2018","regic_grupo_2018","regic_nivel_2018","arranjo_pop_2018","regic_regiao_infl_2018"]
reg=h[cols].dropna(subset=["cod_ibge"]).drop_duplicates("cod_ibge")
reg.to_csv(os.path.join(OUT,"regic_2018.csv"),index=False)
print(f"regic_2018.csv: {len(reg)} munic")
print(reg.regic_grupo_2018.value_counts())

# --- integra ao wide
bp=os.path.join(OUT,"base_municipal_v3.csv")
base=pd.read_csv(bp,dtype={"cod_ibge":str},low_memory=False)
base["cod_ibge"]=base["cod_ibge"].map(c7)
base=base.drop(columns=[c for c in cols if c!="cod_ibge" and c in base.columns])
base=base.merge(reg,on="cod_ibge",how="left")
base.to_csv(bp,index=False)
print("wide atualizado:",base.shape,"| REGIC preench.:",base.regic_nivel_2018.notna().sum())
