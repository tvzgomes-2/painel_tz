#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""diagnostico_bigquery_socios.py — SÓ diagnóstico, não faz a análise completa.

Objetivo: confirmar, com consultas pequenas e baratas, que o dataset público
"Quadros Societários CNPJ" da Base dos Dados (projeto BigQuery público
`basedosdados`, dataset `br_me_cnpj`) tem a estrutura que o guia de método
pressupõe, ANTES de escrever a consulta pesada de comparação de snapshots.

Por quê este passo existe: mesmo padrão já usado com o FTP da RAIS nesta
tese (`diagnostico_ftp_rais.py`/`_2.py`) — sempre confirmar a estrutura real
dos dados antes de construir o pipeline em cima de suposição. Os nomes de
coluna abaixo (cnpj_basico, cnae_fiscal_principal, data, qualificacao etc.)
foram checados via busca web em 24/07/2026 (página do dataset + issue de
testes do próprio repositório `basedosdados/queries-basedosdados`), NÃO
foram inventados — mas o schema pode mudar, então este script confere antes
de qualquer coisa.

REQUISITOS (rodar localmente, com SEU projeto do Google Cloud):
    pip install google-cloud-bigquery db-dtypes
    gcloud auth application-default login
    (ou defina GOOGLE_APPLICATION_CREDENTIALS com um service account json)

USO:
    python diagnostico_bigquery_socios.py --projeto SEU_PROJETO_GCP

Custo: todas as consultas aqui são pequenas (COUNT, LIMIT, ou filtradas por
CNAE) — nenhuma deve passar de poucos GB processados, bem longe da cota
gratuita de 1 TB/mês. Ainda assim, cada consulta imprime o volume estimado
(dry run) ANTES de rodar de verdade, para você decidir se quer prosseguir."""
import argparse
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("Faltou instalar dependência. Rode:\n    pip install google-cloud-bigquery db-dtypes\ne execute de novo.")

CNAES_ALVO = ["4921301", "4921302", "4922101", "4922102", "4929901", "4929902"]

# dataset público confirmado (24/07/2026): projeto `basedosdados`, dataset `br_me_cnpj`
PROJETO_DADOS = "basedosdados"
DATASET = "br_me_cnpj"


def log(msg):
    print(msg, flush=True)


def roda_com_estimativa(client, sql, descricao):
    """Faz dry run primeiro (grátis, só estima bytes processados), pede
    confirmação se for grande, só então roda de verdade."""
    job_config_dry = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    dry = client.query(sql, job_config=job_config_dry)
    gb = dry.total_bytes_processed / 1e9
    log(f"\n--- {descricao} ---")
    log(f"  estimativa: {gb:.3f} GB processados")
    if gb > 5:
        resp = input(f"  ⚠️ consulta estimada em {gb:.1f} GB — continuar? [s/N] ")
        if resp.strip().lower() != "s":
            log("  pulado pelo usuário.")
            return None
    result = client.query(sql).result()
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projeto", required=True, help="ID do seu projeto Google Cloud (para cobrança/cota)")
    args = ap.parse_args()

    client = bigquery.Client(project=args.projeto)

    # 1) confirma que as 3 tabelas existem e lista as colunas reais
    for tabela in ["empresas", "estabelecimentos", "socios", "simples"]:
        try:
            tbl = client.get_table(f"{PROJETO_DADOS}.{DATASET}.{tabela}")
            log(f"\n=== {DATASET}.{tabela} ===")
            log(f"  linhas: {tbl.num_rows:,} | tamanho: {tbl.num_bytes/1e9:.1f} GB")
            log(f"  colunas: {[f.name for f in tbl.schema]}")
        except Exception as e:
            log(f"\n=== {DATASET}.{tabela} === ⚠️ erro: {e}")

    # 2) confirma o intervalo real de datas (snapshots) disponível na tabela de sócios
    sql_datas = f"""
        SELECT DISTINCT data
        FROM `{PROJETO_DADOS}.{DATASET}.socios`
        ORDER BY data
    """
    r = roda_com_estimativa(client, sql_datas, "datas (snapshots) disponíveis em socios")
    if r:
        datas = sorted(row["data"] for row in r)
        log(f"  {len(datas)} snapshots — de {datas[0]} a {datas[-1]}")

    # 3) sanity check: quantos cnpj_basico existem nas 6 CNAEs-alvo, no snapshot mais recente
    cnaes_sql = ", ".join(f"'{c}'" for c in CNAES_ALVO)
    sql_populacao = f"""
        SELECT COUNT(DISTINCT cnpj_basico) AS n_cnpj_basico
        FROM `{PROJETO_DADOS}.{DATASET}.estabelecimentos`
        WHERE cnae_fiscal_principal IN ({cnaes_sql})
          AND data = (SELECT MAX(data) FROM `{PROJETO_DADOS}.{DATASET}.estabelecimentos`)
    """
    r = roda_com_estimativa(client, sql_populacao, "nº de cnpj_basico nas 6 CNAEs-alvo, snapshot mais recente")
    if r:
        for row in r:
            log(f"  {row['n_cnpj_basico']:,} cnpj_basico (CNAE principal, snapshot mais recente)")

    log(
        "\nPróximo passo: cole aqui a saída completa (colunas reais de cada tabela, "
        "intervalo de datas, contagem da população-alvo) — eu ajusto o "
        "extrair_mudanca_socios_cnae.py (Passo 2-4 do guia) para bater exatamente "
        "com o schema confirmado, antes de rodar a consulta pesada de comparação "
        "de snapshots."
    )


if __name__ == "__main__":
    main()
