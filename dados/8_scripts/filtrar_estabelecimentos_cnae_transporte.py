#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""filtrar_estabelecimentos_cnae_transporte.py — refaz/expande o Passo 1
("Delimitação do Universo Amostral") do pipeline de CNPJs do Eixo 2.

POR QUE ESTE SCRIPT EXISTE (24/07/2026): os arquivos canônicos do recorte
até hoje (`filtrados (CNAE 4921301-02)/Estab..._v3.xlsx`) só usam as 2 CNAEs
"núcleo" (transporte urbano/metropolitano). O texto de método em
`pesquisa dos CNPJs.md` sempre descreveu 6 CNAEs — decisão agora
explicitada (ver nota "Atualização metodológica" no mesmo arquivo):

  NÚCLEO   (objeto direto da Tarifa Zero): 4921301 (municipal), 4921302 (metropolitano)
  EXPANSÃO (escala real do grupo econômico): 4922101 (intermunicipal), 4922102
            (interestadual), 4929901 (fretamento municipal), 4929902
            (fretamento inter/interestadual/internacional)

Este script varre as 10 partes brutas de ESTABELECIMENTOS (formato oficial
de distribuição da Receita Federal, sem cabeçalho, ';'-separado, campos
entre aspas, latin-1) e filtra por essas 6 CNAEs, marcando de qual camada
cada match veio e se veio da CNAE principal ou de uma secundária.

NÃO faz ainda: filtro de situação=ATIVOS (Passo 2) nem bridge para código
IBGE (Passo 3) — de propósito. O município aqui sai como o CÓDIGO INTERNO
da Receita Federal (ex. "7099"), que NÃO é o código IBGE e NÃO bate com o
`municipios.csv` já solto na pasta (esse é uma tabela pública diferente,
com código IBGE de 7 dígitos — não serve como ponte para este campo). Fica
como pendência explícita: confirmar qual tabela de município a Receita
distribui (deve vir junto do próprio dump bruto, ou dentro das abas
"municipios" do `Estab..._v2/v3.xlsx` já existentes) antes de georreferenciar.

LAYOUT confirmado por inspeção direta do arquivo em 24/07/2026 (30 colunas,
0-indexadas):
  0 cnpj_basico | 1 cnpj_ordem | 2 cnpj_dv | 3 matriz_filial | 4 nome_fantasia
  5 situacao_cadastral | 6 data_situacao | 7 motivo_situacao | 8 cidade_exterior
  9 pais | 10 data_inicio_atividade | 11 cnae_fiscal_principal
  12 cnae_fiscal_secundaria (pode ter VÁRIOS códigos separados por vírgula
     dentro do mesmo campo) | 13 tipo_logradouro | 14 logradouro | 15 numero
  16 complemento | 17 bairro | 18 cep | 19 uf | 20 municipio (código RFB,
     não-IBGE) | 21-26 contatos | 27 email | 28-29 situação especial

Situação cadastral (códigos oficiais RFB, não inventados — mas o script
imprime a distribuição real encontrada para você conferir): 01 nula,
02 ativa, 03 suspensa, 04 inapta, 08 baixada.

REQUISITOS: só biblioteca padrão do Python (csv, os, glob) — não precisa
instalar nada.

USO (rodar localmente, a partir de qualquer pasta):
    python "C:\Users\HOME\OneDrive\doutorado\_meta\scripts\filtrar_estabelecimentos_cnae_transporte.py"

RESUMÍVEL: cada uma das 10 partes brutas é processada e salva em
`filtrados (6 CNAEs transporte, 24-07-2026)\parcial\ESTABELECIMENTOS<n>.csv`
— se essa parcial já existe, a parte é pulada (apague o arquivo da parcial
se quiser reprocessar aquela parte). Ao final, todas as parciais existentes
são concatenadas no arquivo consolidado, sempre lido do zero do disco (não
confia em acumulação em memória entre partes) — protege contra reinício no
meio do processamento, mesmo padrão já usado com a RAIS nesta pesquisa.

