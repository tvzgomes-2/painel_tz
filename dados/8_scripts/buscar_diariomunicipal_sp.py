#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buscar_diariomunicipal_sp.py

PILOTO — busca "tarifa zero" e termos correlatos no Diário Oficial dos
Municípios Paulistas (SIGPub), mantido pela APM (Associação Paulista de
Municípios): https://www.diariomunicipal.com.br/apm/

Por quê SP e não outro estado: é o estado com mais municípios em "C" (nada
localizado) no nosso Controle único — maior chance de achar algo novo aqui.

Por que "piloto" e não script definitivo: eu (Claude) não consigo testar
isso do meu lado — meu sandbox bloqueia esse domínio (mesma razão por que
não dava para testar api.queridodiario.ok.org.br direto de lá). Então este
script é OTIMISTA e MUITO instrumentado: ele salva a página bruta e imprime
diagnóstico detalhado em cada etapa, para que, se algo não bater com o que
o site realmente devolve, dê para ajustar com base no que ACONTECEU, não
adivinhando de novo (mesmo princípio usado no resto desta pesquisa).

COMO O FORMULÁRIO FUNCIONA (visto num teste manual do autor em 11/09/2026):
  1. GET  /apm/pesquisar-diario           -> página com um token CSRF
     (campo busca_avancada[_token]) embutido no HTML, ligado à sessão.
  2. GET  /apm/pesquisar?busca_avancada[titulo]=...&busca_avancada[texto]=...
     &busca_avancada[dataInicio]=DD/MM/AAAA&busca_avancada[dataFim]=DD/MM/AAAA
     &busca_avancada[_token]=<token da etapa 1>
     -> precisa do MESMO cookie de sessão da etapa 1, senão o token é
     rejeitado (comportamento típico de proteção CSRF Symfony).
  3. IMPORTANTE: o teste manual do autor veio com dataInicio=dataFim=hoje
     (o formulário provavelmente pré-preenche "hoje" por padrão) — isso não
     é útil para nós, então este script SEMPRE força um intervalo amplo
     (DATA_INICIO_PADRAO até hoje), a não ser que --data-inicio/--data-fim
     sejam passados.
  4. O teste manual também caiu no campo "titulo" (ementa), não "texto"
     (corpo do documento) — este script busca por "texto" (mais amplo),
     mas também tenta "titulo" isoladamente se --so-titulo for passado.

⚠️ CONCLUSÃO DO PILOTO (11/09/2026) — VIA HTTP SIMPLES NÃO FUNCIONA:
  Confirmado com teste de controle: o autor buscou "decreto" (termo garantido
  de aparecer em qualquer diário) manualmente no navegador, entre 01/03/2026
  e 30/06/2026, e VIU resultados na tela. Rodando este mesmo script com
  --termo decreto no mesmo intervalo, o resultado foi 0 — a resposta HTTP
  bruta que o `requests` recebe não contém os resultados que o navegador
  mostra. Ou seja: os resultados desta plataforma são montados por
  JavaScript no navegador DEPOIS que a página carrega (confirma a suspeita
  da classe "rest-search-materias" vista antes) — não vêm na resposta que
  uma chamada HTTP simples recebe, por mais que o formulário/token/datas
  estejam corretos.
  CONSEQUÊNCIA: automatizar isso de verdade exigiria um navegador
  automatizado (Playwright/Selenium rodando o JS de verdade), não uma
  chamada HTTP com `requests` — categoria de esforço bem maior, e ainda por
  cima por estado (cada associação estadual é uma instância separada).
  DECISÃO (conversa de 11/09/2026): pausar esta via e priorizar o Querido
  Diário (API JSON documentada, sem essa complicação) — retomar aqui só se
  o Querido Diário não cobrir alguma lacuna específica E valer o esforço de
  automação por navegador para 1 caso pontual.

