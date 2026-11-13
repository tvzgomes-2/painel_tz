# -*- coding: utf-8 -*-
"""rsl_inventario.py — cruza corpus_rsl.csv com o Zotero, o disco, os textos e as fichas.
Substitui a dupla rsl_inventario.py + rsl_fichas.py (que colidiam em fieldnames).
Escreve so depois de validar em memoria; nunca abre o destino em 'w' antes disso."""
import json,os,csv,re,io,glob,unicodedata,collections
H=os.path.expanduser("~"); V=os.path.join(H,"mnt","doutorado")
Z=json.load(open(os.path.join(H,"rsl","zotero.json"),encoding="utf-8"))
CORP=os.path.join(V,"05 - Referências","Rede bibliométrica","corpus_rsl.csv")
TX=os.path.join(V,"_meta","textos_rsl")
FI=os.path.join(V,"05 - Referências","Notas de leitura")
SAIDA=os.path.join(H,"rsl","inventario_rsl.csv")

# 🔒 casamentos revisados a mao — a trava de titulo sozinha erra (6 falsos positivos em 08/09)
OVER={"108":(57,"cap. II de Viacao Ilimitada; duplicata it1628 a mesclar"),
      "73":(None,"editorial RTP 134 — sem item no Zotero (match por titulo era falso positivo)"),
      "77":(None,"Forum Paulista 60a — sem item (idem)"),
      "80":(None,"TCRP Synthesis 101 — sem item (idem)"),
      "93":(None,"sem item (idem)"),
      "34":(112,"A CONFERIR: casa com keblowski2025; titulo do CSV parece de trabalho"),
      "26":(1957,"A CONFERIR: it1957 pode ser a dissertacao ou o artigo"),
      "16":(None,"dossie DSA23 — sem item"),
      "19":(None,"dossie DSA23 — sem item")}

def norm(s):
    s=unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode()
    return re.sub(r"[^a-z0-9 ]"," ",s.lower())
STOP=set("a o as os de da do das dos e em no na nos nas um uma para por com sem sobre fichamento cotejo lote the of and in on for to at an la le les el los des du".split())
def tk(s): return {w for w in norm(s).split() if len(w)>2 and w not in STOP}
def sob(a,b):
    A,B=tk(a),tk(b); return len(A&B)/min(len(A),len(B)) if A and B else 0.0
def sn(s):
    out=set()
    for p in re.split(r"[;|,]| e | and |et al",s or ""):
        for w in norm(p).split():
            if len(w)>3 and w not in STOP: out.add(w)
    return out

zbyck=collections.defaultdict(list)
for z in Z:
    if z["citekey"]: zbyck[z["citekey"].lower()].append(z)
zbyid={z["itemID"]:z for z in Z}

with io.open(CORP,encoding="utf-8-sig",newline="") as f:
    rows=list(csv.DictReader(f,delimiter=";"))
txt={m.group(1):os.path.getsize(os.path.join(TX,f)) for f in os.listdir(TX)
     for m in [re.match(r"^(\d+)\.txt$",f)] if m}

fichas=[]
for f in sorted(glob.glob(os.path.join(FI,"*.md"))):
    b=os.path.basename(f); s=io.open(f,encoding="utf-8",errors="replace").read(7000)
    m=re.search(r"^rsl_id:[ \t]*(\d+)",s,re.M)
    fichas.append({"arq":b,"rid":m.group(1) if m else "",
                   "anos":set(re.findall(r"(19\d\d|20\d\d)",b)),"tk":tk(b),"sn":sn(b.split("(")[0])})
vinc={a["rid"]:a["arq"] for a in fichas if a["rid"]}
livres=[a for a in fichas if not a["rid"]]

COLS=["id","ano","autores","obra","estrato","estado_csv","motivo_exclusao","chaves_csv",
      "zot_item","zot_key","zot_citekey","zot_titulo","zot_ano","match_via","match_conf",
      "tem_item","tem_arquivo","n_anexos","anexo_em_disco","tem_texto","bytes_texto",
      "tem_ficha","ficha","ficha_vinculo","ficha_score","situacao_arquivo","situacao_ficha",
      "alt_candidatos","nota_manual"]
