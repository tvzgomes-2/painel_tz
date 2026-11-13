#!/usr/bin/env python3
"""
build_referencias.py — lista de referências da tese para a aba "Referências" de Dados e conceitos (13/11/2026).

Lê as REFERÊNCIAS do Volume I mais recente (r-número mais alto, o mesmo critério de build_tese_pdf.py),
parágrafo a parágrafo (estilo "Bibliografia"), guarda o negrito do título (ABNT) e classifica cada
referência. Por decisão do autor, a aba publica SÓ livros (com capítulos de livro), teses e artigos de
periódico; notícias, normas, relatórios, bases de dados, páginas, anais, dissertações e TCC ficam fora.
A classificação é por padrão ABNT (heurística) e o relatório no terminal lista o que caiu em cada grupo,
para conferência. Saída: scripts/referencias_tz.json.
"""
import glob, html, json, os, re, sys, zipfile
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT = os.environ.get('TZ_VAULT') or os.path.join(RAIZ, '..', 'doutorado')
PASTA = os.path.join(VAULT, '01 - Projeto', 'Revisão pré-Silvana (até 06-10)')

def ultimo():
    fs = [f for f in glob.glob(os.path.join(PASTA, '*Tese - Volume I - Texto - r*.docx')) if re.search(r' - r(\d+)\.docx$', f)]
    return max(fs, key=lambda f: int(re.search(r' - r(\d+)\.docx$', f).group(1)))

