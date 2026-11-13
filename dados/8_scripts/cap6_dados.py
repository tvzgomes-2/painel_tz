# -*- coding: utf-8 -*-
"""Cap. 6 (tese r21, 02/10/2026) — Análise XII. eixo do destinatário do recurso público (régua analítica, plano de dois eixos).
Lê o retrato congelado de 01/10/2026 da base-mestre. NA != 0: campo vazio ou 'não apurado' fica como não apurado."""
import re, json, sys
import pandas as pd
from pathlib import Path
RAIZ = Path(__file__).resolve().parents[2]   # raiz do cofre (este script fica em _meta/scripts/)
import os
RETRATO = RAIZ / f"03 - Dados/_data/casos por fonte/retratos/{os.environ.get('TZ_RETRATO', '2026-10-01')}/Municípios TZ - consolidado.xlsx"  # r56: TZ_RETRATO=2026-10-11   # retrato congelado
SAIDA = RAIZ / '03 - Dados/_data/Analises_Cap6' / os.environ.get('TZ_CAP6_SAIDA', 'cap6_analise12_destinatario.csv')
d = pd.read_excel(RETRATO)
e = d[d['Situação'].isin(['Ativa', 'Encerrada'])].copy()
S = lambda x: '' if pd.isna(x) else str(x).strip()
ND = re.compile(r'^(não apurad|não verificad|a apurar|<vazio>|$)', re.I)
def prest(x):
    x = S(x).lower()
    if not x or x.startswith('não encontrado') or x.startswith('não apurado') or x.startswith('a apurar'): return 'nd'
    if x.startswith('prestação direta (2015'): return 'privado'   # trajetória: hoje concessão tarifada (encerrada)
    if re.search(r'prestação direta|execução direta|empresa pública|autarquia|operação direta com veículo locado|locação de frota com operação municipal', x): return 'publico'
    return 'privado'
OFERTA = re.compile(r'por km|/km|km ×|km rodado|quilom|valor fixo|/mês|/12 meses|mês fixo|locação|disponibilidade|custo fixo|custo − receita|tacógrafo|preço global', re.I)
DEMANDA = re.compile(r'por passageiro|passageiros|equilíbrio econômico|subvenção de 100% da tarifa|tarifa de gratuidade|tarifa R\$', re.I)
def remun(x):
    t = S(x)
    tl = t.lower()
    if not t or ND.match(tl) or tl.startswith('não apurado'): return 'nd'
    if tl.startswith('não se aplica') or tl.startswith('não aplicável'): return 'na'
    dem, ofe = bool(DEMANDA.search(t)), bool(OFERTA.search(t))
    if dem and not ofe: return 'demanda'
    if ofe and not dem: return 'oferta'
    if dem and ofe: return 'misto'
    return 'outro'
def eixo(r):
    p, m = prest(r['Prestação (eixo 2)']), remun(r['Remuneração do operador'])
    if p == 'publico' or (m == 'na' and p != 'privado'): return 'i_publico'
    if m == 'oferta': return 'ii_oferta'
    if m in ('demanda',): return 'iii_demanda'
    if m in ('misto', 'outro'): return 'x_conferir'
    if p == 'privado': return 'p_privado_nd'
    return 'nd'
e['prest_c'] = e['Prestação (eixo 2)'].map(prest)
e['remun_c'] = e['Remuneração do operador'].map(remun)
e['eixo'] = e.apply(eixo, axis=1)

# ajustes manuais documentados (leitura do campo, 02/10/2026)
AJ = {('Antonina', 'PR'): 'p_privado_nd',      # subsídio mensal a concessão de 20 anos; base de cálculo não lida
      ('Nazaré Paulista', 'SP'): 'iii_demanda',  # subsídio fixo pela receita estimada de passageiros não alunos
      ('Tijucas do Sul', 'PR'): 'ii_oferta',     # contrato vigente (58/2025) por km, sem receita tarifária
      ('Quaraí', 'RS'): 'ii_oferta'}             # r56: contrato emergencial (PP 063/2022), preço mensal pago pela Prefeitura
