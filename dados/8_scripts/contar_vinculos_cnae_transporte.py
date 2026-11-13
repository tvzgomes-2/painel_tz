#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""contar_vinculos_cnae_transporte.py (v3 — caminho real confirmado) —
baixa a RAIS-ESTABELECIMENTOS (arquivo NACIONAL ÚNICO por ano, achado via
diagnóstico do FTP em 24/07/2026) e conta o Nº DE VÍNCULOS FORMAIS
(coluna "Qtd Vínculos Ativos" de cada estabelecimento), por MUNICÍPIO, só
nas CNAEs de transporte coletivo/fretamento do recorte do Eixo 2:

    4921-3/01  Transp. rodoviário coletivo, itinerário fixo, municipal
    4921-3/02  Transp. rodoviário coletivo, itinerário fixo, metropolitano
    4922-1/01  Transp. rodoviário coletivo, itinerário fixo, intermunicipal
    4922-1/02  Transp. rodoviário coletivo, itinerário fixo, interestadual
    4929-9/01  Transp. rodoviário coletivo, fretamento, municipal
    4929-9/02  Transp. rodoviário coletivo, fretamento, intermunicipal/interestadual/internacional

HISTÓRICO DE VERSÕES (documentado porque cada uma corrigiu um erro real,
não é só estilo):
  v1: pedia download manual pelo portal gov.br — funcionava, mas dava
      trabalho manual.
  v2: tentou automatizar via FTP com o padrão de URL antigo
      (`RAIS/<ano>/<UF><ano>.7z`, de cemin.wikidot.com/raisrm) — o autor
      rodou e deu "550 arquivo não encontrado" nas 27 UFs, nos 2 anos.
      Descobrimos por quê: esse padrão é de uma prática ANTERIOR à
      reorganização do Ministério; não existe mais por UF.
  v3 (esta): confirmado por diagnóstico real do FTP (`diagnostico_ftp_
      rais2.py`, rodado pelo autor em 24/07/2026) — desde pelo menos 2022,
      o Ministério distribui:
        - `RAIS_ESTAB_PUB.7z`: 1 arquivo NACIONAL ÚNICO (estabelecimentos,
          ~90-140MB) — o que usamos aqui, é tudo que precisamos.
        - `RAIS_VINC_PUB_<REGIÃO>.7z`: 6 arquivos por REGIÃO (não por UF),
          cada um várias centenas de MB a >1GB (vínculos individuais) —
          NÃO usado aqui, desnecessariamente pesado pro que queremos.
      Caminho confirmado: `/pdet/microdados/RAIS/<ano>/RAIS_ESTAB_PUB.7z`
      — testado e existente em 2022, 2023, "2023 Parcial", 2024 (pastas
      2025 também existe, não inspecionada).

REQUISITOS (rodar localmente): pip install pandas py7zr
USO: python contar_vinculos_cnae_transporte.py
     (baixa pra .\rais_cache\<ano>\RAIS_ESTAB_PUB.7z, extrai, filtra, apaga
     os brutos depois de processar — usa --manter-brutos pra não apagar.)

