# -*- coding: utf-8 -*-
"""
build_fichas.py — gera scripts/fichas_tz.json com as fichas municipais do Apêndice D da
tese (Volume II, r92), para a FICHA LATERAL que abre ao selecionar o município no painel
(item 12.10 do ROADMAP; formato decidido pelo autor em 23/10/2026).

Lê o .docx na ordem do documento — parágrafos E tabelas —, porque o quadro "Ficha-resumo"
de cada município é uma tabela e, numa extração só de texto, ele se descola da ficha.

FILTROS (decisões do autor vigentes em 23/10/2026; mudar aqui, nunca à mão no JSON):
  1. Posição no plano da régua ANALÍTICA fica fora (12.6): gestão do comum, garantia de receita
     sem controle, Bolsa-Empresário. Desde 13/11/2026 a contrapartida e o controle social
     ficam (decisão do autor: "atualizar tudo para base nova").
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
# 13/11/2026 (v0.16): as fichas passam a vir do Apêndice H da r103, na base de 11/11/2026
# (na r92 eram o Apêndice D, na base de 21/10). TZ_FICHAS_DOCX aponta para outro arquivo.
DOCX = os.environ.get('TZ_FICHAS_DOCX') or os.path.join(
    VAULT, '01 - Projeto', 'Revisão pré-Silvana (até 06-10)', '2026-12-05 - Tese - Volume II - Apêndices - r103.docx')
BASE_JSON = os.path.join(BASE_DIR, '..', 'build', 'municipios_dados.json')
OUT = os.path.join(BASE_DIR, 'fichas_tz.json')
VERSAO = 'r103 (Apêndice H; base de 11/11/2026)'

ALIAS = {'EMBU DAS ARTES|SP': '3515004'}
SECOES = ('Arranjo institucional e operacional', 'Trajetória e mecanismos',
          'Posicionamento nas réguas', 'Literatura e fontes', 'Base normativa e contratos')
ESTILO_SECAO = 'Subtítulo de ficha'          # r103: o subtítulo de seção tem estilo próprio

# Dados pessoais (13/11/2026). Nenhum nome de sócio pessoa física no site. A fonte (a ficha do
# cofre e o Apêndice H) nomeia a sócia da Bamonte Transportes nos contratos de Alumínio/SP; o
# painel publica o cargo. As trocas abaixo vêm primeiro, com o texto que o autor escolheu; depois,
# qualquer outro nome completo de sócio PF que sobre (fora de razão social e nome de mercado) vira
# "[pessoa física]" — ver pessoas_fisicas.py —, e o relatório lista cada troca.
TROCA_PESSOA = [
    (re.compile(r'por Eliana Martins Pinto Santoni \(sócia proprietária, representante legal da Bamonte Transportes Ltda\.\)'),
     'pela representante legal da Bamonte Transportes Ltda.'),
    (re.compile(r'e Eliana Martins Pinto Santoni \(Bamonte\)'), 'e pela representante legal da Bamonte Transportes Ltda'),
    (re.compile(r'representada por Eliana Martins Pinto Santoni \(sócia proprietária\)'), 'representada por sua sócia proprietária'),
]
from pessoas_fisicas import mascarar
trocas_pessoa = []

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
           and o.text.strip().startswith(('D.2. As fichas', 'H.2. As fichas')))
fim = next(i for i, (k, o) in enumerate(itens) if i > ini and k == 'p' and o.style.name.startswith('Heading')
           and o.text.strip().startswith(('APÊNDICE E', 'H.3.')))

RE_NOME = re.compile(r'^(.{2,60}?) — ([A-Z]{2})$')
RE_UFCAB = re.compile(r'^[A-Z]{2} — .+\(\d+\)$')
RE_GRUPO = re.compile(r'grupos? econ[oô]mic|GE-\d{3}|operador em grupo|\bgrupo (Guanabara|Barata|Belarmino|Gulin|Turin)', re.I)
# 13/11/2026 (v1.0.0, "atualizar tudo para base nova"): a contrapartida e o controle social
# passam a ficar na ficha. Na mesma data, a POSIÇÃO no plano (Seção 7.6) também passou a ser publicada.
RE_ANALITICA = re.compile(r'gest[aã]o do comum|garantia de receita|'
                          r'bolsa[- ]empres[aá]rio|r[ée]gua anal[ií]tica|posi[cç][aã]o no plano', re.I)
RE_CNPJ = re.compile(r'\s*[·(,;]?\s*CNPJ[:\s]*[\dX.\/-]{8,20}\)?|\b\d{2}\.\d{3}\.\d{3}/\d{4}-[\dX]{2}\b')
removidos = Counter()

def limpa(t):
    for rx, novo in TROCA_PESSOA:
        t, n = rx.subn(novo, t)
        if n: trocas_pessoa.append(f'cargo no lugar do nome ({n}x): {novo}')
    t, nomes = mascarar(t)
    trocas_pessoa.extend(f'[pessoa física] no lugar de um nome ({len(n)} letras)' for n in nomes)
    t2 = RE_CNPJ.sub('', t)
    # restos da própria fonte, onde o número já vinha omitido: "CNPJ (…)", "CNPJ ... confirmado: ."
    t2 = re.sub(r'[;,]?\s*CNPJ \(…\)\)?', '', t2)
    t2 = re.sub(r'\s*CNPJ da contratada agora confirmado:\s*\.', '', t2)
    if t2 != t: removidos['CNPJ retirado do texto'] += 1
    return re.sub(r'\s{2,}', ' ', t2).strip()

fichas, atual, secao, sem_cod = {}, None, None, []
truncadas = []
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
        if t in SECOES or o.style.name == ESTILO_SECAO:
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
            # 13/11/2026: a posição no plano passou a ser publicada (alvo e réguas cruzadas no
            # Panorama, seção 3) — o filtro RE_ANALITICA fica só como registro, sem cortar frases.
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
                if 'grupo' in rot.lower() or RE_GRUPO.search(val):
                    removidos['linha de grupo econômico do quadro-resumo'] += 1; continue
                # r103: em duas fichas a célula veio truncada na própria tese (só a primeira letra:
                # "c", "n", "f", "p"). A linha sai do quadro, e o relatório aponta onde corrigir.
                if len(val.strip()) == 1 and val.strip().isalpha():
                    truncadas.append(f"{atual['nome']}/{atual['uf']}: {rot} = {val.strip()!r}"); continue
                atual['resumo'].append([rot, limpa(val)])
        else:
            removidos['outra tabela (não incorporada)'] += 1
fecha()

# r103: a linha "Literatura (revisão sistemática)" do quadro-resumo repete o que o painel já
# mostra na seção de literatura da ficha (a mesma RSL); fica, porque é a contagem da tese.
saida = {'versao': VERSAO, 'fichas': {k: fichas[k] for k in sorted(fichas, key=int)}}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(saida, f, ensure_ascii=False, separators=(',', ':'))
print(f'fichas_tz.json: {len(fichas)} fichas, {os.path.getsize(OUT)/1024:.0f} KB')
print('filtros aplicados:')
for k, v in removidos.most_common(): print(f'   {v:5d}  {k}')
print(f'dados pessoais: {len(trocas_pessoa)} troca(s)')
for k, v in Counter(trocas_pessoa).most_common(): print(f'   {v:5d}  {k}')
if truncadas:
    print(f'  [AVISO] {len(truncadas)} célula(s) truncada(s) no quadro-resumo da tese, fora do painel:')
    for t in truncadas: print('    ', t)
if sem_cod:
    print('  [ERRO] fichas sem município correspondente na base do painel:')
    for n in sem_cod: print('    ', n)
    raise SystemExit('fichas_tz.json gerado, mas há fichas sem código IBGE — acrescentar ao ALIAS.')