for (m, u), v in AJ.items():
    k = (e['Município'] == m) & (e['UF'] == u); assert k.sum() == 1, m; e.loc[k, 'eixo'] = v
def num(s): return float(s.replace('.', '').replace(',', '.'))
def anual(t):
    t = S(t)
    m = re.search(r'R\$\s*([\d.]+,\d{2})\s*(?:/12 meses| em 12 meses)', t)
    if m: return num(m.group(1))
    m = re.search(r'= R\$\s*([\d.]+,\d{2})', t)
    if m: return num(m.group(1))
    m = re.search(r'homologado R\$\s*([\d.]+,\d{2})', t)
    if m: return num(m.group(1))
    m = re.search(r'R\$\s*([\d.]+,\d{2})\s*(?:/mês|mês fixo)', t)
    if m and 'km' not in t[:m.start()].lower()[-20:]: return 12 * num(m.group(1))
    m = re.search(r'12 × R\$\s*([\d.]+,\d{2})', t)
    if m: return 12 * num(m.group(1))
    m = re.search(r'R\$\s*([\d.]+,\d{2})/12 meses', t)
    return None
e['custo_anual'] = e['Remuneração do operador'].map(anual)
e['pop'] = pd.to_numeric(e['População (2022)'], errors='coerce')
e.loc[(e['Município'] == 'Atílio Vivácqua') & e['pop'].isna(), 'pop'] = 10540   # r56: Censo 2022 (Base Municipal v3), ausente na base-mestre
def faixa(p):
    if pd.isna(p): return 'nd'
    return '< 20 mil' if p < 2e4 else '20–50 mil' if p < 5e4 else '50–100 mil' if p < 1e5 else '> 100 mil'
e['faixa'] = e['pop'].map(faixa)

# custo anual: correções da leitura caso a caso (só entram valores que cobrem o contrato inteiro do operador)
EXC = {('Nazaré Paulista','SP'): 'subsídio exclui passes escolares (contrato à parte)',
       ('Jales','SP'): 'só a parcela fixa da frota; parcela por km não quantificada',
       ('Barra do Turvo','SP'): 'estimativa mensal (R$ 1,53 mi/ano) diverge do contrato (R$ 3 mi em 5 anos)',
       ('Itapetininga','SP'): 'locação de veículos; operação pública, custo total não apurado',
       ('Antonina','PR'): 'subsídio à concessão; o campo traz média anterior à TZ'}
for (m,u),why in EXC.items():
    k=(e['Município']==m)&(e['UF']==u); e.loc[k,'custo_anual']=None
e['custo_hab'] = e['custo_anual']/e['pop']
def rkm(t):
    t=S(t); v=[num(x) for x in re.findall(r'R\$\s*([\d]+,\d{2})\s*/\s*km', t)]
    m=re.search(r'([\d.]+)\s*km/ano, homologado R\$\s*([\d.]+,\d{2})', t)
    if m and not v: v=[num(m.group(2))/num(m.group(1)+',00')]
    m=re.search(r'([\d.]+) km, R\$\s*([\d.]+,\d{2}) em 12', t)
    if m and not v: v=[num(m.group(2))/num(m.group(1)+',00')]
    return v[-1] if v else None   # último valor citado = vigente