O QUE ESTE SCRIPT NÃO SABE (só descobrimos rodando de verdade):
  - Se o token dura só 1 uso ou a sessão inteira.
  - Se há paginação de fato via busca_avancada[page] (chutamos 1, 2, 3...).
  - A estrutura EXATA do HTML de resultado — por isso ele salva a página
    bruta da 1ª busca em `<saida>/pagina1_bruta.html` SEMPRE, e tenta
    extrair resultados via um padrão de link (/apm/materia/HEX/token), que
    foi o formato visto num resultado de outra instância (FAMURS) nesta
    mesma plataforma SIGPub.
  - Se há limite de intervalo de datas (ex.: só aceita até 1 ano de range).
    Se a busca vier vazia com um erro de validação, tentar um intervalo
    menor primeiro (ex.: 01/01/2020 a hoje) antes de desistir.

Uso:
    conda activate <seu_ambiente>      # precisa de: requests
    cd caminho\\para\\_meta\\scripts
    python buscar_diariomunicipal_sp.py
    python buscar_diariomunicipal_sp.py --termo "passe livre"
    python buscar_diariomunicipal_sp.py --data-inicio 01/01/2020

Saída: <saida>/pagina1_bruta.html (sempre) + <saida>/achados_<termo>.csv
(se o parser encontrar algo reconhecível).

