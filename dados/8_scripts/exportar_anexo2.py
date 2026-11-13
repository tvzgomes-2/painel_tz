#!/usr/bin/env python3
# Gera o ANEXO II — Grupos econômicos do transporte coletivo (.docx de leitura).
# Fichas por grupo (identidade histórica + empresas do ranking + sócios-chave),
# abrindo com a "teia" (sócios mais recorrentes na base CNPJ). Formatação ABNT.
import re, os, csv, subprocess, zipfile, shutil, tempfile
from datetime import datetime
import openpyxl
# Caminho do cofre: variável de ambiente > caminho do sandbox (se existir) >
# diretório corrente. O caminho do sandbox estava fixo no código e, rodado na
# máquina do autor, o script morria no os.chdir antes de qualquer coisa.
_SANDBOX="/sessions/kind-sleepy-feynman/mnt/doutorado"
VAULT=os.environ.get("TZ_VAULT") or (_SANDBOX if os.path.isdir(_SANDBOX) else os.getcwd())
os.chdir(VAULT)
os.makedirs("02 - Tese/Leitura",exist_ok=True)
VERSION="Anexo II — Grupos econômicos · versão de leitura — "+datetime.now().strftime("%d/%m/%Y")
OUT="02 - Tese/Leitura/Anexo II - Grupos economicos do transporte coletivo.docx"
def snapshot(path):
    hd=os.path.join(os.path.dirname(path) or ".","Histórico"); os.makedirs(hd,exist_ok=True)
    stem,ext=os.path.splitext(os.path.basename(path))
    shutil.copy2(path, os.path.join(hd, stem+" — "+datetime.now().strftime("%Y-%m-%d_%H%M")+ext))


def na(s): 
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD',str(s or '')) if unicodedata.category(c)!='Mn').lower()

# --- grupos canônicos (Cap 7 §7.2 + identificáveis no ranking) ---
GRUPOS=[
 dict(nome="Guanabara / Real Expresso", fam='Jacob Barata ("rei do ônibus")', base="RJ / interestadual",
   nota="maior grupo do país; teia societária no RJ (Fetranspor/RioCard).", ekw=["familia barata","grupo guanabara","barata"], skw=["barata","guanabara particip"]),
 dict(nome="Comporte", fam='Constantino de Oliveira ("Nenê")', base="MG / SP / DF",
   nota="do ônibus à aviação (Gol).", ekw=["grupo comporte"], skw=["constantino"]),
 dict(nome="Belarmino", fam="Belarmino Ascenção Marta", base="SP / Campinas",
   nota="topo do ranking de vínculos na base CNPJ.", ekw=["belarmino"], skw=["belarmino"]),
 dict(nome="Ruas", fam='José Ruas Vaz ("barão do asfalto")', base="SP (capital)",
   nota="maior operador da capital paulista.", ekw=["ruas"], skw=["ruas"]),
 dict(nome="JCA", fam="Jelson da Costa Antunes", base="interestadual",
   nota="Cometa, Auto Viação 1001, Catarinense.", ekw=["grupo jca"], skw=[]),
 dict(nome="Setti & Braga", fam="família Setti Braga", base="ABC paulista",
   nota="Auto Viação ABC, Metra, Eletra.", ekw=["setti","braga"], skw=["setti braga","braga"]),
 dict(nome="Borborema", fam="família Schwambach", base="PE / Nordeste",
   nota="—", ekw=["borborema","schwambach"], skw=["schwambach"]),
 dict(nome="Lessa Carvalho", fam="família Lessa Carvalho", base="RJ",
   nota="aparece no top-10 de vínculos da base.", ekw=["lessa carvalho"], skw=["lessa carvalho"]),
 dict(nome="Gontijo", fam="família Gontijo", base="MG / SP",
   nota="grande operadora interestadual; incorporou a São Geraldo.", ekw=["gontijo"], skw=["gontijo"]),
 dict(nome="GBS (Garcia / Brasil Sul)", fam="família Boiko", base="PR / Sul",
   nota="Viação Garcia e Expresso Nordeste.", ekw=["grupo gbs","garcia/brasil sul","gbs"], skw=["boiko"]),
 dict(nome="Eucatur", fam="família Gurgacz", base="PR / Norte–Centro-Oeste",
   nota="atuação interestadual.", ekw=["eucatur","gurgacz"], skw=["gurgacz"]),
 dict(nome="Águia Branca", fam="grupo Águia Branca", base="ES",
   nota="líder em passageiros/ano no ranking.", ekw=["aguia branca"], skw=[]),
]
for g in GRUPOS: g['emp']=[]; g['soc']=[]

