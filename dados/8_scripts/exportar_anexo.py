#!/usr/bin/env python3
# Gera o ANEXO I — Fichas municipais de Tarifa Zero (.docx de leitura).
# Uma ficha COMPLETA por município (agrupadas por UF), IBGE da base consolidada,
# conteúdo integral de cada ficha (todos os blocos). Formatação ABNT (Aptos 12, 1,5,
# margens 3-2-3-2, nº topo-direita + rodapé de versão).
#
# ATÉ 21/09/2026 este anexo trazia um RECORTE de 5 seções por ficha (Briefing,
# Principais dados, Legislação, Régua analítica, Grupos econômicos), casadas por
# título normalizado (ver histórico do arquivo). A partir desta data, por decisão
# do autor, o Anexo I passa a trazer a ficha INTEIRA — o mesmo conteúdo que o
# extinto `exportar_fichas_pdf.py` gerava como documento à parte ("Fichas
# municipais de Tarifa Zero — completas", nunca um anexo oficial). Os dois
# scripts foram fundidos: a lógica de corte por bloco (`corpo_da_ficha()`) foi
# trazida para cá, e o `exportar_fichas_pdf.py` foi aposentado (ver
# `_meta/_backups/`).
import re, os, glob, subprocess, zipfile, shutil, tempfile
from datetime import datetime
import openpyxl
# Caminho do cofre: variável de ambiente > caminho do sandbox (se existir) >
# diretório corrente. O caminho do sandbox estava fixo no código e, rodado na
# máquina do autor, o script morria no os.chdir antes de qualquer coisa.
_SANDBOX="/sessions/kind-sleepy-feynman/mnt/doutorado"
VAULT=os.environ.get("TZ_VAULT") or (_SANDBOX if os.path.isdir(_SANDBOX) else os.getcwd())
os.chdir(VAULT)
os.makedirs("02 - Tese/Leitura",exist_ok=True)
VERSION="Apêndice D (volume separado) — Fichas municipais · versão de leitura — "+datetime.now().strftime("%d/%m/%Y")
# Nome do arquivo mantido ("Anexo I") para não quebrar links do cofre; no documento da tese
# o volume é o Apêndice D (revisões r11–r12, 01/10/2026).
OUT="02 - Tese/Leitura/Anexo I - Fichas municipais de Tarifa Zero.docx"
def snapshot(path):
    hd=os.path.join(os.path.dirname(path) or ".","Histórico"); os.makedirs(hd,exist_ok=True)
    stem,ext=os.path.splitext(os.path.basename(path))
    shutil.copy2(path, os.path.join(hd, stem+" — "+datetime.now().strftime("%Y-%m-%d_%H%M")+ext))

FDIR="04 - Análises/Casos municipais/Fichas por município"

def norm(s): return re.sub(r'\s+',' ',str(s or '')).strip().lower()
def delink(s):
    return re.sub(r'\[\[([^\]]+)\]\]',lambda x:x.group(1).split('|')[1] if '|' in x.group(1) else x.group(1).split('#')[0],s)
# --- IBGE + situação da base consolidada ---
wb=openpyxl.load_workbook("03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx", read_only=True, data_only=True)
ws=wb["consolidado"]; rows=list(ws.iter_rows(values_only=True)); hdr=[str(h).strip() for h in rows[0]]
ci={h:idx for idx,h in enumerate(hdr)}
meta={}
for r in rows[1:]:
    m=norm(r[ci['Município']]); uf=str(r[ci['UF']] or '').strip()
    if m: meta[(m,uf)]={'ibge':r[ci['Código IBGE']],'sit':r[ci['Situação']]}

