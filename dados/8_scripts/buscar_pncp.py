#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buscar_pncp.py

Varredura do PNCP (Portal Nacional de Contratações Públicas, API de consulta
pública `https://pncp.gov.br/api/consulta`) por município, para o passo 4 do
pipeline de escalonamento legal (ver `Metodologia - varredura SAPL da
legislação municipal (10-09-2026).md` §10: SAPL → SISCAM → Querido Diário →
PNCP → Conlicitação → busca manual → LAI).

MOTIVO DE EXISTIR (16/09/2026): o objetivo declarado do autor para o PNCP não
é só achar o operador — é melhorar o conhecimento sobre a política de TZ em
si: modelo de remuneração do operador, histórico de contratação e prazo/
natureza (emergencial ou não) do contrato vigente. Isso alimenta direto:
- a régua analítica (B.2 — modelo de financiamento e pagamento; Regras de
  classificação das réguas.md), sobretudo a estratificação B.2.1;
- o campo `qualificador` de trajetória (emergencial/substitutiva vs.
  emergencial-consolidada — achado da conversa com Daniel Santini, 14/09);
- o gargalo declarado `operador_urbano_local` (Hipótese e Pressupostos).

⚠️ BLOQUEIO DE REDE CONFIRMADO (16/09/2026): `pncp.gov.br:443` está com CONNECT
rejeitado pela política de rede tanto no shell do sandbox de nuvem quanto no
shell conectado à máquina do autor (mesmo bloqueio que já parou o Querido
Diário e o SISCAM nesta sessão). O acesso só funcionou via WebFetch (que roda
fora deste sandbox) — ou seja, este script PRECISA rodar no ambiente do
autor, fora do Cowork, exatamente como os outros scripts de rede desta série.

⚠️ TABELA DE MODALIDADE NÃO CONFIRMADA COMO EXAUSTIVA: a API exige
`codigoModalidadeContratacao` (obrigatório) mas não expõe um endpoint de
domínio fácil de consultar por script (a página humana é
https://pncp.gov.br/app/entidades-dominio, que é SPA em JS — não dá pra
raspar). Só o código 6 = "Pregão Eletrônico" foi confirmado empiricamente
(teste real em 16/09/2026, WebFetch, resultado com órgãos reais). Os demais
códigos abaixo (MODALIDADES_PADRAO) vêm de fontes secundárias (manual PNCP,
notebooks de terceiros) e NÃO foram verificados um a um — rode
`--listar-modalidades` primeiro e confirme contra
https://pncp.gov.br/app/entidades-dominio antes de tirar conclusão de
ausência ("não achei nada" pode ser modalidade errada, não ausência real).

⚠️ CAVEAT METODOLÓGICO, a registrar antes de usar os resultados: concessões
de serviço público de transporte coletivo são regidas, em vários municípios,
pela Lei 8.987/1995 (concessões), não pela Lei 14.133/2021 (licitações em
geral) — e o PNCP nasceu da 14.133. Um contrato de concessão ANTIGO (anterior
a 2021, ou nunca republicado no PNCP) pode simplesmente não aparecer aqui.
Ausência de achado no PNCP não é evidência de ausência de contrato — é gap de
cobertura conhecido, mesmo princípio já aplicado ao Querido Diário e ao SAPL.
CONFIRMADO NA PRÁTICA em 16/09/2026 (Canoas/RS): os achados de contratações
foram todos periféricos (manutenção de abrigos, sinalização, curso de agentes
de trânsito) — nenhum é o contrato de operação/concessão em si.