DOCX = os.environ.get('TZ_TESE_DOCX') or ultimo()
x = zipfile.ZipFile(DOCX).read('word/document.xml').decode('utf-8')
refs = []
dentro = False
for p in re.findall(r'<w:p[ >].*?</w:p>', x, re.S):
    st = re.search(r'<w:pStyle w:val="([^"]+)"', p); st = st.group(1) if st else ''
    txt = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p))
    if st.startswith('Ttulo1') or st.startswith('Heading1'):
        dentro = txt.strip().upper().startswith('REFERÊNCIAS'); continue
    if not dentro or not txt.strip():
        continue
    partes = []
    for r in re.findall(r'<w:r[ >].*?</w:r>', p, re.S):
        t = html.unescape(''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', r)))
        if not t: continue
        neg = re.search(r'<w:b(?: w:val="(?:1|true)")?/>', r) is not None
        partes.append((t, neg))
    refs.append((html.unescape(txt).strip(), partes))

EVENTO = re.compile(r'\bIn:\s*(Anais|ANAIS|Proceedings|\d+o|\d+º|[IVXL]+ |Congresso|Encontro|Semin[aá]rio|Simp[oó]sio|Confer)|Anais d|Congresso|Encontro Nacional|Proceedings', re.I)
def tipo(t):
    if re.search(r'\bTese\b|Tese \(|Doctoral|Ph\.? ?D|Doutorado\)', t) and not re.search(r'Disserta', t):
        return 'tese'
    if re.search(r'Disserta[cç][aã]o|Mestrado\)|Master', t): return 'dissertação'
    if re.search(r'conclus[aã]o de curso|TCC', t, re.I): return 'tcc'
    if EVENTO.search(t): return 'evento'
    if re.search(r'\bIn:\s', t) and re.search(r'\((org|orgs|ed|eds|coord)\.\)|Org\.|\bed\.\)|Handbook', t):
        return 'capítulo'
    # periódico: volume/número/páginas, ou DOI fora de "In:"
    if re.search(r'\bv\.\s?\d+', t) and (re.search(r'\bn\.\s?\d+', t) or re.search(r'\bp\.\s?\d', t) or 'doi' in t.lower()):
        return 'artigo'
    if re.search(r'doi\.org|\bDOI\b', t) and not re.search(r'\bIn:\s', t) and re.search(r'\bp\.\s?\d|\bv\.\s?\d|\bn\.\s?\d', t):
        return 'artigo'
    # notícia: data com dia e mês
    if re.search(r'\b\d{1,2} (jan|fev|mar|abr|maio|jun|jul|ago|set|out|nov|dez)\.? \d{4}', t): return 'notícia'
    # livro: autor pessoa ("SOBRENOME, Nome") + "Local: Editora, ano"
    autor_pessoa = re.match(r"^[A-ZÀ-Ú'’\- ]{2,}, [A-ZÀ-Úa-zà-ú]", t) is not None
    if autor_pessoa and re.search(r'[A-ZÀ-Úa-zà-ú\]\.]+: [^.:;]{2,80}, (c\.)?\d{4}', t):
        return 'livro'
    return 'outro'

# casos que a heurística não pega, conferidos um a um na r103 (13/11/2026): início da referência → tipo
AJUSTE = {
    'DIAS, João Luiz da Silva. Tarifa Zero e Eficiência': 'artigo',
    'DOMINGUES, Letícia Birchal et al. Disputas discursivas': 'artigo',
    'MARICATO, Ermínia. O automóvel e a cidade': 'artigo',
    'MITERHOF, Marcelo. Ônibus gratuito': 'artigo',
    'PIRES, Ailton Brasiliense; NÉSPOLI': 'artigo',
    'SAMPAIO BRITO, Anderson Yago': 'artigo',
    'VILLAR, José Alberto da Costa': 'artigo',
    'FETPESP. A voz dos pioneiros': 'livro',
    'GÔMARA, Antônio Rúbio de Barros': 'livro',
    'IASI, Mauro et al. Cidades rebeldes': 'livro',
    'STIEL, Waldemar Corrêa': 'livro',
    'VASCONCELLOS, Eduardo A. de. Risco no trânsito': 'livro',
    'DOMINGUES, Letícia Birchal. Vale-transporte: Visão geral': 'livro',
    'CARVALHO, Carlos Henrique Ribeiro de. TD 3178': 'texto para discussão',
    'ZIONI, Silvana; SANTINI, Daniel. Tarifa Zero contra a Crise Urbana': 'dossiê (número de revista)',
}
_tipo = tipo
def tipo(t):
    for ini, k in AJUSTE.items():
        if t.startswith(ini): return k
    return _tipo(t)

GRUPO = {'livro': 'livros', 'capítulo': 'livros', 'tese': 'teses', 'artigo': 'artigos'}
saida = {'livros': [], 'teses': [], 'artigos': []}
cont = Counter(); amostra = {}
for t, partes in refs:
    k = tipo(t); cont[k] += 1; amostra.setdefault(k, []).append(t[:150])
    if k not in GRUPO: continue
    h = ''.join(f'<b>{html.escape(s)}</b>' if neg else html.escape(s) for s, neg in partes).replace('</b><b>', '')
    h = re.sub(r'(https?://[^\s<]+[^\s<.,;)])', r'<a href="\1" target="_blank" rel="noopener">\1</a>', h)
    saida[GRUPO[k]].append({'h': h, 'q': t, 'cap': k == 'capítulo'})
# ---- o corpus da revisão sistemática (81 trabalhos, rsl_tz.json): 13/11/2026, a lista sai da aba Literatura
# do painel e vem para cá (decisão do autor). Onde o trabalho está nas referências da tese (mesmo sobrenome,
# ano e palavras do título), usa a referência ABNT; senão, monta "Autoria. Título. Veículo." a partir do
# registro da revisão, sem as notas de trabalho entre parênteses (as longas) — e sem acento, como no registro
# e no Apêndice C da tese, onde esses trabalhos estão listados (não precisam entrar nas REFERÊNCIAS do Volume I).
import unicodedata
def _n(z): return unicodedata.normalize('NFD', z).encode('ascii', 'ignore').decode().upper()
RSL = json.load(open(os.path.join(RAIZ, 'scripts', 'rsl_tz.json'), encoding='utf-8'))
NREF = [(_n(t), t, partes) for t, partes in refs]
def _html(partes):
    h = ''.join(f'<b>{html.escape(z)}</b>' if neg else html.escape(z) for z, neg in partes).replace('</b><b>', '')
    return re.sub(r'(https?://[^\s<]+[^\s<.,;)])', r'<a href="\1" target="_blank" rel="noopener">\1</a>', h)
# pares conferidos à mão (o registro da revisão abrevia o título ou traz outra forma do nome)
PAR = {'Dellheim': 'DELLHEIM, Judith', 'Pereira; Vermander': 'FERNANDES PEREIRA, Thais', 'Higa': 'HIGA, Caio',
       'Mendonca': 'MENDONÇA, Adolfo', 'Silva|Ensaios sobre subsidios': 'SILVA, Denize Mirian',
       'Santini; Gomes': 'SANTINI, Daniel et al. A experiência de Tarifa Zero'}
STOP = set('PARA COM SOBRE DOS DAS NOS NAS UMA COMO ENTRE PELA PELO TARIFA ZERO TRANSPORTE PUBLICO COLETIVO BRASIL'.split())
def par_da_tese(x):
    for k, ini in PAR.items():
        a, _, t = k.partition('|')
        if x['aut'].startswith(a) and (not t or x['tit'].startswith(t)):
            achou = [(tt, pp) for tt, pp in refs if tt.startswith(ini)]
            if len(achou) == 1: return achou[0]
    ano = str(x['ano']); tit = re.sub(r'\s*\([^)]{40,}\)', '', x['tit'])
    pal = [w for w in re.findall(r'[A-Z]{4,}', _n(tit)) if w not in STOP]
    sobs = [_n(a.strip().split(',')[0].split()[-1]) for a in re.split(r';| e ', x['aut']) if a.strip()][:3]
    melhor = None
    for nt, t, pp in NREF:
        if ano not in nt: continue
        sc = sum(w in nt for w in pal) / max(1, len(pal))
        if (any(z and z in nt[:120] for z in sobs) and sc >= 0.5) or (sc >= 0.8 and len(pal) >= 3):
            if not melhor or sc > melhor[0]: melhor = (sc, t, pp)
    return (melhor[1], melhor[2]) if melhor else None
corpus = []; casadas = 0; sem_par = []
for x in RSL['itens']:
    achou = par_da_tese(x)
    if achou:
        t, pp = achou; casadas += 1
        corpus.append({'h': _html(pp), 'q': t, 'sup': x['sup'], 'ano': x['ano'], 'reg': f"{x['aut']} ({x['ano']}). {x['tit']}"})
    else:
        sem_par.append(x)
        tit = re.sub(r'\s*\([^)]{40,}\)', '', x['tit']).strip()
        txt = f"{x['aut']}. {tit}. {x.get('vei') or ''}".strip().rstrip('.') + '.'
        if str(x['ano']) not in txt: txt = txt[:-1] + f', {x["ano"]}.'
        corpus.append({'h': html.escape(f"{x['aut']}. ") + '<b>' + html.escape(tit) + '</b>' + html.escape(txt[len(x['aut']) + 2 + len(tit):]),
                       'q': txt, 'sup': x['sup'], 'ano': x['ano']})
# 13/11/2026 (autor): o corpus não fica numa lista à parte — cada trabalho entra no grupo do seu tipo, com a
# marca RSL. Os que já estão nos grupos (citados na tese como livro, tese ou artigo) só ganham a marca; os
# demais entram pelo tipo do registro da revisão. Dissertações, eventos e relatórios só aparecem quando
# são do corpus (os citados fora dele seguem de fora).
por_q = {r['q']: r for k in ('livros', 'teses', 'artigos') for r in saida[k]}
saida['eventos'] = []; saida['outros'] = []
DESTINO = {'artigo': 'artigos', 'entrevista': 'artigos', 'tese ou dissertação': 'teses', 'congresso': 'eventos'}
for c in corpus:
    if c['q'] in por_q:
        por_q[c['q']]['rsl'] = True
    else:
        saida[DESTINO.get(c['sup'], 'outros')].append({'h': c['h'], 'q': c['q'], 'cap': False, 'rsl': True})
for k in ('livros', 'teses', 'artigos', 'eventos', 'outros'):
    saida[k].sort(key=lambda r: _n(r['q']))
saida['n_corpus'] = len(corpus)
print('com a marca RSL:', {k: sum(1 for r in saida[k] if r.get('rsl')) for k in ('livros', 'teses', 'artigos', 'eventos', 'outros')})
print(f'corpus da revisão: {len(corpus)} trabalhos, {casadas} com a referência ABNT da tese')
saida['sem_par'] = [{'aut': x['aut'], 'ano': x['ano'], 'tit': x['tit'], 'vei': x.get('vei', ''), 'sup': x['sup']} for x in sem_par]
if '-pares' in sys.argv:
    for c in corpus:
        if 'reg' in c: print('REG ', c['reg'][:110]); print('TESE', c['q'][:110]); print()
json.dump({'origem': os.path.basename(DOCX), 'total_tese': len(refs), **saida},
          open(os.path.join(RAIZ, 'scripts', 'referencias_tz.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print(f'referências na tese: {len(refs)} ({os.path.basename(DOCX)})')
for k, n in cont.most_common(): print(f'  {k:12s} {n}')
print('publicadas:', {g: len(v) for g, v in saida.items() if isinstance(v, list)})
if '-v' in sys.argv:
    for k in sys.argv[sys.argv.index('-v') + 1:] or amostra:
        print('\n==', k); print('\n'.join(amostra.get(k, [])))
