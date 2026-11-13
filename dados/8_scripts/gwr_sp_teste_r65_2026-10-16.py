# -*- coding: utf-8 -*-
"""Teste parcial da hipótese em SP — r65 (16/10/2026): o mesmo de 07/10/2026, com a base congelada de 11/10/2026.
Teste parcial da hipótese em SP (07/10/2026): GW logística + Moran + logit global.
Y = Tarifa Zero universal ativa (base-mestre, aba 1). X = presença no município de empresa de grupo
econômico multiempresa (223 dos 327 grupos; Tabela mestre ago-2026), mais log da população 2022,
log do PIB per capita 2021 e participação do FPM na receita corrente 2022 (padronizados).
Rodado no ambiente de nuvem da sessão (mgwr, esda, libpysal e statsmodels não estão instalados no computador).
Para rodar localmente: pip install mgwr esda libpysal statsmodels geopandas; definir TZ_VAULT.
Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni"""
import os
VAULT=os.environ.get("TZ_VAULT", os.path.expanduser("~/mnt/doutorado"))
OUT=os.path.join(VAULT,"03 - Dados/_data/Análise espacial GE x TZ (out-2026, teste SP, base 11-10)")
SRC0=os.path.join(VAULT,"03 - Dados/_data/Análise espacial GE x TZ (out-2026, teste SP)")
os.makedirs(OUT,exist_ok=True); os.chdir(OUT)
# ===== etapa: prep =====
import pandas as pd, numpy as np, unicodedata, re, json
U=os.path.join(VAULT,"03 - Dados")+"/"
n=lambda s: re.sub(r"\s+"," ",unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().lower().strip())
df=pd.read_csv(U+"_data/Base Municipal v3/base_municipal_v3.csv",low_memory=False)
sp=df[df.uf=="SP"].copy(); sp["cod_ibge"]=sp.cod_ibge.astype(int)
# TZ atual (base-mestre 07/10)
m=pd.read_excel(U+"_data/congelamento-2026-10-11/Municípios TZ - consolidado.xlsx",sheet_name="consolidado")  # r65: base congelada de 11/10/2026
m["cod"]=pd.to_numeric(m["Código IBGE"],errors="coerce")
print(m["Situação"].value_counts().to_dict())
at=m[(m["Situação"]=="Ativa")]
print("ativas regua aba:",at["Régua — aba"].value_counts().to_dict())
u=set(at.loc[at["Régua — aba"].astype(str).str.contains("1 Universal"),"cod"].dropna().astype(int))
ev=set(m.loc[m["Situação"].isin(["Ativa","Encerrada"]),"cod"].dropna().astype(int))
sp["tz_univ"]=sp.cod_ibge.isin(u).astype(int); sp["tz_ever"]=sp.cod_ibge.isin(ev).astype(int)
print("SP tz_univ",sp.tz_univ.sum(),"tz_ever",sp.tz_ever.sum(),"(base-mestre SP:", (m.UF=="SP").sum(),")")
# grupos
E=pd.read_excel(U+"Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx",sheet_name="Empresas")
R=pd.read_excel(U+"Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx",sheet_name="Resumo por grupo")
print("empresas c/ grupo:",E.id_grupo.notna().sum(), "grupos:",E.id_grupo.nunique(), "resumo:",len(R))
R=R.sort_values("capital_social_total_reais",ascending=False); R["cum"]=R.capital_social_total_reais.cumsum()/R.capital_social_total_reais.sum()
top=set(R.loc[R.cum<=0.5,"id_grupo"]) | {R.iloc[(R.cum>0.5).values.argmax()].id_grupo}
multi=set(R.loc[R.n_empresas>=2,"id_grupo"])
print("top (metade do capital):",len(top),"multiempresa:",len(multi))
key={(n(a),b):c for a,b,c in zip(sp.nome_mun,sp.uf,sp.cod_ibge)}
key[('mogi mirim','SP')]=3530805; key[('embu das artes','SP')]=3515004
def munis(s):
    out=set()
    for p in str(s).split(";"):
        p=p.strip()
        if "/" in p:
            a,b=p.rsplit("/",1)
            k=(n(a),b.strip())
            if k in key: out.add(key[k])
            elif b.strip()=="SP": miss.add(p)
    return out