def corpo_da_ficha(txt):
    """Tira frontmatter, o H1 da ficha e tudo a partir do aparato final; rebaixa
    títulos. Função trazida de `exportar_fichas_pdf.py` (aposentado em
    21/09/2026) quando o Anexo I passou a trazer a ficha inteira em vez de um
    recorte de 5 seções.

    O aparato final (pendências + navegação) começa em '## Pendências' no
    esqueleto novo (8 blocos numerados, prosa) ou em '## Ligações' no
    esqueleto antigo (bullets) -- os dois marcam o mesmo ponto de corte: o
    conteúdo do estudo de caso termina ali, tudo depois é ressalva de
    pesquisa ou link de navegação do cofre, nenhum dos dois cabe no anexo.
    Corta no que vier primeiro (greedy até o fim do arquivo, não só até o
    próximo '##' -- no esqueleto novo 'Pendências' é seguido por 'Fichamentos
    e notas relacionadas', que tem que sair junto). O município já entra como
    '### ' no anexo (ver render abaixo), por isso ### -> #####, ## -> ####."""
    t = re.sub(r"^---\n.*?\n---\n", "", txt, count=1, flags=re.S)
    t = re.sub(r"^#\s+.*?$", "", t, count=1, flags=re.M)          # H1 da ficha
    t = re.sub(r"\n##\s*(Pend[êe]ncias|Liga[çc][õo]es)\b.*\Z", "\n", t, flags=re.S)
    t = delink(t)
    # ponteiros "(ver Pendências)" ficam órfãos aqui: apontam para a seção
    # final que este corte acabou de remover. Tira só o ponteiro morto,
    # mantém o sinalizador substantivo que vem antes dele (não apurado /
    # pendente / não lido) -- é esse sinalizador, não o link, que cumpre a
    # regra NA != 0 no anexo. Achado testando a saída real do pipeline
    # pandoc+LibreOffice, não previsto na 1ª rodada de correção do script
    # (21/09/2026).
    t = re.sub(r"\s?\(ver Pend[êe]ncias\.?\)", "", t)
    t = re.sub(r"\s*[—-]\s*ver Pend[êe]ncias\.?(?=\))", "", t)
    t = re.sub(r"\s*[—-]\s*ver Pend[êe]ncias\.?", ".", t)
    t = re.sub(r"\s+\)", ")", t)
    t = re.sub(r"\.\s*\.", ".", t)
    t = re.sub(r"^###\s", "##### ", t, flags=re.M)
    t = re.sub(r"^##\s(?!###)", "#### ", t, flags=re.M)
    # pandoc (leitor "markdown" padrão, não commonmark) só reconhece um título
    # ATX se ele vier depois de linha em branco; sem ela, o "#### 2. ..." é
    # engolido como continuação do parágrafo anterior e sai como texto literal
    # com cerquilhas no PDF. Achado testando a saída real (21/09/2026): boa
    # parte das fichas tem bloco gerado por script colado direto no próximo
    # título, sem linha em branco entre os dois (ex.: "...2024.\n## 2.
    # Principais dados"). Força a linha em branco antes de qualquer título
    # sobrevivente, sem alterar o texto em si.
    t = re.sub(r"([^\n])\n(#{2,6}\s)", r"\1\n\n\2", t)
    return t.strip()


def parse(path):
    t=open(path,encoding='utf-8',errors='replace').read()
    mm=re.search(r'^municipio:\s*(.+)$',t,re.M); uu=re.search(r'^uf:\s*(.+)$',t,re.M)
    mun=(mm.group(1).strip() if mm else os.path.basename(path)); uf=(uu.group(1).strip() if uu else '')
    # a linha "Aparece em (levantamentos)" já vem dentro do corpo (seção de
    # Bibliografia, incluída por inteiro desde 21/09/2026) -- reanexá-la aqui
    # a duplicava (achado testando a saída real: aparecia duas vezes por
    # município, a segunda com o "**" de negrito não fechando direito). Só
    # fazia sentido extraí-la à parte no recorte antigo, que não trazia
    # Bibliografia.
    corpo = corpo_da_ficha(t)
    return {'mun':mun,'uf':uf,'corpo':corpo,'arq':os.path.basename(path)}


