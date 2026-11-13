#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""baixar_rais_cempre_sidra.py — baixa, por município (todos os 5.570), as duas
tabelas SIDRA/IBGE que substituem, na série atual (2022 em diante), o antigo
Cadastro Central de Empresas (CEMPRE, baseado em RAIS/eSocial):

  - Tabela 9509: salário médio mensal + pessoal ocupado total/assalariado +
    pessoal assalariado médio + salários e outras remunerações, por
    município, SEM faixa de pessoal ocupado nem CNAE. Sucessora da 1685.
  - Tabela 9582: número de empresas por FAIXAS DE PESSOAL OCUPADO, por
    município, CNAE (seção) e ano de fundação. Dá o corte de "porte da
    empresa" (1-4, 5-9, 10-19 ... 1000+) que a 9509 não tem.

CONTEXTO: não existe, na série corrente, uma tabela única que cruze salário
médio × porte × município para os 5.570 municípios — as antigas que faziam
isso (988/992/6703/3421) encerraram em 2021 e só cobriam municípios com 50
mil+ habitantes. Por isso baixamos as duas separadas e cruzamos depois por
`cod_ibge` (união simples — não é o mesmo que ter salário médio POR faixa de
porte; ver ressalva impressa no fim do script).

⚠️ QUEBRA METODOLÓGICA A DOCUMENTAR NA TESE: RAIS tradicional (declaração
anual) terminou no ano-base 2021. A série 2022+ é derivada do eSocial,
metodologia diferente — não tratar 2021 e 2022+ como diretamente
comparáveis sem ressalva.

TENTATIVA 1 (rede do Claude) falhou: `apisidra.ibge.gov.br` está bloqueado
no proxy do sandbox (403 Forbidden confirmado). TENTATIVA 2 (sua máquina,
sessão anterior) trouxe todos os municípios de uma vez e esbarrou no limite
da API SIDRA: "Quantidade de valores solicitados: 133680 excedeu o limite:
50000". Este script corrige isso de duas formas, sem exigir que eu confirme
nada ao vivo (a rede aqui continua bloqueada):
  1. Busca os cod_ibge no PRÓPRIO `base_municipal_v3.csv` do cofre e baixa
     EM LOTES de município (não todos de uma vez), com REDUÇÃO AUTOMÁTICA
     do tamanho do lote sempre que a API responder "excedeu o limite" —
     não precisa acertar o tamanho certo de antemão.
  2. Para a tabela 9582 (que tem 3 classificações: faixas de pessoal, CNAE
     e ano de fundação), consulta os METADADOS da tabela em tempo de
     execução (`/agregados/9582/metadados`) e filtra CNAE e ano de fundação
     para a categoria "Total" — mantém só a dimensão que interessa (faixas
     de pessoal ocupado) sem o produto cartesiano com setor/ano de fundação.
     Se a consulta de metadados falhar por qualquer motivo, o script avisa
     e segue sem esse filtro (só com os lotes menores mesmo).

REQUISITOS (rodar localmente):
    pip install sidrapy pandas requests

USO:
    python baixar_rais_cempre_sidra.py
    (salva os CSVs em ./saida_rais/ — ajuste OUT_DIR abaixo se quiser
    apontar direto para a pasta do cofre, ex.:
    r"C:\\Users\\HOME\\OneDrive\\doutorado\\03 - Dados\\_data\\RAIS-Cempre")

