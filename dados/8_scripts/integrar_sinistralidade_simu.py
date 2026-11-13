#!/usr/bin/env python3
"""integrar_sinistralidade_simu.py — integra a sinistralidade viária do SIMU
(Ministério das Cidades) ao Banco Municipal v3, SEM pysus/compilador.

PASSO MANUAL: baixe o indicador municipal "Acidentes de Transportes" (mortos por
100 mil hab) do SIMU e salve o CSV/XLSX em  _data/sinistralidade/
  https://simu.cidades.gov.br/monitoramento-indicador-acidentes-de-transportes-municipal/

USO:  python3 integrar_sinistralidade_simu.py
O script é TOLERANTE ao layout: detecta a coluna de código IBGE (ou nome+UF),
e as colunas de valor (contagem de óbitos e/ou taxa por 100k), em formato largo
(anos em colunas) ou longo (coluna 'ano'). Imprime o que detectou para conferência.
Saídas: _data/Base Municipal v3/serie_sinistralidade.csv + colunas no wide."""
import os, re, glob, unicodedata, pandas as pd, numpy as np
HERE=os.path.dirname(os.path.abspath(__file__))
V=os.path.join(os.path.abspath(os.path.join(HERE,"..","..")),"03 - Dados","_data")
SRC=os.path.join(V,"sinistralidade"); OUT=os.path.join(V,"Base Municipal v3")
def c7(x):
    try: return str(int(float(x))).zfill(7)
    except: return None
def norm(s):
    s=unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode()
    return re.sub(r'[^A-Z0-9]','',s.upper())

arqs=glob.glob(f"{SRC}/*.csv")+glob.glob(f"{SRC}/*.xlsx")+glob.glob(f"{SRC}/*.xls")
if not arqs:
    raise SystemExit(f"Coloque o arquivo do SIMU em: {SRC}")
f=arqs[0]; print("lendo",f)
if f.lower().endswith(".csv"):
    # tenta separadores comuns do SIMU
    for sep in [";",",","\t"]:
        d=pd.read_csv(f,sep=sep,dtype=str,encoding="utf-8-sig")
        if d.shape[1]>1: break
else:
    d=pd.read_excel(f,dtype=str)
d.columns=[str(c).strip() for c in d.columns]
print("colunas:",list(d.columns))

# coluna de código IBGE
col_cod=next((c for c in d.columns if re.search(r'c[oó]d.*(ibge|mun)|geoc|ibge',c,re.I)),None)
if col_cod:
    d["cod_ibge"]=d[col_cod].map(c7)
else:  # via nome+UF, ponte pela própria base v3
    ncol=next((c for c in d.columns if re.search(r'munic|nome',c,re.I)),None)
    ucol=next((c for c in d.columns if re.fullmatch(r'uf|sigla_?uf',c,re.I)),None)
    bv=pd.read_csv(f"{OUT}/base_municipal_v3.csv",dtype={"cod_ibge":str},low_memory=False)
    bv["chave"]=bv["uf"].astype(str).str[:2].str.upper()+"|"+bv["nome_mun"].map(norm)
    br=bv[["chave","cod_ibge"]].drop_duplicates("chave")
    d["chave"]=d[ucol].astype(str).str[:2].str.upper()+"|"+d[ncol].map(norm)
    d=d.merge(br,on="chave",how="left")
    print(f"ponte por nome ({ncol}+{ucol}) — casados: {d.cod_ibge.notna().sum()}/{len(d)}")

# colunas de valor: anos (largo) e/ou taxa/óbitos
anos=[c for c in d.columns if re.fullmatch(r'(19|20)\d{2}',str(c))]
def tonum(s): return pd.to_numeric(d[s].astype(str).str.replace(".","",regex=False).str.replace(",",".",regex=False),errors="coerce")
serie=None
if anos:  # formato largo: uma coluna por ano
    long=[]
    for a in anos:
        t=d[["cod_ibge"]].copy(); t["ano"]=int(a); t["sinistralidade"]=tonum(a); long.append(t)
    serie=pd.concat(long,ignore_index=True).dropna(subset=["cod_ibge"])
else:      # formato longo: coluna 'ano' + coluna de valor
    ca=next((c for c in d.columns if re.search(r'\bano\b',c,re.I)),None)
    cv=next((c for c in d.columns if re.search(r'taxa|100.?mil|obito|óbito|mort',c,re.I)),None)
    if ca and cv:
        d["ano"]=pd.to_numeric(d[ca],errors="coerce"); d["sinistralidade"]=tonum(cv)
        serie=d[["cod_ibge","ano","sinistralidade"]].dropna(subset=["cod_ibge"])
if serie is None or serie.empty:
    raise SystemExit("Não identifiquei colunas de ano/valor — me mande os nomes das colunas.")
serie.to_csv(f"{OUT}/serie_sinistralidade.csv",index=False)
print("serie_sinistralidade.csv:",serie.shape,"| anos:",sorted(serie.ano.dropna().unique()))

# integra o último ano ao wide
base=pd.read_csv(f"{OUT}/base_municipal_v3.csv",dtype={"cod_ibge":str},low_memory=False)
base["cod_ibge"]=base["cod_ibge"].map(c7)
ult=int(serie.ano.dropna().max())
w=serie[serie.ano==ult].set_index("cod_ibge")["sinistralidade"]
col=f"sinistralidade_transito_{ult}"
base=base.drop(columns=[c for c in [col] if c in base.columns])
base[col]=pd.to_numeric(w.reindex(base.cod_ibge).values,errors="coerce")
base.to_csv(f"{OUT}/base_municipal_v3.csv",index=False)
print("wide atualizado:",base.shape,"|",col,"preench.:",base[col].notna().sum())