# ====================================================================
# 🔴 STUBS DA RSL FICAM FORA DO ANEXO I (decisão do autor, 17/09/2026)
# ====================================================================
# A verificação manual do corpus da RSL criou 57 fichas em 16/09/2026 para
# registrar QUAIS TRABALHOS citam cada município. Elas trazem a tag
# `ficha-auto-rsl` e um aviso dizendo, com todas as letras, que o município
# "não é necessariamente um caso de Tarifa Zero" e que os campos 1-8 não foram
# pesquisados. 56 das 57 NÃO estão na base-mestre — são Rio de Janeiro,
# Salvador, Recife, Porto Alegre, Manaus, Campinas.
#
# Sem este filtro o "Anexo I — Fichas municipais de Tarifa Zero" sairia com 267
# fichas, 57 delas imprimindo praticamente nada sobre cidades sem Tarifa Zero. A
# banca lê o anexo como o universo de casos da pesquisa; seria erro de escopo,
# não de dado.
#
# O corte é pela TAG, não por lista de nomes: quando a ficha for de fato
# pesquisada e a tag sair do frontmatter, ela entra no anexo sozinha. Lista
# manual envelheceria em silêncio.
#
# ⚠️ A TAG SOZINHA NÃO BASTA, e isso foi pego testando, não previsto: das 57
# fichas com a tag, UMA — Itaocara/RJ — ESTÁ na base-mestre, ou seja, é caso
# real de Tarifa Zero cuja ficha por acaso nasceu pelo processo da RSL. Cortar
# só pela tag a deixaria de fora do anexo em silêncio. A segunda condição é
# pertencer à base-mestre: caso de TZ entra sempre, por mais magro que esteja —
# a magreza aparece na própria prosa (blocos curtos, marcadores "não apurado"),
# que é a convenção já adotada.
TAG_STUB = "ficha-auto-rsl"

def eh_stub_rsl(caminho):
    """Stub da RSL = tem a tag E não é caso da base-mestre de Tarifa Zero."""
    try:
        txt = open(caminho, encoding="utf-8", errors="replace").read()
    except OSError:
        return False
    fm = txt.split("---", 2)
    if len(fm) < 3 or TAG_STUB not in fm[1]:
        return False
    mm = re.search(r"^municipio:\s*(.+)$", txt, re.M)
    uu = re.search(r"^uf:\s*(.+)$", txt, re.M)
    if mm and uu and (norm(mm.group(1)), uu.group(1).strip()) in meta:
        return False          # é caso de TZ: entra no anexo
    return True


# glob NAO recursivo, de proposito: as copias de seguranca gravadas pelo
# padronizar_fichas.py ficam em subpasta `_backup-padronizacao-*` DENTRO desta
# pasta. Um rglob aqui duplicaria as fichas corrigidas no anexo.
_todas = [f for f in glob.glob(FDIR+"/*.md") if "MOC" not in f]
_stubs = [f for f in _todas if eh_stub_rsl(f)]
fichas=[parse(f) for f in _todas if f not in _stubs]

# ====================================================================
# 🔴 SÓ A CAMADA 1 ENTRA NO APÊNDICE (decisão do autor, 01/10/2026)
# ====================================================================
# O apêndice de fichas da tese traz apenas os municípios classificados na
# camada 1 (universal) da régua — coluna "Régua — aba" = "1 Universal" da
# base-mestre. Ficam fora as encerradas, as regulamentadas não implantadas,
# os casos excluídos e as fichas de arranjos parciais (camada 2). Para gerar o
# volume com todas as fichas (regra anterior), rodar com TZ_ANEXO_TODAS=1.
_aba = {}
for _r in rows[1:]:
    _m = norm(_r[ci['Município']]); _u = str(_r[ci['UF']] or '').strip()
    if _m: _aba[(_m, _u)] = str(_r[ci['Régua — aba']] or '').strip()
_antes = len(fichas)
if not os.environ.get("TZ_ANEXO_TODAS"):
    fichas = [f for f in fichas if _aba.get((norm(f['mun']), f['uf'])) == '1 Universal']
print("filtro camada 1: %d de %d fichas" % (len(fichas), _antes))
# ordena por UF, depois município
fichas.sort(key=lambda x:(x['uf'], norm(x['mun'])))
ufs=sorted(set(f['uf'] for f in fichas))

# --- monta markdown ---
md=[]
md.append("% Apêndice D — Fichas municipais de Tarifa Zero (volume separado)")
md.append("% Thiago Von Zeidler Gomes")
md.append("% Orientadora: Prof.ª Dra. Silvana Zioni · "+VERSION+"\n")

