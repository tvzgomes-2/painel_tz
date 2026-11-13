#!/usr/bin/env python3
"""Base Espacial Integrada — corte 2022. Join por código IBGE (7 díg) de:
FINBRA (2022), PIB (2020), DENATRAN frota (dez/2022, via ponte nome→código do PIB)
e status Tarifa Zero (base-mestre 155). Saída: base_municipal_integrada_2022.csv."""
import pandas as pd, unicodedata, re

def norm(s):
    s=unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode()
    return re.sub(r'[^A-Z0-9]','',s.upper())
def cod7(x):
    try: return str(int(float(x))).zfill(7)
    except: return None

# --- FINBRA 2022 ---
fb=pd.read_csv("/tmp/finbra_municipal.csv",dtype={"cod_ibge":str})
fb=fb[fb.exercicio==2022].copy(); fb["cod_ibge"]=fb.cod_ibge.map(cod7)
fb=fb[["cod_ibge","uf","populacao","receita_liquida","receita_corrente","despesa_empenhada"]]

# --- PIB 2020 (+ ponte nome→código) ---
pib=pd.read_csv("/tmp/polo_ext/pib_2020.csv",dtype={"cod":str})
pib["cod_ibge"]=pib["cod"].map(cod7)
m=pib["municipio"].str.extract(r'^(.*)\((\w{2})\)\s*$')
pib["nome"]=m[0].str.strip(); pib["uf_pib"]=m[1]
pib["chave"]=pib["uf_pib"]+"|"+pib["nome"].map(norm)
pib=pib.rename(columns={"ano_2020":"pib_2020"})
bridge=pib[["chave","cod_ibge"]].dropna().drop_duplicates("chave")
PIB=pib[["cod_ibge","pib_2020"]]

# --- DENATRAN dez/2022 (junta via ponte) ---
dn=pd.read_csv("/tmp/polo_ext/frota_munic_dez2022.csv")
dn["chave"]=dn["uf"]+"|"+dn["municipio"].map(norm)
dn=dn.merge(bridge,on="chave",how="left")
match=dn.cod_ibge.notna().mean()
dn=dn.dropna(subset=["cod_ibge"])[["cod_ibge","total","automovel","motocicleta","onibus"]]
dn=dn.rename(columns={"total":"frota_total","automovel":"frota_automovel",
                      "motocicleta":"frota_motocicleta","onibus":"frota_onibus"})
dn=dn.groupby("cod_ibge",as_index=False).sum()

# --- TZ (base-mestre 155) ---
tz=pd.read_excel("/sessions/kind-sleepy-feynman/mnt/doutorado/03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx")
tz["cod_ibge"]=tz["Código IBGE"].map(cod7)
tz=tz[["cod_ibge","Situação","Ano início"]].rename(columns={"Situação":"tz_situacao","Ano início":"tz_ano_inicio"})
tz["tz_universal"]=1

# --- JOIN por cod_ibge ---
b=fb.merge(PIB,on="cod_ibge",how="left").merge(dn,on="cod_ibge",how="left").merge(tz,on="cod_ibge",how="left")
b["tz_universal"]=b["tz_universal"].fillna(0).astype(int)
# derivadas
b["pib_pc"]=(b["pib_2020"]*1000/b["populacao"]).round(2)          # PIB em R$ mil -> per capita R$
b["motorizacao"]=(b["frota_total"]/b["populacao"]).round(4)        # frota por habitante
b["receita_pc"]=(b["receita_liquida"]/b["populacao"]).round(2)
b=b.sort_values("cod_ibge")
b.to_csv("/tmp/base_municipal_integrada_2022.csv",index=False)

print(f"municípios na base: {len(b)}")
print(f"  com FINBRA: {b.receita_liquida.notna().sum()} | com PIB: {b.pib_2020.notna().sum()} | com DENATRAN: {b.frota_total.notna().sum()} (match nome→cod: {match:.1%})")
print(f"  TZ universal (155 esperados): {b.tz_universal.sum()}")
print("\nSP 2022:"); print(b[b.cod_ibge=='3550308'][['cod_ibge','populacao','receita_liquida','pib_2020','pib_pc','frota_total','motorizacao','tz_universal']].to_string(index=False))
print("\nSCS (tem TZ):"); print(b[b.cod_ibge=='3548807'][['cod_ibge','receita_pc','pib_pc','motorizacao','tz_universal','tz_situacao']].to_string(index=False))
