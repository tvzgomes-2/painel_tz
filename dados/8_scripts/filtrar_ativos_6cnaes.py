#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""filtrar_ativos_6cnaes.py — Passo 2 do pipeline de CNPJs, refeito sobre o
universo expandido de 6 CNAEs (ver `filtrar_estabelecimentos_cnae_transporte.py`,
Passo 1, e a nota "Atualização metodológica" em `pesquisa dos CNPJs.md`).

Filtra `estabelecimentos_filtrado_6cnaes.csv` (saída do Passo 1) por
situação cadastral = ATIVA ("02") e produz duas saídas:

  1. `estabelecimentos_ativos_6cnaes.csv` — mesmas colunas do Passo 1, só
     as linhas ativas (nível estabelecimento, mantém filiais separadas).
  2. `cnpj_base_ativos_6cnaes.csv` — nível CNPJ BÁSICO (raiz de 8 dígitos),
     1 linha por empresa, com a(s) camada(s) em que aparece (nucleo,
     expansao, ou ambos) e o nº de estabelecimentos ativos.

VALIDAÇÃO JÁ FEITA (24/07/2026): restringindo ao núcleo + CNAE principal +
ativos, o resultado bate EXATAMENTE com os números históricos do Passo 1-2
documentados em `pesquisa dos CNPJs.md` (14.988 estabelecimentos / 12.907
CNPJs BASE) — confirma que o pipeline original usava só núcleo+principal+
ativos, sem CNAE secundária. Este script mantém TODAS as linhas (núcleo e
expansão, principal e secundária) intactas nas colunas de saída, para não
decidir por você o que descartar — a análise seguinte (sócios, Passo 5-7)
decide qual subconjunto usar.

⚠️ ACHADO A CONSIDERAR (ver conversa 24/07/2026): a camada de expansão tem
quase 500 mil CNPJs, dos quais só 933 também aparecem no núcleo — ou seja,
ao nível de CNPJ, a expansão NÃO é majoritariamente "os mesmos grupos que
diversificam". Não filtrar/descartar a expansão aqui, mas não tratá-la como
população automaticamente relevante para os Passos 5-6 sem cruzar antes
com os sócios já mapeados (Passo 7).

USO:
    python "C:\Users\HOME\OneDrive\doutorado\_meta\scripts\filtrar_ativos_6cnaes.py"
"""
import csv
import os

RAIZ = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\CNPJ"
PASTA = os.path.join(RAIZ, "filtrados (6 CNAEs transporte, 24-07-2026)")
ARQUIVO_ENTRADA = os.path.join(PASTA, "estabelecimentos_filtrado_6cnaes.csv")
ARQUIVO_SAIDA_ESTAB = os.path.join(PASTA, "estabelecimentos_ativos_6cnaes.csv")
ARQUIVO_SAIDA_CNPJ = os.path.join(PASTA, "cnpj_base_ativos_6cnaes.csv")

SITUACAO_ATIVA = "02"


def log(msg):
    print(msg, flush=True)


def main():
    if not os.path.exists(ARQUIVO_ENTRADA):
        raise SystemExit(f"Não achei {ARQUIVO_ENTRADA} — rode antes o filtrar_estabelecimentos_cnae_transporte.py")

    cnpj_info = {}  # cnpj_basico -> {"camadas": set, "n_estab": int, "ufs": set}
    total_lidas = 0
    total_ativas = 0

    tmp_estab = ARQUIVO_SAIDA_ESTAB + ".tmp"
    with open(ARQUIVO_ENTRADA, "r", encoding="utf-8-sig", newline="") as fin, \
         open(tmp_estab, "w", encoding="utf-8-sig", newline="") as fout:
        leitor = csv.DictReader(fin)
        escritor = csv.DictWriter(fout, fieldnames=leitor.fieldnames)
        escritor.writeheader()
        for row in leitor:
            total_lidas += 1
            if row["situacao_cadastral"] != SITUACAO_ATIVA:
                continue
            total_ativas += 1
            escritor.writerow(row)

            cb = row["cnpj_basico"]
            info = cnpj_info.setdefault(cb, {"camadas": set(), "n_estab": 0, "ufs": set()})
            info["camadas"].add(row["camada"])
            info["n_estab"] += 1
            info["ufs"].add(row["uf"])
    os.replace(tmp_estab, ARQUIVO_SAIDA_ESTAB)

    tmp_cnpj = ARQUIVO_SAIDA_CNPJ + ".tmp"
    with open(tmp_cnpj, "w", encoding="utf-8-sig", newline="") as fout:
        escritor = csv.writer(fout)
        escritor.writerow(["cnpj_basico", "camada", "n_estabelecimentos_ativos", "ufs"])
        for cb, info in sorted(cnpj_info.items()):
            camada = "ambos" if len(info["camadas"]) > 1 else next(iter(info["camadas"]))
            escritor.writerow([cb, camada, info["n_estab"], "|".join(sorted(info["ufs"]))])
    os.replace(tmp_cnpj, ARQUIVO_SAIDA_CNPJ)

    # resumo
    por_camada = {}
    for info in cnpj_info.values():
        camada = "ambos" if len(info["camadas"]) > 1 else next(iter(info["camadas"]))
        por_camada[camada] = por_camada.get(camada, 0) + 1

    log(f"Lidas: {total_lidas:,} estabelecimentos (6 CNAEs, qualquer situação)")
    log(f"Ativos: {total_ativas:,} estabelecimentos")
    log(f"CNPJs BASE ativos distintos: {len(cnpj_info):,}")
    log(f"  por camada: {por_camada}")
    log(f"\nArquivos gerados:")
    log(f"  {ARQUIVO_SAIDA_ESTAB}")
    log(f"  {ARQUIVO_SAIDA_CNPJ}")


if __name__ == "__main__":
    main()
