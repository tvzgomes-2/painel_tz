"""Auditoria do acervo de normas primárias (read-only).

Confere, para cada arquivo em `03 - Dados/_data/Legislacao e contratos TZ/normas/<UF>/`:
  1. nome no padrão `Município-UF - Ato nº-ano (data) - assunto.ext` e pasta = UF do nome;
  2. duplicata exata (md5) dentro de normas/ ou com contratos/;
  3. camada de texto: PDF sem texto (escaneado) precisa de OCR irmão (`… - OCR.txt`);
     imagens (png/jpg) contam como "imagem — transcrição no log?";
  4. caso: município na base-mestre (escopo), só na régua (outras abas) ou órfão;
  5. registro de leitura: o arquivo é citado pelo nome no log/fichas/notas de norma,
     ou o nº do ato (ex.: 3157/2023, 3.157/2023) aparece no bloco do município no log;
  6. nota padronizada: existe `Norma — Mun-UF — … NNNN-AAAA.md` para o ato? (ou alguma nota do município cita o arquivo pelo nome)
E, por caso em escopo, o nº de ato citado em `Legislação` da base-mestre sem arquivo nem nota.

Uso: python auditar_normas.py [--report] [--json ARQ]   (--report grava _meta/Auditoria de normas AAAA-MM-DD.md)
"""
import os,re,sys,hashlib,subprocess,unicodedata,datetime,collections
import openpyxl
V=os.environ.get("TZ_VAULT") or os.path.expanduser("~/mnt/doutorado"); os.chdir(V)
BASE="03 - Dados/_data/Legislacao e contratos TZ"; NOR=f"{BASE}/normas"; CON=f"{BASE}/contratos"
LOG="04 - Análises/Pesquisa legal/Log de busca jurídica e contratual — municípios.md"
NP="04 - Análises/Pesquisa legal/Normas padronizadas"; FD="04 - Análises/Casos municipais/Fichas por município"
MP="03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx"; RP="03 - Dados/_data/casos por fonte/Tipologias TZ - consolidado.xlsx"
def nz(s): return unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().lower().strip()
def md5(p):
    h=hashlib.md5()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
# universo
mw=openpyxl.load_workbook(MP,read_only=True)["consolidado"]; mr=list(mw.iter_rows(values_only=True)); MH=mr[0]
iS=MH.index("Situação"); iL=MH.index("Legislação"); iEsc=None
ESC={}
for r in mr[1:]:
    if r[0] and r[iS] not in ("Excluída","Reclassificada",None): ESC[(nz(r[0]),r[1])]=r
REG=set()
for ws in openpyxl.load_workbook(RP,read_only=True).worksheets:
    for r in ws.iter_rows(min_row=2,values_only=True):
        if r and r[0] and r[1] and len(str(r[1]))==2: REG.add((nz(r[0]),r[1]))
# textos de referência
log=open(LOG,encoding="utf-8").read()
blocos={}
for b in re.split(r"\n(?=#### )",log):
    m=re.match(r"#### (.+) \(([A-Z]{2})\)",b)
    if m: blocos[(nz(m.group(1)),m.group(2))]=b
fichas={}
for f in os.listdir(FD):
    m=re.match(r"Ficha - (.+) \(([A-Z]{2})\)\.md$",f)
    if m: fichas[(nz(m.group(1)),m.group(2))]=open(os.path.join(FD,f),encoding="utf-8").read()
notas={}; notas_txt=""; notas_txt_mun={}
for f in os.listdir(NP):
    if f.startswith("Norma — "):
        t=open(os.path.join(NP,f),encoding="utf-8").read(); notas_txt+=t
        m=re.match(r"Norma — (.+)-([A-Z]{2}) — (.+)\.md$",f)
        if m: notas.setdefault((nz(m.group(1)),m.group(2)),[]).append((f,m.group(3))); notas_txt_mun.setdefault((nz(m.group(1)),m.group(2)),"")
        if m: notas_txt_mun[(nz(m.group(1)),m.group(2))]+=t
