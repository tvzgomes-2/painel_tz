# -*- coding: utf-8 -*-
"""Rede estendida dos grupos econômicos e figuras da Seção 6.4 (08/10/2026).

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni

1. Refaz a rede de 1º nível (método v4, igual a ars_metricas_rede_2026-10-08.py).
2. Figura 12: pequenos múltiplos das redes de sócios-hub dos 223 grupos multiempresa (327 grupos, numeração de 12/08/2026).
3. Rede estendida: holdings-hub (nível 1) → sócios das holdings (nível 2, socios_segunda_camada.csv)
   → empresas de qualquer setor com sócio de nível 2 (nível 2b) → sócios-hub comuns a 2+ empresas 2b (nível 3).
   Os sócios das empresas 2b vêm de socios_empresas_nivel2b_bruto.csv (varredura awk dos 10 arquivos SOCIO brutos).
4. Louvain nos componentes estendidos que fundem 2+ grupos (20 sementes; modularidade; NMI comunidade × grupo).
5. Figura 13: as 40 maiores ilhas da rede estendida.
6. Mapa 5: agrupamentos CL da tabela mestre por município (municipios_atuacao) sobre a malha IBGE 2022 simplificada.

Nenhum CPF é gravado nas saídas. Uso: python ars_rede_estendida_figuras_2026-10-08.py [caminho do cofre]
"""
import os, sys, tempfile
VAULT=sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..")
U=os.path.join(VAULT,"03 - Dados")+"/"
OUT=U+"_data/CNPJ/ARS - métricas de rede (out-2026)/"
ATT=os.path.join(VAULT,"_attachments")+"/"
TMP=tempfile.gettempdir()+"/"

# ---- 1. Rede de 1º nível (v4) ----
import pandas as pd, networkx as nx, collections, itertools, json
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
import pickle; pickle.dump((B,G,s[["cnpj_basico","ident","qualificacao_socio","tipo_socio"]]),open(TMP+"ars_rede.pkl","wb"))

# ---- 2. Figura 12 ----
import pandas as pd, networkx as nx, pickle, re, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
plt.rcParams.update({"font.family":"DejaVu Sans","svg.fonttype":"none"})
B,G,s=pickle.load(open(TMP+"ars_rede.pkl","rb"))
E=pd.read_excel(U+"Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx",sheet_name="Empresas",dtype=str); E["cnpj_basico"]=E.cnpj_basico.str.zfill(8)
R=pd.read_excel(U+"Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx",sheet_name="Resumo por grupo",dtype={"id_grupo":str})
nucleo=set(E.cnpj_basico)|set(G.nodes())
HOLD=re.compile(r"PARTICIPA|HOLDING|EMPREEND|ADMINISTRA|INVEST|PATRIMON|GEST[AÃ]O|NEGOCIOS|NEGÓCIOS|CAPITAL|S/?A$")
def tipo(ident,t):
    if t!="PJ": return "PF"
    nome,doc=ident.split("|",1); base=re.sub(r"\D","",doc)[:8]
    if base in nucleo: return "OP"
    if HOLD.search(nome): return "HOLD"
    return "OUT"
tp={i:tipo(i,t) for i,t in zip(s.ident,s.tipo_socio)}
gof=dict(zip(E.cnpj_basico,E.id_grupo))
R=R.sort_values("capital_social_total_reais",ascending=False); ordem=list(R.id_grupo); nome={k:str(v).split(" (")[0].replace(" Participacoes Ltda","").replace(" Participacoes","")[:18] for k,v in zip(R.id_grupo,R.nome_grupo)}
panels=[]; n1=0; nhub=0; nv=0; tipos={"PF":0,"HOLD":0,"OP":0,"OUT":0}
for gid in ordem:
    cs=[c for c,g in gof.items() if g==gid and c in G]
    if len(cs)<2: continue
    sub=s[s.cnpj_basico.isin(cs)]
    cnt=sub.groupby("ident").cnpj_basico.nunique(); hubs=list(cnt[cnt>=2].index)
    H=nx.Graph(); H.add_nodes_from(hubs)
    for c,grp in sub[sub.ident.isin(hubs)].groupby("cnpj_basico").ident:
        L=sorted(set(grp))
        for i in range(len(L)):
            for j in range(i+1,len(L)): H.add_edge(L[i],L[j])
    nhub+=len(hubs); nv+=H.number_of_edges()
    for h in hubs: tipos[tp[h]]+=1
    if len(hubs)<2: n1+=1; continue
    panels.append((gid,H))
