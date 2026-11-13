#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""analise_cap4_supramunicipal.py — população potencialmente atingida (elegível,
não usuária) pelas gratuidades decididas fora do município: o patamar
supramunicipal da Seção 4.4.

Fontes (todas read-only):
  - aba 'Nacionais e estaduais' de
    03 - Dados/_data/casos por fonte/Tipologias TZ - consolidado.xlsx (58 medidas)
  - 03 - Dados/_data/Base Municipal v3/base_municipal_v3.csv
    (pop_2022, uf, rm, cadunico_meio_sm_ref_202209 -> salário mínimo de 2022)
  - índice de indício de sistema de ônibus, família B, reconstruído por
    06 - Acadêmico/Artigos/1 - Em elaboração/XXII ENANPUR 2027 — método de detecção com IA/
    indice_indicio_familia_b.py (corte >= 5 pontos)
  - microdados da amostra do Censo 2022, tabela Pessoas, acesso controlado
    (Downloads/07_Academico/Censo2022_Microdados/microdados_censo_amostra_2022_csv_20260908_140041.zip;
    ver 03 - Dados/_data/Censo2022_Microdados/LEIA-ME.md). Estimativa amostral
    ponderada por P0111, não contagem do universo.

DADO DE ACESSO CONTROLADO: a etapa 1 grava SÓ agregados municipais
(_parcial/idade_<UF>.csv e microdados_idade_municipal.csv), que podem ser
publicados; nada no nível de pessoa, domicílio ou área de ponderação.

Saídas em 03 - Dados/_data/Analises_Cap4/:
  supramunicipal_populacao.csv        resumo por grupo de medidas
  supramunicipal_medidas_detalhe.csv  as 58 medidas, grupo e estimativa por medida
  microdados_idade_municipal.csv      agregado municipal da etapa 1

Uso:
  python3 analise_cap4_supramunicipal.py                 # etapas 1 e 2
  python3 analise_cap4_supramunicipal.py micro [UF ...]  # só etapa 1 (checkpoint por UF)
  python3 analise_cap4_supramunicipal.py consolidar      # só etapa 2
