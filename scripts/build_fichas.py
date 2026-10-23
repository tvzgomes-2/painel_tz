# -*- coding: utf-8 -*-
"""
build_fichas.py — gera scripts/fichas_tz.json com as fichas municipais do Apêndice D da
tese (Volume II, r92), para a FICHA LATERAL que abre ao selecionar o município no painel
(item 12.10 do ROADMAP; formato decidido pelo autor em 23/10/2026).

Lê o .docx na ordem do documento — parágrafos E tabelas —, porque o quadro "Ficha-resumo"
de cada município é uma tabela e, numa extração só de texto, ele se descola da ficha.

FILTROS (decisões do autor vigentes em 23/10/2026; mudar aqui, nunca à mão no JSON):
  1. Régua ANALÍTICA caso a caso fica fora até a defesa (12.6): sai a linha "Contrapartida"
     do quadro-resumo, os parágrafos de contrapartida/controle social e qualquer posição no
     plano (gestão do comum, garantia de receita sem controle, Bolsa-Empresário).
     Ficam o custeio escrito na lei, a remuneração e os limitantes — descrição contratual,
     a mesma que o painel já publica no "arranjo do contrato".
  2. Grupos econômicos vão para a Rede de empresas: sai a linha "Operador e grupo econômico" e
     todo parágrafo que fala de grupo econômico ou cita código GE-xxx.
  3. Exposição mínima de empresa (decisão de 26/08/2026): CNPJ é retirado do texto.
Cada filtro conta o que removeu, e o relatório final mostra os números.

Uso:  python3 scripts/build_fichas.py        (da raiz do repositório; rodar depois de build_data.py)
"""
import json, os, re, unicodedata
from collections import Counter
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT = os.environ.get('TZ_VAULT') or os.path.join(BASE_DIR, '..', '..', 'doutorado')
DOCX = os.path.join(VAULT, '01 - Projeto', 'Envio à orientadora — 24-11-2026', '01 Tese',
                    '2026-11-24 - Tese - Volume II - Apêndices - r92.docx')
BASE_JSON = os.path.join(BASE_DIR, '..', 'build', 'municipios_dados.json')
OUT = os.path.join(BASE_DIR, 'fichas_tz.json')
VERSAO = 'r92 (envio de 24/11/2026; base de 21/10/2026, alterações até 22/10/2026)'

ALIAS = {'EMBU DAS ARTES|SP': '3515004'}
SECOES = ('Arranjo institucional e operacional', 'Trajetória e mecanismos',
          'Posicionamento nas réguas', 'Literatura e fontes')

def chave(nome, uf):
    s = unicodedata.normalize('NFD', str(nome))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r"[^A-Za-z0-9 ]", ' ', s)
    return re.sub(r'\s+', ' ', s).strip().upper() + '|' + uf.strip().upper()

base = json.load(open(BASE_JSON, encoding='utf-8'))
NOME2COD = {chave(r['nome'], r['uf']): str(r['id']) for r in base}

d = docx.Document(DOCX)
itens = []
for ch in d.element.body.iterchildren():
    tag = ch.tag.split('}')[1]
    if tag == 'p': itens.append(('p', Paragraph(ch, d)))
    elif tag == 'tbl': itens.append(('t', Table(ch, d)))
ini = next(i for i, (k, o) in enumerate(itens) if k == 'p' and o.style.name.startswith('Heading')
           and o.text.strip().startswith('D.2. As fichas'))
fim = next(i for i, (k, o) in enumerate(itens) if k == 'p' and o.style.name.startswith('Heading')
           and o.text.strip().startswith('APÊNDICE E'))

RE_NOME = re.compile(r'^(.{2,60}?) — ([A-Z]{2})$')
RE_UFCAB = re.compile(r'^[A-Z]{2} — .+\(\d+\)$')
RE_GRUPO = re.compile(r'grupos? econ[oô]mic|GE-\d{3}|operador em grupo|\bgrupo (Guanabara|Barata|Belarmino|Gulin|Turin)', re.I)
RE_ANALITICA = re.compile(r'contrapartida|controle social|gest[aã]o do comum|garantia de receita|'
                          r'bolsa[- ]empres[aá]rio|r[ée]gua anal[ií]tica|destinat[aá]rio do recurso', re.I)
RE_CNPJ = re.compile(r'\s*[·(,;]?\s*CNPJ[:\s]*[\dX.\/-]{8,20}\)?|\b\d{2}\.\d{3}\.\d{3}/\d{4}-[\dX]{2}\b')
removidos = Counter()

