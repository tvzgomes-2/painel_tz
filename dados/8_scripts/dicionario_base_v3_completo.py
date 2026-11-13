# -*- coding: utf-8 -*-
"""Dicionário completo da Base Municipal v3 (read-only sobre a base).

Gera, para TODAS as colunas de base_municipal_v3.csv:
  - o metadado do metadados.csv quando existe (origem "metadados.csv");
  - senão, o metadado atribuído por regra de prefixo, a partir das notas de
    arquitetura do cofre (origem "regra 01/10/2026 — conferir");
  - senão, "[A CONFIRMAR]".
Mais o perfil medido no próprio arquivo: tipo, cobertura (não nulos de 5.570),
zeros, mín/mediana/máx e colunas de conteúdo idêntico. NA ≠ 0: a cobertura
conta só não nulos; os zeros vão em coluna própria.

Saídas (em _data/Base Municipal v3/dicionario/<data>/):
  dicionario_colunas.csv  (1 linha por coluna)
  dicionario_familias.csv (anos colapsados em <ANO>/<AAAAMM>)
  resumo.json
Não altera base_municipal_v3.csv nem metadados.csv.
Uso: python dicionario_base_v3_completo.py [AAAA-MM-DD]
"""
import os, re, sys, json, hashlib
import pandas as pd

DATA = sys.argv[1] if len(sys.argv) > 1 else '2026-10-01'
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
V = os.path.join(ROOT, '03 - Dados', '_data', 'Base Municipal v3')
OUT = os.path.join(V, 'dicionario', DATA)
os.makedirs(OUT, exist_ok=True)
BASE = os.path.join(V, 'base_municipal_v3.csv')
b = pd.read_csv(BASE, low_memory=False, dtype={'cod_ibge': str})
m = pd.read_csv(os.path.join(V, 'metadados.csv'))
sha = hashlib.sha256(open(BASE, 'rb').read()).hexdigest()


def fam(c):
    c2 = re.sub(r'(?<!\d)(19|20)\d{2}(0[1-9]|1[0-2])(?!\d)', '<AAAAMM>', c)
    return re.sub(r'(?<!\d)(19|20)\d{2}(?!\d)', '<ANO>', c2)


# ---- metadados.csv: ids exatos, ids compostos ("a / _b") e padrões (<AAAAMM>, *)
META, PAT = {}, []
for _, r in m.iterrows():
    rid = str(r['id']).strip()
    first = None
    for t in re.findall(r'[A-Za-z0-9_<>*]+', rid):
        if t.startswith('_') and first:
            t = re.sub(r'_[a-z0-9]+$', '', first) + t
        if '<' in t or '*' in t:
            rx = re.sub(r'<[^>]+>', '\x00', t)
            rx = re.escape(rx).replace(r'\*', '[a-z0-9_]+').replace('\x00', r'\d{4,6}')
            PAT.append((re.compile('^' + rx + '$'), r))
        else:
            META.setdefault(t, r)
        first = first or t

