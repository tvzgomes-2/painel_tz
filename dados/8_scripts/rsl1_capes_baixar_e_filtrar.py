#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSL1 — CAPES: baixa os 4 XLSX do Catálogo de Teses e Dissertações (2021-2024)
e filtra localmente pelos Blocos A-E do protocolo da RSL.

Por que este script existe (contexto, RSL1):
  A interface de busca do Catálogo de Teses CAPES (catalogodeteses.capes.gov.br)
  depende de JavaScript e não devolveu resultados de forma confiável. O datastore
  público (CKAN datastore_search) só expõe 1000 linhas por recurso — é amostra,
  não a base. A rota que sobra, e que é reprodutível (Xiao & Watson; King —
  Replicação), é baixar os microdados oficiais e filtrar localmente.

  Rodar o CSV bruto por ano (~455-506 MB) excede o limite de transferência do
  ambiente de trabalho na nuvem — por isso o download é feito pelo XLSX
  equivalente (~150-170 MB cada), que cabe, e por isso este script roda na SUA
  máquina, com a sua rede, não no container.

O que o script faz, em ordem:
  1. Baixa os 4 arquivos XLSX (2021, 2022, 2023, 2024) da API de dados abertos
     da CAPES, com retomada idempotente (não rebaixa o que já está completo).
  2. Abre cada XLSX em modo streaming (openpyxl, read_only) e varre os campos
     de título, resumo (PT/EN) e palavras-chave (PT/EN) com as expressões dos
     Blocos A-E de `Expressões de busca do RSL1 — conjunto a executar
     (03-09-2026)`.
  3. Grava dois CSVs, no padrão do cofre (`;`, UTF-8 sem BOM, quebra de linha
     LF — o mesmo formato de `corpus_rsl.csv` e `execucao_busca.csv`):
       - CAPES_candidatos_<data>.csv       — um registro por trabalho com match
       - CAPES_execucao_por_string_<data>.csv — um N por string, para colar em
         `execucao_busca.csv` (uma linha por string, não por base — é a regra
         do protocolo).

Uso:
    pip install openpyxl
    python rsl1_capes_baixar_e_filtrar.py --dest "C:\\...\\doutorado\\03 - Dados\\_data\\CAPES" --out "C:\\...\\doutorado\\06 - Acadêmico\\...\\RSL..."

  --dest   pasta onde os 4 XLSX brutos ficam salvos. Recomendado: dentro de
           `03 - Dados/_data/` — é onde o cofre já guarda dado bruto externo
           volumoso, e essa pasta NÃO é versionada no git (ver .gitignore).
  --out    pasta onde os dois CSVs de resultado são salvos. Recomendado: a
           pasta da RSL (a nova, se a reestruturação já tiver sido feita).
  --anos   subconjunto de anos a processar (default: todos). Ex.: --anos 2023 2024
  --so-baixar   baixa os XLSX e para — não roda o filtro (útil para separar as
           duas etapas, já que o download de ~645 MB pode demorar).
  --so-filtrar  pula o download e assume que os XLSX já estão em --dest.