print("grupos multiempresa:",sum(1 for g in ordem if sum(1 for c,x in gof.items() if x==g and c in G)>=2),"painéis:",len(panels),"com 1 sócio-hub:",n1,"hubs:",nhub,tipos,"vínculos:",nv)
COR={"PF":"#D9822B","HOLD":"#1A54C7","OP":"#2E9E6A","OUT":"#8A93A3"}
# prateleiras: largura proporcional a sqrt(n)
fig=plt.figure(figsize=(11,13.5),facecolor="white"); ax=fig.add_axes([0,0,1,0.93]); ax.set_axis_off()
W=100; x=0; y=0; rowh=0; LAB=set(ordem[:26])
for gid,H in panels:
    n=H.number_of_nodes(); sz=max(2.2,min(16,2.2*np.sqrt(n)))
    lab=f"{gid} {nome[gid]}" if gid in LAB else ""
    slot=max(sz,len(lab)*0.62)
    if x+slot>W: x=0; y-=rowh+3.2; rowh=0
    pos=nx.spring_layout(H,seed=1,iterations=60)
    P=np.array([pos[v] for v in H]); P=(P-P.min(0))/np.maximum(np.ptp(P,0),1e-9) if n>1 else P*0
    P=P*sz*0.9; P[:,0]+=x+(slot-sz)/2; P[:,1]+=y-sz
    idx={v:k for k,v in enumerate(H)}
    segs=[(P[idx[a]],P[idx[b]]) for a,b in H.edges()]
    ax.add_collection(LineCollection(segs,colors="#C9CED6",linewidths=0.35,zorder=1))
    for t in COR:
        m=[idx[v] for v in H if tp[v]==t]
        if m: ax.scatter(P[m,0],P[m,1],s=4 if n>30 else 7,c=COR[t],zorder=2,linewidths=0)
    if gid in LAB:
        ax.text(x+slot/2,y-sz-1.0,lab,ha="center",va="top",fontsize=5.4,color="#1F2430")
    x+=slot+2.2; rowh=max(rowh,sz+ (2.4 if gid in LAB else 0.6))
ax.set_xlim(-1,W+1); ax.set_ylim(y-rowh-2,1); ax.set_aspect("equal")
fig.legend(handles=[Line2D([0],[0],marker="o",ls="",color=COR[k],label=l,markersize=5) for k,l in [("PF","Sócio pessoa física"),("HOLD","Sócio pessoa jurídica: holding ou participações"),("OP","Sócio pessoa jurídica: operadora de transporte"),("OUT","Sócio pessoa jurídica: outra")]],
           loc="upper center",ncol=2,frameon=False,fontsize=8,labelcolor="#1F2430",bbox_to_anchor=(0.5,0.995))
fig.savefig(ATT+"fig12_rede_socios_327.svg",bbox_inches="tight",facecolor="white"); fig.savefig(OUT+"fig12_rede_socios_327.png",dpi=240,bbox_inches="tight",facecolor="white")