corpus_parts=[log,"\n".join(fichas.values()),notas_txt]
for d,ds,fs in os.walk("."):
    if d.startswith("./_meta") or "/." in d or "07 - Disciplinas" in d: continue
    for f in fs:
        if f.endswith(".md"):
            try: corpus_parts.append(open(os.path.join(d,f),encoding="utf-8").read())
            except Exception: pass
corpus="\n".join(corpus_parts)
SUPTXT=""
for q in ("04 - Análises/Casos municipais/Ficha — Políticas federais, estaduais e distritais de gratuidade.md","04 - Análises/Pesquisa legal/Downloads manuais — esfera supramunicipal (2026-09-28).md","03 - Dados/Linha do tempo — Tarifa Zero no Brasil.md"):
    if os.path.exists(q): SUPTXT+=open(q,encoding="utf-8").read()
for ws in openpyxl.load_workbook(RP,read_only=True).worksheets:
    if "acion" in ws.title or "stadua" in ws.title:
        for r in ws.iter_rows(values_only=True): SUPTXT+=" ".join(str(x) for x in r if x)+"\n"
# contratos md5
cmd5={}
for d,_,fs in os.walk(CON):
    for f in fs: cmd5.setdefault(md5(os.path.join(d,f)),[]).append(os.path.join(d,f))
PAT=re.compile(r"^(?:[A-Z]{2}__)?(?P<mun>.+?)-(?P<uf>[A-Z]{2}) - (?P<rest>.+)$")
SUP=re.compile(r"^(?P<uf>[A-Z]{2}) - (?P<rest>.+)$")
NUM0=re.compile(r"(?<![\d.])(\d{1,2}(?:\.\d{3})+|\d{1,6})-(\d{4})(?!\d)")
NUMS=re.compile(r"n[º°]\s*(\d[\d.]*)(?:,? de .*?|\s+)(\d{4})")  # 'nº 3.157, de … 2023' ou 'nº 4.765 2023'
class _N:
    def findall(self,s): return NUM0.findall(s) or NUMS.findall(s)
NUM=_N()
def num_pats(n,a):
    s=n.replace(".",""); f=f"{int(s):,}".replace(",",".") if s.isdigit() else n
    return {f"{s}/{a}",f"{f}/{a}",f"{s}-{a}",f"{f}-{a}",f"{s}, de",f"nº {s}",f"nº {f}",f"n.º {f}",f"n° {f}",f"n° {s}"}
def pdf_chars(p):
    try: return len(subprocess.run(["pdftotext","-l","3",p,"-"],capture_output=True,timeout=30).stdout.decode("utf-8","ignore").strip())
    except Exception: return -1