Ambos os CSVs de saída são candidatos A TRIAR — nenhum entra em `corpus_rsl.csv`
sem leitura e sem passar pelos filtros 1 e 2 do protocolo.
"""

import argparse
import csv
import io
import os
import re
import ssl
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import date

# ---------------------------------------------------------------------------
# 1. Os 4 recursos (confirmados via CKAN package_show em 09-09-2026)
# ---------------------------------------------------------------------------

RECURSOS = [
    {
        "ano": 2021,
        "url": "https://dadosabertos.capes.gov.br/dataset/dbb9b83e-7779-4b99-89d2-1ff8099f36f6/resource/1dfdb53a-543d-4834-97e2-27df8cb8d83a/download/br-capes-btd-2021-2025-03-31.xlsx",
        "arquivo": "br-capes-btd-2021-2025-03-31.xlsx",
        "tamanho_esperado": 152425037,
    },
    {
        "ano": 2022,
        "url": "https://dadosabertos.capes.gov.br/dataset/dbb9b83e-7779-4b99-89d2-1ff8099f36f6/resource/5aabb7a7-33ab-47b2-8b24-3e6765102f02/download/br-capes-btd-2022-2025-03-31.xlsx",
        "arquivo": "br-capes-btd-2022-2025-03-31.xlsx",
        "tamanho_esperado": 155092109,
    },
    {
        "ano": 2023,
        "url": "https://dadosabertos.capes.gov.br/dataset/dbb9b83e-7779-4b99-89d2-1ff8099f36f6/resource/bb0e4a57-ea99-49e1-a859-36391f541797/download/br-capes-btd-2023-2025-03-31.xlsx",
        "arquivo": "br-capes-btd-2023-2025-03-31.xlsx",
        "tamanho_esperado": 168690508,
    },
    {
        "ano": 2024,
        "url": "https://dadosabertos.capes.gov.br/dataset/dbb9b83e-7779-4b99-89d2-1ff8099f36f6/resource/4af59c52-78b3-450a-9167-bbc8b6c17808/download/br-capes-btd-2024-2025-12-01.xlsx",
        "arquivo": "br-capes-btd-2024-2025-12-01.xlsx",
        "tamanho_esperado": 168709069,
    },
]

# Colunas a varrer (nomes exatos do cabeçalho CAPES — conferidos via
# datastore_search em 09-09-2026). O script falha alto se alguma faltar,
# em vez de varrer campo errado silenciosamente.
CAMPOS_ALVO = [
    "NM_PRODUCAO",       # título
    "DS_RESUMO",         # resumo em português
    "DS_ABSTRACT",       # resumo em inglês
    "DS_PALAVRA_CHAVE",  # palavras-chave em português
    "DS_KEYWORD",        # palavras-chave em inglês
]

# Colunas de identificação levadas para o CSV de candidatos
CAMPOS_ID = [
    "NM_SUBTIPO_PRODUCAO", "NM_PROGRAMA", "NM_ENTIDADE_ENSINO",
    "NM_GRANDE_AREA_CONHECIMENTO", "NM_AREA_CONHECIMENTO",
    "NM_PRODUCAO", "NM_DISCENTE", "NM_ORIENTADOR", "DT_TITULACAO",
    "DS_URL_TEXTO_COMPLETO", "ID_PRODUCAO_INTELECTUAL",
]

# ---------------------------------------------------------------------------
# 2. Expressões de busca — Blocos A-E de
#    "Expressões de busca do RSL1 — conjunto a executar (03-09-2026)"
#    Cada padrão é (bloco, string_legivel, tipo, dado)
#      tipo "frase"       -> substring simples, apos normalizacao
#      tipo "prefixo"     -> regex de prefixo (equivalente ao curinga do Solr)
#      tipo "proximidade" -> duas palavras a ate N tokens de distancia
#      tipo "cooc"        -> duas palavras em qualquer lugar do mesmo campo
# ---------------------------------------------------------------------------

PADROES = [
    # --- Bloco A: nucleo, gratuidade total, portugues (alimenta o corpus) ---
    ("A", '"tarifa zero"', "frase", "tarifa zero"),
    ("A", '"passe livre"', "frase", "passe livre"),
    ("A", '"transporte gratuito"~2', "proximidade", ("transporte", "gratuito", 2)),
    ("A", '"isencao de tarifa"', "frase", "isencao de tarifa"),
    ("A", '"isencao tarifaria"', "frase", "isencao tarifaria"),
    ("A", '"gratuidade universal"', "frase", "gratuidade universal"),
    ("A", '"gratuidade total"', "frase", "gratuidade total"),
    ("A", '"gratuidade tarifaria"', "frase", "gratuidade tarifaria"),
    ("A", '"transporte sem cobranca"', "frase", "transporte sem cobranca"),
    ("A", "catraca(s)", "frase", "catraca"),
    ("A", '"sem catraca"', "frase", "sem catraca"),
    ("A", "destarifa*", "prefixo", r"\bdestarifa\w*"),

    # --- Bloco B: ingles (nao opcional numa base brasileira) ---
    ("B", '"fare-free"', "frase", "fare-free"),
    ("B", '"free public transport"', "frase", "free public transport"),
    ("B", '"free public transportation"', "frase", "free public transportation"),
    ("B", '"zero fare"', "frase", "zero fare"),
    ("B", '"zero tariff"', "frase", "zero tariff"),
    ("B", '"free fare"', "frase", "free fare"),
    ("B", '"free transit"', "frase", "free transit"),
    ("B", '"fare abolition"', "frase", "fare abolition"),

    # --- Bloco C: nomes de programa e de camada ---
    ("C", "vermelhinho(s)", "frase", "vermelhinho"),
    ("C", '"busao 0800"', "frase", "busao 0800"),
    ("C", '"domingo tarifa zero"', "frase", "domingo tarifa zero"),
    ("C", '"tarifa zero de domingo"', "frase", "tarifa zero de domingo"),
    ("C", '"passe livre estudantil"', "frase", "passe livre estudantil"),
    ("C", '"passe livre eleitoral"', "frase", "passe livre eleitoral"),

    # --- Bloco D: movimento (NAO alimenta o corpus - so o denominador) ---
    ("D", '"movimento passe livre"', "frase", "movimento passe livre"),
    ("D", '"movimento tarifa zero"', "frase", "movimento tarifa zero"),
    ("D", '"revolta tarifaria"', "frase", "revolta tarifaria"),
    ("D", '"jornadas de junho"', "frase", "jornadas de junho"),
    ("D", '"junho de 2013"', "frase", "junho de 2013"),

    # --- Bloco E: financiamento (exploratorio - vai a referencial, nao ao corpus) ---
    ("E", '"vale-transporte"', "frase", "vale-transporte"),
    ("E", '"subsidio tarifario"', "frase", "subsidio tarifario"),
    ("E", '"subsidio ao transporte"', "frase", "subsidio ao transporte"),
    ("E", '"versement transport"', "frase", "versement transport"),
    ("E", '"producao quilometrica"', "frase", "producao quilometrica"),
    ("E", '"remuneracao por quilometro"', "frase", "remuneracao por quilometro"),
    ("E", '"contribuicao para disponibilizacao"', "frase", "contribuicao para disponibilizacao"),
    ("E", "CIDE AND transporte", "cooc", ("cide", "transporte")),
    # atencao: "gratuidades" (plural) e outro objeto (isencoes estatutarias -
    # idoso, estudante, PCD). Fica em estrato proprio, nunca somado ao corpus.
    ("E", "gratuidades (estrato proprio - NAO somar ao corpus)", "frase", "gratuidades"),
]


def normalizar(texto):
    """minusculas, sem acento - mesma normalizacao usada no restante da RSL."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sem_acento.lower()