# ---- 3. Rede estendida ----
import pandas as pd, networkx as nx, pickle, re, json, collections
F=U+"_data/CNPJ/filtrados (6 CNAEs transporte, 24-07-2026)/"
B,G,s=pickle.load(open(TMP+"ars_rede.pkl","rb"))
E=pd.read_excel(U+"Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx",sheet_name="Empresas",dtype=str); E["cnpj_basico"]=E.cnpj_basico.str.zfill(8)
gof=dict(zip(E.cnpj_basico,E.id_grupo)); clof=dict(zip(E.cnpj_basico,E.cluster_id))
nucleo=set(G.nodes())
HOLD=re.compile(r"PARTICIPA|HOLDING|EMPREEND|ADMINISTRA|INVEST|PATRIMON|GEST[AÃ]O|NEG[OÓ]CIOS|CAPITAL")
EXC=re.compile(r"ASSOCIA|SINDICAT|COOPERATIV|FEDERA[CÇ]|CONS[OÓ]RCIO")
# nível 1: sócios-hub PJ holding (2+ empresas do núcleo)
cnt=s.groupby("ident").cnpj_basico.nunique()
pj=s[s.tipo_socio=="PJ"].ident.unique()
base=lambda i: re.sub(r"\D","",i.split("|",1)[1])[:8]
hold=[i for i in pj if cnt[i]>=2 and base(i) not in nucleo and HOLD.search(i.split("|")[0])]
hb={base(i):i for i in hold}
print("holdings-hub nível 1:",len(hold))
X=nx.Graph()
for c,i in zip(s.cnpj_basico,s.ident): X.add_edge("E:"+c,"S:"+i,lvl=1)
for n in list(X): X.nodes[n]["lvl"]=("emp1" if n.startswith("E:") else "soc1")
# nível 2: sócios das holdings-hub
s2=pd.read_csv(F+"socios_segunda_camada.csv",dtype=str); s2["cnpj_basico"]=s2.cnpj_basico.str.zfill(8)
s2=s2[s2.cnpj_basico.isin(hb)&(s2.qualificacao_socio!="20")&s2.nome_socio_ou_razao_social.notna()]
s2["ident"]=s2.nome_socio_ou_razao_social.str.strip().str.upper()+"|"+s2.cnpj_cpf_socio.astype(str).str.strip()
s2=s2[~s2.nome_socio_ou_razao_social.str.upper().str.contains(EXC)]
for h,i in zip(s2.cnpj_basico,s2.ident):
    a="S:"+hb[h]; b="S2:"+i
    X.add_edge(a,b,lvl=2); X.nodes[b].setdefault("lvl","soc2")
lv2=set(s2.ident); print("holdings com sócios lidos:",s2.cnpj_basico.nunique(),"sócios nível 2:",len(lv2))
# nível 2b: empresas de qualquer setor com sócio de nível 2; nível 3: sócios-hub dessas empresas
e2b=pd.read_csv(F+"empresas_ligadas_holdings_qualquer_setor.csv",dtype=str); e2b["cnpj_basico"]=e2b.cnpj_basico.str.zfill(8)
e2b=e2b[~e2b.razao_social.str.upper().str.contains(EXC)]
setor=dict(zip(e2b.cnpj_basico,e2b.setor)); rz2=dict(zip(e2b.cnpj_basico,e2b.razao_social))
raw=pd.read_csv(U+"_data/CNPJ/ARS - métricas de rede (out-2026)/socios_empresas_nivel2b_bruto.csv",sep=";",header=None,dtype=str)
raw.columns=["cnpj_basico","tipo","nome","doc","qualif","data","pais","rep","nomerep","qrep","faixa"]
raw["cnpj_basico"]=raw.cnpj_basico.str.zfill(8)
raw=raw[raw.cnpj_basico.isin(setor)&(raw.qualif!="20")&raw.nome.notna()]
raw["ident"]=raw.nome.str.strip().str.upper()+"|"+raw.doc.astype(str).str.strip()
lig=raw[raw.ident.isin(lv2)]
for c,i in zip(lig.cnpj_basico,lig.ident):
    X.add_edge("S2:"+i,"E2:"+c,lvl=2); X.nodes["E2:"+c]["lvl"]="emp2b"
emp2b={c for c in lig.cnpj_basico}
r3=raw[raw.cnpj_basico.isin(emp2b)&~raw.ident.isin(lv2)]
c3=r3.groupby("ident").cnpj_basico.nunique(); hub3=set(c3[c3>=2].index)
for c,i in zip(r3.cnpj_basico,r3.ident):
    if i in hub3: X.add_edge("E2:"+c,"S3:"+i,lvl=3); X.nodes["S3:"+i].setdefault("lvl","soc3")
print("empresas 2b ligadas:",len(emp2b),"sócios-hub nível 3:",len(hub3))
for n,d in X.nodes(data=True):
    if "lvl" not in d: d["lvl"]="soc2" if n.startswith("S2:") else "soc3"
# componentes estendidos: grupos que se fundem
comp=list(nx.connected_components(X))
fus=[]
for c in comp:
    gs={gof[n[2:]] for n in c if n.startswith("E:") and isinstance(gof.get(n[2:]),str)}
    if len(gs)>=2: fus.append((len(c),sorted(gs)))
