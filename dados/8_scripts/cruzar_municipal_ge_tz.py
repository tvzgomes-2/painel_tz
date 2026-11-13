import openpyxl, unicodedata, json, re
import pandas as pd
import geopandas as gpd
from scipy.stats import chi2_contingency

def norm(s):
    s = str(s).strip().upper()
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

BASE = "/sessions/kind-sleepy-feynman/mnt/doutorado"
DADOS = f"{BASE}/03 - Dados/_data/casos por fonte"

gdf = gpd.read_file(f"{BASE}/03 - Dados/_data/espacial/BR_Municipios_2022.shp")
name_lookup = {(norm(r['NM_MUN']), r['SIGLA_UF']): str(r['CD_MUN']) for _, r in gdf.iterrows()}
def resolve_nome_uf(nome, uf):
    return name_lookup.get((norm(nome), str(uf).strip()))

base = pd.read_csv(f"{BASE}/03 - Dados/_data/Base Municipal v3/base_municipal_v3.csv", dtype={'cod_ibge': str}, low_memory=False)
base = base[['cod_ibge', 'uf', 'pop_2022']].copy()
base['cod_ibge'] = base['cod_ibge'].astype(str)

uf_regiao = {
 'SP':'Sudeste','RJ':'Sudeste','MG':'Sudeste','ES':'Sudeste',
 'PR':'Sul','SC':'Sul','RS':'Sul',
 'MT':'Centro-Oeste','MS':'Centro-Oeste','GO':'Centro-Oeste','DF':'Centro-Oeste',
 'BA':'Nordeste','SE':'Nordeste','AL':'Nordeste','PE':'Nordeste','PB':'Nordeste','RN':'Nordeste','CE':'Nordeste','PI':'Nordeste','MA':'Nordeste',
 'PA':'Norte','AM':'Norte','AC':'Norte','RO':'Norte','RR':'Norte','AP':'Norte','TO':'Norte'
}
base['regiao'] = base['uf'].map(uf_regiao)

wb1 = openpyxl.load_workbook(f"{DADOS}/Municípios TZ - consolidado.xlsx", data_only=True)
ws1 = wb1['consolidado']
rows1 = list(ws1.iter_rows(min_row=2, values_only=True))
universal_cods = set()
for r in rows1:
    if r[16] and 'EXCLU' in str(r[16]).upper():
        continue
    cod = r[2] or resolve_nome_uf(r[0], r[1])
    if cod: universal_cods.add(str(cod))

wb2 = openpyxl.load_workbook(f"{DADOS}/Tipologias TZ - consolidado.xlsx", data_only=True)
def cods_from_sheet(name, code_col_idx=None):
    ws = wb2[name]
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    cods = set()
    for r in rows:
        cod = r[code_col_idx] if code_col_idx is not None else None
        if not cod: cod = resolve_nome_uf(r[0], r[1])
        if cod: cods.add(str(cod))
    return cods

cods_2a = cods_from_sheet('2a Temporal-dias')
cods_2b = cods_from_sheet('2b Temporal-eventos', 2)
cods_3  = cods_from_sheet('3 Espacial-periferico')
cods_4  = cods_from_sheet('4 Grupo social')

parcial_voluntaria = (cods_2a | cods_3 | cods_4) - universal_cods
obrigacao_eleitoral_only = cods_2b - universal_cods - parcial_voluntaria

def tz_categoria(cod):
    if cod in universal_cods: return 'universal'
    if cod in parcial_voluntaria: return 'parcial_voluntaria'
    if cod in obrigacao_eleitoral_only: return 'obrigacao_eleitoral_2b'
    return 'nenhuma'

base['tz_categoria'] = base['cod_ibge'].apply(tz_categoria)

with open('/tmp/cruz/pairs.json') as f:
    pairs = json.load(f)
from collections import defaultdict
grupos_por_muni = defaultdict(set)
for cod, gid in pairs:
    grupos_por_muni[cod].add(gid)

base['n_grupos_ge'] = base['cod_ibge'].map(lambda c: len(grupos_por_muni.get(c, set())))
base['tem_ge'] = base['n_grupos_ge'] > 0

print("=== Universo TZ por categoria ===")
print(base['tz_categoria'].value_counts())
print("\n=== Presenca de GE (todo o universo, n=5570) ===")
print(base['tem_ge'].value_counts())
print("\n=== Contingencia bruta (tz_categoria x tem_ge) ===")
ct = pd.crosstab(base['tz_categoria'], base['tem_ge'])
print(ct)
print("\n=== % com GE, por categoria ===")
pct = (base.groupby('tz_categoria')['tem_ge'].mean()*100).round(1)
print(pct)

# Chi2 + odds ratio: universal vs nenhuma (exclui obrigacao_eleitoral e parcial para isolar o contraste central)
sub = base[base['tz_categoria'].isin(['universal','nenhuma'])]
ct2 = pd.crosstab(sub['tz_categoria'], sub['tem_ge'])
print("\n--- universal vs nenhuma ---")
print(ct2)
chi2, p, dof, exp = chi2_contingency(ct2)
a = ct2.loc['universal', True]; b = ct2.loc['universal', False]
c = ct2.loc['nenhuma', True]; d = ct2.loc['nenhuma', False]
odds_ratio = (a*d)/(b*c)
print(f"chi2={chi2:.2f} p={p:.4f} odds_ratio(GE em universal vs nenhuma)={odds_ratio:.3f}")

sub2 = base[base['tz_categoria'].isin(['parcial_voluntaria','nenhuma'])]
ct3 = pd.crosstab(sub2['tz_categoria'], sub2['tem_ge'])
print("\n--- parcial_voluntaria vs nenhuma ---")
print(ct3)
chi2b, pb, dofb, expb = chi2_contingency(ct3)
a2 = ct3.loc['parcial_voluntaria', True]; b2 = ct3.loc['parcial_voluntaria', False]
c2 = ct3.loc['nenhuma', True]; d2 = ct3.loc['nenhuma', False]
odds_ratio2 = (a2*d2)/(b2*c2)
print(f"chi2={chi2b:.2f} p={pb:.4f} odds_ratio(GE em parcial_voluntaria vs nenhuma)={odds_ratio2:.3f}")

# por regiao, para contexto (nao controla nada, so descritivo)
print("\n=== % com GE por regiao (todo o universo) ===")
print((base.groupby('regiao')['tem_ge'].mean()*100).round(1))
print("\n=== % TZ universal por regiao (dentre quem tem GE vs quem nao tem) ===")
print(pd.crosstab(base['regiao'], base['tz_categoria']))

base.to_csv('/tmp/cruz/base_municipal_tz_ge.csv', index=False)
print("\nsalvo:", base.shape)
