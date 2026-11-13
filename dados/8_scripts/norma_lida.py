"""Critério 'norma lida' da regra A.2(e) — módulo comum (read-only).

Um caso tem a norma lida quando o texto do ato pode ser apontado no cofre, por uma de duas vias:
  1. arquivo — há em `normas/<UF>/` um arquivo do município cujo nº de ato aparece no campo `Legislação`
     da base-mestre — no nome do arquivo ou, para páginas .html/.txt, no cabeçalho do texto — (ou, se o
     campo não traz nº, qualquer arquivo de norma do município);
  2. nota — há uma nota `Norma — Mun-UF — …` que não é só catálogo: sem o aviso 'Ficha de catalogação'
     da auditoria de 17/09, ou com seção de leitura do texto ('Leitura integral', 'Texto integral',
     'Dispositivos lidos', 'Conferência na fonte oficial').
Notícia, página de programa ou declaração da Prefeitura não contam como leitura da norma.

`avaliar()` devolve {(mun_nz, uf): (nivel, detalhe)} com nivel ∈ {'lida — arquivo', 'lida — sem arquivo', 'não localizada'}.
04/11/2026 (decisão do autor): a via 'nota' só conta com vinculo_tz direto; 'não lida' passa a 'não localizada'. O quarto estado,
'não existe — política sem norma', é gravado por completude_v2_0930.py a partir do estado terminal (não depende de arquivo).
Uso direto: python norma_lida.py [--so-fechados]  (lista os casos)
"""
import os,re,unicodedata,sys
def nz(s): return unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode().lower().strip()
BASE="03 - Dados/_data/Legislacao e contratos TZ/normas"; ND="04 - Análises/Pesquisa legal/Normas padronizadas"
PAT=re.compile(r"^(?P<mun>.+?)-(?P<uf>[A-Z]{2}) - (?P<rest>.+)$")
NUMF=re.compile(r"(?<![\d.])(\d{1,2}(?:\.\d{3})+|\d{1,6})-(\d{4})(?!\d)")
NUML=re.compile(r"(?:n[º°o.]\s*|Lei\s+|Decreto\s+|LC\s+|Complementar\s+|Ordin[aá]ria\s+)(\d[\d.]*)\s*(?:/|,? de [^;)]*?)\s*(\d{4})")
SECOES=("Leitura integral","Texto integral","Dispositivos lidos","Conferência na fonte oficial","Leitura do texto integral")
def _arquivos(V):
    out={}
    for uf in os.listdir(os.path.join(V,BASE)):
        d=os.path.join(V,BASE,uf)
        if not os.path.isdir(d): continue
        for f in os.listdir(d):
            st=os.path.splitext(f)[0]
            if st.endswith(" - texto") or ("OCR" in st and f.endswith(".txt")): continue
            m=PAT.match(re.sub(r"^[A-Z]{2}__","",st))
            if m: out.setdefault((nz(m.group("mun")),m.group("uf")),[]).append(f)
    return out
def _notas(V):
    out={}
    for f in os.listdir(os.path.join(V,ND)):
        m=re.match(r"Norma — (.+)-([A-Z]{2}) — ",f)
        if not m: continue
        t=open(os.path.join(V,ND,f),encoding="utf-8").read()
        cat="Ficha de catalogação" in t or "Ficha gerada a partir dos dados já registrados na planilha-mestre" in t
        lida=(not cat) or any(("## "+s) in t or ("### "+s) in t for s in SECOES)
        mv=re.search(r"^vinculo_tz:\s*(.+)$",t,re.M); vv=(mv.group(1) if mv else "").lower()
        lida=lida and "direto" in vv and "indireto" not in vv  # 04/11/2026 (decisão do autor): só a nota do ato da política conta
        out.setdefault((nz(m.group(1)),m.group(2)),[]).append((f,lida))
    return out
def _cab(V,uf,f):
    import html as _h
    try: t=open(os.path.join(V,BASE,uf,f),encoding="utf-8",errors="ignore").read()
    except Exception: return ""
    t=re.sub(r"(?is)<(script|style).*?</\1>"," ",t); t=_h.unescape(re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",t))); t=re.sub(r"\S{60,}"," ",t)  # tira base64/CSS embutidos
    return t[:20000]
def _nums(s): return {(n.replace(".","").lstrip("0") or "0",a) for n,a in NUML.findall(str(s or ""))}
def avaliar(V,mestre_rows,H):
    A=_arquivos(V); N=_notas(V); iL=H.index("Legislação"); R={}
    for r in mestre_rows:
        if not r[0]: continue
        k=(nz(r[0]),r[1]); arqs=A.get(k,[]); nums=_nums(r[iL])
        fa=[f for f in arqs if any((n.replace(".","").lstrip("0") or "0",a) in nums for n,a in NUMF.findall(f)+NUML.findall(f))] if nums else arqs
        if not fa and nums:  # páginas .html sem nº no nome (ex.: 'Tarifa Zero de X - UF.html'): procurar o nº no cabeçalho do texto
            for f in arqs:
                if f.lower().endswith((".html",".htm",".txt")):
                    t=_cab(V,k[1],f)
                    if any(re.search(rf"(?<!\d){n}\D{{0,12}}{a}(?!\d)",t) or re.search(rf"(?<!\d){int(n):,}".replace(",",".")+rf"\D{{0,12}}{a}(?!\d)",t) for n,a in nums if n.isdigit()): fa.append(f); break
        if len(fa)>1:  # 09/10/2026: prefere o arquivo do 1º ato citado no campo Legislação (o ato-base vem primeiro)
            ordem=[(n.replace(".","").lstrip("0") or "0",a) for n,a in NUML.findall(str(r[iL] or ""))]
            def _pos(f):
                ks=[(n.replace(".","").lstrip("0") or "0",a) for n,a in NUMF.findall(f)+NUML.findall(f)]
                return min([ordem.index(x) for x in ks if x in ordem] or [999])
            fa=sorted(fa,key=_pos)
        nl=[f for f,l in N.get(k,[]) if l]
        if fa: R[k]=("lida — arquivo",fa[0])
        elif nl: R[k]=("lida — sem arquivo",nl[0])
        elif arqs: R[k]=("lida — arquivo",arqs[0]+" (nº diferente do campo Legislação — conferir)")
        else: R[k]=("não localizada","nenhum arquivo em normas/ e nenhuma nota de leitura do ato (vínculo direto)")
    return R
if __name__=="__main__":
    import openpyxl
    V=os.environ.get("TZ_VAULT") or os.path.expanduser("~/mnt/doutorado")
    ws=openpyxl.load_workbook(os.path.join(V,"03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx"),read_only=True)["consolidado"]
    rows=list(ws.iter_rows(values_only=True)); H=list(rows[0]); R=avaliar(V,rows[1:],H)
    iE=H.index("Estado terminal (completude)")
    for r in rows[1:]:
        if not r[0]: continue
        e=str(r[iE] or "")
        if "--so-fechados" in sys.argv and not e.startswith("Fechado — com norma"): continue
        nv,det=R[(nz(r[0]),r[1])]
        if nv!="lida — arquivo" or "conferir" in det: print(f"{r[0]}/{r[1]} | {e[:30]} | {nv} | {det[:110]}")