def compilar_padroes():
    compilados = []
    for bloco, legivel, tipo, dado in PADROES:
        if tipo == "frase":
            compilados.append((bloco, legivel, tipo, normalizar(dado)))
        elif tipo == "prefixo":
            compilados.append((bloco, legivel, tipo, re.compile(dado)))
        elif tipo == "proximidade":
            a, b, n = dado
            compilados.append((bloco, legivel, tipo, (normalizar(a), normalizar(b), n)))
        elif tipo == "cooc":
            a, b = dado
            compilados.append((bloco, legivel, tipo, (normalizar(a), normalizar(b))))
        else:
            raise ValueError(f"tipo de padrao desconhecido: {tipo}")
    return compilados


def casa(padrao_compilado, texto_norm, tokens):
    bloco, legivel, tipo, dado = padrao_compilado
    if tipo == "frase":
        return dado in texto_norm
    if tipo == "prefixo":
        return bool(dado.search(texto_norm))
    if tipo == "proximidade":
        a, b, n = dado
        pos_a = [i for i, t in enumerate(tokens) if t == a]
        pos_b = [i for i, t in enumerate(tokens) if t == b]
        return any(abs(i - j) <= n for i in pos_a for j in pos_b)
    if tipo == "cooc":
        a, b = dado
        return a in texto_norm and b in texto_norm
    return False


JANELA_TRECHO = 150  # caracteres de contexto para cada lado do match, no CSV de candidatos

