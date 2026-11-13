# -*- coding: utf-8 -*-
"""
agregar_microdados_censo2022.py — agrega os microdados da amostra do Censo 2022
(tabela Pessoas, acesso controlado) ao nível MUNICIPAL e produz a matriz
origem-destino de trabalho.

Por que existe: a base municipal já tem `pct_trab_outro_munic_2022` e
`censo22_modal_*_pct`, vindos de agregados do SIDRA — eles dizem QUANTOS saem do
município. O microdado diz PARA ONDE vão, POR QUAL MODO, EM QUANTO TEMPO e COM
QUE RENDA, e traz o peso amostral, que permite declarar a incerteza.

⚠️ DADO DE ACESSO CONTROLADO. Os arquivos de origem são versão personalizada e
rastreável, vinculada ao termo de compromisso assinado, com desagregação até área
de ponderação. Este script produz APENAS agregados municipais — que podem ser
publicados. Os microdados e qualquer saída no nível de indivíduo ou de área de
ponderação NÃO entram no pacote de replicação. Ver LEIA-ME de
`03 - Dados/_data/Censo2022_Microdados/`.

Lê direto de dentro do .zip, uma UF por vez, em blocos — não descompacta os
~3,5 GB da tabela Pessoas. Checkpoint por UF: se o parcial existir, pula.

Variáveis usadas (ver dicionario_microdados_cd2022.csv):
  P0080 município de residência · P0111 peso amostral · P1120 categoria do local
  de trabalho (1 em casa · 2 fora de casa, mesmo município · 3 outro município ·
  4 outro país · 5 mais de um) · P1140 município do local de trabalho ·
  P1170 meio de transporte (única resposta, 15 categorias) · P1180 faixa de tempo ·
  P1190 tempo em minutos · P1110 rendimento de todas as fontes

Uso:  python agregar_microdados_censo2022.py
"""
import os
import glob
import zipfile
import pandas as pd

V = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data"
ZIP = (r"C:\Users\HOME\Downloads\07_Academico\Censo2022_Microdados"
       r"\microdados_censo_amostra_2022_csv_20260908_140041.zip")
OUT = os.path.join(V, "Censo2022_Microdados", "agregados")
os.makedirs(OUT, exist_ok=True)

FORCAR = False          # True refaz todas as UFs, mesmo com parcial no disco
BLOCO = 400_000         # linhas por bloco de leitura

COLS = ["P0080", "P0111", "P1120", "P1140", "P1170", "P1180", "P1190", "P1110"]

# agrupamento de modo (P1170) -- resposta única
MODO = {1: "ativo", 2: "ativo", 3: "moto", 4: "moto", 5: "auto", 6: "auto",
        7: "van", 8: "onibus", 9: "onibus", 10: "trilho",
        11: "outros", 12: "outros", 13: "outros", 14: "outros"}
MODOS = ["ativo", "moto", "auto", "van", "onibus", "trilho", "outros"]


