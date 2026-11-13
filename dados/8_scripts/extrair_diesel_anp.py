"""
Extrai o preço médio anual do óleo diesel a partir dos arquivos "semanal Brasil"
da ANP (Levantamento de Preços de Combustíveis), para comparar com a série de
tarifa de ônibus reconciliada (2005-2024) e a série de Carvalho e Pereira
(1995-2008) já usadas no Cap. 2.

CONTEXTO (28/07/2026): o sandbox onde eu (Claude) processo dados travou depois
de eu já ter baixado os dois arquivos-fonte via navegador. Este script roda na
sua máquina — depois de rodar, me devolva o CSV gerado (ou cole a tabela impressa
no terminal) para eu seguir a análise (testar se o diesel explica a desaceleração
da tarifa real em 2005-2006, ou os regimes 2013-2019 / pandemia / pós-pandemia).

USO:
    1. Confirme que os dois arquivos estão na mesma pasta deste script, ou ajuste
       PASTA_ARQUIVOS abaixo. Baixe-os aqui se ainda não tiver:
       - semanal-brasil-2004-a-2012.xlsx
         https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/shlp/2001-2012/semanal-brasil-2004-a-2012.xlsx
       - semanal-brasil-desde-2013.xlsx
         https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/shlp/semanal/semanal-brasil-desde-2013.xlsx
       (os dois já foram baixados nesta sessão e devem estar em Downloads)
    2. pip install pandas openpyxl  (se ainda não tiver)
    3. python extrair_diesel_anp.py

SAÍDA:
    - Imprime no terminal a estrutura de cada arquivo (abas, colunas, head) —
      IMPORTANTE: confira se bate com o que o script espera (ver DIAGNÓSTICO
      abaixo) porque não consegui inspecionar os arquivos antes do sandbox travar.
    - Se conseguir detectar as colunas esperadas, salva:
      diesel_anp_anual_1995_2024.csv  (ano, preco_medio_revenda_R$_litro, n_semanas)
    - Se NÃO conseguir detectar automaticamente, imprime os nomes de coluna e
      valores únicos da coluna de produto, para eu ajustar o script na próxima
      rodada — nesse caso, é só me colar o que apareceu no terminal.
"""

import glob
import os
import re
import sys

import pandas as pd

PASTA_ARQUIVOS = os.path.dirname(os.path.abspath(__file__))  # ajuste se necessário

ARQUIVOS_ESPERADOS = [
    "semanal-brasil-2004-a-2012.xlsx",
    "semanal-brasil-desde-2013.xlsx",
]


def localizar_arquivos():
    encontrados = []
    for nome in ARQUIVOS_ESPERADOS:
        caminho = os.path.join(PASTA_ARQUIVOS, nome)
        if os.path.exists(caminho):
            encontrados.append(caminho)
        else:
            # tenta achar por glob (nome parecido) na pasta do script e no Downloads do usuário
            candidatos = glob.glob(os.path.join(PASTA_ARQUIVOS, "*semanal*brasil*.xlsx"))
            downloads = os.path.join(os.path.expanduser("~"), "Downloads")
            if os.path.isdir(downloads):
                candidatos += glob.glob(os.path.join(downloads, "*semanal*brasil*.xlsx"))
            for c in candidatos:
                if c not in encontrados:
                    encontrados.append(c)
    return sorted(set(encontrados))


def detectar_coluna(colunas, padroes):
    """Procura a primeira coluna cujo nome (normalizado, sem acento/maiúsculas)
    contenha algum dos padrões."""
    def normaliza(s):
        s = str(s).upper()
        for a, b in [("Á", "A"), ("Ã", "A"), ("Â", "A"), ("É", "E"), ("Ê", "E"),
                     ("Í", "I"), ("Ó", "O"), ("Õ", "O"), ("Ô", "O"), ("Ú", "U"), ("Ç", "C")]:
            s = s.replace(a, b)
        return s

    norm_map = {c: normaliza(c) for c in colunas}
    for padrao in padroes:
        for col, norm in norm_map.items():
            if padrao in norm:
                return col
    return None


def encontrar_linha_cabecalho(caminho, aba):
    """Os arquivos da ANP têm ~8 linhas de metadados/relatório antes da
    tabela de verdade. Varre as primeiras 30 linhas (sem cabeçalho) procurando
    a linha que contém a célula 'PRODUTO' — essa é a linha de cabeçalho real."""
    bruto = pd.read_excel(caminho, sheet_name=aba, header=None, nrows=30)
    for i, row in bruto.iterrows():
        valores = [str(v).strip().upper() for v in row.tolist()]
        if "PRODUTO" in valores:
            return i
    return None