# --- ranking: mapear empresas a grupos ---
wb=openpyxl.load_workbook("04 - Análises/ranking_50_empresas_onibus_brasil.xlsx", read_only=True, data_only=True)
ws=wb["Ranking consolidado"]; rows=list(ws.iter_rows(values_only=True)); hdr=[str(h).strip() for h in rows[0]]
ci={h:i for i,h in enumerate(hdr)}
def cell(r,k): 
    v=r[ci[k]] if k in ci else None; return str(v).strip() if v not in (None,'') else ''
for r in rows[1:]:
    emp=cell(r,'Empresa (nome no ranking)')
    if not emp: continue
    obs=na(cell(r,'Observações')); pos=cell(r,'Posição'); sede=cell(r,'Sede (Receita)')
    nat=cell(r,'Natureza jurídica'); cnpj=cell(r,'CNPJ')
    for g in GRUPOS:
        if any(k in obs for k in g['ekw']):
            g['emp'].append(dict(pos=pos,emp=emp,sede=sede,nat=nat,cnpj=cnpj)); break

# --- sócios: teia + atribuição ---
socios=[]
with open("03 - Dados/_data/CNPJ/ARS - Sócios/contagem_socios.csv",encoding='utf-8',errors='replace') as f:
    rd=csv.reader(f,delimiter=';'); next(rd)
    for row in rd:
        if len(row)<2: continue
        nm=row[0].split('_')[0].strip()
        try: c=int(row[1])
        except: continue
        socios.append((nm,c))
socios.sort(key=lambda x:-x[1])
for nm,c in socios:
    n=na(nm)
    for g in GRUPOS:
        if any(k in n for k in g['skw']):
            if len(g['soc'])<8 and c>=2: g['soc'].append((nm.title(),c))
            break

# --- monta markdown ---
md=[]
md.append("% Anexo II — Grupos econômicos do transporte coletivo")
md.append("% Thiago Von Zeidler Gomes")
md.append("% Orientadora: Prof.ª Dra. Silvana Zioni · "+VERSION+"\n")
md.append("# Anexo II — Grupos econômicos do transporte coletivo\n")
md.append("Este anexo reúne os grupos econômicos do transporte coletivo urbano identificados "
 "pela pesquisa. A Análise de Redes Sociais sobre o quadro societário da Receita Federal "
 "(CNAE 4921-3/01 e 4921-3/02) detectou **26 clusters** entre os 13.570 sócios distintos; "
 "as fichas a seguir sistematizam os **grupos nomeados** — aqueles com trajetória histórica "
 "documentada e correspondência família ↔ cluster ↔ imprensa. A nomeação completa dos 26 "
 "clusters é tarefa em curso. As empresas listadas por grupo provêm do ranking das 50 maiores "
 "operadoras; os sócios-chave, da contagem de vínculos na base. O travessão (—) indica dado "
 "não disponível. Fonte: elaboração do autor a partir do quadro societário da Receita Federal, "
 "do ranking de operadoras e do levantamento histórico da pesquisa (2026).")

# teia (top 25)
md.append("\n## A teia societária: sócios mais recorrentes na base\n")
md.append("A tabela lista os sócios (pessoas físicas e jurídicas) com maior número de vínculos "
 "a empresas do setor na base CNPJ — o núcleo da concentração societária. Os documentos "
 "(CPF/CNPJ) constam mascarados na base de origem.\n")
