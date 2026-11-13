# Auditoria somente-leitura: base-mestre × régua × notas de norma × fichas × log. Gera relatório; não altera nada.
# v1 09/10/2026 (_scratch/auditoria-1009). v2 09/10/2026 (noite): corrige falsos positivos sistemáticos (cats. 2, 3, 6, 8, 13, 14)
# e lê as EXCEÇÕES REVISADAS em '04 - Análises/Pesquisa legal/Auditoria — exceções revisadas.md': um achado cuja categoria,
# município e assinatura (início do texto do achado) batem com uma linha de lá vai para 'Revisados (não alertam)'.
# Se o campo mudar, a assinatura deixa de bater e o alerta volta. USO: python auditar_fichas_normas_tabela.py
import os,re,glob,unicodedata,collections,openpyxl,yaml
V=os.path.expanduser("~/mnt/doutorado"); os.chdir(V)
def nz(s): return unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode().lower().strip()
MP="03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx"; RP="03 - Dados/_data/casos por fonte/Tipologias TZ - consolidado.xlsx"
ND="04 - Análises/Pesquisa legal/Normas padronizadas/"; FD="04 - Análises/Casos municipais/Fichas por município/"
ws=openpyxl.load_workbook(MP,read_only=True)["consolidado"]; rows=list(ws.iter_rows(values_only=True)); H=rows[0]
g=lambda r,k: r[H.index(k)]
M={(r[0],r[1]):r for r in rows[1:] if r[0]}
esc={k:r for k,r in M.items() if str(g(r,"Situação")) in ("Ativa","Encerrada")}
w=openpyxl.load_workbook(RP,read_only=True); RG={}
for aba,col in [("1 Universal","Subtipo"),("2 Parcial","Subtipo"),("3 Encerradas","Subtipo (antes de encerrar)")]:
    rr=list(w[aba].iter_rows(values_only=True)); h=rr[0]
    for r in rr[1:]:
        if r[0]: RG.setdefault((r[0],r[1]),[]).append((aba,r[h.index(col)]))
# notas de norma
NN=collections.defaultdict(list)
for f in glob.glob(ND+"Norma — *.md"):
    m=re.match(r"Norma — (.+)-([A-Z]{2}) — (.+)\.md",os.path.basename(f))
    if not m: continue
    t=open(f,encoding="utf-8").read(); fm={}
    if t.startswith("---"):
        try: fm=yaml.safe_load(t.split("---")[1]) or {}
        except Exception: fm={"_erro_yaml":True}
    fm["_cat"]=("Ficha gerada a partir dos dados já registrados" in t or "Ficha de catalogação" in t) and not any(x in t for x in ("## Leitura integral","## Texto integral","## Dispositivos lidos","### Leitura integral"))
    fm["_arq"]=os.path.basename(f); NN[(nz(m.group(1)),m.group(2))].append(fm)
