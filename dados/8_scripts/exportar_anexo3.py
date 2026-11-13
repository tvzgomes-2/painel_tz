#!/usr/bin/env python3
# Gera o ANEXO III — RSL completa e fichamentos (Tarifa Zero) em .docx de leitura.
# Fonte única: "02 - Tese/Anexo - RSL completa e fichamentos (Tarifa Zero).md"
# (já é prosa pronta, ao contrário dos Anexos I/II que agregam muitas fichas/registros).
# Formatação ABNT (Aptos 12, 1,5, margens 3-2-3-2, nº topo-direita + rodapé de versão) —
# mesmo padrão dos outros dois anexos e da tese.
import re, os, glob, subprocess, zipfile, shutil, tempfile
from datetime import datetime

# Caminho do cofre: variável de ambiente > caminho do sandbox (se existir) >
# diretório corrente. Mesmo padrão portátil adotado nos outros scripts em 16/09/2026.
_SANDBOX = "/sessions/kind-sleepy-feynman/mnt/doutorado"
VAULT = os.environ.get("TZ_VAULT") or (_SANDBOX if os.path.isdir(_SANDBOX) else os.getcwd())
os.chdir(VAULT)

FIGS = "/tmp/figs"
os.makedirs(FIGS, exist_ok=True)
os.makedirs("02 - Tese/Leitura", exist_ok=True)

SRC = "02 - Tese/Anexo - RSL completa e fichamentos (Tarifa Zero).md"
VERSION = "Anexo III — RSL completa e fichamentos · versão de leitura — " + datetime.now().strftime("%d/%m/%Y")
OUT = "02 - Tese/Leitura/Anexo III - RSL completa e fichamentos (Tarifa Zero).docx"


def snapshot(path):
    hd = os.path.join(os.path.dirname(path) or ".", "Histórico")
    os.makedirs(hd, exist_ok=True)
    stem, ext = os.path.splitext(os.path.basename(path))
    shutil.copy2(path, os.path.join(hd, stem + " — " + datetime.now().strftime("%Y-%m-%d_%H%M") + ext))


def resolve_fig(name):
    raw = name.split('|')[0].split('#')[0].strip()
    stem = re.sub(r'\.(png|jpg|jpeg|svg|gif)$', '', raw, flags=re.I)
    if raw.lower().endswith('.svg'):
        p = os.path.join(FIGS, stem + ".png")
        if not os.path.exists(p):
            hits = glob.glob("_attachments/**/" + stem + ".svg", recursive=True)
            if hits:
                r = subprocess.run(["convert", "-density", "150", hits[0], p], capture_output=True)
                if r.returncode != 0:
                    p = None
        if p and os.path.exists(p):
            return p
    hits = glob.glob("_attachments/**/" + stem + ".*", recursive=True)
    return os.path.abspath(hits[0]) if hits else None


def process_inline(line):
    def emb(mm):
        p = resolve_fig(mm.group(1))
        return ("\n![](<" + p + ">)\n") if p else ("\n*[Figura ausente: " + mm.group(1) + "]*\n")
    line = re.sub(r'!\[\[([^\]]+)\]\]', emb, line)
    line = re.sub(r'\[\[([^\]]+)\]\]', lambda x: x.group(1).split('|')[1] if '|' in x.group(1) else x.group(1).split('#')[0], line)
    line = re.sub(r'</?(span|font|sup|sub)[^>]*>', '', line)
    return line


DROP_CALLOUT = ["vínculo metodológico", "dados e análises relacionados", "a revisar", "dados e analises"]


def clean_body(md):
    lines = md.split('\n')
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        m = re.match(r'^\s*>\s*\[!(\w+)\]([+-]?)\s*(.*)$', line)
        if m:
            typ = m.group(1)
            ttl = (m.group(3) or '').strip()
            if any(k in ttl.lower() or k == typ.lower() for k in DROP_CALLOUT):
                i += 1
                while i < n and lines[i].lstrip().startswith('>'):
                    i += 1
                continue
            i += 1
            body = []
            while i < n and lines[i].lstrip().startswith('>'):
                body.append(re.sub(r'^\s*>\s?', '', lines[i]))
                i += 1
            out.append("")
            if ttl:
                out.append("**" + ttl + "**")
            for b in body:
                if b.strip():
                    out.append(process_inline(b))
            out.append("")
            continue
        out.append(process_inline(line))
        i += 1
    return '\n'.join(out).strip()


