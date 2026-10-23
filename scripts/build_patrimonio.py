# build_patrimonio.py — dados da aba "Além do ônibus" da Rede de empresas (rede-ge.html), Seção 6.4 da tese:
# holdings, financeirização e patrimônio fora do ônibus. Pedido do autor (23/10/2026):
# "adicionar a camada de empresas fora das de transporte (holdings, fundos, financeiras,
# construtoras etc.), talvez em uma nova página".
#
# Cadeia (sempre por empresa; a pessoa no meio nunca sai daqui):
#   grupo (GE) ─ empresa do grupo ─ holding sócia (PJ, fora do recorte de transporte)
#   ─ [sócio da holding: pessoa ou empresa, ANÔNIMO] ─ empresa de qualquer setor (nível 2b)
# Fontes: Tabela mestre v5 (empresa -> grupo), quadro de sócios do recorte de 6 CNAEs,
# sócios das holdings (2ª camada), as 1.164 empresas ligadas aos sócios das holdings
# (levantamento de ago/2026, Teste 16) e a varredura dos sócios dessas empresas (out/2026).
#
# FRONTEIRA DE EXPOSIÇÃO: nenhum nome de pessoa, CPF ou CNPJ. Razão social que leva nome de
# pessoa (empresa individual, "Fulano Empreendimentos") sai mascarada — o teste cruza com
# os nomes de sócios pessoa física de todas as camadas. Vínculo de sócio não é controle.
import os, re, json, collections, unicodedata
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT = os.environ.get('TZ_VAULT') or os.path.join(BASE_DIR, '..', '..', 'doutorado')
F = os.path.join(VAULT, '03 - Dados', '_data', 'CNPJ', 'filtrados (6 CNAEs transporte, 24-07-2026)')
ARSD = os.path.join(VAULT, '03 - Dados', '_data', 'CNPJ', 'ARS - métricas de rede (out-2026)')
V5 = os.path.join(VAULT, '01 - Projeto', 'Envio à orientadora — 24-11-2026', '02 Bases de dados (xlsx)',
                  '04 Grupos econômicos (Tabela mestre v5, 17-10-2026).xlsx')
REDE = os.path.join(BASE_DIR, 'rede_ge.json')
OUT = os.path.join(BASE_DIR, 'patrimonio.json')
z8 = lambda c: str(c).strip().split('.')[0].zfill(8)
EXC = re.compile(r'ASSOCIA|SINDICAT|COOPERATIV|FEDERA[CÇ]|CONS[OÓ]RCIO', re.I)

# --- 1. empresa -> grupo (v5) ---
emp = pd.read_excel(V5, sheet_name='Empresas', usecols=['cnpj_basico', 'id_grupo'], dtype=str)
emp = emp[emp.id_grupo.fillna('').str.startswith('GE')]
g_of = {z8(c): g for c, g in zip(emp.cnpj_basico, emp.id_grupo)}
print('empresas dos grupos (v5):', len(g_of), '| grupos:', len(set(g_of.values())))

# --- 2. sócios das empresas dos grupos; os PJ de fora do recorte são as holdings ---
s1 = pd.read_csv(os.path.join(F, 'socios_filtrado_6cnaes.csv'), dtype=str)
s1.columns = [c.strip().lstrip('﻿') for c in s1.columns]
s1['cnpj_basico'] = s1.cnpj_basico.map(z8)
s1 = s1[s1.cnpj_basico.isin(g_of)]
pj = s1[s1.tipo_socio == 'PJ'].copy()
pj['soc8'] = pj.cnpj_cpf_socio.str.replace(r'\D', '', regex=True).str[:8]
# o "recorte" da tese aqui são as 1.040 empresas dos 327 grupos: sócio PJ que é uma delas é
# sócio cruzado; os demais são as holdings (126 e 361 — a tese diz 360 e anota a recontagem)
univ = set(g_of)
print('vínculos de sócio PJ:', len(pj), '| CNPJs distintos:', pj.soc8.nunique(),
      '| do próprio recorte:', pj[pj.soc8.isin(univ)].soc8.nunique(), '| fora (holdings):', pj[~pj.soc8.isin(univ)].soc8.nunique())
