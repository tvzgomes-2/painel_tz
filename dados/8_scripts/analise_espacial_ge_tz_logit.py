import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
import warnings
warnings.filterwarnings("ignore")

gdf = gpd.read_file("gdf_final.gpkg")
df = pd.DataFrame(gdf.drop(columns="geometry"))

# Logistic regression: TZ ~ GE score + log(pop)
X = sm.add_constant(df[["ge_score","log_pop"]])
y = df["tz_universal"]
model = sm.Logit(y, X).fit(disp=0)
print("=== Logit: TZ ~ GE_score + log_pop ===")
print(model.summary2().tables[1])
print()

# Marginal effects for interpretability
print("Odds ratios:")
print(np.exp(model.params))
print()

# Now with the NARROWER variable: presença de 1 dos 11 grupos reconhecidos (robustez)
espac = pd.read_csv("/sessions/kind-sleepy-feynman/mnt/doutorado/03 - Dados/_data/CNPJ/filtrados (6 CNAEs transporte, 24-07-2026)/espacializacao_grupos_por_municipio.csv")
municipios_com_grupo = set(espac["cod_ibge"].unique())
df["tem_grupo_reconhecido"] = df["cod_ibge"].isin(municipios_com_grupo).astype(int)
print(f"Municípios com 1 dos 11 grupos reconhecidos: {df['tem_grupo_reconhecido'].sum()}")
print(f"  dos quais TZ universal (hoje): {df[df['tem_grupo_reconhecido']==1]['tz_universal'].sum()}")
print(f"  taxa TZ nesse subconjunto: {df[df['tem_grupo_reconhecido']==1]['tz_universal'].mean():.4f}")
print(f"  taxa TZ nacional: {df['tz_universal'].mean():.4f}")

corr2 = df[["tem_grupo_reconhecido","tz_universal"]].corr().iloc[0,1]
print(f"Correlação simples (grupo reconhecido x TZ): {corr2:.4f}")

X2 = sm.add_constant(df[["tem_grupo_reconhecido","log_pop"]])
model2 = sm.Logit(y, X2).fit(disp=0)
print("\n=== Logit: TZ ~ tem_grupo_reconhecido + log_pop ===")
print(model2.summary2().tables[1])
print("Odds ratios:", np.exp(model2.params).to_dict())
