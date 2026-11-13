"""
Gera a Figura 1 da nota "Análise - Cruzamento espacial GE x Tarifa Zero.md"
(diagrama de Moran bivariado, GE score x defasagem espacial de TZ).
Segue a paleta de [[Identidade Visual da Pesquisa]]. Salva SVG em `_attachments/`.

Rodar a partir da raiz do cofre: python3 _meta/scripts/analise_espacial_ge_tz_moran_scatter.py

Dependências instaladas em 21/08/2026: libpysal, esda, geopandas.
"""
import pandas as pd
import numpy as np
import geopandas as gpd
from libpysal.weights import KNN
import esda
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

BASE = "."
ATT = f"{BASE}/_attachments"
PRETO = "#0E0E10"
ROSA = "#FF2D6B"
AZUL = "#1A54C7"
PAPEL = "#FAF9F5"

plt.rcParams["font.family"] = "Poppins"
plt.rcParams["figure.facecolor"] = PAPEL
plt.rcParams["axes.facecolor"] = PAPEL
plt.rcParams["savefig.facecolor"] = PAPEL
plt.rcParams["text.color"] = PRETO
plt.rcParams["axes.edgecolor"] = PRETO
plt.rcParams["axes.labelcolor"] = PRETO
plt.rcParams["xtick.color"] = PRETO
plt.rcParams["ytick.color"] = PRETO
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

df = pd.read_csv(f"{BASE}/03 - Dados/_data/Base Municipal v3/base_municipal_v3.csv", low_memory=False)
df["cod_ibge"] = df["cod_ibge"].astype(int)
tz = pd.read_excel(f"{BASE}/03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx", sheet_name="consolidado")
tz["Código IBGE"] = pd.to_numeric(tz["Código IBGE"], errors="coerce")
ativos_ibge = set(tz.loc[tz["Situação"] == "Ativa", "Código IBGE"].dropna().astype(int))
df["tz_universal"] = df["cod_ibge"].isin(ativos_ibge).astype(int)
df["ge_score"] = df["cnpj_nucleo_escore_confianca_prelim"].fillna(0)

gdf = gpd.read_file(f"{BASE}/03 - Dados/_data/espacial/BR_Municipios_2022.shp")
gdf["CD_MUN"] = gdf["CD_MUN"].astype(int)
gdf = gdf.merge(df[["cod_ibge", "tz_universal", "ge_score"]], left_on="CD_MUN", right_on="cod_ibge", how="inner")

gdf_c = gdf.copy()
gdf_c["geometry"] = gdf_c.geometry.centroid
gdf_c = gdf_c.set_geometry("geometry").to_crs(epsg=5880)  # SIRGAS2000/Polyconic — evita custo de topologia dos polígonos
w = KNN.from_dataframe(gdf_c, k=8)
w.transform = "r"

ge = gdf["ge_score"].values
tz_vals = gdf["tz_universal"].values
ge_z = (ge - ge.mean()) / ge.std()
tz_lag = esda.moran.lag_spatial(w, tz_vals)
tz_lag_z = (tz_lag - tz_lag.mean()) / tz_lag.std()
mbv = esda.Moran_BV(ge, tz_vals, w, permutations=999)

fig, ax = plt.subplots(figsize=(6.5, 6))
ax.scatter(ge_z, tz_lag_z, s=10, color=AZUL, alpha=0.35, edgecolors="none")
coef = np.polyfit(ge_z, tz_lag_z, 1)
xs = np.linspace(ge_z.min(), ge_z.max(), 50)
ax.plot(xs, coef[0] * xs + coef[1], color=ROSA, linewidth=2.5)
ax.axhline(0, color=PRETO, linewidth=0.8, alpha=0.4)
ax.axvline(0, color=PRETO, linewidth=0.8, alpha=0.4)
ax.set_xlabel("Escore de GE do município (padronizado)")
ax.set_ylabel("Tarifa Zero dos municípios vizinhos (defasagem espacial, padronizada)")
ax.set_title(f"Diagrama de Moran bivariado — I={mbv.I:.3f}, p={mbv.p_sim:.3f}\nInclinação positiva: alto GE tende a vizinhar TZ, não o contrário",
             fontsize=10, fontweight="bold", loc="left")
fig.tight_layout()
fig.savefig(f"{ATT}/Fig - Diagrama de Moran bivariado GE x TZ (ago-2026).svg", format="svg")
plt.close(fig)
print(f"Figura 1 regenerada. Moran BV I={mbv.I:.4f}, p={mbv.p_sim:.4f}")