def _ler_uf(z, nome):
    """Soma por município, lendo em blocos. Devolve (agregado_municipal, od)."""
    acc, od = {}, {}
    leitor = pd.read_csv(z.open(nome), sep=";", encoding="latin-1", usecols=COLS,
                         dtype=str, chunksize=BLOCO, low_memory=False)
    for ch in leitor:
        ch["w"] = pd.to_numeric(ch["P0111"], errors="coerce")
        ch = ch[ch["w"].notna() & (ch["w"] > 0)]
        for c in ("P0080", "P1120", "P1140", "P1170", "P1180"):
            ch[c] = pd.to_numeric(ch[c], errors="coerce")
        ch["min"] = pd.to_numeric(ch["P1190"], errors="coerce")
        ch["renda"] = pd.to_numeric(ch["P1110"], errors="coerce")
        # universo: quem tem categoria de local de trabalho declarada
        u = ch[ch["P1120"].isin([1, 2, 3, 4, 5])].copy()
        if u.empty:
            continue
        u["sai"] = u["P1120"] == 3
        u["modo"] = u["P1170"].map(MODO)
        for cod, g in u.groupby("P0080"):
            a = acc.setdefault(int(cod), {k: 0.0 for k in (
                "w_tot", "n_tot", "w_mesmo", "w_sai", "w_pais", "w_mult",
                "w_tempo", "wt_min", "w_tempo_sai", "wt_min_sai",
                "w_tempo_fica", "wt_min_fica", "w_mais1h", "w_tempo_faixa",
                "w_renda_sai", "wr_sai", "w_renda_fica", "wr_fica")})
            a["w_tot"] += g["w"].sum(); a["n_tot"] += len(g)
            a["w_mesmo"] += g.loc[g["P1120"].isin([1, 2]), "w"].sum()
            a["w_sai"] += g.loc[g["sai"], "w"].sum()
            a["w_pais"] += g.loc[g["P1120"] == 4, "w"].sum()
            a["w_mult"] += g.loc[g["P1120"] == 5, "w"].sum()
            for m in MODOS:
                a.setdefault(f"w_modo_{m}", 0.0)
                a.setdefault(f"w_modo_{m}_sai", 0.0)
                a.setdefault(f"w_modo_{m}_fica", 0.0)
                sel = g["modo"] == m
                a[f"w_modo_{m}"] += g.loc[sel, "w"].sum()
                a[f"w_modo_{m}_sai"] += g.loc[sel & g["sai"], "w"].sum()
                a[f"w_modo_{m}_fica"] += g.loc[sel & ~g["sai"], "w"].sum()
            a.setdefault("w_modo_tot", 0.0); a.setdefault("w_modo_tot_sai", 0.0)
            a.setdefault("w_modo_tot_fica", 0.0)
            mm = g["modo"].notna()
            a["w_modo_tot"] += g.loc[mm, "w"].sum()
            a["w_modo_tot_sai"] += g.loc[mm & g["sai"], "w"].sum()
            a["w_modo_tot_fica"] += g.loc[mm & ~g["sai"], "w"].sum()
            t = g[g["min"].notna()]
            a["w_tempo"] += t["w"].sum(); a["wt_min"] += (t["min"] * t["w"]).sum()
            ts = t[t["sai"]]; tf = t[~t["sai"]]
            a["w_tempo_sai"] += ts["w"].sum(); a["wt_min_sai"] += (ts["min"] * ts["w"]).sum()
            a["w_tempo_fica"] += tf["w"].sum(); a["wt_min_fica"] += (tf["min"] * tf["w"]).sum()
            fx = g[g["P1180"].isin([1, 2, 3, 4, 5, 6, 7])]
            a["w_tempo_faixa"] += fx["w"].sum()
            a["w_mais1h"] += fx.loc[fx["P1180"].isin([5, 6, 7]), "w"].sum()
            r = g[g["renda"].notna()]
            rs = r[r["sai"]]; rf = r[~r["sai"]]
            a["w_renda_sai"] += rs["w"].sum(); a["wr_sai"] += (rs["renda"] * rs["w"]).sum()
            a["w_renda_fica"] += rf["w"].sum(); a["wr_fica"] += (rf["renda"] * rf["w"]).sum()
        # origem-destino: só quem trabalha em outro município e tem destino
        s = u[u["sai"] & u["P1140"].notna()]
        for (o, d), g in s.groupby(["P0080", "P1140"]):
            k = (int(o), int(d))
            v = od.setdefault(k, [0.0, 0])
            v[0] += g["w"].sum(); v[1] += len(g)
    return acc, od


