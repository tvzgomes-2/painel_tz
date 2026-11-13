#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""filtrar_empresas_6cnaes.py — testa a hipótese "operador pequeno" para a
discrepância CNAE núcleo × MUNIC (56,5% dos municípios com CNPJ núcleo
declaram, na MUNIC 2020, NÃO ter ônibus intramunicipal — ver `pesquisa dos
CNPJs.md`, Passo 10).

O teste por Nº DE SÓCIOS (24/07/2026) deu sinal fraco: média 1,00 sócio nos
municípios discrepantes vs. 1,25 nos que batem com a MUNIC — diferença
pequena, não conclusiva sozinha.

Este script traz um teste mais direto, a partir da tabela `empresas`
(natureza jurídica, porte, capital social) — em especial a natureza
jurídica **2135 = Empresário (Individual)**, que é o proxy mais limpo de
"operador individual/pequeno" que a Receita distribui (mais direto que
contar sócios, já que Empresário Individual não tem sócio por definição).

LAYOUT confirmado por inspeção direta (`empresas0.csv`, 24/07/2026) — 7
colunas, sem cabeçalho, ';'-separado, aspas, latin-1:
  0 cnpj_basico | 1 razao_social | 2 natureza_juridica | 3 qualificacao_responsavel
  4 capital_social (formato brasileiro, ex. "3000,00") | 5 porte_empresa
  6 ente_federativo_responsavel (só para órgãos públicos, quase sempre vazio)

USO:
    python "C:\Users\HOME\OneDrive\doutorado\_meta\scripts\filtrar_empresas_6cnaes.py"

Depende de `cnpj_base_ativos_6cnaes.csv` (Passo 2) já existir. Resumível
por parte, mesmo padrão dos scripts anteriores desta rodada."""
import csv
import glob
import os

RAIZ = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\CNPJ"
PASTA_BRUTOS = os.path.join(RAIZ, "Receita Federal - dados brutos")
PASTA_SAIDA = os.path.join(RAIZ, "filtrados (6 CNAEs transporte, 24-07-2026)")
ARQUIVO_CNPJ_BASE = os.path.join(PASTA_SAIDA, "cnpj_base_ativos_6cnaes.csv")
PASTA_PARCIAL = os.path.join(PASTA_SAIDA, "parcial_empresas")
ARQUIVO_FINAL = os.path.join(PASTA_SAIDA, "empresas_filtrado_6cnaes.csv")

COLUNAS_SAIDA = [
    "cnpj_basico", "razao_social", "natureza_juridica", "capital_social",
    "porte_empresa", "camada",
]


def log(msg):
    print(msg, flush=True)


def carrega_cnpj_base(caminho):
    mapa = {}
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            mapa[row["cnpj_basico"]] = row["camada"]
    return mapa


def processa_parte(caminho_entrada, caminho_saida, cnpj_camada):
    total_lidas = 0
    total_match = 0
    with open(caminho_entrada, "r", encoding="latin1", errors="replace", newline="") as fin, \
         open(caminho_saida, "w", encoding="utf-8-sig", newline="") as fout:
        leitor = csv.reader(fin, delimiter=";", quotechar='"')
        escritor = csv.writer(fout)
        escritor.writerow(COLUNAS_SAIDA)
        for campos in leitor:
            total_lidas += 1
            if len(campos) < 6:
                continue
            cb = campos[0].strip()
            camada = cnpj_camada.get(cb)
            if camada is None:
                continue
            total_match += 1
            escritor.writerow([cb, campos[1], campos[2], campos[4], campos[5], camada])
            if total_lidas % 2_000_000 == 0:
                log(f"    ... {total_lidas:,} linhas lidas, {total_match:,} casaram até agora")
    return total_lidas, total_match


def main():
    if not os.path.exists(ARQUIVO_CNPJ_BASE):
        raise SystemExit(f"Não achei {ARQUIVO_CNPJ_BASE} — rode antes o filtrar_ativos_6cnaes.py (Passo 2).")

    log("Carregando CNPJs BASE ativos (Passo 2)...")
    cnpj_camada = carrega_cnpj_base(ARQUIVO_CNPJ_BASE)
    log(f"  {len(cnpj_camada):,} CNPJs BASE carregados.")

    os.makedirs(PASTA_PARCIAL, exist_ok=True)
    partes = sorted(glob.glob(os.path.join(PASTA_BRUTOS, "empresas*.csv")))
    if not partes:
        raise SystemExit(f"Nenhum arquivo empresas*.csv encontrado em {PASTA_BRUTOS}")
    log(f"{len(partes)} partes de empresas encontradas.")

    for caminho_entrada in partes:
        nome = os.path.basename(caminho_entrada)
        caminho_saida = os.path.join(PASTA_PARCIAL, nome)
        if os.path.exists(caminho_saida):
            log(f"\n{nome}: já processada — pulando.")
            continue
        log(f"\n{nome}: processando...")
        caminho_tmp = caminho_saida + ".tmp"
        total_lidas, total_match = processa_parte(caminho_entrada, caminho_tmp, cnpj_camada)
        os.replace(caminho_tmp, caminho_saida)
        log(f"  {total_lidas:,} linhas lidas, {total_match:,} empresas casaram")

    log(f"\n{'='*70}\nConcatenando parciais em {ARQUIVO_FINAL}")
    parciais = sorted(glob.glob(os.path.join(PASTA_PARCIAL, "empresas*.csv")))
    if len(parciais) < len(partes):
        log(f"  ⚠️ só {len(parciais)}/{len(partes)} partes prontas — rode de novo para completar.")

    caminho_tmp_final = ARQUIVO_FINAL + ".tmp"
    total_final = 0
    natureza_count = {}
    porte_count = {}
    with open(caminho_tmp_final, "w", encoding="utf-8-sig", newline="") as fout:
        escritor = csv.writer(fout)
        escritor.writerow(COLUNAS_SAIDA)
        for caminho_parcial in parciais:
            with open(caminho_parcial, "r", encoding="utf-8-sig", newline="") as fin:
                leitor = csv.reader(fin)
                next(leitor)
                for linha in leitor:
                    escritor.writerow(linha)
                    total_final += 1
                    natureza_count[linha[2]] = natureza_count.get(linha[2], 0) + 1
                    porte_count[linha[4]] = porte_count.get(linha[4], 0) + 1
    os.replace(caminho_tmp_final, ARQUIVO_FINAL)

    log(f"\nConsolidado final: {total_final:,} empresas.")
    log(f"Natureza jurídica mais comuns: {sorted(natureza_count.items(), key=lambda x: -x[1])[:10]}")
    log(f"  (2135 = Empresário Individual — proxy de operador pequeno/individual)")
    log(f"Porte empresa: {porte_count}")
    log(f"\nArquivo: {ARQUIVO_FINAL}")
    log(
        "\nPróximo passo: cole aqui a saída — cruzo natureza_juridica/porte/capital_social "
        "com os municípios 'Caso A' (discrepantes da MUNIC) vs. os que batem, pra testar "
        "se a discrepância é mesmo explicada por operador individual/pequeno porte."
    )


if __name__ == "__main__":
    main()
