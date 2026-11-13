#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buscar_querido_diario.py

Busca legislação de Tarifa Zero nos DIÁRIOS OFICIAIS municipais indexados pelo
Querido Diário (Open Knowledge Brasil) — API pública, sem bloqueio de bot
(diferente de leismunicipais.com.br e legislacaodigital.com.br, que retornam
HTTP 403 para acesso automatizado).

Documentação da API: https://docs.queridodiario.ok.org.br/pt-br/latest/utilizando/api-publica.html
Base: https://api.queridodiario.org.br/gazettes

⚠️ 11/09/2026: o domínio antigo `api.queridodiario.ok.org.br` (usado nas duas
primeiras versões deste script e ainda citado na documentação oficial acima)
está DESATIVADO — não serve mais a API, e por isso qualquer cliente TLS
(Python/OpenSSL, curl/schannel, Chrome/BoringSSL) falha o handshake contra
ele por igual. O domínio correto e ativo é `api.queridodiario.org.br` (sem o
"ok."), confirmado via o pacote `querido-diario-mcp-server` (PyPI), cuja
variável QD_API_BASE_URL usa esse endereço como padrão de produção.

DOIS MODOS:

1. Modo padrão (sem --nacional) — varre só os municípios que ainda faltam na
   nossa base (lidos ao vivo do "Controle único...csv"): `estado` começando em
   "B1" (número declarado, texto a obter — 63 casos) ou "C" (nada localizado —
   62 casos). Total ~125. Um `territory_ids` por chamada.

2. Modo --nacional — busca CADA TERMO EM TODO O BRASIL de uma vez (sem
   `territory_ids`, que é opcional na API — omitir busca em todos os
   municípios indexados), paginando via `offset` até um teto de segurança.
   Serve para achar TZ em municípios que NEM ESTÃO na nossa base de 176 casos
   ainda — não só preencher lacuna de caso conhecido, achar caso novo.
   Agrega os resultados por município e marca quais já estão na base (cod_ibge
   no Controle único) e quais são achado NOVO, fora dos 176.

   ⚠️ Os nomes de campo da resposta (territory_id, territory_name, etc.) não
   estão 100% documentados publicamente — o script tenta várias chaves
   plausíveis e, se não achar nenhuma, imprime o JSON bruto do 1º resultado
   para ajuste manual (mesmo princípio de "ver o .json" usado em
   buscar_texto_normas_sapl.py quando os campos não batem o esperado).

O Querido Diário não cobre 100% dos municípios/anos — a ausência de resultado
aqui não é prova de ausência da lei, é ausência de cobertura OU ausência de
achado; o script registra qual dos dois quando possível.

Uso:
    conda activate <seu_ambiente>          # precisa de: pandas, requests
    cd caminho\\para\\_meta\\scripts
    python buscar_querido_diario.py                 # modo padrão, ~125 municípios
    python buscar_querido_diario.py --nacional       # modo nacional, todo o Brasil

Saída (modo padrão): saida_querido_diario/resumo.csv + um .json por município.
Saída (modo --nacional): saida_querido_diario/nacional/resumo_nacional.csv
(um município por linha, com "ja_na_base" True/False) + um .json por termo.

