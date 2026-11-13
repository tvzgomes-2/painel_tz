#!/usr/bin/env python3
# Exporta a tese (Introdução + Cap 1–8 + Conclusão) para .docx de LEITURA.
# Formatação (ABNT NBR 14724 / Guia UFABC 2021): Aptos 12, justificado, entrelinha 1,5
# (simples em citações/legendas), margens 3-2-3-2, nº topo-direita + rodapé de versão,
# numeração das subpartes própria (C.x, C.x.y — sem numeração automática do pandoc),
# legendas designativo+nº+travessão acima / Fonte abaixo, tabelas IBGE, citações
# longas recuadas 4 cm. Callouts saem como destaque (negrito), NÃO como citação.
import re, os, glob, subprocess, sys, zipfile, shutil, tempfile
from datetime import datetime
# Caminho do cofre: variável de ambiente > caminho do sandbox (se existir) >
# diretório corrente. O caminho do sandbox estava fixo no código e, rodado na
# máquina do autor, o script morria no os.chdir antes de qualquer coisa.
_SANDBOX="/sessions/kind-sleepy-feynman/mnt/doutorado"
VAULT=os.environ.get("TZ_VAULT") or (_SANDBOX if os.path.isdir(_SANDBOX) else os.getcwd())
os.chdir(VAULT)
FIGS="/tmp/figs"
VERSION="Versão de leitura — "+datetime.now().strftime("%d/%m/%Y")
OUTDIR="02 - Tese/Leitura"
OUT=OUTDIR+"/Tese (para leitura).docx"
def snapshot(path):
    hd=os.path.join(os.path.dirname(path) or ".","Histórico"); os.makedirs(hd,exist_ok=True)
    stem,ext=os.path.splitext(os.path.basename(path))
    shutil.copy2(path, os.path.join(hd, stem+" — "+datetime.now().strftime("%Y-%m-%d_%H%M")+ext))

ORDER=[("02 - Tese/Introdução.md","Introdução"),
 ("02 - Tese/Capítulos/Cap 1 - Além do carro.md","Capítulo 1"),
 ("02 - Tese/Capítulos/Cap 2 - As causas externas do colapso.md","Capítulo 2"),
 ("02 - Tese/Capítulos/Cap 3 - O colapso interno do modelo.md","Capítulo 3"),
 ("02 - Tese/Capítulos/Cap 4 - Modelos heterodoxos.md","Capítulo 4"),
 ("02 - Tese/Capítulos/Cap 5 - Panorama Nacional da Tarifa Zero.md","Capítulo 5"),
 ("02 - Tese/Capítulos/Cap 6 - Uma régua para medir a Tarifa Zero.md","Capítulo 6"),
 ("02 - Tese/Capítulos/Cap 7 - A estrutura de poder no transporte coletivo.md","Capítulo 7"),
 ("02 - Tese/Capítulos/Cap 8 - Inovação e Resistência.md","Capítulo 8"),
 ("02 - Tese/Conclusão (tese).md","Conclusão")]
DROP_H2=["metadados","ligações","estrutura proposta","lista de inicial","lista de estudos",
 "bibliografia básica","referências (zotero)","material importado","insumos","municípios mapeados na bibliografia"]
DROP_CALLOUT=["vínculo metodológico","dados e análises relacionados","a revisar","dados e analises"]
def resolve_fig(name):
    raw=name.split('|')[0].split('#')[0].strip(); stem=re.sub(r'\.(png|jpg|jpeg|svg|gif)$','',raw,flags=re.I)
    if raw.lower().endswith('.svg'):
        p=os.path.join(FIGS,stem+".png")
        if os.path.exists(p): return p
    hits=glob.glob("_attachments/**/"+stem+".*",recursive=True)
    return os.path.abspath(hits[0]) if hits else None
