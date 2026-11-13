#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""filtrar_socios_6cnaes.py — Passo 5 do pipeline de CNPJs, refeito sobre o
universo expandido de 6 CNAEs (depende do Passo 2 já concluído: ver
`cnpj_base_ativos_6cnaes.csv`, gerado por `filtrar_ativos_6cnaes.py`).

Varre as 10 partes brutas de SOCIO (`SOCIO0.csv`...`SOCIO9.csv`, ~2,6 GB no
total) e mantém só as linhas cujo `cnpj_basico` está entre os 269.206 CNPJs
BASE ativos já identificados nas 6 CNAEs — produzindo a "Tabela de Sócios 2"
(equivalente expandida da Tabela de Sócios 1 original: 23.842 vínculos /
1.012 PJ (535 holdings) / 12.556 PF, que só cobria o núcleo de 2 CNAEs).

Cada vínculo sai marcado com a CAMADA do CNPJ a que pertence (nucleo,
expansao ou ambos — herdada de `cnpj_base_ativos_6cnaes.csv`), preservando
a distinção para a análise seguinte (não decide por você se deve juntar ou
não as duas camadas).

⚠️ Isto NÃO é ainda o Passo 7 (PJs dentro de PJs / segunda camada via
sócios já centrais) — é só a extração 1:1 dos sócios ligados aos CNPJs já
filtrados por CNAE. O Passo 7 vem depois, usando a saída deste script.

LAYOUT confirmado por inspeção direta (`SOCIO0.csv`, 24/07/2026) — 11
colunas, sem cabeçalho, ';'-separado, aspas, latin-1:
  0 cnpj_basico | 1 identificador_de_socio (1=PJ, 2=PF, 3=estrangeiro)
  2 nome_socio_ou_razao_social | 3 cnpj_cpf_socio (CPF mascarado
    "***XXXXXX**" para PF; CNPJ completo p/ PJ) | 4 qualificacao_socio
  5 data_entrada_sociedade | 6 pais | 7 representante_legal (CPF mascarado)
  8 nome_representante | 9 qualificacao_representante_legal | 10 faixa_etaria

REQUISITOS: só biblioteca padrão (csv, os, glob).

USO:
    python "C:\Users\HOME\OneDrive\doutorado\_meta\scripts\filtrar_socios_6cnaes.py"

RESUMÍVEL por parte, mesmo padrão dos scripts anteriores desta rodada —
cada `SOCIO<n>.csv` processado vira uma parcial; se a parcial já existe,
a parte é pulada. Concatenação final sempre relida do disco."""
import csv
import glob
import os

RAIZ = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\CNPJ"
PASTA_BRUTOS = os.path.join(RAIZ, "Receita Federal - dados brutos")
PASTA_SAIDA = os.path.join(RAIZ, "filtrados (6 CNAEs transporte, 24-07-2026)")
ARQUIVO_CNPJ_BASE = os.path.join(PASTA_SAIDA, "cnpj_base_ativos_6cnaes.csv")
PASTA_PARCIAL = os.path.join(PASTA_SAIDA, "parcial_socios")
ARQUIVO_FINAL = os.path.join(PASTA_SAIDA, "socios_filtrado_6cnaes.csv")

TIPO_SOCIO = {"1": "PJ", "2": "PF", "3": "estrangeiro"}

COLUNAS_SAIDA = [
    "cnpj_basico", "tipo_socio", "nome_socio_ou_razao_social", "cnpj_cpf_socio",
    "qualificacao_socio", "data_entrada_sociedade", "faixa_etaria", "camada",
]


def log(msg):
    print(msg, flush=True)


def carrega_cnpj_base(caminho):
    """cnpj_basico -> camada, a partir da saída do Passo 2."""
    mapa = {}
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f)
        for row in leitor:
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
            if len(campos) < 11:
                continue
            cb = campos[0].strip()
            camada = cnpj_camada.get(cb)
            if camada is None:
                continue
            total_match += 1
            escritor.writerow([
                cb, TIPO_SOCIO.get(campos[1].strip(), campos[1].strip()),
                campos[2], campos[3], campos[4], campos[5], campos[10], camada,
            ])
            if total_lidas % 2_000_000 == 0:
                log(f"    ... {total_lidas:,} linhas lidas, {total_match:,} vínculos casaram até agora")
    return total_lidas, total_match


def main():
    if not os.path.exists(ARQUIVO_CNPJ_BASE):
        raise SystemExit(f"Não achei {ARQUIVO_CNPJ_BASE} — rode antes o filtrar_ativos_6cnaes.py (Passo 2).")

    log("Carregando CNPJs BASE ativos (Passo 2)...")
    cnpj_camada = carrega_cnpj_base(ARQUIVO_CNPJ_BASE)
    log(f"  {len(cnpj_camada):,} CNPJs BASE carregados.")

    os.makedirs(PASTA_PARCIAL, exist_ok=True)
    partes = sorted(glob.glob(os.path.join(PASTA_BRUTOS, "SOCIO*.csv")))
    if not partes:
        raise SystemExit(f"Nenhum arquivo SOCIO*.csv encontrado em {PASTA_BRUTOS}")
    log(f"{len(partes)} partes de sócios encontradas.")

    for caminho_entrada in partes:
        nome = os.path.basename(caminho_entrada)
        caminho_saida = os.path.join(PASTA_PARCIAL, nome)
        if os.path.exists(caminho_saida):
            log(f"\n{nome}: já processada — pulando. Apague {caminho_saida} para refazer.")
            continue
        log(f"\n{nome}: processando...")
        caminho_tmp = caminho_saida + ".tmp"
        total_lidas, total_match = processa_parte(caminho_entrada, caminho_tmp, cnpj_camada)
        os.replace(caminho_tmp, caminho_saida)
        log(f"  {total_lidas:,} linhas lidas, {total_match:,} vínculos societários casaram")

    log(f"\n{'='*70}\nConcatenando parciais em {ARQUIVO_FINAL}")
    parciais = sorted(glob.glob(os.path.join(PASTA_PARCIAL, "SOCIO*.csv")))
    if len(parciais) < len(partes):
        log(f"  ⚠️ só {len(parciais)}/{len(partes)} partes prontas — rode de novo para completar.")

    caminho_tmp_final = ARQUIVO_FINAL + ".tmp"
    total_final = 0
    tipo_count = {}
    camada_count = {}
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
                    tipo_count[linha[1]] = tipo_count.get(linha[1], 0) + 1
                    camada_count[linha[7]] = camada_count.get(linha[7], 0) + 1
    os.replace(caminho_tmp_final, ARQUIVO_FINAL)

    log(f"\nConsolidado final: {total_final:,} vínculos societários.")
    log(f"Por tipo de sócio: {tipo_count}")
    log(f"Por camada do CNPJ: {camada_count}")
    log(f"\nArquivo: {ARQUIVO_FINAL}")
    log(
        "\nPróximo passo: cole aqui a saída completa — a partir dela decidimos o recorte "
        "para o Passo 7 (buscar os mesmos CPFs/CNPJs de sócio em qualquer CNAE nacional, "
        "não só nas 6 já filtradas)."
    )


if __name__ == "__main__":
    main()