miss=set()
E2=E[E.id_grupo.notna()].copy()
col="municipios_nucleo_ativo"
pres={}
for g,s1,s2 in zip(E2.id_grupo,E2[col],E2.municipios_atuacao):
    for c in munis(s1)|munis(s2): pres.setdefault(c,set()).add(g)
print("SP munic sem match:",len(miss),list(miss)[:8])
sp["ge_n"]=sp.cod_ibge.map(lambda c: len(pres.get(c,())))
sp["ge_any"]=(sp.ge_n>0).astype(int)
sp["ge_multi"]=sp.cod_ibge.map(lambda c: int(bool(pres.get(c,set())&multi)))
sp["ge_top"]=sp.cod_ibge.map(lambda c: int(bool(pres.get(c,set())&top)))
print(sp[["ge_any","ge_multi","ge_top"]].sum().to_dict())
print(pd.crosstab(sp.ge_multi,sp.tz_univ))
# covariáveis
sp["log_pop"]=np.log(sp.pop_2022)
sp["log_pibpc"]=np.log(sp.pib_per_capita_2021)
sp["fpm_share"]=sp.fpm_share_receita_corrente_2022
sp["bus_pc"]=sp.frota_onibus_2023/sp.pop_2022*1000
sp["onibus_intramun"]=pd.to_numeric(sp.munic_onibus_intramun_2017,errors="coerce")
sp["concessao17"]=pd.to_numeric(sp.munic_concessao_2017,errors="coerce").fillna(0)
for c in ["log_pop","log_pibpc","fpm_share","bus_pc","onibus_intramun","concessao17"]: print(c, sp[c].isna().sum(), round(sp[c].mean(),3))
print(pd.crosstab(sp.onibus_intramun,sp.tz_univ))
sp.to_csv("sp_modelo.csv",index=False)
json.dump({"top":sorted(top),"multi_n":len(multi)},open("grupos_def.json","w"))

# ===== etapa: modelo =====
import pandas as pd, numpy as np, geopandas as gpd, json, warnings
warnings.filterwarnings("ignore")
import statsmodels.api as sm
from mgwr.gwr import GWR
from mgwr.sel_bw import Sel_BW
from spglm.family import Binomial
import libpysal, esda
U=os.path.join(SRC0,"SP_municipios_2022_simpl.geojson")
g=gpd.read_file(U); g["cod_ibge"]=g.CD_MUN.astype(int)
d=pd.read_csv("sp_modelo.csv")
g=g.merge(d,on="cod_ibge"); g=g[g.fpm_share.notna()].reset_index(drop=True)
print("n",len(g),"TZ",g.tz_univ.sum())
gp=g.to_crs(5880)  # SIRGAS Polyconic Brazil (metros)
cen=gp.geometry.representative_point(); coords=np.c_[cen.x,cen.y]
cont=["log_pop","log_pibpc","fpm_share"]
Z=g[cont].apply(lambda s:(s-s.mean())/s.std())
X=np.c_[g.ge_multi.values, Z.values]; names=["ge_multi"]+cont
y=g.tz_univ.values.reshape(-1,1)
out={}
# global logit
lg=sm.Logit(y,sm.add_constant(X)).fit(disp=0)
tab=pd.DataFrame({"coef":lg.params,"se":lg.bse,"p":lg.pvalues,"OR":np.exp(lg.params)},index=["const"]+names)
print(tab.round(3)); out["logit"]=tab.round(4).to_dict(); out["logit_aic"]=lg.aic; out["logit_pseudoR2"]=lg.prsquared
# sem grupo (comparação)
lg0=sm.Logit(y,sm.add_constant(Z.values)).fit(disp=0); out["logit_sem_ge_aic"]=lg0.aic
# GW logística
sel=Sel_BW(coords,y,X,family=Binomial(),constant=True)
bw=sel.search(criterion="AICc"); print("bw",bw)
res=GWR(coords,y,X,bw=bw,family=Binomial(),constant=True).fit()
print("GWR AICc",res.aicc,"global AICc", lg.aic)
out.update(bw=float(bw),gwr_aicc=float(res.aicc),gwr_aic=float(res.aic))
P=res.params; T=res.tvalues
crit=res.critical_tval() if hasattr(res,"critical_tval") else 1.96
crit=np.atleast_1d(crit); print("t crítico (Bonferroni-adj, da Silva & Fotheringham):",crit)
for i,nm in enumerate(["const"]+names):
    g["b_"+nm]=P[:,i]; g["t_"+nm]=T[:,i]
    c=crit[i] if len(crit)>1 else crit[0]
    g["sig_"+nm]=(np.abs(T[:,i])>c).astype(int)
    s=g["b_"+nm]; out["gwr_"+nm]={"min":float(s.min()),"q1":float(s.quantile(.25)),"med":float(s.median()),"q3":float(s.quantile(.75)),"max":float(s.max()),"pct_pos":float((s>0).mean()),"n_sig":int(g["sig_"+nm].sum()),"n_sig_pos":int(((g["sig_"+nm]==1)&(s>0)).sum()),"n_sig_neg":int(((g["sig_"+nm]==1)&(s<0)).sum()),"t_crit":float(c)}
    print(nm, out["gwr_"+nm])
