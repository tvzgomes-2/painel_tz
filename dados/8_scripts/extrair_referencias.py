#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extrair_referencias.py — extrai a seção de referências de cada item do corpus da RSL
e monta as três tabelas da rede bibliométrica.

Contexto: "05 - Referências/Rede bibliométrica/LEIA-ME.md".

ENTRADA   um diretório com os textos dos itens, nomeados <id>.txt (ex. 22.txt) ou
          os PDFs nomeados <id>.pdf (exige pdfplumber). O id é o do corpus_rsl.csv.
SAÍDA     na pasta da rede: referencias_brutas.csv · citacoes_completas.csv ·
          referencias_distintas.csv

USO   python3 extrair_referencias.py --entrada <dir> [--so-listar]

⚠️ O parser é heurístico: reconhece entrada ABNT (SOBRENOME CAIXA-ALTA),
   anglo-saxã (Sobrenome, N. / Sobrenome, Nome) e repetição de autoria (____).
   SEMPRE conferir o resultado — livros e teses com bibliografia longa produzem
   ruído, e itens sem seção de referências (o GT-VT, que só tem notas de rodapé)
   saem com zero entradas, o que é o resultado correto e não uma falha.
"""
import argparse, csv, collections, os, re, sys, unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REDE = os.path.join(RAIZ, "05 - Referências", "Rede bibliométrica")

CAB = re.compile(r'(REFER[EÊ]NCIAS?|REFERENCES|BIBLIOGRAFIA|BIBLIOGRAPHY|WORKS CITED|'
                 r'/r\.sc/e\.sc/f\.sc/e\.sc/r\.sc/ecircumflex\.sc/n\.sc/c\.sc/i\.sc/a\.sc/s\.sc)', re.I)
FIM = re.compile(r'^\s*(AP[EÊ]NDICE|ANEXO|APPENDIX)\b', re.I)
RUIDO = re.compile(r'^(===PAG|Journal of Sustainable|Rev\. BRas|REV\. BRAS|Revista DELOS|'
                   r'M O B I|MARIANA FIX|ISSN|DOI:|\d{1,3}$)', re.I)
INI    = re.compile(r'^\s{0,10}((?:[A-ZÁÂÃÀÉÊÍÓÔÕÚÜÇ][A-ZÁÂÃÀÉÊÍÓÔÕÚÜÇ\'\-]{1,}\s*){1,4})[,;.]')
INI_EN = re.compile(r'^\s{0,10}[A-ZÁÂÃ][a-zà-ÿ\'\-]{1,22}(\s+[A-ZÁÂÃ][a-zà-ÿ\'\-]{1,22}){0,2},\s*([A-Z]\.|[A-ZÁÂÃ][a-zà-ÿ])')
INI_R  = re.compile(r'^\s{0,10}(_{3,}|-{3,}|―{2,})')
INI_NUM= re.compile(r'^\s{0,10}\[\d{1,3}\]\s')
INI_NUM2=re.compile(r'^\s{0,10}\d{1,3}\.\s+[A-ZÁÂÃÉÍÓÚ]')   # 'N. Autor' (TCRP, relatorios tecnicos)
INI_EN2= re.compile(r"^\s{0,10}[A-ZÁÂÃ][a-zà-ÿ'\-]{2,22}(\s+[A-ZÁÂÃ][a-zà-ÿ'\-]{2,22}){0,2}\s+(?:[A-Z]\.\s*){1,3}(19|20)\d\d")
# Defeito corrigido em 07/09/2026 — tres lacunas do reconhecedor de abertura de
# entrada, encontradas ao ampliar a cobertura de 65 para 83 itens com texto:
#   (a) referencia numerada estilo IEEE ('[1] EU, "Roadmap to a Single...') —
#       item 95 (Fearnley, 2013) devolvia 0 entradas com 18 linhas de bloco;
#   (b) autoria francesa/anglo sem virgula antes da inicial ('Appay A. 2005.') —
#       item 97 (Warin, 2014) devolvia 0 entradas com 24 linhas de bloco;
#   (c) cabecalho de pagina corrente tomado como cabecalho de secao — ver
#       CAB_CORRENTE/CAB_PAG em bloco().
# Sem (a) e (b) o corpus internacional saia artificialmente sem arestas, o que
# reforcava por DEFEITO DE MEDIDA o achado de que "os campos nao se citam".

# Defeito corrigido em 09/09/2026 — duas causas, uma de extracao e uma de parser:
#   (d) PDF de DUAS COLUNAS extraido com 'pdftotext -layout' intercala as colunas:
#       o cabecalho 'References' cai na mesma linha do texto da coluna vizinha e
#       bloco() nao o reconhece (exige linha curta). Sintoma: 31 dos 34 itens com
#       texto novo devolviam 0 entradas — id 66 (Bull et al., RSUE) com bloco=0 e
#       id 80 (Volinski, TCRP) com bloco=738 e ZERO entradas.
#       Solucao: extrair em MODO FLUXO (pdftotext sem -layout) em diretorio proprio,
#       '_meta/textos_rsl_fluxo/', e apontar --entrada para ele. O diretorio -layout
#       ('_meta/textos_rsl/') e preservado: e o que as fichas citaram.
#   (e) referencia numerada 'N. Autor' (TCRP e relatorios tecnicos) — INI_NUM so
#       reconhecia o estilo IEEE '[N]'. Acrescentado INI_NUM2.

def norm(s):
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode()
    return re.sub(r'\s+',' ',s).strip()

def texto(caminho):
    if caminho.endswith(".txt"):
        return open(caminho,encoding="utf-8",errors="replace").read()
    try:
        import pdfplumber
    except ImportError:
        sys.exit("Para ler PDFs é preciso pdfplumber (pip install pdfplumber) — "
                 "ou forneça os textos já extraídos como <id>.txt")
    with pdfplumber.open(caminho) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)

CAB_PAG = re.compile(r'\s\d{1,4}\s*$')

def bloco(txt):
    """Bloco de referencias.

    Regra de escolha do cabecalho (corrigida em 07/09/2026): entre os
    candidatos, descarta-se o que e CABECALHO DE PAGINA CORRENTE — a linha que
    termina em numero de pagina e reaparece tres vezes ou mais no documento
    ("6. Referencias Bibliograficas 85", "... 86", "... 87"). Antes, a regra
    "ultimo cabecalho vence" fazia o ultimo rodape ganhar e o bloco comecava a
    tres linhas do fim: o item 98 (Castro, 2016 — dissertacao de 1.992 linhas)
    devolvia 3 linhas de bloco e 0 entradas. O sintoma e silencioso: a extracao
    nao falha, so devolve quase nada, e o item parece nao citar ninguem."""
    L=txt.split("\n"); ini=None
    def _b(x): return re.sub(r'\s*\d{1,4}\s*$','',x).strip().lower()
    cand=[(i,l.strip()) for i,l in enumerate(L) if len(l.strip())<=60 and CAB.search(l.strip())]
    if cand:
        freq=collections.Counter(_b(c[1]) for c in cand)
        vivos=[c for c in cand if not (CAB_PAG.search(c[1]) and freq[_b(c[1])]>=3)]
        ini=(vivos or cand)[-1][0]+1                      # último cabeçalho não-corrente vence
    if ini is None: return []
    out=[]
    for l in L[ini:]:
        if FIM.match(l.strip()): break
        out.append(l)
    return out

def entradas(L):
    ents=[]; cur=[]
    for l in L:
        raw=l.rstrip()
        if RUIDO.match(raw.strip()): continue
        if INI.match(raw) or INI_EN.match(raw) or INI_R.match(raw) \
           or INI_NUM.match(raw) or INI_NUM2.match(raw) or INI_EN2.match(raw):
            if cur: ents.append(" ".join(cur))
            cur=[raw.strip()]
        elif cur: cur.append(raw.strip())
    if cur: ents.append(" ".join(cur))
    res=[]
    for e in ents:
        e=re.sub(r'^\[\d{1,3}\]\s*','',e)      # marcador IEEE nao e autoria
        e=re.sub(r'\s+',' ',e).strip()
        e=re.sub(r'(Dispon[íi]vel em:.*|Acesso em:.*|Available at:.*|Accessed on:.*)$','',e).strip(' .;,')
        if len(e)<28: continue
        if not re.search(r'\b(19[0-9]{2}|20[0-2][0-9])\b', e) and len(e)<60: continue
        res.append(e[:400])
    return res

def sobrenome(e):
    """Sobrenome da entrada, ou None quando ela abre com travessão de continuação.

    Na ABNT, '______.' no início de uma referência significa 'mesmo autor da
    anterior'. Antes de 03/09/2026 essas entradas caíam no rótulo 'anon' e
    viravam nós órfãos da rede — o que, além de perder a autoria, DUPLICAVA
    obras já presentes sob a chave correta (caso verificado: Harvey, 'O direito
    à cidade', Lutas Sociais 29, 2012, contado como harvey2012 pelo item 28 e
    como anon2012 pelo item 8). Ver a nota de correção na pasta da rede.
    """
    if INI_R.match(e): return None
    m=re.match(r"^([A-Za-zÁÂÃÀÉÊÍÓÔÕÚÜÇáâãàéêíóôõúüç'\-]+)", e)
    return norm(m.group(1)).lower() if m else "anon"

SER_ANO = re.compile(r'(?:\bn\.|\bnº|\bno\.|\bnum\.|\bTD|\bv\.|\bvol\.|\bp\.)\s*°?\s*$', re.I)
FAIXA_ANO = re.compile(r'\b(19[0-9]{2}|20[0-2][0-9])\s*[-–—/]\s*(?:19[0-9]{2}|20[0-2][0-9]|[0-9]{2})\b')
ANO = re.compile(r'\b(19[0-9]{2}|20[0-2][0-9])\b')

def ano_de(e):
    """Ano de publicacao da entrada.

    Correcao de 04/09/2026. O criterio anterior era "o primeiro ano da string",
    e ele errava em dois casos: numero de serie lido como ano ("TD n. 1966",
    de onde vinha camarano1966) e intervalo do titulo lido como ano
    ("(1992-2009)", de onde vinha pereira1992). Agora devolve o primeiro ano
    que NAO esteja dentro de um intervalo AAAA-AAAA/AAAA-AA nem venha logo
    depois de um marcador de serie. Mantem-se "o primeiro" e nao "o ultimo"
    porque parte das entradas sai da extracao com duas referencias coladas, e
    o ultimo ano seria o da referencia seguinte.
    Ver _meta/scripts/corrigir_ano_citekey.py, que aplicou a mesma regra
    retroativamente aos CSVs ja gerados.
    """
    faixas=[(m.start(),m.end()) for m in FAIXA_ANO.finditer(e)]
    for m in ANO.finditer(e):
        s=m.start()
        if any(a<=s<b for a,b in faixas): continue
        if SER_ANO.search(e[max(0,s-12):s].rstrip()): continue
        return m.group(1)
    achados=ANO.findall(e)
    return achados[0] if achados else "sd"

def chave(e, anterior=None):
    sob=sobrenome(e)
    if sob is None:
        sob = anterior or "anon"
    return f"{sob}{ano_de(e)}"

def chaves(es):
    """Chaves de uma lista de entradas NA ORDEM DO ORIGINAL.

    A ordem importa: o travessão só resolve contra a entrada imediatamente
    anterior da mesma lista de referências.
    """
    out=[]; ult=None
    for e in es:
        k=chave(e, ult)
        s=sobrenome(e)
        if s is not None and s!="anon": ult=s
        out.append(k)
    return out

def mapa_corpus():
    """chave normalizada -> id do corpus.

    Deriva do primeiro sobrenome + ano, e acrescenta as chaves da coluna
    'chaves_alternativas' — necessária porque o campo cita com data errada
    (Caribe 2021 em vez de 2019), edicao diferente ou entidade (NTU 2023/2025/2026).
    """
    m={}
    with open(os.path.join(REDE,"corpus_rsl.csv"),encoding="utf-8-sig") as f:
        for r in csv.DictReader(f,delimiter=";"):
            prim=re.split(r'[;,]', r["autores"].strip('" '))[0]
            prim=re.sub(r'\bet\s*al\.?', '', prim, flags=re.I)          # remove "et al."
            prim=norm(prim).strip().split()[0] if norm(prim).strip() else ""
            sob=re.sub(r'[^a-z]','', prim.lower())
            if sob: m[f"{sob}{r['ano']}"]=r["id"]
            for alt in (r.get("chaves_alternativas") or "").split(","):
                alt=alt.strip().lower()
                if alt: m[alt]=r["id"]
    return m

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--entrada",required=True,help="diretório com <id>.txt ou <id>.pdf")
    p.add_argument("--so-listar",action="store_true",help="só relata a contagem, não grava")
    a=p.parse_args()
    arqs=sorted(os.listdir(a.entrada))
    rows=[]
    for nome in arqs:
        cid,ext=os.path.splitext(nome)
        if ext.lower() not in (".txt",".pdf"): continue
        b=bloco(texto(os.path.join(a.entrada,nome))); es=entradas(b)
        print(f"{cid:>6}  bloco={len(b):>5}  entradas={len(es):>4}"
              + ("   ⚠️ zero — conferir se o item tem seção de referências" if not es else ""))
        for e,k in zip(es, chaves(es)): rows.append({"id_origem":cid,"chave":k,"referencia":e})
    if a.so_listar: return
    CORPUS=mapa_corpus()
    with open(os.path.join(REDE,"referencias_brutas.csv"),"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["id_origem","chave","referencia"],delimiter=";")
        w.writeheader(); w.writerows(rows)
    vistos=set(); out=[]
    for r in rows:
        k=(r["id_origem"],r["chave"])
        if k in vistos: continue
        vistos.add(k)
        out.append({"id_origem":r["id_origem"],"chave_citada":r["chave"],
                    "id_corpus_citado":CORPUS.get(r["chave"],""),
                    "tipo":"interno" if r["chave"] in CORPUS else "externo",
                    "referencia":r["referencia"]})
    freq=collections.Counter(o["chave_citada"] for o in out)
    for o in out: o["cocitacoes"]=freq[o["chave_citada"]]
    out.sort(key=lambda o:(int(o["id_origem"]) if o["id_origem"].isdigit() else 99,
                           -o["cocitacoes"], o["chave_citada"]))
    with open(os.path.join(REDE,"citacoes_completas.csv"),"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["id_origem","chave_citada","id_corpus_citado","tipo",
                                       "cocitacoes","referencia"],delimiter=";")
        w.writeheader(); w.writerows(out)
    prim={}
    for o in out: prim.setdefault(o["chave_citada"],o)
    dist=[{"chave":k,"cocitacoes":freq[k],"no_corpus":v["id_corpus_citado"],
           "citada_por":",".join(sorted({x["id_origem"] for x in out if x["chave_citada"]==k},
                                        key=lambda s:(len(s),s))),
           "referencia":v["referencia"]} for k,v in prim.items()]
    dist.sort(key=lambda d:(-d["cocitacoes"], d["chave"]))
    with open(os.path.join(REDE,"referencias_distintas.csv"),"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["chave","cocitacoes","no_corpus","citada_por","referencia"],delimiter=";")
        w.writeheader(); w.writerows(dist)
    print(f"\ncitações: {len(out)} · referências distintas: {len(dist)} · "
          f"internas ao corpus: {sum(1 for o in out if o['tipo']=='interno')}")
    print("gravado em 05 - Referências/Rede bibliométrica/")

if __name__=="__main__": main()