# ---- regras de prefixo (fonte primária conforme as notas de arquitetura do cofre:
# "Banco Municipal v3 — arquitetura, fontes e metadados", "ETL - Base Municipal
# Integrada", "Dados municipais — dicionário e caminhos" e os cabeçalhos dos scripts)
NA_TXT = {'Não pesquisado', 'Não informado', 'nan', 'NaN', '', '-'}
POLO = 'POLO — espinha dados_gerais (dicionário "Novo Metadados")'
R = [
    (r'^cod_ibge$', 'Identificação', 'Código IBGE do município (7 dígitos, texto) — chave de todas as junções', 'IBGE', '2022', 'código', 'montar_base_v2.py'),
    (r'^(nome_mun|nome_uf|uf|reg)$', 'Identificação', 'Nome do município, nome e sigla da UF, grande região', 'IBGE, via ' + POLO, '—', 'texto', 'montar_base_v2.py'),
    (r'^(micro|meso)$', 'Divisão territorial', 'Micro e mesorregião geográfica', 'IBGE, via ' + POLO, '2010', 'texto', 'montar_base_v2.py'),
    (r'^rm$', 'Divisão territorial', 'Região metropolitana, aglomeração urbana ou RIDE', 'IBGE, via ' + POLO, '2010', 'texto', 'montar_base_v2.py'),
    (r'^centralidade$', 'Divisão territorial', 'Centralidade na rede urbana (REGIC 2008) — superada por regic_*_2018', 'IBGE — REGIC 2008, via ' + POLO, '2008', 'categoria', 'montar_base_v2.py'),
    (r'^mun_his_tur$', 'Divisão territorial', 'Município histórico ou turístico', 'Ministério do Turismo, via ' + POLO, '2017', 'categoria', 'montar_base_v2.py'),
    (r'^regiao_admin_sp$', 'Divisão territorial', 'Região administrativa (SP) — coluna vazia no arquivo', '[A CONFIRMAR]', '—', '—', '—'),
    (r'^(rgi|rgint|conc_urbana|catmetropol|recau)_(cod|nome)_2022$', 'Divisão territorial', 'Regiões geográficas imediata e intermediária, concentração urbana, categoria metropolitana e região de articulação urbana', 'IBGE — Recortes Territoriais 2022', '2022', 'código/texto', 'enriquecer_perfil_socioeconomico.py'),
    (r'^area_km2$', 'Território', 'Área territorial', 'IBGE, via ' + POLO, '[A CONFIRMAR]', 'km²', 'montar_base_v2.py'),
    (r'^area_urb$', 'Território', 'Área urbana', 'IBGE, via ' + POLO, '2005', 'km²', 'montar_base_v2.py'),
    (r'(areas_urbanizadas|area_total_mapeada|loteamento_vazio|outros_equipamentos_urbanos|vazios_)', 'Território', 'Áreas urbanizadas por classe (densa, pouco densa, loteamento vazio, vazios, equipamentos)', 'IBGE — Áreas Urbanizadas do Brasil 2019, via ' + POLO, '2019', 'km²', 'montar_base_v2.py'),
    (r'^pop_\d{4}$', 'Demografia', 'População residente (Censo ou estimativa anual)', 'IBGE — Censos 2010/2022 e estimativas (COPIS; SIDRA 6579)', 'ano no nome', 'hab', 'montar_v3_fase1.py'),
    (r'^(pop_urb_10|txc_pop_10_16|dens_2016)$', 'Demografia', 'População urbana 2010, crescimento 2010–2016 e densidade 2016', 'IBGE, via ' + POLO, '2010–2016', '%; hab/km²', 'montar_base_v2.py'),
    (r'^(densid_pop__22|taxa__cresc_10_22|faixa_pop_2022)$', 'Demografia', 'Densidade 2022, crescimento 2010–2022 e faixa de porte', 'IBGE — Censo 2022, via ' + POLO, '2022', 'hab/km²; %; faixa', 'montar_base_v2.py'),
    (r'^(pref|part)_(12|16|20)$|^prof_pref_16$|^sit_eleit$', 'Política', 'Prefeito, partido, profissão e situação eleitoral (2012, 2016, 2020)', 'TSE, via ' + POLO, '2012/2016/2020', 'texto', 'montar_base_v2.py'),
    (r'^ideologia_(prefeito|grupo)_20(20|24)_brc2023$', 'Política', 'Ideologia do partido do prefeito (escala 0–10) e grupo esquerda/direita', 'TSE + Bolognesi, Ribeiro e Codato (2023)', '2020/2024', 'escala 0–10; categoria', 'enriquecimento Gomes Filho (2025), 04/09/2026'),
    (r'^anten_', 'Telecomunicações', 'Antenas de telefonia (total e de uma operadora)', 'Telebrasil, via ' + POLO, '2016', 'n', 'montar_base_v2.py'),
    (r'^(pib|pib_per_cap|pib_per_capita|pib_preco_concorrentes)_20(13|21)$|^(ativ_.*valor_adicion_bruto|prin_atividade)_20(13|21)$', 'Economia', 'PIB, PIB per capita e atividades de maior valor adicionado', 'IBGE — PIB dos Municípios, via ' + POLO, '2013/2021', 'R$; texto', 'montar_base_v2.py'),
    (r'^renda_media_2010$', 'Economia', 'Rendimento nominal médio mensal', 'IBGE — Censo 2010, via ' + POLO, '2010', 'R$', 'montar_base_v2.py'),
    (r'^(rec_total|rec_prop|desp_tcu)$', 'Fiscal', 'Receita total, receita própria e despesa com transporte coletivo', 'STN — FINBRA 2015, via ' + POLO, '2015', 'R$', 'montar_base_v2.py'),
    (r'^finbra_(receita_liquida|receita_corrente|despesa_empenhada)_2022$', 'Fiscal', 'Receita líquida, receita corrente e despesa empenhada', 'STN — Siconfi/DCA (Anexos I-C e I-D)', '2022', 'R$', 'montar_base_integrada.py'),
    (r'^fpm_', 'Fiscal', 'Fundo de Participação dos Municípios: bruto, deduções (FUNDEB e outras), líquido, per capita e parcela na receita corrente', 'STN — Siconfi/DCA Anexo I-C', '2019–2025', 'R$; R$/hab; %', 'enriquecer_base_fpm.py'),
    (r'^despesa_empenhada_2022$', 'Fiscal', 'Despesa empenhada total', 'STN — Siconfi/DCA Anexo I-D', '2022', 'R$', 'montar_v3_fase1.py'),
    (r'^(veic|auto|moto|outr_veic)_20(10|16|23)$|^txc_(auto|moto)_10_16$|^txc_motor_23$', 'Motorização', 'Frota de veículos, automóveis, motos e outros; crescimento 2010–2016', 'DENATRAN, via ' + POLO, '2010/2016/2023', 'veículos; %', 'montar_base_v2.py'),
    (r'^frota_(total|auto|moto|onibus)_\d{4}$', 'Motorização', 'Frota registrada por tipo (dezembro de cada ano)', 'DENATRAN/SENATRAN', '2013–2025 (sem 2020)', 'veículos', 'montar_v3_fase1.py'),
    (r'^(auto|moto)_por_1000hab_\d{4}$|^taxa_motorizacao_\d{4}$', 'Motorização', 'Automóveis e motos por mil habitantes; taxa de motorização', 'Derivado: DENATRAN/SENATRAN ÷ população IBGE', '2013–2025 (sem 2020)', 'veíc. por 1.000 hab', 'montar_v3_fase1.py'),
    (r'^motorizacao_2023$', 'Motorização', 'Veículos por habitante', 'Derivado: DENATRAN ÷ IBGE', '2023', 'veíc/hab', 'montar_base_v2.py'),
    (r'^tx_acid_tran_2014$', 'Sinistralidade', 'Óbitos por acidente de trânsito por habitante', 'Ministério da Saúde, via ' + POLO, '2014', 'taxa', 'montar_base_v2.py'),
    (r'^(obitos_2022|ob_tran_22|tx_mortalidade_100mil_hab)$', 'Sinistralidade', 'Óbitos no trânsito em 2022 e taxa por 100 mil hab.', POLO + ' — fonte primária [A CONFIRMAR]', '2022', 'n; taxa', 'montar_base_v2.py'),
    (r'^(obitos|feridos)_[a-z_]+_2019$', 'Sinistralidade', 'Óbitos e feridos no trânsito por modo da vítima (9 modos + resíduo)', 'Ministério das Cidades — SIMU (Acidentes de Transportes)', '2019', 'n', 'enriquecer_base_sinistralidade_modo.py'),
    (r'^(acess|pav|cal|arb|logr)$', 'Entorno urbano', 'Entorno dos domicílios: acessibilidade, pavimentação, calçada, arborização, logradouro', 'IBGE — Censo 2010, via ' + POLO, '2010', '%', 'montar_base_v2.py'),
    (r'^ibeu$', 'Índices compostos', 'Índice de Bem-Estar Urbano', 'Observatório das Metrópoles, via ' + POLO, '2013 (base 2010)', 'índice 0–1', 'montar_base_v2.py'),
    (r'^idh$', 'Índices compostos', 'IDH municipal', 'Atlas PNUD, via ' + POLO, '2010', 'índice 0–1', 'montar_base_v2.py'),
    (r'^(entorno_total|.*_existe|arboriz_.*)$', 'Entorno urbano', 'Moradores por característica do entorno (pavimentação, iluminação, ponto de ônibus, ciclovia, calçada, rampa, arborização)', 'IBGE — Censo 2022 (SIDRA 6591)', '2022', 'pessoas', 'baixar_sidra.py'),
    (r'^pct_(calcada|iluminacao|rampa)_2022$', 'Entorno urbano', 'Proporção de moradores com calçada, iluminação e rampa', 'Derivado: Censo 2022 (SIDRA 6591)', '2022', '%', 'montar_base_v2.py'),
    (r'^pd(_ano|_rev|_em_elab)?$', 'Planejamento', 'Plano diretor: existência, ano, revisão, em elaboração', 'IBGE — MUNIC 2015, via ' + POLO, '2015', 'categoria; ano', 'montar_base_v2.py'),
    (r'^pdmu$', 'Planejamento', 'Plano de mobilidade urbana (existência)', POLO, '2016/2017', 'categoria', 'montar_base_v2.py'),
    (r'^ext_via$', 'Transporte (POLO)', 'Extensão do sistema viário', 'IBGE, via ' + POLO, '2010', 'km', 'montar_base_v2.py'),
    (r'^(conc_tcu|concessionioria|frota_bus|gps_bus)$', 'Transporte (POLO)', 'Concessão do transporte, concessionária, frota de ônibus e GPS na frota', POLO + ' (levantamento próprio, sem data)', 's/d', 'categoria; n', 'montar_base_v2.py'),
    (r'^sist_metroviar$', 'Transporte (POLO)', 'Existência de sistema metroferroviário', POLO + ' — fonte primária [A CONFIRMAR]', '[A CONFIRMAR]', 'sim/não', 'montar_base_v2.py'),
    (r'^(trab|estudo)_', 'Deslocamento', 'Pessoas que trabalham/estudam no próprio ou em outro município, no domicílio, em vários municípios ou no exterior', 'IBGE — Censo 2022 (SIDRA 10329 e 10321)', '2022', 'pessoas', 'baixar_sidra.py'),
    (r'^pct_(trab|estuda)_outro_munic_2022$', 'Deslocamento', 'Pendularidade: % que trabalha/estuda em outro município', 'Derivado: Censo 2022 (SIDRA)', '2022', '%', 'montar_base_v2.py'),
    (r'^md22_', 'Deslocamento', 'Deslocamento para o trabalho (microdados): modo, tempo, renda, destino principal, quem sai e quem fica', 'IBGE — Censo 2022, Microdados da Amostra (acesso controlado)', '2022', '%; min; R$; código', 'agregar_microdados_censo2022.py'),
    (r'^censo22_modal_', 'Deslocamento', 'Meio de transporte principal para o trabalho (% por modo)', 'IBGE — Censo 2022 (SIDRA 10332)', '2022', '%', 'analise_IV_censo2022_auto_x_tpc.py'),
    (r'^tz_', 'Tarifa Zero', 'Situação, ano de início e indicador de Tarifa Zero universal', 'Base-mestre da pesquisa (Municípios TZ - consolidado.xlsx), sincronizada em 05/09/2026', '05/09/2026', 'categoria; ano; 0/1', 'sincronização de 05/09/2026'),
    (r'^passe_', 'Tarifa Zero', 'Passe Livre nos turnos da eleição de 2022 e sua abrangência', 'IDEC + Tarifa Zero BH, via ' + POLO, '2022', 'categoria', 'montar_base_v2.py'),
    (r'^extensao_viaria_urbana', 'Infraestrutura viária (OSM)', 'Extensão viária dentro da mancha urbanizada, por classe', 'OpenStreetMap (Geofabrik) × IBGE Áreas Urbanizadas 2019', 'extração 2026; mancha 2019', 'km', 'calcular_densidade_viaria_urbana.py'),
    (r'^munic_(estatutarios|funcionarios)_total_2020$|^munic_admin_indireta_existe_2020$|^munic_conferencia_2020$', 'Institucional', 'Pessoal da administração (estatutários, total), administração indireta, conferência de transporte', 'IBGE — MUNIC 2020', '2020', 'n; 0/1', 'enriquecimento Gomes Filho (2025), 04/09/2026'),
    (r'^secretaria_transportes_dummy_h3$', 'Institucional', 'Órgão gestor de transporte com secretaria (exclusiva, conjunta ou subordinada) = 1', 'Derivado: IBGE — MUNIC 2020 (munic_orgao_gestor_2020)', '2020', '0/1', 'enriquecimento Gomes Filho (2025), 04/09/2026'),
    (r'^munic_(permissao|autorizacao|prestacao_direta|nao_regulamentado)_2020$', 'Institucional', 'Forma de delegação do ônibus intramunicipal (colunas irmãs de munic_concessao_2020)', 'IBGE — MUNIC 2020 (bloco Transporte)', '2020', 'sim/não', 'montar_v3_fase2.py'),
    (r'^frota_onibus_conv_2024$|^pax_comuns_2024$', 'Operação (PEMOB)', 'Frota de ônibus convencional e passageiros comuns', 'Ministério das Cidades — PEMOB', '2024', 'veículos; passageiros', 'montar_v3_fase2.py'),
    (r'^cadunico_', 'Vulnerabilidade', 'Famílias e pessoas no Cadastro Único por faixa de renda e no Bolsa Família', 'MDS/SAGI — MI Social (CadÚnico)', 'set/2022 e ago/2025', 'n; %; R$', 'DB - CadÚnico (06/09/2026)'),
    (r'^rais_', 'Emprego', 'Estabelecimentos (total, RAIS negativa, com vínculo) e vínculos; núcleo 4921-3 e expansão 4922/4929 em colunas separadas', 'MTE — RAIS Estabelecimentos (RAIS_ESTAB_PUB)', '[A CONFIRMAR] — ano não confirmado', 'n', 'agregar_rais_estabelecimentos.py'),
    (r'^gini_', 'Desigualdade', 'Gini da renda domiciliar per capita (pessoa como unidade) e controles da amostra', 'IBGE — Censo 2022, Microdados (Domicílios, acesso controlado)', '2022', 'índice 0–1; n', 'calcular_gini_censo2022.py'),
]
RC = [(re.compile(t[0]),) + t[1:] for t in R]


