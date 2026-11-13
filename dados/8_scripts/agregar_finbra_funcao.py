#!/usr/bin/env python3
"""agregar_finbra_funcao.py — agrega a DESPESA POR FUNÇÃO do FINBRA (Siconfi
DCA Anexo I-E) por município × ano, com foco em:
  - Função 15 — Urbanismo (infraestrutura urbana, serviços urbanos, ZELADORIA)
  - Função 26 — Transporte
e integra ao Banco Municipal v3 (serie_finbra + colunas/taxas no wide).

PRÉ-REQUISITO (rodar na máquina do autor — a API é bloqueada no sandbox):
  python3 baixar_finbra_siconfi.py --anos 2019 2020 2021 2022 2023 \
      --tipos funcao --saida "03 - Dados/_data/FINBRA_nacional"
  -> gera finbra_funcao_YYYY.csv (mesmas colunas do I-D:
     exercicio,cod_ibge,uf,...,coluna,cod_conta,conta,valor)

USO:
  python3 agregar_finbra_funcao.py            # detecta os anos disponíveis
Saída:
  _data/Base Municipal v3/serie_funcao.csv    (munic×ano: desp por função-alvo)
  atualiza base_municipal_v3.csv com desp_urbanismo_2022, desp_transporte_2022,
  pct_* sobre despesa e as taxas CAGR 2019–2023.
"""
import pandas as pd, numpy as np, glob, re, os
HERE=os.path.dirname(os.path.abspath(__file__))
V=os.path.join(os.path.abspath(os.path.join(HERE,"..","..")),"03 - Dados","_data")
FN=os.path.join(V,"FINBRA_nacional"); OUT=os.path.join(V,"Base Municipal v3")
COLUNA="Despesas Empenhadas"          # medida usada nas séries do v3
# funções-alvo (código IBGE da função): número -> rótulo curto
ALVO={15:"urbanismo",26:"transporte",25:"energia",17:"saneamento",
      16:"habitacao",4:"administracao"}
def c7(x):
    try: return str(int(float(x))).zfill(7)
    except: return None
def cagr(a,b,n):
    a=pd.to_numeric(a,errors="coerce"); b=pd.to_numeric(b,errors="coerce")
    return np.round(np.where((a>0)&(b>0),(b/a)**(1/n)-1,np.nan)*100,2)
def num_funcao(row):
    """extrai o nº da função de cod_conta/conta (ex.: 'DF26...','26 - Transporte')."""
    for campo in (str(row.get("cod_conta","")),str(row.get("conta",""))):
        m=re.search(r'(\d{1,2})',campo)
        if m: return int(m.group(1))
    return None

arqs=sorted(glob.glob(f"{FN}/finbra_funcao_*.csv"))
if not arqs:
    raise SystemExit("Nenhum finbra_funcao_*.csv encontrado. Rode antes o coletor "
                     "'baixar_finbra_siconfi.py --tipos funcao'.")
recs=[]
for f in arqs:
    ano=int(re.search(r'funcao_(\d{4})',f).group(1))
    d=pd.read_csv(f,dtype=str)
    d=d[d["coluna"]==COLUNA].copy()
    d["cod_ibge"]=d["cod_ibge"].map(c7)
    d["func"]=d.apply(num_funcao,axis=1)
    d=d[d["func"].isin(ALVO)]
    d["valor"]=pd.to_numeric(d["valor"],errors="coerce")
    # soma subfunções dentro da função (nível função)
    g=d.groupby(["cod_ibge","func"],as_index=False)["valor"].sum()
    g["ano"]=ano; recs.append(g)
sf=pd.concat(recs,ignore_index=True)
sf["funcao_nome"]=sf["func"].map(ALVO)
wide_sf=sf.pivot_table(index=["cod_ibge","ano"],columns="funcao_nome",values="valor").reset_index()
wide_sf.columns=[f"desp_{c}" if c not in("cod_ibge","ano") else c for c in wide_sf.columns]
wide_sf.to_csv(f"{OUT}/serie_funcao.csv",index=False)
print("serie_funcao.csv ->",wide_sf.shape,"| anos:",sorted(sf.ano.unique()))

# ---- integra ao wide (snapshots 2022 + taxas 2019–2023) ----
base=pd.read_csv(f"{OUT}/base_municipal_v3.csv",dtype={"cod_ibge":str})
d22=wide_sf[wide_sf.ano==2022].set_index("cod_ibge")
desp_emp=pd.to_numeric(base.get("despesa_empenhada_2022"),errors="coerce").values
for nome in ["urbanismo","transporte"]:
    col=f"desp_{nome}"
    if col in wide_sf.columns:
        v=pd.to_numeric(d22[col].reindex(base["cod_ibge"]).values,errors="coerce")
        base[f"{col}_2022"]=v
        base[f"pct_{nome}_desp_2022"]=np.round(v/desp_emp*100,2)
        w=wide_sf.pivot_table(index="cod_ibge",columns="ano",values=col)
        if 2019 in w.columns and 2023 in w.columns:
            base[f"{nome}_cagr_2019_2023"]=cagr(
                w[2019].reindex(base["cod_ibge"]).values,
                w[2023].reindex(base["cod_ibge"]).values,4)
base.to_csv(f"{OUT}/base_municipal_v3.csv",index=False)
print("base_municipal_v3.csv atualizada com desp_urbanismo/transporte + pct + CAGR.")
print("  cobertura urbanismo 2022:",base.get("desp_urbanismo_2022").notna().sum() if "desp_urbanismo_2022" in base else 0)
