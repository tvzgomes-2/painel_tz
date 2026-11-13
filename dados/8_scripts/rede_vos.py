#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rede_vos.py — mapas bibliométricos da RSL no padrão VOSviewer.

Implementa, sem dependências externas:
  * normalização por força de associação (association strength), van Eck & Waltman
  * VOS mapping technique — minimização de V(x)=Σ s_ij d_ij² − (2/n) Σ d_ij
  * agrupamento por modularidade (Louvain de um nível, com refinamento)
  * rótulos com supressão de sobreposição, como o VOSviewer

SAÍDAS  três SVGs em _attachments/, cores fixas em hex e fundo branco.
"""
import csv, math, os, re, sys, random, collections

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR = sys.argv[1] if len(sys.argv)>1 else os.path.join(_RAIZ,"05 - Referências","Rede bibliométrica")
OUT = sys.argv[2] if len(sys.argv)>2 else os.path.join(_RAIZ,"_attachments")

# paleta de clusters — categórica, legível em claro e escuro, sem vermelho/verde adjacentes
PALETA = ["#c0392b","#2e86c1","#27865a","#b7860b","#7d3c98","#0e8f9e","#d35400","#7f8c8d",
          "#a93226","#1f618d","#1e8449","#9a7d0a"]

def esc(s):
    return (str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;"))

# ---------------------------------------------------------------- dados
def ler_citacoes():
    p=os.path.join(DIR,"citacoes_completas.csv")
    with open(p,encoding="utf-8") as f: return list(csv.DictReader(f,delimiter=";"))

def ler_corpus():
    p=os.path.join(DIR,"corpus_rsl.csv")
    with open(p,encoding="utf-8") as f: return {r["id"]:r for r in csv.DictReader(f,delimiter=";")}

def ler_refs():
    p=os.path.join(DIR,"referencias_distintas.csv")
    with open(p,encoding="utf-8") as f: return {r["chave"]:r for r in csv.DictReader(f,delimiter=";")}

# ---------------------------------------------------------------- rótulos
def rotulo_de_chave(chave, referencia=""):
    """Autor + ano, como o VOSviewer mostra em cocitação."""
    m=re.match(r"^([a-zA-ZÀ-ÿ_\-]+?)((?:19|20)\d{2}[a-z]?|sd)$", chave)
    if m:
        nome,ano=m.group(1),m.group(2)
    else:
        m2=re.search(r"((?:19|20)\d{2})", chave)
        ano=m2.group(1) if m2 else "s.d."
        nome=chave[:m2.start()] if m2 else chave
    nome=nome.replace("_"," ").strip(" -")
    nome=nome[:1].upper()+nome[1:]
    if ano=="sd": ano="s.d."
    return f"{nome}, {ano}"

def ano_de_chave(chave):
    m=re.search(r"((?:19|20)\d{2})", chave)
    return int(m.group(1)) if m else None

# ---------------------------------------------------------------- grafo
def normalizar(pesos, forca):
    """Association strength: s_ij = c_ij * (2m) / (w_i * w_j)."""
    total=sum(pesos.values()) or 1
    s={}
    for (a,b),c in pesos.items():
        wa,wb=forca.get(a,1),forca.get(b,1)
        s[(a,b)]= c*2*total/(wa*wb) if wa and wb else 0.0
    mx=max(s.values()) or 1
    return {k:v/mx for k,v in s.items()}

def vos_layout(nos, sim, iters=3000, seed=42, rep=1.0):
    """Minimiza V(x)=Σ s_ij d_ij² − (2/n) Σ d_ij por descida de gradiente."""
    random.seed(seed); n=len(nos); idx={k:i for i,k in enumerate(nos)}
    pos=[[math.cos(2*math.pi*i/n)+random.uniform(-.15,.15),
          math.sin(2*math.pi*i/n)+random.uniform(-.15,.15)] for i in range(n)]
    S=[[0.0]*n for _ in range(n)]
    for (a,b),v in sim.items():
        if a in idx and b in idx:
            S[idx[a]][idx[b]]=v; S[idx[b]][idx[a]]=v
    lr=0.08
    for it in range(iters):
        gx=[0.0]*n; gy=[0.0]*n
        for i in range(n):
            xi,yi=pos[i]
            for j in range(i+1,n):
                xj,yj=pos[j]; ex,ey=xi-xj,yi-yj
                d=math.hypot(ex,ey) or 1e-6
                # atração ponderada
                a=2.0*S[i][j]
                gx[i]+=a*ex; gy[i]+=a*ey; gx[j]-=a*ex; gy[j]-=a*ey
                # repulsão uniforme (termo −2/n Σ d)
                r=rep*(2.0/n)/d
                gx[i]-=r*ex; gy[i]-=r*ey; gx[j]+=r*ex; gy[j]+=r*ey
        t=lr*(1-0.85*it/iters)
        for i in range(n):
            m=math.hypot(gx[i],gy[i]) or 1e-9
            step=min(m,0.25)/m*t*3.0
            pos[i][0]-=gx[i]*step; pos[i][1]-=gy[i]*step
        # recentrar
        cx=sum(p[0] for p in pos)/n; cy=sum(p[1] for p in pos)/n
        for p in pos: p[0]-=cx; p[1]-=cy
    # rotação por componentes principais: eixo de maior variância na horizontal
    sxx=sum(p[0]*p[0] for p in pos)/n; syy=sum(p[1]*p[1] for p in pos)/n
    sxy=sum(p[0]*p[1] for p in pos)/n
    th=0.5*math.atan2(2*sxy, sxx-syy)
    c,s_=math.cos(-th), math.sin(-th)
    pos=[[p[0]*c-p[1]*s_, p[0]*s_+p[1]*c] for p in pos]
    if sum(p[0]*p[0] for p in pos) < sum(p[1]*p[1] for p in pos):
        pos=[[p[1],-p[0]] for p in pos]
    mx=max(max(abs(p[0]) for p in pos), max(abs(p[1]) for p in pos)) or 1
    return {k:(pos[idx[k]][0]/mx, pos[idx[k]][1]/mx) for k in nos}

def louvain(nos, pesos, seed=42, resolucao=1.0):
    """Modularidade gulosa, um nível com varreduras até estabilizar."""
    random.seed(seed)
    adj=collections.defaultdict(dict)
    for (a,b),w in pesos.items():
        if a==b: continue
        adj[a][b]=adj[a].get(b,0)+w; adj[b][a]=adj[b].get(a,0)+w
    k={u:sum(adj[u].values()) for u in nos}
    m2=sum(k.values()) or 1
    com={u:i for i,u in enumerate(nos)}
    tot={i:k[u] for u,i in com.items()}
    ordem=list(nos); random.shuffle(ordem)
    for _ in range(60):
        mudou=False
        for u in ordem:
            cu=com[u]; ku=k[u]
            tot[cu]-=ku
            liga=collections.Counter()
            for v,w in adj[u].items(): liga[com[v]]+=w
            melhor,ganho=cu,liga[cu]-resolucao*tot.get(cu,0)*ku/m2
            for c,w in liga.items():
                g=w-resolucao*tot.get(c,0)*ku/m2
                if g>ganho+1e-12: melhor,ganho=c,g
            tot[melhor]=tot.get(melhor,0)+ku; com[u]=melhor
            if melhor!=cu: mudou=True
        if not mudou: break
    # renumerar por tamanho
    tam=collections.Counter(com.values())
    ordem_c=[c for c,_ in tam.most_common()]
    ren={c:i for i,c in enumerate(ordem_c)}
    return {u:ren[c] for u,c in com.items()}

# ---------------------------------------------------------------- desenho
def largura_texto(txt, fs):
    return len(txt)*fs*0.56

def desenhar(caminho, nos, pos, peso, cluster, rot, titulo, subtitulo, nota,
             W=1600, H=1080, modo="cluster", ano=None, legenda_clusters=None,
             rodape_fonte=""):
    M=86; TOP=112; BOT=150
    xs=[pos[u][0] for u in nos]; ys=[pos[u][1] for u in nos]
    x0,x1=min(xs),max(xs); y0,y1=min(ys),max(ys)
    sx=(W-2*M)/((x1-x0) or 1); sy=(H-TOP-BOT)/((y1-y0) or 1)
    s=min(sx,sy)*0.94
    ox=M+((W-2*M)-(x1-x0)*s)/2; oy=TOP+((H-TOP-BOT)-(y1-y0)*s)/2
    def T(u):
        x,y=pos[u]; return (ox+(x-x0)*s, oy+((y1-y)-0)*s)
    pmax=max(peso.values()) or 1
    def raio(u): return 4.5+17.0*math.sqrt(peso[u]/pmax)
    def fonte(u): return 10.0+11.0*math.sqrt(peso[u]/pmax)

    # cor
    if modo=="cluster":
        cor=lambda u: PALETA[cluster[u]%len(PALETA)]
    else:
        anos=[ano[u] for u in nos if ano.get(u)]
        amin,amax=min(anos),max(anos)
        def grad(t):
            # paradas ancoradas em anos reais, para diferenciar a faixa densa recente
            def n(a): return (a-amin)/((amax-amin) or 1)
            pts=[(0.0,(43,58,143)),(n(1990),(31,111,176)),(n(2005),(26,145,132)),
                 (n(2015),(141,182,60)),(1.0,(242,202,39))]
            pts=[(max(0.0,min(1.0,a)),c) for a,c in pts]
            for i in range(len(pts)-1):
                a,ca=pts[i]; b,cb=pts[i+1]
                if a<=t<=b:
                    f=(t-a)/(b-a)
                    return tuple(round(ca[j]+(cb[j]-ca[j])*f) for j in range(3))
            return pts[-1][1]
        def cor(u):
            a=ano.get(u)
            if not a: return "#b9b9b9"
            t=(a-amin)/((amax-amin) or 1)
            r,g,b=grad(t); return f"#{r:02x}{g:02x}{b:02x}"

    o=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
       '<style>text{font-family:Aptos,Calibri,"Segoe UI",Helvetica,Arial,sans-serif}</style>']
    o.append(f'<text x="{M}" y="48" font-size="23" font-weight="700" fill="#111111">{esc(titulo)}</text>')
    o.append(f'<text x="{M}" y="74" font-size="13.5" fill="#555555">{esc(subtitulo)}</text>')

    # arestas — bezier com leve arco, como o VOSviewer
    ares=sorted(((k,v) for k,v in SIM_GLOBAL.items() if k[0] in peso and k[1] in peso),
                key=lambda kv: kv[1])
    smax=max((v for _,v in ares), default=1)
    for (a,b),v in ares:
        (xa,ya),(xb,yb)=T(a),T(b)
        mxp,myp=(xa+xb)/2,(ya+yb)/2
        dx,dy=xb-xa,yb-ya; L=math.hypot(dx,dy) or 1
        cxp,cyp=mxp-dy/L*L*0.07, myp+dx/L*L*0.07
        t=v/smax
        sw=0.6+3.2*t
        op=0.22+0.50*t
        col=cor(a) if modo=="cluster" else "#9aa7b4"
        o.append(f'<path d="M{xa:.1f},{ya:.1f} Q{cxp:.1f},{cyp:.1f} {xb:.1f},{yb:.1f}" fill="none" stroke="{col}" stroke-width="{sw:.2f}" opacity="{op:.2f}"/>')

    # nós
    for u in sorted(nos,key=lambda z:peso[z]):
        x,y=T(u); r=raio(u)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{cor(u)}" fill-opacity="0.62" stroke="{cor(u)}" stroke-opacity="0.85" stroke-width="1.0"/>')

    # rótulos com supressão de sobreposição
    caixas=[]
    def cabe(bx):
        for c in caixas:
            if not (bx[2]<c[0] or bx[0]>c[2] or bx[3]<c[1] or bx[1]>c[3]): return False
        return True
    for u in sorted(nos,key=lambda z:-peso[z]):
        x,y=T(u); fs=fonte(u); txt=rot[u]
        w=largura_texto(txt,fs); h=fs*1.15
        bx=(x-w/2-6, y-h/2-4, x+w/2+6, y+h/2+4)
        if not cabe(bx): continue
        caixas.append(bx)
        yy=y+fs*0.35
        o.append(f'<text x="{x:.1f}" y="{yy:.1f}" font-size="{fs:.1f}" font-weight="600" '
                 f'text-anchor="middle" fill="none" stroke="#ffffff" stroke-width="{max(2.0,fs*0.30):.1f}" '
                 f'stroke-linejoin="round" opacity="0.92">{esc(txt)}</text>')
        o.append(f'<text x="{x:.1f}" y="{yy:.1f}" font-size="{fs:.1f}" font-weight="600" '
                 f'text-anchor="middle" fill="#1a1a1a">{esc(txt)}</text>')

    # legenda
    ly=H-BOT+30; lx=M
    if modo=="cluster" and legenda_clusters:
        o.append(f'<text x="{lx}" y="{ly-16}" font-size="12" font-weight="700" fill="#333333">agrupamentos (modularidade)</text>')
        for ci,nome in legenda_clusters:
            c=PALETA[ci%len(PALETA)]
            o.append(f'<circle cx="{lx+7}" cy="{ly}" r="7" fill="{c}" fill-opacity="0.85" stroke="#ffffff" stroke-width="1.2"/>')
            o.append(f'<text x="{lx+20}" y="{ly+4.5}" font-size="11.5" fill="#333333">{esc(nome)}</text>')
            lx+=largura_texto(nome,11.5)+40
            if lx>W-300: lx=M; ly+=22
    elif modo=="ano":
        anos=[ano[u] for u in nos if ano.get(u)]
        amin,amax=min(anos),max(anos)
        bw,bh=300,13
        o.append(f'<text x="{M}" y="{ly-16}" font-size="12" font-weight="700" fill="#333333">ano da referência</text>')
        def _n(a): return max(0.0,min(1.0,(a-amin)/((amax-amin) or 1)))
        paradas=[(0.0,"#2b3a8f"),(_n(1990),"#1f6fb0"),(_n(2005),"#1a9184"),
                 (_n(2015),"#8db63c"),(1.0,"#f2ca27")]
        stops="".join(f'<stop offset="{a:.4f}" stop-color="{c}"/>' for a,c in paradas)
        o.append(f'<defs><linearGradient id="g" x1="0" x2="1">{stops}</linearGradient></defs>')
        o.append(f'<rect x="{M}" y="{ly-6}" width="{bw}" height="{bh}" fill="url(#g)" stroke="#cccccc" stroke-width="0.8"/>')
        for k in range(5):
            v=amin+(amax-amin)*k/4; xx=M+bw*k/4
            o.append(f'<text x="{xx:.0f}" y="{ly+bh+14}" font-size="10.5" text-anchor="middle" fill="#555555">{int(round(v))}</text>')
        o.append(f'<circle cx="{M+bw+40}" cy="{ly}" r="7" fill="#b9b9b9" fill-opacity="0.85" stroke="#ffffff" stroke-width="1.2"/>')
        o.append(f'<text x="{M+bw+54}" y="{ly+4.5}" font-size="11.5" fill="#333333">sem ano identificado</text>')

    o.append(f'<text x="{M}" y="{H-32}" font-size="10.5" fill="#6a6a6a">{esc(nota)}</text>')
    if rodape_fonte:
        o.append(f'<text x="{M}" y="{H-14}" font-size="10.5" fill="#6a6a6a">{esc(rodape_fonte)}</text>')
    o.append('</svg>')
    open(caminho,"w",encoding="utf-8", newline="\n").write("\n".join(o))
    print("gravado:", os.path.basename(caminho), len(nos),"nós")

SIM_GLOBAL={}

# ---------------------------------------------------------------- montagens
def rede_cocitacao(minimo=2):
    cc=ler_citacoes(); refs=ler_refs()
    por=collections.defaultdict(set)          # item do corpus -> refs externas
    for r in cc:
        if r["tipo"]=="externo": por[r["id_origem"]].add(r["chave_citada"])
    cita=collections.Counter()                 # ref -> nº de itens que a citam
    for it,ch in por.items():
        for c in ch: cita[c]+=1
    nos=sorted([c for c,v in cita.items() if v>=minimo], key=lambda c:(-cita[c],c))
    sn=set(nos)
    pesos=collections.Counter()
    for it,ch in por.items():
        loc=sorted(ch & sn)
        for i in range(len(loc)):
            for j in range(i+1,len(loc)):
                pesos[(loc[i],loc[j])]+=1
    # manter só o componente gigante
    adj=collections.defaultdict(set)
    for a,b in pesos: adj[a].add(b); adj[b].add(a)
    vistos=set(); comps=[]
    for u in nos:
        if u in vistos: continue
        pil=[u]; comp=set()
        while pil:
            v=pil.pop()
            if v in comp: continue
            comp.add(v); vistos.add(v); pil.extend(adj[v]-comp)
        comps.append(comp)
    gigante=max(comps,key=len) if comps else set()
    nos=[u for u in nos if u in gigante]; sn=set(nos)
    pesos={k:v for k,v in pesos.items() if k[0] in sn and k[1] in sn}
    forca=collections.Counter()
    for (a,b),w in pesos.items(): forca[a]+=w; forca[b]+=w
    peso={u:cita[u] for u in nos}
    rot={u:rotulo_de_chave(u, refs.get(u,{}).get("referencia","")) for u in nos}
    ano={u:ano_de_chave(u) for u in nos}
    return nos,pesos,forca,peso,rot,ano,len(comps),len(por)

def rede_interna():
    cc=ler_citacoes(); corpus=ler_corpus()
    pares=collections.Counter()
    for r in cc:
        if r["tipo"]=="interno" and r["id_corpus_citado"]:
            a,b=r["id_origem"],r["id_corpus_citado"]
            if a!=b: pares[tuple(sorted((a,b),key=int))]+=1
    grau=collections.Counter()
    for (a,b),w in pares.items(): grau[a]+=w; grau[b]+=w
    nos=[i for i in sorted(corpus,key=int) if grau[i]>0]
    sn=set(nos); pares={k:v for k,v in pares.items() if k[0] in sn and k[1] in sn}
    rot={}
    for i in nos:
        aut=corpus[i]["autores"].strip('" ').split(";")[0].strip()
        aut=aut.split(",")[0].strip()
        rot[i]=f"{aut}, {corpus[i]['ano']}"
    ano={i:int(corpus[i]["ano"]) for i in nos}
    return nos,pares,grau,dict(grau),rot,ano,corpus

if __name__=="__main__":
    os.makedirs(OUT,exist_ok=True)

    # ---------- 1. cocitação de referências
    nos,pesos,forca,peso,rot,ano,ncomp,nitens=rede_cocitacao(minimo=2)
    sim=normalizar(pesos,forca); SIM_GLOBAL.clear(); SIM_GLOBAL.update(sim)
    pos=vos_layout(nos,sim,iters=2600,rep=9.0)
    cl=louvain(nos,pesos)
    tam=collections.Counter(cl.values())
    # nomear clusters pelo nó de maior peso
    nomes=[]
    for ci,_ in tam.most_common():
        top=max([u for u in nos if cl[u]==ci], key=lambda z:peso[z])
        nomes.append((ci,f"{len(nomes)+1} — {rot[top]} · {tam[ci]} refs"))
    desenhar(os.path.join(OUT,"Rede de cocitacao de referencias - RSL (set-2026).svg"),
        nos,pos,peso,cl,rot,
        "Rede de cocitação de referências — corpus da RSL",
        f"{len(nos)} referências cocitadas por ao menos 2 dos {nitens} itens com referências extraídas (de 43 no corpus) · aresta = cocitação · tamanho = nº de itens que citam · cor = agrupamento",
        "Técnica de mapeamento e normalização por força de associação (van Eck & Waltman); agrupamento por modularidade. Rótulos suprimidos onde haveria sobreposição.",
        legenda_clusters=nomes,
        rodape_fonte="Fonte: elaboração do autor a partir das referências extraídas dos itens do corpus (2026).")

    desenhar(os.path.join(OUT,"Rede de cocitacao de referencias - sobreposicao temporal (set-2026).svg"),
        nos,pos,peso,cl,rot,
        "Rede de cocitação de referências — sobreposição temporal",
        f"mesma rede, colorida pelo ano da referência citada · {len(nos)} referências · tamanho = nº de itens do corpus que citam",
        "A base intelectual mais citada é recente; os nós escuros marcam a produção anterior que o campo cita pouco.",
        modo="ano", ano=ano,
        rodape_fonte="Fonte: elaboração do autor a partir das referências extraídas dos itens do corpus (2026).")

    # ---------- 2. citações internas
    nos2,pares2,forca2,peso2,rot2,ano2,corpus=rede_interna()
    sim2=normalizar(pares2,forca2); SIM_GLOBAL.clear(); SIM_GLOBAL.update(sim2)
    pos2=vos_layout(nos2,sim2,iters=2600,seed=7,rep=14.0)
    cl2=louvain(nos2,pares2,seed=7,resolucao=0.45)
    tam2=collections.Counter(cl2.values()); nomes2=[]
    for ci,_ in tam2.most_common():
        top=max([u for u in nos2 if cl2[u]==ci], key=lambda z:peso2[z])
        nomes2.append((ci,f"{len(nomes2)+1} — {rot2[top]} · {tam2[ci]} itens"))
    isolados=len(corpus)-len(nos2)
    desenhar(os.path.join(OUT,"Rede de citacoes internas do corpus - RSL (set-2026).svg"),
        nos2,pos2,peso2,cl2,rot2,
        "Rede de citações internas do corpus — RSL",
        f"{len(nos2)} dos {len(corpus)} itens estão conectados · aresta = um item do corpus cita outro · tamanho = grau · cor = agrupamento",
        f"{isolados} itens não citam nem são citados por outro item do corpus e por isso não aparecem. Arestas só existem entre itens já fichados.",
        legenda_clusters=nomes2, W=1500, H=1000,
        rodape_fonte="Fonte: elaboração do autor a partir dos fichamentos do corpus (2026).")