def limpa(t):
    t2 = RE_CNPJ.sub('', t)
    # restos da própria fonte, onde o número já vinha omitido: "CNPJ (…)", "CNPJ ... confirmado: ."
    t2 = re.sub(r'[;,]?\s*CNPJ \(…\)\)?', '', t2)
    t2 = re.sub(r'\s*CNPJ da contratada agora confirmado:\s*\.', '', t2)
    if t2 != t: removidos['CNPJ retirado do texto'] += 1
    return re.sub(r'\s{2,}', ' ', t2).strip()

fichas, atual, secao, sem_cod = {}, None, None, []
def fecha():
    if atual and atual.get('cod'):
        f = fichas.setdefault(atual['cod'], {'nome': atual['nome'], 'uf': atual['uf'], 'resumo': [], 'blocos': []})
        f['resumo'] += atual['resumo']; f['blocos'] += [b for b in atual['blocos'] if b['itens']]

for k, o in itens[ini + 1:fim]:
    if k == 'p':
        t = o.text.strip()
        if not t or RE_UFCAB.match(t):
            continue
        m = RE_NOME.match(t)
        if m and not t.startswith('•'):
            fecha()
            nome, uf = m.group(1).strip(), m.group(2)
            cod = NOME2COD.get(chave(nome, uf)) or ALIAS.get(chave(nome, uf))
            if not cod: sem_cod.append(f'{nome}/{uf}')
            atual = {'nome': nome, 'uf': uf, 'cod': cod, 'resumo': [], 'blocos': [{'t': 'Síntese', 'itens': []}]}
            secao = atual['blocos'][0]
            continue
        if atual is None:
            continue                       # ressalvas gerais antes da primeira ficha
        if t in SECOES:
            secao = {'t': t, 'itens': []}; atual['blocos'].append(secao); continue
        # registro de trabalho, não texto para o leitor: a evidência do portão traz o log da
        # leitura ("LEITURA 26/09/2026 (noite, 14): ... salvos em normas/SP") e a posição na
        # planilha repete o quadro-resumo
        if t.startswith(('• Evidência do portão', '• Onde o caso está na planilha')) or t == 'Portão de acesso':
            removidos['linha de registro de trabalho'] += 1; continue
        # 23/10/2026: o filtro corta a FRASE, não o parágrafo inteiro — a primeira versão
        # tirava 48 parágrafos e, com eles, trajetória e síntese que só mencionavam o tema
        # de passagem (a síntese de Santa Cruz Cabrália, por exemplo).
        frases = re.split(r'(?<=[.;!?])\s+(?=[A-ZÀ-Ú“"(•])', t)
        fica = []
        for fr in frases:
            if RE_GRUPO.search(fr):
                removidos['frase sobre grupo econômico'] += 1; continue
            if RE_ANALITICA.search(fr):
                removidos['frase de régua analítica / contrapartida'] += 1; continue
            fica.append(fr)
        if not fica:
            continue
        secao['itens'].append(limpa(' '.join(fica)))
    else:
        if atual is None:
            continue
        linhas = [[c.text.strip() for c in r.cells] for r in o.rows]
        if linhas and linhas[0] and linhas[0][0].startswith('Ficha-resumo'):
            for r in linhas[1:]:
                if len(r) < 2: continue
                rot, val = r[0], r[1]
                if rot.lower().startswith('contrapartida'):
                    removidos['linha "Contrapartida" do quadro-resumo'] += 1; continue
                if 'grupo' in rot.lower() or RE_GRUPO.search(val):
                    removidos['linha de grupo econômico do quadro-resumo'] += 1; continue
                atual['resumo'].append([rot, limpa(val)])
        else:
            removidos['outra tabela (não incorporada)'] += 1
fecha()

saida = {'versao': VERSAO, 'fichas': {k: fichas[k] for k in sorted(fichas, key=int)}}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(saida, f, ensure_ascii=False, separators=(',', ':'))
print(f'fichas_tz.json: {len(fichas)} fichas, {os.path.getsize(OUT)/1024:.0f} KB')
print('filtros aplicados:')
for k, v in removidos.most_common(): print(f'   {v:5d}  {k}')
if sem_cod:
    print('  [ERRO] fichas sem município correspondente na base do painel:')
    for n in sem_cod: print('    ', n)
    raise SystemExit('fichas_tz.json gerado, mas há fichas sem código IBGE — acrescentar ao ALIAS.')