⏱️ DUAS FASES (redesenho de 16/09/2026, após 1ª rodada muito lenta): rodar
"tudo de uma vez" nos 155 municípios da base é impraticável — 13 modalidades
× 6 blocos de data por município na 1ª busca, mais um 2º passo
(--buscar-contrato) que puxa TODOS os contratos do CNPJ da prefeitura sem
filtro (150 num único município testado). A partir de agora:
  FASE 1 — triagem (padrão, sem --buscar-contrato): só `contratações`,
  restrita às modalidades plausíveis para contrato de operação/concessão de
  transporte (ver MODALIDADES_TRIAGEM) — rápida, dá pra rodar nos 155.
  FASE 2 — aprofundamento (--buscar-contrato): 2º passo em `/v1/contratos`,
  só para os municípios que a Fase 1 sinalizou como relevantes (ou que você
  aponte manualmente num CSV menor). NÃO rodar em lote grande — o script
  avisa (não bloqueia) se `--buscar-contrato` vier com muitos municípios.

⏱️ SEGUNDO AJUSTE DE VELOCIDADE (16/09/2026, ainda lento após o primeiro): o
fatiamento fixo em blocos de 1 ano nunca foi confirmado como uma exigência
real da API — era uma suposição cautelosa herdada de outros scripts desta
série (SAPL/Querido Diário), carregada sem testar. Este ajuste tentou o
intervalo INTEIRO numa só chamada por modalidade, bisectando só em erro 400.

⚠️ TERCEIRO AJUSTE — CORREÇÃO, NÃO VELOCIDADE (16/09/2026, mesmo dia): o ajuste
acima **piorou o resultado, não só a velocidade** — Canoas/RS caiu de 4
achados (com blocos de 1 ano) para 0 (com intervalo inteiro), numa rodada
comparável. A hipótese "a API erra com 400 se o intervalo for grande demais"
**não se confirmou**: o mais provável, a partir desta única evidência, é que a
API devolva HTTP 200 com resultado vazio/truncado para um intervalo grande
demais, em vez de recusar — silencioso, sem erro para bisectar. Isto NÃO foi
verificado em fonte primária (não dá pra testar a API a partir daqui — ver
bloqueio de rede acima); é inferência a partir de uma única regressão
observada, registrada como tal (Becker: não confundir inferência com dado).
Correção adotada, cautelosa: **`--bloco-dias` volta a ter padrão 365** (o
fatiamento que comprovadamente achou os 4 registros de Canoas), com a
bisecção automática mantida como rede de segurança dentro de cada bloco (em
caso de 400/422 mesmo num intervalo de 1 ano). Use `--bloco-dias 0` para
testar de novo o intervalo inteiro, deliberadamente, se quiser gerar mais
evidência sobre o comportamento real da API — os novos logs por modalidade
(registros brutos antes do filtro) tornam essa checagem visível desta vez,
em vez de silenciosa.

O QUE O SCRIPT FAZ:
1. Para cada município (CSV municipio,uf,cod_ibge), consulta
   `/v1/contratacoes/publicacao` cruzando um intervalo de datas (padrão:
   01/04/2021 até hoje, tentado inteiro numa chamada, bisectado só se a API
   recusar) × uma lista de modalidades (padrão: MODALIDADES_TRIAGEM,
   6 códigos plausíveis — use --modalidades todas para os 13 completos),
   filtrando por `codigoMunicipioIbge`.
2. Filtra client-side (a API não tem busca por texto/CNAE) o campo
   `objetoCompra` contra uma lista de termos de transporte coletivo.
3. Só em modo aprofundamento (--buscar-contrato): para cada achado, busca em
   `/v1/contratos` pelo CNPJ do órgão (`orgaoEntidade.cnpj`), pagina até o
   fim (corrigido — antes só lia a página 1) e filtra de novo pelo objeto
   antes de gravar (antes gravava todos os contratos do órgão, filtrados ou
   não, inflando o JSON).
4. Grava `<saida>/achados_<municipio>-<uf>.json` (bruto) e `<saida>/resumo.csv`
   (uma linha por achado, achatada para leitura rápida).

Uso:
    # Fase 1 — triagem rápida, todos os municípios da base:
    python3 buscar_pncp.py --arquivo municipios.csv --saida resultados

    # Fase 2 — aprofundamento, só nos municípios que a Fase 1 sinalizou
    # (crie um CSV menor, ex. municipios_aprofundar.csv):
    python3 buscar_pncp.py --arquivo municipios_aprofundar.csv --saida resultados --buscar-contrato

    # antes de tudo, confirmar a tabela de modalidade:
    python3 buscar_pncp.py --listar-modalidades