RETOMÁVEL: se já existe `saida_rais_estab_cnae\vinculos_cnae_transporte_
<ano>.csv`, o ano é pulado (apague o arquivo se quiser reprocessar). Como
agora é só 1 arquivo por ano (não 27), a chance de perder progresso num
reinício é bem menor que na v2, mas o download/extração de cada ano ainda
fica em pasta própria — se cair no meio, rodar de novo retoma sem
rebaixar o que já teria sido extraído."""
import argparse
import ftplib
import glob
import os
import re
import sys
import unicodedata

import pandas as pd

try:
    import py7zr
except ImportError:
    sys.exit("Faltou instalar dependência. Rode:\n    pip install pandas py7zr\ne execute de novo.")

# ============ AJUSTE AQUI ============
ANOS = ["2022", "2024"]  # ano-base 2022 (mesma safra do RAIS/POLO já integrado) + o mais recente

FTP_HOST = "ftp.mtps.gov.br"
FTP_PATH_TEMPLATE = "/pdet/microdados/RAIS/{ano}/RAIS_ESTAB_PUB.7z"

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rais_cache")
BASE_CSV = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\Base Municipal v3\base_municipal_v3.csv"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saida_rais_estab_cnae")

CNAES_ALVO = {"4921301", "4921302", "4922101", "4922102", "4929901", "4929902"}
# ======================================


def log(msg):
    print(msg, flush=True)


def salvar_atomico(df, path):
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, path)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def normalizar_cnae(v):
    if pd.isna(v):
        return None
    digits = re.sub(r"\D", "", str(v))
    return digits[:7] if len(digits) >= 7 else None


def c7(x):
    try:
        return str(int(float(x))).zfill(7)
    except Exception:
        return None


def baixa_ftp(ano, dest_7z):
    caminho = FTP_PATH_TEMPLATE.format(ano=ano)
    try:
        ftp = ftplib.FTP(FTP_HOST, timeout=120)
        ftp.login()
        tamanho = None
        try:
            tamanho = ftp.size(caminho)
        except Exception:
            pass
        if tamanho:
            log(f"  tamanho esperado: {tamanho/1e6:.1f} MB")
        with open(dest_7z, "wb") as f:
            ftp.retrbinary(f"RETR {caminho}", f.write, blocksize=1024 * 1024)
        ftp.quit()
        return True, None
    except Exception as e:
        return False, str(e)


def extrai_7z(path_7z, pasta_destino):
    with py7zr.SevenZipFile(path_7z, mode="r") as z:
        z.extractall(path=pasta_destino)


def achar_txt_extraido(pasta):
    """Procura o arquivo de dados extraído. NÃO confia só na extensão
    .txt — achado real (24/07/2026): o RAIS_ESTAB_PUB.7z de 2024 extrai um
    arquivo chamado 'RAIS_ESTAB_PUB.COMT' (extensão não-padrão, mesmo
    sendo o mesmo texto ';'-separado de sempre). Prioriza .txt se existir;
    senão pega o maior arquivo da pasta (o de dados é sempre o maior, MBs/
    GB — não tem como ser confundido com algum eventual .pdf/.txt de
    licença que venha junto)."""
    txts = glob.glob(os.path.join(pasta, "**", "*.txt"), recursive=True)
    if txts:
        return txts[0]
    todos = [f for f in glob.glob(os.path.join(pasta, "**", "*"), recursive=True) if os.path.isfile(f)]
    if not todos:
        return None
    maior = max(todos, key=os.path.getsize)
    log(f"  (nenhum .txt encontrado — usando o maior arquivo extraído: {os.path.basename(maior)}, "
        f"{os.path.getsize(maior)/1e6:.1f} MB)")
    return maior


def ler_cabecalho(path):
    """Lê e detecta separador/encoding do cabeçalho. Achado real
    (24/07/2026): o RAIS_ESTAB_PUB de 2024 vem com os nomes de coluna
    ENVOLTOS EM ASPAS LITERAIS no cabeçalho (ex.: '"Município - Código"')
    — o split ingênuo mantinha as aspas dentro do nome, mas o pandas (que
    entende CSV com aspas de verdade) devolve o nome SEM aspas depois de
    ler — dava ValueError de usecols não batendo. Removendo aspas nas
    pontas de cada nome aqui já resolve pros dois formatos (2022, sem
    aspas; 2024, com aspas)."""
    for enc in ("latin1", "utf-8", "utf-8-sig", "cp1252"):
        try:
            with open(path, "r", encoding=enc, errors="strict") as f:
                primeira = f.readline()
            for sep in (";", ",", "\t", "|"):
                partes = [p.strip().strip('"').strip() for p in primeira.strip().split(sep)]
                if len(partes) > 3:
                    return partes, sep, enc
        except (UnicodeDecodeError, LookupError):
            continue
    return None, None, None


def achar_coluna(colunas, candidatos_regex):
    colunas_norm = {c: norm(c) for c in colunas}
    for padrao in candidatos_regex:
        pad_norm = norm(padrao)
        for original, n in colunas_norm.items():
            if pad_norm in n:
                return original, padrao
    return None, None


def processar_ano(ano, manter_brutos):
    log(f"\n{'='*70}\nAno-base {ano}\n{'='*70}")
    out_csv = os.path.join(OUT_DIR, f"vinculos_cnae_transporte_{ano}.csv")
    if os.path.exists(out_csv):
        log(f"  já existe {out_csv} — pulando (apague o arquivo se quiser refazer).")
        return pd.read_csv(out_csv, dtype=str)

    pasta_ano = os.path.join(CACHE_DIR, ano)
    os.makedirs(pasta_ano, exist_ok=True)
    dest_7z = os.path.join(pasta_ano, "RAIS_ESTAB_PUB.7z")
    pasta_extraida = os.path.join(pasta_ano, "extraido")

    txt = achar_txt_extraido(pasta_extraida) if os.path.isdir(pasta_extraida) else None

    if txt is None:
        if not os.path.exists(dest_7z):
            log(f"  baixando {FTP_PATH_TEMPLATE.format(ano=ano)} ...")
            ok, erro = baixa_ftp(ano, dest_7z)
            if not ok:
                log(f"  ⚠️ falhou o download: {erro}")
                return None
            log(f"  baixado: {os.path.getsize(dest_7z)/1e6:.1f} MB")
        log(f"  extraindo .7z...")
        try:
            os.makedirs(pasta_extraida, exist_ok=True)
            extrai_7z(dest_7z, pasta_extraida)
        except Exception as e:
            log(f"  ⚠️ falhou a extração: {e}")
            return None
        txt = achar_txt_extraido(pasta_extraida)
        if not manter_brutos and os.path.exists(dest_7z):
            os.remove(dest_7z)

    if txt is None:
        log(f"  ⚠️ não achei .txt extraído em {pasta_extraida}.")
        return None

    log(f"  processando {os.path.basename(txt)}...")
    colunas, sep, enc = ler_cabecalho(txt)
    if colunas is None:
        log(f"  ⚠️ não detectei separador/encoding — abra o arquivo manualmente e cole aqui as primeiras colunas.")
        return None
    log(f"  separador={sep!r} encoding={enc!r}")
    log(f"  colunas ({len(colunas)}): {colunas}")

    col_cnae, _ = achar_coluna(colunas, ["CNAE 2.0 Subclasse", "Subclasse CNAE", "CNAE Subclasse", "CNAE 2.0"])
    col_muni, _ = achar_coluna(colunas, ["Município", "Municipio"])
    col_vinc, _ = achar_coluna(colunas, ["Qtd Vinculos Ativos", "Qtd Vínculos Ativos", "Vinculos Ativos"])

    log(f"  coluna CNAE: {col_cnae!r} | Município: {col_muni!r} | Vínculos: {col_vinc!r}")
    if not (col_cnae and col_muni and col_vinc):
        log("  ⚠️ PAREI — não achei as 3 colunas com confiança. Cole aqui a lista de colunas acima "
            "pra eu ajustar os candidatos de nome.")
        return None

    usecols = [col_cnae, col_muni, col_vinc]
    acumulado = {}
    total_linhas = 0
    total_alvo = 0
    leitor = pd.read_csv(txt, sep=sep, encoding=enc, usecols=usecols, dtype=str,
                          chunksize=500_000, on_bad_lines="skip", engine="c")
    for chunk in leitor:
        total_linhas += len(chunk)
        chunk["_cnae_norm"] = chunk[col_cnae].map(normalizar_cnae)
        alvo = chunk[chunk["_cnae_norm"].isin(CNAES_ALVO)].copy()
        total_alvo += len(alvo)
        if len(alvo) == 0:
            continue
        alvo["_vinc_num"] = pd.to_numeric(
            alvo[col_vinc].astype(str).str.replace(",", ".", regex=False), errors="coerce"
        ).fillna(0)
        grp = alvo.groupby(col_muni)["_vinc_num"].sum()
        for muni, soma in grp.items():
            acumulado[muni] = acumulado.get(muni, 0) + soma
    log(f"  {total_linhas} linhas lidas, {total_alvo} estabelecimentos nas CNAEs alvo")

    if not manter_brutos:
        try:
            os.remove(txt)
        except OSError:
            pass

    if not acumulado:
        log("  ⚠️ nenhum estabelecimento nas CNAEs alvo — confira a coluna de CNAE escolhida.")
        return None

    df_out = pd.DataFrame(
        [{"cod_muni_rais_bruto": k, f"vinculos_cnae_transporte_{ano}": v} for k, v in acumulado.items()]
    )
    log(f"  {len(df_out)} municípios (código bruto). Soma nacional: "
        f"{df_out[f'vinculos_cnae_transporte_{ano}'].sum():,.0f}")

    df_out.to_csv(out_csv, index=False)
    return df_out


def bridge_codigo_rais_para_ibge(df_out, col_valor, base):
    base_cods = set(base["cod_ibge"])
    base_cod6 = {c[:6]: c for c in base_cods}
    bruto = df_out["cod_muni_rais_bruto"].astype(str).str.strip()
    cand_7 = bruto.str.zfill(7)
    cand_6 = bruto.str.zfill(6)
    match_7 = cand_7.isin(base_cods).sum()
    match_6 = cand_6.map(lambda x: x in base_cod6).sum()
    log(f"  bridge: hipótese 7 dígitos = {match_7}/{len(df_out)}; hipótese 6 dígitos (sem DV) = {match_6}/{len(df_out)}")
    if match_6 >= match_7:
        df_out["cod_ibge"] = cand_6.map(base_cod6)
    else:
        df_out["cod_ibge"] = cand_7.where(cand_7.isin(base_cods))
    sem_match = df_out["cod_ibge"].isna().sum()
    if sem_match:
        log(f"  ⚠️ {sem_match} códigos sem correspondência.")
    return df_out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manter-brutos", action="store_true", help="não apaga .7z/.txt depois de processar")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    base = pd.read_csv(BASE_CSV, usecols=["cod_ibge"], dtype=str, low_memory=False)
    base["cod_ibge"] = base["cod_ibge"].map(c7)

    algum_ok = False
    for ano in ANOS:
        df_ano = processar_ano(ano, args.manter_brutos)
        if df_ano is None:
            continue
        col_valor = f"vinculos_cnae_transporte_{ano}"
        if "cod_ibge" not in df_ano.columns:
            df_ano = bridge_codigo_rais_para_ibge(df_ano, col_valor, base)
            df_ano = df_ano.dropna(subset=["cod_ibge"])[["cod_ibge", col_valor]]
            salvar_atomico(df_ano, os.path.join(OUT_DIR, f"vinculos_cnae_transporte_{ano}.csv"))
        log(f"  final: {len(df_ano)} municípios com cod_ibge.")
        algum_ok = True

    if not algum_ok:
        sys.exit("\nNenhum ano processado com sucesso — veja os avisos acima.")
    log(
        "\nPróximo passo: cole aqui o resumo impresso acima (colunas escolhidas, cobertura do "
        "bridge, soma nacional) — eu confirmo e integro como coluna própria no base_municipal_v3.csv."
    )


if __name__ == "__main__":
    main()
