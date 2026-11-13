# -*- coding: utf-8 -*-
"""
agregar_modo_perfil_censo2022.py — meio de transporte para o trabalho por perfil
(renda do trabalho em salários mínimos, cor ou raça, sexo), a partir dos microdados
da amostra do Censo 2022 (tabela Pessoas, acesso controlado).

Criado em 02/10/2026 para a Análise I do Cap. 2 (r18): "quem usa o automóvel e a
motocicleta". Produz APENAS agregados por município × modo × faixa de renda × cor ×
sexo (somas de peso e contagem de registros) — publicáveis. Os microdados não saem
do zip. Ver LEIA-ME de 03 - Dados/_data/Censo2022_Microdados/.

Variáveis: P0080 município · P0111 peso · P0160 sexo · P0210 cor ou raça ·
P1080 rendimento bruto mensal habitual de todos os trabalhos · P1170 meio de
transporte para o trabalho (resposta única; universo: quem tem P1170 declarado).
Salário mínimo de referência: R$ 1.212 (2022).
Uso: python3 agregar_modo_perfil_censo2022.py [UF ...]   (checkpoint por UF)
"""
import os, sys, zipfile
import pandas as pd
import numpy as np
HOME = os.path.expanduser("~")
ZIP = os.path.join(HOME, "mnt/Downloads/07_Academico/Censo2022_Microdados/microdados_censo_amostra_2022_csv_20260908_140041.zip")
if not os.path.exists(ZIP):
    ZIP = r"C:\Users\HOME\Downloads\07_Academico\Censo2022_Microdados\microdados_censo_amostra_2022_csv_20260908_140041.zip"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "03 - Dados", "_data", "Censo2022_Microdados", "agregados", "modo_perfil")
os.makedirs(OUT, exist_ok=True)
SM = 1212.0
COLS = ["P0080", "P0111", "P0160", "P0210", "P1080", "P1170"]
BINS = [-np.inf, 0, 0.5, 1, 2, 3, 5, 10, np.inf]
LAB = ["sem", "ate_0.5", "0.5_1", "1_2", "2_3", "3_5", "5_10", "mais_10"]

def uf(z, nome, dest):
    acc = []
    import pyarrow as pa, pyarrow.csv as pc
    rd = pc.open_csv(z.open(nome), read_options=pc.ReadOptions(block_size=1 << 26, encoding="latin-1"),
                     parse_options=pc.ParseOptions(delimiter=";"),
                     convert_options=pc.ConvertOptions(include_columns=COLS, column_types={c: pa.string() for c in COLS}))
    for b in rd:
        ch = b.to_pandas()
        w = pd.to_numeric(ch["P0111"], errors="coerce")
        m = pd.to_numeric(ch["P1170"], errors="coerce")
        k = w.notna() & (w > 0) & m.notna() & (m > 0)
        ch = ch[k]
        r = pd.to_numeric(ch["P1080"], errors="coerce").fillna(0) / SM
        d = pd.DataFrame({"cod": pd.to_numeric(ch["P0080"], errors="coerce").astype("Int64"),
                          "modo": m[k].astype(int), "renda": pd.cut(r, BINS, labels=LAB).astype(str),
                          "cor": pd.to_numeric(ch["P0210"], errors="coerce").fillna(9).astype(int),
                          "sexo": pd.to_numeric(ch["P0160"], errors="coerce").fillna(9).astype(int),
                          "w": w[k], "n": 1})
        acc.append(d.groupby(["cod", "modo", "renda", "cor", "sexo"], observed=True)[["w", "n"]].sum())
    pd.concat(acc).groupby(level=[0, 1, 2, 3, 4]).sum().reset_index().to_csv(dest, index=False)

z = zipfile.ZipFile(ZIP)
nomes = sorted(n for n in z.namelist() if "/Pessoas_" in n)
alvo = sys.argv[1:]
for nome in nomes:
    u = nome.split("/")[0]
    if alvo and u not in alvo: continue
    dest = os.path.join(OUT, f"modo_perfil_{u}.csv")
    if os.path.exists(dest): continue
    uf(z, nome, dest); print("ok", u, flush=True)
