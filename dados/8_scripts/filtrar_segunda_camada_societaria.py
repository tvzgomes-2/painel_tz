#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""filtrar_segunda_camada_societaria.py — Passo 7 do pipeline de CNPJs (nunca
executado até 24/07/2026 — ver `pesquisa dos CNPJs.md` e [[Pendências]]).

PERGUNTA: os sócios-PESSOA JURÍDICA (PJ) das empresas de transporte (6 CNAEs)
são, eles próprios, outras empresas com sócios próprios — quem está por trás
dessas holdings/participações (ex.: COMPORTE PARTICIPAÇÕES, GB GUANABARA
PARTICIPAÇÕES, BAMPAR PARTICIPAÇÕES, VILAR DO REI PARTICIPAÇÕES — nomes que já
aparecem no recorte, ver `Socios PJ - recorte 6 CNAEs - 2026-07-24.xlsx`)?
Essa é a "segunda camada societária" que `Barões do ônibus — matérias.md`
descreve qualitativamente (Mondo FIP, Ikatu, NV9, Anbema, FeltTech, Pirajuçara
Participações) — este script traz o lado quantitativo/CNPJ.

O QUE ESTE SCRIPT FAZ (3 saídas, mesmo padrão dos scripts anteriores desta
rodada — resumível por parte, escrita atômica):
  1. `estabelecimentos_segunda_camada.csv` — filtra ESTABELECIMENTOS0-9.csv
     pelos CNPJs BASE dos sócios-PJ (SEM filtro de CNAE — essas holdings
     tipicamente têm CNAE de "administração de holdings", não de transporte;
     é esperado que a maioria não apareça em nenhum recorte de transporte).
  2. `empresas_segunda_camada.csv` — filtra empresas0-9.csv pelos mesmos
     CNPJs BASE (natureza jurídica, capital social, porte).
  3. `socios_segunda_camada.csv` — filtra SOCIO0-9.csv pelos mesmos CNPJs
     BASE — traz OS PRÓPRIOS SÓCIOS dessas holdings (2ª camada: quem controla
     quem controla as empresas de ônibus).

ENTRADA: `socios_pj_completo.csv` (coluna `cnpj_basico_socio_pj`) — 1.769
sócios-PJ distintos do recorte de 6 CNAEs de transporte, já levantados em
24/07/2026. (Equivalente em conteúdo à aba "Sócios PJ" de `Socios PJ - recorte
6 CNAEs - 2026-07-24.xlsx`; lido do CSV aqui para não depender de openpyxl.)

USO:
    python "C:\Users\HOME\OneDrive\doutorado\_meta\scripts\filtrar_segunda_camada_societaria.py"