achados=collections.defaultdict(list)
def A(cat,k,txt): achados[cat].append(f"{k[0]}/{k[1]} — {txt}")
KW_GATE=["cadastr","resident","moradores da zona","renda","carteir","comprovante","matricul","estudante","idos","somente","apenas"]
for k,r in esc.items():
    sub=str(g(r,"Régua — subtipo") or ""); aba=str(g(r,"Régua — aba") or ""); port=nz(g(r,"Régua — portão")); st=str(g(r,"Status no log") or ""); et=str(g(r,"Estado terminal (completude)") or "")
    # 1. régua × mestre
    rg=RG.get(k,[])
    if not rg: A("1. Caso em escopo sem linha na régua",k,f"aba na mestre: {aba}")
    elif len(rg)>1 and k not in [("Belo Horizonte","MG"),("Brasília","DF")]: A("1. Mais de uma linha na régua (A.1.5)",k,str(rg))
    # 2. subtipo × texto do portão
    if sub=="1a" and not port.startswith("nenhum"):
        hit=[w_ for w_ in KW_GATE if w_ in port and not re.search(r"(sem|nenhum|nao (ha|exige)|não)\W+[^;]{0,40}"+w_,port)]
        if hit: A("2. Subtipo 1a com termo de portão no campo 'Régua — portão' (conferir se é ressalva ou portão)",k,f"termos: {', '.join(hit)} · portão: {str(g(r,'Régua — portão'))[:160]}")
    if sub=="1c" and "resid" not in port and "munic" not in port: A("2. 1c sem menção a residência no portão",k,str(g(r,"Régua — portão"))[:160])
    if sub=="1d" and not re.search(r"prazo|ate \d|\d{2}/\d{2}/\d{4}|vigen",port): A("2. 1d sem prazo no portão",k,str(g(r,"Régua — portão"))[:160])
    # 3. status × subtipo
    sm=re.findall(r"\b([12][a-e])\b",st)
    if sub and sm and sub not in sm and not st.startswith("Pendente"): A("3. 'Status no log' cita subtipo diferente do da régua",k,f"régua {sub} · status: {st[:150]}")
    # 4. nota de norma × subtipo
    notas=NN.get((nz(k[0]),k[1]),[])
    if sub=="1a":
        for n in notas:
            if n.get("vinculo_tz")!="direto": continue  # normas de contexto ou categoriais não classificam
            c=nz(n.get("concede_gratuidade"))
            if any(x in c for x in ("so ","apenas","grupo","moradores","resident","estudant","idos")) and "nao" not in c[:4]:
                A("4. Nota de norma restringe público, régua diz 1a",k,f"{n['_arq']}: concede = {n.get('concede_gratuidade')}")
    # 5. Legislação × notas
    leg=nz(g(r,"Legislação"))
    if notas and any(x in leg for x in ("nao encontrei","nao localizada","nao localizado")) and any(n.get("vinculo_tz")=="direto" for n in notas):
        A("5. Campo 'Legislação' diz não encontrada, mas há nota de norma com vínculo direto",k,"; ".join(n["_arq"] for n in notas)[:200])
    nums=set(x.replace(".","").lstrip("0") for x in re.findall(r"(?:n[ºo°]\s*|lei\s+|decreto\s+|lc\s+)(\d[\d.]*)",leg))
    nnums=set(str(n.get("numero","")).replace(".","").lstrip("0") for n in notas)
    if nums and nnums and not (nums & nnums): A("5. Nº no campo 'Legislação' não bate com nenhuma nota de norma",k,f"Legislação: {str(g(r,'Legislação'))[:100]} · notas: {sorted(nnums)}")
    # 6. notas só de catálogo em caso fechado com norma
    if et.startswith("Fechado — com norma") and notas and all(n["_cat"] for n in notas) and not str(g(r,"Norma lida (A.2e)") or "").startswith("lida — arquivo"):
        A("6. Fechado com norma, mas todas as notas de norma são só catálogo (leitura apoiada no arquivo)",k,"; ".join(n["_arq"] for n in notas)[:200])
    # 7. ano início × data da norma direta
    try: ai=int(str(g(r,"Ano início"))[:4])
    except Exception: ai=None
    anos=[int(str(n.get("ano"))[:4]) for n in notas if n.get("vinculo_tz")=="direto" and str(n.get("ano","")).isdigit()]
    if ai and anos and min(anos)<ai-1: A("7. Norma direta anterior ao 'Ano início' (conferir trajetória ou início)",k,f"ano início {ai} · normas diretas {sorted(anos)}")
    # 8. prova × ano
    pv=str(g(r,"Prova de operação — atualidade (2025/2026)") or "")
    if pv.startswith("atende") and not re.search(r"202[56]",pv): A("8. Prova 'atende' sem ano 2025/2026 no início",k,pv[:120])
    if str(g(r,"Situação"))=="Ativa" and et.startswith("Fechado — com norma") and not pv.startswith("atende"): A("8. Fechado com norma sem prova 'atende'",k,pv[:120])
    # 9. texto defasado que alimenta o Briefing
    ob=nz(str(g(r,"Obs. legal") or "").split("||")[0])  # só a entrada mais recente (o histórico fica depois de '||')
    if et.startswith("Fechado") and any(x in ob for x in ("candidata","nº nao capturado","no nao capturado","nao localizei","nao encontrei","pista fraca")):
        A("9. 'Obs. legal' defasada em caso fechado (aparece no Briefing da ficha)",k,str(g(r,"Obs. legal"))[:160])
    # 10. e-SIC 'a enviar' em caso fechado
    es=str(g(r,"e-SIC / varredura nº") or "")
    if et.startswith("Fechado") and "a enviar" in es: A("10. Caso fechado com e-SIC ainda 'a enviar'",k,es)
    # 11. CNPJ do operador
    if g(r,"Operador — CNPJ") and "candidat" in nz(g(r,"Operador — CNPJ")): A("11. Coluna 'Operador — CNPJ' com candidato",k,str(g(r,"Operador — CNPJ"))[:120])
    # 12. situação × aba
    if str(g(r,"Situação"))=="Encerrada" and not aba.startswith("3"): A("12. Encerrada fora da aba 3",k,aba)
    if str(g(r,"Situação"))=="Ativa" and aba.startswith("3"): A("12. Ativa na aba 3",k,aba)