Autor: Thiago Von Zeidler Gomes
Orientadora: Prof.ª Silvana Zioni
"""

import argparse
import re
import time
from datetime import date, timedelta
from pathlib import Path

import requests

BASE = "https://www.diariomunicipal.com.br/apm"
URL_BUSCA = f"{BASE}/pesquisar"

# 11/09/2026: a 1ª tentativa usou /pesquisar-diario como página do
# formulário — ERRADO. Essa URL é um seletor de MUNICÍPIO (form_estado),
# sem nenhum campo busca_avancada; o token que ela tem (state[_token]) é
# um placeholder ("csrf-token") preenchido por JS no navegador, não um
# token real utilizável. O formulário de busca avançada de verdade (que
# gera os campos busca_avancada[...] vistos numa busca real do autor)
# deve estar na própria /pesquisar sem parâmetros — testando isso primeiro
# agora, com um candidato alternativo de reserva.
URLS_FORMULARIO_CANDIDATAS = [
    URL_BUSCA,  # /apm/pesquisar sem query — mais provável
    f"{BASE}/pesquisar-diario",  # fallback (sabemos que É o form errado,
                                  # mas mantido para diagnóstico comparativo)
]

DATA_INICIO_PADRAO = "01/01/2010"

TERMOS_PADRAO = [
    "tarifa zero",
    "passe livre",
    "transporte coletivo gratuito",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
    ),
    # user-agent de navegador comum só para não cair em algum filtro que
    # rejeite clientes HTTP "crus" sem User-Agent — NÃO é para disfarçar
    # automação de humano (o site não bloqueia bot; é só higiene de
    # requisição, muitos servidores recusam requests sem UA por engano).
}


def chamar_com_retentativas(func_chamada, tentativas: int = 4, espera_base: float = 4.0):
    """Mesmo padrão usado em buscar_querido_diario.py: retentativa em erro
    transitório (timeout, conexão, 429/5xx), com espera crescente."""
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
            print(f"    ⏳ tentativa {tentativa}/{tentativas} falhou "
                  f"({type(ultimo_erro).__name__}: {ultimo_erro}); "
                  f"esperando {espera:.0f}s...")
            time.sleep(espera)
    raise ultimo_erro


def pegar_token(sessao: requests.Session, saida: Path) -> tuple:
    """Tenta cada URL candidata em ordem; salva o HTML de CADA uma (não só
    da que 'der certo') para diagnóstico, e retorna (token, url_usada) da
    primeira que tiver um campo busca_avancada[_token] com valor que NÃO
    seja um placeholder óbvio (ex.: "csrf-token")."""
    candidatos_regex = [
        r'name="busca_avancada\[_token\]"[^>]*\svalue="([^"]+)"',
        r'busca_avancada\[_token\]"\s*value="([^"]+)"',
        r'"_token"\s*:\s*"([^"]+)"',
    ]
    placeholders_obvios = {"csrf-token", "token", ""}

    diagnostico = []
    for i, url in enumerate(URLS_FORMULARIO_CANDIDATAS, start=1):
        def chamada():
            r = sessao.get(url, headers=_HEADERS, timeout=30)
            r.raise_for_status()
            return r

        try:
            r = chamar_com_retentativas(chamada)
        except Exception as e:
            diagnostico.append(f"  {i}. {url} -> erro: {e}")
            continue

        html = r.text
        arq = saida / f"formulario_bruto_{i}.html"
        arq.write_text(html, encoding="utf-8")

        tem_busca_avancada = "busca_avancada" in html
        token_achado = None
        for padrao in candidatos_regex:
            m = re.search(padrao, html)
            if m and m.group(1) not in placeholders_obvios:
                token_achado = m.group(1)
                break

        diagnostico.append(
            f"  {i}. {url} -> salvo em {arq.name}; "
            f"contém 'busca_avancada': {tem_busca_avancada}; "
            f"token real achado: {'sim' if token_achado else 'não'}"
        )

        if token_achado:
            return token_achado, url

    raise RuntimeError(
        "Não achei um token CSRF real (não-placeholder) em nenhuma das "
        "URLs candidatas. Diagnóstico:\n" + "\n".join(diagnostico) +
        "\n\nAbra os arquivos formulario_bruto_N.html salvos na pasta de "
        "saída, procure por 'busca_avancada' (Ctrl+F) e veja se o campo "
        "_token tem um valor de verdade ali perto — me manda esse trecho "
        "para eu ajustar o regex ou a URL."
    )


def buscar_pagina(
    sessao: requests.Session, token: str, termo: str, campo: str,
    data_inicio: str, data_fim: str, pagina: int,
) -> requests.Response:
    params = {
        "busca_avancada[page]": str(pagina) if pagina > 1 else "",
        "busca_avancada[entidadeUsuaria]": "",
        "busca_avancada[nome_orgao]": "",
        "busca_avancada[titulo]": termo if campo == "titulo" else "",
        "busca_avancada[texto]": termo if campo == "texto" else "",
        "busca_avancada[dataInicio]": data_inicio,
        "busca_avancada[dataFim]": data_fim,
        "busca_avancada[Enviar]": "",
        "busca_avancada[_token]": token,
    }

    def chamada():
        r = sessao.get(URL_BUSCA, params=params, headers=_HEADERS, timeout=45)
        r.raise_for_status()
        return r

    return chamar_com_retentativas(chamada)


PADRAO_LINK_MATERIA = re.compile(r'/apm/materia/[A-Fa-f0-9]+/[\w\-]+')


def extrair_resultados(html: str) -> list:
    """Tenta achar blocos de resultado pelo padrão de link /apm/materia/...
    (visto num resultado real de outra instância SIGPub, FAMURS-RS).
    Retorna uma lista de dicts com o link e ~300 caracteres de contexto ao
    redor (para dar pista do título/órgão/data sem precisar entender a
    estrutura HTML exata)."""
    achados = []
    for m in PADRAO_LINK_MATERIA.finditer(html):
        ini = max(0, m.start() - 300)
        fim = min(len(html), m.end() + 100)
        contexto_bruto = html[ini:fim]
        # tira tags HTML de forma tosca só para dar um contexto legível
        contexto_texto = re.sub(r"<[^>]+>", " ", contexto_bruto)
        contexto_texto = re.sub(r"\s+", " ", contexto_texto).strip()
        achados.append({
            "link": "https://www.diariomunicipal.com.br" + m.group(0),
            "contexto": contexto_texto[-400:],  # o que vem ANTES do link importa mais
        })
    return achados


_MESES_DIAS = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def _bissexto(ano: int) -> bool:
    return ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0)


def somar_meses(d: date, n: int) -> date:
    m = d.month - 1 + n
    ano = d.year + m // 12
    mes = m % 12 + 1
    dia_max = _MESES_DIAS[mes - 1]
    if mes == 2 and not _bissexto(ano):
        dia_max = 28
    return date(ano, mes, min(d.day, dia_max))


def gerar_janelas(data_inicio: date, data_fim: date, meses_por_janela: int = 5) -> list:
    """Quebra [data_inicio, data_fim] em janelas de no máximo `meses_por_janela`
    meses (o site rejeita qualquer busca com intervalo >= 6 meses — usamos 5
    por margem de segurança em vez de tentar cravar exatamente no limite)."""
    janelas = []
    cursor = data_inicio
    while cursor <= data_fim:
        fim_janela = min(somar_meses(cursor, meses_por_janela) - timedelta(days=1), data_fim)
        janelas.append((cursor, fim_janela))
        cursor = fim_janela + timedelta(days=1)
    return janelas


PADRAO_ERRO_VALIDACAO = re.compile(r'<li id="[\w]+_error\d*"[^>]*>([^<]+)</li>')


def detectar_erros_validacao(html: str) -> list:
    """11/09/2026: uma busca com intervalo de datas >= 6 meses NÃO dá erro
    HTTP — devolve HTTP 200 com o próprio formulário de volta e uma mensagem
    de erro tipo <li id="busca_avancada_dataFim_error1">O intervalo das
    datas deve ser inferior a 6 meses.</li>. Sem checar isso explicitamente,
    o script contaria "0 resultados" como se fosse busca vazia, quando na
    verdade a busca nem rodou."""
    return PADRAO_ERRO_VALIDACAO.findall(html)


def rodar(termos, campo, data_inicio_str, data_fim_str, saida: Path, pausa: float,
          max_paginas: int, meses_por_janela: int):
    saida.mkdir(parents=True, exist_ok=True)
    sessao = requests.Session()

    print("=== Etapa 1: pegar token CSRF do formulário ===")
    try:
        token, url_usada = pegar_token(sessao, saida)
        print(f"  ✅ token obtido em {url_usada} ({token[:20]}...).")
    except Exception as e:
        print(f"  🔴 {e}")
        return

    data_inicio = time.strptime(data_inicio_str, "%d/%m/%Y")
    data_fim = time.strptime(data_fim_str, "%d/%m/%Y")
    data_inicio = date(data_inicio.tm_year, data_inicio.tm_mon, data_inicio.tm_mday)
    data_fim = date(data_fim.tm_year, data_fim.tm_mon, data_fim.tm_mday)
    janelas = gerar_janelas(data_inicio, data_fim, meses_por_janela)
    minimo_requisicoes = len(janelas) * len(termos)
    print(f"  intervalo total {data_inicio_str} a {data_fim_str} quebrado em "
          f"{len(janelas)} janela(s) de até {meses_por_janela} mes(es) cada "
          f"(o site rejeita janelas >= 6 meses).")
    print(f"  isso é no mínimo {minimo_requisicoes} requisições (janelas x termos, "
          f"mais se alguma janela tiver mais de 1 página de resultado) — com "
          f"{pausa}s de pausa entre cada uma, pelo menos ~{minimo_requisicoes * pausa / 60:.1f} min.")

    for termo in termos:
        print(f"\n=== termo: '{termo}' (campo={campo}) — {len(janelas)} janela(s) ===")
        todos_achados = []
        primeira_pagina_salva = False

        for idx_janela, (jan_inicio, jan_fim) in enumerate(janelas, start=1):
            ji_str = jan_inicio.strftime("%d/%m/%Y")
            jf_str = jan_fim.strftime("%d/%m/%Y")

            for pagina in range(1, max_paginas + 1):
                try:
                    r = buscar_pagina(sessao, token, termo, campo, ji_str, jf_str, pagina)
                except Exception as e:
                    print(f"  🔴 janela {idx_janela} ({ji_str}-{jf_str}), "
                          f"página {pagina}: erro: {e}")
                    break

                # pausa incondicional a cada requisição (não só quando há
                # achado) — a maioria das janelas vai dar 0 resultado, e sem
                # isso o script martelaria o site sem espera nenhuma na
                # maior parte do tempo.
                time.sleep(pausa)

                erros = detectar_erros_validacao(r.text)
                if erros:
                    print(f"  ⚠️  janela {idx_janela} ({ji_str}-{jf_str}): "
                          f"formulário recusou a busca — {'; '.join(erros)}")
                    if not primeira_pagina_salva:
                        arq_erro = saida / f"erro_validacao_{re.sub(r'[^a-z0-9]+', '_', termo.lower())}.html"
                        arq_erro.write_text(r.text, encoding="utf-8")
                        primeira_pagina_salva = True
                    break  # não adianta paginar uma busca que nem rodou

                if not primeira_pagina_salva:
                    arq_bruto = saida / f"pagina1_bruta_{re.sub(r'[^a-z0-9]+', '_', termo.lower())}.html"
                    arq_bruto.write_text(r.text, encoding="utf-8")
                    print(f"  📄 (janela {idx_janela}) página salva em {arq_bruto.name} "
                          f"para inspecionar se algo não bater.")
                    primeira_pagina_salva = True

                achados_pagina = extrair_resultados(r.text)
                if achados_pagina:
                    print(f"  janela {idx_janela} ({ji_str}-{jf_str}), página {pagina}: "
                          f"{len(achados_pagina)} resultado(s).")
                    todos_achados.extend(achados_pagina)
                else:
                    break

        if todos_achados:
            arq_csv = saida / f"achados_{re.sub(r'[^a-z0-9]+', '_', termo.lower())}.csv"
            import csv
            with arq_csv.open("w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=["link", "contexto"])
                w.writeheader()
                w.writerows(todos_achados)
            print(f"  ✅ {len(todos_achados)} achado(s) no total, salvos em {arq_csv}")
        else:
            print(f"  (nenhum achado reconhecido para '{termo}' em nenhuma janela — "
                  f"se isso for surpreendente, veja pagina1_bruta_*.html e "
                  f"erro_validacao_*.html, se existir, na pasta de saída.)")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--termo", action="append", default=None,
                     help="Termo a buscar (pode repetir --termo várias vezes). "
                          "Padrão: os 3 termos em TERMOS_PADRAO.")
    ap.add_argument("--campo", choices=["texto", "titulo"], default="texto",
                     help="Buscar no corpo do documento ('texto', padrão, mais "
                          "amplo) ou só na ementa ('titulo', mais restrito).")
    ap.add_argument("--data-inicio", default=DATA_INICIO_PADRAO,
                     help=f"DD/MM/AAAA (padrão {DATA_INICIO_PADRAO}).")
    ap.add_argument("--data-fim", default=date.today().strftime("%d/%m/%Y"),
                     help="DD/MM/AAAA (padrão hoje).")
    ap.add_argument("--saida", default="saida_diariomunicipal_sp")
    ap.add_argument("--pausa", type=float, default=1.5)
    ap.add_argument("--max-paginas", type=int, default=20,
                     help="Teto de páginas por janela, cinto de segurança (padrão 20).")
    ap.add_argument("--meses-por-janela", type=int, default=5,
                     help="Tamanho de cada janela de busca em meses (padrão 5 — "
                          "o site rejeita qualquer intervalo >= 6 meses).")
    args = ap.parse_args()

    termos = args.termo if args.termo else TERMOS_PADRAO
    print(f"PILOTO diariomunicipal.com.br/apm (SP) — {len(termos)} termo(s), "
          f"{args.data_inicio} a {args.data_fim}, campo={args.campo}.")
    rodar(termos, args.campo, args.data_inicio, args.data_fim,
          Path(args.saida), args.pausa, args.max_paginas, args.meses_por_janela)


if __name__ == "__main__":
    main()
