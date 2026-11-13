# build_rsl.py — dados da aba "Literatura" do Painel Brasil (Seção 5.2 e Apêndice C da tese, r103).
# Pedido do autor (24/10/2026): "RSL não está incorporada".
# Fontes: pacote 6 da tese (06 Revisão sistemática da literatura.xlsx — corpus_rsl, citacoes)
# e a matriz de fatores da codificação dos 81 itens (09/10/2026, v2) — o Quadro 7.
# Tudo o que sai daqui é referência bibliográfica pública (autor, ano, título, veículo) e
# contagens; a coluna de posicionalidade e os motivos de exclusão não saem.
import os, json, collections
import pandas as pd
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT = os.environ.get('TZ_VAULT') or os.path.join(BASE_DIR, '..', '..', 'doutorado')
PAC = os.path.join(VAULT, '01 - Projeto', 'Envio à orientadora — 24-11-2026', '02 Bases de dados (xlsx)', '06 Revisão sistemática da literatura.xlsx')
MAT = os.path.join(VAULT, '04 - Análises', 'RSL (revisão sistemática)', 'matriz_fatores_rsl_codificacao_v2_2026-10-09.csv')
OUT = os.path.join(BASE_DIR, 'rsl_tz.json')

c = pd.read_excel(PAC, sheet_name='corpus_rsl')
fich = c[c.estado == 'fichado']
corpus = fich[fich.estrato.astype(str).str.startswith('RSL')].copy()
assert len(c) == 183 and len(fich) == 121 and len(corpus) == 81, (len(c), len(fich), len(corpus))
proc = c.procedimento.fillna('outra').value_counts().to_dict()
funil = {'registros': len(c), 'busca': int(proc.get('busca_de_base', 0)), 'bola': int(proc.get('bola_de_neve', 0)),
         'dossies': int(proc.get('enumeracao_de_volume', 0)),
         'outras': int(len(c) - proc.get('busca_de_base', 0) - proc.get('bola_de_neve', 0) - proc.get('enumeracao_de_volume', 0)),
         'fichados': len(fich), 'excluidos': int((c.estado == 'excluido_apos_leitura').sum()),
         'reclass': int((c.estado == 'reclassificado_db').sum()), 'indisp': int((c.estado == 'indisponivel').sum()),
         'corpus': len(corpus), 'fora_estratos': len(fich) - len(corpus)}
ESTR = {'RSL1': 'Bases indexadas (BDTD/IBICT, SciELO)', 'RSL2': 'Literatura técnico-setorial (ANTP)',
        'RSL3': 'Anais de congressos (ANTP, ANPET, ENANPUR, ANPOCS, ANPAD)', 'RSL4': 'Dossiês temáticos (JOSUM 2023, Diálogos Socioambientais 2025)'}
estratos = [{'k': k, 'rot': ESTR[k], 'n': int((corpus.estrato == k).sum())} for k in ESTR]
anos = corpus.ano.astype(int).value_counts().sort_index()
por_ano = [{'a': int(a), 'n': int(n)} for a, n in anos.items()]
SUP = {'artigo_periodico': 'artigo', 'tese_dissertacao': 'tese ou dissertação', 'comunicacao_congresso': 'congresso',
       'apresentacao_slides': 'apresentação', 'relatorio_tecnico': 'relatório técnico', 'livro_capitulo': 'capítulo de livro',
       'documento_institucional': 'documento institucional', 'entrevista': 'entrevista', 'livro': 'livro', 'documento_tecnico': 'documento técnico'}
txt = lambda v: None if pd.isna(v) else str(v).strip()
itens = [{'id': int(r.id), 'ano': int(r.ano), 'aut': txt(r.autores), 'tit': txt(r.referencia_curta), 'vei': txt(r.veiculo),
          'est': txt(r.estrato), 'sup': SUP.get(txt(r.genero_suporte), txt(r.genero_suporte))}
         for _, r in corpus.sort_values(['ano', 'autores'], ascending=[False, True]).iterrows()]
# Quadro 7: fatores, nº de trabalhos e nº com achado empírico próprio (E)
FAT = {'F1': ('Capacidade fiscal do município', '+', False), 'F2': ('Operação pública ou contrato pago pela oferta', '+', True),
       'F3': ('Decisão política e calendário eleitoral', '+', False), 'F4': ('Ganho de demanda e economia local', '+', True),
       'E1': ('Fonte de custeio dedicada', '+', True), 'E2': ('Crise do sistema ou saída do operador privado', '+', False),
       'E3': ('Mobilização social e conflito tarifário', '+', False),
       'F5': ('Custo do sistema e peso no orçamento', '−', False), 'F6': ('Concessão vigente remunerada por passageiro', '−', True),
       'F7': ('Porte e complexidade operacional', '−', True), 'F8': ('Contestação judicial do custeio', '−', False),
       'F9': ('Poder e resistência dos operadores privados', '−', False), 'E4': ('Preferência por gratuidade focalizada', '−', True)}
