# -*- coding: utf-8 -*-
"""
build_arranjo.py — gera scripts/arranjo_tz.json a partir da aba `arranjo_A1_A6` do
pacote 5 da tese ("05 Arranjo, contratos e custos.xlsx", levantamento de 14/10/2026
harmonizado com a base de 21/10/2026).

Por que existe: até out/2026 o painel exibia `tz_operador` — o NOME de quem opera — e
nada sobre o contrato. A tese usa o capítulo inteiro (5.6) para mostrar que a diferença
decisiva não é quem opera, e sim o que foi contratado: uma prefeitura que opera com frota
própria e uma concessionária que recebeu a gratuidade por termo aditivo apareciam, no
painel, como a mesma coisa. Este crosswalk leva ao painel o objeto contratado, o arranjo
A1–A6, a via jurídica, a função da norma e a forma de remuneração.

FRONTEIRA (decisão do autor, 23/10/2026 — itens 12.6 e 12.7 do ROADMAP): fica FORA deste
arquivo tudo que é régua ANALÍTICA — o destinatário do recurso em quatro categorias, a
contrapartida e a posição no plano. O que entra aqui é a descrição contratual do Capítulo 5
(Parte 2 da tese), não a leitura crítica do Capítulo 7, suspensa até a defesa.

RESSALVA DA FONTE: o Leia-me do pacote diz "versão de trabalho, enviada em 24/11/2026;
não redistribuir antes do depósito com DOI". Publicar estes campos num site aberto é
decisão editorial do autor, não consequência técnica de rodar este script.

Chave: código IBGE (string), como nos demais crosswalks.
Uso:  python3 scripts/build_arranjo.py        (da raiz do repositório)
"""
import json
import os
import re
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT = os.environ.get('TZ_VAULT') or os.path.join(BASE_DIR, '..', '..', 'doutorado')
PACOTE = os.path.join(VAULT, '01 - Projeto', 'Envio à orientadora — 24-11-2026',
                      '02 Bases de dados (xlsx)', '05 Arranjo, contratos e custos.xlsx')
OUT = os.path.join(BASE_DIR, 'arranjo_tz.json')
# 13/11/2026 (v1.0.0): base de 11/11/2026. As abas do pacote 5 de 22/10 dão lugar às tabelas
# depositadas em dados/5_arranjo_contratos/ (DOI 10.5281/zenodo.24186039) — lidas, nunca escritas
# — e, no arranjo A1–A6, ao levantamento harmonizado com a base de 11/11 (r102), que é o que a
# tese usa e não está no depósito. TZ_PACOTE5 volta ao pacote antigo, para refazer a v0.15.
DADOS5 = os.path.join(BASE_DIR, '..', 'dados', '5_arranjo_contratos')
CSV5 = {'arranjo_D1_D5': 'arranjo_operacional_D1_D5.csv', 'destinatario_contrapartida': 'destinatario_contrapartida.csv',
        'preco_km_41_contratos': 'preco_km_contratos.csv', 'custo_por_habitante': 'custo_habitante_contratos.csv',
        'custeio_no_ato': 'custeio_no_ato.csv',
        'arranjo_A1_A6': os.path.join(VAULT, '03 - Dados', '_data', 'Analises_Cap5_r75', 'arranjo_A1-A6_base-2026-11-11_r102.csv')}
def ler(aba):
    if os.environ.get('TZ_PACOTE5'):
        return pd.read_excel(os.environ['TZ_PACOTE5'], sheet_name=aba)
    f = CSV5[aba]
    f = f if os.path.isabs(f) else os.path.join(DADOS5, f)
    print(f'fonte de {aba}: {os.path.relpath(f, os.path.join(BASE_DIR, ".."))}')
    return pd.read_csv(f)



def txt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = re.sub(r'\s+', ' ', str(v)).strip()
    if not s or s.lower() in ('nan', 'none', 'sem informação', 'não apurado'):
        return None
    return s


df = ler('arranjo_A1_A6')
print('linhas na aba:', len(df))

# A força da prova de cada codificação. A tese é explícita: 80 das 186 codificações do
# objeto vêm de fonte secundária, e "o objeto lido não diz como o contrato é executado".
# Exibir a classificação sem dizer de onde ela veio seria repetir, em escala menor, o
# problema que o item 12.2 corrigiu na régua.
PROVA = {
    'cláusula lida': ('alta', 'cláusula de contrato lida'),
    'edital/TR': ('alta', 'edital ou termo de referência lido'),
    'fonte secundária': ('media', 'fonte secundária (notícia, portal, histórico de busca)'),
    'MUNIC 2020 (autodeclaração)': ('baixa', 'MUNIC 2020 — autodeclaração da prefeitura, anterior à política'),
    'resposta a e-SIC': ('alta', 'resposta a pedido de acesso à informação'),
    'resposta a pedido de acesso': ('alta', 'resposta a pedido de acesso à informação'),
}

out = {}
sem_cod = []
for _, r in df.iterrows():
    cod = r.get('Código IBGE')
    try:
        cod = str(int(float(cod)))
    except (TypeError, ValueError):
        sem_cod.append(f"{r.get('Município')}/{r.get('UF')}")
        continue
    arranjo = txt(r.get('A'))
    e = {}
    if arranjo:
        e['a'] = arranjo
    for campo, chave in (('esfera', 'esf'), ('Via jurídica código', 'via'),
                         ('Função da norma código', 'norma'),
                         ('Remuneração — corte binário', 'rem')):
        v = txt(r.get(campo))
        if v:
            e[chave] = v
    loc = txt(r.get('Tipo de locação (derivado)'))
    if loc and loc != 'não é locação':
        e['loc'] = loc
    leitura = txt(r.get('Objeto contratado leitura'))
    if leitura in PROVA:
        e['prova'], e['prova_txt'] = PROVA[leitura]
    if e:
        out[cod] = e

if sem_cod:
    print('  [aviso] linhas sem código IBGE, fora do arquivo:')
    for n in sem_cod:
        print('   ', n)

out = {k: out[k] for k in sorted(out, key=int)}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
    f.write('\n')

from collections import Counter
print(f"arranjo_tz.json: {len(out)} municípios, {os.path.getsize(OUT)} bytes")
for campo, rot in (('a', 'arranjo'), ('via', 'via jurídica'), ('rem', 'remuneração'), ('prova', 'força da prova')):
    c = Counter(v.get(campo) for v in out.values() if v.get(campo))
    print(f"  {rot}:")
    for k, n in c.most_common():
        print(f"     {n:4d}  {k}")