hold = pj[~pj.soc8.isin(univ)]
h_grupos = collections.defaultdict(set)
for h, c in zip(hold.soc8, hold.cnpj_basico): h_grupos[h].add(g_of[c])
e2 = pd.read_csv(os.path.join(F, 'empresas_segunda_camada.csv'), dtype=str)
e2.columns = [c.strip().lstrip('﻿') for c in e2.columns]
e2['cnpj_basico'] = e2.cnpj_basico.map(z8)
nat = dict(zip(e2.cnpj_basico, e2.natureza_juridica)); rz_h = dict(zip(e2.cnpj_basico, e2.razao_social))
NAT = {'2062': 'Sociedade limitada', '2054': 'Sociedade anônima fechada', '2046': 'Sociedade anônima aberta',
       '2240': 'Sociedade simples limitada', '2232': 'Sociedade simples pura', '2216': 'Sociedade em comandita?',
       '2143': 'Cooperativa', '2135': 'Empresário individual', '2305': 'EIRELI', '2313': 'EIRELI'}
fj = collections.Counter(nat.get(h, '?') for h in h_grupos)
print('forma jurídica das holdings:', fj.most_common(8))

# --- 3. sócios das holdings (2ª camada) ---
s2 = pd.read_csv(os.path.join(F, 'socios_segunda_camada.csv'), dtype=str)
s2.columns = [c.strip().lstrip('﻿') for c in s2.columns]
s2['cnpj_basico'] = s2.cnpj_basico.map(z8)
s2 = s2[s2.cnpj_basico.isin(h_grupos) & (s2.qualificacao_socio != '20') & s2.nome_socio_ou_razao_social.notna()]
s2 = s2[~s2.nome_socio_ou_razao_social.str.contains(EXC)]
s2['ident'] = s2.nome_socio_ou_razao_social.str.strip().str.upper() + '|' + s2.cnpj_cpf_socio.astype(str).str.strip()
holds_do_socio = collections.defaultdict(set)
for h, i in zip(s2.cnpj_basico, s2.ident): holds_do_socio[i].add(h)
print('holdings com sócio lido:', s2.cnpj_basico.nunique(), '| sócios de 2ª camada:', s2.ident.nunique())

# --- 4. empresas de qualquer setor com sócio de 2ª camada (nível 2b) ---
e2b = pd.read_csv(os.path.join(F, 'empresas_ligadas_holdings_qualquer_setor.csv'), dtype=str)
e2b['cnpj_basico'] = e2b.cnpj_basico.map(z8)
print('empresas 2b (ago/2026):', len(e2b), '| setores:', e2b.setor.nunique())
raw = pd.read_csv(os.path.join(ARSD, 'socios_empresas_nivel2b_bruto.csv'), sep=';', header=None, dtype=str)
raw.columns = ['cnpj_basico', 'tipo', 'nome', 'doc', 'qualif', 'data', 'pais', 'rep', 'nomerep', 'qrep', 'faixa']
raw['cnpj_basico'] = raw.cnpj_basico.map(z8)
raw = raw[raw.nome.notna()]
raw['ident'] = raw.nome.str.strip().str.upper() + '|' + raw.doc.astype(str).str.strip()
lig = raw[raw.ident.isin(holds_do_socio) & raw.cnpj_basico.isin(set(e2b.cnpj_basico))]
e_hold = collections.defaultdict(lambda: collections.Counter())   # empresa 2b -> holding -> nº de sócios em comum
for c, i in zip(lig.cnpj_basico, lig.ident):
    for h in holds_do_socio[i]: e_hold[c][h] += 1
print('empresas 2b ligadas a uma holding de grupo:', len(e_hold), 'de', len(e2b))

# --- 5. máscara de nome de pessoa nas razões sociais ---
def norm(t): return unicodedata.normalize('NFKD', str(t).upper()).encode('ascii', 'ignore').decode()
pf = list(s1[s1.tipo_socio == 'PF'].nome_socio_ou_razao_social.dropna()) + \
     list(s2[s2.tipo_socio == 'PF'].nome_socio_ou_razao_social.dropna()) + list(raw[raw.tipo == '2'].nome.dropna())
