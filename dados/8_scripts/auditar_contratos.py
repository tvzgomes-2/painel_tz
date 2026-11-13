"""Auditoria do acervo de contratos e instrumentos (read-only).

Confere, para cada arquivo em `03 - Dados/_data/Legislacao e contratos TZ/contratos/<UF>/`:
  1. nome no padrão `Município-UF - Instrumento nº-ano (data) - assunto.ext` e pasta = UF do nome;
  2. tipo do instrumento (contrato, aditivo/apostilamento, edital/licitação, ETP/TR,
     homologação/ata, dispensa, publicação em DO, export de portal, notícia/página, outro);
  3. camada de texto (PDF escaneado precisa de OCR irmão `… - OCR.txt`);
  4. caso: escopo (base-mestre), régua fora do escopo ou órfão;
  5. fichamento: citado pelo nome em nota do cofre, ou o nº do instrumento / data do nome
     aparece no bloco do município no log ou na ficha, ou ≥2 palavras distintivas do nome
     (empresa, nº de empenho, tema) aparecem no bloco — este último é indício fraco, conferir;
  6. base-mestre: o caso tem `Operador`, `Remuneração do operador` e `Trajetória contratual` preenchidos?
Com --extrair DIR grava, por documento, o texto extraído e um resumo de trechos-chave
(objeto, contratada, valor, vigência, tarifa/gratuidade) em DIR/<UF>/<arquivo>.txt.

Uso: python auditar_contratos.py [--report] [--extrair DIR] [--budget SEG] [--json ARQ]
(o texto extraído fica em cache em ~/.ctx_cache; com --budget, rodar de novo até concluir)
"""
import os,re,sys,hashlib,subprocess,unicodedata,datetime,collections,zipfile,csv,io,html as H
import openpyxl
V=os.environ.get("TZ_VAULT") or os.path.expanduser("~/mnt/doutorado"); os.chdir(V)
BASE="03 - Dados/_data/Legislacao e contratos TZ"; CON=f"{BASE}/contratos"; NOR=f"{BASE}/normas"
LOG="04 - Análises/Pesquisa legal/Log de busca jurídica e contratual — municípios.md"
FD="04 - Análises/Casos municipais/Fichas por município"
MP="03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx"; RP="03 - Dados/_data/casos por fonte/Tipologias TZ - consolidado.xlsx"
def nz(s): return unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().lower().strip()
def md5(p):
    h=hashlib.md5()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
mr=list(openpyxl.load_workbook(MP,read_only=True)["consolidado"].iter_rows(values_only=True)); MH=mr[0]
iS=MH.index("Situação"); iO=MH.index("Operador"); iR=MH.index("Remuneração do operador"); iT=MH.index("Trajetória contratual")
ESC={(nz(r[0]),r[1]):r for r in mr[1:] if r[0] and r[iS] not in ("Excluída","Reclassificada",None)}
REG=set()
for ws in openpyxl.load_workbook(RP,read_only=True).worksheets:
    for r in ws.iter_rows(min_row=2,values_only=True):
        if r and r[0] and r[1] and len(str(r[1]))==2: REG.add((nz(r[0]),r[1]))
log=open(LOG,encoding="utf-8").read(); blocos={}
for b in re.split(r"\n(?=#### )",log):
    m=re.match(r"#### (.+) \(([A-Z]{2})\)",b)
    if m: blocos[(nz(m.group(1)),m.group(2))]=b
fichas={}
for f in os.listdir(FD):
    m=re.match(r"Ficha - (.+) \(([A-Z]{2})\)\.md$",f)
    if m: fichas[(nz(m.group(1)),m.group(2))]=open(os.path.join(FD,f),encoding="utf-8").read()
parts=[]
for d,ds,fs in os.walk("."):
    if d.startswith("./_meta") or "/." in d or "07 - Disciplinas" in d: continue
    for f in fs:
        if f.endswith(".md"):
            try: parts.append(open(os.path.join(d,f),encoding="utf-8").read())
            except Exception: pass
