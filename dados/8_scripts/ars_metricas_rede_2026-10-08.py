# -*- coding: utf-8 -*-
"""Métricas de rede dos grupos econômicos (08/10/2026) — promessa do memorial de qualificação (Eixo 2).
Reproduz a rede do método v4 (calcular_grupos_economicos_v2.py): 7.680 empresas do núcleo, menos 121 consórcios;
arestas = sócio comum (nome + CPF/CNPJ mascarado), sem a qualificação 20. Confere que os componentes batem com o v4.
Calcula: grau, intermediação, proximidade e autovetor por empresa (dentro do componente); por grupo, densidade,
diâmetro, centralização (Freeman), sócios-ponte, sócios de articulação (bipartido) e comunidades de Louvain
(20 sementes; modularidade e estabilidade); posição dos operadores comprovados das políticas de Tarifa Zero.
Nenhum CPF é gravado nas saídas. Requer networkx, pandas, scikit-learn, matplotlib.
Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni"""
import os
VAULT = os.environ.get("TZ_VAULT", os.path.expanduser("~/mnt/doutorado"))
OUT = os.path.join(VAULT, "03 - Dados/_data/CNPJ/ARS - métricas de rede (out-2026)")
os.makedirs(OUT, exist_ok=True); os.chdir(OUT)
# ===== etapa: rede =====
import pandas as pd, networkx as nx, collections, itertools, json
U=os.path.join(VAULT,"03 - Dados")+"/"
F=U+"_data/CNPJ/filtrados (6 CNAEs transporte, 24-07-2026)/"
comp=pd.read_csv(F+"rede_nucleo_ativa_equity_componentes.csv",dtype=str); comp["cnpj_basico"]=comp.cnpj_basico.str.zfill(8)
cons=comp.razao_social.str.upper().str.contains("CONSORCIO|CONSÓRCIO",regex=True)
univ=set(comp.loc[~cons,"cnpj_basico"]); print("universo",len(comp),"consórcios",cons.sum(),"sem",len(univ))
soc=pd.read_csv(F+"socios_filtrado_6cnaes.csv",dtype=str); soc.columns=[c.strip() for c in soc.columns]
soc["cnpj_basico"]=soc.cnpj_basico.str.zfill(8)
s=soc[soc.cnpj_basico.isin(univ)&(soc.qualificacao_socio!="20")].copy()
s["ident"]=s.nome_socio_ou_razao_social.str.strip().str.upper()+"|"+s.cnpj_cpf_socio.astype(str).str.strip()
s=s[s.ident.notna()]
print("vínculos",len(s),"sócios distintos",s.ident.nunique())
# bipartido
B=nx.Graph()
B.add_nodes_from(univ,bipartite=0)
for c,i in zip(s.cnpj_basico,s.ident): B.add_edge(c,"S:"+i)
# projeção ponderada (nº de sócios em comum)
G=nx.Graph(); G.add_nodes_from(univ)
w=collections.Counter()
for i,grp in s.groupby("ident").cnpj_basico:
    cs=sorted(set(grp))
    for a,b in itertools.combinations(cs,2): w[(a,b)]+=1
for (a,b),k in w.items(): G.add_edge(a,b,weight=k)
cc=sorted(nx.connected_components(G),key=len,reverse=True)
print("empresas",G.number_of_nodes(),"arestas",G.number_of_edges(),"componentes>=2",sum(1 for c in cc if len(c)>=2),"maiores",[len(c) for c in cc[:12]])
# conferir com v4
v4=pd.read_csv(F+"grupos_economicos_v4_componentes_completos.csv",dtype=str); v4["cnpj_basico"]=v4.cnpj_basico.str.zfill(8)
sz=v4.groupby("componente_id").size().sort_values(ascending=False)
print("v4 componentes",len(sz),"maiores",sz.head(12).tolist())
import pickle; import tempfile; PK=os.path.join(tempfile.gettempdir(),"ars_rede.pkl"); pickle.dump((B,G,s[["cnpj_basico","ident","qualificacao_socio","tipo_socio"]]),open(PK,"wb"))

