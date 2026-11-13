#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""enriquecer_prosa_municipal.py — gera, EM PROSA, os Blocos 2 (Principais
dados), 3 (Contexto da mobilidade) e a subseção "Régua descritiva" do Bloco 5
(Classificação), no calibre validado em São Caetano do Sul (SCS).

ESCOPO (proposta confirmada pelo autor em 21/09/2026 — "vamos fazer isso
sim!"): só a camada MECANIZÁVEL do esqueleto de 8 blocos. Bloco 1 (Briefing),
Régua analítica, Blocos 6/7/8 (grupos econômicos, RSL/notícias/legislação,
literatura) exigem pesquisa de caso que não existe pronta para a maioria dos
~211 municípios fora dos casos-bandeira — não são gerados aqui.

REGRAS-PADRÃO DO AUTOR (21/09/2026, vale para TODAS as fichas):
  - eliminar a simulação de financiamento CTP/CTPU (não entra em Bloco 2).
  - eliminar a linha "frota de ônibus (DENATRAN/SENATRAN) cresceu de X para
    Y" — a frota_onibus_AAAA não é usada aqui. O Bloco 3 usa frota_total
    (todos os veículos) e motorização, como no texto validado de SCS.

IDEMPOTÊNCIA / PRESERVAÇÃO DA VOZ DO AUTOR: cada bloco gerado fica entre
marcadores HTML-comment com um hash do conteúdo gerado
(`<!-- prosa:BLOCO:inicio hash:XXXX -->` ... `<!-- prosa:BLOCO:fim -->`).
Numa nova rodada: se o hash do conteúdo atual bate com o hash gravado, o
texto não foi tocado à mão — pode ser regenerado livremente. Se diverge,
o autor editou a prosa à mão (caso de SCS) e o script NÃO sobrescreve por
padrão — fica marcado "divergente, pulado" no relatório (usar --forcar para
sobrescrever mesmo assim). Sem marcador nenhum: se a seção já existe com
conteúdo (ficha antiga, escrita à mão ou por outro gerador), também não
mexe por padrão — só insere quando a seção está ausente ou vazia.

USO
  python enriquecer_prosa_municipal.py --testar "São Caetano do Sul" SP
      → imprime a prosa gerada para um município, não grava nada.
  python enriquecer_prosa_municipal.py [--gravar] [--forcar]
      → roda para todas as fichas do cofre. Simula por padrão.
"""
import argparse
import datetime
import glob
import hashlib
import os
import re
import shutil
import sys
import unicodedata

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.environ.get("TZ_VAULT") or HERE
V = os.path.join(RAIZ, "03 - Dados", "_data")
BASE_CSV = os.path.join(V, "Base Municipal v3", "base_municipal_v3.csv")
FICHAS_DIR = os.path.join(RAIZ, "04 - Análises", "Casos municipais", "Fichas por município")

sys.path.insert(0, HERE)
import enriquecer_regua_portao as regua  # reusa carregar()/camada/portão — não duplica a lógica


# ---------------------------------------------------------------- formatação
def fmt_num(v, casas=0):
    if pd.isna(v):
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(v, casas=1):
    if pd.isna(v):
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return f"{v:.{casas}f}%".replace(".", ",")


def fmt_reais(v, casas=0):
    if pd.isna(v):
        return None
    return f"R$ {fmt_num(v, casas)}"


def fmt_reais_esc(v):
    """Reais com escala automática (bilhões/milhões), como no texto de SCS."""
    if pd.isna(v):
        return None
    av = abs(v)
    if av >= 1e9:
        n = v / 1e9
        return f"R$ {fmt_num(n, 2)} " + ("bilhão" if round(n, 2) == 1 else "bilhões")
    if av >= 1e6:
        n = v / 1e6
        return f"R$ {fmt_num(n, 1)} " + ("milhão" if round(n, 1) == 1 else "milhões")
    return fmt_reais(v)


def lista_e(items):
    """Junta itens com vírgula e 'e' antes do último, como prosa em português."""
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " e " + items[-1]


_CONECTORES_MIN = {"do", "da", "dos", "das", "de", "e"}


def titulo_mun(nome):
    """Corrige a capitalização de 'nome_mun' (ex.: 'São Caetano Do Sul' ->
    'São Caetano do Sul') — o banco grafa conectores em maiúscula."""
    partes = str(nome).split(" ")
    return " ".join(p.lower() if p.lower() in _CONECTORES_MIN and i > 0 else p
                     for i, p in enumerate(partes))


_PLACEHOLDERS_NA = {"", "-", "—", "nao especificado", "não especificado", "nao apurado",
                     "não apurado", "n/a", "na", "nao determinavel", "não determinável",
                     "a verificar", "nao informado", "não informado"}


def valor_util(v):
    """NA != 0: filtra placeholders textuais ('Não especificado', '—' etc.)
    que o pandas não reconhece como NaN mas que não são dado nenhum."""
    if pd.isna(v):
        return None
    sv = str(v).strip()
    if n_(sv).lower() in {n_(p) for p in _PLACEHOLDERS_NA} or sv.lower() in _PLACEHOLDERS_NA:
        return None
    return v


def evidencia_citavel(ev):
    """Filtro de qualidade: a coluna 'Portão — evidência' é um rastro de
    auditoria do AUTOR/pesquisa (datas de revisão, referências a
    CLAUDE.md, dicionários brutos da planilha) — não prosa pronta para a
    tese. Só entra na prosa gerada quando é curta e não tem sinais de nota
    interna; caso contrário, o bloco cita a existência da evidência sem
    reproduzi-la."""
    if not ev:
        return None
    if len(ev) > 220:
        return None
    if re.search(r"CLAUDE\.md|Confirmado pelo autor|\{['\"]?\w+['\"]?:|https?://|Dados originais desta linha", ev):
        return None
    return ev


def n_(s):
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or ""))
                if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def c7(x):
    try:
        return str(int(float(x))).zfill(7)
    except Exception:
        return None


# ------------------------------------------------------------ dados globais
_GINI_MEDIANA = None
_GINI_Q3 = None


def carregar_base():
    global _GINI_MEDIANA, _GINI_Q3
    df = pd.read_csv(BASE_CSV, low_memory=False, dtype={"cod_ibge": str})
    df["cod_ibge"] = df["cod_ibge"].map(c7)
    df["chave"] = df["uf"].str.upper().str.strip() + "|" + df["nome_mun"].map(n_)
    g = df["gini_dom_pc_2022"].dropna()
    _GINI_MEDIANA = g.median()
    _GINI_Q3 = g.quantile(0.75)
    return df


# variantes de grafia entre o frontmatter das fichas e nome_mun do banco —
# mesmo bridge usado em enriquecer_fichas_municipais.py (único candidato por
# UF, já conferido lá).
CORRECOES_NOME_FICHA = {
    "SP|ARTHURNOGUEIRA": "SP|ARTURNOGUEIRA",
    "SP|EMBUDASARTES": "SP|EMBU",
}


def linha_municipio(df, municipio, uf):
    chave = uf.strip().upper() + "|" + n_(municipio)
    chave = CORRECOES_NOME_FICHA.get(chave, chave)
    m = df[df["chave"] == chave]
    if m.empty:
        return None
    return m.iloc[0]


# =================================================================
# BLOCO 2 — PRINCIPAIS DADOS
# =================================================================
def p2_populacao(r):
    pop22 = r.get("pop_2022")
    if pd.isna(pop22):
        return None
    frases = [f"{titulo_mun(r['nome_mun'])} tinha {fmt_num(pop22)} habitantes em 2022"]
    pop25 = r.get("pop_2025")
    if pd.notna(pop25):
        frases[0] += f", projetados para {fmt_num(pop25)} em 2025"
    cagr = r.get("pop_cagr_2010_2022")
    if pd.notna(cagr):
        frases[0] += f" — crescimento de {fmt_pct(cagr, 2)} ao ano entre 2010 e 2022"
    frases[0] += "."
    dens = r.get("densid_pop__22")
    if pd.notna(dens):
        s = f"A densidade é de {fmt_num(dens, 1)} hab/km²."
        urb = r.get("taxa_urbanizacao_2022")
        if pd.notna(urb) and round(urb, 1) >= 99.9:
            s = s[:-1] + "; como o município é 100% urbanizado, essa densidade já é, na prática, a densidade da própria área urbana."
        elif pd.notna(urb):
            s = s[:-1] + f" (taxa de urbanização de {fmt_pct(urb, 1)})."
        frases.append(s)
    if int(r.get("em_arranjo_pop") or 0) == 1 and pd.notna(r.get("arranjo_pop_ibge")):
        pos = r.get("posicao_arranjo") or "integrante"
        pos_map = {"satelite": "satélite", "polo": "polo", "co-polo": "co-polo", "isolado": "isolado"}
        pos_txt = pos_map.get(pos, pos)
        dep = r.get("dependencia_pendular")
        tem_rm = pd.notna(r.get("rm")) and r.get("rm") != "Nenhuma"
        if tem_rm:
            s = f"O município integra {r['rm']}, na posição de {pos_txt} do {r['arranjo_pop_ibge']}"
        else:
            s = f"O município é {pos_txt} do {r['arranjo_pop_ibge']}"
        if pd.notna(dep):
            dep_fmt = str(dep).replace(">=", "≥").replace("media", "média")
            if "(" in dep_fmt:
                s += f", com dependência pendular {dep_fmt.split(' (')[0]} ({dep_fmt.split('(')[-1].rstrip(')')} dos ocupados trabalham fora do município)"
            else:
                s += f", com dependência pendular {dep_fmt}"
        s += "."
        frases.append(s)
    elif pd.notna(r.get("rm")) and r.get("rm") != "Nenhuma":
        frases.append(f"O município integra {r['rm']}.")
    return " ".join(frases)


_SETOR_MAP = {
    "Adm. Pública": "administração pública",
    "Agropecuária": "agropecuária",
    "Serviços": "serviços",
    "Indústria": "indústria",
    "Eletricidade e gás": "eletricidade e gás",
    "Construção": "construção",
}


def p2_pib(r):
    pib = r.get("pib_preco_concorrentes_2021")
    if pd.isna(pib):
        return None
    frases = []
    s = f"O PIB municipal em 2021 foi de {fmt_reais_esc(pib * 1000)}"
    pibpc = r.get("pib_per_capita_2021")
    if pd.notna(pibpc):
        s += f" ({fmt_reais(pibpc)} per capita)"
    sal = r.get("salario_medio_mensal_r")
    if pd.notna(sal):
        s += f" e o salário médio mensal, pela RAIS/SIDRA, era de {fmt_reais(sal, 2) if sal < 1000 else fmt_reais(sal)} em 2024"
    s += "."
    frases.append(s)
    a1, a2, a3 = r.get("ativ_maior_valor_adicion_bruto_2021"), r.get("ativ_segundo_maior_valor_adicion_bruto_2021"), r.get("ativ_terceiro_maior_valor_adicion_bruto_2021")
    if pd.notna(a1):
        s2 = (f'Na composição do PIB por valor adicionado bruto — a métrica do IBGE que mostra quais '
              f'atividades geram mais riqueza no município —, a maior fatia vem de "{a1}"')
        if pd.notna(a2):
            s2 += f", seguida por {a2[0].lower() + a2[1:]}"
        if pd.notna(a3):
            s2 += f" e por {a3[0].lower() + a3[1:]}"
        setor = _SETOR_MAP.get(r.get("prin_atividade_2021"))
        if setor:
            s2 += f"; no agregado por grandes setores, {setor.capitalize()} é a atividade principal"
        s2 += "."
        frases.append(s2)
    return " ".join(frases)


def _fpm_trajetoria(r):
    anos = list(range(2019, 2026))
    serie = [(a, r.get(f"fpm_liquido_{a}")) for a in anos]
    serie = [(a, v) for a, v in serie if pd.notna(v)]
    if len(serie) < 2:
        return None
    quedas = [serie[i][0] for i in range(1, len(serie)) if serie[i][1] < serie[i - 1][1]]
    a0, v0 = serie[0]
    a1, v1 = serie[-1]
    s = f"O FPM (Siconfi), líquido de Fundeb, "
    if quedas:
        anoq = quedas[0]
        vq = dict(serie)[anoq]
        s += f"caiu em {anoq} ({fmt_reais_esc(vq)}) e "
        s += "cresceu quase todos os anos desde então " if len(quedas) == 1 else "oscilou nos anos seguintes "
    else:
        s += "cresceu "
    s += f"até {fmt_reais_esc(v1)} em {a1}"
    pc = r.get(f"fpm_liquido_pc_{a1}")
    if pd.notna(pc):
        s += f" ({fmt_reais(pc, 2)} per capita)"
    share = r.get("fpm_share_receita_corrente_2022")
    rec = r.get("finbra_receita_corrente_2022")
    if pd.notna(share) and pd.notna(rec):
        s += f" — equivalente a {fmt_pct(share * 100, 2)} da receita corrente em 2022 ({fmt_reais_esc(rec)})"
    s += "."
    return s


def p2_fiscal(r):
    desp = r.get("despesa_empenhada_2022")
    if pd.isna(desp):
        return None
    frases = []
    s = f"Do lado fiscal, a despesa empenhada em 2022 foi de {fmt_reais_esc(desp)}"
    pct_inv = r.get("pct_investimento_desp_2022")
    inv = r.get("investimentos_2022")
    if pd.notna(pct_inv) and pd.notna(inv):
        s += f", dos quais {fmt_pct(pct_inv, 2)} foram investimento ({fmt_reais_esc(inv)})"
    rc = r.get("receita_cagr_2019_2023")
    ic = r.get("investimento_cagr_2019_2023")
    if pd.notna(rc) and pd.notna(ic):
        s += f" — receita e investimento cresceram, respectivamente, {fmt_pct(rc, 2)} e {fmt_pct(ic, 2)} ao ano entre 2019 e 2023"
    s += "."
    frases.append(s)
    fpm = _fpm_trajetoria(r)
    if fpm:
        frases.append(fpm)
    return " ".join(frases)


def p2_emprego(r):
    rais = r.get("vinculos_formais_rais_2022")
    if pd.isna(rais):
        return None
    frases = [f"O emprego formal somava {fmt_num(rais)} vínculos em 2022 (RAIS)"]
    ne_t, ne_c, ne_n, nv = (r.get("rais_n_estab_total"), r.get("rais_n_estab_com_vinculo"),
                            r.get("rais_n_estab_negativa"), r.get("rais_vinculos_ativos"))
    if pd.notna(ne_t):
        s = f"; pela RAIS Estabelecimentos, o município tinha {fmt_num(ne_t)} estabelecimentos"
        if pd.notna(ne_c) and pd.notna(nv):
            s += f", dos quais {fmt_num(ne_c)} com vínculo ativo ({fmt_num(nv)} vínculos)"
        if pd.notna(ne_n):
            s += f" e {fmt_num(ne_n)} em situação de RAIS negativa"
        frases[0] += s
    frases[0] += "."
    inf = r.get("taxa_informalidade_ampla_censo2022_pct")
    if pd.notna(inf):
        infn, ocn = r.get("informais_ampla_censo2022"), r.get("ocupados_total_censo2022")
        s = f"A informalidade, pela definição ampla do Censo 2022, atingia {fmt_pct(inf, 1)} dos ocupados"
        if pd.notna(infn) and pd.notna(ocn):
            s += f" ({fmt_num(infn)} de {fmt_num(ocn)} pessoas)"
        s += "."
        frases.append(s)
    return " ".join(frases)


def p2_indices(r):
    idh, ibeu, gini = r.get("idh"), r.get("ibeu"), r.get("gini_dom_pc_2022")
    if pd.isna(idh) and pd.isna(ibeu) and pd.isna(gini):
        return None
    partes = []
    if pd.notna(idh):
        partes.append(f"O IDH é {fmt_num(idh, 3)}")
    if pd.notna(ibeu):
        partes.append(f"o IBEU é {fmt_num(ibeu, 3)}")
    s1 = (" e ".join(partes) if len(partes) <= 2 else ", ".join(partes[:-1]) + " e " + partes[-1])
    s1 = s1[0].upper() + s1[1:] + "." if s1 else ""
    frases = [s1] if s1 else []
    if pd.notna(gini):
        nd = r.get("gini_n_domicilios")
        ns = r.get("gini_domic_sem_renda")
        s2 = f"O Gini de renda domiciliar per capita (Censo 2022"
        if pd.notna(nd):
            s2 += f", {fmt_num(nd)} domicílios na amostra"
            if pd.notna(ns):
                s2 += (", nenhum sem renda declarada" if ns == 0 else f", {fmt_num(ns)} sem renda declarada")
        s2 += f") é {fmt_num(gini, 4)}"
        if _GINI_MEDIANA is not None:
            rel = "acima" if gini > _GINI_MEDIANA else "abaixo"
            s2 += f" — {rel} da mediana nacional ({fmt_num(_GINI_MEDIANA, 3)})"
            if _GINI_Q3 is not None:
                rel3 = "e acima do" if gini > _GINI_Q3 else "e abaixo do"
                if gini <= _GINI_MEDIANA:
                    rel3 = "abaixo também do" if gini < _GINI_Q3 else "mas acima do"
                s2 += f" {rel3} 3º quartil ({fmt_num(_GINI_Q3, 3)})"
        s2 += "."
        frases.append(s2)
    return " ".join(frases)


def p2_cadunico(r):
    pes = r.get("cadunico_pes_202508")
    fam = r.get("cadunico_fam_202508")
    if pd.isna(pes) or pd.isna(fam):
        return None
    frases = [f"No CadÚnico (ago/2025), há {fmt_num(pes)} pessoas cadastradas em {fmt_num(fam)} famílias"]
    cob = r.get("cadunico_cobertura_pct_202508")
    atu = r.get("cadunico_taxa_atualizacao_pct_202508")
    if pd.notna(cob):
        frases[0] += f" — cobertura de {fmt_pct(cob, 1)} da população"
        if pd.notna(atu):
            frases[0] += f", com {fmt_pct(atu, 1)} de atualização cadastral"
    frases[0] += "."
    pob = r.get("cadunico_fam_sit_pobreza_202508")
    ext = r.get("cadunico_fam_sit_extrema_pobreza_202508")
    pbf = r.get("cadunico_pes_benef_pbf_202508")
    if pd.notna(pob) and pd.notna(ext):
        s = f"Dessas famílias, {fmt_num(pob)} estão em situação de pobreza e {fmt_num(ext)} em extrema pobreza (faixas disjuntas, não aninhadas)"
        if pd.notna(pbf):
            s += f"; {fmt_num(pbf)} pessoas são beneficiárias do Bolsa Família"
        s += "."
        frases.append(s)
    return " ".join(frases)


def montar_bloco2(r):
    partes = [p2_populacao(r), p2_pib(r), p2_fiscal(r), p2_emprego(r), p2_indices(r), p2_cadunico(r)]
    partes = [p for p in partes if p]
    if not partes:
        return None
    return "## 2. Principais dados\n\n" + "\n\n".join(partes)


# =================================================================
# BLOCO 3 — CONTEXTO DA MOBILIDADE
# =================================================================
_MODOS = [
    ("censo22_modal_automovel_pct", "automóvel", "o"),
    ("censo22_modal_a_pe_pct", "a pé", None),
    ("censo22_modal_onibus_pct", "ônibus", "o"),
    ("censo22_modal_trem_metro_pct", "trem/metrô", "o"),
    ("censo22_modal_motocicleta_pct", "motocicleta", "a"),
    ("censo22_modal_bicicleta_pct", "bicicleta", "a"),
    ("censo22_modal_taxi_pct", "táxi", "o"),
    ("censo22_modal_van_pct", "van", "a"),
    ("censo22_modal_brt_pct", "BRT", "o"),
    ("censo22_modal_mototaxi_pct", "mototáxi", "o"),
    ("censo22_modal_caminhonete_pct", "caminhonete", "a"),
    ("censo22_modal_embarcacao_pequena_pct", "embarcação pequena", "a"),
    ("censo22_modal_embarcacao_grande_pct", "embarcação grande", "a"),
    ("censo22_modal_outros_pct", "outros modos", None),
]


def p3_modal_frota(r):
    vals = [(lbl, r.get(col), art) for col, lbl, art in _MODOS]
    # NA != 0: só entram modos com participação mensurável (>=0,05%) — um
    # "0,0%" arredondado não é dado, é ruído de casas decimais.
    vals = [(lbl, v, art) for lbl, v, art in vals if pd.notna(v) and v >= 0.05]
    if not vals:
        return None
    vals.sort(key=lambda x: -x[1])
    principal_lbl, principal_v, principal_art = vals[0]
    resto = vals[1:]
    intro = f"{principal_art + ' ' if principal_art else ''}{principal_lbl}"
    s = (f"Pela partição modal do Censo 2022, {intro} é o modo predominante: "
         f"{fmt_pct(principal_v, 1)} das viagens")
    if resto:
        grandes, pequenos = (resto[:4], resto[4:]) if len(resto) > 4 else (resto, [])
        itens_grandes = [f"{fmt_pct(v, 1)} {l}" if a is None else f"{fmt_pct(v, 1)} de {l}" for l, v, a in grandes]
        if pequenos:
            cauda = lista_e([f"{l} ({fmt_pct(v, 1)})" for l, v, a in pequenos])
            corpo = ", ".join(itens_grandes) + f" e uma cauda pequena de {cauda}"
        else:
            corpo = lista_e(itens_grandes)
        s += f", contra {corpo}"
    s += "."
    frota25, frota13 = r.get("frota_total_2025"), r.get("frota_total_2013")
    if pd.notna(frota25):
        s += f" A frota total é de {fmt_num(frota25)} veículos em 2025"
        if pd.notna(frota13):
            s += f" (era {fmt_num(frota13)} em 2013)"
        auto25, moto25 = r.get("auto_por_1000hab_2025"), r.get("moto_por_1000hab_2025")
        if pd.notna(auto25) and pd.notna(moto25):
            s += f", com taxa de motorização de {fmt_num(auto25, 1)} automóveis e {fmt_num(moto25, 1)} motocicletas por mil habitantes"
            auto13, moto13 = r.get("auto_por_1000hab_2013"), r.get("moto_por_1000hab_2013")
            if pd.notna(auto13) and pd.notna(moto13):
                _VERBO_PLURAL = {"caiu": "caíram", "subiu": "subiram"}
                dir_auto = "caiu" if auto25 < auto13 else "subiu"
                dir_moto = "subiu" if moto25 > moto13 else "caiu"
                if dir_auto == dir_moto:
                    s += f" — a taxa de automóveis e a de motocicletas {_VERBO_PLURAL[dir_auto]} ambas desde 2013"
                else:
                    s += (f" — a taxa de automóveis {dir_auto} desde 2013 ({fmt_num(auto13, 1)}/mil), "
                          f"mas a de motocicletas {dir_moto} ({fmt_num(moto13, 1)}/mil)")
        s += "."
    return s


def p3_tempo_deslocamento(r):
    tm = r.get("md22_tempo_medio_min")
    if pd.isna(tm):
        return None
    s = f"Pelos microdados do Censo 2022, o tempo médio de deslocamento é de {fmt_num(tm, 1)} minutos"
    saem, ficam = r.get("md22_tempo_medio_min_saem"), r.get("md22_tempo_medio_min_ficam")
    if pd.notna(saem) and pd.notna(ficam):
        s += (f" — mas essa média esconde uma diferença grande conforme o destino: quem trabalha "
              f"fora do município leva, em média, {fmt_num(saem, 1)} minutos, contra {fmt_num(ficam, 1)} minutos de quem fica")
        mais1h = r.get("md22_tempo_mais_1h_pct")
        if pd.notna(mais1h):
            s += f"; {fmt_pct(mais1h, 1)} dos deslocamentos passam de uma hora"
    s += "."
    rsaem, rficam = r.get("md22_renda_media_saem"), r.get("md22_renda_media_ficam")
    if pd.notna(rsaem) and pd.notna(rficam):
        dif = (rsaem / rficam - 1) * 100 if rficam else None
        s2 = f"A renda média segue o mesmo corte: {fmt_reais(rsaem)} para quem trabalha fora contra {fmt_reais(rficam)} para quem fica"
        if dif is not None:
            s2 += f" ({'+' if dif >= 0 else ''}{fmt_pct(dif, 1)})"
        s2 += "."
        tm_mesmo, tm_fora = r.get("md22_trab_mesmo_munic_pct"), r.get("md22_trab_outro_munic_pct")
        if pd.notna(tm_mesmo) and pd.notna(tm_fora):
            s2 += f" Do total de ocupados, {fmt_pct(tm_mesmo, 1)} trabalham no próprio município e {fmt_pct(tm_fora, 1)} em outro."
        return s + " " + s2
    return s


def p3_viario(r):
    tot = r.get("extensao_viaria_total_km")
    if pd.isna(tot):
        return None
    s = f"O sistema viário soma {fmt_num(tot, 2)} km"
    dens = r.get("densidade_viaria_km_km2")
    densu = r.get("densidade_viaria_urbana_km_km2")
    if pd.notna(dens):
        s += f", com densidade de {fmt_num(dens, 1)} km/km²"
        if pd.notna(densu):
            s += f" ({fmt_num(densu, 1)} km/km² sobre a malha urbanizada)"
    estr, colet, local = r.get("extensao_viaria_estrutural_km"), r.get("extensao_viaria_coletora_km"), r.get("extensao_viaria_local_km")
    if pd.notna(estr) and pd.notna(colet) and pd.notna(local):
        s += f" — {fmt_num(estr, 1)} km de vias estruturais, {fmt_num(colet, 1)} km de coletoras e {fmt_num(local, 1)} km de vias locais"
    s += "."
    ped, ciclov, ciclof, corr = (r.get("extensao_pedestres_km"), r.get("extensao_ciclovia_km"),
                                  r.get("extensao_ciclofaixa_km"), r.get("extensao_corredor_onibus_km"))
    partes2 = []
    if pd.notna(ped) and ped > 0:
        partes2.append(f"{fmt_num(ped, 1)} km de vias exclusivas para pedestres")
    if pd.notna(ciclov) and ciclov > 0:
        partes2.append(f"{fmt_num(ciclov, 1)} km de ciclovia")
    if partes2:
        s2 = "Há " + " e ".join(partes2)
        faltantes = []
        if pd.notna(ciclof) and ciclof == 0:
            faltantes.append("ciclofaixa")
        if pd.notna(corr) and corr == 0:
            faltantes.append("corredor de ônibus")
        if faltantes:
            junc = " nem ".join(faltantes)
            s2 += f" (sem {junc} registrado{'s' if len(faltantes) > 1 else ''})"
        s2 += "."
        s += " " + s2
    npts, nterm, nrotas, ext_r = (r.get("n_pontos_onibus_osm"), r.get("n_terminais_onibus_osm"),
                                   r.get("n_rotas_onibus_osm"), r.get("extensao_rotas_onibus_km"))
    # NA != 0: 0 rotas no OpenStreetMap é, na maioria dos casos, mapeamento
    # incompleto, não ausência real de serviço (achado de 16/09/2026, mesmo
    # motivo pelo qual enriquecer_contexto_mobilidade.py descartou esta
    # variável nas fichas antigas) — só se afirma com rotas > 0 mapeadas.
    if pd.notna(nrotas) and nrotas > 0:
        s3 = f"Pelo mapeamento do OpenStreetMap, o sistema de ônibus tem {fmt_num(npts)} pontos" if pd.notna(npts) else "Pelo mapeamento do OpenStreetMap, o sistema de ônibus tem"
        if pd.notna(nterm):
            s3 += f", {fmt_num(nterm)} terminais"
        s3 += f" e {fmt_num(nrotas)} rotas"
        if pd.notna(ext_r):
            s3 += f", somando {fmt_num(ext_r, 1)} km de extensão"
        s3 += "."
        s += " " + s3
    elif pd.notna(nrotas) and nrotas == 0:
        s += (" Pelo mapeamento do OpenStreetMap, o sistema de ônibus não tem rotas mapeadas — "
              "mapeamento incompleto é mais provável que ausência real de serviço (ver Pendências).")
    return s


def p3_entorno(r):
    tot = r.get("entorno_total")
    if pd.isna(tot) or tot == 0:
        return None
    pav = r.get("via_pavimentada_existe")
    ilu = r.get("pct_iluminacao_2022")
    calc = r.get("pct_calcada_2022")
    rampa = r.get("pct_rampa_2022")
    ponto = r.get("ponto_onibus_existe")
    bike = r.get("via_bicicleta_existe")
    pct_pav = (pav / tot * 100) if pd.notna(pav) else None
    pct_ponto = (ponto / tot * 100) if pd.notna(ponto) else None
    pct_bike = (bike / tot * 100) if pd.notna(bike) else None
    basicos = []
    if pct_pav is not None:
        basicos.append(f"{fmt_pct(pct_pav, 0 if round(pct_pav, 2) == 100 else 1)} têm via pavimentada")
    if pd.notna(ilu):
        basicos.append(f"{fmt_pct(ilu, 2)} iluminação pública")
    if pd.notna(calc):
        basicos.append(f"{fmt_pct(calc, 1)} calçada")
    if not basicos:
        return None
    s = (f"No entorno dos domicílios (Censo 2022, sobre os {fmt_num(tot)} domicílios do município), "
         f"a infraestrutura urbana básica é ")
    alta = all(("100" in b or float(re.search(r'[\d,]+', b).group().replace(',', '.')) >= 90) for b in basicos)
    s += ("quase universal: " if alta else "desigual: ") + ", ".join(basicos) + "."
    cauda = []
    if pd.notna(rampa):
        cauda.append(f"rampa de cadeirante ({fmt_pct(rampa, 1)})")
    partes_baixas = []
    if pct_ponto is not None:
        partes_baixas.append(f"só {fmt_pct(pct_ponto, 1)} dos domicílios têm ponto de ônibus no entorno")
    if pct_bike is not None:
        partes_baixas.append(f"{fmt_pct(pct_bike, 1)} têm via para bicicleta")
    if cauda or partes_baixas:
        s2 = ""
        if cauda:
            s2 += f"A cobertura cai para {' e '.join(cauda)}"
        if partes_baixas:
            if s2:
                s2 += " e cai bastante para o que está mais ligado à mobilidade coletiva e ativa: "
            else:
                s2 += "A cobertura cai bastante para o que está mais ligado à mobilidade coletiva e ativa: "
            s2 += " e ".join(partes_baixas)
        s2 += "."
        s += " " + s2
    return s


def p3_planejamento(r):
    pd_ = r.get("pd")
    partes = []
    if isinstance(pd_, str) and pd_.strip().lower() == "sim":
        s = "O município tem Plano Diretor"
        ano = r.get("pd_ano")
        rev = valor_util(r.get("pd_rev"))
        if pd.notna(ano):
            try:
                s += f" desde {int(float(ano))}"
            except (TypeError, ValueError):
                pass
        if rev and re.match(r"^\d{4}$", str(rev).strip()):
            s += f" (revisado em {rev})"
    else:
        s = "O município não declara ter Plano Diretor" if isinstance(pd_, str) else None
    if s:
        pdmu_possui = r.get("pdmu_possui_2025")
        pdmu_ano = r.get("pdmu_ano_elaboracao")
        pdmu_lei = r.get("pdmu_aprovado_lei_2025")
        obrig = r.get("pdmu_obrigado_2025")
        if isinstance(pdmu_possui, str) and pdmu_possui.strip().lower() == "sim":
            s += " e Plano de Mobilidade Urbana"
            if pd.notna(pdmu_ano):
                s += f" desde {int(pdmu_ano)}"
            if isinstance(pdmu_lei, str) and pdmu_lei.strip().lower() == "sim":
                s += ", aprovado por lei municipal"
            if obrig == 1 or obrig == "1":
                s += " — está entre os municípios obrigados a tê-lo"
        elif obrig == 1 or obrig == "1":
            s += "; está entre os municípios obrigados a ter Plano de Mobilidade Urbana, mas a base não registra que o tenha"
        s += "."
        partes.append(s)
    ciclov, bicicl = r.get("munic_ciclovia_2020"), r.get("munic_bicicletario_2020")
    extras = []
    if pd.notna(ciclov):
        extras.append(("ciclovia própria", ciclov == 1))
    if pd.notna(bicicl):
        extras.append(("bicicletário", bicicl == 1))
    if extras:
        tem = [x[0] for x in extras if x[1]]
        nao = [x[0] for x in extras if not x[1]]
        s2 = "Pela MUNIC 2020, "
        if tem and nao:
            s2 += f"também tem {' e '.join(tem)}, mas não {' nem '.join(nao)}."
        elif tem:
            s2 += f"também tem {' e '.join(tem)}."
        elif nao:
            s2 += f"não tem {' nem '.join(nao)}."
        partes.append(s2)
    return " ".join(partes) if partes else None


_ORGAO_TXT = {}


def p3_gestao(r):
    org = valor_util(r.get("munic_orgao_gestor_2020"))
    if not org:
        return None
    s = f"A gestão do transporte é feita por {str(org).strip()[0].lower() + str(org).strip()[1:]}"
    extras = []
    if r.get("munic_plano_transp_2020") == 1:
        extras.append("plano de transporte próprio")
    if r.get("munic_onibus_intramun_2020") == 1:
        extras.append("serviço de ônibus intramunicipal")
    forma = None
    for col, txt in [("munic_concessao_2020", "contratação por concessão"),
                      ("munic_permissao_2020", "contratação por permissão"),
                      ("munic_autorizacao_2020", "contratação por autorização"),
                      ("munic_prestacao_direta_2020", "prestação direta"),
                      ("munic_nao_regulamentado_2020", "serviço não regulamentado")]:
        if r.get(col) == 1:
            forma = txt
            break
    if forma:
        extras.append(forma)
    if extras:
        s += ", com " + lista_e(extras)
    s += "."
    return s


_MODOS_SEG = ["pedestre", "ciclista", "motociclista", "automovel", "caminhonete", "triciclo", "veic_pesado", "ocup_onibus", "outros"]
_MODOS_SEG_LBL = {"pedestre": "pedestres", "ciclista": "ciclistas", "motociclista": "motociclistas",
                   "automovel": "ocupantes de automóvel", "caminhonete": "ocupantes de caminhonete",
                   "triciclo": "ocupantes de triciclo", "veic_pesado": "ocupantes de veículo pesado",
                   "ocup_onibus": "ocupantes de ônibus", "outros": "outros"}


def _por_modo(r, prefixo):
    pos, zero = [], []
    for m in _MODOS_SEG:
        v = r.get(f"{prefixo}_{m}_2019")
        if pd.isna(v):
            continue
        if v > 0:
            pos.append((_MODOS_SEG_LBL[m], int(v)))
        elif v == 0:
            zero.append(_MODOS_SEG_LBL[m])
    return pos, zero


def p3_seguranca(r):
    tot_ob, tot_fe = r.get("obitos_transito_2019"), r.get("feridos_transito_2019")
    if pd.isna(tot_ob):
        return None
    s = f"Em segurança viária, 2019 registrou {fmt_num(tot_ob)} óbitos"
    if pd.notna(tot_fe):
        s += f" e {fmt_num(tot_fe)} feridos"
    s += " em acidentes de trânsito"
    taxa = r.get("taxa_obitos_transito_100k_2019")
    cagr = r.get("obitos_transito_cagr_2010_2019")
    if pd.notna(taxa):
        s += f" — taxa de {fmt_num(taxa, 1)} óbitos por 100 mil habitantes"
        if pd.notna(cagr):
            dirc = "queda" if cagr < 0 else "alta"
            s += f", em {dirc} de {fmt_pct(abs(cagr), 2)} ao ano desde 2010"
    s += "."
    pos_ob, zero_ob = _por_modo(r, "obitos")
    if pos_ob:
        pos_ob.sort(key=lambda x: -x[1])
        s2 = "Por modo, os óbitos se dividem entre " + lista_e([f"{l} ({v})" for l, v in pos_ob])
        if "ocupantes de ônibus" in zero_ob:
            s2 += ", sem nenhum óbito entre ocupantes de ônibus"
        s2 += "."
        s += " " + s2
    pos_fe, zero_fe = _por_modo(r, "feridos")
    if pos_fe:
        pos_fe.sort(key=lambda x: -x[1])
        s3 = "Os feridos, entre " + lista_e([f"{l} ({v})" for l, v in pos_fe])
        if zero_fe:
            s3 += f", sem feridos entre {lista_e(zero_fe)}"
        s3 += " (SIMU, 2019)."
        s += " " + s3
    return s


def montar_bloco3(r):
    partes = [p3_modal_frota(r), p3_tempo_deslocamento(r), p3_viario(r), p3_entorno(r),
              p3_planejamento(r), p3_gestao(r), p3_seguranca(r)]
    partes = [p for p in partes if p]
    if not partes:
        return None
    return "## 3. Contexto da mobilidade\n\n" + "\n\n".join(partes)


# =================================================================
# RÉGUA DESCRITIVA (prosa) — reaproveita a lógica de enriquecer_regua_portao
# =================================================================
def montar_regua_descritiva(k, portao, aba_de, subtipo_por_aba, linhas, situacao, nome_mun):
    abas = aba_de.get(k, [])
    destino_confirmado = regua.resolve_destino_portao(k, portao, situacao)
    cam_aba = None
    if abas:
        pares = [regua.camada_por_aba(a, k, subtipo_por_aba) for a in dict.fromkeys(abas)]
        cams = [p[1] for p in pares if p[1]]
        if cams:
            cam_aba = sorted(cams)[-1]

    p = portao.get(k)
    val, ev = (p if p else (None, None))

    # Precedência: (1) portão mecanicamente resolvido pelo valor exato do campo
    # (LEITURA) — ex.: "nenhum"→1a, "procedimento"→1b; (2) Subtipo já
    # classificado à mão pelo autor na planilha (`camada_por_aba`), que também é
    # afirmação — não "candidato" — quando há evidência registrada (o autor já
    # decidiu 1c vs 2a lendo o campo `Portão`/evidência, mesmo que o valor do
    # campo não bata literalmente com uma chave de LEITURA, como em "pessoa
    # (residência)"); (3) Subtipo preenchido mas SEM evidência documentada —
    # candidato mais fraco; (4) nada determinado.
    camada_final = destino_confirmado or cam_aba
    fonte_confiavel = bool(destino_confirmado) or (cam_aba and ev)
    frases = []

    if "Regulamentada não implantada" in abas:
        # regra A.1.6 (decisão do autor, 26/09/2026): norma sem operação gratuita — fora das camadas
        frases.append(f"{nome_mun} está no grupo **regulamentada e não implantada** (regra A.1.6): há norma que "
                      f"institui a Tarifa Zero, mas a operação gratuita não começou — fica fora das camadas e da "
                      f"contagem do panorama até a implantação.")
    elif camada_final and camada_final in regua.CAMADA and fonte_confiavel:
        rot, universal = regua.CAMADA[camada_final]
        rot_curto = rot.split("**")[1] if "**" in rot else rot
        s = f"{nome_mun} está na camada {rot_curto}"
        if val and val.strip().lower() != "nenhum":
            s += f", sub-marcada pelo portão de {val}"
        s += ": "
        ev_ok = evidencia_citavel(ev)
        if ev_ok:
            s += ev_ok.strip().rstrip(".") + ". "
        elif ev:
            s += ("classificação com evidência registrada na planilha da régua (nota interna de pesquisa, "
                  "não citável diretamente na tese — ver `Tipologias TZ - consolidado.xlsx`). ")
        elif camada_final == "1a":
            s += "não há evidência de condição de acesso registrada na planilha da régua. "
        frases.append(s.strip())
    elif camada_final and camada_final in regua.CAMADA:
        rot, _ = regua.CAMADA[camada_final]
        rot_curto = rot.split("**")[1] if "**" in rot else rot
        frases.append(f"{nome_mun} é candidato à camada {rot_curto} pela planilha (Subtipo classificado), mas "
                       f"sem evidência documentada registrada — a classificar com o dispositivo antes de afirmar.")
    elif val:
        frases.append(f"{nome_mun} tem portão de acesso do tipo \"{val}\" identificado na planilha, mas a camada "
                       f"exata (universal ou parcial) ainda depende de checar o dispositivo — não decidido nesta rodada.")
    else:
        frases.append(f"A camada de {nome_mun} na régua descritiva ainda não está determinada — "
                       f"portão de acesso não verificado ou município fora das abas de `Tipologias TZ - consolidado.xlsx`.")

    nl = valor_util(linhas.get(k))
    if nl:
        frases.append(f"O sistema tem {nl} linha(s) registradas (base-mestre); a cobertura proporcional da rede "
                       f"(critério de Kębłowski) ainda não foi conferida contra as linhas alcançadas pela gratuidade.")
    else:
        frases.append("Cobertura proporcional da rede: número de linhas do sistema não registrado na base-mestre "
                       "— sem ele a proporção não pode ser aferida.")
    return "### Régua descritiva\n\n" + " ".join(frases)


# =================================================================
# IDEMPOTÊNCIA — marcadores com hash
# =================================================================
def _hash(txt):
    return hashlib.sha1(txt.strip().encode("utf-8")).hexdigest()[:10]


def envolver(bloco_id, corpo):
    h = _hash(corpo)
    return (f"<!-- prosa:{bloco_id}:inicio hash:{h} gerado:{datetime.date.today().isoformat()} -->\n"
            f"{corpo}\n"
            f"<!-- prosa:{bloco_id}:fim -->")


_RE_MARK = {}


def _re_marcador(bloco_id):
    if bloco_id not in _RE_MARK:
        _RE_MARK[bloco_id] = re.compile(
            rf"<!-- prosa:{bloco_id}:inicio hash:([0-9a-f]+)[^>]*-->\n(.*?)\n<!-- prosa:{bloco_id}:fim -->",
            re.S)
    return _RE_MARK[bloco_id]


def aplicar_bloco(txt, bloco_id, corpo_novo, ancoras_insercao, forcar=False):
    """Retorna (novo_txt, status). status em: 'inserido'/'substituido'/'igual'/
    'divergente-pulado'/'conteudo-manual-pulado'/'sem-ancora'."""
    if corpo_novo is None:
        return txt, "sem-dados"
    m = _re_marcador(bloco_id).search(txt)
    if m:
        hash_salvo, conteudo_atual = m.group(1), m.group(2)
        if _hash(conteudo_atual) != hash_salvo and not forcar:
            return txt, "divergente-pulado"
        # 28/09/2026: compara pelo hash do conteúdo, não pelo invólucro — o carimbo "gerado:AAAA-MM-DD"
        # muda todo dia e fazia uma segunda passada reescrever as 272 fichas só para trocar a data.
        if _hash(corpo_novo) == hash_salvo:
            return txt, "igual"
        novo_bloco = envolver(bloco_id, corpo_novo)
        return txt[:m.start()] + novo_bloco + txt[m.end():], "substituido"
    # sem marcador: procura a seção-alvo (heading do próprio bloco) já existente
    titulo = corpo_novo.split("\n", 1)[0]
    padrao_secao = re.escape(titulo).replace(r"\ ", r"\s+")
    m2 = re.search(rf"^{padrao_secao}.*?(?=\n^#{{1,3}}\s|\Z)", txt, re.S | re.M)
    if m2:
        conteudo_existente = txt[m2.end(0) if False else m2.start():m2.end()]
        # já tem título mas sem marcador — só considera "vazio" se não houver texto substantivo
        corpo_sem_titulo = re.sub(r"^.*?\n", "", conteudo_existente, count=1).strip()
        if len(corpo_sem_titulo) > 40 and not forcar:
            return txt, "conteudo-manual-pulado"
        novo_bloco = envolver(bloco_id, corpo_novo)
        return txt[:m2.start()] + novo_bloco + "\n" + txt[m2.end():], "substituido" if corpo_sem_titulo else "inserido"
    # nada existe: insere na primeira âncora que casar
    for padrao in ancoras_insercao:
        anc = re.search(padrao, txt, re.S | re.M)
        if anc:
            novo_bloco = envolver(bloco_id, corpo_novo)
            return txt[:anc.end()] + "\n\n" + novo_bloco + txt[anc.end():], "inserido"
    return txt, "sem-ancora"


# =================================================================
def gerar_para_municipio(df, portao, aba_de, subtipo_por_aba, linhas, situacao, municipio, uf):
    r = linha_municipio(df, municipio, uf)
    if r is None:
        return None, None, None, f"sem correspondência no banco para {municipio}/{uf}"
    b2 = montar_bloco2(r)
    b3 = montar_bloco3(r)
    k = (regua.n(municipio), uf.strip().upper())
    rd = montar_regua_descritiva(k, portao, aba_de, subtipo_por_aba, linhas, situacao, titulo_mun(r["nome_mun"]))
    return b2, b3, rd, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--testar", nargs=2, metavar=("MUNICIPIO", "UF"))
    ap.add_argument("--gravar", action="store_true")
    ap.add_argument("--forcar", action="store_true")
    ap.add_argument("--so", nargs=2, metavar=("MUNICIPIO", "UF"),
                    help="28/09/2026: restringe a gravação a uma ficha (útil com --forcar)")
    a = ap.parse_args()

    df = carregar_base()
    portao, aba_de, subtipo_por_aba, linhas, situacao = regua.carregar()

    if a.testar:
        municipio, uf = a.testar
        b2, b3, rd, erro = gerar_para_municipio(df, portao, aba_de, subtipo_por_aba, linhas, situacao, municipio, uf)
        if erro:
            print("🔴", erro)
            return
        print(b2 or "(bloco 2 sem dados)")
        print()
        print(b3 or "(bloco 3 sem dados)")
        print()
        print(rd or "(régua descritiva sem dados)")
        return

    if not os.path.isdir(FICHAS_DIR):
        sys.exit(f"🔴 não achei as fichas em {FICHAS_DIR}")
    arquivos = sorted(glob.glob(os.path.join(FICHAS_DIR, "Ficha - *.md")))
    print(f"{len(arquivos)} fichas encontradas")

    status_count = {}
    plano = []
    sem_match = []
    for path in arquivos:
        txt = open(path, encoding="utf-8").read()
        mm = re.search(r"^municipio:\s*(.+)$", txt, re.M)
        uu = re.search(r"^uf:\s*(.+)$", txt, re.M)
        if not (mm and uu):
            continue
        municipio, uf = mm.group(1).strip(), uu.group(1).strip()
        if a.so and (municipio, uf) != (a.so[0], a.so[1]):
            continue
        b2, b3, rd, erro = gerar_para_municipio(df, portao, aba_de, subtipo_por_aba, linhas, situacao, municipio, uf)
        if erro:
            sem_match.append(f"{municipio} ({uf})")
            continue
        txt2 = txt
        s2 = "sem-ancora"
        txt2, s2 = aplicar_bloco(txt2, "bloco2", b2,
                                  [r"^## 1\.\s*Briefing.*?(?=\n^## |\Z)"], a.forcar)
        status_count[("bloco2", s2)] = status_count.get(("bloco2", s2), 0) + 1
        txt3, s3 = aplicar_bloco(txt2, "bloco3", b3,
                                  [r"^## 2\.\s*Principais dados.*?(?=\n^## |\Z)",
                                   r"^## 1\.\s*Briefing.*?(?=\n^## |\Z)"], a.forcar)
        status_count[("bloco3", s3)] = status_count.get(("bloco3", s3), 0) + 1
        txt4, s4 = aplicar_bloco(txt3, "regua_descritiva", rd,
                                  [r"^## 3\.\s*Contexto da mobilidade.*?(?=\n^## |\Z)",
                                   r"^## 2\.\s*Principais dados.*?(?=\n^## |\Z)"], a.forcar)
        status_count[("regua_descritiva", s4)] = status_count.get(("regua_descritiva", s4), 0) + 1
        if txt4 != txt:
            plano.append((path, txt4))

    print("\n=== status por bloco ===")
    for (bloco, st), c in sorted(status_count.items()):
        print(f"  {bloco:20s} {st:25s} {c}")
    print(f"\n{len(plano)} fichas seriam alteradas.")
    if sem_match:
        print(f"\nSem correspondência no banco ({len(sem_match)}):")
        for m in sem_match[:30]:
            print(f"  - {m}")
        if len(sem_match) > 30:
            print(f"  ... e mais {len(sem_match) - 30}")

    if not a.gravar:
        print("\nnada foi escrito. Para aplicar: --gravar")
        return
    bk = os.path.join(RAIZ, "_meta", "_backups", "prosa-" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M"))
    os.makedirs(bk, exist_ok=True)
    for path, novo in plano:
        # backup com sufixo .bak (não cria nome de nota duplicado); newline="\n" evita CRLF no Windows
        shutil.copy2(path, os.path.join(bk, os.path.basename(path) + ".bak"))
        open(path, "w", encoding="utf-8", newline="\n").write(novo)
    print(f"\n✅ {len(plano)} fichas gravadas · backup em {os.path.basename(bk)}")


if __name__ == "__main__":
    main()
