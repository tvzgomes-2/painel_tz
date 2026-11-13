#!/usr/bin/env python3
"""Agrega o FINBRA (Siconfi DCA) por município×ano a partir dos CSVs filtrados
(linhas de total). Saída: painel finbra_municipal.csv."""
import pandas as pd, glob, os

SRC="/tmp/finbra"; OUT="/tmp/finbra_municipal.csv"
def rd(p):
    return pd.read_csv(p, usecols=["exercicio","cod_ibge","uf","populacao","coluna","cod_conta","valor"],
                       dtype={"cod_ibge":str}, low_memory=False)

# ---- Receitas ----
rec=pd.concat([rd(f) for f in sorted(glob.glob(f"{SRC}/rec_*.f.csv"))], ignore_index=True)
tr=rec[rec.cod_conta=="TotalReceitas"]
bruta=tr[tr.coluna=="Receitas Brutas Realizadas"].groupby(["cod_ibge","exercicio"]).agg(
    receita_bruta=("valor","sum"), uf=("uf","first"), populacao=("populacao","first")).reset_index()
ded=tr[tr.coluna!="Receitas Brutas Realizadas"].groupby(["cod_ibge","exercicio"])["valor"].sum().rename("deducoes").reset_index()
corr=rec[(rec.cod_conta=="RO1.0.0.0.00.0.0") & (rec.coluna=="Receitas Brutas Realizadas")].groupby(
    ["cod_ibge","exercicio"])["valor"].sum().rename("receita_corrente").reset_index()
R=bruta.merge(ded,on=["cod_ibge","exercicio"],how="left").merge(corr,on=["cod_ibge","exercicio"],how="left")
R["deducoes"]=R["deducoes"].fillna(0)
R["receita_liquida"]=R["receita_bruta"]-R["deducoes"]

# ---- Despesas ----
desp=pd.concat([rd(f) for f in sorted(glob.glob(f"{SRC}/desp_*.f.csv"))], ignore_index=True)
td=desp[desp.cod_conta=="TotalDespesas"]
def col(nome,alias):
    return td[td.coluna==nome].groupby(["cod_ibge","exercicio"])["valor"].sum().rename(alias).reset_index()
D=col("Despesas Empenhadas","despesa_empenhada").merge(
   col("Despesas Liquidadas","despesa_liquidada"),on=["cod_ibge","exercicio"],how="outer").merge(
   col("Despesas Pagas","despesa_paga"),on=["cod_ibge","exercicio"],how="outer")

# ---- Painel ----
base=R.merge(D,on=["cod_ibge","exercicio"],how="outer")
base=base[["cod_ibge","uf","exercicio","populacao","receita_bruta","deducoes","receita_liquida",
           "receita_corrente","despesa_empenhada","despesa_liquidada","despesa_paga"]]
base=base.sort_values(["cod_ibge","exercicio"])
base.to_csv(OUT,index=False)
print(f"OK: {base.cod_ibge.nunique()} municípios, {len(base)} linhas (munic×ano), anos {sorted(base.exercicio.unique())}")
print("amostra SP 2022:")
print(base[(base.cod_ibge=='3550308')&(base.exercicio==2022)].to_string(index=False))