PARES, PRIMEIROS = set(), collections.Counter()
for nm in pf:
    tk = [t for t in re.split(r'[^A-Z]+', norm(nm)) if t]
    if len(tk) >= 2:
        PRIMEIROS[tk[0]] += 1
        for j in range(1, len(tk)):
            if tk[j] not in ('DE', 'DA', 'DO', 'DOS', 'DAS', 'E'): PARES.add((tk[0], tk[j]))
NEG = set('VIACAO TRANSPORTES TRANSPORTE AUTO EXPRESSO EMPRESA RAPIDO CIA COMPANHIA GRUPO SAO SANTA SANTO NOSSA SENHORA BOM NOVA NOVO'.split())
PRIM = {k for k, v in PRIMEIROS.items() if v >= 2 and len(k) >= 3} - NEG
def tem_pessoa(rz):
    n = norm(rz)
    if re.search(r'\d{8,}', n): return True                    # MEI: CPF na razão social
    if re.search(r'&\s*CIA\b|\bE OUTROS\b', n): return True   # "Fulano & Cia", "Fulano e outros"
    tk = [t for t in re.split(r'[^A-Z]+', n) if t]
    sig = [t for t in tk if t not in ('DE', 'DA', 'DO', 'DOS', 'DAS', 'E')]
    for a, b in zip(sig, sig[1:]):
        if (a, b) in PARES: return True
    return bool(sig) and sig[0] in PRIM and len(sig) > 1 and sig[1] not in NEG
MASC = '[razão social com nome de pessoa]'
def nome_pub(rz):
    if not isinstance(rz, str) or not rz.strip(): return None
    if tem_pessoa(rz): return MASC
    # situação processual sai da razão social, como na Rede de empresas
    rz = re.sub(r'\s*-?\s*\b(EM RECUPERACAO JUDICIAL|FALIDO|FALIDA|MASSA FALIDA( DE)?|EM LIQUIDACAO( EXTRAJUDICIAL)?)\b\s*', ' ', rz.strip(), flags=re.I)
    return re.sub(r'\s+', ' ', rz).strip(' -')

# --- 6. setores: "serviços financeiros" separa holding de finança em sentido estrito ---
HOLD_CNAE = {'6461100', '6462000', '6463800'}
def setor_pub(setor, cnae):
    c = str(cnae)
    if setor == 'Serviços financeiros':
        return 'Holdings e participações' if c in HOLD_CNAE else 'Finanças (banco, crédito, seguro, gestão)'
    return setor
e2b['setor_pub'] = [setor_pub(a, b) for a, b in zip(e2b.setor, e2b.cnae)]
fin = e2b[e2b.setor == 'Serviços financeiros']
print('serviços financeiros:', len(fin), '| holdings:', (fin.setor_pub == 'Holdings e participações').sum(), '| estritas:', (fin.setor_pub != 'Holdings e participações').sum())
SIT = {'02': 'ativa', '08': 'baixada', '04': 'inapta', '03': 'suspensa'}

# --- 7. saída por grupo ---
rede = json.load(open(REDE, encoding='utf-8'))
NOS = {n['id']: n for n in rede['nos']}
emp_out, idx = [], {}
for _, r in e2b.iterrows():
    c = r.cnpj_basico
    hs = e_hold.get(c, {})
    gs = sorted({g for h in hs for g in h_grupos[h]})
    idx[c] = len(emp_out)
    emp_out.append({'nome': nome_pub(r.razao_social), 'setor': r.setor_pub, 'uf': r.uf if isinstance(r.uf, str) and re.fullmatch(r'[A-Z]{2}', r.uf) else None,   # linhas com a UF deslocada trazem o CEP
                   
                    'sit': SIT.get(str(r.situacao).zfill(2), 'outra'), 'cnae': str(r.cnae)[:4],
                    'grupos': gs})
hold_out, hidx = [], {}
for h in sorted(h_grupos, key=lambda h: -len(h_grupos[h])):
    hidx[h] = len(hold_out)
    hold_out.append({'nome': nome_pub(rz_h.get(h)) or '[holding sem razão social na base]',
                     'forma': NAT.get(nat.get(h), 'outra'), 'grupos': sorted(h_grupos[h])})