# condição local (multicolinearidade)
try:
    lcn=res.local_collinearity()[2]; g["cond"]=lcn; out["cond_max"]=float(np.nanmax(lcn)); out["cond_gt30"]=int((lcn>30).sum())
except Exception as e: print("lc",e)
# Moran
w=libpysal.weights.Queen.from_dataframe(gp,use_index=False); w.transform="r"
ilands=w.islands
mi=esda.Moran(g.tz_univ.values.astype(float),w,permutations=9999); out["moran_tz"]={"I":mi.I,"p_sim":mi.p_sim}
bv=esda.Moran_BV(g.tz_univ.values.astype(float),g.ge_multi.values.astype(float),w,permutations=9999); out["moran_bv_tz_ge"]={"I":bv.I,"p_sim":bv.p_sim}
mg=esda.Moran(g.ge_multi.values.astype(float),w,permutations=9999); out["moran_ge"]={"I":mg.I,"p_sim":mg.p_sim}
li=esda.Moran_Local(g.tz_univ.values.astype(float),w,permutations=9999,seed=1)
g["lisa_q"]=li.q; g["lisa_p"]=li.p_sim
out["lisa_HH_sig"]=int(((li.q==1)&(li.p_sim<0.05)).sum())
print({k:out[k] for k in ["moran_tz","moran_bv_tz_ge","moran_ge","lisa_HH_sig"]}, "ilhas",ilands)
# estratos de porte
g["faixa"]=pd.cut(g.pop_2022,[0,20e3,50e3,100e3,500e3,1e8],labels=["<20 mil","20–50 mil","50–100 mil","100–500 mil",">500 mil"])
ct=g.groupby(["faixa","ge_multi"]).tz_univ.agg(["sum","count"]); ct["taxa"]=(ct["sum"]/ct["count"]*100).round(1)
print(ct); out["estratos"]={f"{a}|{b}":[int(r["sum"]),int(r["count"])] for (a,b),r in ct.iterrows()}
g.drop(columns="geometry").to_csv("sp_resultados.csv",index=False)
g[["cod_ibge","NM_MUN","tz_univ","ge_multi","b_ge_multi","t_ge_multi","sig_ge_multi","lisa_q","lisa_p","geometry"]].to_file("sp_resultados.geojson",driver="GeoJSON")
json.dump(out,open("resultados.json","w"),indent=1,default=float)

# ===== etapa: robust =====
import pandas as pd,numpy as np,statsmodels.api as sm,json
g=pd.read_csv("sp_resultados.csv")
cont=["log_pop","log_pibpc","fpm_share"]
Z=g[cont].apply(lambda s:(s-s.mean())/s.std())
r={}
def fit(mask,gev,lab,extra=None):
    X=pd.concat([g.loc[mask,[gev]],Z.loc[mask]],axis=1)
    if extra: X=pd.concat([X,g.loc[mask,extra]],axis=1)
    m=sm.Logit(g.loc[mask,"tz_univ"],sm.add_constant(X)).fit(disp=0)
    r[lab]={"n":int(mask.sum()),"tz":int(g.loc[mask,"tz_univ"].sum()),"OR_ge":round(float(np.exp(m.params[gev])),3),"p_ge":round(float(m.pvalues[gev]),3),"OR_fpm":round(float(np.exp(m.params["fpm_share"])),3),"p_fpm":round(float(m.pvalues["fpm_share"]),3),"OR_pop":round(float(np.exp(m.params["log_pop"])),3),"p_pop":round(float(m.pvalues["log_pop"]),3)}