rows=[]; byhash=collections.defaultdict(list)
for uf in sorted(os.listdir(NOR)):
    pd=os.path.join(NOR,uf)
    if not os.path.isdir(pd): continue
    for f in sorted(os.listdir(pd)):
        p=os.path.join(pd,f)
        if os.path.isdir(p): continue
        stem,ext=os.path.splitext(f); ext=ext.lower().lstrip(".")
        h=md5(p); byhash[h].append(p)
        sup=SUP.match(stem); m=None if sup else PAT.match(stem); prob=[]
        mun,muf=(m.group("mun"),m.group("uf")) if m else (None,None)
        if not m and not sup: prob.append("nome fora do padrão")
        if m and re.match(r"^[A-Z]{2}__",stem): prob.append("prefixo UF__ (lote SAPL) — padronizar")
        elif m and uf!="_A-IDENTIFICAR" and muf!=uf: prob.append(f"UF do nome ({muf}) ≠ pasta ({uf})")
        elif sup and sup.group("uf") not in (uf,"BR") and uf!="_A-IDENTIFICAR": prob.append(f"UF do nome ({sup.group('uf')}) ≠ pasta ({uf})")
        if re.search(r"  |\(\d\)$|\.pdf$|copia|cópia|^Copy",stem,re.I): prob.append("nome com sinal de cópia/espaço duplo")
        k=(nz(mun),muf) if mun else None
        caso="supramunicipal (estadual/federal)" if sup else "órfão"
        if k in ESC: caso="escopo"
        elif k in REG: caso="régua (fora do escopo)"
        # texto
        txt="ok"
        if ext=="txt" and "OCR" in stem: continue  # OCR irmão: companheiro do PDF, não é documento próprio
        if ext=="pdf":
            c=pdf_chars(p)
            if c<200:
                irmao=[g for g in os.listdir(pd) if g.startswith(stem[:40]) and "OCR" in g and g.endswith(".txt")]
                txt="escaneado c/ OCR" if irmao else "escaneado SEM OCR"
        elif ext in("png","jpg","jpeg"): txt="imagem"
        elif ext=="txt": txt="texto (OCR?)"
        # registro
        reg="não registrado"
        if f in corpus or stem in corpus: reg="citado pelo nome"
        else:
            nums=NUM.findall(stem) if (m or sup) else []
            blk=(blocos.get(k,"")+fichas.get(k,"")) if m else SUPTXT
            if any(any(q in blk for q in num_pats(n,a)) for n,a in nums): reg="nº citado no log/ficha"
            elif not nums and k and blocos.get(k): reg="sem nº no nome (conferir)"
        # nota
        nota="—"
        if k in notas and m:
            nums=NUM.findall(stem); ns=[n.replace(".","")+"-"+a for n,a in nums]
            nota="tem nota" if any(any(x in t.replace(".","") for x in ns) for _,t in notas[k]) else ("tem nota (arquivo citado em nota)" if (f in notas_txt_mun.get(k,"") or stem in notas_txt_mun.get(k,"")) else "sem nota do ato")
        elif m and ext!="txt": nota="sem nota do município"
        rows.append(dict(uf=uf,arq=f,ext=ext,md5=h,mun=mun,caso=caso,txt=txt,reg=reg,nota=nota,prob=prob))
# duplicatas
dup=[(h,ps) for h,ps in byhash.items() if len(ps)>1]
dupc=[(r["arq"],cmd5[r["md5"]]) for r in rows if r["md5"] in cmd5]
# casos em escopo: nº na Legislação sem arquivo nem nota
arqs_por_mun=collections.defaultdict(str)
contr_por_mun=collections.defaultdict(list)
for d,_,fs in os.walk(CON):
    for f in fs:
        mm=PAT.match(os.path.splitext(f)[0])
        if mm: contr_por_mun[(nz(mm.group("mun")),mm.group("uf"))].append(f)
for r in rows:
    if r["mun"]: arqs_por_mun[(nz(r["mun"]),r["uf"])]+=" "+r["arq"].replace(".","")
falta=[]
for k,r in ESC.items():
    leg=str(r[iL] or "")
    for n,a in re.findall(r"(?:n[º°o.]\s*|Lei\s+|Decreto\s+|LC\s+|Complementar\s+|Lei Ordin[aá]ria\s+)(\d[\d.]*)\s*/\s*(\d{4})",leg):
        s=n.replace(".","").lstrip("0") or "0"
        alvo=re.compile(rf"(?<!\d)0*{s}-{a}(?!\d)")
        if not alvo.search(arqs_por_mun[k]) and not any(alvo.search(t.replace(".","")) for _,t in notas.get(k,[])):
            emc=[f for f in contr_por_mun.get(k,[]) if alvo.search(f.replace(".",""))]
            blk=blocos.get(k,"")
            lido=any(q in blk for q in (f"{n}/{a}",f"{s}/{a}")) and re.search(r"lid[ao]|texto (integral|primário)|dispositivo",blk)
            falta.append((r[0],r[1],f"{n}/{a}","em contratos/ (não é norma)" if emc else ("citado no log, sem arquivo" if lido else "sem arquivo nem leitura registrada")))