CSV de entrada: colunas municipio,uf,cod_ibge (mesmo formato dos outros
scripts desta série — buscar_querido_diario_candidatos.py, sapl_varredura.py).

Autor: Thiago Von Zeidler Gomes
Orientadora: Prof.ª Silvana Zioni
"""

import argparse
import json
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

BASE = "https://pncp.gov.br/api/consulta/v1"

# ⚠️ NÃO CONFIRMADO COMO EXAUSTIVO — só o código 6 foi testado de fato
# (16/09/2026). Validar com --listar-modalidades / a página de domínio antes
# de confiar em "não achei nada" para os demais códigos.
MODALIDADES_PADRAO = {
    1: "Leilão - Eletrônico",
    2: "Diálogo Competitivo",
    3: "Concurso",
    4: "Concorrência - Eletrônica",
    5: "Concorrência - Presencial",
    6: "Pregão - Eletrônico",          # ✅ confirmado empiricamente 16/09/2026
    7: "Pregão - Presencial",
    8: "Dispensa de Licitação",
    9: "Inexigibilidade",
    10: "Manifestação de Interesse",
    11: "Pré-qualificação",
    12: "Credenciamento",
    13: "Leilão - Presencial",
}

# Subconjunto plausível para contrato de operação/concessão de transporte —
# usado como padrão da Fase 1 (triagem). Concessões costumam ir por
# concorrência; contratações emergenciais/pontuais aparecem como dispensa ou
# pregão. Leilão, concurso, diálogo competitivo, pré-qualificação e
# credenciamento raramente se aplicam a esse tipo de contrato — mantidos só
# em MODALIDADES_PADRAO para quem quiser rodar `--modalidades todas`.
MODALIDADES_TRIAGEM = {c: MODALIDADES_PADRAO[c] for c in (4, 5, 6, 7, 8, 9)}

# Subconjunto plausível AMPLIADO, para a "rodada completa" (buscar_pncp_completo.py,
# ajuste de 18/09/2026 — depois de ~2 dias de execução real mostrarem que os 13
# códigos completos custam caro para pouco ganho: nas amostras vistas, Leilão
# (1 e 13), Diálogo Competitivo (2), Concurso (3) e Pré-qualificação (11)
# devolveram consistentemente poucos ou zero registros brutos, e nenhuma dessas
# modalidades é, por definição legal, a de um contrato de operação/concessão de
# transporte coletivo (leilão é para alienação/concessão de uso de bem público,
# não para contratar um serviço; concurso é para projeto técnico/artístico;
# diálogo competitivo é para soluções inovadoras complexas, raríssimo em nível
# municipal; pré-qualificação é fase prévia a uma modalidade já coberta abaixo).
# Mantém os 6 da triagem rápida (MODALIDADES_TRIAGEM) mais Manifestação de
# Interesse (10) e Credenciamento (12), que podem preceder uma concessão e têm
# custo baixo nas amostras vistas (raramente >30 registros brutos). Isto é
# intencionalmente mais amplo que a triagem, mas mais estreito que os 13
# completos — decisão registrada aqui, não silenciosa; quem quiser reverter à
# exaustão completa usa `--modalidades todas` (buscar_pncp.py) ou
# `--modalidades-todas-13` (buscar_pncp_completo.py). Ver "TERCEIRO AJUSTE" no
# docstring do módulo: "não achei nada" não é evidência de ausência real.
MODALIDADES_RODADA_COMPLETA = {c: MODALIDADES_PADRAO[c] for c in (4, 5, 6, 7, 8, 9, 10, 12)}

TERMOS_TRANSPORTE = [
    "transporte coletivo",
    "transporte público",
    "sistema de transporte",
    "ônibus",
    "onibus",
    "tarifa",
    "passageiro",
    "concessão do transporte",
    "concessao do transporte",
    "mobilidade urbana",
    "operador do sistema",
    "permissão de transporte",
    "permissao de transporte",
]

LIMITE_AVISO_LOTE_APROFUNDAMENTO = 10


def _sessao():
    s = requests.Session()
    s.headers.update({"User-Agent": "pesquisa-doutorado-pgt-ufabc (thiago@poloplanejamento.com)"})
    return s


def listar_modalidades():
    print("Tabela usada por este script (NÃO confirmada como exaustiva —")
    print("confirme contra https://pncp.gov.br/app/entidades-dominio):\n")
    for cod, nome in MODALIDADES_PADRAO.items():
        marca = "✅ confirmado" if cod == 6 else "⚠️ não testado"
        na_triagem = "· usada na triagem padrão" if cod in MODALIDADES_TRIAGEM else ""
        print(f"  {cod:>2} — {nome:<30} {marca}  {na_triagem}")


MIN_DIAS_BISECCAO = 31  # não bisecta abaixo disso — evita recursão infinita


def _chamar(sessao, endpoint, params, pausa, tentativas=5):
    """Devolve: dict de resposta em caso de 200; {"data": [], ...} em 404;
    "ERRO_INTERVALO" em 400 (sem re-tentativa — bisectar, não adianta repetir
    o mesmo intervalo inválido); None se esgotar tentativas noutros erros."""
    for i in range(tentativas):
        try:
            r = sessao.get(f"{BASE}/{endpoint}", params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return {"data": [], "totalRegistros": 0}
            if r.status_code in (400, 422):
                return "ERRO_INTERVALO"
            time.sleep(pausa * (2 ** i))
        except requests.RequestException:
            time.sleep(pausa * (2 ** i))
    return None


def _buscar_janela(sessao, endpoint, params_extra, d1: date, d2: date, pausa,
                    tamanho_pagina=50, profundidade=0):
    """Busca paginada numa janela de datas [d1, d2] para um endpoint/params
    fixos. Tenta a janela inteira primeiro; só bisecta (corta ao meio e
    recursa) se a API recusar com 400 — assim o caso comum (API aceita o
    intervalo cheio) custa 1 chamada em vez de N blocos fixos de 1 ano."""
    registros_totais = []
    pagina = 1
    while True:
        params = dict(params_extra)
        params.update({
            "dataInicial": d1.strftime("%Y%m%d"),
            "dataFinal": d2.strftime("%Y%m%d"),
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        })
        resp = _chamar(sessao, endpoint, params, pausa)
        time.sleep(pausa)
        if resp == "ERRO_INTERVALO":
            dias = (d2 - d1).days
            if dias <= MIN_DIAS_BISECCAO:
                print(f"    ⚠️ intervalo {d1}–{d2} recusado pela API (400) e já no tamanho "
                      f"mínimo de bisecção — pulando essa janela.")
                return registros_totais
            meio = d1 + (d2 - d1) // 2
            return (
                _buscar_janela(sessao, endpoint, params_extra, d1, meio, pausa, tamanho_pagina, profundidade + 1)
                + _buscar_janela(sessao, endpoint, params_extra, meio + timedelta(days=1), d2, pausa, tamanho_pagina, profundidade + 1)
            )
        if resp is None:
            break
        registros = resp.get("data", [])
        if not registros:
            break
        registros_totais.extend(registros)
        total_paginas = resp.get("totalPaginas", 1)
        if pagina >= total_paginas:
            break
        pagina += 1
    return registros_totais


def _janelas_iniciais(data_ini: date, data_fim: date, bloco_dias):
    """Se --bloco-dias não for passado, devolve o intervalo inteiro como uma
    única janela (deixa a API decidir, com bisecção automática em caso de
    400). Se passado, pré-fatia em blocos fixos desse tamanho — útil se você
    já sabe que a API recusa intervalos longos e quer pular a tentativa."""
    if not bloco_dias:
        return [(data_ini, data_fim)]
    janelas = []
    d1 = data_ini
    while d1 <= data_fim:
        d2 = min(d1 + timedelta(days=bloco_dias - 1), data_fim)
        janelas.append((d1, d2))
        d1 = d2 + timedelta(days=1)
    return janelas


def buscar_modalidade(sessao, cod_ibge, cod_mod, nome_mod, data_ini, data_fim, pausa,
                       tamanho_pagina=50, bloco_dias=None):
    """Busca contratacoes/publicacao para UM município × UMA modalidade, já
    filtradas por termo de transporte no objeto. Extraído de buscar_municipio
    em 18/09/2026 para permitir checkpoint por modalidade (não só por
    município) em buscar_pncp_completo.py — uma rodada de ~2 dias mostrou que
    perder o progresso de um município inteiro por causa de uma falha numa
    única modalidade é caro demais para não ter esse nível de retomada."""
    params_extra = {
        "codigoModalidadeContratacao": cod_mod,
        "codigoMunicipioIbge": cod_ibge,
    }
    registros = []
    for d1, d2 in _janelas_iniciais(data_ini, data_fim, bloco_dias):
        registros.extend(_buscar_janela(sessao, "contratacoes/publicacao", params_extra,
                                         d1, d2, pausa, tamanho_pagina))
    print(f"    [{nome_mod}] {len(registros)} registro(s) bruto(s) antes do filtro de termo "
          f"({data_ini.isoformat()}–{data_fim.isoformat()})")
    achados = []
    for reg in registros:
        objeto = (reg.get("objetoCompra") or "").lower()
        if any(termo in objeto for termo in TERMOS_TRANSPORTE):
            reg["_modalidade_nome"] = nome_mod
            achados.append(reg)
    return achados


def buscar_municipio(sessao, cod_ibge, modalidades, data_ini, data_fim, pausa, tamanho_pagina=50, bloco_dias=None):
    """Retorna lista de registros de contratacoes/publicacao filtrados por
    município e por termo de transporte no objeto, para TODAS as modalidades
    passadas (uma chamada por modalidade a buscar_modalidade). Mantido para
    compatibilidade com o uso de fase única deste script (--buscar-contrato);
    buscar_pncp_completo.py usa buscar_modalidade diretamente para poder
    fazer checkpoint por modalidade."""
    achados = []
    for cod_mod, nome_mod in modalidades.items():
        achados.extend(buscar_modalidade(sessao, cod_ibge, cod_mod, nome_mod, data_ini, data_fim,
                                          pausa, tamanho_pagina, bloco_dias))
    return achados


def buscar_contrato(sessao, cnpj_orgao, data_ini, data_fim, pausa, bloco_dias=None):
    """Segundo passo (Fase 2 — aprofundamento): busca em /v1/contratos pelo
    CNPJ do órgão (por padrão, uma janela com o intervalo inteiro, bisectada
    só se a API recusar), e já filtra pelo objeto antes de devolver (antes
    devolvia todos os contratos do órgão, sem filtro — 150 registros brutos
    num único caso testado). Devolve (filtrados, total_bruto_verificado)
    para o chamador poder reportar quantos foram varridos vs. sobraram."""
    if not cnpj_orgao:
        return [], 0
    brutos = []
    for d1, d2 in _janelas_iniciais(data_ini, data_fim, bloco_dias):
        brutos.extend(_buscar_janela(sessao, "contratos", {"cnpjOrgao": cnpj_orgao}, d1, d2, pausa))
    filtrados = [
        c for c in brutos
        if any(t in (c.get("objetoContrato") or "").lower() for t in TERMOS_TRANSPORTE)
    ]
    return filtrados, len(brutos)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arquivo", help="CSV com colunas municipio,uf,cod_ibge")
    ap.add_argument("--saida", default="saida_pncp")
    ap.add_argument("--data-inicial", default="2021-04-01", help="AAAA-MM-DD (Lei 14.133/2021 é de abril/2021)")
    ap.add_argument("--data-final", default=None, help="AAAA-MM-DD, padrão hoje")
    ap.add_argument("--modalidades", default=None,
                     help="códigos separados por vírgula (ex. '6,8,9'), ou a palavra 'todas' para os 13 completos. "
                          "Padrão: MODALIDADES_TRIAGEM (4,5,6,7,8,9 — plausíveis para operação/concessão)")
    ap.add_argument("--pausa", type=float, default=1.0)
    ap.add_argument("--bloco-dias", type=int, default=365,
                     help="pré-fatiamento em blocos fixos desse tamanho (dias). Padrão: 365 "
                          "(comprovadamente funciona — ver TERCEIRO AJUSTE no docstring). "
                          "Use 0 para tentar o intervalo inteiro numa chamada (bisecta só se a "
                          "API recusar com 400/422) — modo mais rápido em tese, mas que já deu "
                          "0 achados onde 365 dias deu 4; use só para gerar evidência, não em produção.")
    ap.add_argument("--listar-modalidades", action="store_true")
    ap.add_argument("--buscar-contrato", action="store_true",
                     help="FASE 2 (aprofundamento): para cada achado, busca também o contrato efetivo via "
                          "cnpjOrgao. Bem mais lento — use só num CSV pequeno, com os municípios que a Fase 1 "
                          "(sem esta flag) já sinalizou como relevantes.")
    args = ap.parse_args()

    if args.listar_modalidades:
        listar_modalidades()
        return

    if not args.arquivo:
        ap.error("--arquivo é obrigatório (ou use --listar-modalidades)")

    data_ini = date.fromisoformat(args.data_inicial)
    data_fim = date.fromisoformat(args.data_final) if args.data_final else date.today()

    if args.modalidades:
        if args.modalidades.strip().lower() == "todas":
            modalidades = MODALIDADES_PADRAO
        else:
            codigos = [int(c) for c in args.modalidades.split(",")]
            modalidades = {c: MODALIDADES_PADRAO.get(c, f"código {c} (nome desconhecido)") for c in codigos}
    else:
        modalidades = MODALIDADES_TRIAGEM

    alvos = pd.read_csv(args.arquivo, dtype={"cod_ibge": str})
    alvos["cod_ibge"] = alvos["cod_ibge"].str.strip()

    modo = "FASE 2 — aprofundamento (--buscar-contrato ativo)" if args.buscar_contrato else "FASE 1 — triagem (rápida, sem 2º passo de contrato)"
    n_janelas_iniciais = len(_janelas_iniciais(data_ini, data_fim, args.bloco_dias))
    print(f"Modo: {modo}")
    print(f"{len(alvos)} municípios × {len(modalidades)} modalidades × "
          f"{n_janelas_iniciais} janela(s) de data por padrão na 1ª busca "
          f"({'bisecta automaticamente se a API recusar' if n_janelas_iniciais == 1 else 'bloco fixo via --bloco-dias'}).")
    if args.buscar_contrato and len(alvos) > LIMITE_AVISO_LOTE_APROFUNDAMENTO:
        print(f"⚠️ Você está rodando --buscar-contrato em {len(alvos)} municípios de uma vez — "
              f"isso puxa TODOS os contratos do CNPJ de cada órgão (pode ser lento e pesado). "
              f"Recomendado: rode a Fase 1 primeiro (sem --buscar-contrato) em toda a base, "
              f"revise o resumo.csv, e só depois rode a Fase 2 num CSV menor com os casos "
              f"sinalizados. Continuando mesmo assim...\n")
    print("⚠️ Rodando fora do Cowork? Este script NÃO funciona dentro do sandbox/ponte "
          "(pncp.gov.br está bloqueado por política de rede nos dois ambientes testados "
          "em 16/09/2026). Rode do seu terminal normal.\n")

    saida = Path(args.saida)
    saida.mkdir(exist_ok=True, parents=True)
    sessao = _sessao()
    linhas_resumo = []

    for i, row in alvos.iterrows():
        municipio, uf, ibge = row["municipio"], row["uf"], row["cod_ibge"]
        print(f"\n=== [{i+1}/{len(alvos)}] {municipio}/{uf} (IBGE {ibge}) ===")

        achados = buscar_municipio(sessao, ibge, modalidades, data_ini, data_fim, args.pausa,
                                    bloco_dias=args.bloco_dias)
        print(f"  {len(achados)} contratação(ões) com termo de transporte no objeto.")

        contratos_extra = []
        if args.buscar_contrato and achados:
            cnpjs = {a.get("orgaoEntidade", {}).get("cnpj") for a in achados if a.get("orgaoEntidade")}
            for cnpj in cnpjs:
                filtrados, total_bruto = buscar_contrato(sessao, cnpj, data_ini, data_fim, args.pausa,
                                                          bloco_dias=args.bloco_dias)
                print(f"  cnpj {cnpj}: {len(filtrados)} contrato(s) com termo de transporte "
                      f"(de {total_bruto} verificados no órgão).")
                contratos_extra.extend(filtrados)

        if achados or contratos_extra:
            arq = saida / f"achados_{municipio}-{uf}.json".replace("/", "-")
            arq.write_text(
                json.dumps({"contratacoes": achados, "contratos": contratos_extra}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"  📄 salvo: {arq}")

        for a in achados:
            orgao = a.get("orgaoEntidade", {}) or {}
            linhas_resumo.append({
                "municipio": municipio, "uf": uf, "cod_ibge": ibge,
                "tipo": "contratacao",
                "modalidade": a.get("_modalidade_nome", ""),
                "orgao": orgao.get("razaoSocial", ""),
                "cnpj_orgao": orgao.get("cnpj", ""),
                "objeto": (a.get("objetoCompra") or "")[:300],
                "valor_estimado": a.get("valorTotalEstimado"),
                "data_publicacao": a.get("dataPublicacaoPncp"),
                "link_pncp": a.get("linkSistemaOrigem") or a.get("numeroControlePNCP"),
            })
        # contratos_extra já vem filtrado por buscar_contrato — não precisa refiltrar aqui.
        for c in contratos_extra:
            linhas_resumo.append({
                "municipio": municipio, "uf": uf, "cod_ibge": ibge,
                "tipo": "contrato",
                "modalidade": "",
                "orgao": (c.get("orgaoEntidade") or {}).get("razaoSocial", ""),
                "cnpj_orgao": (c.get("orgaoEntidade") or {}).get("cnpj", ""),
                "fornecedor": c.get("nomeRazaoSocialFornecedor", ""),
                "cnpj_fornecedor": c.get("niFornecedor", ""),
                "objeto": (c.get("objetoContrato") or "")[:300],
                "valor_inicial": c.get("valorInicial"),
                "vigencia_inicio": c.get("dataVigenciaInicio"),
                "vigencia_fim": c.get("dataVigenciaFim"),
            })

    resumo = pd.DataFrame(linhas_resumo)
    resumo.to_csv(saida / "resumo.csv", index=False, encoding="utf-8-sig")
    print(f"\n=== Resumo: {len(resumo)} linha(s) de achado (contratações + contratos) "
          f"em {resumo['municipio'].nunique() if not resumo.empty else 0} município(s) ===")
    print(f"Detalhe em {saida}/resumo.csv e um .json por município com achado.")
    print("\n⚠️ Lembrete: 'não achou nada' pode ser (a) modalidade errada — confira com "
          "--listar-modalidades ou rode com --modalidades todas; (b) contrato anterior a "
          "2021 ou de concessão (Lei 8.987/1995) nunca republicado no PNCP — gap de "
          "cobertura, não ausência de contrato; (c) termo de busca não bate com o objeto "
          "cadastrado — abrir o link_pncp/numeroControlePNCP manualmente antes de "
          "descartar o caso.")
    if not args.buscar_contrato:
        print("\n➡️ Próximo passo sugerido: revise o resumo.csv, monte um CSV menor só com "
              "os municípios/casos relevantes, e rode de novo com --buscar-contrato "
              "(Fase 2) apenas nesse subconjunto.")


if __name__ == "__main__":
    main()