corpus="\n".join(parts); corpus_n=nz(corpus)
PAT=re.compile(r"^(?P<mun>.+?)-(?P<uf>[A-Z]{2}) - (?P<rest>.+)$")
STOP=set("""portal transparencia contrato contratos edital prefeitura municipal municipio transporte coletivo gratuito gratuita publico publica urbano urbana
termo aditivo noticia pagina oficial export autor utf8 digitalizado pncp processo pregao eletronico presencial licitacao dispensa emergencial servicos servico
passageiros onibus locacao linhas linha tarifa contratacao empresa transportes viacao parte versao detalhe pdf""".split())
CAND=set()
for q in ("04 - Análises/Pesquisa legal/Busca ativa — MUNIC declara TZ, fora da base — resultado (25-09-2026).md","04 - Análises/Achados - TZ não mapeada (verificação dos 141 candidatos).md","04 - Análises/Monitoramento - Candidatos indeterminados (TZ não mapeada).md"):
    if os.path.exists(q): CAND|=set(nz(m) for m in re.findall(r"\*\*([^*/]+?)/[A-Z]{2}\*\*",open(q,encoding="utf-8").read()))
NUM=re.compile(r"(?<![\d.])(\d{1,9}(?:\.\d{3})*)-(\d{4})(?!\d)")
DAT=re.compile(r"(?<!\d)(\d{2})-(\d{2})-(\d{4})(?!\d)")
def tipo(rest):
    r=nz(rest)
    for k,t in (("termo aditivo","aditivo/apostilamento"),("aditivo","aditivo/apostilamento"),("apostil","aditivo/apostilamento"),("aditamento","aditivo/apostilamento"),
                ("resolucao contratual","aditivo/apostilamento"),("distrato","aditivo/apostilamento"),
                ("contrato","contrato"),("homolog","homologação/ata/adjudicação"),("adjudica","homologação/ata/adjudicação"),("ata ","homologação/ata/adjudicação"),
                ("ratifica","homologação/ata/adjudicação"),("etp","ETP/TR/DOD"),("termo de referencia","ETP/TR/DOD"),("estudo tecnico","ETP/TR/DOD"),(" tr ","ETP/TR/DOD"),("dod","ETP/TR/DOD"),
                ("mapa de riscos","ETP/TR/DOD"),("edital","edital/licitação"),("pregao","edital/licitação"),("concorrencia","edital/licitação"),("pe ","edital/licitação"),("pp ","edital/licitação"),
                ("dispensa","dispensa/inexigibilidade"),("inexigib","dispensa/inexigibilidade"),("portal","export de portal"),("siconfi","export de portal"),("lai ","resposta LAI"),
                ("dom","publicação em DO"),("do ","publicação em DO"),("diario","publicação em DO"),("noticia","notícia/página oficial"),("prefeitura","notícia/página oficial"),
                ("pagina","notícia/página oficial"),("site","notícia/página oficial"),("horario","horários/itinerários"),("itinerario","horários/itinerários"),("cartaz","horários/itinerários")):
        if (" "+r+" ").find(k if k.startswith(" ") or k.endswith(" ") else k)>=0: return t
    return "outro"
def pdftext(p,l=None):
    a=["pdftotext","-l","40",p,"-"] if l is None else ["pdftotext","-l",str(l),p,"-"]
    try: return subprocess.run(a,capture_output=True,timeout=60).stdout.decode("utf-8","ignore")
    except Exception: return ""