# relatório
C=lambda key: collections.Counter(r[key] for r in rows)
out=[f"# Auditoria do acervo de normas — {datetime.date.today():%d/%m/%Y}","",
f"Gerado por `_meta/scripts/auditar_normas.py` (read-only). Arquivos em `normas/`: **{len(rows)}**.","",
"## Resumo","",
f"- Caso: {dict(C('caso'))}",f"- Texto: {dict(C('txt'))}",f"- Registro de leitura: {dict(C('reg'))}",f"- Nota padronizada: {dict(C('nota'))}",
f"- Extensões: {dict(C('ext'))}",
f"- Nome/pasta com problema: {sum(1 for r in rows if r['prob'])}",
f"- Duplicatas exatas dentro de normas/: {len(dup)} grupos · iguais a arquivo de contratos/: {len(dupc)}",
f"- Casos em escopo com nº de ato na `Legislação` sem arquivo nem nota: {len(falta)}",""]
def tab(title,sel,cols):
    L=[r for r in rows if sel(r)]
    out.extend([f"## {title} ({len(L)})","","| UF | arquivo | "+" | ".join(cols)+" |","|---|---|"+"---|"*len(cols)])
    for r in L: out.append(f"| {r['uf']} | {r['arq']} | "+" | ".join(str(r[c]) if c!='prob' else '; '.join(r['prob']) for c in cols)+" |")
    out.append("")
tab("Nome ou pasta fora do padrão",lambda r:r["prob"],["prob","caso"])
out.extend([f"## Duplicatas exatas (md5) dentro de normas/ ({len(dup)})",""]+[f"- `{h[:8]}`: "+" · ".join(os.path.relpath(p,NOR) for p in ps) for h,ps in dup]+[""])
out.extend([f"## Iguais a arquivo de contratos/ ({len(dupc)})",""]+[f"- {a} = "+" · ".join(os.path.relpath(p,CON) for p in ps) for a,ps in dupc]+[""])
tab("PDF escaneado sem OCR",lambda r:r["txt"]=="escaneado SEM OCR",["caso","reg"])
tab("Não registrados (nem nome nem nº no log/ficha/nota)",lambda r:r["reg"]=="não registrado" and r["ext"]!="txt",["caso","txt"])
tab("Órfãos (município fora da mestre e da régua)",lambda r:r["caso"]=="órfão",["reg"])
tab("Escopo: arquivo de ato sem nota padronizada",lambda r:r["caso"]=="escopo" and r["nota"] in("sem nota do ato","sem nota do município") and r["ext"]!="txt",["reg","txt"])
out.extend([f"## Escopo: nº de ato citado na base-mestre sem arquivo nem nota ({len(falta)})",""]+[f"- {m} ({u}): {n} — {st}" for m,u,n,st in sorted(falta)]+[""])
rep="\n".join(out)
if "--report" in sys.argv:
    fn=f"_meta/Auditoria de normas {datetime.date.today():%Y-%m-%d}.md"
    open(fn,"w",encoding="utf-8",newline="\n").write("---\ntitle: \"Auditoria de normas "+f"{datetime.date.today():%Y-%m-%d}"+"\"\ntags: [auditoria, legislacao]\npublish: false\ncreated: "+f"{datetime.date.today():%Y-%m-%d}"+"\n---\n\n"+rep+"\n")
    print("relatório:",fn)
print("\n".join(out[:14]))
if "--json" in sys.argv:
    import json
    json.dump([{k:v for k,v in r.items() if k not in ("trechos","k")} for r in rows],open(sys.argv[sys.argv.index("--json")+1],"w",encoding="utf-8"),ensure_ascii=False,indent=0)
