# -*- coding: utf-8 -*-
"""Levantamento documental caso a caso (Apêndice D da tese), a partir do retrato congelado.
Só lê a cópia datada da base-mestre. NA != 0: campo vazio vira 'não apurado'.
Uso: python levantamento_apendice_d.py [AAAA-MM-DD]  -> retratos/<data>/levantamento_apendice_d.json"""
import sys, os, re, json
import pandas as pd
DATA = sys.argv[1] if len(sys.argv) > 1 else '2026-10-01'
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '03 - Dados', '_data', 'casos por fonte', 'retratos', DATA)
d = pd.read_excel(os.path.join(R, 'Municípios TZ - consolidado.xlsx'))
e = d[d['Situação'].isin(['Ativa', 'Encerrada'])].copy()
S = lambda x: '' if pd.isna(x) else str(x).strip()
def inst(x):
    x = S(x).lower()
    if not x or x == 'nan': return 'não apurado'
    if x.startswith('não encontrado'): return 'não localizado'
    if x.startswith('a verificar'): return 'a verificar'
    if x.startswith('nenhum ato'): return 'nenhum ato (política sem norma)'
    if x.startswith('contrato'): return 'contrato como fundamento'
    if 'autorizativa' in x: return 'lei autorizativa'
    if '+ decreto' in x: return 'lei + decreto'
    if 'complementar' in x: return 'lei complementar'
    if x.startswith('decreto'): return 'decreto'
    if x.startswith('lei'): return 'lei ordinária'
    return 'outro'
def prest(x):
    x = S(x).lower()
    if not x or x.startswith('não encontrado'): return 'não localizada'
    if x.startswith('prestação direta'): return 'prestação direta'
    if 'empresa pública' in x or 'autarquia' in x: return 'empresa pública ou autarquia'
    if 'aditivo' in x: return 'aditivo à concessão existente'
    if 'emergencial' in x or 'dispensa' in x: return 'contrato emergencial ou dispensa'
    if 'locação' in x: return 'locação de veículos com motorista'
    if 'concessão' in x: return 'concessão'
    if 'licitad' in x or 'contrato novo' in x: return 'contrato licitado'
    return 'outro'
def ato(row):
    t = S(row['Ato vigente que concede (eixo 1)']) or S(row['Legislação'])
    m = re.search(r'(lei complementar|lei ordinária|lei|decreto|contrato|edital pe|pe)\s*(?:municipal\s*)?(?:n[ºo°.]*\s*)?(\d[\d.]*/\d{2,4})', t, re.I)
    if m:
        k = m.group(1).lower(); k = {'lei ordinária': 'Lei', 'lei': 'Lei', 'lei complementar': 'LC', 'decreto': 'Decreto', 'contrato': 'Contrato', 'edital pe': 'PE', 'pe': 'PE'}[k]
        return f'{k} {m.group(2)}'
    i = inst(row['Instrumento (eixo 1)'])
    return {'nenhum ato (política sem norma)': 'sem norma', 'não localizado': 'não localizado', 'a verificar': 'a verificar'}.get(i, 'não apurado')
def prova(x):
    p = [s.strip() for s in S(x).split('·')]
    return (p[0] or 'não apurado'), (p[1] if len(p) > 1 and re.fullmatch(r'20\d\d', p[1]) else '')
def ano(x):
    m = re.search(r'(19|20)\d\d', S(x)); return m.group(0) if m else ''
def estado(x):
    x = S(x)
    if x.startswith('Fechado — com norma'): return 'fechado: norma lida'
    if x.startswith('Fechado — política sem norma'): return 'fechado: política sem norma'
    if x.startswith('Fechado — encerrada'): return 'fechado: encerrada'
    if x.lower().startswith('lacuna declarada'): return 'lacuna declarada (e-SIC sem resposta até o fim da coleta)'  # 11/11/2026, decisão do autor
    if 'enviado' in x: return 'aguarda e-SIC (enviado)'
    if 'pronto' in x: return 'aguarda e-SIC (pronto)'
    if 'encerrada' in x: return 'aberto: ato ou data do fim'
    f = x.split('falta:')[-1].strip() if 'falta:' in x else x
    return 'aberto: ' + f.replace('norma lida / subtipo', 'norma e subtipo').replace('prova 2025–2026', 'prova 2025–26')
rows = []
for _, r in e.sort_values(['UF', 'Município']).iterrows():
    pv, pa = prova(r['Prova de operação — atualidade (2025/2026)'])
    rows.append(dict(mun=S(r['Município']), uf=S(r['UF']), sit=S(r['Situação']), inicio=ano(r['Ano início']), fim=ano(r['Fim']),
        ato=ato(r), inst=inst(r['Instrumento (eixo 1)']), prest=prest(r['Prestação (eixo 2)']), prova=pv, prova_ano=pa,
        estado=estado(r['Estado terminal (completude)']), aba=S(r['Régua — aba']), subtipo=S(r['Régua — subtipo']),
        cnpj=bool(re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}', S(r['Operador — CNPJ']))),
        remun=S(r['Remuneração do operador']).lower(), custeio=S(r['Mecanismo de custeio']).lower(),
        linhas=bool(re.match(r'\d', S(r['Nº linhas']))), portao_txt=bool(S(r['Portão visível no texto da norma'])),
        base=S(r['Instrumento — base da decisão']).lower(), nlev=S(r['Fontes — nº de levantamentos (recontagem)']),
        esic=S(r['e-SIC / varredura nº'])))
json.dump(rows, open(os.path.join(R, 'levantamento_apendice_d.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(rows))
