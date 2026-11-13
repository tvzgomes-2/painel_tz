#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""baixar_censo2022_informalidade.py — baixa, por município (todos os
5.570), os dados do Censo 2022 sobre POSIÇÃO NA OCUPAÇÃO / CATEGORIA DO
EMPREGO no trabalho principal (com/sem carteira assinada, conta própria
com/sem CNPJ, empregador, trabalhador familiar auxiliar etc.) — a base
para construir uma variável de INFORMALIDADE por município.

CONTEXTO E POR QUE ESTE SCRIPT EXISTE (mesma razão do
`baixar_rais_cempre_sidra.py`): a API do SIDRA/IBGE está bloqueada no
sandbox do Claude (`apisidra.ibge.gov.br` e `servicodados.ibge.gov.br`
testados — ambos 403 Forbidden pelo proxy). Precisa rodar na sua máquina.

⚠️ RESSALVAS METODOLÓGICAS IMPORTANTES (documentar sempre que citar):
1. Estes dados vêm dos "Resultados preliminares da AMOSTRA" do Censo 2022
   (~10% da população, questionário da amostra) — NÃO são o Censo completo
   (questionário básico). Têm coeficiente de variação (erro amostral) maior
   em municípios pequenos. Confira a coluna de margem/CV se o SIDRA
   devolver uma (algumas tabelas do Censo trazem MC/CV junto do valor).
2. A tabela usada (10261, confirmada por checagem do release oficial do
   IBGE — ver "Censo 2022: Trabalho e Rendimento") mistura, na mesma
   classificação, POSIÇÃO NA OCUPAÇÃO (Empregado / Conta própria /
   Empregador / Trabalhador familiar auxiliar) e, dentro de "Empregado",
   a CATEGORIA DO EMPREGO (setor privado/público/doméstico/estatal ×
   com/sem carteira assinada). O SCRIPT NÃO decide sozinho quais categorias
   somam para "informalidade" — ele baixa TODAS as categorias que existem
   e imprime a lista completa, para essa decisão ser tomada com o autor
   depois de ver os rótulos reais (a essa altura só confirmamos os rótulos
   de "Empregados" citados num slide do IBGE; os de conta própria/
   empregador ainda não foram vistos na prática).
3. Definição de trabalho combinada com o Thiago (23/07/2026): DEFINIÇÃO
   AMPLA de informalidade — não se limitar a "empregado sem carteira".
   Depois que este script rodar e você colar a lista de categorias
   encontradas, eu (Claude) monto a soma específica (ex.: empregado sem
   carteira + doméstico sem carteira + conta própria sem CNPJ + empregador
   sem CNPJ + trabalhador familiar auxiliar, se essas categorias existirem
   separadamente na tabela) e documento a composição exata no
   `metadados.csv`.

REQUISITOS (rodar localmente):
    pip install sidrapy pandas requests

USO:
    python baixar_censo2022_informalidade.py
    (salva os CSVs em ./saida_censo2022/ — ajuste OUT_DIR abaixo se quiser
    apontar direto pra pasta do cofre, ex.:
    r"C:\\Users\\HOME\\OneDrive\\doutorado\\03 - Dados\\_data\\Censo2022-Informalidade")