Resumível: se travar ou for interrompido, rode de novo — pula partes já
processadas em `parcial_2camada_*/`.
"""
import csv
import glob
import os

RAIZ = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\CNPJ"
PASTA_BRUTOS = os.path.join(RAIZ, "Receita Federal - dados brutos")
PASTA_SAIDA = os.path.join(RAIZ, "filtrados (6 CNAEs transporte, 24-07-2026)")
ARQUIVO_SOCIOS_PJ = os.path.join(PASTA_SAIDA, "socios_pj_completo.csv")


def log(msg):
    print(msg, flush=True)


def carrega_cnpjs_base_pj():
    """Lê o CSV de sócios-PJ e devolve o conjunto de CNPJs BASE (8 dígitos) distintos."""
    cnpjs = set()
    with open(ARQUIVO_SOCIOS_PJ, "r", encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f)
        for row in leitor:
            v = row.get("cnpj_basico_socio_pj")
            if v:
                cnpjs.add(str(v).strip().zfill(8))
    return cnpjs


def processa_estabelecimentos(cnpjs_base, pasta_parcial):
    os.makedirs(pasta_parcial, exist_ok=True)
    partes = sorted(glob.glob(os.path.join(PASTA_BRUTOS, "ESTABELECIMENTOS*.csv")))
    if not partes:
        raise SystemExit(f"Nenhum ESTABELECIMENTOS*.csv em {PASTA_BRUTOS}")
    log(f"[Estabelecimentos] {len(partes)} partes encontradas.")
    colunas = [
        "cnpj_basico", "cnpj_ordem", "cnpj_dv", "matriz_filial", "nome_fantasia",
        "situacao_cadastral", "data_situacao_cadastral", "motivo_situacao",
        "data_inicio_atividade", "cnae_fiscal_principal", "cnae_fiscal_secundaria",
        "uf", "municipio_codigo_rfb",
    ]
    for caminho_entrada in partes:
        nome = os.path.basename(caminho_entrada)
        caminho_saida = os.path.join(pasta_parcial, nome)
        if os.path.exists(caminho_saida):
            log(f"  {nome}: já processada — pulando.")
            continue
        log(f"  {nome}: processando...")
        caminho_tmp = caminho_saida + ".tmp"
        total_lidas = total_match = 0
        with open(caminho_entrada, "r", encoding="latin1", errors="replace", newline="") as fin, \
             open(caminho_tmp, "w", encoding="utf-8-sig", newline="") as fout:
            leitor = csv.reader(fin, delimiter=";", quotechar='"')
            escritor = csv.writer(fout)
            escritor.writerow(colunas)
            for campos in leitor:
                total_lidas += 1
                if len(campos) < 21 or campos[0].strip() not in cnpjs_base:
                    continue
                total_match += 1
                escritor.writerow([
                    campos[0], campos[1], campos[2], campos[3], campos[4], campos[5],
                    campos[6], campos[7], campos[10], campos[11], campos[12],
                    campos[19], campos[20],
                ])
        os.replace(caminho_tmp, caminho_saida)
        log(f"    {total_lidas:,} lidas, {total_match:,} casaram")


def processa_empresas(cnpjs_base, pasta_parcial):
    os.makedirs(pasta_parcial, exist_ok=True)
    partes = sorted(glob.glob(os.path.join(PASTA_BRUTOS, "empresas*.csv")))
    if not partes:
        raise SystemExit(f"Nenhum empresas*.csv em {PASTA_BRUTOS}")
    log(f"[Empresas] {len(partes)} partes encontradas.")
    colunas = ["cnpj_basico", "razao_social", "natureza_juridica", "qualificacao_responsavel",
               "capital_social", "porte_empresa", "ente_federativo_responsavel"]
    for caminho_entrada in partes:
        nome = os.path.basename(caminho_entrada)
        caminho_saida = os.path.join(pasta_parcial, nome)
        if os.path.exists(caminho_saida):
            log(f"  {nome}: já processada — pulando.")
            continue
        log(f"  {nome}: processando...")
        caminho_tmp = caminho_saida + ".tmp"
        total_lidas = total_match = 0
        with open(caminho_entrada, "r", encoding="latin1", errors="replace", newline="") as fin, \
             open(caminho_tmp, "w", encoding="utf-8-sig", newline="") as fout:
            leitor = csv.reader(fin, delimiter=";", quotechar='"')
            escritor = csv.writer(fout)
            escritor.writerow(colunas)
            for campos in leitor:
                total_lidas += 1
                if len(campos) < 6 or campos[0].strip() not in cnpjs_base:
                    continue
                total_match += 1
                escritor.writerow(campos[:7])
        os.replace(caminho_tmp, caminho_saida)
        log(f"    {total_lidas:,} lidas, {total_match:,} casaram")


def processa_socios(cnpjs_base, pasta_parcial):
    os.makedirs(pasta_parcial, exist_ok=True)
    partes = sorted(glob.glob(os.path.join(PASTA_BRUTOS, "SOCIO*.csv")))
    if not partes:
        raise SystemExit(f"Nenhum SOCIO*.csv em {PASTA_BRUTOS}")
    log(f"[Sócios da 2ª camada] {len(partes)} partes encontradas.")
    colunas = ["cnpj_basico", "tipo_socio", "nome_socio_ou_razao_social", "cnpj_cpf_socio",
               "qualificacao_socio", "data_entrada_sociedade", "faixa_etaria"]
    for caminho_entrada in partes:
        nome = os.path.basename(caminho_entrada)
        caminho_saida = os.path.join(pasta_parcial, nome)
        if os.path.exists(caminho_saida):
            log(f"  {nome}: já processada — pulando.")
            continue
        log(f"  {nome}: processando...")
        caminho_tmp = caminho_saida + ".tmp"
        total_lidas = total_match = 0
        with open(caminho_entrada, "r", encoding="latin1", errors="replace", newline="") as fin, \
             open(caminho_tmp, "w", encoding="utf-8-sig", newline="") as fout:
            leitor = csv.reader(fin, delimiter=";", quotechar='"')
            escritor = csv.writer(fout)
            escritor.writerow(colunas)
            for campos in leitor:
                total_lidas += 1
                if len(campos) < 11 or campos[0].strip() not in cnpjs_base:
                    continue
                total_match += 1
                escritor.writerow([
                    campos[0], "PJ" if campos[1].strip() == "1" else ("PF" if campos[1].strip() == "2" else "estrangeiro"),
                    campos[2], campos[3], campos[4], campos[5], campos[10],
                ])
        os.replace(caminho_tmp, caminho_saida)
        log(f"    {total_lidas:,} lidas, {total_match:,} casaram")


def concatena(pasta_parcial, prefixo, arquivo_final, colunas_esperadas):
    parciais = sorted(glob.glob(os.path.join(pasta_parcial, f"{prefixo}*.csv")))
    tmp = arquivo_final + ".tmp"
    total = 0
    with open(tmp, "w", encoding="utf-8-sig", newline="") as fout:
        escritor = csv.writer(fout)
        escritor.writerow(colunas_esperadas)
        for caminho in parciais:
            with open(caminho, "r", encoding="utf-8-sig", newline="") as fin:
                leitor = csv.reader(fin)
                next(leitor)
                for linha in leitor:
                    escritor.writerow(linha)
                    total += 1
    os.replace(tmp, arquivo_final)
    log(f"  Consolidado: {total:,} linhas -> {arquivo_final}")
    return total


def main():
    log("Carregando CNPJs BASE dos sócios-PJ (Socios PJ - recorte 6 CNAEs - 2026-07-24.xlsx)...")
    cnpjs_base = carrega_cnpjs_base_pj()
    log(f"  {len(cnpjs_base):,} CNPJs BASE distintos de sócios-PJ a buscar na base bruta.\n")

    log("=" * 70)
    processa_estabelecimentos(cnpjs_base, os.path.join(PASTA_SAIDA, "parcial_2camada_estab"))
    concatena(
        os.path.join(PASTA_SAIDA, "parcial_2camada_estab"), "ESTABELECIMENTOS",
        os.path.join(PASTA_SAIDA, "estabelecimentos_segunda_camada.csv"),
        ["cnpj_basico", "cnpj_ordem", "cnpj_dv", "matriz_filial", "nome_fantasia",
         "situacao_cadastral", "data_situacao_cadastral", "motivo_situacao",
         "data_inicio_atividade", "cnae_fiscal_principal", "cnae_fiscal_secundaria",
         "uf", "municipio_codigo_rfb"],
    )

    log("\n" + "=" * 70)
    processa_empresas(cnpjs_base, os.path.join(PASTA_SAIDA, "parcial_2camada_empresas"))
    concatena(
        os.path.join(PASTA_SAIDA, "parcial_2camada_empresas"), "empresas",
        os.path.join(PASTA_SAIDA, "empresas_segunda_camada.csv"),
        ["cnpj_basico", "razao_social", "natureza_juridica", "qualificacao_responsavel",
         "capital_social", "porte_empresa", "ente_federativo_responsavel"],
    )

    log("\n" + "=" * 70)
    processa_socios(cnpjs_base, os.path.join(PASTA_SAIDA, "parcial_2camada_socios"))
    concatena(
        os.path.join(PASTA_SAIDA, "parcial_2camada_socios"), "SOCIO",
        os.path.join(PASTA_SAIDA, "socios_segunda_camada.csv"),
        ["cnpj_basico", "tipo_socio", "nome_socio_ou_razao_social", "cnpj_cpf_socio",
         "qualificacao_socio", "data_entrada_sociedade", "faixa_etaria"],
    )

    log("\n" + "=" * 70)
    log("Concluído. Três arquivos novos em:")
    log(f"  {PASTA_SAIDA}")
    log("  - estabelecimentos_segunda_camada.csv  (cadastro das holdings/participações)")
    log("  - empresas_segunda_camada.csv           (natureza jurídica, capital, porte)")
    log("  - socios_segunda_camada.csv             (quem SÃO OS SÓCIOS dessas holdings — 2ª camada)")
    log("\nCole a saída deste script aqui para eu analisar os resultados.")


if __name__ == "__main__":
    main()