md.append("| Sócio | Nº de empresas |")
md.append("|---|---|")
for nm,c in socios[:25]:
    md.append("| %s | %d |" % (nm.title(), c))
md.append("\nFonte: elaboração do autor a partir de `contagem_socios.csv` (Receita Federal, quadro societário).\n")

# fichas por grupo
md.append("\n```{=openxml}\n<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>\n```\n")
md.append("## Fichas por grupo econômico\n")
for g in GRUPOS:
    md.append("\n### %s\n" % g['nome'])
    md.append("**Família / fundador:** %s" % g['fam'] + "\n")
    md.append("**Base:** %s" % g['base'] + "\n")
    md.append("**Nota histórica:** %s" % g['nota'] + "\n")
    if g['emp']:
        md.append("**Empresas identificadas no ranking das 50 maiores**\n")
        for e in g['emp']:
            extra=[x for x in [e['sede'],e['nat']] if x]
            md.append("- **%sº %s** — %s%s" % (e['pos'], e['emp'], ("; ".join(extra)+"" if extra else ""), (" · CNPJ "+e['cnpj'] if e['cnpj'] else "")))
        md.append("")
    if g['soc']:
        md.append("**Sócios-chave na base CNPJ** (nº de empresas vinculadas)\n")
        for nm,c in g['soc']:
            md.append("- %s — %d" % (nm,c))
        md.append("")
    md.append("Fonte: elaboração do autor (ranking de operadoras; quadro societário da Receita Federal; síntese histórica do Cap. 7).\n")

combined="\n".join(md)
open('/tmp/anexo2.md','w',encoding='utf-8').write(combined)
subprocess.run(["pandoc","/tmp/anexo2.md","-f","markdown+raw_attribute","-o",OUT,"--toc","--toc-depth=2"],check=True)