def process_inline(line):
    def emb(mm):
        p=resolve_fig(mm.group(1))
        return ("\n![](<"+p+">)\n") if p else ("\n*[Figura ausente: "+mm.group(1)+"]*\n")
    line=re.sub(r'!\[\[([^\]]+)\]\]',emb,line)
    line=re.sub(r'\[\[([^\]]+)\]\]',lambda x:x.group(1).split('|')[1] if '|' in x.group(1) else x.group(1).split('#')[0],line)
    line=re.sub(r'</?(span|font|sup|sub)[^>]*>','',line)
    return line
def clean(path,label):
    md=re.sub(r'^---\n.*?\n---\n','',open(path,encoding='utf-8',errors='replace').read(),count=1,flags=re.S)
    lines=md.split('\n'); out=[]; i=0; n=len(lines)
    while i<n and not lines[i].startswith('# '): i+=1
    title=lines[i][2:].strip() if i<n else label
    special=label in ("Introdução","Conclusão")
    mlab=re.match(r'Cap[íi]tulo\s+(\d+)',label); cnum=mlab.group(1) if mlab else None
    out.append("# "+(label if special else label+" — "+title)+"\n"); i+=1
    drop=False; s1=0; s2=0
    while i<n:
        line=lines[i]
        h=re.match(r'^(#{2,6})\s+(.*)$', line)
        if h:
            htext=h.group(2).strip(); tl=htext.lower()
            if any(k in tl for k in DROP_H2): drop=True; i+=1; continue
            if 'texto integral' in tl: drop=False; i+=1; continue
            drop=False
            ht=re.sub(r'^[^0-9A-Za-zÀ-ÿ]+','',htext).strip()   # tira emoji/símbolo inicial
            mnum=re.match(r'^(\d+(?:\.\d+)+)\.?\s+(.*)$', ht)
            if special:
                out.append("## "+ht); i+=1; continue
            if mnum:
                comps=mnum.group(1).split('.'); rest=mnum.group(2).strip()
                if len(comps)<=2: s1+=1; s2=0; out.append("## %s.%d. %s"%(cnum,s1,rest))
                else:
                    if s1==0: s1=1
                    s2+=1; out.append("### %s.%d.%d. %s"%(cnum,s1,s2,rest))
                i+=1; continue
            out.append("### "+ht); i+=1; continue   # subparte sem número → subordinada, sem número
        if drop: i+=1; continue
        m=re.match(r'^\s*>\s*\[!(\w+)\]([+-]?)\s*(.*)$',line)
        if m:
            typ=m.group(1); ttl=(m.group(3) or '').strip()
            if any(k in ttl.lower() or k==typ.lower() for k in DROP_CALLOUT):
                i+=1
                while i<n and lines[i].lstrip().startswith('>'): i+=1
                continue
            i+=1; body=[]
            while i<n and lines[i].lstrip().startswith('>'):
                body.append(re.sub(r'^\s*>\s?','',lines[i])); i+=1
            out.append("")
            if ttl: out.append("**"+ttl+"**")
            for b in body:
                if b.strip(): out.append(process_inline(b))
            out.append(""); continue
        if line.lstrip().startswith('>'):
            blk=[]
            while i<n and lines[i].lstrip().startswith('>'):
                blk.append(re.sub(r'^\s*>\s?','',lines[i])); i+=1
            first=next((b for b in blk if b.strip()),'')
            out.append("")
            if first.strip().startswith('**'):        # caixa de destaque → não é citação
                for b in blk:
                    if b.strip(): out.append(process_inline(b)); out.append("")
            else:                                       # citação real → mantém recuo
                for b in blk: out.append(("> "+process_inline(b)) if b.strip() else ">")
                out.append("")
            continue
        if re.match(r'^\**\s*coment[áa]rio do autor',line.strip(),flags=re.I):
            i+=1
            while i<n and not lines[i].strip(): i+=1
            while i<n and lines[i].strip(): i+=1
            continue
        out.append(process_inline(line)); i+=1
    return '\n'.join(out).strip()