fus.sort(reverse=True)
print("componentes estendidos com 2+ grupos:",len(fus))
for n,gs in fus[:15]: print(n,len(gs),gs[:12])
# CL da tabela mestre: conferir
cl=collections.defaultdict(set)
for c,g in gof.items():
    k=clof.get(c)
    if isinstance(k,str) and k.startswith("CL-") and isinstance(g,str): cl[k].add(g)
same={}
gcomp={}
for k,c in enumerate(comp):
    for n in c:
        if n.startswith("E:") and isinstance(gof.get(n[2:]),str): gcomp[gof[n[2:]]]=k
for k,gs in sorted(cl.items()):
    comps={gcomp.get(g) for g in gs}
    print(k,sorted(gs),"-> componentes estendidos:",len(comps))
pickle.dump((X,setor,rz2,gof),open(TMP+"ars_estendida.pkl","wb"))
json.dump({"holdings_hub":len(hold),"socios_nivel2":len(lv2),"empresas_2b":len(emp2b),"socios_hub_3":len(hub3),"fusoes":fus},open(OUT+"ars_estendida_resumo.json","w"),indent=1,default=list)

# ---- 4. Louvain nos componentes fundidos ----
import networkx as nx, collections, json, pickle
from sklearn.metrics import normalized_mutual_info_score as NMI
X,setor,rz2,gof=pickle.load(open(TMP+"ars_estendida.pkl","rb"))
res=[]
for c in nx.connected_components(X):
    gs={gof[n[2:]] for n in c if n.startswith("E:") and isinstance(gof.get(n[2:]),str)}
    if len(gs)<2: continue
    H=X.subgraph(c); best=None; mods=[]
    for seed in range(20):
        P=nx.community.louvain_communities(H,seed=seed); q=nx.community.modularity(H,P); mods.append(q)
        if best is None or q>best[0]: best=(q,P)
    q,P=best; lab={n:k for k,p in enumerate(P) for n in p}
    E1=[n for n in c if n.startswith("E:") and isinstance(gof.get(n[2:]),str)]
    nmi=NMI([gof[n[2:]] for n in E1],[lab[n] for n in E1])
    sep=all(len({lab[n] for n in E1 if gof[n[2:]]==g} & {lab[m] for m in E1 if gof[m[2:]]!=g})==0 for g in gs)
    fin=sum(1 for n in c if n.startswith("E2:") and setor.get(n[3:])=="Serviços financeiros")
    res.append({"nos":len(c),"grupos":sorted(gs),"comunidades":len(P),"modularidade_max":round(q,3),"modularidade_min":round(min(mods),3),"nmi_comunidade_grupo":round(nmi,2),"grupos_em_comunidades_distintas":sep,"empresas_financeiras":fin})
res.sort(key=lambda r:-r["nos"])
for r in res: print(r)
json.dump(res,open(OUT+"ars_estendida_louvain.json","w"),ensure_ascii=False,indent=1)

# ---- 5. Figura 13 ----
import pickle, networkx as nx, numpy as np, collections, matplotlib, pandas as pd; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
plt.rcParams.update({"font.family":"DejaVu Sans","svg.fonttype":"none"})
X,setor,rz2,gof=pickle.load(open(TMP+"ars_estendida.pkl","rb"))
R=pd.read_excel(U+"Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx",sheet_name="Resumo por grupo",dtype={"id_grupo":str})
nome={k:str(v).split(" (")[0].replace(" Participacoes Ltda","").replace(" Participacoes","")[:16] for k,v in zip(R.id_grupo,R.nome_grupo)}
def cat(n):
    if n.startswith("E:"): return "emp1"
    if n.startswith("S:"): return "soc1"
    if n.startswith("S2:"): return "soc2"
    if n.startswith("S3:"): return "soc3"
    st=setor.get(n[3:],"")
    return "fin" if st=="Serviços financeiros" else ("trp" if st=="Transporte terrestre" else "out")
COR={"emp1":"#1F2430","soc1":"#D9822B","soc2":"#1A54C7","fin":"#E3B505","trp":"#2E9E6A","out":"#B8BEC8","soc3":"#C2410C"}
SZ={"emp1":9,"soc1":5,"soc2":5,"fin":10,"trp":6,"out":4,"soc3":4}
isl=[]
for c in nx.connected_components(X):
    if not any(n.startswith("E2:") for n in c): continue
    gs=collections.Counter(gof[n[2:]] for n in c if n.startswith("E:") and isinstance(gof.get(n[2:]),str))
    if not gs: continue
    isl.append((len(c),c,gs))