# ===== etapa: metricas =====
import pandas as pd, networkx as nx, numpy as np, pickle, collections, json, warnings
from networkx.algorithms import bipartite
warnings.filterwarnings("ignore")
U=os.path.join(VAULT,"03 - Dados")+"/"
B,G,s=pickle.load(open(os.path.join(__import__("tempfile").gettempdir(),"ars_rede.pkl"),"rb"))
E=pd.read_excel(U+"Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx",sheet_name="Empresas",dtype=str)
E["cnpj_basico"]=E.cnpj_basico.str.zfill(8)
R=pd.read_excel(U+"Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx",sheet_name="Resumo por grupo",dtype={"id_grupo":str})
g_of=dict(zip(E.cnpj_basico,E.id_grupo)); cl_of=dict(zip(E.cnpj_basico,E.cluster_id)); rz=dict(zip(E.cnpj_basico,E.razao_social))
print("empresas com grupo",E.id_grupo.notna().sum(),"grupos",E.id_grupo.nunique())
# conferência: cada grupo multiempresa = um componente?
comp_of={}
for k,c in enumerate(nx.connected_components(G)):
    for n in c: comp_of[n]=k
chk=collections.defaultdict(set)
for c,gid in g_of.items():
    if isinstance(gid,str) and c in comp_of: chk[gid].add(comp_of[c])
print("grupos em >1 componente:",sum(1 for v in chk.values() if len(v)>1), "grupos sem nó na rede:", E.id_grupo.nunique()-len(chk))
# ---------- métricas por empresa (dentro do componente)
rows=[]
for c in nx.connected_components(G):
    H=G.subgraph(c); n=len(c)
    if n>=3:
        bt=nx.betweenness_centrality(H,normalized=True); cl=nx.closeness_centrality(H)
        try: ev=nx.eigenvector_centrality_numpy(H)
        except Exception: ev={x:np.nan for x in c}
    else:
        bt={x:0.0 for x in c}; cl={x:1.0 if n==2 else 0.0 for x in c}; ev={x:np.nan for x in c}
    for x in c:
        rows.append(dict(cnpj_basico=x,razao_social=rz.get(x),id_grupo=g_of.get(x),cluster_id=cl_of.get(x),tamanho_componente=n,
                         grau=H.degree(x),grau_ponderado=H.degree(x,weight="weight"),intermediacao=bt[x],proximidade=cl[x],autovetor=ev[x]))
emp=pd.DataFrame(rows)
# ---------- sócios: grau no bipartido e pontos de articulação
soc_deg=collections.Counter(s.ident)
rows=[]; art_total=0
gstats=[]
for gid,sub in emp[emp.id_grupo.notna()].groupby("id_grupo"):
    cs=set(sub.cnpj_basico); n=len(cs)
    H=G.subgraph(cs)
    socs={nb for c in cs for nb in B.neighbors(c)}
    BB=B.subgraph(cs|socs)
    multi=[x for x in socs if BB.degree(x)>=2]          # sócios que ligam 2+ empresas do grupo
    arts=[x for x in nx.articulation_points(BB) if x.startswith("S:")] if n>=2 else []
    d=nx.density(H) if n>=2 else np.nan
    degs=np.array([H.degree(x) for x in cs]) if n>=2 else np.array([0])
    cdeg=((degs.max()-degs).sum()/((n-1)*(n-2))) if n>=3 else np.nan   # centralização de grau (Freeman)
    bts=sub.intermediacao.values; cbt=((bts.max()-bts).sum()/(n-1)) if n>=3 else np.nan  # centralização de intermediação (normalizada)
    diam=nx.diameter(H) if n>=2 and nx.is_connected(H) else np.nan
    pj=sum(1 for x in multi if s.loc[s.ident==x[2:],"tipo_socio"].iloc[0]=="PJ") if multi else 0
    central=sub.sort_values(["intermediacao","grau"],ascending=False).iloc[0]
    gstats.append(dict(id_grupo=gid,n_empresas=n,n_socios=len(socs),socios_ponte=len(multi),socios_ponte_pj=pj,socios_articulacao=len(arts),
                       densidade=d,centralizacao_grau=cdeg,centralizacao_intermediacao=cbt,diametro=diam,
                       empresa_central=central.razao_social,intermediacao_max=central.intermediacao))