Ajuste BASE_CSV abaixo se o caminho do `base_municipal_v3.csv` for
diferente do padrão do cofre."""
import os
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
    requests = None  # descoberta de metadados vira best-effort sem isso

# ajuste para a pasta do cofre se quiser salvar direto lá, ex.:
# OUT_DIR = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\Censo2022-Informalidade"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saida_censo2022")

# caminho padrão do banco no cofre (ajuste se rodar de outro lugar)
BASE_CSV = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\Base Municipal v3\base_municipal_v3.csv"

# Tabela 10261: pessoas de 14+ ocupadas, por posição na ocupação e categoria
# do emprego no trabalho principal, por sexo — Censo 2022, resultados
# preliminares da amostra. Confirmada com granularidade municipal no
# release oficial do IBGE (apresentação "Trabalho e Rendimento").
TABELA_INFORMALIDADE = "10261"

# Tabela 10268: nível de ocupação (pessoas ocupadas / população 14+) — usada
# como denominador/contexto (total de ocupados por município), mesma fonte.
TABELA_OCUPACAO = "10268"

PERIODO = "last 1"   # 1 período mais recente disponível
LOTE_INICIAL = 300   # nº de municípios por chamada; reduz sozinho se a API reclamar de limite


def log(msg):
    print(msg, flush=True)


def salvar_atomico(df, path):
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, path)


def carregar_cod_ibge():
    if not os.path.exists(BASE_CSV):
        log(f"⚠️ Não achei {BASE_CSV} — ajuste a constante BASE_CSV no script.")
        return []
    df = pd.read_csv(BASE_CSV, usecols=["cod_ibge"], dtype=str, low_memory=False)
    codigos = df["cod_ibge"].dropna().map(lambda x: str(int(float(x))).zfill(7)).unique().tolist()
    log(f"cod_ibge carregado de base_municipal_v3.csv: {len(codigos)} municípios")
    return codigos


def imprimir_metadados_completos(tabela):
    """Imprime TODAS as classificações e categorias da tabela — não filtra
    nada. O objetivo aqui é DESCOBRIR a lista real de categorias de posição
    na ocupação/categoria do emprego (não sabemos de antemão se conta
    própria/empregador aparecem com ou sem CNPJ como categorias distintas)
    antes de decidir a fórmula de informalidade."""
    if requests is None:
        log("  (pacote requests não instalado — pulando impressão de metadados)")
        return None
    url = f"https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}/metadados"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        meta = r.json()
    except Exception as e:
        log(f"  ⚠️ não consegui ler metadados de {url} ({e}).")
        return None

    log(f"\n=== Metadados completos da tabela {tabela}: {meta.get('nome', '')!r} ===")
    log(f"Período disponível: {meta.get('periodicidade', {})}")
    log("Variáveis:")
    for v in meta.get("variaveis", []):
        log(f"  [{v.get('id')}] {v.get('nome')} (unidade: {v.get('unidade')})")
    log("Classificações e categorias:")
    for classif in meta.get("classificacoes", []):
        log(f"  Classificação [{classif.get('id')}] {classif.get('nome')!r}:")
        for cat in classif.get("categorias", []):
            log(f"    - [{cat.get('id')}] {cat.get('nome')}")
    return meta


def descobrir_filtro_sexo_total(meta):
    """Dentro dos metadados já lidos, acha a classificação 'sexo' e devolve
    o filtro {classif_id: id_categoria_Total} — mantemos as outras
    classificações (posição/categoria do emprego) TODAS ABERTAS (explícito
    'all'), porque é exatamente isso que queremos enumerar."""
    if meta is None:
        return None
    filtro = {}
    for classif in meta.get("classificacoes", []):
        nome = classif.get("nome", "").lower()
        classif_id = str(classif["id"])
        if "sexo" in nome:
            for cat in classif.get("categorias", []):
                if str(cat.get("nome", "")).strip().lower() == "total":
                    filtro[classif_id] = str(cat["id"])
                    log(f"  sexo: filtrando para Total (id={cat['id']})")
                    break
        else:
            filtro[classif_id] = "all"
            log(f"  classificação mantida ABERTA (todas as categorias): {classif.get('nome')!r}")
    return filtro


def baixar_tabela_em_lotes(tabela, nome_arquivo, cod_ibge_list, classifications=None, forcar=False):
    """Mesma lógica adaptativa de lote do script da RAIS/SIDRA: reduz o
    tamanho do lote pela metade sempre que a API reclamar de limite."""
    path_existente = os.path.join(OUT_DIR, nome_arquivo)
    if not forcar and os.path.exists(path_existente):
        log(f"\n=== Tabela {tabela}: já existe {path_existente} — pulando download ===")
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
                continue
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
        time.sleep(0.5)

    if not partes:
        log(f"  ⚠️ nenhum dado baixado para a tabela {tabela}.")
        return pd.DataFrame()

    resultado = pd.concat(partes, ignore_index=True)
    log(f"  total: {resultado.shape[0]} linhas x {resultado.shape[1]} colunas")
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

    # --- Passo 1: descobrir a estrutura real da tabela 10261 (sem adivinhar) ---
    meta_informalidade = imprimir_metadados_completos(TABELA_INFORMALIDADE)
    filtro_informalidade = descobrir_filtro_sexo_total(meta_informalidade)

    # --- Passo 2: baixar 10261 para todos os municípios, com TODAS as
    # categorias de posição/categoria do emprego (só sexo fixado em Total) ---
    baixar_tabela_em_lotes(
        TABELA_INFORMALIDADE, "sidra_10261_posicao_ocupacao.csv", codigos,
        classifications=filtro_informalidade,
    )

    # --- Passo 3: tabela de contexto (nível de ocupação / total ocupados) ---
    meta_ocupacao = imprimir_metadados_completos(TABELA_OCUPACAO)
    filtro_ocupacao = descobrir_filtro_sexo_total(meta_ocupacao)
    baixar_tabela_em_lotes(
        TABELA_OCUPACAO, "sidra_10268_nivel_ocupacao.csv", codigos,
        classifications=filtro_ocupacao,
    )

    log("\n=== OK — CSVs e metadados impressos acima ===")
    log(
        "\nPróximo passo: cole aqui no chat (1) a lista de categorias que\n"
        "apareceu em 'Classificações e categorias' da tabela 10261 acima —\n"
        "preciso ver os nomes EXATOS (ex.: existe mesmo 'Conta própria sem\n"
        "CNPJ' e 'Empregador sem CNPJ' como categorias, ou só 'Conta própria'\n"
        "sem quebra?) — e (2) o preview do CSV salvo (df.head()). Com isso eu\n"
        "monto a soma exata da definição AMPLA de informalidade (combinada\n"
        "com você) e documento a composição no metadados.csv antes de\n"
        "integrar ao banco municipal."
    )


if __name__ == "__main__":
    main()