isl.sort(key=lambda t:-t[0]); print("ilhas que cresceram:",len(isl))
isl=isl[:40]
fig=plt.figure(figsize=(11,12.5),facecolor="white"); ax=fig.add_axes([0,0,1,0.93]); ax.set_axis_off()
W=100; x=0; y=0; rowh=0
for n,c,gs in isl:
    H=X.subgraph(c); sz=max(6,min(30,1.25*np.sqrt(n)))
    lab=" + ".join(f"{g} {nome[g]}" for g,_ in gs.most_common(3))+(" …" if len(gs)>3 else "")+f" ({n} nós)"
    fs=4.6 if sz<12 else 5.4; slot=max(sz,len(lab)*fs*0.105)
    if x+slot>W: x=0; y-=rowh+4; rowh=0
    pos=nx.spring_layout(H,seed=2,iterations=50)
    nodes=list(H); P=np.array([pos[v] for v in nodes]); P=(P-P.min(0))/np.maximum(np.ptp(P,0),1e-9); P=P*sz*0.92; P[:,0]+=x+(slot-sz)/2; P[:,1]+=y-sz
    idx={v:k for k,v in enumerate(nodes)}
    ax.add_collection(LineCollection([(P[idx[a]],P[idx[b]]) for a,b in H.edges()],colors="#D5D9E0",linewidths=0.25,zorder=1))
    for t in ["out","soc3","soc2","soc1","trp","fin","emp1"]:
        m=[idx[v] for v in nodes if cat(v)==t]
        if m: ax.scatter(P[m,0],P[m,1],s=SZ[t]*(0.6 if n>200 else 1),c=COR[t],zorder=3 if t in("fin","emp1") else 2,linewidths=0)
    ax.text(x+slot/2,y-sz-0.8,lab,ha="center",va="top",fontsize=fs,color="#1F2430")
    x+=slot+3; rowh=max(rowh,sz+2.5)
ax.set_xlim(-1,W+1); ax.set_ylim(y-rowh-2,1); ax.set_aspect("equal")
L=[("emp1","Operadora de transporte (núcleo)"),("soc1","Sócio de 1º nível"),("soc2","Sócio de holding (2º nível)"),("fin","Empresa ligada: serviços financeiros"),("trp","Empresa ligada: transporte fora do recorte"),("out","Empresa ligada: outro setor"),("soc3","Sócio comum a empresas ligadas (3º nível)")]
fig.legend(handles=[Line2D([0],[0],marker="o",ls="",color=COR[k],label=l,markersize=5) for k,l in L],loc="upper center",ncol=3,frameon=False,fontsize=7.5,labelcolor="#1F2430",bbox_to_anchor=(0.5,0.998))
fig.savefig(ATT+"fig13_rede_estendida.svg",bbox_inches="tight",facecolor="white"); fig.savefig(OUT+"fig13_rede_estendida.png",dpi=240,bbox_inches="tight",facecolor="white")

# ---- 6. Mapa 5 ----
import pandas as pd, geopandas as gpd, unicodedata, re, collections, json
E=pd.read_excel(U+"Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx",sheet_name="Empresas",dtype=str)
C=pd.read_excel(U+"Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx",sheet_name="Resumo por cluster",dtype=str)
FUS=sorted(C[C.fusao_de_2plus_grupos.astype(str)=="True"].cluster_id)
g=gpd.read_file(U+"_data/CNPJ/ARS - métricas de rede (out-2026)/BR_municipios_2022_simpl.geojson")
def nz(t): t=unicodedata.normalize("NFKD",str(t)).encode("ascii","ignore").decode().upper(); return re.sub(r"[^A-Z ]","",t.replace("-"," ")).strip()
g["k"]=g.NM_MUN.map(nz)+"/"+g.SIGLA_UF
key=set(g.k)
E=E[E.id_grupo.notna()]
cl=collections.defaultdict(set); grp=collections.defaultdict(set); miss=collections.Counter()
for _,r in E.iterrows():
    for m in str(r.municipios_atuacao).split(";"):
        m=re.sub(r"\s*\(.*?\)","",m).strip()
        if "/" not in m: continue
        n,uf=m.rsplit("/",1); k=nz(n)+"/"+uf.strip()
        if k not in key: miss[k]+=1; continue
        grp[k].add(r.id_grupo)
        if r.cluster_id in FUS: cl[k].add(r.cluster_id)
