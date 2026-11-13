# -*- coding: utf-8 -*-
"""analises_r62.py — contas novas da revisão r62 (15/10/2026), só leitura das bases:
(1) cruzamento das duas réguas (subtipo da régua descritiva × destinatário do recurso da régua analítica), camada 1;
(2) proposta de índice de institucionalidade da política (escalas 0–3 e 0–5), sobre o levantamento do arranjo (14/10).
Uso (na raiz do cofre): python "_meta/scripts/analises_r62.py". Saída: 03 - Dados/_data/Analises_r62/."""
import json, re, warnings
from pathlib import Path
import pandas as pd
warnings.filterwarnings('ignore')
U = Path(__file__).resolve().parents[2]; D = U / '03 - Dados' / '_data'; OUT = D / 'Analises_r62'; OUT.mkdir(exist_ok=True)
res = {}
# (1) cruzamento das réguas
d = pd.read_csv(D / 'Analises_Cap6' / 'cap6_analise12_destinatario_2026-10-11.csv')
d['sub'] = d['Régua — subtipo'].fillna('sem subtipo').replace({'': 'sem subtipo'})
EIXO = {'i_publico': 'operação pública', 'ii_oferta': 'empresa paga pela oferta', 'iii_demanda': 'empresa paga pela demanda',
        'p_privado_nd': 'empresa, remuneração não apurada', 'nd': 'prestação não apurada'}
d['dest'] = d.eixo.map(EIXO)
ct = pd.crosstab(d['sub'], d['dest'], margins=True, margins_name='total')
cols = [EIXO[k] for k in EIXO if EIXO[k] in ct.columns] + ['total']
ct = ct[cols]; ct.to_csv(OUT / 'cruzamento_reguas_camada1.csv'); res['cruzamento'] = ct.to_dict()
ct2 = pd.crosstab(d['dest'], d['contra_c'].fillna('não apurada'), margins=True, margins_name='total'); ct2.to_csv(OUT / 'destinatario_x_contrapartida.csv')
res['dest_contra'] = ct2.to_dict()
print(ct.to_string()); print(); print(ct2.to_string()); print()
# (2) índice de institucionalidade
f = pd.read_excel(U / '03 - Dados' / 'Frente CNPJ — arranjo operacional (dimensões 1 a 5).xlsx', sheet_name='Arranjo D1-D5')
f = f[f['Escopo'] == 'em escopo'].copy()
b = pd.read_excel(D / 'casos por fonte' / 'Municípios TZ - consolidado.xlsx')
b['cod'] = pd.to_numeric(b['Código IBGE'], errors='coerce')
f['cod'] = pd.to_numeric(f['Código IBGE'], errors='coerce')
f = f.merge(b[['cod', 'População (2022)', 'Fonte de custeio', 'Mecanismo de custeio']], on='cod', how='left')
def declarada(r):
    for c in ('Fonte de custeio', 'Mecanismo de custeio'):
        v = str(r[c]).strip().lower()
        if v and v != 'nan' and not v.startswith(('não apurad', 'não verificad', 'a verificar')): return 1
    return 0
d1 = f['D1 instrumento — Parte E'].astype(str); fn = f['Função da norma código'].astype(str); via = f['Via jurídica código'].astype(str)
f['N_institui'] = fn.isin(['institui a gratuidade', 'efetiva lei autorizativa']).astype(int)
f['R_decreto'] = d1.str.contains('decreto').astype(int)
f['F_custeio'] = f.apply(declarada, axis=1)
f['O_operacao'] = (~via.isin(['sem informação', 'nan'])).astype(int)
direta = via.str.startswith('execução direta') | via.str.startswith('empresa pública')
f['K_documento'] = (f['Objeto contratado nº'].notna() | (direta & (f['R_decreto'] == 1))).astype(int)
f['escala_0_3'] = f[['N_institui', 'F_custeio', 'O_operacao']].sum(axis=1)
f['escala_0_5'] = f[['N_institui', 'R_decreto', 'F_custeio', 'O_operacao', 'K_documento']].sum(axis=1)
pop = pd.to_numeric(f['População (2022)'], errors='coerce')
f['faixa'] = pd.cut(pop, [0, 20000, 100000, 1e9], labels=['até 20 mil', '20 a 100 mil', 'acima de 100 mil'])
keep = ['Município', 'UF', 'cod', 'Situação', 'faixa', 'N_institui', 'R_decreto', 'F_custeio', 'O_operacao', 'K_documento', 'escala_0_3', 'escala_0_5']
f[keep].to_csv(OUT / 'indice_institucionalidade.csv', index=False)
for esc in ('escala_0_3', 'escala_0_5'):
    t = pd.crosstab(f['faixa'], f[esc], margins=True, margins_name='total'); t.to_csv(OUT / f'indice_{esc}_por_porte.csv')
    print(t.to_string()); print('media', round(f[esc].mean(), 2), 'mediana', f[esc].median()); print()
    res[esc] = {'por_porte': t.to_dict(), 'media': round(float(f[esc].mean()), 2)}
res['componentes'] = {c: int(f[c].sum()) for c in ['N_institui', 'R_decreto', 'F_custeio', 'O_operacao', 'K_documento']}
res['n'] = int(len(f)); print(res['componentes'], res['n'])
json.dump(res, open(OUT / 'resultados_r62.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