NÃO MEXE no arquivo canônico anterior (`filtrados (CNAE 4921301-02)/`) —
grava tudo numa pasta nova, para você reconciliar canônico-vs-histórico
depois de conferir o resultado (norma do cofre: nunca sobrescrever/apagar
sem confirmação)."""
import csv
import glob
import os

RAIZ = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\CNPJ"
PASTA_BRUTOS = os.path.join(RAIZ, "Receita Federal - dados brutos")
PASTA_SAIDA = os.path.join(RAIZ, "filtrados (6 CNAEs transporte, 24-07-2026)")
PASTA_PARCIAL = os.path.join(PASTA_SAIDA, "parcial")
ARQUIVO_FINAL = os.path.join(PASTA_SAIDA, "estabelecimentos_filtrado_6cnaes.csv")

NUCLEO = {"4921301", "4921302"}
EXPANSAO = {"4922101", "4922102", "4929901", "4929902"}
CNAES_ALVO = NUCLEO | EXPANSAO

COLUNAS_SAIDA = [
    "cnpj_basico", "cnpj_ordem", "cnpj_dv", "matriz_filial", "nome_fantasia",
    "situacao_cadastral", "data_situacao_cadastral", "data_inicio_atividade",
    "cnae_fiscal_principal", "cnae_fiscal_secundaria",
    "uf", "municipio_codigo_rfb", "cep",
    "cnae_alvo_encontrado", "camada", "tipo_match",
]

SITUACAO_DESCRICAO = {"01": "nula", "02": "ativa", "03": "suspensa", "04": "inapta", "08": "baixada"}


def log(msg):
    print(msg, flush=True)


def camada_de(cnae):
    if cnae in NUCLEO:
        return "nucleo"
    if cnae in EXPANSAO:
        return "expansao"
    return None


def processa_linha(campos):
    """Recebe os 30 campos crus de uma linha e devolve (linha_saida, situacao)
    se a linha casar com alguma das 6 CNAEs-alvo (principal OU secundária),
    ou None se não casar."""
    if len(campos) < 21:
        return None, None
    cnae_principal = campos[11].strip()
    cnae_secundarias = [c.strip() for c in campos[12].split(",") if c.strip()]

    if cnae_principal in CNAES_ALVO:
        cnae_encontrado = cnae_principal
        tipo_match = "principal"
    else:
        cnae_encontrado = next((c for c in cnae_secundarias if c in CNAES_ALVO), None)
        tipo_match = "secundaria"

    if cnae_encontrado is None:
        return None, None

    situacao = campos[5].strip()
    linha_saida = [
        campos[0], campos[1], campos[2], campos[3], campos[4],
        situacao, campos[6], campos[10],
        cnae_principal, campos[12],
        campos[19], campos[20], campos[18],
        cnae_encontrado, camada_de(cnae_encontrado), tipo_match,
    ]
    return linha_saida, situacao


def processa_parte(caminho_entrada, caminho_saida):
    total_lidas = 0
    total_match = 0
    contagem_situacao = {}
    with open(caminho_entrada, "r", encoding="latin1", errors="replace", newline="") as fin, \
         open(caminho_saida, "w", encoding="utf-8-sig", newline="") as fout:
        leitor = csv.reader(fin, delimiter=";", quotechar='"')
        escritor = csv.writer(fout)
        escritor.writerow(COLUNAS_SAIDA)
        for campos in leitor:
            total_lidas += 1
            linha_saida, situacao = processa_linha(campos)
            if linha_saida is not None:
                total_match += 1
                contagem_situacao[situacao] = contagem_situacao.get(situacao, 0) + 1
                escritor.writerow(linha_saida)
            if total_lidas % 2_000_000 == 0:
                log(f"    ... {total_lidas:,} linhas lidas, {total_match:,} casaram até agora")
    return total_lidas, total_match, contagem_situacao


def main():
    os.makedirs(PASTA_PARCIAL, exist_ok=True)

    partes = sorted(glob.glob(os.path.join(PASTA_BRUTOS, "ESTABELECIMENTOS*.csv")))
    if not partes:
        raise SystemExit(f"Nenhum arquivo ESTABELECIMENTOS*.csv encontrado em {PASTA_BRUTOS}")
    log(f"{len(partes)} partes encontradas em {PASTA_BRUTOS}")

    contagem_situacao_geral = {}
    for caminho_entrada in partes:
        nome = os.path.basename(caminho_entrada)
        caminho_saida = os.path.join(PASTA_PARCIAL, nome)
        if os.path.exists(caminho_saida):
            log(f"\n{nome}: já processada (parcial existe) — pulando. Apague {caminho_saida} para refazer.")
            continue
        log(f"\n{nome}: processando...")
        caminho_tmp = caminho_saida + ".tmp"
        total_lidas, total_match, contagem_situacao = processa_parte(caminho_entrada, caminho_tmp)
        os.replace(caminho_tmp, caminho_saida)
        log(f"  {total_lidas:,} linhas lidas, {total_match:,} casaram com as 6 CNAEs-alvo")
        log(f"  situação cadastral entre os matches: {contagem_situacao}")
        for k, v in contagem_situacao.items():
            contagem_situacao_geral[k] = contagem_situacao_geral.get(k, 0) + v

    # concatenação final — sempre relida do disco, nunca confia em acumulação em memória
    log(f"\n{'='*70}\nConcatenando todas as parciais em {ARQUIVO_FINAL}")
    parciais = sorted(glob.glob(os.path.join(PASTA_PARCIAL, "ESTABELECIMENTOS*.csv")))
    if len(parciais) < len(partes):
        log(f"  ⚠️ só {len(parciais)}/{len(partes)} partes têm parcial pronta — rode de novo para completar as que faltam antes de usar o consolidado.")

    caminho_tmp_final = ARQUIVO_FINAL + ".tmp"
    total_final = 0
    with open(caminho_tmp_final, "w", encoding="utf-8-sig", newline="") as fout:
        escritor = csv.writer(fout)
        escritor.writerow(COLUNAS_SAIDA)
        for i, caminho_parcial in enumerate(parciais):
            with open(caminho_parcial, "r", encoding="utf-8-sig", newline="") as fin:
                leitor = csv.reader(fin)
                next(leitor)  # pula cabeçalho de cada parcial
                for linha in leitor:
                    escritor.writerow(linha)
                    total_final += 1
    os.replace(caminho_tmp_final, ARQUIVO_FINAL)

    log(f"\nConsolidado final: {total_final:,} estabelecimentos nas 6 CNAEs-alvo.")
    log(f"Distribuição de situação cadastral (códigos oficiais: 01 nula, 02 ativa, 03 suspensa, 04 inapta, 08 baixada):")
    for k, v in sorted(contagem_situacao_geral.items(), key=lambda x: -x[1]):
        log(f"  {k} ({SITUACAO_DESCRICAO.get(k, '?')}): {v:,}")
    log(f"\nArquivo: {ARQUIVO_FINAL}")
    log(
        "\nPróximo passo: cole aqui a saída completa (contagens por parte, distribuição de "
        "situação cadastral) — a partir dela eu escrevo o filtro de ATIVOS (Passo 2) e "
        "reconcilio com o `Estab..._v3.xlsx` canônico (ver quantos CNPJs a mais a camada de "
        "expansão traz em relação aos 12.907 já conhecidos)."
    )


if __name__ == "__main__":
    main()