"""
import os, sys, glob, runpy, zipfile
import numpy as np, pandas as pd


def _p(*cands):
    for c in cands:
        c = os.path.expanduser(c)
        if os.path.exists(c):
            return c
    return os.path.expanduser(cands[0])


V = _p('~/mnt/doutorado', r'C:\Users\HOME\OneDrive\doutorado')
ZIP = _p('~/mnt/Downloads/07_Academico/Censo2022_Microdados/microdados_censo_amostra_2022_csv_20260908_140041.zip',
         r'C:\Users\HOME\Downloads\07_Academico\Censo2022_Microdados\microdados_censo_amostra_2022_csv_20260908_140041.zip')
D = os.path.join(V, '03 - Dados', '_data')
BASE = os.path.join(D, 'Base Municipal v3', 'base_municipal_v3.csv')
TIPO = os.path.join(D, 'casos por fonte', 'Tipologias TZ - consolidado.xlsx')
IDX = os.path.join(V, '06 - Acadêmico', 'Artigos', '1 - Em elaboração',
                   'XXII ENANPUR 2027 — método de detecção com IA', 'indice_indicio_familia_b.py')
OUT = os.path.join(D, 'Analises_Cap4')
PARC = os.path.join(OUT, '_parcial')
os.makedirs(PARC, exist_ok=True)

COLS = ['P0080', 'P0100', 'P0111', 'P0181', 'P0650', 'P0660', 'P1110']
BLOCO = 500_000

# salário mínimo de referência do Censo (jul/2022) = 2 x meio SM do CadÚnico 2022-09 na base
_b = pd.read_csv(BASE, usecols=['cadunico_meio_sm_ref_202209'])
SM = 2 * float(_b['cadunico_meio_sm_ref_202209'].dropna().mode()[0])


# ---------------------------------------------------------------- etapa 1
def _agrega(ch, hh_renda=None):
    w = pd.to_numeric(ch['P0111'], errors='coerce')
    ch = ch.assign(w=w)[w.notna() & (w > 0)]
    ida = pd.to_numeric(ch['P0181'], errors='coerce')
    ren = pd.to_numeric(ch['P1110'], errors='coerce').fillna(0)
    fre = pd.to_numeric(ch['P0650'], errors='coerce')
    cur = pd.to_numeric(ch['P0660'], errors='coerce')
    w = ch['w']
    f = pd.DataFrame({'cod_ibge': pd.to_numeric(ch['P0080'], errors='coerce'),
                      'pop_w': w, 'n': 1})
    f['p16_mais'] = w * (ida >= 16)
    f['p18_mais'] = w * (ida >= 18)
    f['p60_mais'] = w * (ida >= 60)
    f['p60_64'] = w * ((ida >= 60) & (ida <= 64))
    f['p65_mais'] = w * (ida >= 65)
    f['n65_mais'] = 1 * (ida >= 65)
    f['p60_renda_le2sm'] = w * ((ida >= 60) & (ren <= 2 * SM))
    f['p60_renda_lt2sm'] = w * ((ida >= 60) & (ren < 2 * SM))
    f['p65_renda_le2sm'] = w * ((ida >= 65) & (ren <= 2 * SM))
    f['p65_renda_lt2sm'] = w * ((ida >= 65) & (ren < 2 * SM))
    if hh_renda is not None:   # renda total do domicílio (soma de P1110 dos moradores)
        hr = ch['P0100'].map(hh_renda).fillna(0)
        f['p60_rendadom_le2sm'] = w * ((ida >= 60) & (hr <= 2 * SM))
    f['est_creche_pre'] = w * ((fre == 1) & cur.isin([1, 2]))
    f['est_basica'] = w * ((fre == 1) & cur.isin([3, 4, 5, 6, 7]))
    f['est_superior'] = w * ((fre == 1) & cur.isin([8, 9, 10, 11]))
    return f.groupby('cod_ibge').sum()


def etapa_micro(ufs=None):
    z = zipfile.ZipFile(ZIP)
    nomes = sorted(n for n in z.namelist() if '/Pessoas_' in n and n.endswith('.csv'))
    for nome in nomes:
        uf = nome.split('/')[0]
        if ufs and uf not in ufs:
            continue
        alvo = os.path.join(PARC, f'idade_{uf}.csv')
        if os.path.exists(alvo):
            print(f'UF {uf}: parcial no disco, pulando', flush=True)
            continue
        print(f'UF {uf}: lendo {nome}', flush=True)
        if uf == '50':   # MS: critério de renda familiar -> lê a UF inteira para somar por domicílio
            ch = pd.read_csv(z.open(nome), sep=';', encoding='latin-1', usecols=COLS, dtype=str)
            hh = pd.to_numeric(ch['P1110'], errors='coerce').fillna(0).groupby(ch['P0100']).sum()
            acc = _agrega(ch, hh)
        else:
            acc = None
            for ch in pd.read_csv(z.open(nome), sep=';', encoding='latin-1', usecols=COLS,
                                  dtype=str, chunksize=BLOCO):
                a = _agrega(ch)
                acc = a if acc is None else acc.add(a, fill_value=0)
        acc.reset_index().to_csv(alvo + '.tmp', index=False)
        os.replace(alvo + '.tmp', alvo)
        print(f'  {len(acc)} municípios', flush=True)


# ---------------------------------------------------------------- etapa 2
GRUPO = {}
for i in ['G1', 'G2', 'G3']:
    GRUPO[i] = '1'
for i in ['F1', 'F2', 'F7'] + [f'E{k}' for k in [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13]]:
    GRUPO[i] = '2'
for i in ['G4', 'G5', 'G6', 'G7', 'G8', 'G11'] + [f'G{k}' for k in range(13, 33)]:
    GRUPO[i] = '3'
for i in ['G9', 'G10', 'G12']:
    GRUPO[i] = '4'
for i in ['D1', 'E16', 'E14']:
    GRUPO[i] = '5'
for i in ['F3', 'F4', 'F5', 'F6', 'F8', 'E7', 'E15', 'E17']:
    GRUPO[i] = '6'

# grupo 3, componente idoso de cada norma, lido do campo 'Portão' da aba:
# (UF, coluna do agregado, critério legível).
G3_IDOSO = {
    'G6':  ('SP', 'p60_64',             '60 a 64 anos, sem renda (65+ é piso federal)'),
    'G8':  ('MG', 'p65_renda_lt2sm',    '65+ com renda individual < 2 SM'),
    'G13': ('CE', 'p65_mais',           '65+ sem exigência de renda'),
    'G14': ('BA', 'p60_mais',           '60+ (só hidroviário), sem renda'),
    'G15': ('PR', 'p65_renda_le2sm',    '65+ com renda <= 2 SM (exigência de CadÚnico não aplicada)'),
    'G16': ('SC', 'p60_renda_lt2sm',    '60+ com renda < 2 SM'),
    'G17': ('ES', 'p65_mais',           '65+ sem exigência de renda'),
    'G18': ('PA', 'p65_mais',           '65+ sem corte de renda'),
    'G19': ('AM', 'p65_mais',           '65+ sem corte de renda'),
    'G21': ('PI', 'p60_renda_le2sm',    '60+ com renda <= 2 SM'),
    'G22': ('RN', 'p60_mais',           '60+ com cadastro DER-RN, sem renda'),
    'G23': ('PB', 'p60_mais',           '60+ (2 vagas; sem limite no de características urbanas), sem renda'),
    'G24': ('SE', 'p65_renda_le2sm',    '65+ com renda <= 2 SM'),
    'G25': ('MS', 'p60_rendadom_le2sm', '60+ com renda familiar (total do domicílio) <= 2 SM'),
    'G26': ('MT', 'p60_renda_le2sm',    '60+ com renda <= 2 SM'),
    'G27': ('TO', 'p60_renda_le2sm',    '60+ com renda <= 2 SM'),
    'G28': ('RO', 'p60_renda_le2sm',    '60+ com renda <= 2 SM'),
    'G29': ('AC', 'p65_renda_le2sm',    '65+ com renda <= 2 SM'),
}
G3_SEM = {
    'G4': 'jovem 15-29 de família no CadÚnico com renda <= 2 SM (interestadual): CadÚnico por idade não está no cofre',
    'G5': "PcD 'comprovadamente carente' (interestadual): carência sem definição mensurável",
    'G7': 'estudantes, PcD e doentes crônicos (vale-social): critérios não parametrizados na aba',
    'G11': 'idoso só tem desconto de 40%; PcD e estudante de baixa renda: critérios não mensurados',
    'G20': 'só PcD com carteira',
    'G30': 'meia estudantil; idosos e PcD a confirmar',
    'G31': 'só PcD',
    'G32': 'mulheres de baixa renda vítimas de violência: sem medida no Censo',
}
BELEM_BRT = ['Belém', 'Ananindeua', 'Marituba', 'Benevides', 'Santa Bárbara do Pará',
             'Santa Izabel do Pará', 'Castanhal']


def _f(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else int(round(v))


def etapa_consolidar():
    parc = sorted(glob.glob(os.path.join(PARC, 'idade_*.csv')))
    if len(parc) != 27:
        sys.exit(f'faltam parciais: {len(parc)}/27 UFs')
    m = pd.concat([pd.read_csv(f) for f in parc], ignore_index=True)
    m = m.groupby('cod_ibge', as_index=False).sum(min_count=1)
    m.round(1).to_csv(os.path.join(OUT, 'microdados_idade_municipal.csv'), index=False)

    cwd = os.getcwd()
    os.chdir(os.path.dirname(BASE))
    b = runpy.run_path(IDX, run_name='lib')['df']
    os.chdir(cwd)
    b = b[['cod_ibge', 'nome_mun', 'uf', 'rm', 'pop_2022', 'indice_familia_b']].copy()
    b['cod_ibge'] = pd.to_numeric(b['cod_ibge'], errors='coerce').astype('Int64')
    m['cod_ibge'] = m['cod_ibge'].astype('Int64')
    x = b.merge(m, on='cod_ibge', how='left')
    x['sist'] = x['indice_familia_b'] >= 5
    nsist = int(x['sist'].sum())
    sem_micro = int(x['pop_w'].isna().sum())

    def S(col, msk=None):
        return float(x.loc[msk, col].sum() if msk is not None else x[col].sum())

    def uf(u):
        return x['uf'] == u

    calib = S('pop_w') / S('pop_2022')

    FMIC = ('Microdados da amostra do Censo 2022 (Pessoas, acesso controlado), ponderados por P0111 — '
            'Downloads/07_Academico/Censo2022_Microdados/microdados_censo_amostra_2022_csv_20260908_140041.zip '
            '-> 03 - Dados/_data/Analises_Cap4/microdados_idade_municipal.csv')
    FIDX = ('índice de indício de sistema, família B, >= 5 pontos (indice_indicio_familia_b.py sobre '
            '03 - Dados/_data/Base Municipal v3/base_municipal_v3.csv)')
    FBASE = '03 - Dados/_data/Base Municipal v3/base_municipal_v3.csv (pop_2022, Censo 2022)'

    tab = pd.read_excel(TIPO, sheet_name='Nacionais e estaduais')
    tab['grupo'] = tab['ID'].map(GRUPO)
    assert tab['grupo'].notna().all(), tab.loc[tab['grupo'].isna(), 'ID'].tolist()
    assert len(tab) == 58, len(tab)
    nmed = tab['grupo'].value_counts().to_dict()

    def ids(g):
        return ', '.join(tab.loc[tab['grupo'] == g, 'ID'])

    det = []
    for _, r in tab.iterrows():
        i = r['ID']
        g = r['grupo']
        d = {'ID': i, 'grupo': g, 'UF': r['UF'], 'portao': r['Portão'], 'situacao': r['Situação'],
             'criterio_estimado': '', 'populacao_elegivel': None, 'estimavel': ''}
        if i in G3_IDOSO:
            u, col, crit = G3_IDOSO[i]
            d.update(criterio_estimado=f'componente idoso: {crit}', populacao_elegivel=_f(S(col, uf(u))),
                     estimavel='parcial (só componente idoso; PcD e demais grupos não estimados)')
        elif i in G3_SEM:
            d.update(criterio_estimado=G3_SEM[i], estimavel='não estimável')
        elif g == '1':
            d.update(criterio_estimado='65+ residentes no Brasil', populacao_elegivel=_f(S('p65_mais')),
                     estimavel='sim')
        elif g == '2':
            d.update(criterio_estimado='18+ (proxy do eleitorado) na UF/BR da medida',
                     populacao_elegivel=_f(S('p18_mais') if r['UF'] == 'BR' else S('p18_mais', uf(r['UF']))),
                     estimavel='proxy (eleitorado apto do TSE não está no cofre)')
        elif i == 'G9':
            d.update(criterio_estimado='frequenta escola, exceto creche/pré, residente no DF',
                     populacao_elegivel=_f(S('est_basica', uf('DF')) + S('est_superior', uf('DF'))),
                     estimavel='teto')
        elif i == 'G10':
            msk = x['rm'] == 'Região Metropolitana de Recife'
            d.update(criterio_estimado='frequenta escola, exceto creche/pré, residente na RM de Recife '
                                       '(rede pública não identificável)',
                     populacao_elegivel=_f(S('est_basica', msk) + S('est_superior', msk)), estimavel='teto')
        elif i == 'G12':
            msk = (x['rm'] == 'Região Metropolitana de Goiânia') | ((x['nome_mun'] == 'Anápolis') & uf('GO'))
            d.update(criterio_estimado='frequenta escola, exceto creche/pré, residente na RM de Goiânia + Anápolis',
                     populacao_elegivel=_f(S('est_basica', msk) + S('est_superior', msk)), estimavel='teto')
        elif i == 'D1':
            d.update(criterio_estimado='população residente no DF', populacao_elegivel=_f(S('pop_2022', uf('DF'))),
                     estimavel='sim')
        elif i == 'E16':
            # os 7 municípios citados na aba coincidem com a RM de Belém da base
            # (a base grafa 'Santa Isabel Do Pará' e 'Santa Bárbara Do Pará')
            msk = x['rm'] == 'Região Metropolitana de Belém'
            assert msk.sum() == len(BELEM_BRT), x.loc[msk, 'nome_mun'].tolist()
            d.update(criterio_estimado='população dos 7 municípios atendidos pelo BRT Metropolitano',
                     populacao_elegivel=_f(S('pop_2022', msk)), estimavel='teto')
        elif i == 'E14':
            d.update(criterio_estimado='inscritos no ENEM 2024 na BA',
                     estimavel='não estimável (dado do INEP não está no cofre)')
        elif g == '6':
            d.update(estimavel='não aplicável (sem portão próprio: norma-marco, proposta, estudo, '
                               'cofinanciamento ou antecedente)')
        det.append(d)
    det = pd.DataFrame(det)
    det['populacao_elegivel'] = det['populacao_elegivel'].astype('Int64')
    det.to_csv(os.path.join(OUT, 'supramunicipal_medidas_detalhe.csv'), index=False)

    g3 = det[(det['grupo'] == '3') & det['populacao_elegivel'].notna()]
    rec_sist = f'municípios com indício de sistema (>= 5 pontos; {nsist} municípios)'
    resumo = [
        dict(grupo='1', descricao='Federal: 65+ no transporte coletivo urbano (CF art. 230 §2º; Estatuto art. 39; ADI 3768)',
             n_medidas=nmed['1'], ids=ids('1'), recorte='Brasil', criterio='residentes com 65 anos ou mais',
             populacao_elegivel=_f(S('p65_mais')), fonte=FMIC, ano='2022',
             ressalva='Elegível, não usuário. Estimativa amostral ponderada, não contagem do universo (SIDRA 9514).'),
        dict(grupo='1', descricao='idem', n_medidas=nmed['1'], ids=ids('1'), recorte=rec_sist,
             criterio='residentes com 65 anos ou mais', populacao_elegivel=_f(S('p65_mais', x['sist'])),
             fonte=FMIC + '; ' + FIDX, ano='2022 (índice: MUNIC 2020 e outras)',
             ressalva='O direito vale onde houver transporte coletivo urbano; o índice é proxy de existência, não prova.'),
        dict(grupo='2', descricao='Gratuidade eleitoral (ADPF 1013, Res. TSE 23.736/2024 e 23.751/2026; atos estaduais)',
             n_medidas=nmed['2'], ids=ids('2'), recorte='Brasil',
             criterio='residentes com 18 anos ou mais (proxy do eleitorado)',
             populacao_elegivel=_f(S('p18_mais')), fonte=FMIC, ano='2022',
             ressalva='Portão de tempo: vale só nos dias de votação. Eleitorado apto do TSE não está no cofre. '
                      'Com 16+ (idade de alistamento) o valor é maior.'),
        dict(grupo='2', descricao='idem', n_medidas=nmed['2'], ids=ids('2'), recorte=rec_sist,
             criterio='residentes com 18 anos ou mais', populacao_elegivel=_f(S('p18_mais', x['sist'])),
             fonte=FMIC + '; ' + FIDX, ano='2022',
             ressalva='Recorte do transporte urbano municipal; os atos estaduais alcançam também o intermunicipal.'),
        dict(grupo='3', descricao='Gratuidades estaduais e federais de grupo fora do urbano municipal '
                                  '(idosos e PcD de baixa renda, com cota; outros grupos)',
             n_medidas=nmed['3'], ids=ids('3'), recorte=f'{len(g3)} UFs com componente idoso estimável',
             criterio='componente idoso de cada norma (idade e renda individual conforme o portão; MS: renda do domicílio)',
             populacao_elegivel=_f(float(g3['populacao_elegivel'].sum())),
             fonte=FMIC + f'; SM 2022 = R$ {SM:.0f} (2 x cadunico_meio_sm_ref_202209 da base)', ano='2022',
             ressalva='Teto do componente idoso. Cota de 2 assentos por veículo limita o acesso; exigências de CadÚnico, '
                      'cadastro e carteira não aplicadas; renda individual do Censo (P1110) aproxima critérios de renda; '
                      'PcD não estimado; 8 medidas não estimáveis (ver detalhe).'),
        dict(grupo='4', descricao='Passe livre estudantil estadual/distrital (DF, PE/RMR, GO/RMTC)',
             n_medidas=nmed['4'], ids=ids('4'), recorte='DF + RM de Recife + RM de Goiânia e Anápolis',
             criterio='frequenta escola ou faculdade, exceto creche e pré-escola',
             populacao_elegivel=_f(float(det.loc[det['grupo'] == '4', 'populacao_elegivel'].sum())),
             fonte=FMIC, ano='2022',
             ressalva='Teto: rede pública (PE), distância de 1 km (DF) e cadastro não aplicados; RM de Goiânia ≠ área '
                      'da RMTC. Componente estudantil do RS está em G11 (grupo 3), não estimado.'),
        dict(grupo='5', descricao='Vai de Graça (DF): domingos, feriados e carnaval, todo o STPC/DF', n_medidas=1,
             ids='D1', recorte='Distrito Federal', criterio='população residente',
             populacao_elegivel=_f(S('pop_2022', uf('DF'))), fonte=FBASE, ano='2022',
             ressalva='Portão de tempo recorrente; não exclui não residentes.'),
        dict(grupo='5', descricao='Tarifa zero aos domingos e feriados no BRT Metropolitano de Belém', n_medidas=1,
             ids='E16', recorte='7 municípios atendidos (' + ', '.join(BELEM_BRT) + ')',
             criterio='população residente',
             populacao_elegivel=_f(float(det.loc[det['ID'] == 'E16', 'populacao_elegivel'].iloc[0])),
             fonte=FBASE, ano='2022', ressalva='Teto: o corredor do BRT atende parte de cada município.'),
        dict(grupo='5', descricao='Gratuidade intermunicipal a candidatos do ENEM (BA, 2024)', n_medidas=1, ids='E14',
             recorte='BA', criterio='inscritos no ENEM', populacao_elegivel=None,
             fonte='não está no cofre (INEP, microdados do ENEM 2024)', ano='',
             ressalva='não estimável; medida encerrada (datas pontuais).'),
        dict(grupo='6', descricao='Sem portão próprio: marco legal, PEC, estudo, cofinanciamento estadual, '
                                  'antecedente (Lei 6.091/1974) e ADI 845',
             n_medidas=nmed['6'], ids=ids('6'), recorte='', criterio='', populacao_elegivel=None, fonte='', ano='',
             ressalva='não aplicável: não há população-alvo própria.'),
    ]
    res = pd.DataFrame(resumo)
    res['populacao_elegivel'] = res['populacao_elegivel'].astype('Int64')
    res.to_csv(os.path.join(OUT, 'supramunicipal_populacao.csv'), index=False)

    print(f'calibração: soma dos pesos / pop_2022 da base = {calib:.4f}; municípios sem microdado: {sem_micro}; '
          f'indício >= 5: {nsist}')
    print(f'SM = {SM}; medidas por grupo: {nmed}; total = {sum(nmed.values())}')
    print(f"pop_w BR = {S('pop_w'):,.0f}; pop_2022 BR = {S('pop_2022'):,.0f}; pop_2022 indício = {S('pop_2022', x['sist']):,.0f}; pop_w indício = {S('pop_w', x['sist']):,.0f}")
    print(f"16+ BR = {S('p16_mais'):,.0f}; 16+ indício = {S('p16_mais', x['sist']):,.0f}")
    print(f"60+ BR = {S('p60_mais'):,.0f}; 60-64 BR = {S('p60_64'):,.0f}; n65 amostra = {S('n65_mais'):,.0f}")
    for k, msk in [('DF', uf('DF')), ('RMR', x['rm'] == 'Região Metropolitana de Recife'),
                   ('RMG+Anápolis', (x['rm'] == 'Região Metropolitana de Goiânia') | ((x['nome_mun'] == 'Anápolis') & uf('GO')))]:
        print(f"  {k}: basica {S('est_basica', msk):,.0f} | superior {S('est_superior', msk):,.0f} | "
              f"creche/pré {S('est_creche_pre', msk):,.0f} | n mun {int(msk.sum())}")
    pd.set_option('display.width', 250)
    print(res[['grupo', 'ids', 'recorte', 'populacao_elegivel']].to_string())
    print(det.loc[det['grupo'].isin(['2', '3', '4', '5']), ['ID', 'UF', 'criterio_estimado', 'populacao_elegivel']].to_string())


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        etapa_micro()
        etapa_consolidar()
    elif a[0] == 'micro':
        etapa_micro(a[1:] or None)
    elif a[0] == 'consolidar':
        etapa_consolidar()