allm=pd.Series(True,index=g.index)
fit(allm,"ge_multi","A. todos, grupo multiempresa (223)")
fit(allm,"ge_any","B. todos, qualquer dos 327")
fit(allm,"ge_top","C. todos, 26 maiores grupos")
fit(g.onibus_intramun==1,"ge_multi","D. só com ônibus intramunicipal (MUNIC 2017)")
fit((g.pop_2022>=20e3)&(g.pop_2022<500e3),"ge_multi","E. 20 mil a 500 mil hab.")
for k,v in r.items(): print(k,v)
# onde estão os 79 negativos significativos
s=g[g.sig_ge_multi==1]
print(s.regiao_admin_sp.value_counts().head(10).to_dict() if "regiao_admin_sp" in g else "")
print("TZ entre sig:",s.tz_univ.sum(),"de",len(s),"; grupo entre sig:",s.ge_multi.sum())
json.dump(r,open("robustez.json","w"),indent=1,ensure_ascii=False)

# ===== etapa: mapas =====
import geopandas as gpd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np, matplotlib.ticker
from matplotlib.colors import TwoSlopeNorm, LinearSegmentedColormap
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
plt.rcParams.update({"axes.formatter.use_locale":False,"font.family":"DejaVu Sans","font.size":9,"svg.fonttype":"none"})
g=gpd.read_file("sp_resultados.geojson")
TINTA="#1F2430"
# Mapa 1: sobreposição
cat=np.select([(g.tz_univ==1)&(g.ge_multi==1),(g.tz_univ==1),(g.ge_multi==1)],["ambos","tz","ge"],"nenhum")
cores={"nenhum":"#EEF0F3","ge":"#A9B4C8","tz":"#1A54C7","ambos":"#D9822B"}
fig,ax=plt.subplots(figsize=(7.2,4.6),facecolor="white")
g.assign(c=[cores[c] for c in cat]).plot(color=[cores[c] for c in cat],edgecolor="#FFFFFF",linewidth=0.2,ax=ax)
ax.set_axis_off()
n={k:int((cat==k).sum()) for k in cores}
ax.legend(handles=[Patch(fc=cores["tz"],label=f"Tarifa Zero universal, sem empresa de grupo ({n['tz']})"),
                   Patch(fc=cores["ambos"],label=f"Tarifa Zero universal e empresa de grupo ({n['ambos']})"),
                   Patch(fc=cores["ge"],label=f"Empresa de grupo, sem Tarifa Zero ({n['ge']})"),
                   Patch(fc=cores["nenhum"],ec="#C9CED6",label=f"Nenhum dos dois ({n['nenhum']})")],
          loc="upper left",bbox_to_anchor=(0,0.02),ncol=2,frameon=False,fontsize=8,labelcolor=TINTA)
fig.savefig("mapa_sp_sobreposicao.svg",bbox_inches="tight",facecolor="white"); fig.savefig("mapa_sp_sobreposicao.png",dpi=220,bbox_inches="tight",facecolor="white")
# Mapa 2: coeficiente local
cm=LinearSegmentedColormap.from_list("d",["#1A54C7","#8FB0E8","#F7F7F7","#F2B48C","#C2410C"])
v=g.b_ge_multi; lim=max(abs(v.min()),abs(v.max()))
fig,ax=plt.subplots(figsize=(7.2,4.6),facecolor="white")
g.plot(column="b_ge_multi",cmap=cm,norm=TwoSlopeNorm(0,-lim,lim),edgecolor="#FFFFFF",linewidth=0.2,ax=ax,legend=True,
       legend_kwds={"shrink":0.55,"label":"Coeficiente local (log da razão de chances)","orientation":"vertical"})
cb=fig.axes[-1]; cb.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x,p: f"{x:.1f}".replace(".",",").replace("-","−")))
g[g.sig_ge_multi==1].boundary.plot(ax=ax,color=TINTA,linewidth=0.6)
ax.set_axis_off()
ax.legend(handles=[Line2D([0],[0],color=TINTA,lw=1,label=f"Significativo (|t| > 2,50; {int(g.sig_ge_multi.sum())} municípios)")],loc="upper left",bbox_to_anchor=(0,0.02),frameon=False,fontsize=8,labelcolor=TINTA)
fig.savefig("mapa_sp_coef_local_grupo.svg",bbox_inches="tight",facecolor="white"); fig.savefig("mapa_sp_coef_local_grupo.png",dpi=220,bbox_inches="tight",facecolor="white")
print(n)
