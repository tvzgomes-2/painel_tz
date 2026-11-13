#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditor do cofre (Doutorado — Tarifa Zero e Grupos Econômicos).
Read-only: NÃO altera arquivos. Codifica os checks recorrentes da nossa rotina:
  ERROS   → links/embeds quebrados para NOTAS/figuras, frontmatter ausente, truncação/corrupção
  AVISOS  → link quebrado p/ binário (PDF/Office: de-hidratado ou migrado p/ Zotero),
            frontmatter incompleto, números canônicos a revisar (137/168; e 155/170/511/531/536 superados),
            arquivo superado em uso, basenames duplicados (wikilink ambíguo)
  INFO    → figuras sem legenda/fonte, .py que não compila
Uso:  python3 "_meta/scripts/auditar_cofre.py" [--report]
      --report grava também `_meta/Auditoria do cofre — AAAA-MM-DD.md`
Saída: código 1 se houver ERROS (útil para "não encerrar com erro").
"""
import os, re, sys, glob, ast, hashlib
from datetime import date

VAULT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(VAULT)

# diretórios cujo CONTEÚDO não é lido (mas os nomes ainda contam como alvo de link)
# (relatórios de auditoria anteriores citam, como texto, os problemas encontrados —
# incluindo trechos como "[[wikilinks]]" tirados de outras notas; sem essa exclusão,
# cada rodada nova re-lê os relatórios antigos e ecoa/multiplica os mesmos falsos positivos)
SKIP_CONTENT = (".obsidian", ".git", ".trash", "03 - Dados/_data", "02 - Tese/Leitura/Histórico",
                "_meta/Auditoria do cofre", "_meta/_backups", "_meta/_scratch", "_meta/scripts/_scratch")
# ("_scratch" acrescentado em 24/09/2026: saídas intermediárias de scripts — prévias, rascunhos de
# rodada, trechos com [[ aberto — não são notas do cofre; lê-las gerava links "quebrados" que
# atravessavam linhas e avisos de frontmatter sem nada acionável.)
# ("_meta/_backups" acrescentado em 19/09/2026: cada backup é uma foto congelada de uma nota em outro
# momento — ler seu conteúdo re-checa links que já eram quebrados (ou não) naquela data, multiplicando
# falsos positivos a cada nova rodada de backups, sem nada de acionável hoje. Mesma lógica já aplicada
# a "_meta/Auditoria do cofre" acima. O nome da pasta ainda conta como alvo de link, como as demais.)
# não exigir frontmatter nestes caminhos
SKIP_FM = ("_templates", ".obsidian", "LEIA-ME", "README", "CLAUDE.md", "_scratch", "_meta/Auditoria do cofre")
REQUIRED_FM = ("title", "tags", "publish", "created")
SUPERSEDED = "Municípios com Tarifa Zero.xlsx"   # base de 137 (jan/2025), superada
BIB = "05 - Referências/_zotero/biblioteca.bib"
DOC_EXT = (".docx",".doc",".pdf",".pptx",".xlsx",".odt")
VERSION_NOISE = ("versao","versão","cega","final","copia","cópia","autores","com","sem",
 "identificacao","identificação","anpet","scs","ds","rev","draft","v","vf","docx",
 "de","do","da","the","1","2","3")

def rel(p): return p.replace("\\","/")
def skip_content(p): return any(s in rel(p) for s in SKIP_CONTENT)

# ---- índice de nomes (alvos válidos de wikilink): basenames de TODOS os arquivos ----
all_files=[p for p in glob.glob("**/*", recursive=True) if os.path.isfile(p) and ".obsidian" not in rel(p) and "/.git" not in rel(p)]
basenames=set(os.path.basename(p) for p in all_files)
mdnames=set(os.path.splitext(os.path.basename(p))[0] for p in all_files if p.lower().endswith(".md"))
allstems=set(os.path.splitext(os.path.basename(p))[0] for p in all_files)  # nome sem extensão, qualquer tipo
# (Obsidian resolve [[nome]] sem extensão também para não-.md — ex.: [[dashboard]] -> dashboard.html)

# ---- coleta de notas .md legíveis ----
mds=[p for p in all_files if p.lower().endswith(".md") and not skip_content(p)]

erros=[]; avisos=[]; info=[]
_rd_cache={}
def rd(p):
    # cache: cada arquivo é lido só 1x mesmo com várias checagens sobre o mesmo p
    # (script fazia até ~7 leituras do mesmo .md; em pastas sincronizadas via nuvem
    # isso multiplicava a latência de I/O e podia deixar a auditoria muito lenta)
    if p in _rd_cache: return _rd_cache[p]
    try: v = open(p, "rb").read().decode("utf-8","replace")
    except Exception: v = None
    _rd_cache[p]=v
    return v

# ---------- 1) links e embeds ----------
# extensões binárias (não versionadas; podem sair do disco p/ Zotero ou de-hidratar):
# alvo quebrado destes tipos vira AVISO, não ERRO.
BIN_LINK_EXTS={'.pdf','.doc','.docx','.xls','.xlsx','.ppt','.pptx','.odt','.ods','.html','.htm'}
LINK=re.compile(r'(!?)\[\[([^\]\n]+)\]\]')  # wikilink não atravessa linha (24/09/2026: [[ aberto em trecho citado gerava falso 'quebrado')
def mask_code(txt):
    # substitui blocos ```...``` e trechos `inline` por espaços do mesmo comprimento
    # (preserva quebras de linha e todas as posições/índices de caractere) — evita
    # falso positivo de "link/embed quebrado" quando [[...]] ou ![[...]] aparece como
    # TEXTO LITERAL dentro de código (ex.: exemplo de sintaxe numa nota-tutorial, ou
    # um trecho citado num relatório de auditoria anterior), não como wikilink de verdade.
    def blank(m):
        s=m.group(0)
        return "".join(c if c=="\n" else " " for c in s)
    out=re.sub(r'```.*?```', blank, txt, flags=re.S)
    out=re.sub(r'`[^`\n]*`', blank, out)
    return out
def _existe(nome):
    return nome in mdnames or nome in basenames or nome in allstems
def target_ok(t):
    sem_alias = t.split('|')[0].strip()
    if sem_alias == "": return True             # âncora na mesma nota
    if sem_alias.startswith("@"): return True    # citekey Zotero
    # tenta o alvo INTEIRO primeiro — '#' pode ser parte literal do nome do
    # arquivo (ex.: "...(UOL Prime #13, 2024)"), não necessariamente uma âncora
    if _existe(sem_alias): return True
    # só then trata '#' como separador de âncora (sintaxe [[Nota#Seção]])
    sem_ancora = sem_alias.split('#')[0].strip()
    if sem_ancora == "": return True
    return _existe(sem_ancora)
for p in mds:
    txt=rd(p)
    if txt is None: continue
    masked=mask_code(txt)
    for m in LINK.finditer(masked):
        emb, tgt = m.group(1), m.group(2)
        if not target_ok(tgt):
            ln=txt[:m.start()].count("\n")+1
            base=tgt.split('|')[0].strip()
            if not _existe(base):
                base=base.split('#')[0].strip()
            ext=os.path.splitext(base)[1].lower()
            kind='embed' if emb else 'link'
            msg=f"{kind} quebrado: [[{tgt}]] — {rel(p)}:{ln}"
            # alvos binários (PDF/Office) não são versionados e podem estar
            # de-hidratados (OneDrive) ou migrados p/ o Zotero → aviso, não erro.
            if ext in BIN_LINK_EXTS:
                avisos.append(msg+" (binário ausente do disco — de-hidratado/Zotero?)")
            else:
                erros.append(msg)

# ---------- 2) frontmatter ----------
def frontmatter(txt):
    m=re.match(r'^---\n(.*?)\n---\n', txt, re.S)
    return m.group(1) if m else None
for p in mds:
    if any(s in rel(p) for s in SKIP_FM): continue
    txt=rd(p)
    if txt is None: continue
    fm=frontmatter(txt)
    if fm is None:
        # frontmatter aberto mas não fechado = truncação
        if txt.startswith("---") and txt.count("\n---")==0:
            erros.append(f"frontmatter ABERTO e não fechado (possível truncação): {rel(p)}")
        else:
            avisos.append(f"sem frontmatter: {rel(p)}")
        continue
    faltam=[k for k in REQUIRED_FM if not re.search(r'^%s\s*:'%k, fm, re.M)]
    if faltam:
        avisos.append(f"frontmatter incompleto (falta {', '.join(faltam)}): {rel(p)}")

# ---------- 3) truncação / corrupção ----------
for p in mds:
    txt=rd(p)
    if txt is None:
        erros.append(f"ilegível/corrompido: {rel(p)}"); continue
    if len(txt.strip())==0:
        avisos.append(f"arquivo vazio: {rel(p)}"); continue
    if txt.count("```") % 2 != 0:
        erros.append(f"bloco de código ``` não fechado (possível truncação): {rel(p)}")
# scripts .py devem compilar
for p in glob.glob("_meta/scripts/*.py"):
    src=rd(p)
    try: ast.parse(src)
    except SyntaxError as e:
        erros.append(f"script não compila ({e.lineno}: {e.msg}): {rel(p)}")

# ---------- 4) números canônicos (536 vs 137 Santini / 143-186 NTU 2024-2026) ----------
NUM=re.compile(r'(?<!\d)(?<!GE-)(?<!vs\. )(137|143|186|168)(?!\d)')
# exclui "GE-137" (código de grupo econômico, não o achado 137 de Santini) e
# "X vs. 137" (valor de comparação estatística, ex.: taxa de motocicleta por
# 1.000 hab.) — os dois padrões geram falso positivo no check de fonte/edição.
# canônico superado usado como número atual (ver Números canônicos da base-mestre — reconciliação)
CANON_VELHO=re.compile(r'(?<!\d)(155|511|531|536)(?!\d)')
# 25/09/2026: 170 saiu da lista — voltou a ser o número vigente da aba 1 Universal. O número atual passa a ser
# lido da própria planilha (antes estava fixo em 176/175, já defasado), para a mensagem não envelhecer.
def _canon_atual():
    try:
        import openpyxl
        w=openpyxl.load_workbook("03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx",read_only=True)
        rs=list(w["consolidado"].iter_rows(values_only=True)); h=rs[0]; s=h.index("Situação")
        esc=[(r[0],r[1],r[s]) for r in rs[1:] if r[s] in ("Ativa","Encerrada")]
        a=sum(1 for x in esc if x[2]=="Ativa"); e=len(esc)-a
        w2=openpyxl.load_workbook("03 - Dados/_data/casos por fonte/Tipologias TZ - consolidado.xlsx",read_only=True)
        u=sum(1 for _ in w2["1 Universal"].iter_rows())-1
        return f"{len(esc)} registros / {len({(x[0],x[1]) for x in esc})} municípios ({a} ativas + {e} encerradas); aba 1 Universal {u} (planilha, lido agora)"
    except Exception as ex:
        return f"não foi possível ler a planilha ({ex})"
CANON_ATUAL=_canon_atual()
CANON_DATA=re.compile(r'abr/?2026|ago/?2026|03/08/2026|Santini v8|baseline|superad|hist[óo]ric|a revisar')
YEAR=re.compile(r'20(24|25|26)')
for p in mds:
    if not rel(p).startswith("02 - Tese"): continue   # só no texto da tese
    txt=rd(p)
    if txt is None: continue
    for i,l in enumerate(txt.split("\n"),1):
        for m in NUM.finditer(l):
            n=m.group(1); low=l.lower()
            if n=="168":
                avisos.append(f"número 168 SUPERADO (instantâneo não datado do relatório diário NTU; usar 143/186 com edição — ver DB - NTU (série 2024-2026) §3.1): {rel(p)}:{i} — “{l.strip()[:80]}”")
                continue
            if n=="137":
                fonte = "santini" in low
            else:  # 143 ou 186 (NTU 2026) — exige menção à edição/ano na mesma linha
                fonte = ("ntu" in low) and (YEAR.search(l) is not None)
            if not fonte:
                avisos.append(f"número {n} sem citar fonte/edição: {rel(p)}:{i} — “{l.strip()[:80]}”")
        for m in CANON_VELHO.finditer(l):
            if CANON_DATA.search(l): continue
            avisos.append(f"canônico SUPERADO {m.group(1)} sem data/qualificador — atual: {CANON_ATUAL}: {rel(p)}:{i} — “{l.strip()[:80]}”")

# ---------- 5) arquivo superado em uso ----------
for p in mds:
    txt=rd(p)
    if txt and SUPERSEDED in txt and "superad" not in txt.lower() and "não usar" not in txt.lower():
        avisos.append(f"referência ao arquivo SUPERADO '{SUPERSEDED}': {rel(p)}")

# ---------- 6) basenames duplicados (wikilink ambíguo) ----------
from collections import defaultdict
bymd=defaultdict(list)
for p in all_files:
    if p.lower().endswith(".md") and "/.obsidian" not in rel(p) and os.path.basename(p) not in ("LEIA-ME.md","README.md"):
        bymd[os.path.basename(p)].append(rel(p))
so_backup=0
for name,paths in bymd.items():
    if len(paths)>1:
        vivos=[x for x in paths if not x.startswith("_meta/_backups/")]
        if len(vivos)<=1:   # 25/09/2026: cópia só em _meta/_backups não é ambiguidade de trabalho — contar à parte
            so_backup+=1; continue
        avisos.append(f"nota com nome duplicado (link ambíguo) '{name}': "+" | ".join(paths))
if so_backup:
    info.append(f"{so_backup} notas têm cópias apenas em _meta/_backups/ — para o Obsidian não resolver links para elas, excluir a pasta em Configurações > Arquivos e links > Arquivos excluídos")

# ---------- 7) figuras sem legenda/fonte (INFO) ----------
CAP=re.compile(r'\b(Figura|Tabela|Gr[áa]fico|Quadro|Mapa|Organograma|Fluxograma|Esquema)\b', re.I)
for p in mds:
    if not rel(p).startswith("02 - Tese"): continue
    txt=rd(p)
    if txt is None: continue
    lines=txt.split("\n")
    for i,l in enumerate(lines):
        if re.search(r'!\[\[', l):
            janela=" ".join(lines[max(0,i-3):i+4])
            if not CAP.search(janela):
                info.append(f"figura possivelmente sem legenda: {rel(p)}:{i+1}")
            if "fonte" not in janela.lower():
                info.append(f"figura possivelmente sem Fonte: {rel(p)}:{i+1}")

# ---------- 8) citekeys vs biblioteca.bib ----------
bibkeys=set()
if os.path.exists(BIB):
    btxt=rd(BIB) or ""
    bibkeys=set(m.group(1).strip() for m in re.finditer(r'^@\w+\{([^,]+),', btxt, re.M))
    PLACEHOLDERS={"citekey","autor_ano","key","chave","ano"}
    bib_lower={k.lower() for k in bibkeys}
    used=set()
    for p in mds:
        r=rel(p)
        if "_templates" in r or r.startswith("_meta"): continue   # não contar relatórios/templates como "uso"
        txt=rd(p)
        if txt is None: continue
        for m in re.finditer(r'\[\[@([^\]|#]+)', txt): used.add(m.group(1).strip())   # [[@key]]
        for m in re.finditer(r'(?<![\w@])@([a-zA-Z][a-zA-Z0-9_]+\d{4}[a-z]?)\b', txt): used.add(m.group(1).strip())  # @key inline
    for p in mds:
        b=os.path.basename(p)
        if b.startswith("@") and "_templates" not in rel(p): used.add(os.path.splitext(b)[0][1:].strip())  # nota @key.md
    faltam=sorted({k for k in used if k and k.lower() not in PLACEHOLDERS and k.lower() not in bib_lower})
    for k in faltam:
        avisos.append(f"citekey usado sem entrada no .bib: @{k}")
    info.append(f"citekeys no .bib nunca citados no cofre: {len(bib_lower - {u.lower() for u in used})} de {len(bibkeys)}")
else:
    avisos.append(f"biblioteca.bib não encontrado em {BIB}")

# ---------- 9) redundância de artigos / versões ----------
def norm_stem(name):
    st=os.path.splitext(name)[0].lower()
    st=re.sub(r'\(\d{1,2}\)','',st)             # (1), (3) — preserva anos (2025)
    st=re.sub(r'[^a-z0-9áàâãéêíóôõúç]+',' ',st)     # separadores -> espaço
    toks=[t for t in st.split() if t and t not in VERSION_NOISE]
    return " ".join(toks).strip()
GRUPOS_DISTINTOS={"artigo enanpur"}  # ENANPUR 2025 (aceito) e ENANPUR 2027 (em elaboração) são artigos diferentes
groups=defaultdict(list)
for p in all_files:
    if not p.lower().endswith(DOC_EXT): continue
    if "/.obsidian" in rel(p): continue
    # 24/09/2026: versões arquivadas de propósito (_versoes/, _versoes antigas/, _backups) e leituras de
    # terceiros das disciplinas (07 - Disciplinas: capítulos 1-3, partes de apresentação) não são redundância.
    if any(x in rel(p) for x in ("/_versoes/", "/_versoes antigas/", "_meta/_backups/", "07 - Disciplinas/")): continue
    key=norm_stem(os.path.basename(p))
    if key in GRUPOS_DISTINTOS: continue
    if len(key)>=4: groups[key].append(rel(p))
EXPORT_EXT={".doc",".docx",".odt",".rtf",".pptx",".ppt",".pdf"}
def so_exportacao(paths):
    """Mesmo documento na mesma pasta, mudando só a extensão (docx+pdf, pptx+pdf)
    é exportação, não versão redundante. Cópias em pastas diferentes, ou dois
    arquivos da mesma extensão, continuam sendo aviso."""
    if len(paths)<2: return False
    dirs={os.path.dirname(x) for x in paths}
    if len(dirs)!=1: return False
    stems={os.path.splitext(os.path.basename(x))[0].lower() for x in paths}
    if len(stems)!=1: return False
    exts=[os.path.splitext(x)[1].lower() for x in paths]
    return len(exts)==len(set(exts)) and set(exts)<=EXPORT_EXT

for key,paths in sorted(groups.items()):
    if so_exportacao(paths):
        continue
    if len(paths)>=4:
        avisos.append(f"muitas versões do mesmo documento (~'{key}', {len(paths)}): "+" | ".join(sorted(paths)[:6])+(" …" if len(paths)>6 else ""))
    elif len(paths)==2 or len(paths)==3:
        info.append(f"possíveis versões redundantes (~'{key}'): "+" | ".join(sorted(paths)))

# ---------- 10) pastas 'Artigos' paralelas (estrutura redundante) ----------
artdirs=sorted({os.path.dirname(rel(p)).split("/Artigos")[0]+"/Artigos" for p in all_files if "/Artigos/" in rel(p) or rel(p).endswith("/Artigos")})
roots=sorted({d for d in artdirs})
if len({r.split("/Artigos")[0] for r in roots})>1:
    avisos.append("há mais de uma árvore 'Artigos' (consolidar conteúdo × estrutura): "+" | ".join(sorted({r for r in roots})))

# ---------- 11) duplicatas exatas por hash (mesmo conteúdo, nomes diferentes) ----------
# Complementa a seção 9 (que compara nomes normalizados): aqui comparamos bytes,
# então pega duplicata mesmo com nome totalmente diferente. Hoje escopado à pasta de
# normas/contratos (onde já achamos 11 grupos em 19/09/2026); os arquivos resolvidos
# foram movidos para _meta/_backups/, que fica fora deste escopo, então não voltam
# a ser reportados.
HASH_DIRS = ("03 - Dados/_data/Legislacao e contratos TZ",)
HASH_EXT = (".pdf", ".csv", ".xlsx", ".xls", ".json", ".docx", ".doc")
def _hash_arquivo(caminho):
    h = hashlib.md5()
    with open(caminho, "rb") as f:
        for bloco_bytes in iter(lambda: f.read(65536), b""):
            h.update(bloco_bytes)
    return h.hexdigest()
hash_groups = defaultdict(list)
for p in all_files:
    rp = rel(p)
    if not rp.lower().endswith(HASH_EXT): continue
    if not any(rp.startswith(d) for d in HASH_DIRS): continue
    try:
        hash_groups[_hash_arquivo(p)].append(rp)
    except OSError:
        continue
for h, paths in sorted(hash_groups.items()):
    if len(paths) < 2: continue
    avisos.append("duplicata exata por conteúdo (hash igual, nomes diferentes): " + " | ".join(sorted(paths)))

# ---------- relatório ----------
def bloco(titulo, itens, emoji):
    out=[f"## {emoji} {titulo} ({len(itens)})"]
    out += [f"- {x}" for x in itens] if itens else ["- (nenhum)"]
    return "\n".join(out)

resumo=f"Notas .md analisadas: {len(mds)} · ERROS: {len(erros)} · AVISOS: {len(avisos)} · INFO: {len(info)}"
report="\n\n".join([
    "# 🔍 Auditoria do cofre — "+date.today().isoformat(),
    "> Gerado por `_meta/scripts/auditar_cofre.py` (read-only). "+resumo,
    bloco("ERROS (corrigir antes de encerrar)", erros, "🔴"),
    bloco("AVISOS (revisar)", avisos, "🟡"),
    bloco("INFO (melhorias)", info, "🔵"),
])
print(report)

if "--report" in sys.argv:
    outp=os.path.join("_meta", "Auditoria do cofre — "+date.today().isoformat()+".md")
    fm="---\ntitle: \"Auditoria do cofre — %s\"\ntags: [meta, auditoria]\npublish: false\ncreated: %s\n---\n\n" % (date.today().isoformat(), date.today().isoformat())
    open(outp,"w",encoding="utf-8", newline="\n").write(fm+report+"\n")
    print("\n[relatório salvo em] "+outp)

sys.exit(1 if erros else 0)