Ajuste BASE_CSV abaixo se o caminho do `base_municipal_v3.csv` for
diferente do padrão do cofre."""
import os
import re
import sys
import time

import pandas as pd

try:
    import sidrapy
except ImportError:
    sys.exit(
        "Faltou instalar dependências. Rode:\n"
        "    pip install sidrapy pandas requests\n"
        "e execute este script de novo."
    )

try:
    import requests
except ImportError:
    requests = None  # metadados vira best-effort; sem requests só pulamos esse passo

# ajuste para a pasta do cofre se quiser salvar direto lá, ex.:
# OUT_DIR = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\RAIS-Cempre"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saida_rais")

# caminho padrão do banco no cofre (ajuste se rodar de outro lugar)
BASE_CSV = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\Base Municipal v3\base_municipal_v3.csv"

TABELA_SALARIO = "9509"   # salário médio mensal, pessoal ocupado/assalariado — todos os municípios, sem faixa/CNAE
TABELA_PORTE = "9582"     # nº de empresas por faixas de pessoal ocupado — todos os municípios, com CNAE e ano de fundação
PERIODO = "last 1"        # 1 ano mais recente disponível; troque para "2023" etc. se quiser fixar

LOTE_INICIAL = 300        # nº de municípios por chamada; reduz sozinho se a API reclamar de limite


def log(msg):
    print(msg, flush=True)


def salvar_atomico(df, path):
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, path)


def carregar_cod_ibge():
    """Lê os cod_ibge (7 dígitos, string) do banco municipal já existente no
    cofre. Se não achar o arquivo, cai para uma lista vazia e avisa — nesse
    caso, ajuste BASE_CSV no topo do script."""
    if not os.path.exists(BASE_CSV):
        log(f"⚠️ Não achei {BASE_CSV} — ajuste a constante BASE_CSV no script.")
        return []
    df = pd.read_csv(BASE_CSV, usecols=["cod_ibge"], dtype=str, low_memory=False)
    codigos = df["cod_ibge"].dropna().map(lambda x: str(int(float(x))).zfill(7)).unique().tolist()
    log(f"cod_ibge carregado de base_municipal_v3.csv: {len(codigos)} municípios")
    return codigos


def descobrir_categoria_total(tabela, manter_classificacao_com_palavra):
    """Consulta os metadados da tabela no SIDRA e devolve um dict de
    classificações a passar em `classifications=`:
      - para a classificação CUJO NOME contém `manter_classificacao_com_palavra`
        (a dimensão que queremos ABERTA, ex. 'pessoal ocupado'): valor "all"
        — é preciso ser EXPLÍCITO ("all"), porque omitir a classificação do
        dict não traz todas as categorias, traz só a default (geralmente
        Total) — bug já visto na 1ª rodada (saiu só a linha Total de porte).
      - para as DEMAIS classificações: id da categoria "Total", pra não
        multiplicar linhas por CNAE/ano de fundação que não usamos.
    Retorna {} (sem filtro nenhum) se a consulta de metadados falhar — nesse
    caso o script ainda funciona, só que sem filtro (mais linhas, mais
    lento, mas sem quebrar)."""
    if requests is None:
        log("  (pacote requests não instalado — pulando filtro de metadados)")
        return {}
    url = f"https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}/metadados"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        meta = r.json()
    except Exception as e:
        log(f"  ⚠️ não consegui ler metadados de {url} ({e}) — seguindo sem filtro de Total.")
        return {}

    filtro = {}
    for classif in meta.get("classificacoes", []):
        nome = classif.get("nome", "")
        classif_id = str(classif["id"])
        if manter_classificacao_com_palavra.lower() in nome.lower():
            filtro[classif_id] = "all"
            log(f"  classificação mantida ABERTA (todas as categorias, explícito 'all'): {nome!r}")
            continue
        total_id = None
        for cat in classif.get("categorias", []):
            if str(cat.get("nome", "")).strip().lower() == "total":
                total_id = cat.get("id")
                break
        if total_id is not None:
            filtro[classif_id] = str(total_id)
            log(f"  classificação {nome!r}: filtrando para categoria Total (id={total_id})")
        else:
            log(f"  ⚠️ não achei categoria 'Total' em {nome!r} — essa dimensão fica sem filtro "
                f"(pode inflar o resultado).")
    return filtro


def baixar_tabela_em_lotes(tabela, nome_arquivo, cod_ibge_list, classifications=None, forcar=False):
    """Baixa uma tabela SIDRA em lotes de município, reduzindo o tamanho do
    lote pela metade sempre que a API reclamar de limite de valores, até
    conseguir. Concatena tudo no final.

    Se `forcar=False` (padrão) e já existir um CSV de saída com esse nome,
    PULA o download e só lê o arquivo existente — útil pra não rebaixar a
    9509 de novo quando só a 9582 precisou de correção. Use forcar=True (ou
    apague o arquivo) se quiser reprocessar do zero."""
    path_existente = os.path.join(OUT_DIR, nome_arquivo)
    if not forcar and os.path.exists(path_existente):
        log(f"\n=== Tabela {tabela}: já existe {path_existente} — pulando download "
            f"(rode com o arquivo apagado, ou forcar=True, se quiser refazer) ===")
        return pd.read_csv(path_existente, skiprows=[1])

    log(f"\n=== Baixando tabela {tabela} em lotes (período={PERIODO}) ===")
    codigos = list(cod_ibge_list)
    partes = []
    i = 0
    lote = LOTE_INICIAL
    while i < len(codigos):
        chunk = codigos[i:i + lote]
        codigos_str = ",".join(chunk)
        try:
            kwargs = dict(
                table_code=tabela,
                territorial_level="6",
                ibge_territorial_code=codigos_str,
                period=PERIODO,
                header="y",
            )
            if classifications:
                kwargs["classifications"] = classifications
            df = sidrapy.get_table(**kwargs)
        except ValueError as e:
            if "excedeu o limite" in str(e) and lote > 10:
                lote = max(10, lote // 2)
                log(f"  limite excedido com lote={len(chunk)} — reduzindo para {lote} e tentando de novo.")
                continue  # não avança i; tenta o mesmo trecho com lote menor
            log(f"  ⚠️ erro ao baixar município {i}-{i+lote} ({chunk[0]}...): {e}")
            i += lote
            continue
        except Exception as e:
            log(f"  ⚠️ erro inesperado no lote {i}-{i+lote}: {e} — tentando de novo em 5s.")
            time.sleep(5)
            continue

        partes.append(df)
        log(f"  lote {i}-{i+len(chunk)}/{len(codigos)} OK ({df.shape[0]} linhas)")
        i += lote
        time.sleep(0.5)  # gentileza com a API

    if not partes:
        log(f"  ⚠️ nenhum dado baixado para a tabela {tabela}.")
        return pd.DataFrame()

    resultado = pd.concat(partes, ignore_index=True)
    log(f"  total: {resultado.shape[0]} linhas x {resultado.shape[1]} colunas")
    log(f"  colunas: {list(resultado.columns)}")
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, nome_arquivo)
    salvar_atomico(resultado, path)
    log(f"  salvo em: {path}")
    return resultado


def main():
    log(f"Saída em: {OUT_DIR}")
    codigos = carregar_cod_ibge()
    if not codigos:
        sys.exit("Sem lista de municípios para consultar — ajuste BASE_CSV e rode de novo.")

    # --- Tabela 9509: salário médio mensal + pessoal ocupado/assalariado ---
    baixar_tabela_em_lotes(TABELA_SALARIO, "sidra_9509_salario_medio_bruto.csv", codigos)

    # --- Tabela 9582: nº de empresas por faixas de pessoal ocupado ---
    # forcar=True: a 1ª rodada (antes desta correção) salvou um CSV com só a
    # linha "Total" de porte (bug já corrigido no filtro acima) — precisa
    # refazer mesmo que o arquivo já exista.
    log(f"\nConsultando metadados da tabela {TABELA_PORTE} para filtrar CNAE/ano de fundação em 'Total'...")
    filtro_total = descobrir_categoria_total(TABELA_PORTE, manter_classificacao_com_palavra="pessoal")
    df_porte = baixar_tabela_em_lotes(
        TABELA_PORTE, "sidra_9582_porte_filtrado.csv", codigos, classifications=filtro_total or None, forcar=True
    )

    log("\n=== OK — CSVs salvos em " + OUT_DIR + " ===")
    log(
        "\nPróximos passos (pode voltar pro Claude com estes CSVs): (1) conferir\n"
        "se `cod_ibge`/`D1C` (código do município na saída do SIDRA) bate 1:1\n"
        "com os 5.570 do banco; (2) cruzar salário médio (9509) com faixas de\n"
        "pessoal (9582) e com o `rais_2022.csv` já extraído do dump da POLO\n"
        "(`_data/POLO/.../t_rais/rais_2022.csv`) para validação cruzada;\n"
        "(3) construir os dois cenários (CTP: isenta faixas 1-4/5-9; CTPU: sem\n"
        "isenção) usando salário médio como proxy da folha, comparando com o\n"
        "custo do sistema de TP já no banco (tarifa_reconciliada,\n"
        "subsidio_pct_custo_ntu etc.)."
    )


if __name__ == "__main__":
    main()