def extrair_trecho(padrao_compilado, valor_original, texto_norm, tokens, janela=JANELA_TRECHO):
    """Recorta um trecho do campo original em torno do ponto onde o padrao
    casou - e o que faltava no CSV de candidatos ate 09-09-2026: ele so
    registrava QUAL campo bateu (campos_com_match), nunca o TEXTO que bateu.
    Isso tornava a "triagem por titulo e resumo" (protocolo, Sec 9, passo 3)
    impossivel de fato para os candidatos que so bateram por resumo/palavra-
    chave (807 dos 863 candidatos da rodada de 09-09-2026) - o resumo/keyword
    em si nunca aparecia em lugar nenhum do CSV, so no XLSX de 150-170 MB de
    origem. Aproximacao: a posicao e achada no texto NORMALIZADO (sem acento)
    e a mesma janela de indices e aplicada ao texto ORIGINAL - valido na
    pratica para PT/EN porque a normalizacao NFKD + remocao de combining
    marks preserva o comprimento em caracteres na esmagadora maioria dos
    casos (cada letra acentuada vira 1 caractere solto, nao uma string maior)."""
    bloco, legivel, tipo, dado = padrao_compilado
    pos = None
    if tipo == "frase":
        pos = texto_norm.find(dado)
    elif tipo == "prefixo":
        m = dado.search(texto_norm)
        pos = m.start() if m else None
    elif tipo == "proximidade":
        a, b, n = dado
        pos_a = [i for i, t in enumerate(tokens) if t == a]
        pos_b = [i for i, t in enumerate(tokens) if t == b]
        melhor = None
        for i in pos_a:
            for j in pos_b:
                if abs(i - j) <= n and (melhor is None or abs(i - j) < melhor[0]):
                    melhor = (abs(i - j), min(i, j))
        if melhor:
            pos = texto_norm.find(tokens[melhor[1]])
    elif tipo == "cooc":
        a, b = dado
        candidatos_pos = [p for p in (texto_norm.find(a), texto_norm.find(b)) if p >= 0]
        pos = min(candidatos_pos) if candidatos_pos else None

    if pos is None or pos < 0:
        pos = 0
    ini = max(0, pos - janela)
    fim = min(len(valor_original), pos + janela)
    trecho = valor_original[ini:fim].replace("\n", " ").replace("\r", " ").replace(";", ",").strip()
    return f"{'…' if ini > 0 else ''}{trecho}{'…' if fim < len(valor_original) else ''}"


# ---------------------------------------------------------------------------
# 3. Download idempotente
# ---------------------------------------------------------------------------

def instalar_contexto_ssl_robusto():
    """Alguns Windows corporativos (antivirus/proxy com inspecao de TLS) fazem
    o contexto SSL padrao do Python falhar com CERTIFICATE_VERIFY_FAILED mesmo
    quando o certificado do site e valido - o Python nao enxerga a cadeia
    completa. Isso tem duas causas possiveis, e cada uma pede um remedio
    diferente:
      (a) o Python nao consegue ler o armazem de certificados do SO onde a
          cadeia legitima esta - o bundle da `certifi` (Mozilla) resolve;
      (b) ha uma CA corporativa própria no meio da cadeia (antivirus ou proxy
          fazendo inspecao de TLS) - essa CA esta instalada no Windows, mas
          NUNCA vai estar no bundle da certifi (que so tem CAs publicas). Ai
          o unico remedio e usar a API nativa do SO para validar, via
          `truststore` (pacote da propria PyPA para este caso exato).
    Tenta, nesta ordem: truststore -> certifi -> padrao do sistema.
    Instala um opener global para urllib - afeta so este processo."""
    contexto = None
    origem = "padrao do sistema"
    try:
        import truststore
        truststore.inject_into_ssl()
        contexto = ssl.create_default_context()
        origem = "truststore (verificacao nativa do SO - cobre CA corporativa/antivirus)"
    except ImportError:
        try:
            import certifi
            contexto = ssl.create_default_context(cafile=certifi.where())
            origem = f"certifi ({certifi.where()})"
        except ImportError:
            contexto = ssl.create_default_context()

    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=contexto))
    urllib.request.install_opener(opener)
    print(f"[ssl] contexto de verificacao: {origem}")


MAX_TENTATIVAS = 6  # cada uma retoma de onde a anterior parou (Range) - nao reinicia do zero