# ligações holding -> empresa 2b (nº de sócios em comum; a pessoa não sai)
lig_out = [[hidx[h], idx[c], k] for c, hc in e_hold.items() if c in idx for h, k in hc.items() if h in hidx]
grupos_out = {}
for g in sorted(NOS):
    hs = [hidx[h] for h in h_grupos if g in h_grupos[h]]
    es = [i for i, e in enumerate(emp_out) if g in e['grupos']]
    if not hs and not es: continue
    grupos_out[g] = {'h': hs, 'e': es}
print('grupos com holding:', sum(1 for v in grupos_out.values() if v['h']), '| com empresa fora do transporte:', sum(1 for v in grupos_out.values() if v['e']))

# pontes: empresas fora do transporte que tocam holdings de 2+ grupos (de unidades distintas)
ub = {g: NOS[g].get('ub') or g for g in NOS}
pontes = collections.Counter()
for e in emp_out:
    us = sorted({ub.get(g, g) for g in e['grupos']})
    if len(us) >= 2:
        for a in range(len(us)):
            for b in range(a + 1, len(us)): pontes[(us[a], us[b])] += 1
# componentes: unidades que se encontram fora do transporte
pai = {}
def raiz(x):
    pai.setdefault(x, x)
    while pai[x] != x: pai[x] = pai[pai[x]]; x = pai[x]
    return x
for (a, b) in pontes: pai[raiz(a)] = raiz(b)
blocos = collections.defaultdict(set)
for (a, b) in pontes: blocos[raiz(a)] |= {a, b}
blocos = sorted((sorted(v) for v in blocos.values()), key=len, reverse=True)
print('pares de unidades com empresa fora do transporte em comum:', len(pontes), '| blocos:', [len(b) for b in blocos[:8]])

setores = collections.Counter(e['setor'] for e in emp_out)
ativas = collections.Counter(e['setor'] for e in emp_out if e['sit'] == 'ativa')
saida = {
    'resumo': {'vinc_pj': int(len(pj)), 'cnpj_pj': int(pj.soc8.nunique()), 'cruzadas': int(pj[pj.soc8.isin(univ)].soc8.nunique()),
               'holdings': len(h_grupos), 'formas': {NAT.get(k, k): v for k, v in fj.most_common()},
               'n_emp': len(emp_out), 'n_ativas': sum(1 for e in emp_out if e['sit'] == 'ativa'),
               'n_ligadas': sum(1 for e in emp_out if e['grupos']), 'n_fin': int(len(fin)),
               'n_fin_hold': int((fin.setor_pub == 'Holdings e participações').sum()),
               'n_mascaradas': sum(1 for e in emp_out if e['nome'] == MASC) + sum(1 for h in hold_out if h['nome'] == MASC)},
    'setores': [{'s': k, 'n': v, 'a': ativas.get(k, 0)} for k, v in setores.most_common()],
    'empresas': emp_out, 'holdings': hold_out, 'lig': lig_out, 'grupos': grupos_out,
    'pontes': [[a, b, k] for (a, b), k in pontes.most_common()], 'blocos': blocos,
    'nomes': {g: {'rot': NOS[g]['rot'], 'mercado': NOS[g].get('mercado'), 'ub': NOS[g].get('ub'), 'topo': NOS[g].get('topo')} for g in grupos_out},
    'unidades': {u['id']: u['nome'] for u in rede['unidades']},
}
json.dump(saida, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
_t = open(OUT, encoding='utf-8').read()
assert not re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}|\*{3}\.?\d{3}\.?\d{3}-?\*{2}', _t), 'CPF na saída'
assert not re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}|"\d{8}"|\d{14}', _t), 'CNPJ na saída'
assert not re.search(r'"[^"]*\d{8,}[^"]*"', _t), 'sequência longa de dígitos em texto'
assert not re.search(r'RECUPERACAO JUDICIAL|FALID', _t), 'situação processual na saída'
print(f'patrimonio.json: {os.path.getsize(OUT)/1024:.0f} KB — empresas {len(emp_out)}, holdings {len(hold_out)}, ligações {len(lig_out)}; mascaradas {saida["resumo"]["n_mascaradas"]}')
