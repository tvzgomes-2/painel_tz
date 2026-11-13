import pandas as pd
import geopandas as gpd
import numpy as np
import libpysal
from libpysal.weights import Queen, KNN
import esda
import warnings
warnings.filterwarnings("ignore")

base = "/sessions/kind-sleepy-feynman/mnt/doutorado"

# 1. Load attribute data
df = pd.read_csv(f"{base}/03 - Dados/_data/Base Municipal v3/base_municipal_v3.csv", low_memory=False)
df["cod_ibge"] = df["cod_ibge"].astype(int)

# 2. Refresh tz_universal with the CURRENT canonical xlsx (Ativa only = 163)
tz = pd.read_excel(f"{base}/03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx", sheet_name="consolidado")
tz["Código IBGE"] = pd.to_numeric(tz["Código IBGE"], errors="coerce")
ativos_ibge = set(tz.loc[tz["Situação"] == "Ativa", "Código IBGE"].dropna().astype(int))
print(f"Municípios Ativa (universal hoje) no xlsx: {len(ativos_ibge)}")

df["tz_universal_old"] = df["tz_universal"]
df["tz_universal"] = df["cod_ibge"].isin(ativos_ibge).astype(int)
print("tz_universal (antigo, base_municipal_v3):", df["tz_universal_old"].sum())
print("tz_universal (atualizado, xlsx hoje):", df["tz_universal"].sum())

# 3. GE score
df["ge_score"] = df["cnpj_nucleo_escore_confianca_prelim"].fillna(0)

# 4. Load geometry
gdf = gpd.read_file(f"{base}/03 - Dados/_data/espacial/BR_Municipios_2022.shp")
gdf["CD_MUN"] = gdf["CD_MUN"].astype(int)
gdf = gdf.merge(df[["cod_ibge", "tz_universal", "ge_score", "pop_2022", "uf"]],
                 left_on="CD_MUN", right_on="cod_ibge", how="inner")
print("Municípios com geometria + atributos:", len(gdf))
gdf = gdf.dropna(subset=["pop_2022"])
gdf["log_pop"] = np.log(gdf["pop_2022"].clip(lower=1))

gdf.to_file("/tmp/spatial/gdf_merged.gpkg", driver="GPKG")
df.to_csv("/tmp/spatial/base_atualizada.csv", index=False)
print("OK - dados preparados")