def _tamanho_atual(tmp):
    return os.path.getsize(tmp) if os.path.exists(tmp) else 0


def baixar(recurso, dest_dir):
    destino = os.path.join(dest_dir, recurso["arquivo"])
    esperado = recurso["tamanho_esperado"]

    if os.path.exists(destino) and os.path.getsize(destino) == esperado:
        print(f"[{recurso['ano']}] ja baixado e completo ({esperado/1e6:.0f} MB) - pulando")
        return destino

    tmp = destino + ".part"
    print(f"[{recurso['ano']}] baixando {recurso['arquivo']} ({esperado/1e6:.0f} MB esperados)...")

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        ja_tenho = _tamanho_atual(tmp)
        if ja_tenho >= esperado:
            break  # o .part de uma tentativa anterior ja completou o arquivo

        req = urllib.request.Request(recurso["url"])
        modo_retomada = ja_tenho > 0
        if modo_retomada:
            req.add_header("Range", f"bytes={ja_tenho}-")
            print(f"  [tentativa {tentativa}/{MAX_TENTATIVAS}] retomando de {ja_tenho/1e6:.0f} MB "
                  f"({ja_tenho*100/esperado:.1f}% ja salvo)...")
        elif tentativa > 1:
            print(f"  [tentativa {tentativa}/{MAX_TENTATIVAS}] recomecando do zero...")

        inicio = time.time()
        baixado_nesta_tentativa = 0
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                # Se pedimos Range e o servidor devolveu 200 (nao 206), ele nao
                # suporta retomada - o corpo eh o arquivo inteiro de novo, entao
                # descartamos o .part parcial e comecamos este corpo do zero.
                aceita_range = resp.status == 206
                if modo_retomada and not aceita_range:
                    print("  [aviso] servidor nao devolveu 206 (Partial Content) - "
                          "nao suporta retomada; reiniciando este arquivo do zero.")
                    ja_tenho = 0
                modo_escrita = "ab" if (modo_retomada and aceita_range) else "wb"
                with open(tmp, modo_escrita) as f:
                    while True:
                        bloco = resp.read(1024 * 256)
                        if not bloco:
                            break
                        f.write(bloco)
                        baixado_nesta_tentativa += len(bloco)
                        total_no_disco = ja_tenho + baixado_nesta_tentativa
                        pct = min(100, total_no_disco * 100 / esperado)
                        velocidade = baixado_nesta_tentativa / max(time.time() - inicio, 0.001) / 1e6
                        sys.stdout.write(f"\r  {pct:5.1f}%  ({total_no_disco/1e6:.0f}/{esperado/1e6:.0f} MB, "
                                          f"{velocidade:.1f} MB/s)")
                        sys.stdout.flush()
            print()
        except Exception as e:
            print(f"\n  [tentativa {tentativa}/{MAX_TENTATIVAS}] FALHOU: {e}")
            if tentativa == MAX_TENTATIVAS:
                print(f"[{recurso['ano']}] desistindo apos {MAX_TENTATIVAS} tentativas. "
                      f"O arquivo parcial ficou em {tmp} ({_tamanho_atual(tmp)/1e6:.0f} MB) - "
                      f"rode o script de novo mais tarde, ele retoma dai.")
                raise
            espera = min(30, 2 ** tentativa)
            print(f"  aguardando {espera}s antes de tentar de novo (retoma do que ja baixou)...")
            time.sleep(espera)

    tamanho_real = os.path.getsize(tmp)
    if tamanho_real < esperado:
        # BUG corrigido em 09-09-2026: o loop de tentativas so verificava
        # `ja_tenho >= esperado` no INICIO de cada iteracao. Se uma tentativa
        # terminasse "limpa" (resp.read() devolveu vazio = EOF) mas curta -
        # o que acontece quando um proxy/antivirus corporativo encerra a
        # conexao no meio de um download longo sem lancar excecao Python -,
        # o for simplesmente esgotava as tentativas e o codigo seguia como
        # se tivesse dado certo, so avisando no log. O arquivo truncado virava
        # o "destino" final e quebrava no openpyxl (BadZipFile) na hora de
        # filtrar - depois de already ter baixado os outros anos, e depois de
        # ja ter gasto o tempo de filtragem dos anos anteriores (perdido, pois
        # o CSV de saida so e gravado no final do main()).
        # Agora: tamanho menor que o esperado apos esgotar as tentativas e
        # ERRO explicito, nao aviso - e o .part fica no disco (nao vira
        # "destino") para a proxima chamada retomar/reiniciar sozinha.
        raise RuntimeError(
            f"[{recurso['ano']}] download incompleto apos {MAX_TENTATIVAS} tentativas: "
            f"{tamanho_real} de {esperado} bytes esperados ({tamanho_real*100/esperado:.1f}%). "
            f"O servidor da CAPES parece encerrar a conexao antes do fim (nao e erro de rede "
            f"transiente comum, senao a excecao teria sido pega e contado como tentativa). "
            f"O arquivo parcial ficou em {tmp} - rode o script de novo, ele detecta que "
            f"'{os.path.basename(destino)}' ainda nao existe com o tamanho certo e tenta de novo."
        )
    if tamanho_real > esperado:
        print(f"[{recurso['ano']}] AVISO: tamanho baixado ({tamanho_real} B) e MAIOR que o "
              f"esperado ({esperado} B) - o arquivo publicado pela CAPES deve ter crescido "
              f"desde 09-09-2026. Seguindo mesmo assim; registre isso na nota de execucao.")
    os.replace(tmp, destino)
    return destino