KINDS=r'(Figura|Gr[áa]fico|Tabela|Quadro|Mapa|Organograma|Fluxograma|Esquema)'
_cap_re=re.compile(r'^\s*(?:\*\*)?\s*'+KINDS+r'\b[\s\.:—\-]*([0-9]+[A-Za-z]?)?\s*[\.:—\-]?\s*(.*?)(?:\*\*)?\s*$', re.I)
def _is_cap(line):
    if not line or not re.match(r'^\s*(?:\*\*)?\s*'+KINDS+r'\b', line, re.I): return None
    if len(line.split())>22: return None
    return _cap_re.match(line)
def number_captions(md):
    lines=md.split('\n'); out=[]; counters={}; skip=set(); n=len(lines)
    def render(m):
        kind=m.group(1); k=kind.lower().replace('á','a')
        counters[k]=counters.get(k,0)+1
        desc=re.sub(r'^\d+[A-Za-z]?[\s\.:—\-]*','',(m.group(3) or '').strip())
        sep=' — ' if desc else ''
        return "**"+kind.capitalize()+" "+str(counters[k])+sep+desc+"**"
    i=0
    while i<n:
        if i in skip: i+=1; continue
        line=lines[i]
        if line.strip().startswith('!['):
            prev=next((o for o in reversed(out) if o.strip()),'')
            if not _is_cap(prev):
                for j in range(i+1, min(i+4,n)):
                    if not lines[j].strip(): continue
                    mj=_is_cap(lines[j])
                    if mj: out.append(render(mj)); skip.add(j)
                    break
            out.append(line)
            look=" ".join(lines[i+1:i+4]).lower()
            if 'fonte' not in look: out.append("Fonte: elaboração do autor.")
            i+=1; continue
        m=_is_cap(line)
        if m: out.append(render(m)); i+=1; continue
        out.append(line); i+=1
    return '\n'.join(out)

def fix_crossrefs(md):
    """Realinha referências no corpo ('Figura N', 'Tabela N') à legenda mais próxima."""
    lines=md.split('\n')
    capre=re.compile(r'^\*\*'+KINDS+r'\s+(\d+)\b', re.I)
    caps=[]
    for idx,l in enumerate(lines):
        mc=capre.match(l.strip())
        if mc: caps.append((idx, mc.group(1).lower().replace('á','a'), mc.group(2)))
    refre=re.compile(r'\b(Figura|Gr[áa]fico|Tabela|Quadro|Mapa)\s+(\d+)\b')
    changes=[]
    def repl_line(idx,l):
        if capre.match(l.strip()): return l
        def r(m):
            kind=m.group(1); k=kind.lower().replace('á','a'); old=m.group(2)
            cands=[c for c in caps if c[1]==k]
            if not cands: return m.group(0)
            best=min(cands, key=lambda c:(abs(c[0]-idx), 0 if c[0]<=idx else 1))
            new=best[2]
            if new!=old:
                changes.append((kind,old,new)); return kind+" "+new
            return m.group(0)
        return refre.sub(r,l)
    lines=[repl_line(i,l) for i,l in enumerate(lines)]
    return '\n'.join(lines), changes