# 13. fichas: frontmatter camada × régua
for k,r in esc.items():
    f=FD+f"Ficha - {k[0]} ({k[1]}).md"
    if not os.path.exists(f): A("13. Caso sem ficha",k,""); continue
    t=open(f,encoding="utf-8").read(); m=re.search(r"^camada: (.+)$",t,re.M); sub=str(g(r,"Régua — subtipo") or "")
    if m and sub and f"({sub})" not in m.group(1) and not (str(g(r,"Régua — aba") or "").startswith("3") and "encerrada" in m.group(1)): A("13. 'camada' do frontmatter da ficha difere do subtipo da régua",k,f"ficha: {m.group(1)} · régua: {sub}")
    if "nº não capturado" in t.split("<!-- prosa")[0] and str(g(r,"Estado terminal (completude)")).startswith("Fechado"): pass
# 14. notas de norma de municípios fora da base
mun={(nz(a),b) for a,b in M}
for _ws in w.worksheets:
    for _r in _ws.iter_rows(min_row=2,values_only=True):
        if _r and _r[0] and len(_r)>1 and isinstance(_r[1],str) and len(_r[1])==2: mun.add((nz(_r[0]),_r[1]))
for k,ns in NN.items():
    if k not in mun: achados["14. Nota de norma de município fora da base-mestre"].append(f"{k[0]}/{k[1]} — {len(ns)} nota(s)")
    for n in ns:
        if n.get("_erro_yaml"): achados["15. Nota de norma com frontmatter inválido"].append(n["_arq"])
XP="04 - Análises/Pesquisa legal/Auditoria — exceções revisadas.md"; EXC=[]
if os.path.exists(XP):
    for l in open(XP,encoding="utf-8"):
        c=[x.strip() for x in l.strip().strip("|").split("|")]
        if len(c)>=5 and re.match(r"^\d+$",c[0]): EXC.append((c[0],c[1],c[2].strip("`")))
rev=collections.defaultdict(list)
for cat in list(achados):
    n=cat.split(".")[0]; keep=[]
    for x in achados[cat]:
        mu,_,det=x.partition(" — ")
        if any(n==e[0] and mu==e[1] and det.startswith(e[2]) for e in EXC): rev[cat].append(x)
        else: keep.append(x)
    achados[cat]=keep
    if not keep: del achados[cat]
import datetime; HOJE=datetime.date.today().strftime("%d/%m/%Y")
out=["---",'title: "Auditoria — fichas, normas e tabela (rodada atual)"',"tags: [auditoria, pesquisa-legal, regua]","publish: false","created: 2026-10-09","---","",
f"# Auditoria — fichas, normas e tabela (rodada de {HOJE})","","Autor: Thiago Von Zeidler Gomes","Orientadora: Prof.ª Dra. Silvana Zioni","",
f"Leitura cruzada por script (somente leitura) da base-mestre ({len(esc)} casos em escopo), da régua, de {sum(len(v) for v in NN.values())} notas de norma e das fichas. Script: `_meta/scripts/_scratch/auditoria-1009/auditar_fichas_normas_tabela.py`. Cada achado é um **sinal a conferir**, não um erro confirmado. Achados já decididos ficam em [[Auditoria — exceções revisadas]] e aparecem no fim, sem alertar.",""]
if not achados: out+=["**Nenhum alerta em aberto.**",""]
for cat in sorted(achados,key=lambda c:int(c.split(".")[0])):
    out+= [f"## {cat} ({len(achados[cat])})",""]+[f"- {x}" for x in sorted(achados[cat])]+[""]
if rev:
    out+=[f"## Revisados (não alertam) ({sum(len(v) for v in rev.values())})",""]
    for cat in sorted(rev,key=lambda c:int(c.split(".")[0])): out+=[f"- {cat.split('(')[0].strip()}: "+"; ".join(x.split(" — ")[0] for x in sorted(rev[cat]))]
    out+=[""]
out+=["## Ligações","","- [[Auditoria — exceções revisadas]]","- [[Auditoria — fichas, normas e tabela (09-10-2026)]] (1ª rodada, com a triagem)","- [[Log de busca jurídica e contratual — municípios]]","- [[Regras de classificacao das reguas]]","- [[_índice - Normas padronizadas]]",""]
p="04 - Análises/Pesquisa legal/Auditoria — fichas, normas e tabela (rodada atual).md"
open(p,"w",encoding="utf-8",newline="\n").write("\n".join(out))
for cat in sorted(achados,key=lambda c:int(c.split(".")[0])): print(len(achados[cat]),"|",cat)
print("revisados (não alertam):",sum(len(v) for v in rev.values()))
