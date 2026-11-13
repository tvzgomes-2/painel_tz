import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.api as sm
import warnings
warnings.filterwarnings("ignore")

gdf = gpd.read_file("gdf_final.gpkg")
df = pd.DataFrame(gdf.drop(columns="geometry"))
espac = pd.read_csv("/sessions/kind-sleepy-feynman/mnt/doutorado/03 - Dados/_data/CNPJ/filtrados (6 CNAEs transporte, 24-07-2026)/espacializacao_grupos_por_municipio.csv")
municipios_com_grupo = set(espac["cod_ibge"].unique())
df["tem_grupo_reconhecido"] = df["cod_ibge"].isin(municipios_com_grupo).astype(int)

for thresh in [30000, 50000, 100000]:
    sub = df[df["pop_2022"] >= thresh].copy()
    print(f"\n=== Município com população >= {thresh} (N={len(sub)}, TZ={sub['tz_universal'].sum()}, com grupo={sub['tem_grupo_reconhecido'].sum()}) ===")
    print(f"Taxa TZ com grupo reconhecido: {sub[sub['tem_grupo_reconhecido']==1]['tz_universal'].mean():.4f} | sem grupo: {sub[sub['tem_grupo_reconhecido']==0]['tz_universal'].mean():.4f}")
    print(f"Taxa TZ ge_score>=4 (alto): {sub[sub['ge_score']>=4]['tz_universal'].mean():.4f} | ge_score<4: {sub[sub['ge_score']<4]['tz_universal'].mean():.4f}")
    try:
        X = sm.add_constant(sub[["tem_grupo_reconhecido","log_pop"]])
        m = sm.Logit(sub["tz_universal"], X).fit(disp=0)
        print("Logit (grupo reconhecido, controlando pop):")
        print(m.summary2().tables[1])
    except Exception as e:
        print("Logit falhou:", e)