def load_status():
    p="04 - Análises/Casos municipais/Completude das fichas.md"
    if not os.path.exists(p): return []
    t=re.sub(r'^---\n.*?\n---\n','',open(p,encoding='utf-8',errors='replace').read(),count=1,flags=re.S)
    o=[]; lines=t.split('\n'); i=0; n=len(lines); drop=False
    while i<n:
        ln=lines[i]
        h=re.match(r'^(#{1,6})\s+(.*)$',ln)
        if h:
            txt=h.group(2).strip()
            if txt.lower().startswith('ligações') or txt.lower().startswith('ligações'): drop=True; i+=1; continue
            drop=False
            txt=re.sub(r'^[^0-9A-Za-zÀ-ÿ]+','',txt).strip()
            # rebaixa um nível (o # da nota vira ## sob a seção de status)
            lvl=min(len(h.group(1))+1,4)
            o.append("#"*lvl+" "+txt); i+=1; continue
        if drop: i+=1; continue
        mc=re.match(r'^\s*>\s*\[!(\w+)\]([+-]?)\s*(.*)$',ln)
        if mc:
            ttl=(mc.group(3) or '').strip(); i+=1; body=[]
            while i<n and lines[i].lstrip().startswith('>'):
                body.append(re.sub(r'^\s*>\s?','',lines[i])); i+=1
            o.append("")
            if ttl: o.append("*"+delink(ttl)+"*")
            for b in body:
                if b.strip(): o.append(delink(b))
            o.append(""); continue
        o.append(delink(ln)); i+=1
    return o

# 01/10/2026: o painel de completude (nota de 14/07) é documento de trabalho e está
# defasado frente ao filtro da camada 1 (lista casos parciais como SP, DF, Maceió);
# fica fora do volume da tese. TZ_ANEXO_STATUS=1 o devolve para uso interno.
if os.environ.get("TZ_ANEXO_STATUS")=="1":
    md.append("# Status de completude das fichas\n")
    md += load_status()
    md.append("\n```{=openxml}\n<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>\n```\n")
md.append("# Apêndice D — Fichas municipais de Tarifa Zero (volume separado)\n")
md.append("Este apêndice reúne a **ficha completa** de cada um dos %d municípios do "
    "recorte de Tarifa Zero (todos os blocos da ficha, exceto pendências de "
    "pesquisa e links de navegação do cofre — que não fazem sentido fora dele), "
    "organizadas por unidade da federação. Este documento é parte da tese de "
    "doutorado de Thiago Von Zeidler Gomes (PGT/UFABC, orientação de Silvana "
    "Zioni). Entram só os municípios classificados na camada 1 (universal) da "
    "régua descritiva na base de 11 de outubro de 2026 (base congelada); o código IBGE provém da base-mestre consolidada. "
    "Fonte: elaboração do autor a partir do acervo da pesquisa "
    "(2026)." % len(fichas))
UFNAME={'AC':'Acre','AL':'Alagoas','AM':'Amazonas','AP':'Amapá','BA':'Bahia','CE':'Ceará',
 'DF':'Distrito Federal','ES':'Espírito Santo','GO':'Goiás','MA':'Maranhão','MG':'Minas Gerais',
 'MS':'Mato Grosso do Sul','MT':'Mato Grosso','PA':'Pará','PB':'Paraíba','PE':'Pernambuco',
 'PI':'Piauí','PR':'Paraná','RJ':'Rio de Janeiro','RN':'Rio Grande do Norte','RO':'Rondônia',
 'RR':'Roraima','RS':'Rio Grande do Sul','SC':'Santa Catarina','SE':'Sergipe','SP':'São Paulo','TO':'Tocantins'}
for uf in ufs:
    grp=[f for f in fichas if f['uf']==uf]
    md.append("\n## %s — %s (%d)\n" % (uf, UFNAME.get(uf,uf), len(grp)))
    for f in grp:
        info=meta.get((norm(f['mun']),uf),{})
        ibge=info.get('ibge'); ibge=str(ibge) if ibge not in (None,'') else '—'
        md.append("\n### %s — %s\n" % (f['mun'], uf))
        md.append("**Código IBGE:** %s" % ibge + "\n")
        md.append(f['corpo'] + "\n")