def _fechar(acc):
    linhas = []
    for cod, a in acc.items():
        wt = a["w_tot"]
        if wt <= 0:
            continue
        p_sai = a["w_sai"] / wt
        n = a["n_tot"]
        # CV sob amostragem aleatória simples -- É PISO, não o CV real (o desenho
        # do Censo é por conglomerados; a variância verdadeira é maior)
        cv = ((p_sai * (1 - p_sai) / n) ** 0.5 / p_sai * 100) if (n > 0 and 0 < p_sai < 1) else None
        r = {"cod_ibge": cod,
             "md22_ocup_local_trab": round(wt),
             "md22_ocup_local_trab_n": int(n),
             "md22_trab_mesmo_munic_pct": round(a["w_mesmo"] / wt * 100, 2),
             "md22_trab_outro_munic_pct": round(p_sai * 100, 2),
             "md22_trab_outro_pais_pct": round(a["w_pais"] / wt * 100, 2),
             "md22_trab_multiplos_pct": round(a["w_mult"] / wt * 100, 2),
             "md22_trab_outro_munic_cv_srs": None if cv is None else round(cv, 1)}
        def pct(num, den):
            return round(num / den * 100, 2) if den and den > 0 else None
        # divisão modal sobre quem declarou meio de transporte
        for m in MODOS:
            r[f"md22_modo_{m}_pct"] = pct(a.get(f"w_modo_{m}", 0.0), a.get("w_modo_tot", 0.0))
        # só o ônibus ganha o corte saem × ficam -- é o modo que a tese discute
        r["md22_modo_onibus_pct_saem"] = pct(a.get("w_modo_onibus_sai", 0.0), a.get("w_modo_tot_sai", 0.0))
        r["md22_modo_onibus_pct_ficam"] = pct(a.get("w_modo_onibus_fica", 0.0), a.get("w_modo_tot_fica", 0.0))
        r["md22_tempo_medio_min"] = round(a["wt_min"] / a["w_tempo"], 1) if a["w_tempo"] > 0 else None
        r["md22_tempo_medio_min_saem"] = round(a["wt_min_sai"] / a["w_tempo_sai"], 1) if a["w_tempo_sai"] > 0 else None
        r["md22_tempo_medio_min_ficam"] = round(a["wt_min_fica"] / a["w_tempo_fica"], 1) if a["w_tempo_fica"] > 0 else None
        r["md22_tempo_mais_1h_pct"] = round(a["w_mais1h"] / a["w_tempo_faixa"] * 100, 2) if a["w_tempo_faixa"] > 0 else None
        r["md22_renda_media_saem"] = round(a["wr_sai"] / a["w_renda_sai"], 2) if a["w_renda_sai"] > 0 else None
        r["md22_renda_media_ficam"] = round(a["wr_fica"] / a["w_renda_fica"], 2) if a["w_renda_fica"] > 0 else None
        linhas.append(r)
    return pd.DataFrame(linhas)


def main():
    z = zipfile.ZipFile(ZIP)
    pessoas = sorted(n for n in z.namelist() if "/Pessoas_" in n and n.endswith(".csv"))
    print(f"{len(pessoas)} arquivos de Pessoas no zip")
    for nome in pessoas:
        uf = nome.split("/")[0]
        alvo = os.path.join(OUT, f"_parcial_md22_{uf}.csv")
        alvo_od = os.path.join(OUT, f"_parcial_od_{uf}.csv")
        if os.path.exists(alvo) and os.path.exists(alvo_od) and not FORCAR:
            print(f"  UF {uf}: parcial no disco -- pulando")
            continue
        print(f"  UF {uf}: lendo {nome} ...", flush=True)
        acc, od = _ler_uf(z, nome)
        _fechar(acc).to_csv(alvo, index=False)
        pd.DataFrame([{"cod_origem": o, "cod_destino": d, "pessoas_peso": round(v[0]), "n_amostra": v[1]}
                      for (o, d), v in od.items()]).to_csv(alvo_od, index=False)
        print(f"    {len(acc)} municipios, {len(od)} pares origem-destino")

    ag = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(OUT, "_parcial_md22_*.csv")))],
                   ignore_index=True)
    ag.to_csv(os.path.join(OUT, "md22_agregado_municipal.csv"), index=False)
    od = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(OUT, "_parcial_od_*.csv")))],
                   ignore_index=True).sort_values("pessoas_peso", ascending=False)
    od.to_csv(os.path.join(OUT, "md22_origem_destino_trabalho.csv"), index=False)
    print(f"\nagregado municipal: {len(ag)} municipios")
    print(f"matriz origem-destino: {len(od)} pares")
    print(f"\nsaidas em: {OUT}")
    print("PROXIMO PASSO: mesclar na base_municipal_v3.csv (eu faco daqui, com backup e conferencia).")


if __name__ == "__main__":
    main()