grp=pd.DataFrame(gstats).merge(R[["id_grupo","nome_grupo","capital_social_total_reais","nome_mercado_confirmado"]],on="id_grupo",how="left")
# ---------- Louvain (projeção ponderada, 20 sementes)
from sklearn.metrics import normalized_mutual_info_score as nmi
nodes=sorted(G.nodes()); labs=[]; mods=[]
for seed in range(20):
    com=nx.community.louvain_communities(G,weight="weight",resolution=1.0,seed=seed)
    mods.append(nx.community.modularity(G,com,weight="weight"))
    lab={x:k for k,c in enumerate(com) for x in c}; labs.append([lab[x] for x in nodes])
pairs=[nmi(labs[i],labs[j]) for i in range(20) for j in range(i+1,20)]
# comunidades só nos componentes com 2+ empresas (isoladas viram comunidades unitárias)
comR=nx.community.louvain_communities(G,weight="weight",resolution=1.0,seed=0)
lab0={x:k for k,c in enumerate(comR) for x in c}
emp["comunidade_louvain"]=emp.cnpj_basico.map(lab0)
ncom=emp[emp.id_grupo.notna()].groupby("id_grupo").comunidade_louvain.nunique()
# estabilidade da divisão por grupo: nº de comunidades em cada semente
ncs=pd.DataFrame({f"s{k}":pd.Series(dict(zip(nodes,labs[k]))) for k in range(20)})
ncs["id_grupo"]=ncs.index.map(g_of)
spl=ncs[ncs.id_grupo.notna()].groupby("id_grupo").nunique()
grp["comunidades_louvain"]=grp.id_grupo.map(ncom)
grp["comunidades_min"]=grp.id_grupo.map(spl.min(axis=1)); grp["comunidades_max"]=grp.id_grupo.map(spl.max(axis=1))
# modularidade interna dos grupos grandes (Louvain só dentro do grupo)
def modint(gid):
    cs=set(emp.loc[emp.id_grupo==gid,"cnpj_basico"]); H=G.subgraph(cs)
    if len(cs)<5: return np.nan
    c=nx.community.louvain_communities(H,weight="weight",seed=0); return nx.community.modularity(H,c,weight="weight")
grp["modularidade_interna"]=grp.id_grupo.map(modint)
out=dict(empresas=G.number_of_nodes(),arestas=G.number_of_edges(),socios=int(s.ident.nunique()),
         modularidade_media=float(np.mean(mods)),modularidade_min=float(min(mods)),modularidade_max=float(max(mods)),
         nmi_medio=float(np.mean(pairs)),nmi_min=float(min(pairs)),comunidades_total=len(comR),
         comunidades_2mais=sum(1 for c in comR if len(c)>=2))
emp.to_csv("ars_metricas_empresas.csv",index=False); grp.to_csv("ars_metricas_grupos.csv",index=False)
json.dump(out,open("ars_resumo.json","w"),indent=1); print(json.dumps(out,indent=1))
print(grp.describe().T[["count","mean","50%","max"]].round(3))

# ===== etapa: extra =====
import pandas as pd, pickle, networkx as nx, json
B,G,s=pickle.load(open(os.path.join(__import__("tempfile").gettempdir(),"ars_rede.pkl"),"rb"))
e=pd.read_csv("ars_metricas_empresas.csv",dtype={"cnpj_basico":str})
tipo=dict(zip("S:"+s.ident,s.tipo_socio))
res={"grupos_3mais":0,"com_articulacao":0,"articulacao_pj":0,"so_pj":0}
for gid,sub in e[e.id_grupo.notna()].groupby("id_grupo"):
    cs=set(sub.cnpj_basico)
    if len(cs)<3: continue
    res["grupos_3mais"]+=1
    socs={nb for c in cs for nb in B.neighbors(c)}
    BB=B.subgraph(cs|socs)
    arts=[x for x in nx.articulation_points(BB) if x.startswith("S:")]
    if arts:
        res["com_articulacao"]+=1
        if any(tipo.get(x)=="PJ" for x in arts): res["articulacao_pj"]+=1
        if all(tipo.get(x)=="PJ" for x in arts): res["so_pj"]+=1
print(res); json.dump(res,open("ars_articulacao.json","w"))