# ---------------------------------------------------------------------------
# 4. Filtro local
# ---------------------------------------------------------------------------

def filtrar_arquivo(caminho_xlsx, ano, padroes, contagem_por_string, candidatos_out):
    try:
        import openpyxl
    except ImportError:
        sys.exit("ERRO: openpyxl nao esta instalado. Rode: pip install openpyxl")

    print(f"[{ano}] abrindo {os.path.basename(caminho_xlsx)} (modo streaming)...")
    wb = openpyxl.load_workbook(caminho_xlsx, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]

    linhas = ws.iter_rows(values_only=True)
    cabecalho = next(linhas)
    idx = {}
    for nome in CAMPOS_ALVO + CAMPOS_ID:
        if nome not in cabecalho:
            sys.exit(f"ERRO [{ano}]: coluna esperada '{nome}' nao encontrada no cabecalho. "
                      f"O layout do CAPES pode ter mudado - conferir manualmente antes de prosseguir.")
        idx[nome] = cabecalho.index(nome)

    n_lidas = 0
    n_com_match = 0
    t0 = time.time()

    for linha in linhas:
        n_lidas += 1
        if n_lidas % 200000 == 0:
            print(f"  ... {n_lidas} linhas lidas ({time.time()-t0:.0f}s)")

        matches_desta_linha = []  # (bloco, legivel, campo, trecho)
        for campo in CAMPOS_ALVO:
            valor = linha[idx[campo]]
            if not valor:
                continue
            valor_str = str(valor)
            texto_norm = normalizar(valor_str)
            tokens = texto_norm.split()
            for p in padroes:
                if casa(p, texto_norm, tokens):
                    bloco, legivel = p[0], p[1]
                    trecho = extrair_trecho(p, valor_str, texto_norm, tokens)
                    matches_desta_linha.append((bloco, legivel, campo, trecho))
                    contagem_por_string[(ano, bloco, legivel)] = contagem_por_string.get((ano, bloco, legivel), 0) + 1

        if matches_desta_linha:
            n_com_match += 1
            blocos_e_strings = ", ".join(f"{b}:{s}" for b, s, _, _ in matches_desta_linha)
            campos = ", ".join(sorted(set(c for _, _, c, _ in matches_desta_linha)))
            # um trecho por (campo, string) - e a evidencia que faltava para a
            # triagem por titulo e resumo (protocolo Sec 9, passo 3) sem ter
            # que reabrir o XLSX de 150-170 MB para cada candidato.
            trechos = " | ".join(f"{c}[{s}]: {t}" for _, s, c, t in matches_desta_linha)
            linha_saida = {"ano": ano, "blocos_e_strings": blocos_e_strings,
                            "campos_com_match": campos, "trechos": trechos}
            for nome in CAMPOS_ID:
                linha_saida[nome] = linha[idx[nome]]
            candidatos_out.append(linha_saida)

    wb.close()
    print(f"[{ano}] {n_lidas} linhas lidas, {n_com_match} com pelo menos um match "
          f"({time.time()-t0:.0f}s)")