e['rkm'] = e['Remuneração do operador'].map(rkm)
e.loc[(e['Município']=='Agudos'),'rkm']=None          # valor de 2014-2015, fora do período
e.loc[(e['Município']=='Leopoldina'),'rkm']=None      # só a linha distrital
e.loc[(e['Município']=='Jales'),'rkm']=None           # km + parcela fixa por veículo
def fonte(r):
    t=(S(r['Fonte de custeio'])+' | '+S(r['Mecanismo de custeio'])).lower()
    if re.search(r'ttp|taxa de transporte|taxa de mobilidade', t): return '4_receita_vinculada'
    if 'royalties' in t: return 'r_royalties'
    if re.search(r'fundo|fmtu|fumtrap|funtecom|fmtc', t) and not re.search(r'revogado', t): return '3_fundo'
    if re.search(r'dota[çc][ãa]o|dotações|crédito especial|créditos adicionais|crédito suplementar|empenho|fonte 1\.500|fonte 01', t): return '2_dotacao'
    if re.search(r'inferid|presumid|hipótese|indício', t): return 'nd_inferido'
    if re.search(r'orçamento|recursos próprios|tesouro|receita tributária|iptu|subsídio municipal|100% municipal|receitas próprias', t): return '1_orcamento_geral'
    return 'nd'
e['fonte_c']=e.apply(fonte,axis=1)
def contra(x):
    t=S(x).lower()
    if not t or re.match(r'^(não apurad|não verificad|não confirmad|não documentad|<vazio>)', t): return 'nd'
    if re.search(r'comitê|deliberativ|paritári|conselho diretor|concidade|consultas públicas|participação social|participação da sociedade', t): return 'controle_social_previsto'
    return 'outro_registro'
e['contra_c']=e['Contrapartida'].map(contra)
def ge(x):
    t=S(x)
    if t.startswith('operador em grupo') or t.startswith('operador é empresa isolada de grande'): return 'em_ge'
    if t.startswith('operador identificado, isolado'): return 'isolado'
    if t.startswith('sem operador privado'): return 'sem_operador'
    if t.startswith('sugestão'): return 'sugestao'
    return 'nd'
e['ge_c']=e['Operador × GE — resultado (cruzamento)'].map(ge)
RKM = {'Taquarituba': 6.91, 'Pederneiras': 6.42, 'Mandirituba': None, 'Morretes': round(55200/9188, 2)}
for m, v in RKM.items():
    e.loc[e['Município'] == m, 'rkm'] = v
e.loc[e['Município'] == 'Pains', 'rkm'] = 15.89   # campo 'Fonte de custeio': R$ 15,89/km × 20.400 km (contrato R$ 324.156,00)
def contra2(x):
    t = S(x).lower()
    if not t or re.match(r'^(não apurad|não verificad|não confirmad|não documentad)', t): return 'nd'
    if re.search(r'não participativo|não documentado', t): return 'outro_registro'
    if re.search(r'comitê|deliberativ|paritári|concidade|consultas públicas|participação social|participação da sociedade', t): return 'controle_social_previsto'
    return 'outro_registro'
e['contra_c'] = e['Contrapartida'].map(contra2)
C1 = e[e['Régua — aba'] == '1 Universal'].copy()
if __name__ == '__main__':
    import pandas as pd
    print(C1.eixo.value_counts()); print(pd.crosstab(C1.faixa, C1.eixo, margins=True)); print(pd.crosstab(C1.faixa, C1.prest_c, margins=True))
    print(C1.contra_c.value_counts()); print(C1[C1.contra_c == 'controle_social_previsto'][['Município', 'UF', 'eixo']])
    print(C1.ge_c.value_counts())
    y = C1[C1.rkm.notna()]; print(len(y), round(y.rkm.median(), 2), y.rkm.min(), y.rkm.max())
    x = C1[C1.custo_hab.notna()]; print(len(x), x.custo_hab.quantile([.25, .5, .75]).round(1).to_dict(), x.custo_hab.min(), x.custo_hab.max())
    cols = ['Município', 'UF', 'Código IBGE', 'pop', 'faixa', 'Régua — subtipo', 'Prestação (eixo 2)', 'Remuneração do operador', 'eixo', 'rkm', 'custo_anual', 'custo_hab', 'contra_c', 'ge_c']
    SAIDA.parent.mkdir(parents=True, exist_ok=True); C1[cols].to_csv(SAIDA, index=False, encoding='utf-8')