mt = pd.read_csv(MAT)
mt = mt[mt.rsl_id.isin(set(corpus.id))]
fatores = []
for k, (rot, sent, novo) in FAT.items():
    d = mt[mt.fator == k]
    fatores.append({'k': k, 'rot': rot, 's': sent, 'novo': novo, 'n': int(d.rsl_id.nunique()),
                    'e': int(d[d.natureza == 'E'].rsl_id.nunique())})
chk = {f['k']: (f['n'], f['e']) for f in fatores}
assert chk['F5'][0] == 27 and chk['F4'][0] == 25 and chk['F9'] == (13, 6) and chk['E2'] == (10, 5), chk   # como na Seção 5.2
# --- municípios por trabalho do corpus (24/10/2026, autor: "literatura aqui não responde à RSL") ---
# Liga cada fichamento ao item do corpus pelo rsl_id do cabeçalho da ficha (norma da RSL: o id
# canônico é o do corpus, e a ficha o espelha) e o nome do município ao código IBGE.
# Grau da menção (pacote 6): A = o trabalho estuda o caso; B = analisa; C = menção de passagem.
import re, unicodedata
NOTAS = os.path.join(VAULT, '05 - Referências', 'Notas de leitura')
fid = {}
for f in os.listdir(NOTAS):
    if f.startswith('Fichamento - ') and f.endswith('.md'):
        with open(os.path.join(NOTAS, f), encoding='utf-8') as h:
            mm = re.search(r'^rsl_id:\s*(\d+)', h.read(4000), re.M)
        if mm: fid[f] = int(mm.group(1))
nrm = lambda t: re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode().lower())
base = json.load(open(os.path.join(BASE_DIR, '..', 'build', 'municipios_dados.json'), encoding='utf-8'))
cod = {(nrm(m['nome']), m['uf']): str(m['id']) for m in base}
cod[(nrm('Embu das Artes'), 'SP')] = cod.get((nrm('Embu'), 'SP'), cod.get((nrm('Embu das Artes'), 'SP')))
ml = pd.read_excel(PAC, sheet_name='municipios_na_literatura')
ml['id'] = ml.fichamento.map(fid)
# ficha sem rsl_id: liga por sobrenome do 1º autor + ano, só quando há UM item do corpus com essa chave
sob = lambda t: nrm(re.split(r'[ ,;]', str(t).strip())[0])
chave_c = collections.Counter((sob(a_), int(y)) for a_, y in zip(corpus.autores, corpus.ano))
id_por_chave = {(sob(a_), int(y)): int(i) for a_, y, i in zip(corpus.autores, corpus.ano, corpus.id) if chave_c[(sob(a_), int(y))] == 1}
def por_chave(f):
    mm = re.match(r'Fichamento - (.+?) \((\d{4})', str(f))
    return id_por_chave.get((sob(mm.group(1)), int(mm.group(2)))) if mm else None
falta = ml.id.isna()
ml.loc[falta, 'id'] = ml.loc[falta, 'fichamento'].map(por_chave)
print(f"fichamentos ligados: por rsl_id {ml.fichamento.map(fid).notna().sum()} linhas; por autor+ano mais {int(falta.sum() - ml.id.isna().sum())}")
ml = ml[ml.id.isin(set(corpus.id))]
mun = collections.defaultdict(dict); sem_cod = set()
for _, r in ml.iterrows():
    c_ = cod.get((nrm(r.municipio), r.uf))
    if not c_: sem_cod.add(f"{r.municipio}/{r.uf}"); continue
    g = str(r.nivel_par)
    old = mun[c_].get(int(r.id))
    if old is None or g < old: mun[c_][int(r.id)] = g
mun = {k: sorted([[i, g] for i, g in v.items()], key=lambda x: (x[1], x[0])) for k, v in mun.items()}
print(f"municípios com algum trabalho do corpus: {len(mun)} | com estudo ou análise (A/B): {sum(1 for v in mun.values() if any(g in 'AB' for _, g in v))} | sem código IBGE: {len(sem_cod)} {sorted(sem_cod)[:6]}")
uni = {str(m['id']) for m in base if m.get('tz_status') == 'Ativa'}
print(f"dos {len(uni)} universais: {len(uni & set(mun))} com algum trabalho identificado; {len(uni - set(mun))} sem (a tese, pela ficha de cada política no Apêndice H, conta 81 citados e 92 sem)")
saida = {'funil': funil, 'estratos': estratos, 'por_ano': por_ano, 'itens': itens, 'fatores': fatores, 'mun': mun,
         'retrato': 'corpus encerrado em 16/09/2026; matriz de fatores de 09/10/2026'}
json.dump(saida, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(f"rsl_tz.json: {os.path.getsize(OUT)/1024:.0f} KB — funil {funil['registros']}→{funil['fichados']}→{funil['corpus']}; estratos {[e['n'] for e in estratos]}; fatores {chk}")