def postprocess(docx_path):
    tmp=tempfile.mkdtemp()
    with zipfile.ZipFile(docx_path) as z: z.extractall(tmp)
    W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    docp=os.path.join(tmp,"word","document.xml"); xml=open(docp,encoding='utf-8').read()
    def fix_grid(m):
        cols=[max(int(float(c)),1000) for c in re.findall(r'<w:gridCol w:w="(\d+(?:\.\d+)?)"',m.group(0))]
        return '<w:tblGrid>'+''.join('<w:gridCol w:w="%d"/>'%c for c in cols)+'</w:tblGrid>'
    xml=re.sub(r'<w:tblGrid>.*?</w:tblGrid>',fix_grid,xml,flags=re.S)
    ibge=('<w:tblBorders>'
      '<w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
      '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
      '<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
      '<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
      '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
      '<w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
      '</w:tblBorders>')
    xml=re.sub(r'<w:sectPr\s*/>','<w:sectPr></w:sectPr>',xml)
    refs='<w:headerReference w:type="default" r:id="rIdHdrTZ"/><w:footerReference w:type="default" r:id="rIdFtrTZ"/>'
    pgmar='<w:pgMar w:top="1701" w:right="1134" w:bottom="1134" w:left="1701" w:header="851" w:footer="851" w:gutter="0"/>'
    def fix_sect(m):
        body=m.group(1)
        body=re.sub(r'<w:headerReference[^>]*/>','',body)
        body=re.sub(r'<w:footerReference[^>]*/>','',body)
        body=re.sub(r'<w:pgMar[^>]*/>','',body)
        return '<w:sectPr>'+refs+pgmar+body+'</w:sectPr>'
    xml=re.sub(r'<w:sectPr[^>]*>(.*?)</w:sectPr>',fix_sect,xml,flags=re.S)
    open(docp,'w',encoding='utf-8').write(xml)
    stp=os.path.join(tmp,"word","styles.xml"); st=open(stp,encoding='utf-8').read()
    st=re.sub(r'<w:rFonts[^/]*/>', '<w:rFonts w:ascii="Aptos" w:hAnsi="Aptos" w:cs="Aptos"/>', st, count=1)
    def _fix_tblstyle(m):
        blk=m.group(0)
        if '<w:tblBorders>' in blk: return blk
        if '<w:tblCellMar>' in blk: return blk.replace('<w:tblCellMar>', ibge+'<w:tblCellMar>',1)
        return blk.replace('</w:tblPr>', ibge+'</w:tblPr>',1)
    st=re.sub(r'<w:style w:type="table"[^>]*w:styleId="Table"[^>]*>.*?</w:style>', _fix_tblstyle, st, flags=re.S)
    if '<w:rPrDefault><w:rPr>' in st and 'w:sz w:val="24"' not in st:
        st=st.replace('<w:rPrDefault><w:rPr>', '<w:rPrDefault><w:rPr><w:sz w:val="24"/><w:szCs w:val="24"/>',1)
    def _fix_ppr(m):
        inner=m.group(1)
        ma=re.search(r'<w:spacing[^>]*w:after="(\d+)"', inner); after=ma.group(1) if ma else '160'
        inner=re.sub(r'<w:spacing[^>]*/>','',inner); inner=re.sub(r'<w:jc[^>]*/>','',inner)
        return '<w:pPrDefault><w:pPr><w:spacing w:after="'+after+'" w:line="360" w:lineRule="auto"/><w:jc w:val="both"/>'+inner+'</w:pPr></w:pPrDefault>'
    if re.search(r'<w:pPrDefault>\s*<w:pPr>.*?</w:pPr>\s*</w:pPrDefault>', st, re.S):
        st=re.sub(r'<w:pPrDefault>\s*<w:pPr>(.*?)</w:pPr>\s*</w:pPrDefault>', _fix_ppr, st, count=1, flags=re.S)
    else:
        st=st.replace('</w:docDefaults>', '<w:pPrDefault><w:pPr><w:spacing w:line="360" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr></w:pPrDefault></w:docDefaults>',1)
    blockstyle=('<w:style w:type="paragraph" w:styleId="BlockText">'
      '<w:name w:val="Block Text"/><w:basedOn w:val="Normal"/>'
      '<w:pPr><w:spacing w:line="240" w:lineRule="auto"/><w:ind w:left="2268"/><w:jc w:val="both"/></w:pPr>'
      '<w:rPr><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>')
    if re.search(r'<w:style w:type="paragraph" w:styleId="BlockText">',st):
        st=re.sub(r'<w:style w:type="paragraph" w:styleId="BlockText">.*?</w:style>', blockstyle, st, flags=re.S)
    else:
        st=st.replace('</w:styles>', blockstyle+'</w:styles>',1)
    open(stp,'w',encoding='utf-8').write(st)
    footer=('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
      '<w:ftr xmlns:w="'+W+'" xmlns:r="'+R+'">'
      '<w:p><w:pPr><w:jc w:val="center"/><w:rPr><w:sz w:val="16"/></w:rPr></w:pPr>'
      '<w:r><w:rPr><w:sz w:val="16"/></w:rPr><w:t xml:space="preserve">'+VERSION+'</w:t></w:r>'
      '</w:p></w:ftr>')
    open(os.path.join(tmp,"word","footer1.xml"),'w',encoding='utf-8').write(footer)
    header=('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
      '<w:hdr xmlns:w="'+W+'" xmlns:r="'+R+'">'
      '<w:p><w:pPr><w:jc w:val="right"/><w:rPr><w:sz w:val="20"/></w:rPr></w:pPr>'
      '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r>'
      '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
      '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:fldChar w:fldCharType="end"/></w:r>'
      '</w:p></w:hdr>')
    open(os.path.join(tmp,"word","header1.xml"),'w',encoding='utf-8').write(header)
    relp=os.path.join(tmp,"word","_rels","document.xml.rels"); rel=open(relp,encoding='utf-8').read()
    add=('<Relationship Id="rIdFtrTZ" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
         '<Relationship Id="rIdHdrTZ" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>')
    rel=rel.replace('</Relationships>',add+'</Relationships>'); open(relp,'w',encoding='utf-8').write(rel)
    ctp=os.path.join(tmp,"[Content_Types].xml"); ct=open(ctp,encoding='utf-8').read()
    add=('<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
         '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>')
    ct=ct.replace('</Types>',add+'</Types>'); open(ctp,'w',encoding='utf-8').write(ct)
    nz=docx_path+".tmp"
    with zipfile.ZipFile(nz,'w',zipfile.ZIP_DEFLATED) as z:
        for root,_,fs in os.walk(tmp):
            for fn in fs: z.write(os.path.join(root,fn),os.path.relpath(os.path.join(root,fn),tmp))
    shutil.move(nz,docx_path); shutil.rmtree(tmp)