# --- postprocess (mesmo padrão do Anexo I) ---
def postprocess(docx_path):
    tmp=tempfile.mkdtemp()
    with zipfile.ZipFile(docx_path) as z: z.extractall(tmp)
    W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'; R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    docp=os.path.join(tmp,"word","document.xml"); xml=open(docp,encoding='utf-8').read()
    def fix_grid(m):
        cols=[max(int(float(c)),1200) for c in re.findall(r'<w:gridCol w:w="(\d+(?:\.\d+)?)"',m.group(0))]
        return '<w:tblGrid>'+''.join('<w:gridCol w:w="%d"/>'%c for c in cols)+'</w:tblGrid>'
    xml=re.sub(r'<w:tblGrid>.*?</w:tblGrid>',fix_grid,xml,flags=re.S)
    xml=re.sub(r'<w:sectPr\s*/>','<w:sectPr></w:sectPr>',xml)
    refs='<w:headerReference w:type="default" r:id="rIdHdrTZ"/><w:footerReference w:type="default" r:id="rIdFtrTZ"/>'
    pgmar='<w:pgMar w:top="1701" w:right="1134" w:bottom="1134" w:left="1701" w:header="851" w:footer="851" w:gutter="0"/>'
    def fix_sect(m):
        b=m.group(1)
        for pat in (r'<w:headerReference[^>]*/>',r'<w:footerReference[^>]*/>',r'<w:pgMar[^>]*/>'): b=re.sub(pat,'',b)
        return '<w:sectPr>'+refs+pgmar+b+'</w:sectPr>'
    xml=re.sub(r'<w:sectPr[^>]*>(.*?)</w:sectPr>',fix_sect,xml,flags=re.S)
    open(docp,'w',encoding='utf-8').write(xml)
    stp=os.path.join(tmp,"word","styles.xml"); st=open(stp,encoding='utf-8').read()
    st=re.sub(r'<w:rFonts[^/]*/>', '<w:rFonts w:ascii="Aptos" w:hAnsi="Aptos" w:cs="Aptos"/>', st, count=1)
    ibge=('<w:tblBorders><w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
      '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
      '<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/><w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
      '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="808080"/><w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/></w:tblBorders>')
    def _ft(m):
        blk=m.group(0)
        if '<w:tblBorders>' in blk: return blk
        if '<w:tblCellMar>' in blk: return blk.replace('<w:tblCellMar>', ibge+'<w:tblCellMar>',1)
        return blk.replace('</w:tblPr>', ibge+'</w:tblPr>',1)
    st=re.sub(r'<w:style w:type="table"[^>]*w:styleId="Table"[^>]*>.*?</w:style>', _ft, st, flags=re.S)
    if '<w:rPrDefault><w:rPr>' in st and 'w:sz w:val="24"' not in st:
        st=st.replace('<w:rPrDefault><w:rPr>', '<w:rPrDefault><w:rPr><w:sz w:val="24"/><w:szCs w:val="24"/>',1)
    def _fp(m):
        inner=m.group(1); ma=re.search(r'<w:spacing[^>]*w:after="(\d+)"', inner); a=ma.group(1) if ma else '120'
        inner=re.sub(r'<w:spacing[^>]*/>','',inner); inner=re.sub(r'<w:jc[^>]*/>','',inner)
        return '<w:pPrDefault><w:pPr><w:spacing w:after="'+a+'" w:line="360" w:lineRule="auto"/><w:jc w:val="both"/>'+inner+'</w:pPr></w:pPrDefault>'
    if re.search(r'<w:pPrDefault>\s*<w:pPr>.*?</w:pPr>\s*</w:pPrDefault>', st, re.S):
        st=re.sub(r'<w:pPrDefault>\s*<w:pPr>(.*?)</w:pPr>\s*</w:pPrDefault>', _fp, st, count=1, flags=re.S)
    else:
        st=st.replace('</w:docDefaults>','<w:pPrDefault><w:pPr><w:spacing w:line="360" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr></w:pPrDefault></w:docDefaults>',1)
    open(stp,'w',encoding='utf-8').write(st)
    footer=('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:ftr xmlns:w="'+W+'" xmlns:r="'+R+'">'
      '<w:p><w:pPr><w:jc w:val="center"/><w:rPr><w:sz w:val="16"/></w:rPr></w:pPr>'
      '<w:r><w:rPr><w:sz w:val="16"/></w:rPr><w:t xml:space="preserve">'+VERSION+'</w:t></w:r></w:p></w:ftr>')
    open(os.path.join(tmp,"word","footer1.xml"),'w',encoding='utf-8').write(footer)
    header=('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:hdr xmlns:w="'+W+'" xmlns:r="'+R+'">'
      '<w:p><w:pPr><w:jc w:val="right"/><w:rPr><w:sz w:val="20"/></w:rPr></w:pPr>'
      '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r>'
      '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
      '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:fldChar w:fldCharType="end"/></w:r></w:p></w:hdr>')
    open(os.path.join(tmp,"word","header1.xml"),'w',encoding='utf-8').write(header)
    relp=os.path.join(tmp,"word","_rels","document.xml.rels"); rel=open(relp,encoding='utf-8').read()
    rel=rel.replace('</Relationships>',
      '<Relationship Id="rIdFtrTZ" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
      '<Relationship Id="rIdHdrTZ" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/></Relationships>')
    open(relp,'w',encoding='utf-8').write(rel)
    ctp=os.path.join(tmp,"[Content_Types].xml"); ct=open(ctp,encoding='utf-8').read()
    ct=ct.replace('</Types>',
      '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
      '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/></Types>')
    open(ctp,'w',encoding='utf-8').write(ct)
    nz=docx_path+".tmp"
    with zipfile.ZipFile(nz,'w',zipfile.ZIP_DEFLATED) as z:
        for root,_,fs in os.walk(tmp):
            for fn in fs: z.write(os.path.join(root,fn),os.path.relpath(os.path.join(root,fn),tmp))
    shutil.move(nz,docx_path); shutil.rmtree(tmp)
postprocess(OUT); snapshot(OUT)
print("grupos:",len(GRUPOS),"| com empresas:",sum(1 for g in GRUPOS if g['emp']),"| com sócios:",sum(1 for g in GRUPOS if g['soc']),"| OK:",OUT,os.path.getsize(OUT),"bytes")
