#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""georreferenciar_e_cruzar_munic.py — Passos 3 e 10 do pipeline de CNPJs,
feitos juntos a pedido do autor (24/07/2026): georreferenciar os
estabelecimentos das 6 CNAEs (Passo 3) e cruzar com a MUNIC/IBGE (Passo 10)
para checar CONSISTÊNCIA da base — os municípios que aparecem no recorte de
CNPJs batem com os que a MUNIC diz ter sistema de ônibus municipal?

PONTE RFB → IBGE (achado de 24/07/2026, resolve pendência do Passo 3): o
campo `municipio` do arquivo bruto de estabelecimentos NÃO é o código IBGE
— é um código interno da Receita Federal. O `municipios.csv` já solto em
`_data/CNPJ/Receita Federal - dados brutos/` tem a ponte certa, só que pela
coluna **`siafi_id`** (não `codigo_ibge` diretamente) — validado batendo 5
casos manualmente (UF + nome do município conferem) e confirmando que
`siafi_id` é único nos 5.570 municípios (sem ambiguidade).

O QUE ESTE SCRIPT FAZ:
  1. Carrega `estabelecimentos_ativos_6cnaes.csv` (saída do Passo 2).
  2. Bridge `municipio_codigo_rfb` → `codigo_ibge` via `siafi_id`.
  3. Agrega por município: nº de estabelecimentos ativos (núcleo, expansão).
  4. Cruza com `base_municipal_v3.csv` — campos MUNIC 2020 relacionados a
     sistema de ônibus (`munic_onibus_intramun_2020`, `munic_concessao_2020`,
     `munic_permissao_2020`, `munic_autorizacao_2020`,
     `munic_prestacao_direta_2020`, `munic_nao_regulamentado_2020`,
     `munic_orgao_gestor_2020`) — para achar INCONSISTÊNCIAS:
       (a) município com estabelecimento núcleo (CNAE urbano) mas MUNIC
           declara NÃO ter ônibus intramunicipal;
       (b) município que a MUNIC diz ter ônibus, mas nenhum estabelecimento
           núcleo aparece na base de CNPJs (pode ser operado por empresa
           sediada em outro município — mesma ressalva já registrada para
           `vinculos_cnae_transporte_*` no banco municipal).

NÃO CONCLUI sozinho se é erro de base ou fenômeno real (empresa de fora
operando linha local) — só lista os casos para checagem manual/qualitativa.

USO:
    python "C:\Users\HOME\OneDrive\doutorado\_meta\scripts\georreferenciar_e_cruzar_munic.py"