def meta_for(c):
    r = META.get(c)
    if r is None:
        for rx, rr in PAT:
            if rx.match(c):
                r = rr
                break
    if r is not None:
        g = lambda k: ('' if pd.isna(r.get(k)) else str(r.get(k)).strip())
        return dict(bloco=g('tema')[:1].upper() + g('tema')[1:], descricao=g('rotulo'), fonte=g('fonte'),
                    referencia=g('ano_serie'), unidade=g('unidade'), script='', metodo=g('metodo')[:400],
                    situacao_metadado=g('status'), origem_metadado='metadados.csv')
    for rx, bloco, desc, fonte, ref, un, sc in RC:
        if rx.search(c):
            return dict(bloco=bloco, descricao=desc, fonte=fonte, referencia=ref, unidade=un, script=sc, metodo='',
                        situacao_metadado='', origem_metadado='regra 01/10/2026 — conferir')
    return dict(bloco='[A CONFIRMAR]', descricao='[A CONFIRMAR]', fonte='[A CONFIRMAR]', referencia='', unidade='',
                script='', metodo='', situacao_metadado='', origem_metadado='[A CONFIRMAR]')


rows = []
for i, c in enumerate(b.columns):
    s = b[c]
    if s.dtype == object:  # NA codificado como texto não é dado (NA ≠ 0)
        s = s.replace(list(NA_TXT), pd.NA)
    nn = int(s.notna().sum())
    num = pd.api.types.is_numeric_dtype(s)
    r = dict(ordem=i + 1, coluna=c, familia=fam(c), tipo='numérico' if num else 'texto', cobertura=nn,
             cobertura_pct=round(100 * nn / len(b), 1), zeros=int((s == 0).sum()) if num else None,
             distintos=int(s.nunique()), constante=bool(nn > 0 and s.nunique() == 1),
             na_como_texto=int(b[c].isin(list(NA_TXT)).sum()) if b[c].dtype == object else 0)
    if num and nn:
        r.update(minimo=float(s.min()), mediana=float(s.median()), maximo=float(s.max()))
    r.update(meta_for(c))
    rows.append(r)