res=[]
for r in rows:
    rid=r["id"]
    cand=[];via="";conf="";nota=""
    for k in [x.strip().lower() for x in (r["chaves_alternativas"] or "").split(",") if x.strip()]:
        for z in zbyck.get(k,[]):
            if z not in cand: cand.append(z); via="citekey"; conf="alta"
    if not cand:
        ti,an,au=r["referencia_curta"],r["ano"],sn(r["autores"]); best=[]
        for z in Z:
            s=sob(ti,z["titulo"])
            if s<0.34: continue
            yr = an and z["ano"] and abs(int(an)-int(z["ano"]))<=1
            aov = bool(au & sn(z["autores"])) if (au and z["autores"]) else None
            lvl = ("alta" if (s>=0.80 and aov is not False) or (s>=0.55 and yr and aov is not False)
                   else "media" if (s>=0.50 and (yr or aov)) or (s>=0.34 and yr and aov) else "baixa")
            best.append((s+(0.15 if yr else 0)+(0.15 if aov else 0),lvl,z))
        best.sort(key=lambda x:-x[0])
        if best: cand=[b[2] for b in best[:3]]; conf=best[0][1]; via="titulo"
    if rid in OVER:
        iid,nota=OVER[rid]; via="revisado_a_mao"
        cand=[zbyid[iid]] if (iid and iid in zbyid) else []
        conf="media" if "CONFERIR" in nota else "alta"
    z0=cand[0] if cand else None
    # ficha
    if rid in vinc: sf,fv,fs="fichada e vinculada",vinc[rid],""
    else:
        sc=[]
        for a in livres:
            aov=len(sn(r["autores"]) & a["sn"]); yr=r["ano"] in a["anos"]
            tov=len(tk(r["referencia_curta"]) & a["tk"])/max(1,min(len(tk(r["referencia_curta"])),len(a["tk"])))
            s=(0.60+0.10*min(aov,3)+0.20*tov if aov and yr else
               0.30+0.08*min(aov,3)+0.20*tov if aov else
               0.40+0.20*tov if yr and tov>=0.5 else
               0.35+0.20*tov if tov>=0.7 else 0.0)
            if s>0: sc.append((s,a["arq"]))
        sc.sort(key=lambda t:-t[0])
        fv=sc[0][1] if sc else ""; fs=f"{sc[0][0]:.2f}" if sc else ""
        sf=("ficha existe, falta rsl_id" if sc and sc[0][0]>=0.75 else
            "candidata a conferir" if sc and sc[0][0]>=0.50 else "sem ficha")
    a_=bool(z0 and z0["n_anexos_ok"]); t_=rid in txt; i_=bool(z0)
    sa=("SEM ITEM no Zotero"+(" (mas ha texto extraido)" if t_ else " e sem arquivo") if not i_ else
        "ok" if a_ and t_ else
        "arquivo ok, falta extrair texto" if a_ else
        "item ok, arquivo ausente do storage (ha texto)" if t_ else
        "item ok, SEM arquivo e sem texto — BUSCAR")
    res.append({"id":rid,"ano":r["ano"],"autores":r["autores"],"obra":r["referencia_curta"],
        "estrato":r["estrato"],"estado_csv":r["estado"],"motivo_exclusao":r["motivo_exclusao"],
        "chaves_csv":r["chaves_alternativas"],
        "zot_item":z0["itemID"] if z0 else "","zot_key":z0["key"] if z0 else "",
        "zot_citekey":z0["citekey"] if z0 else "","zot_titulo":z0["titulo"] if z0 else "",
        "zot_ano":z0["ano"] if z0 else "","match_via":via,"match_conf":conf,
        "tem_item":"sim" if i_ else "NAO","tem_arquivo":"sim" if a_ else "NAO",
        "n_anexos":z0["n_anexos"] if z0 else 0,"anexo_em_disco":z0["n_anexos_ok"] if z0 else 0,
        "tem_texto":"sim" if t_ else "NAO","bytes_texto":txt.get(rid,0),
        "tem_ficha":"sim" if rid in vinc else "NAO","ficha":vinc.get(rid,""),
        "ficha_vinculo":fv,"ficha_score":fs,"situacao_arquivo":sa,"situacao_ficha":sf,
        "alt_candidatos":" || ".join(f'{z["itemID"]}:{z["titulo"][:60]}' for z in cand[1:3]),
        "nota_manual":nota})

buf=io.StringIO(); w=csv.DictWriter(buf,fieldnames=COLS,delimiter=";",lineterminator="\r\n")
w.writeheader(); w.writerows(res)
chk=list(csv.DictReader(io.StringIO(buf.getvalue()),delimiter=";"))
assert len(chk)==len(rows) and len(chk[0])==len(COLS),(len(chk),len(rows))
with io.open(SAIDA,"w",encoding="utf-8-sig",newline="") as f: f.write(buf.getvalue())

def C(k): return collections.Counter(x[k] for x in res)
print(f"linhas: {len(res)}  ->  {SAIDA}")
print("== SITUACAO DO ARQUIVO");  [print(f"  {v:>4}  {k}") for k,v in C("situacao_arquivo").most_common()]
print("== SITUACAO DA FICHA");    [print(f"  {v:>4}  {k}") for k,v in C("situacao_ficha").most_common()]
print("== VIA DO CASAMENTO");     [print(f"  {v:>4}  {k}") for k,v in C("match_via").most_common()]
falta=[x for x in res if x["tem_arquivo"]!="sim"]
print("\nSEM ARQUIVO ("+str(len(falta))+"):", ", ".join(x["id"] for x in falta))
print("  destes, sem texto:", ", ".join(x["id"] for x in falta if x["tem_texto"]!="sim") or "(nenhum)")
print("EXTRAIR TEXTO (arquivo em disco):", ", ".join(x["id"] for x in res if x["situacao_arquivo"].startswith("arquivo ok")) or "(nenhum)")
print("SEM FICHA:", ", ".join(x["id"] for x in res if x["situacao_ficha"]=="sem ficha") or "(nenhum)")