# ===== etapa: fig =====
import pandas as pd, pickle, networkx as nx, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"svg.fonttype":"none"})
B,G,s=pickle.load(open(os.path.join(__import__("tempfile").gettempdir(),"ars_rede.pkl"),"rb"))
e=pd.read_csv("ars_metricas_empresas.csv",dtype={"cnpj_basico":str})
PAL=['#1A54C7','#D9822B','#2E9E6A','#8E44AD','#C2410C','#0E7490','#A16207','#64748B']
TINTA="#1F2430"
fig,axs=plt.subplots(1,2,figsize=(9.6,4.6),facecolor="white")
for ax,(gid,tit) in zip(axs,[("GE-001","A. Barata (51 empresas)"),("GE-005","B. Comporte (20 empresas)")]):
    cs=list(e.loc[e.id_grupo==gid,"cnpj_basico"]); H=G.subgraph(cs)
    com=nx.community.louvain_communities(H,weight="weight",seed=0)
    com=sorted(com,key=len,reverse=True); cm={x:k for k,c in enumerate(com) for x in c}
    pos=nx.spring_layout(H,seed=3,k=0.35,iterations=200,weight=None)
    bt=dict(zip(e.cnpj_basico,e.intermediacao))
    nx.draw_networkx_edges(H,pos,ax=ax,edge_color="#B8BEC8",width=0.6)
    nx.draw_networkx_nodes(H,pos,ax=ax,node_color=[PAL[cm[x]%len(PAL)] for x in H],node_size=[30+600*bt.get(x,0) for x in H],linewidths=0.4,edgecolors="#FFFFFF")
    mod=nx.community.modularity(H,com,weight="weight")
    br=lambda v: f"{v:.2f}".replace(".",",")
    ax.set_title(f"{tit}\n{len(com)} comunidades · modularidade {br(mod)} · densidade {br(nx.density(H))}",fontsize=9,color=TINTA,loc="left")
    ax.set_axis_off()
fig.text(0.01,0.01,"Cor: comunidade (Louvain). Tamanho do nó: centralidade de intermediação. Aresta: sócio em comum.",fontsize=8,color="#4A5160")
fig.savefig("ars_redes_barata_comporte.svg",bbox_inches="tight",facecolor="white"); fig.savefig("ars_redes_barata_comporte.png",dpi=220,bbox_inches="tight",facecolor="white")

# ===== etapa: grupos com 5+ empresas e operadores das políticas de Tarifa Zero =====
import re
e=pd.read_csv("ars_metricas_empresas.csv",dtype={"cnpj_basico":str}); g=pd.read_csv("ars_metricas_grupos.csv")
def inner(gid):
    cs=set(e.loc[e.id_grupo==gid,"cnpj_basico"]); H=G.subgraph(cs)
    ks=[len(nx.community.louvain_communities(H,weight="weight",seed=k)) for k in range(20)]
    return pd.Series(dict(com_min=min(ks),com_max=max(ks)))
big=g[g.n_empresas>=5].copy(); big[["com_min","com_max"]]=big.id_grupo.apply(inner); big.to_csv("ars_grupos_5mais.csv",index=False)
m=pd.read_excel(U+"_data/casos por fonte/Municípios TZ - consolidado.xlsx",sheet_name="consolidado",dtype=str)
ops=[]
for mun,uf,v in zip(m["Município"],m["UF"],m["Operador — CNPJ"]):
    if isinstance(v,str):
        for x in re.findall(r'\d{2}\.?\d{3}\.?\d{3}(?:/\d{4}-?\d{2})?',v): ops.append((mun,uf,re.sub(r'\D','',x)[:8]))
o=pd.DataFrame(ops,columns=["Município","UF","cnpj_basico"]).drop_duplicates()
jg=o.merge(e,on="cnpj_basico"); jg=jg[jg.id_grupo.notna()].copy(); pos=[];ns=[]
for _,r in jg.iterrows():
    sub=e[e.id_grupo==r.id_grupo].sort_values(["intermediacao","grau"],ascending=False).reset_index(drop=True)
    ns.append(len(sub)); pos.append(int(sub.index[sub.cnpj_basico==r.cnpj_basico][0])+1)
jg["n_grupo"]=ns; jg["posicao_intermediacao"]=pos
jg.merge(g[["id_grupo","nome_grupo","densidade","modularidade_interna"]],on="id_grupo").to_csv("ars_operadores_tz.csv",index=False)
print("operadores comprovados:",o.cnpj_basico.nunique(),"em grupo:",len(jg))
