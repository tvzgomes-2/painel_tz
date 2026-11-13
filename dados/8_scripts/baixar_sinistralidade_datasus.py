#!/usr/bin/env python3
"""baixar_sinistralidade_datasus.py — óbitos por ACIDENTE DE TRANSPORTE por
município (SIM/DATASUS, causa básica CID-10 V01–V89), série anual + taxa por
100 mil hab. Rode na SUA máquina. Pesado (baixa DO por UF/ano do FTP DATASUS).

Requer: pip install pysus pandas
Fonte SIM: https://rfsaldanha.github.io/sis/sim.html  (via pysus.online_data.SIM)
Alternativa pronta (viewer): SIMU/Min. Cidades — "Acidentes de Transportes"
  https://simu.cidades.gov.br/monitoramento-indicador-acidentes-de-transportes-municipal/
  (mortos/100 mil hab por município; use se preferir não processar o SIM bruto).

USO:  python3 baixar_sinistralidade_datasus.py --anos 2018 2019 2020 2021 2022
Saídas: _data/DATASUS/obitos_transito_bruto_*.parquet (cache) +
        _data/Base Municipal v3/serie_sinistralidade.csv (cod_ibge, ano,
        obitos_transito) e colunas no wide (obitos_transito_2022, taxa_100k)."""
import argparse, os, re, pandas as pd, numpy as np
HERE=os.path.dirname(os.path.abspath(__file__))
V=os.path.join(os.path.abspath(os.path.join(HERE,"..","..")),"03 - Dados","_data")
DS=os.path.join(V,"DATASUS"); OUT=os.path.join(V,"Base Municipal v3")
UFS=["RO","AC","AM","RR","PA","AP","TO","MA","PI","CE","RN","PB","PE","AL","SE","BA",
     "MG","ES","RJ","SP","PR","SC","RS","MS","MT","GO","DF"]
def c7(x):
    try: return str(int(float(x))).zfill(7)
    except: return None
def e_transporte(cid):
    s=str(cid).upper()
    m=re.match(r'V(\d{2})',s)
    return bool(m) and 1<=int(m.group(1))<=89   # V01–V89

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--anos",nargs="+",type=int,required=True); a=ap.parse_args()
    os.makedirs(DS,exist_ok=True)
    from pysus.online_data.SIM import download
    recs=[]
    for ano in a.anos:
        cache=f"{DS}/obitos_transito_bruto_{ano}.parquet"
        if os.path.exists(cache):
            df=pd.read_parquet(cache)
        else:
            partes=[]
            for uf in UFS:
                try:
                    d=download(uf,ano)              # DO daquele UF/ano
                    d=d[["CODMUNRES","CAUSABAS"]].copy()
                    d=d[d["CAUSABAS"].map(e_transporte)]
                    partes.append(d)
                    print(f"  {uf}/{ano}: {len(d)} óbitos de transporte")
                except Exception as e:
                    print(f"  ! {uf}/{ano}: {e}")
            df=pd.concat(partes,ignore_index=True) if partes else pd.DataFrame(columns=["CODMUNRES","CAUSABAS"])
            df.to_parquet(cache)
        g=df.groupby("CODMUNRES").size().reset_index(name="obitos_transito")
        g["cod_ibge"]=g["CODMUNRES"].map(c7); g["ano"]=ano
        recs.append(g[["cod_ibge","ano","obitos_transito"]])
    serie=pd.concat(recs,ignore_index=True).dropna(subset=["cod_ibge"])
    serie.to_csv(f"{OUT}/serie_sinistralidade.csv",index=False)
    print("serie_sinistralidade.csv:",serie.shape,"| anos:",sorted(serie.ano.unique()))

    # integra ao wide (último ano + taxa/100k com pop_2022)
    base=pd.read_csv(f"{OUT}/base_municipal_v3.csv",dtype={"cod_ibge":str},low_memory=False)
    base["cod_ibge"]=base["cod_ibge"].map(c7)
    ult=serie.ano.max()
    w=serie[serie.ano==ult].set_index("cod_ibge")["obitos_transito"]
    base[f"obitos_transito_{ult}"]=pd.to_numeric(w.reindex(base.cod_ibge).values,errors="coerce")
    pop=pd.to_numeric(base.get("pop_2022"),errors="coerce")
    base[f"taxa_obitos_transito_100k_{ult}"]=(base[f"obitos_transito_{ult}"]/pop*1e5).round(2)
    base.to_csv(f"{OUT}/base_municipal_v3.csv",index=False)
    print("wide atualizado:",base.shape)

if __name__=="__main__": main()
