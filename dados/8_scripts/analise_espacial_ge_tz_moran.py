import geopandas as gpd
import numpy as np
from libpysal.weights import KNN
import esda
import warnings
warnings.filterwarnings("ignore")

gdf = gpd.read_file("gdf_merged.gpkg")
print(len(gdf), "municípios")

# Usar centroides em projeção métrica (evita o custo de topologia de polígonos de alta resolução)
gdf_proj = gdf.copy()
gdf_proj["geometry"] = gdf_proj.geometry.centroid
gdf_proj = gdf_proj.set_geometry("geometry").to_crs(epsg=5880)  # SIRGAS 2000 / Brazil Polyconic

w = KNN.from_dataframe(gdf_proj, k=8)
w.transform = "r"
print("Pesos KNN(k=8) construídos.")

mi_tz = esda.Moran(gdf["tz_universal"].values, w, permutations=999)
print(f"\nMoran's I (TZ universal): I={mi_tz.I:.4f}, p={mi_tz.p_sim:.4f}, z={mi_tz.z_sim:.2f}")

mi_ge = esda.Moran(gdf["ge_score"].values, w, permutations=999)
print(f"Moran's I (GE score): I={mi_ge.I:.4f}, p={mi_ge.p_sim:.4f}, z={mi_ge.z_sim:.2f}")

mbv = esda.Moran_BV(gdf["ge_score"].values, gdf["tz_universal"].values, w, permutations=999)
print(f"\nMoran BV (GE_i vs lag(TZ)_j): I={mbv.I:.4f}, p={mbv.p_sim:.4f}")
mbv2 = esda.Moran_BV(gdf["tz_universal"].values, gdf["ge_score"].values, w, permutations=999)
print(f"Moran BV (TZ_i vs lag(GE)_j): I={mbv2.I:.4f}, p={mbv2.p_sim:.4f}")

corr = np.corrcoef(gdf["ge_score"], gdf["tz_universal"])[0,1]
print(f"\nCorrelação simples (Pearson) GE score x TZ: {corr:.4f}")

import pickle
with open("weights_knn.pkl","wb") as f:
    pickle.dump(w, f)
gdf.to_file("gdf_final.gpkg", driver="GPKG")
print("done")