def postprocess(docx_path):
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(docx_path) as z:
        z.extractall(tmp)
    W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    docp = os.path.join(tmp, "word", "document.xml")
    xml = open(docp, encoding='utf-8').read()

    def fix_grid(m):
        cols = [max(int(float(c)), 1000) for c in re.findall(r'<w:gridCol w:w="(\d+(?:\.\d+)?)"', m.group(0))]
        return '<w:tblGrid>' + ''.join('<w:gridCol w:w="%d"/>' % c for c in cols) + '</w:tblGrid>'
    xml = re.sub(r'<w:tblGrid>.*?</w:tblGrid>', fix_grid, xml, flags=re.S)
    ibge = ('<w:tblBorders>'
            '<w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
            '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
            '<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            '<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
            '<w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            '</w:tblBorders>')
    xml = re.sub(r'<w:sectPr\s*/>', '<w:sectPr></w:sectPr>', xml)
    refs = '<w:headerReference w:type="default" r:id="rIdHdrTZ"/><w:footerReference w:type="default" r:id="rIdFtrTZ"/>'
    pgmar = '<w:pgMar w:top="1701" w:right="1134" w:bottom="1134" w:left="1701" w:header="851" w:footer="851" w:gutter="0"/>'

    def fix_sect(m):
        body = m.group(1)
        body = re.sub(r'<w:headerReference[^>]*/>', '', body)
        body = re.sub(r'<w:footerReference[^>]*/>', '', body)
        body = re.sub(r'<w:pgMar[^>]*/>', '', body)
        return '<w:sectPr>' + refs + pgmar + body + '</w:sectPr>'
    xml = re.sub(r'<w:sectPr[^>]*>(.*?)</w:sectPr>', fix_sect, xml, flags=re.S)
    open(docp, 'w', encoding='utf-8').write(xml)

    stp = os.path.join(tmp, "word", "styles.xml")
    st = open(stp, encoding='utf-8').read()
    st = re.sub(r'<w:rFonts[^/]*/>', '<w:rFonts w:ascii="Aptos" w:hAnsi="Aptos" w:cs="Aptos"/>', st, count=1)

    def _fix_tblstyle(m):
        blk = m.group(0)
        if '<w:tblBorders>' in blk:
            return blk
        if '<w:tblCellMar>' in blk:
            return blk.replace('<w:tblCellMar>', ibge + '<w:tblCellMar>', 1)
        return blk.replace('</w:tblPr>', ibge + '</w:tblPr>', 1)
    st = re.sub(r'<w:style w:type="table"[^>]*w:styleId="Table"[^>]*>.*?</w:style>', _fix_tblstyle, st, flags=re.S)
    if '<w:rPrDefault><w:rPr>' in st and 'w:sz w:val="24"' not in st:
        st = st.replace('<w:rPrDefault><w:rPr>', '<w:rPrDefault><w:rPr><w:sz w:val="24"/><w:szCs w:val="24"/>', 1)

    def _fix_ppr(m):
        inner = m.group(1)
        ma = re.search(r'<w:spacing[^>]*w:after="(\d+)"', inner)
        after = ma.group(1) if ma else '160'
        inner = re.sub(r'<w:spacing[^>]*/>', '', inner)
        inner = re.sub(r'<w:jc[^>]*/>', '', inner)
        return '<w:pPrDefault><w:pPr><w:spacing w:after="' + after + '" w:line="360" w:lineRule="auto"/><w:jc w:val="both"/>' + inner + '</w:pPr></w:pPrDefault>'
    if re.search(r'<w:pPrDefault>\s*<w:pPr>.*?</w:pPr>\s*</w:pPrDefault>', st, re.S):
        st = re.sub(r'<w:pPrDefault>\s*<w:pPr>(.*?)</w:pPr>\s*</w:pPrDefault>', _fix_ppr, st, count=1, flags=re.S)
    else:
        st = st.replace('</w:docDefaults>', '<w:pPrDefault><w:pPr><w:spacing w:line="360" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr></w:pPrDefault></w:docDefaults>', 1)
    blockstyle = ('<w:style w:type="paragraph" w:styleId="BlockText">'
                  '<w:name w:val="Block Text"/><w:basedOn w:val="Normal"/>'
                  '<w:pPr><w:spacing w:line="240" w:lineRule="auto"/><w:ind w:left="2268"/><w:jc w:val="both"/></w:pPr>'
                  '<w:rPr><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>')
    if re.search(r'<w:style w:type="paragraph" w:styleId="BlockText">', st):
        st = re.sub(r'<w:style w:type="paragraph" w:styleId="BlockText">.*?</w:style>', blockstyle, st, flags=re.S)
    else:
        st = st.replace('</w:styles>', blockstyle + '</w:styles>', 1)
    open(stp, 'w', encoding='utf-8').write(st)

    footer = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
              '<w:ftr xmlns:w="' + W + '" xmlns:r="' + R + '">'
              '<w:p><w:pPr><w:jc w:val="center"/><w:rPr><w:sz w:val="16"/></w:rPr></w:pPr>'
              '<w:r><w:rPr><w:sz w:val="16"/></w:rPr><w:t xml:space="preserve">' + VERSION + '</w:t></w:r>'
              '</w:p></w:ftr>')
    open(os.path.join(tmp, "word", "footer1.xml"), 'w', encoding='utf-8').write(footer)
    header = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
              '<w:hdr xmlns:w="' + W + '" xmlns:r="' + R + '">'
              '<w:p><w:pPr><w:jc w:val="right"/><w:rPr><w:sz w:val="20"/></w:rPr></w:pPr>'
              '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r>'
              '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
              '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:fldChar w:fldCharType="end"/></w:r>'
              '</w:p></w:hdr>')
    open(os.path.join(tmp, "word", "header1.xml"), 'w', encoding='utf-8').write(header)
    relp = os.path.join(tmp, "word", "_rels", "document.xml.rels")
    rel = open(relp, encoding='utf-8').read()
    add = ('<Relationship Id="rIdFtrTZ" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
           '<Relationship Id="rIdHdrTZ" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>')
    rel = rel.replace('</Relationships>', add + '</Relationships>')
    open(relp, 'w', encoding='utf-8').write(rel)
    ctp = os.path.join(tmp, "[Content_Types].xml")
    ct = open(ctp, encoding='utf-8').read()
    add = ('<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
           '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>')
    ct = ct.replace('</Types>', add + '</Types>')
    open(ctp, 'w', encoding='utf-8').write(ct)
    nz = docx_path + ".tmp"
    with zipfile.ZipFile(nz, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, fs in os.walk(tmp):
            for fn in fs:
                z.write(os.path.join(root, fn), os.path.relpath(os.path.join(root, fn), tmp))
    shutil.move(nz, docx_path)
    shutil.rmtree(tmp)


# --- monta o markdown ---
raw = open(SRC, encoding='utf-8', errors='replace').read()
raw = re.sub(r'^---\n.*?\n---\n', '', raw, count=1, flags=re.S)

# título (primeira linha "# ...")
lines = raw.split('\n')
i = 0
while i < len(lines) and not lines[i].startswith('# '):
    i += 1
title = lines[i][2:].strip() if i < len(lines) else "Anexo III — RSL completa e fichamentos"
body_raw = '\n'.join(lines[i + 1:])

# corta a seção "## Ligações" (housekeeping interno do cofre) e tudo depois dela,
# preservando o bloco de autoria que a segue no arquivo-fonte
cut = body_raw.find('\n## Ligações')
if cut != -1:
    body_raw = body_raw[:cut]

body = clean_body(body_raw)
body += "\n\n---\n\n**Autor:** Thiago Von Zeidler Gomes\n**Orientadora:** Prof.ª Silvana Zioni\n"

md = ("% " + title + "\n% Thiago Von Zeidler Gomes\n% Orientadora: Prof.ª Silvana Zioni · " + VERSION + "\n\n"
      "# " + title + "\n\n" + body)


def convert_html_tables(md):
    def repl(m):
        r = subprocess.run(["pandoc", "-f", "html", "-t", "markdown-raw_html"], input=m.group(0), capture_output=True, text=True)
        return "\n\n" + (r.stdout.strip() or "") + "\n\n"
    return re.sub(r'<table\b.*?</table>', repl, md, flags=re.S | re.I)


md = convert_html_tables(md)
open('/tmp/anexo3.md', 'w', encoding='utf-8').write(md)
subprocess.run(["pandoc", "/tmp/anexo3.md", "-f", "markdown+raw_html+raw_attribute", "-o", OUT, "--toc", "--toc-depth=2"], check=True)
postprocess(OUT)
snapshot(OUT)
print("OK:", OUT, os.path.getsize(OUT), "bytes")
