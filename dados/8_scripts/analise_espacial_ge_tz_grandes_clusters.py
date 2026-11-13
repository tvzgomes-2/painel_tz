import pandas as pd
import numpy as np
import statsmodels.api as sm
import warnings
warnings.filterwarnings("ignore")

base = "/sessions/kind-sleepy-feynman/mnt/doutorado"
df = pd.read_csv(f"{base}/03 - Dados/_data/Base Municipal v3/base_municipal_v3.csv", low_memory=False)
df["cod_ibge"] = df["cod_ibge"].astype(int)

tz = pd.read_excel(f"{base}/03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx", sheet_name="consolidado")
tz["Código IBGE"] = pd.to_numeric(tz["Código IBGE"], errors="coerce")
ativos_ibge = set(tz.loc[tz["Situação"] == "Ativa", "Código IBGE"].dropna().astype(int))
df["tz_universal"] = df["cod_ibge"].isin(ativos_ibge).astype(int)

espac = pd.read_csv(f"{base}/03 - Dados/_data/CNPJ/filtrados (6 CNAEs transporte, 24-07-2026)/espacializacao_grupos_por_municipio.csv")

GRANDES = ["Barata", "Lessa Carvalho", "1001", "Belarmino", "Corleto"]
PEQUENOS = ["Baltazar", "Pekin/Constantino", "Nova Suissa", "Andorinha", "Gammbus", "Ruas"]

muni_grande = set(espac[espac["grupo"].isin(GRANDES)]["cod_ibge"].unique())
muni_pequeno = set(espac[espac["grupo"].isin(PEQUENOS)]["cod_ibge"].unique())
# município pode ter os dois tipos presentes - checar overlap
overlap = muni_grande & muni_pequeno
print(f"Municípios com grande cluster: {len(muni_grande)}")
print(f"Municípios com cluster pequeno/regional: {len(muni_pequeno)}")
print(f"Overlap (tem os dois tipos): {len(overlap)}")

df["tem_grande"] = df["cod_ibge"].isin(muni_grande).astype(int)
df["tem_pequeno"] = df["cod_ibge"].isin(muni_pequeno).astype(int)
df["log_pop"] = np.log(df["pop_2022"].clip(lower=1))

print(f"\n=== Contingência bruta ===")
print(f"Nenhum grupo reconhecido: N={((df['tem_grande']==0)&(df['tem_pequeno']==0)).sum()}, taxa TZ={df[(df['tem_grande']==0)&(df['tem_pequeno']==0)]['tz_universal'].mean():.4f}")
print(f"Só cluster PEQUENO/regional: N={((df['tem_grande']==0)&(df['tem_pequeno']==1)).sum()}, taxa TZ={df[(df['tem_grande']==0)&(df['tem_pequeno']==1)]['tz_universal'].mean():.4f}")
print(f"Tem GRANDE cluster (nacional): N={(df['tem_grande']==1).sum()}, taxa TZ={df[df['tem_grande']==1]['tz_universal'].mean():.4f}")
print(f"Taxa TZ nacional geral: {df['tz_universal'].mean():.4f}")

print("\n=== Logit: TZ ~ tem_grande + log_pop (nacional, 5.570 municípios) ===")
X = sm.add_constant(df[["tem_grande","log_pop"]])
m = sm.Logit(df["tz_universal"], X).fit(disp=0)
print(m.summary2().tables[1])
print("Odds ratio tem_grande:", np.exp(m.params["tem_grande"]))

print("\n=== Logit: TZ ~ tem_grande + tem_pequeno + log_pop (nacional) ===")
X2 = sm.add_constant(df[["tem_grande","tem_pequeno","log_pop"]])
m2 = sm.Logit(df["tz_universal"], X2).fit(disp=0)
print(m2.summary2().tables[1])
print("Odds ratios:", np.exp(m2.params).to_dict())

# Recorte por porte, só tem_grande
for thresh in [30000, 50000, 100000]:
    sub = df[df["pop_2022"] >= thresh].copy()
    print(f"\n=== pop >= {thresh} (N={len(sub)}) — tem_grande ===")
    print(f"Taxa TZ com grande cluster: {sub[sub['tem_grande']==1]['tz_universal'].mean():.4f} (N={sub['tem_grande'].sum()}) | sem: {sub[sub['tem_grande']==0]['tz_universal'].mean():.4f}")
    try:
        Xs = sm.add_constant(sub[["tem_grande","log_pop"]])
        ms = sm.Logit(sub["tz_universal"], Xs).fit(disp=0)
        print(ms.summary2().tables[1])
    except Exception as e:
        print("falhou:", e)