print("municípios com grupo:",len(grp),"com CL de fusão:",len(cl),"sem casar:",len(miss),list(miss.most_common(15)))
print({c:sum(c in v for v in cl.values()) for c in FUS}, "2+ CL:",sum(len(v)>1 for v in cl.values()))
json.dump({"FUS":FUS,"cl":{k:sorted(v) for k,v in cl.items()},"grp":{k:sorted(v) for k,v in grp.items()},"miss":dict(miss)},open(TMP+"mapa5_dados.json","w"),ensure_ascii=False)

import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
plt.rcParams.update({"font.family":"DejaVu Sans","svg.fonttype":"none"})
LAB={"CL-01":"Barata + JAL","CL-02":"Comporte + Lessa Carvalho + Rodap + 5 holdings","CL-03":"Belarmino + Weipar","CL-05":"Gulin + Senestra + Transguara + Stabile + AGPS","CL-06":"Nossa Senhora do Ó + Del Rey","CL-09":"Terra + Sunpass","CL-12":"Nova Suissa + Guimarães Lopes"}
COR={"CL-01":"#1A54C7","CL-02":"#D9822B","CL-03":"#2E9E6A","CL-05":"#8E44AD","CL-06":"#C0392B","CL-09":"#E3B505","CL-12":"#17A2B8"}
def cat(k):
    v=cl.get(k)
    if v: return "2+" if len(v)>1 else next(iter(v))
    return "ge" if k in grp else "0"
g["c"]=g.k.map(cat)
CC=dict(COR); CC.update({"2+":"#1F2430","ge":"#C9CED6","0":"#FFFFFF"})
u2=g[["SIGLA_UF","geometry"]].copy(); u2["geometry"]=u2.buffer(0.02); uf=u2.dissolve("SIGLA_UF"); uf["geometry"]=uf.buffer(-0.02).simplify(0.01)
fig,axs=plt.subplots(1,2,figsize=(13,6.6),facecolor="white",gridspec_kw={"width_ratios":[1.05,1]})
box=(-54.5,-27.2,-39.5,-17.5)
for ax,lim in zip(axs,[None,box]):
    for c in ["0","ge"]+FUS+["2+"]:
        sub=g[g.c==c]
        if len(sub): sub.plot(ax=ax,rasterized=True,color=CC[c],edgecolor="#E4E7EC" if c=="0" else "white",linewidth=0.05 if lim is None else 0.15)
    uf.boundary.plot(ax=ax,color="#5B6475",linewidth=0.35 if lim is None else 0.6)
    ax.set_axis_off(); ax.set_aspect("equal")
    if lim: ax.set_xlim(lim[0],lim[2]); ax.set_ylim(lim[1],lim[3])
axs[0].add_patch(Rectangle((box[0],box[1]),box[2]-box[0],box[3]-box[1],fill=False,ec="#1F2430",lw=0.8,ls="--"))
axs[0].set_title("A. Brasil",loc="left",fontsize=10,color="#1F2430")
axs[1].set_title("B. Sudeste e Sul (detalhe)",loc="left",fontsize=10,color="#1F2430")
n={c:sum(c in v for v in cl.values()) for c in FUS}
H=[Patch(fc=COR[c],ec="none",label=f"{c} {LAB[c]} ({n[c]})") for c in FUS]
H+=[Patch(fc="#1F2430",ec="none",label=f"Dois ou mais agrupamentos ({sum(len(v)>1 for v in cl.values())})"),
    Patch(fc="#C9CED6",ec="none",label=f"Só grupos fora dos agrupamentos ({len(set(grp)-set(cl))})")]
fig.legend(handles=H,loc="lower center",ncol=2,frameon=False,fontsize=8,labelcolor="#1F2430",bbox_to_anchor=(0.5,0.0))
fig.subplots_adjust(bottom=0.13,top=0.97,wspace=0.02)
fig.savefig(ATT+"mapa5_agrupamentos_cl.svg",bbox_inches="tight",facecolor="white"); fig.savefig(OUT+"mapa5_agrupamentos_cl.png",dpi=220,bbox_inches="tight",facecolor="white")
print("ok",g.c.value_counts().to_dict())