combined="\n".join(md)
# /tmp fixo (herdado da versão anterior) só existia por ter sido escrito e
# testado só no sandbox da nuvem; na máquina do autor (Windows) /tmp não é
# gravável e o script morria aqui. tempfile.gettempdir() resolve para o temp
# real do SO em qualquer ambiente -- achado rodando de verdade pela 1ª vez
# contra o cofre completo na máquina do autor (21/09/2026).
_mdp = os.path.join(tempfile.gettempdir(), "anexo.md")
open(_mdp,'w',encoding='utf-8').write(combined)

subprocess.run(["pandoc",_mdp,"-f","markdown+raw_attribute","-o",OUT,"--toc","--toc-depth=2"],check=True)

# --- postprocess: fonte/margens/entrelinha/rodapé/cabeçalho (subset do export) ---
def postprocess(docx_path):
    tmp=tempfile.mkdtemp()
    with zipfile.ZipFile(docx_path) as z: z.extractall(tmp)
    W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    docp=os.path.join(tmp,"word","document.xml"); xml=open(docp,encoding='utf-8').read()
    xml=re.sub(r'<w:sectPr\s*/>','<w:sectPr></w:sectPr>',xml)
    refs='<w:headerReference w:type="default" r:id="rIdHdrTZ"/><w:footerReference w:type="default" r:id="rIdFtrTZ"/>'
    pgmar='<w:pgMar w:top="1701" w:right="1134" w:bottom="1134" w:left="1701" w:header="851" w:footer="851" w:gutter="0"/>'
    def fix_sect(m):
        body=m.group(1)
        for pat in (r'<w:headerReference[^>]*/>',r'<w:footerReference[^>]*/>',r'<w:pgMar[^>]*/>'):
            body=re.sub(pat,'',body)
        return '<w:sectPr>'+refs+pgmar+body+'</w:sectPr>'
    xml=re.sub(r'<w:sectPr[^>]*>(.*?)</w:sectPr>',fix_sect,xml,flags=re.S)
    open(docp,'w',encoding='utf-8').write(xml)
    stp=os.path.join(tmp,"word","styles.xml"); st=open(stp,encoding='utf-8').read()
    st=re.sub(r'<w:rFonts[^/]*/>', '<w:rFonts w:ascii="Aptos" w:hAnsi="Aptos" w:cs="Aptos"/>', st, count=1)
    if '<w:rPrDefault><w:rPr>' in st and 'w:sz w:val="24"' not in st:
        st=st.replace('<w:rPrDefault><w:rPr>', '<w:rPrDefault><w:rPr><w:sz w:val="24"/><w:szCs w:val="24"/>',1)
    def _fix_ppr(m):
        inner=m.group(1)
        ma=re.search(r'<w:spacing[^>]*w:after="(\d+)"', inner); after=ma.group(1) if ma else '120'
        inner=re.sub(r'<w:spacing[^>]*/>','',inner); inner=re.sub(r'<w:jc[^>]*/>','',inner)
        return '<w:pPrDefault><w:pPr><w:spacing w:after="'+after+'" w:line="360" w:lineRule="auto"/><w:jc w:val="both"/>'+inner+'</w:pPr></w:pPrDefault>'
    if re.search(r'<w:pPrDefault>\s*<w:pPr>.*?</w:pPr>\s*</w:pPrDefault>', st, re.S):
        st=re.sub(r'<w:pPrDefault>\s*<w:pPr>(.*?)</w:pPr>\s*</w:pPrDefault>', _fix_ppr, st, count=1, flags=re.S)
    else:
        st=st.replace('</w:docDefaults>', '<w:pPrDefault><w:pPr><w:spacing w:line="360" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr></w:pPrDefault></w:docDefaults>',1)
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
print("fichas:",len(fichas),"| UFs:",len(ufs),"| OK:",OUT,os.path.getsize(OUT),"bytes")
print("fichas fora do anexo por serem stub da RSL (tag %s): %d" % (TAG_STUB, len(_stubs)))

# --- diagnóstico: fichas com corpo muito curto (podem ser casos pobres de dado
# de verdade, ou sinal de que algo não casou direito) ---
curtas = [(f['mun'], f['uf'], len(f['corpo'])) for f in fichas if len(f['corpo']) < 400]
print("\nfichas com corpo < 400 caracteres (%d):" % len(curtas))
for mun, uf, n in sorted(curtas, key=lambda x: x[2])[:20]:
    print("  %4d chars  %s — %s" % (n, mun, uf))