CACHE=os.environ.get("CTX_CACHE") or os.path.expanduser("~/.ctx_cache")
def texto(p,ext,pd,stem):
    os.makedirs(CACHE,exist_ok=True); cp=os.path.join(CACHE,hashlib.md5((p+str(os.path.getmtime(p))).encode()).hexdigest())
    if os.path.exists(cp):
        a=open(cp,encoding="utf-8").read(); i=a.index("\n"); return a[:i],a[i+1:]
    if DEADLINE and datetime.datetime.now()>DEADLINE: raise TimeoutError
    st,t=_texto(p,ext,pd,stem)
    open(cp,"w",encoding="utf-8").write(st+"\n"+t); return st,t
def _texto(p,ext,pd,stem):
    if ext=="pdf":
        t=pdftext(p)
        if len(t.strip())<200:
            ir=[g for g in os.listdir(pd) if "OCR" in g and g.endswith(".txt") and (g.startswith(stem[:40]) or (len(re.sub(r" - OCR.*$","",g))>=25 and stem.startswith(re.sub(r" - OCR.*$","",g))))]
            if ir: return "escaneado c/ OCR",open(os.path.join(pd,ir[0]),encoding="utf-8",errors="ignore").read()
            return "escaneado SEM OCR",t
        return "ok",t
    if ext in("txt","csv","json","xml"): return "ok",open(p,encoding="utf-8",errors="ignore").read()
    if ext=="html":
        t=open(p,encoding="utf-8",errors="ignore").read(); t=re.sub(r"(?is)<(script|style).*?</\1>"," ",t)
        return "ok",H.unescape(re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",t)))
    if ext=="docx":
        try:
            import docx; d=docx.Document(p); return "ok","\n".join(x.text for x in d.paragraphs)+"\n".join(c.text for tb in d.tables for rw in tb.rows for c in rw.cells)
        except Exception as e: return "erro docx",""
    if ext in("xlsx",):
        try:
            wb=openpyxl.load_workbook(p,read_only=True,data_only=True); out=[]
            for ws in wb.worksheets:
                for i,r in enumerate(ws.iter_rows(values_only=True)):
                    if i>200: break
                    out.append(" | ".join(str(x) for x in r if x is not None))
            return "ok","\n".join(out)
        except Exception: return "erro xlsx",""
    if ext=="zip":
        cp=os.path.join(pd,stem+" - texto.txt")
        if os.path.exists(cp): return "zip c/ texto extraído",open(cp,encoding="utf-8",errors="ignore").read()
        try: return "zip (lista)","\n".join(zipfile.ZipFile(p).namelist())
        except Exception: return "erro zip",""
    if ext in("png","jpg","jpeg"): return "imagem",""
    if ext in("doc","xls","rar"):
        cp=os.path.join(pd,stem+" - texto.txt")
        if os.path.exists(cp): return f"{ext} c/ texto extraído",open(cp,encoding="utf-8",errors="ignore").read()
        return f"{ext} (sem extrator no device)",""
    return "?",""
KW=[("objeto",r"objeto[^\n]{0,8}[:\-–]?\s*(.{0,260})"),("contratad",r"contratad[ao]\s*[:\-–]\s*(.{0,160})"),
    ("valor",r"(R\$\s?[\d.]{1,15},\d{2}(?:[^\n]{0,80}))"),("vigência",r"vig[êe]ncia[^\n]{0,200}"),
    ("tarifa/gratuidade",r"[^\n]{0,140}(?:gratuit|tarifa zero|sem cobran|n[ãa]o (?:ser[áa]|haver[áa]) cobran|vedad[ao] a cobran|tarifa p[úu]blica zero|isen[çc][ãa]o tarif|passe livre)[^\n]{0,140}"),
    ("tarifa (cobrança)",r"[^\n]{0,100}(?:valor da tarifa|tarifa de R\$|tarifa (?:no valor|fixada)|cobran[çc]a de tarifa|venda de cr[ée]ditos)[^\n]{0,120}"),
    ("lei citada",r"Lei (?:Municipal |Complementar |Ordin[áa]ria )?(?:n[º°.o]*\s*)?[\d.]+/\d{4}")]
def trechos(t):
    o=[]
    for k,rx in KW:
        ms=[re.sub(r"\s+"," ",m.group(0)).strip() for m in re.finditer(rx,t,re.I)]
        seen=[]; 
        for x in ms:
            if x not in seen: seen.append(x)
        if seen: o.append(f"[{k}] "+" ‖ ".join(seen[:3 if k!='lei citada' else 8])[:900])
    return o
def num_pats(n,a):
    s=n.replace(".","").lstrip("0") or "0"; f=f"{int(s):,}".replace(",",".")
    return {f"{n}/{a}",f"{s}/{a}",f"{f}/{a}",f"0{s}/{a}",f"00{s}/{a}",f"{s}-{a}",f"{n}-{a}"}
ext_dir=sys.argv[sys.argv.index("--extrair")+1] if "--extrair" in sys.argv else None
DEADLINE=datetime.datetime.now()+datetime.timedelta(seconds=int(sys.argv[sys.argv.index("--budget")+1])) if "--budget" in sys.argv else None
rows=[]; byhash=collections.defaultdict(list)
for uf in sorted(os.listdir(CON)):
    pd=os.path.join(CON,uf)
    if not os.path.isdir(pd): continue
    for d,_,fs in os.walk(pd):
        for f in sorted(fs):
            p=os.path.join(d,f); stem,ext=os.path.splitext(f); ext=ext.lower().lstrip(".")
            if ext=="txt" and ("OCR" in stem or stem.endswith(" - texto")): continue  # companheiros (OCR/extração), não são documentos próprios
            h=md5(p); byhash[h].append(p)
            m=PAT.match(stem if d==pd else os.path.basename(d)); prob=[]
            mun,muf,rest=(m.group("mun"),m.group("uf"),m.group("rest")) if m else (None,None,stem)
            if not m: prob.append("nome fora do padrão")
            elif muf!=uf: prob.append(f"UF do nome ({muf}) ≠ pasta ({uf})")
            if d!=pd: prob.append("em subpasta")
            k=(nz(mun),muf) if mun else None
            caso="escopo" if k in ESC else ("régua (fora do escopo)" if k in REG else ("candidato (busca ativa/achados)" if mun and nz(mun) in CAND else "órfão"))
            txt,t=texto(p,ext,d,stem)
            reg="NÃO FICHADO"
            blk=(blocos.get(k,"")+"\n"+fichas.get(k,"")) if k else ""
            if f in corpus or stem in corpus or nz(stem)[:60] in corpus_n: reg="citado pelo nome"
            else:
                nums=NUM.findall(rest); dats=DAT.findall(rest)
                if any(any(q in blk for q in num_pats(n,a)) for n,a in nums): reg="nº citado no log/ficha"
                elif any(f"{a}/{b}/{c}" in blk for a,b,c in dats): reg="data citada no log/ficha"
                elif blk and sum(1 for w in set(re.findall(r"[a-z0-9]{5,}",nz(rest))) if w not in STOP and w in nz(blk))>=2: reg="assunto citado no log/ficha (palavras-chave)"
                elif not blocos.get(k): reg="NÃO FICHADO (sem bloco no log)"
            tr=trechos(t) if t else []
            if ext_dir:
                od=os.path.join(ext_dir,uf); os.makedirs(od,exist_ok=True)
                with open(os.path.join(od,f+".txt"),"w",encoding="utf-8") as g:
                    g.write(f"### {f}\ntexto: {txt} · {len(t)} chars · caso {caso} · {reg}\n"+"\n".join(tr)+"\n\n--- início ---\n"+re.sub(r"[ \t]+"," ",t[:1500])+"\n")
            rows.append(dict(uf=uf,arq=f,ext=ext,mun=mun,k=k,caso=caso,tipo=tipo(rest),txt=txt,nch=len(t),reg=reg,prob=prob,trechos=tr))
dup=[(h,ps) for h,ps in byhash.items() if len(ps)>1]
nmd5={}
for d,_,fs in os.walk(NOR):
    for f in fs: nmd5.setdefault(md5(os.path.join(d,f)),[]).append(f)
dupn=[(r["arq"],nmd5[h]) for h,ps in byhash.items() for r in rows if h in nmd5 and any(r["arq"]==os.path.basename(p) for p in ps)]
porm=collections.defaultdict(list)
for r in rows:
    if r["k"]: porm[r["k"]].append(r)
mest=[]
for k,L in sorted(porm.items()):
    if k in ESC:
        e=ESC[k]; mest.append((e[0],e[1],len(L),sum(1 for r in L if r["reg"].startswith("NÃO")),*(("✓" if (e[i] and str(e[i]).strip() not in ("","—","-")) else "vazio") for i in (iO,iR,iT))))
C=lambda key: collections.Counter(r[key] for r in rows)
out=[f"# Auditoria do acervo de contratos e instrumentos — {datetime.date.today():%d/%m/%Y}","",
f"Gerado por `_meta/scripts/auditar_contratos.py` (read-only). Documentos em `contratos/` (sem os OCR irmãos): **{len(rows)}** de **{len(porm)}** municípios.","",
"## Resumo","",f"- Caso: {dict(C('caso'))}",f"- Tipo: {dict(C('tipo'))}",f"- Texto: {dict(C('txt'))}",f"- Fichamento: {dict(C('reg'))}",
f"- Nome/pasta com problema: {sum(1 for r in rows if r['prob'])}",f"- Duplicatas exatas: {len(dup)} grupos · iguais a arquivo de normas/: {len(dupn)}",""]
out+=["## Não fichados","","| UF | arquivo | tipo | caso | texto |","|---|---|---|---|---|"]+[f"| {r['uf']} | {r['arq']} | {r['tipo']} | {r['caso']} | {r['txt']} |" for r in rows if r["reg"].startswith("NÃO")]+[""]
out+=["## Nome/pasta fora do padrão","",*[f"- {r['uf']}/{r['arq']}: {'; '.join(r['prob'])}" for r in rows if r["prob"]],""]
out+=["## Duplicatas","",*[f"- `{h[:8]}`: "+" · ".join(os.path.relpath(p,CON) for p in ps) for h,ps in dup],*[f"- {a} = normas/{' · '.join(b)}" for a,b in dupn],""]
out+=["## Escaneados sem OCR","",*[f"- {r['uf']}/{r['arq']}" for r in rows if r["txt"]=="escaneado SEM OCR"],""]
out+=["## Por município em escopo — base-mestre","","| Município | UF | docs | não fichados | Operador | Remuneração | Trajetória contratual |","|---|---|---|---|---|---|---|"]+[f"| {a} | {b} | {c} | {d} | {e} | {f} | {g} |" for a,b,c,d,e,f,g in mest]+[""]
out+=["## Fora do escopo","",*[f"- {r['uf']}/{r['arq']} — {r['caso']}" for r in rows if r["caso"]!="escopo"],""]
rep="\n".join(out)
if "--report" in sys.argv:
    fn=f"_meta/Auditoria de contratos {datetime.date.today():%Y-%m-%d}.md"
    open(fn,"w",encoding="utf-8",newline="\n").write("---\ntitle: \"Auditoria de contratos "+f"{datetime.date.today():%Y-%m-%d}"+"\"\ntags: [auditoria, contratos]\npublish: false\ncreated: "+f"{datetime.date.today():%Y-%m-%d}"+"\n---\n\n"+rep+"\n")
    print("relatório:",fn)
print("\n".join(out[:12]))
if "--json" in sys.argv:
    import json
    json.dump([{k:v for k,v in r.items() if k not in ("trechos","k")} for r in rows],open(sys.argv[sys.argv.index("--json")+1],"w",encoding="utf-8"),ensure_ascii=False,indent=0)