pb='```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n'
parts=["% Tarifa Zero e Grupos Econômicos no Brasil\n% Thiago Von Zeidler Gomes\n% Orientadora: Prof.ª Dra. Silvana Zioni · "+VERSION+"\n"]
for f,label in ORDER:
    if not os.path.exists(f): print("FALTA",f,file=sys.stderr); continue
    parts.append(pb+clean(f,label))
def convert_html_tables(md):
    def repl(m):
        r=subprocess.run(["pandoc","-f","html","-t","markdown-raw_html"],input=m.group(0),capture_output=True,text=True)
        return "\n\n"+(r.stdout.strip() or "")+"\n\n"
    return re.sub(r'<table\b.*?</table>',repl,md,flags=re.S|re.I)
combined=number_captions(convert_html_tables('\n\n'.join(parts)))
combined,changes=fix_crossrefs(combined)
os.makedirs(OUTDIR,exist_ok=True)
open('/tmp/tese_leitura.md','w',encoding='utf-8').write(combined)
subprocess.run(["pandoc","/tmp/tese_leitura.md","-f","markdown+raw_html+raw_attribute","-o",OUT,"--toc","--toc-depth=2"],check=True)
postprocess(OUT); snapshot(OUT)
# gera também os anexos como arquivos SEPARADOS (cada um com seu próprio histórico)
for _scr in ["_meta/scripts/exportar_anexo.py","_meta/scripts/exportar_anexo2.py","_meta/scripts/exportar_anexo3.py"]:
    subprocess.run(["python3",_scr],check=True)
if changes:
    print("REFS realinhadas ("+str(len(changes))+"):")
    for kind,old,new in changes: print("  "+kind+" "+old+" -> "+kind+" "+new)
print("OK:",OUT,os.path.getsize(OUT),"bytes")