Autor: Thiago Von Zeidler Gomes
Orientadora: Prof.ª Silvana Zioni
"""

import argparse
import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

API_BASE = "https://api.queridodiario.org.br/gazettes"

_SESSION = requests.Session()


def get_com_fallback_ssl(url: str, params: dict, timeout: int):
    """Nome mantido por compatibilidade com o resto do script; o fallback de
    TLS que existia aqui (SECLEVEL=1) foi removido em 11/09/2026 — o erro de
    SSL nunca foi um problema de cifra, era o domínio errado (ver nota no
    topo do arquivo). Chamada simples agora."""
    return _SESSION.get(url, params=params, timeout=timeout)


def chamar_com_retentativas(func_chamada, tentativas: int = 5, espera_base: float = 5.0):
    """Roda `func_chamada()` (uma função sem argumentos que faz a chamada
    HTTP e devolve o .json()). Em erro TRANSITÓRIO — timeout, erro de
    conexão, ou qualquer HTTP 429 ou 5xx (502/503/504, mas também os "erro
    de origem" do Cloudflare como 520/521/522/523/524/526, que não têm
    número fixo) — tenta de novo com espera crescente (5s, 10s, 20s, 40s...)
    antes de desistir. Qualquer erro 4xx que não seja 429 (ex.: 400 por
    parâmetro inválido) sobe na hora, sem retentativa, porque repetir não
    vai resolver.

    11/09/2026: primeira rodada nacional bateu timeout + 503 em cadeia (API
    sobrecarregada/instável); a rodada seguinte, já com retentativa em
    429/502/503/504, ainda tropeçou porque um 520 (Cloudflare, "erro
    desconhecido" do servidor de origem) apareceu e não estava coberto —
    daí o critério ter virado "qualquer 5xx", não uma lista fixa de
    códigos."""
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            return func_chamada()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            ultimo_erro = e
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status == 429 or (status is not None and 500 <= status < 600):
                ultimo_erro = e
            else:
                raise
        if tentativa < tentativas:
            espera = espera_base * (2 ** (tentativa - 1))
            print(f"      ⏳ tentativa {tentativa}/{tentativas} falhou "
                  f"({type(ultimo_erro).__name__}: {ultimo_erro}); "
                  f"esperando {espera:.0f}s e tentando de novo...")
            time.sleep(espera)
    raise ultimo_erro

# Termos fortes de Tarifa Zero — cada um é uma chamada separada à API (a
# querystring do Querido Diário busca frase/termo, não múltiplos OR).
TERMOS = [
    "tarifa zero",
    "passe livre",
    "transporte coletivo gratuito",
    "transporte gratuito",
    "gratuidade tarifária",
    "subsídio tarifário",
]

CAMINHO_CONTROLE = (
    Path(__file__).resolve().parent.parent.parent
    / "03 - Dados" / "_data" / "Legislacao e contratos TZ"
    / "_historico" / "Controle unico - legislacao PlanMob e contratos, 176 casos (2026-09-11).csv"
)


def normalizar(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).strip()


def bate_frase_exata(termo: str, gazette: dict) -> bool:
    """Confirma que a FRASE do termo aparece de fato, contígua, no(s)
    excerto(s) do diário retornado — não basta a API tê-lo devolvido.

    Bug encontrado em 20/09/2026: a busca nacional trata `querystring` como
    relevância frouxa (tipo OR de palavras/stems), não frase exata — ao
    contrário do sapl_varredura.py, que sempre refiltra no cliente exigindo
    a frase contígua. Reprocessando os 15.000 registros brutos da rodada de
    5 termos refinados de 19-20/09/2026 (447 municípios "batidos"), só 3
    registros / 2 municípios tinham a frase de fato no excerto — o resto
    eram falsos positivos (ex.: 'institui o programa tarifa zero' batendo em
    editais culturais e normas de ICP-Brasil sem nenhuma relação com TZ).
    Esta função fecha esse buraco: só entra no resumo quem passa aqui.
    """
    alvo = re.sub(r"\s+", " ", normalizar(termo).lower()).strip()
    if not alvo:
        return False
    texto = " ".join(gazette.get("excerpts", []) or [])
    texto = re.sub(r"\s+", " ", normalizar(texto).lower())
    return alvo in texto


def montar_alvos(filtro: Optional[str], municipios_arquivo: Optional[str] = None) -> pd.DataFrame:
    if not CAMINHO_CONTROLE.exists():
        raise SystemExit(
            f"Não achei o Controle único em:\n  {CAMINHO_CONTROLE}\n"
            "Ajuste CAMINHO_CONTROLE no topo do script se o arquivo estiver "
            "em outro lugar (ex.: se a data no nome do arquivo mudou)."
        )
    df = pd.read_csv(CAMINHO_CONTROLE, dtype={"cod_ibge": str})
    df["estado"] = df["estado"].astype(str)
    df["cod_ibge"] = df["cod_ibge"].str.strip()

    if municipios_arquivo:
        # Lista explícita de cod_ibge, IGNORA o campo "estado" por completo —
        # roda os municípios pedidos sejam eles B1, B2, C ou até A. Uso: retomar
        # uma lista de trabalho externa (ex.: os candidatos de uma rodada de
        # saneamento) sem depender de o Controle único já refletir o estado
        # certo para cada um.
        #
        # Desde 16/09/2026: se o arquivo já traz colunas "municipio" e "uf"
        # próprias (em vez de exigir que o cod_ibge exista no Controle
        # único), usa ESSAS para montar o alvo — permite buscar município
        # que nunca entrou na base dos 176 casos (ex.: candidatos novos de
        # uma rodada de saneamento por homônimo). O "estado" do Controle
        # único, quando existir, é só anexado a título de contexto no
        # resumo.csv; quando não existir, marca "FORA-DA-BASE".
        alvo_path = Path(municipios_arquivo)
        if not alvo_path.exists():
            raise SystemExit(f"--municipios-arquivo não encontrado: {alvo_path}")
        alvo_df = pd.read_csv(alvo_path, dtype=str)
        if "cod_ibge" not in alvo_df.columns:
            raise SystemExit(
                f"{alvo_path} precisa de uma coluna 'cod_ibge' (como "
                "alvo_pendentes_2026-09-16.csv)."
            )
        alvo_df["cod_ibge"] = alvo_df["cod_ibge"].str.strip()

        tem_nomes_proprios = "municipio" in alvo_df.columns and "uf" in alvo_df.columns

        if tem_nomes_proprios:
            alvo = alvo_df[["cod_ibge", "municipio", "uf"]].copy()
            alvo = alvo.merge(
                df[["cod_ibge", "estado"]].drop_duplicates("cod_ibge"),
                on="cod_ibge", how="left",
            )
            fora_da_base = alvo["estado"].isna()
            alvo.loc[fora_da_base, "estado"] = "FORA-DA-BASE (não consta no Controle único)"
            if fora_da_base.any():
                codigos_fora = sorted(alvo.loc[fora_da_base, "cod_ibge"])
                print(f"ℹ️  {len(codigos_fora)} cod_ibge de {alvo_path} não constam no "
                      f"Controle único (fora dos 176 casos) — buscando mesmo assim, "
                      f"com os nomes do próprio arquivo: {codigos_fora}")
        else:
            codigos = set(alvo_df["cod_ibge"])
            alvo = df[df["cod_ibge"].isin(codigos)].copy()
            achados = set(alvo["cod_ibge"])
            faltando = codigos - achados
            if faltando:
                print(f"⚠️  {len(faltando)} cod_ibge de {alvo_path} não bateram "
                      f"com o Controle único (fora da base de 176?) e o arquivo "
                      f"não tem colunas 'municipio'/'uf' para buscar mesmo assim "
                      f"(adicione-as para incluir município fora da base): "
                      f"{sorted(faltando)}")
        if filtro:
            print("⚠️  --filtro ignorado porque --municipios-arquivo foi "
                  "passado junto (a lista explícita manda).")
    elif filtro:
        alvo = df[df["estado"].str.startswith(filtro)].copy()
    else:
        alvo = df[df["estado"].str.startswith(("B1", "C"))].copy()

    alvo = alvo[alvo["cod_ibge"].notna() & (alvo["cod_ibge"] != "")]
    return alvo[["municipio", "uf", "cod_ibge", "estado"]].reset_index(drop=True)


def buscar_termo(territory_id: str, termo: str, tamanho: int = 10) -> dict:
    params = {
        "territory_ids": territory_id,
        "querystring": termo,
        "excerpt_size": 400,
        "number_of_excerpts": 2,
        "size": tamanho,
    }

    def chamada():
        r = get_com_fallback_ssl(API_BASE, params, timeout=45)
        r.raise_for_status()
        return r.json()

    return chamar_com_retentativas(chamada)


def buscar_pagina_nacional(termo: str, offset: int, tamanho: int) -> dict:
    """Busca SEM territory_ids — a API varre todos os municípios indexados."""
    params = {
        "querystring": termo,
        "excerpt_size": 400,
        "number_of_excerpts": 1,
        "size": tamanho,
        "offset": offset,
    }

    def chamada():
        r = get_com_fallback_ssl(API_BASE, params, timeout=45)
        r.raise_for_status()
        return r.json()

    return chamar_com_retentativas(chamada)


def extrair_territorio(gazette: dict) -> tuple:
    """Tenta várias chaves plausíveis para IBGE/nome do município na resposta.
    Retorna (ibge_ou_None, nome_ou_None, chaves_vistas_para_debug)."""
    ibge = (
        gazette.get("territory_id")
        or gazette.get("territory_ids")
        or gazette.get("territoryId")
        or gazette.get("ibge_code")
    )
    if isinstance(ibge, list):
        ibge = ibge[0] if ibge else None
    nome = (
        gazette.get("territory_name")
        or gazette.get("territoryName")
        or gazette.get("city")
        or gazette.get("municipio")
    )
    return (str(ibge) if ibge else None, nome, list(gazette.keys()))


def buscar_nacional(termo: str, teto: int, tamanho_pagina: int, pausa: float) -> list:
    """Pagina um termo em todo o Brasil até `teto` resultados ou esgotar."""
    achados = []
    offset = 0
    total_declarado = None
    debug_impresso = False

    while len(achados) < teto:
        try:
            resp = buscar_pagina_nacional(termo, offset, tamanho_pagina)
        except requests.RequestException as e:
            print(f"    🔴 erro em offset={offset}: {e}")
            break

        if total_declarado is None:
            total_declarado = resp.get("total_gazettes", resp.get("total", 0))
            print(f"    '{termo}': {total_declarado} diário(s) no Brasil todo "
                  f"(coletando até {teto}).")

        gazettes = resp.get("gazettes", [])
        if not gazettes:
            break

        if not debug_impresso:
            ibge, nome, chaves = extrair_territorio(gazettes[0])
            if ibge is None:
                print(f"    ⚠️  não achei campo de território óbvio no 1º resultado. "
                      f"Chaves disponíveis: {chaves}")
                print(f"    ⚠️  1º resultado bruto (ajustar extrair_territorio() se "
                      f"precisar): {json.dumps(gazettes[0], ensure_ascii=False)[:800]}")
            debug_impresso = True

        achados.extend(gazettes)
        offset += len(gazettes)
        if total_declarado and offset >= total_declarado:
            break
        time.sleep(pausa)

    return achados[:teto]


def rodar_modo_nacional(
    saida: Path, teto_por_termo: int, tamanho_pagina: int, pausa: float,
    termos_para_rodar: Optional[list] = None,
):
    """Se `termos_para_rodar` for None, roda os 6 termos padrão. Se for uma
    lista (via --termos), busca de novo SÓ esses termos — os demais são
    reaproveitados do achados_<termo>.json já salvo numa rodada anterior
    (sem nova chamada à API), para não perder o que já foi coletado nem
    bater de novo num servidor que já mostrou estar sob estresse
    (11/09/2026: rodada nacional cheia de 503/520/429/timeout — ver retentativas
    em chamar_com_retentativas). Se um termo pedido em --termos nunca foi
    coletado antes E não está na lista a rodar agora, entra como 0 (com
    aviso), não como erro silencioso."""
    saida_nacional = saida / "nacional"
    saida_nacional.mkdir(parents=True, exist_ok=True)

    a_rodar = set(termos_para_rodar) if termos_para_rodar else set(TERMOS)

    # base de comparação: quais cod_ibge já estão nos 176 casos
    ja_conhecidos = set()
    if CAMINHO_CONTROLE.exists():
        base = pd.read_csv(CAMINHO_CONTROLE, dtype={"cod_ibge": str})
        ja_conhecidos = set(base["cod_ibge"].str.strip().dropna())
    else:
        print("⚠️  Controle único não encontrado — não vou saber marcar 'já na base'.")

    por_municipio = {}  # ibge -> {nome, termos: {termo: [gazettes]}}

    # BUG corrigido em 19/09/2026: este loop iterava só sobre TERMOS (os 6
    # padrão), então uma frase nova passada em --termos (fora dos 6) nunca era
    # buscada nem aparecia no output — silenciosamente ignorada, sem erro. A
    # união com `a_rodar` garante que todo termo pedido explicitamente entra no
    # loop, mesmo sem estar nos 6 originais; os 6 originais continuam sendo
    # considerados (para poder reaproveitar cache deles quando não repedidos).
    for termo in sorted(set(TERMOS) | a_rodar):
        arq_termo = saida_nacional / f"achados_{re.sub(r'[^a-z0-9]+', '_', termo.lower())}.json"

        if termo in a_rodar:
            print(f"\n=== termo nacional: '{termo}' ===")
            hits = buscar_nacional(termo, teto_por_termo, tamanho_pagina, pausa)
            print(f"    coletados: {len(hits)} diário(s) com '{termo}'.")
            arq_termo.write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")
        elif arq_termo.exists():
            hits = json.loads(arq_termo.read_text(encoding="utf-8"))
            print(f"\n=== termo '{termo}': reaproveitando coleta salva anteriormente "
                  f"({len(hits)} diário(s), sem chamar a API de novo) ===")
        else:
            hits = []
            print(f"\n=== termo '{termo}': NÃO pedido em --termos e sem coleta "
                  f"anterior salva em {arq_termo.name} — entrando como 0 ===")

        n_bruto = len(hits)
        hits = [g for g in hits if bate_frase_exata(termo, g)]
        if n_bruto and len(hits) != n_bruto:
            print(f"    ⚠️  frase exata confirmada em {len(hits)} de {n_bruto} "
                  f"diário(s) — descartados {n_bruto - len(hits)} falso(s) "
                  f"positivo(s) da busca frouxa da API.")

        for g in hits:
            ibge, nome, _ = extrair_territorio(g)
            chave = ibge or f"sem_ibge::{nome}"
            reg = por_municipio.setdefault(chave, {"ibge": ibge, "nome": nome, "termos": {}})
            reg["termos"].setdefault(termo, []).append(g)

    linhas = []
    for chave, reg in por_municipio.items():
        ibge, nome = reg["ibge"], reg["nome"]
        termos_batidos = list(reg["termos"].keys())
        n_total = sum(len(v) for v in reg["termos"].values())
        primeiro_termo = termos_batidos[0]
        primeiro_g = reg["termos"][primeiro_termo][0]
        excertos = primeiro_g.get("excerpts", [])
        linhas.append({
            "cod_ibge": ibge,
            "municipio_conforme_qd": nome,
            "ja_na_base_176": (ibge in ja_conhecidos) if ibge else "desconhecido (sem ibge)",
            "termos_batidos": ", ".join(termos_batidos),
            "n_diarios_total": n_total,
            "data_1o_diario": primeiro_g.get("date", ""),
            "url_1o_diario": primeiro_g.get("txt_url") or primeiro_g.get("url", ""),
            "excerto": (excertos[0] if excertos else "").replace("\n", " ")[:500],
        })

    colunas = [
        "cod_ibge", "municipio_conforme_qd", "ja_na_base_176", "termos_batidos",
        "n_diarios_total", "data_1o_diario", "url_1o_diario", "excerto",
    ]
    resumo = pd.DataFrame(linhas, columns=colunas)

    if resumo.empty:
        resumo.to_csv(saida_nacional / "resumo_nacional.csv", index=False, encoding="utf-8-sig")
        print("\n=== Resumo nacional: 0 achados no total. ===")
        print("⚠️  Isso quase certamente é sinal de ERRO DE CONEXÃO em todos os "
              "termos (veja as mensagens 🔴 acima), não ausência real de resultado "
              "— a API do Querido Diário tem MUITOS diários com esses termos. "
              "Resolva o erro de conexão antes de tratar isso como resultado válido.")
        return

    resumo = resumo.sort_values(
        by=["ja_na_base_176", "n_diarios_total"], ascending=[True, False]
    )
    resumo.to_csv(saida_nacional / "resumo_nacional.csv", index=False, encoding="utf-8-sig")

    novos = resumo[resumo["ja_na_base_176"] == False]  # noqa: E712
    novos.to_csv(saida_nacional / "achados_NOVOS_fora_da_base.csv", index=False, encoding="utf-8-sig")

    print(f"\n=== Resumo nacional: {len(resumo)} município(s) distintos com algum "
          f"achado ===")
    print(f"  · já na base de 176 casos: {(resumo['ja_na_base_176'] == True).sum()}")  # noqa: E712
    print(f"  · NOVOS, fora da base: {len(novos)}")
    print(f"Detalhe em {saida_nacional}/resumo_nacional.csv "
          f"e {saida_nacional}/achados_NOVOS_fora_da_base.csv")
    print("\n⚠️  Lembrete: são termos fortes mas ainda é triagem lexical — abrir a "
          "URL/excerto e confirmar antes de tratar como caso novo. Um achado 'NOVO' "
          "pode ser: (a) TZ real ainda não catalogado — bom achado; (b) menção sem "
          "TZ de fato (proposta rejeitada, notícia sobre outro município, etc.).")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--saida", default="saida_querido_diario",
        help="Pasta de saída (padrão: saida_querido_diario)",
    )
    ap.add_argument(
        "--filtro", default=None,
        help='Prefixo de "estado" a buscar (ex.: "C" ou "B1"). '
             "Padrão: B1 e C juntos (~125 municípios).",
    )
    ap.add_argument(
        "--municipios-arquivo", default=None,
        help="CSV com coluna 'cod_ibge' — roda só esses municípios, "
             "IGNORANDO o campo 'estado' (inclui B2/A se estiverem na "
             "lista). Substitui --filtro quando os dois são passados. "
             "Ex.: alvo_pendentes_2026-09-16.csv.",
    )
    ap.add_argument(
        "--filtro-cod-ibge", default=None,
        help="Lista de cod_ibge separados por vírgula (ex.: "
             "'5201306,5202502') — restringe o que --filtro ou "
             "--municipios-arquivo já selecionou a só esses códigos. Uso "
             "típico: retomar so os municípios que deram erro numa rodada "
             "anterior, sem reprocessar o resto.",
    )
    ap.add_argument(
        "--pausa", type=float, default=1.0,
        help="Segundos de pausa entre chamadas à API (padrão 1.0 — "
             "a API pede bom senso, ~60 req/min).",
    )
    ap.add_argument(
        "--nacional", action="store_true",
        help="Em vez de varrer só os municípios que faltam na base, busca "
             "cada termo em TODO O BRASIL (sem restringir por município) — "
             "para achar TZ em municípios fora dos 176 casos atuais.",
    )
    ap.add_argument(
        "--teto-por-termo", type=int, default=3000,
        help="Só com --nacional: máximo de diários a coletar por termo "
             "(cinto de segurança contra termos muito genéricos). Padrão 3000.",
    )
    ap.add_argument(
        "--tamanho-pagina", type=int, default=50,
        help="Só com --nacional: resultados por página na paginação (padrão 50).",
    )
    ap.add_argument(
        "--termos", default=None,
        help='Lista separada por vírgula de termos ADICIONAIS a buscar, além '
             'dos 6 padrão (ex.: "institui o programa tarifa zero,institui a '
             'gratuidade do transporte"). Com --nacional, os termos NÃO '
             'listados aqui reaproveitam o achados_<termo>.json já salvo de '
             'uma rodada anterior (sem nova chamada à API); sem --nacional '
             '(modo por município), todos os termos da união (6 padrão + '
             'estes) são buscados para cada município do alvo — não há cache '
             'por termo nesse modo. Desde 20/09/2026: disponível nos dois '
             'modos (antes só funcionava com --nacional).',
    )
    args = ap.parse_args()

    if args.nacional:
        saida = Path(args.saida)
        saida.mkdir(exist_ok=True)
        termos_para_rodar = (
            [t.strip() for t in args.termos.split(",") if t.strip()]
            if args.termos else None
        )
        alvo_termos = termos_para_rodar or TERMOS
        print(f"Modo NACIONAL: {len(alvo_termos)} termo(s) a buscar agora "
              f"({len(TERMOS) - len(alvo_termos)} reaproveitado(s) de rodada "
              f"anterior, se houver), até {args.teto_por_termo} diários por termo.")
        rodar_modo_nacional(
            saida, args.teto_por_termo, args.tamanho_pagina, args.pausa,
            termos_para_rodar=termos_para_rodar,
        )
        return

    termos_extra = (
        [t.strip() for t in args.termos.split(",") if t.strip()]
        if args.termos else []
    )
    termos_alvo = sorted(set(TERMOS) | set(termos_extra))
    if termos_extra:
        print(f"Termos adicionais pedidos via --termos: {len(termos_extra)} "
              f"— total de {len(termos_alvo)} termos por município nesta rodada.")

    alvos = montar_alvos(args.filtro, args.municipios_arquivo)
    if args.filtro_cod_ibge:
        so = {c.strip() for c in args.filtro_cod_ibge.split(",") if c.strip()}
        antes = len(alvos)
        alvos = alvos[alvos["cod_ibge"].isin(so)].reset_index(drop=True)
        faltando = so - set(alvos["cod_ibge"])
        if faltando:
            print(f"⚠️  --filtro-cod-ibge: {len(faltando)} código(s) não "
                  f"estavam na seleção de --filtro/--municipios-arquivo "
                  f"(fora do alvo original?): {sorted(faltando)}")
        print(f"--filtro-cod-ibge: restringindo de {antes} para "
              f"{len(alvos)} municípios.")
    saida = Path(args.saida)
    saida.mkdir(exist_ok=True)
    arq_resumo = saida / "resumo.csv"

    # Retomada automática (20/09/2026, adicionado para a rodada de 5.570
    # municípios): antes o resumo.csv só era gravado no FINAL do loop inteiro
    # — numa rodada de dezenas de milhares de chamadas, rodando por horas sem
    # supervisão, uma queda no meio (sono do notebook, terminal fechado,
    # instabilidade de rede) perdia tudo. Agora cada município processado é
    # gravado incrementalmente (ver mais abaixo) e, se resumo.csv já existir
    # de uma rodada anterior interrompida, os cod_ibge já presentes nele são
    # pulados automaticamente — só reprocessa o que falta.
    ja_processados = set()
    if arq_resumo.exists():
        anterior = pd.read_csv(arq_resumo, dtype={"cod_ibge": str})
        ja_processados = set(anterior["cod_ibge"].dropna())
        antes = len(alvos)
        alvos = alvos[~alvos["cod_ibge"].isin(ja_processados)].reset_index(drop=True)
        print(f"↻ Retomando: {len(ja_processados)} município(s) já no "
              f"{arq_resumo.name} de uma rodada anterior — pulando esses, "
              f"restam {len(alvos)} de {antes}.")

    print(f"{len(alvos)} municípios a varrer ({len(termos_alvo)} termos cada = "
          f"{len(alvos) * len(termos_alvo)} chamadas à API).")

    linhas_resumo = []

    for i, row in alvos.iterrows():
        municipio, uf, ibge, estado = row["municipio"], row["uf"], row["cod_ibge"], row["estado"]
        print(f"\n=== [{i+1}/{len(alvos)}] {municipio}/{uf} (IBGE {ibge}, estado={estado}) ===")

        achados_municipio = {}
        algum_achado = False
        erro = ""

        for termo in termos_alvo:
            try:
                resp = buscar_termo(ibge, termo)
            except requests.HTTPError as e:
                print(f"  🔴 erro HTTP em '{termo}': {e}")
                erro = str(e)
                time.sleep(args.pausa)
                continue
            except requests.RequestException as e:
                print(f"  🔴 erro de rede em '{termo}': {e}")
                erro = str(e)
                time.sleep(args.pausa)
                continue

            gazettes_brutos = resp.get("gazettes", [])
            gazettes = [g for g in gazettes_brutos if bate_frase_exata(termo, g)]
            total = len(gazettes)
            if total:
                algum_achado = True
                if len(gazettes) != len(gazettes_brutos):
                    print(f"  🎯 '{termo}': {total} diário(s) com a FRASE confirmada "
                          f"(de {len(gazettes_brutos)} devolvido(s) pela API — "
                          f"{len(gazettes_brutos) - total} descartado(s) por não "
                          f"terem a frase contígua no excerto).")
                else:
                    print(f"  🎯 '{termo}': {total} diário(s) com o termo.")
                achados_municipio[termo] = gazettes
            else:
                print(f"  ·  '{termo}': 0.")
            time.sleep(args.pausa)

        if achados_municipio:
            arq = saida / f"{municipio}-{uf}.json".replace("/", "-")
            arq.write_text(
                json.dumps(achados_municipio, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"  📄 salvo: {arq}")

        # top achado pro resumo (primeiro termo com resultado, primeiro gazette)
        top_termo, top_excerto, top_data, top_url = "", "", "", ""
        for termo, gzs in achados_municipio.items():
            if gzs:
                top_termo = termo
                g = gzs[0]
                top_data = g.get("date", "")
                top_url = g.get("txt_url") or g.get("url") or ""
                excertos = g.get("excerpts", [])
                top_excerto = excertos[0] if excertos else ""
                break

        linha = {
            "municipio": municipio, "uf": uf, "cod_ibge": ibge, "estado_atual": estado,
            "algum_achado": algum_achado,
            "termo_do_1o_achado": top_termo,
            "data_diario": top_data,
            "url_diario": top_url,
            "excerto": top_excerto.replace("\n", " ")[:500],
            "erro": erro,
        }
        linhas_resumo.append(linha)

        # Gravação incremental (20/09/2026): cada município processado é
        # anexado ao resumo.csv NA HORA, não só no final do loop — ver nota
        # de retomada automática acima. Escreve o cabeçalho só se o arquivo
        # ainda não existir (1ª linha desta rodada, ou rodada nova do zero).
        pd.DataFrame([linha]).to_csv(
            arq_resumo, mode="a", header=not arq_resumo.exists(),
            index=False, encoding="utf-8-sig",
        )

    if linhas_resumo:
        resumo_rodada = pd.DataFrame(linhas_resumo)
        n_achados = resumo_rodada["algum_achado"].sum()
        print(f"\n=== Resumo desta execução: {n_achados}/{len(resumo_rodada)} "
              f"município(s) NOVO(s) (além dos já retomados) com algum achado "
              f"por palavra-chave no Querido Diário ===")
    else:
        print("\n=== Nada a processar nesta execução — todos os municípios do "
              "alvo já estavam no resumo.csv de uma rodada anterior. ===")
    print(f"Detalhe acumulado em {saida}/resumo.csv (todas as execuções desta "
          f"pasta de saída) e um .json por município com achado.")
    print("\n⚠️  Lembrete: achado aqui é TRIAGEM LEXICAL num diário oficial, não é "
          "a lei em si — abrir o excerto/URL e confirmar antes de citar. E ausência "
          "de achado pode ser cobertura incompleta do Querido Diário para esse "
          "município/ano, não prova de ausência da lei.")


if __name__ == "__main__":
    main()