def carregar_arquivo(caminho):
    print(f"\n{'='*70}\nLendo: {caminho}\n{'='*70}")
    xl = pd.ExcelFile(caminho)
    print("Abas encontradas:", xl.sheet_names)
    melhor_aba = xl.sheet_names[0]

    linha_cab = encontrar_linha_cabecalho(caminho, melhor_aba)
    print(f"Linha de cabeçalho real detectada: {linha_cab}")

    if linha_cab is not None:
        df = xl.parse(melhor_aba, header=linha_cab)
    else:
        df = xl.parse(melhor_aba)

    print(f"Aba usada: '{melhor_aba}' — {df.shape[0]} linhas, {df.shape[1]} colunas")
    print("Colunas:", list(df.columns))
    print(df.head(8).to_string())
    return df


def processar(df):
    col_produto = detectar_coluna(df.columns, ["PRODUTO"])
    col_data = detectar_coluna(df.columns, ["DATA INICIAL", "DATA_INICIAL", "DATA"])
    col_preco = detectar_coluna(
        df.columns,
        ["PRECO MEDIO REVENDA", "PRECO MEDIO DE REVENDA", "PRECO MEDIO"],
    )

    print("\nDIAGNÓSTICO de colunas detectadas:")
    print("  coluna de produto :", col_produto)
    print("  coluna de data    :", col_data)
    print("  coluna de preço   :", col_preco)

    if col_produto is None or col_preco is None or col_data is None:
        print("\n!! Não consegui detectar automaticamente todas as colunas necessárias.")
        if col_produto:
            print("Valores únicos na coluna de produto:", df[col_produto].dropna().unique())
        return None

    print("\nValores únicos na coluna de produto:", sorted(df[col_produto].dropna().unique().tolist()))

    # filtra linhas de diesel (cobre variações: "ÓLEO DIESEL", "OLEO DIESEL", "DIESEL S10", "DIESEL S500" etc.)
    mask_diesel = df[col_produto].astype(str).str.upper().str.contains("DIESEL", na=False)
    df_diesel = df[mask_diesel].copy()
    print(f"\nLinhas de diesel encontradas: {len(df_diesel)} (de {len(df)} totais)")
    if df_diesel.empty:
        return None

    df_diesel[col_data] = pd.to_datetime(df_diesel[col_data], errors="coerce")
    df_diesel["ano"] = df_diesel[col_data].dt.year
    df_diesel[col_preco] = pd.to_numeric(
        df_diesel[col_preco].astype(str).str.replace(",", "."), errors="coerce"
    )

    anual = (
        df_diesel.groupby("ano")[col_preco]
        .agg(preco_medio_revenda_reais_litro="mean", n_semanas="count")
        .reset_index()
    )
    return anual


def main():
    arquivos = localizar_arquivos()
    if not arquivos:
        print("Nenhum arquivo encontrado. Coloque os .xlsx na mesma pasta deste script")
        print("ou no seu Downloads, com os nomes originais da ANP.")
        sys.exit(1)

    resultados = []
    for caminho in arquivos:
        df = carregar_arquivo(caminho)
        anual = processar(df)
        if anual is not None:
            resultados.append(anual)

    if not resultados:
        print("\n!! Não consegui montar a série anual em nenhum arquivo.")
        print("Me cole a saída acima (colunas + head + valores únicos de produto)")
        print("que eu ajusto o script.")
        sys.exit(1)

    final = pd.concat(resultados).groupby("ano", as_index=False).agg(
        preco_medio_revenda_reais_litro=("preco_medio_revenda_reais_litro", "mean"),
        n_semanas=("n_semanas", "sum"),
    )
    final = final.sort_values("ano")

    saida = os.path.join(PASTA_ARQUIVOS, "diesel_anp_anual_1995_2024.csv")
    final.to_csv(saida, index=False)

    print(f"\n{'='*70}")
    print("RESULTADO FINAL (também salvo em):", saida)
    print(f"{'='*70}")
    print(final.to_string(index=False))
    print("\nMe devolva este CSV (ou a tabela acima) para eu continuar a análise.")


if __name__ == "__main__":
    main()