P = pd.DataFrame(rows)

# colunas de conteúdo idêntico (duplicatas)
grp = {}
for c in P.coluna:
    if b[c].notna().sum() == 0:
        continue
    k = hashlib.md5(pd.util.hash_pandas_object(b[c].astype(str), index=False).values.tobytes()).hexdigest()
    grp.setdefault(k, []).append(c)
ident = {c: ', '.join(x for x in v if x != c) for v in grp.values() if len(v) > 1 for c in v}
P['identica_a'] = P.coluna.map(ident).fillna('')
P.to_csv(os.path.join(OUT, 'dicionario_colunas.csv'), index=False, encoding='utf-8-sig')


def anos(cols):
    ys = sorted({y for c in cols for y in re.findall(r'(?<!\d)((?:19|20)\d{2})(?:0[1-9]|1[0-2])?(?!\d)', c)})
    if not ys:
        return ''
    return ys[0] if len(ys) == 1 else f'{ys[0]}–{ys[-1]} ({len(ys)} anos)'


F = (P.groupby('familia', sort=False)
     .agg(n_colunas=('coluna', 'size'), anos_no_nome=('coluna', anos), bloco=('bloco', 'first'),
          descricao=('descricao', 'first'), fonte=('fonte', 'first'), referencia=('referencia', 'first'),
          unidade=('unidade', 'first'), script=('script', 'first'), cobertura_min=('cobertura', 'min'),
          cobertura_max=('cobertura', 'max'), origem_metadado=('origem_metadado', 'first'))
     .reset_index())
F.to_csv(os.path.join(OUT, 'dicionario_familias.csv'), index=False, encoding='utf-8-sig')
res = dict(data=DATA, arquivo='base_municipal_v3.csv', sha256=sha, municipios=len(b), colunas=len(b.columns),
           familias=len(F), metadados_csv_linhas=len(m),
           origem=P.origem_metadado.value_counts().to_dict(), blocos=P.bloco.value_counts().to_dict(),
           colunas_vazias=P[P.cobertura == 0].coluna.tolist(),
           colunas_na_como_texto=P[P.na_como_texto > 0][['coluna', 'na_como_texto']].values.tolist(),
           colunas_constantes=P[P.constante].coluna.tolist(),
           colunas_identicas=[v for v in grp.values() if len(v) > 1],
           tz_situacao=b['tz_situacao'].value_counts().to_dict() if 'tz_situacao' in b else None,
           a_confirmar=P[P.origem_metadado == '[A CONFIRMAR]'].coluna.tolist())
json.dump(res, open(os.path.join(OUT, 'resumo.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items() if k != 'blocos'}, ensure_ascii=False)[:4000])
print(res['blocos'])
