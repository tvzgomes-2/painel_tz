import os, re, unicodedata
import pandas as pd

V = "/sessions/kind-sleepy-feynman/mnt/doutorado/03 - Dados/_data"
OUT = os.path.join(V, "Base Municipal v3")
BASE_CSV = os.path.join(OUT, "base_municipal_v3.csv")
POLO_RAIS_CSV = os.path.join(V, "POLO", "_extraido", "rais_2022.csv")

CORRECOES_NOME = {
    "BA|CAMACA": "2905602", "SE|GRACCHOCARDOSO": "2802601", "MG|BRAZOPOLIS": "3108909",
    "RN|ASSU": "2400208", "RN|SERRACAIADA": "2410306", "PB|SAOVICENTEDOSERIDO": "2515401",
    "TO|TABOCAO": "1708254", "PE|IGUARACY": "2606903", "CE|ITAPAJE": "2306306",
    "SP|MOGIMIRIM": "3530805", "RO|ALVORADADOOESTE": "1100346", "MT|POXOREU": "5107008",
    "SP|FLORINEA": "3516101", "RN|CAMPOGRANDE": "2401305", "SP|EMBUDASARTES": "3515004",
    "PB|JOCACLAUDINO": "2513653", "RN|BOASAUDE": "2405306", "BA|SANTATEREZINHA": "2928505",
    "BA|MUQUEMDOSAOFRANCISCO": "2922250", "RO|ESPIGAODOOESTE": "1100098", "RN|AREZ": "2401206",
}
CORRECOES_NOME_POLO = {
    "PA|ELDORADODOCARAJAS": "1502954", "PA|SANTAIZABELDOPARA": "1506500",
    "PE|BELEMDESAOFRANCISCO": "2601607", "PE|LAGOADOITAENGA": "2608503",
}

def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", s.upper())

def c7(x):
    try: return str(int(float(x))).zfill(7)
    except Exception: return None

def salvar_atomico(df, path):
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)

base = pd.read_csv(BASE_CSV, dtype={"cod_ibge": str}, low_memory=False)
base["cod_ibge"] = base["cod_ibge"].map(c7)
base_nomes = base[["cod_ibge", "nome_mun", "uf"]].copy()

rais = pd.read_csv(POLO_RAIS_CSV)
antes = len(rais)
rais = rais[rais["uf"].notna()].copy()
print(f"rais_2022.csv: {antes} -> {len(rais)} após descartar footer")

rais["chave"] = rais["uf"].str.upper().str.strip() + "|" + rais["municipio"].map(norm)
bridge = base_nomes.assign(chave=base_nomes.uf.str.upper().str.strip() + "|" + base_nomes.nome_mun.map(norm))
d = rais.merge(bridge[["chave", "cod_ibge"]], on="chave", how="left")

sem_match = d[d.cod_ibge.isna()]
for _, row in sem_match.iterrows():
    cod = CORRECOES_NOME.get(row["chave"]) or CORRECOES_NOME_POLO.get(row["chave"])
    if cod:
        d.loc[d["chave"] == row["chave"], "cod_ibge"] = cod
ainda_sem = d[d.cod_ibge.isna()]
print(f"ainda sem cod_ibge: {len(ainda_sem)}")
d = d.dropna(subset=["cod_ibge"]).copy()
d["cod_ibge"] = d["cod_ibge"].map(c7)
d["vinculos_formais_rais_2022"] = pd.to_numeric(d["total"], errors="coerce")

print(f"municípios com vínculos formais: {d.cod_ibge.nunique()} / 5570")
print(f"soma nacional: {d.vinculos_formais_rais_2022.sum():,.0f}")

resumo = d[["cod_ibge", "vinculos_formais_rais_2022"]].drop_duplicates(subset="cod_ibge")

# cross-check contra base_tributavel_ctpu (deveria ser igual, já que CTPU = soma de todas as faixas = total)
check = base[["cod_ibge", "base_tributavel_ctpu"]].merge(resumo, on="cod_ibge", how="inner")
check["dif"] = check["vinculos_formais_rais_2022"] - check["base_tributavel_ctpu"]
n_dif = (check["dif"].abs() > 0.5).sum()
print(f"cross-check vs base_tributavel_ctpu: {n_dif} municípios com diferença (de {len(check)} comparáveis)")
if n_dif:
    print(check[check["dif"].abs() > 0.5].head(10).to_string(index=False))

base = base.drop(columns=[c for c in resumo.columns if c != "cod_ibge" and c in base.columns])
base = base.merge(resumo, on="cod_ibge", how="left")
salvar_atomico(base, BASE_CSV)
print(f"\nOK - base_municipal_v3.csv: {base.shape[0]} x {base.shape[1]}")
