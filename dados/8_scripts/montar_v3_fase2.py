#!/usr/bin/env python3
"""Banco Municipal v3 — FASE 2: extrair do ACERVO (sem coleta externa):
  A) PEMOB/SIMOB-ANTP  -> série de tarifa (2016–2024), taxa de gratuidade
     (2018–2024), pax e frota de ônibus (abas anuais 2018–2024 de PEMOB.xlsx).
  B) MUNIC 2020 "Transporte" -> institucional dos 5.570 municípios
     (plano/conselho/fundo de transporte, regulamentação, isenção total, etc.).
Chave: código IBGE (7 díg). Saídas em _data/Base Municipal v3/ e colunas no wide.

Obs.: a tarifa PEMOB (2016–2024, por código IBGE, ~limitada à amostra ANTP) é a
série limpa; o PDF SIMOB (copia-de-tarifas_2005-a-atual) guarda o histórico
2005–2015 dessas cidades (formato irregular — deepening manual, não automatizado)."""
import pandas as pd, numpy as np, openpyxl, re, os
V="/sessions/kind-sleepy-feynman/mnt/doutorado/03 - Dados/_data"
OUT=f"{V}/Base Municipal v3"
def c7(x):
    try: return str(int(float(x))).zfill(7)
    except: return None
def cagr(a,b,n):
    a=pd.to_numeric(a,errors="coerce"); b=pd.to_numeric(b,errors="coerce")
    return np.round(np.where((a>0)&(b>0),(b/a)**(1/n)-1,np.nan)*100,2)
def simno(x):
    s=str(x).strip().lower()
    return 1 if s=="sim" else (0 if s in("não","nao") else np.nan)

# ================= A) PEMOB =================
# A1) tarifa (CSV pronto, 2016–2024) e gratuidade (2018–2024), por código IBGE
def le_quadro(nome,anos):
    d=pd.read_csv(f"{V}/PEMOB/{nome}",sep=";",dtype=str,encoding="utf-8-sig")
    d["cod_ibge"]=d["CÓDIGO IBGE"].map(c7)
    long=[]
    for a in anos:
        col=str(a)
        if col in d.columns:
            t=d[["cod_ibge",col]].copy(); t["ano"]=a
            t["valor"]=(t[col].astype(str).str.replace("R$","",regex=False)
                        .str.replace(".","",regex=False).str.replace(",",".",regex=False)
                        .str.strip().replace({"":None,"nan":None}))
            long.append(t[["cod_ibge","ano","valor"]])
    return pd.concat(long,ignore_index=True).dropna(subset=["cod_ibge"])
tar=le_quadro("PEMOB - quadro de tarifas.csv",range(2016,2025)).rename(columns={"valor":"tarifa"})
gra=le_quadro("PEMOB - quadro de gratuidades.csv",range(2018,2025)).rename(columns={"valor":"tx_gratuidade"})
tar.to_csv(f"{OUT}/serie_tarifa.csv",index=False)

# A2) pax e frota das abas anuais de PEMOB.xlsx (códigos de pergunta como colunas)
CODES={"3.4.1.A":"pax_comuns","3.4.1.F":"pax_equivalentes","3.4.1.E":"gratuidades_n",
       "1.5.1.A":"frota_onibus_conv","3.1.1.A":"tarifa_pemob"}
wb=openpyxl.load_workbook(f"{V}/PEMOB/PEMOB.xlsx",read_only=True)
pemob_rows=[]
for y in range(2018,2025):
    sh=str(y)
    if sh not in wb.sheetnames: continue
    ws=wb[sh]; it=ws.iter_rows(values_only=True); hdr=list(next(it))
    idx={str(h).strip():i for i,h in enumerate(hdr)}
    ci=idx.get("CÓDIGO IBGE",idx.get("CODIGO IBGE",0))
    for row in it:
        cod=c7(row[ci])
        if not cod: continue
        rec={"cod_ibge":cod,"ano":y}
        for code,name in CODES.items():
            if code in idx: rec[name]=row[idx[code]]
        pemob_rows.append(rec)
pemob=pd.DataFrame(pemob_rows)
for c in ["pax_comuns","pax_equivalentes","gratuidades_n","frota_onibus_conv","tarifa_pemob"]:
    if c in pemob: pemob[c]=pd.to_numeric(pemob[c],errors="coerce")
