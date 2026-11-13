"""
Gera as Figuras 2, 3, 4 da nota "Análise - Cruzamento espacial GE x Tarifa Zero.md"
(taxa de TZ por escore de confiança do núcleo, por categoria de cluster, e por
recorte de porte). Segue a paleta de [[Identidade Visual da Pesquisa]] (preto
#0E0E10 + acentos azul/rosa, tipografia Poppins, fundo papel #FAF9F5, sem
gradiente/ícone). Salva SVGs em `_attachments/`.

Rodar a partir da raiz do cofre: python3 _meta/scripts/analise_espacial_ge_tz_graficos.py
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

BASE = "."  # rodar a partir da raiz do cofre
ATT = f"{BASE}/_attachments"

PRETO = "#0E0E10"
ROSA = "#FF2D6B"
AZUL = "#1A54C7"
PAPEL = "#FAF9F5"

plt.rcParams["font.family"] = "Poppins"
plt.rcParams["figure.facecolor"] = PAPEL
plt.rcParams["axes.facecolor"] = PAPEL
plt.rcParams["savefig.facecolor"] = PAPEL
plt.rcParams["text.color"] = PRETO
plt.rcParams["axes.edgecolor"] = PRETO
plt.rcParams["axes.labelcolor"] = PRETO
plt.rcParams["xtick.color"] = PRETO
plt.rcParams["ytick.color"] = PRETO
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False


def preparar_dados():
    df = pd.read_csv(f"{BASE}/03 - Dados/_data/Base Municipal v3/base_municipal_v3.csv", low_memory=False)
    df["cod_ibge"] = df["cod_ibge"].astype(int)

    tz = pd.read_excel(f"{BASE}/03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx", sheet_name="consolidado")
    tz["Código IBGE"] = pd.to_numeric(tz["Código IBGE"], errors="coerce")
    ativos_ibge = set(tz.loc[tz["Situação"] == "Ativa", "Código IBGE"].dropna().astype(int))
    df["tz_universal"] = df["cod_ibge"].isin(ativos_ibge).astype(int)
    df["ge_score"] = df["cnpj_nucleo_escore_confianca_prelim"].fillna(0)

    espac = pd.read_csv(f"{BASE}/03 - Dados/_data/CNPJ/filtrados (6 CNAEs transporte, 24-07-2026)/espacializacao_grupos_por_municipio.csv")
    GRANDES = ["Barata", "Lessa Carvalho", "1001", "Belarmino", "Corleto"]
    PEQUENOS = ["Baltazar", "Pekin/Constantino", "Nova Suissa", "Andorinha", "Gammbus", "Ruas"]
    muni_grande = set(espac[espac["grupo"].isin(GRANDES)]["cod_ibge"].unique())
    muni_pequeno = set(espac[espac["grupo"].isin(PEQUENOS)]["cod_ibge"].unique())
    df["categoria_cluster"] = "Nenhum grupo"
    df.loc[df["cod_ibge"].isin(muni_pequeno), "categoria_cluster"] = "Cluster pequeno/regional"
    df.loc[df["cod_ibge"].isin(muni_grande), "categoria_cluster"] = "Grande cluster nacional"
    return df


def fig_escore(df):
    tab1 = df.groupby("ge_score")["tz_universal"].agg(["mean", "count"]).reset_index()
    fig, ax = plt.subplots(figsize=(7, 4.2))
    bars = ax.bar(tab1["ge_score"].astype(str), tab1["mean"] * 100, color=AZUL, width=0.6)
    ax.set_xlabel("Escore de confiança do núcleo CNAE de transporte (0 = nenhum operador formal)")
    ax.set_ylabel("% de municípios com Tarifa Zero universal")
    ax.set_title("Taxa de TZ cresce com a presença de operador formal\n(não é teste de concentração em grupo — ver §2 da nota)",
                  fontsize=10, fontweight="bold", loc="left")
    for b, n in zip(bars, tab1["count"]):
        ax.annotate(f"n={n}", (b.get_x() + b.get_width() / 2, b.get_height() + 0.15), ha="center", fontsize=8, color=PRETO)
    media = df["tz_universal"].mean() * 100
    ax.axhline(media, color=PRETO, linestyle="--", linewidth=1)
    ax.annotate("média nacional", (0, media + 0.3), fontsize=8, color=PRETO)
    fig.tight_layout()
    fig.savefig(f"{ATT}/Fig - Taxa TZ por escore de confianca do nucleo (ago-2026).svg", format="svg")
    plt.close(fig)


def fig_categoria(df):
    ordem = ["Nenhum grupo", "Cluster pequeno/regional", "Grande cluster nacional"]
    tab2 = df.groupby("categoria_cluster")["tz_universal"].agg(["mean", "count"]).reindex(ordem).reset_index()
    cores2 = [PRETO, ROSA, AZUL]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(tab2["categoria_cluster"], tab2["mean"] * 100, color=cores2, width=0.55)
    ax.set_ylabel("% de municípios com Tarifa Zero universal")
    ax.set_title("Grandes clusters aparecem MAIS, não menos, em municípios com TZ", fontsize=11, fontweight="bold", loc="left")
    for b, n, m in zip(bars, tab2["count"], tab2["mean"]):
        ax.annotate(f"{m * 100:.1f}%\n(n={n})", (b.get_x() + b.get_width() / 2, b.get_height() + 0.15),
                     ha="center", fontsize=9, color=PRETO, fontweight="medium")
    media = df["tz_universal"].mean() * 100
    ax.axhline(media, color=PRETO, linestyle="--", linewidth=1, alpha=0.5)
    ax.annotate(f"média nacional ({media:.1f}%)", (1.5, media + 0.35), fontsize=8, color=PRETO, ha="center")
    plt.xticks(fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{ATT}/Fig - Taxa TZ por categoria de cluster GE (ago-2026).svg", format="svg")
    plt.close(fig)


def fig_porte(df):
    threshs = [0, 30000, 50000, 100000]
    labels = ["Nacional\n(todos)", "30 mil+\nhab.", "50 mil+\nhab.", "100 mil+\nhab."]
    com, sem = [], []
    for t in threshs:
        sub = df[df["pop_2022"] >= t]
        com.append(sub[sub["categoria_cluster"] == "Grande cluster nacional"]["tz_universal"].mean() * 100)
        sem.append(sub[sub["categoria_cluster"] != "Grande cluster nacional"]["tz_universal"].mean() * 100)
    x = np.arange(len(labels))
    w = 0.35
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.bar(x - w / 2, sem, w, label="Sem grande cluster", color=PRETO)
    ax.bar(x + w / 2, com, w, label="Com grande cluster", color=AZUL)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("% de municípios com Tarifa Zero universal")
    ax.set_title("O padrão se mantém (e cresce) em cidades maiores", fontsize=11, fontweight="bold", loc="left")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    for i, (c, s) in enumerate(zip(com, sem)):
        ax.annotate(f"{c:.1f}%", (i + w / 2, c + 0.15), ha="center", fontsize=8)
        ax.annotate(f"{s:.1f}%", (i - w / 2, s + 0.15), ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{ATT}/Fig - Taxa TZ grande cluster por recorte de porte (ago-2026).svg", format="svg")
    plt.close(fig)


if __name__ == "__main__":
    df = preparar_dados()
    fig_escore(df)
    fig_categoria(df)
    fig_porte(df)
    print("Figuras 2, 3 e 4 regeneradas em _attachments/.")