def gravar_csv_validado(caminho, linhas, campos):
    """Grava em io.StringIO, reparse e so entao escreve o destino -
    evita truncar o arquivo antes de descobrir um erro (regra do cofre)."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=campos, delimiter=";", lineterminator="\n")
    w.writeheader()
    w.writerows(linhas)
    texto = buf.getvalue()
    checagem = list(csv.reader(io.StringIO(texto), delimiter=";"))
    tamanhos = {len(r) for r in checagem}
    assert len(tamanhos) == 1, f"CSV desalinhado: tamanhos de linha {tamanhos}"
    assert len(checagem) == len(linhas) + 1, "numero de linhas nao bate apos reparse"
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        f.write(texto)


# ---------------------------------------------------------------------------
# 5. main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", required=True, help="pasta para os 4 XLSX brutos (recomendado: 03 - Dados/_data/CAPES)")
    ap.add_argument("--out", required=True, help="pasta para os CSVs de resultado (recomendado: a pasta da RSL)")
    ap.add_argument("--anos", nargs="*", type=int, default=None, help="subconjunto de anos, ex.: --anos 2023 2024")
    ap.add_argument("--so-baixar", action="store_true", help="so baixa os XLSX, nao filtra")
    ap.add_argument("--so-filtrar", action="store_true", help="pula o download, assume XLSX ja em --dest")
    args = ap.parse_args()

    os.makedirs(args.dest, exist_ok=True)
    os.makedirs(args.out, exist_ok=True)

    recursos = [r for r in RECURSOS if args.anos is None or r["ano"] in args.anos]
    if not recursos:
        sys.exit("nenhum recurso selecionado - conferir --anos")

    caminhos = {}
    anos_falhos_download = []
    if not args.so_filtrar:
        instalar_contexto_ssl_robusto()
        for r in recursos:
            try:
                caminhos[r["ano"]] = baixar(r, args.dest)
            except Exception as e:
                if isinstance(e, urllib.error.URLError) and "CERTIFICATE_VERIFY_FAILED" in str(e):
                    sys.exit(
                        "\nFalha de certificado SSL mesmo com truststore/certifi tentados.\n"
                        "Isto e quase certamente uma CA corporativa (antivirus ou proxy com\n"
                        "inspecao de TLS) que nem o Windows original nem a certifi conhecem\n"
                        "pelo nome que este processo Python esta enxergando.\n"
                        "Rode NA ORDEM e tente de novo apos cada passo:\n"
                        "  1) pip install truststore   (se ainda nao esta instalado - confira\n"
                        "     a primeira linha impressa acima: deve dizer '[ssl] contexto de\n"
                        "     verificacao: truststore (...)'; se disser 'certifi' ou 'padrao\n"
                        "     do sistema', o pacote nao foi encontrado - instale e rode de novo)\n"
                        "  2) pip install pip-system-certs\n"
                        "  3) Se nada disso resolver: pergunte ao TI se ha um proxy/antivirus\n"
                        "     com inspecao de TLS (Kaspersky, ESET, Zscaler, Netskope, etc.) e\n"
                        "     peca o certificado raiz dele em .cer/.pem para eu apontar o\n"
                        "     script direto pra ele.\n"
                    )
                # Download de UM ano falhou (ex.: truncamento repetido pelo
                # servidor - ver o RuntimeError em baixar()). Antes isso
                # abortava o script inteiro, inclusive os anos seguintes que
                # nem tinham sido tentados ainda. Agora: registra e segue para
                # o proximo ano - filtragem roda com o que baixou de verdade.
                print(f"\n[{r['ano']}] FALHA NO DOWNLOAD - pulando este ano: {e}\n")
                anos_falhos_download.append(r["ano"])
    else:
        for r in recursos:
            caminho = os.path.join(args.dest, r["arquivo"])
            if not os.path.exists(caminho):
                sys.exit(f"--so-filtrar pedido mas {caminho} nao existe")
            caminhos[r["ano"]] = caminho

    if args.so_baixar:
        print("Download concluido (--so-baixar). Encerrando sem filtrar.")
        return

    padroes = compilar_padroes()
    contagem_por_string = {}
    candidatos = []
    anos_falhos_filtro = []

    # Cada ano e filtrado isoladamente: um XLSX corrompido/inesperado em UM
    # ano (crash do openpyxl, coluna faltando etc.) nao pode mais derrubar o
    # processo inteiro e jogar fora o trabalho ja feito nos anos anteriores -
    # foi exatamente isso que aconteceu em 09-09-2026 (2021 e 2022 filtrados
    # com sucesso, ~15 min de processamento, descartados porque 2023 quebrou
    # antes de qualquer CSV ser gravado). Agora: registra o erro, segue para
    # o proximo ano, e grava no final o que deu certo.
    for r in recursos:
        if r["ano"] not in caminhos:
            continue  # download deste ano falhou - ja registrado acima
        try:
            filtrar_arquivo(caminhos[r["ano"]], r["ano"], padroes, contagem_por_string, candidatos)
        except Exception as e:
            print(f"\n[{r['ano']}] FALHA AO FILTRAR - pulando este ano: {e}\n")
            anos_falhos_filtro.append(r["ano"])

    anos_ok = [r["ano"] for r in recursos if r["ano"] not in anos_falhos_download and r["ano"] not in anos_falhos_filtro]
    recursos_ok = [r for r in recursos if r["ano"] in anos_ok]

    hoje = date.today().isoformat()

    # --- CSV 1: candidatos (um por trabalho com match) ---
    campos_candidatos = ["ano", "blocos_e_strings", "campos_com_match", "trechos"] + CAMPOS_ID
    caminho_candidatos = os.path.join(args.out, f"CAPES_candidatos_{hoje}.csv")
    gravar_csv_validado(caminho_candidatos, candidatos, campos_candidatos)
    print(f"\nGravado: {caminho_candidatos}  ({len(candidatos)} candidatos)")

    # --- CSV 2: execucao por string (para colar em execucao_busca.csv) ---
    linhas_execucao = []
    for r in recursos_ok:
        for bloco, legivel, tipo, dado in PADROES:
            n = contagem_por_string.get((r["ano"], bloco, legivel), 0)
            linhas_execucao.append({
                "data": hoje, "estrato": "RSL1",
                "base": f"Catalogo de Teses CAPES - XLSX {r['ano']} (dados abertos, local)",
                "string": legivel, "bloco": bloco,
                "filtro_data": "sem recorte", "n_resultados": n,
            })
    campos_execucao = ["data", "estrato", "base", "string", "bloco", "filtro_data", "n_resultados"]
    caminho_execucao = os.path.join(args.out, f"CAPES_execucao_por_string_{hoje}.csv")
    gravar_csv_validado(caminho_execucao, linhas_execucao, campos_execucao)
    print(f"Gravado: {caminho_execucao}  ({len(linhas_execucao)} linhas - uma por string x ano)")

    print("\nPROXIMO PASSO: nenhum destes candidatos entra em corpus_rsl.csv sem leitura "
          "e sem passar pelos filtros 1 e 2 do protocolo. O CSV de execucao por string "
          "pode ser colado em execucao_busca.csv (mesmas colunas-nucleo).")

    anos_falhos = sorted(set(anos_falhos_download) | set(anos_falhos_filtro))
    if anos_falhos:
        print(f"\n⚠️  ANOS NAO PROCESSADOS: {anos_falhos} - os CSVs acima cobrem so "
              f"{sorted(anos_ok)}. Rode de novo so para os anos que faltaram, ex.:\n"
              f"  python {os.path.basename(__file__)} --dest \"{args.dest}\" --out \"{args.out}\" "
              f"--anos {' '.join(str(a) for a in anos_falhos)}\n"
              f"(os anos que ja baixaram certo nao sao rebaixados - o script pula quem ja "
              f"esta completo) e depois una manualmente os dois pares de CSV de saida "
              f"(candidatos e execucao_por_string) antes de colar em execucao_busca.csv.")
        sys.exit(1)


if __name__ == "__main__":
    main()