pemob=pemob.merge(gra,on=["cod_ibge","ano"],how="outer").merge(tar,on=["cod_ibge","ano"],how="outer")
pemob.to_csv(f"{OUT}/serie_pemob.csv",index=False)
print("A) PEMOB -> serie_tarifa:",tar.cod_ibge.nunique(),"munic |",
      "serie_pemob:",pemob.shape,"| anos:",sorted(pemob.ano.dropna().unique()))

# ================= B) MUNIC 2020 Transporte =================
wm=openpyxl.load_workbook(f"{V}/MUNIC/Base_MUNIC_2020.xlsx",read_only=True)
wt=wm["Transporte"]; it=wt.iter_rows(values_only=True); h=list(next(it))
mi={str(c).strip():i for i,c in enumerate(h)}
# código -> nome de saída (Mtra no arquivo == MTRA no dicionário)
MAP={"Mtra01":("munic_orgao_gestor_2020","txt"),
     "Mtra07":("munic_plano_transp_2020","simno"),
     "Mtra09":("munic_conferencia_2020","simno"),
     "Mtra10":("munic_conselho_2020","simno"),
     "Mtra16":("munic_fundo_2020","simno"),
     "Mtra17":("munic_fundo_ativo_2020","simno"),
     "Mtra19":("munic_onibus_intramun_2020","simno"),
     "Mtra1911":("munic_concessao_2020","simno"),
     "Mtra1912":("munic_permissao_2020","simno"),
     "Mtra1913":("munic_autorizacao_2020","simno"),
     "Mtra1914":("munic_prestacao_direta_2020","simno"),
     "Mtra1915":("munic_nao_regulamentado_2020","simno"),
     "Mtra2010":("munic_isencao_total_2020","simno"),
     "Mtra21":("munic_frota_adaptada_2020","txt"),
     "Mtra24":("munic_ciclovia_2020","simno"),
     "Mtra25":("munic_bicicletario_2020","simno")}
recs=[]
for row in it:
    cod=c7(row[mi["CodMun"]])
    if not cod: continue
    r={"cod_ibge":cod}
    for src,(dst,typ) in MAP.items():
        if src in mi:
            v=row[mi[src]]
            r[dst]=simno(v) if typ=="simno" else (None if str(v).strip() in("-","Não informou","Recusa") else v)
    recs.append(r)
munic=pd.DataFrame(recs)
munic.to_csv(f"{OUT}/munic_transporte_2020.csv",index=False)
print("B) MUNIC 2020 ->",munic.shape,"| plano transp Sim:",int(munic.munic_plano_transp_2020.sum()),
      "| fundo Sim:",int(munic.munic_fundo_2020.sum()),"| isenção total Sim:",int(munic.munic_isencao_total_2020.sum()))

# ================= integra ao WIDE =================
base=pd.read_csv(f"{OUT}/base_municipal_v3.csv",dtype={"cod_ibge":str})
base["cod_ibge"]=base["cod_ibge"].map(c7)
# PEMOB snapshots + taxa tarifa
tw=tar.assign(tarifa=lambda x:pd.to_numeric(x.tarifa,errors="coerce")).pivot_table(index="cod_ibge",columns="ano",values="tarifa")
base["tarifa_2024"]=tw[2024].reindex(base.cod_ibge).values if 2024 in tw else np.nan
if 2018 in tw and 2024 in tw:
    base["tarifa_cagr_2018_2024"]=cagr(tw[2018].reindex(base.cod_ibge).values,tw[2024].reindex(base.cod_ibge).values,6)
gw=gra.assign(v=lambda x:pd.to_numeric(x.tx_gratuidade,errors="coerce")).pivot_table(index="cod_ibge",columns="ano",values="v")
base["tx_gratuidade_2024"]=gw[2024].reindex(base.cod_ibge).values if 2024 in gw else np.nan
p24=pemob[pemob.ano==2024].set_index("cod_ibge")
for c in ["pax_comuns","frota_onibus_conv"]:
    if c in pemob: base[f"{c}_2024"]=pd.to_numeric(p24[c].reindex(base.cod_ibge).values,errors="coerce")
base["na_amostra_pemob"]=base.cod_ibge.isin(pemob.cod_ibge.dropna().unique()).astype(int)
# MUNIC 2020
base=base.merge(munic,on="cod_ibge",how="left")
base.to_csv(f"{OUT}/base_municipal_v3.csv",index=False)
print("WIDE atualizado:",base.shape,"| tarifa_2024 preench.:",base.tarifa_2024.notna().sum(),
      "| MUNIC plano preench.:",base.munic_plano_transp_2020.notna().sum())