"""
import csv
import os

RAIZ_CNPJ = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\CNPJ"
PASTA_FILTRADOS = os.path.join(RAIZ_CNPJ, "filtrados (6 CNAEs transporte, 24-07-2026)")
ARQUIVO_ESTAB_ATIVOS = os.path.join(PASTA_FILTRADOS, "estabelecimentos_ativos_6cnaes.csv")
ARQUIVO_MUNICIPIOS_RFB = os.path.join(RAIZ_CNPJ, "Receita Federal - dados brutos", "municipios.csv")
BASE_MUNICIPAL_V3 = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\Base Municipal v3\base_municipal_v3.csv"

ARQUIVO_SAIDA_MUNICIPIO = os.path.join(PASTA_FILTRADOS, "estabelecimentos_por_municipio_6cnaes.csv")
ARQUIVO_SAIDA_INCONSISTENCIAS = os.path.join(PASTA_FILTRADOS, "inconsistencias_cnpj_x_munic.csv")

CAMPOS_MUNIC = [
    "munic_onibus_intramun_2020", "munic_orgao_gestor_2020",
    "munic_concessao_2020", "munic_permissao_2020", "munic_autorizacao_2020",
    "munic_prestacao_direta_2020", "munic_nao_regulamentado_2020",
]


def log(msg):
    print(msg, flush=True)


def c7(x):
    try:
        return str(int(float(x))).zfill(7)
    except Exception:
        return None


def carrega_ponte_municipios():
    """siafi_id -> codigo_ibge (7 dígitos), nome, uf."""
    ponte = {}
    with open(ARQUIVO_MUNICIPIOS_RFB, encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            ponte[row["siafi_id"]] = {
                "codigo_ibge": c7(row["codigo_ibge"]),
                "nome": row["nome"],
                "codigo_uf": row["codigo_uf"],
            }
    return ponte


def main():
    import pandas as pd

    log("Carregando ponte de municípios (siafi_id -> IBGE)...")
    ponte = carrega_ponte_municipios()
    log(f"  {len(ponte):,} municípios na ponte.")

    log("Carregando estabelecimentos ativos (Passo 2)...")
    agregados = {}  # codigo_ibge -> {"nucleo": n, "expansao": n, "ambos_estab": n}
    sem_ponte = 0
    total = 0
    with open(ARQUIVO_ESTAB_ATIVOS, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            total += 1
            info = ponte.get(row["municipio_codigo_rfb"])
            if info is None or info["codigo_ibge"] is None:
                sem_ponte += 1
                continue
            cod = info["codigo_ibge"]
            ag = agregados.setdefault(cod, {"nucleo": 0, "expansao": 0})
            ag[row["camada"]] = ag.get(row["camada"], 0) + 1
    log(f"  {total:,} estabelecimentos lidos, {sem_ponte:,} sem correspondência na ponte ({sem_ponte/total*100:.2f}%).")
    log(f"  {len(agregados):,} municípios distintos com ao menos 1 estabelecimento ativo (6 CNAEs).")

    # salva agregado por município
    tmp = ARQUIVO_SAIDA_MUNICIPIO + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as fout:
        w = csv.writer(fout)
        w.writerow(["cod_ibge", "n_estab_ativos_nucleo", "n_estab_ativos_expansao"])
        for cod, ag in sorted(agregados.items()):
            w.writerow([cod, ag.get("nucleo", 0), ag.get("expansao", 0)])
    os.replace(tmp, ARQUIVO_SAIDA_MUNICIPIO)
    log(f"  salvo {ARQUIVO_SAIDA_MUNICIPIO}")

    # cruza com MUNIC
    log("\nCruzando com base_municipal_v3.csv (campos MUNIC 2020)...")
    base = pd.read_csv(BASE_MUNICIPAL_V3, dtype={"cod_ibge": str}, low_memory=False)
    base["cod_ibge"] = base["cod_ibge"].map(c7)

    campos_disponiveis = [c for c in CAMPOS_MUNIC if c in base.columns]
    log(f"  campos MUNIC encontrados no banco: {campos_disponiveis}")

    munic_onibus = base.set_index("cod_ibge")["munic_onibus_intramun_2020"].to_dict() if "munic_onibus_intramun_2020" in base.columns else {}
    nome_uf = base.set_index("cod_ibge")[["nome_mun", "uf"]].to_dict("index") if "nome_mun" in base.columns else {}

    todos_municipios_ibge = set(base["cod_ibge"].dropna())
    municipios_com_nucleo = {cod for cod, ag in agregados.items() if ag.get("nucleo", 0) > 0}

    caso_a = []  # tem nucleo, MUNIC diz que nao tem onibus
    caso_b = []  # MUNIC diz que tem onibus, sem estabelecimento nucleo
    for cod in todos_municipios_ibge:
        declara_onibus = munic_onibus.get(cod)
        tem_nucleo = cod in municipios_com_nucleo
        if tem_nucleo and declara_onibus == 0:
            caso_a.append(cod)
        if declara_onibus == 1 and not tem_nucleo:
            caso_b.append(cod)

    log(f"\n  Caso A — tem estabelecimento núcleo (CNAE urbano) mas MUNIC diz NÃO ter ônibus intramunicipal: {len(caso_a):,}")
    log(f"  Caso B — MUNIC diz ter ônibus intramunicipal mas NENHUM estabelecimento núcleo na base de CNPJs: {len(caso_b):,}")
    log(f"  (referência: {len(municipios_com_nucleo):,} municípios com estabelecimento núcleo no total; "
        f"{sum(1 for v in munic_onibus.values() if v == 1):,} municípios declaram ônibus intramunicipal na MUNIC 2020)")

    tmp2 = ARQUIVO_SAIDA_INCONSISTENCIAS + ".tmp"
    with open(tmp2, "w", encoding="utf-8-sig", newline="") as fout:
        w = csv.writer(fout)
        w.writerow(["cod_ibge", "nome_mun", "uf", "caso", "n_estab_ativos_nucleo", "munic_onibus_intramun_2020"])
        for cod in caso_a:
            nu = nome_uf.get(cod, {})
            w.writerow([cod, nu.get("nome_mun"), nu.get("uf"), "A_tem_cnpj_sem_declaracao_munic",
                        agregados.get(cod, {}).get("nucleo", 0), munic_onibus.get(cod)])
        for cod in caso_b:
            nu = nome_uf.get(cod, {})
            w.writerow([cod, nu.get("nome_mun"), nu.get("uf"), "B_declara_munic_sem_cnpj",
                        agregados.get(cod, {}).get("nucleo", 0), munic_onibus.get(cod)])
    os.replace(tmp2, ARQUIVO_SAIDA_INCONSISTENCIAS)
    log(f"\n  salvo {ARQUIVO_SAIDA_INCONSISTENCIAS}")


if __name__ == "__main__":
    main()
